"""
AI Recommendation Enhancer
===========================

HYBRID INTELLIGENCE: Combines institutional data analysis with AI reasoning

Our Analysis (Data-Driven) → AI Enhancement (Context & Reasoning) → Optimal Recommendations

Sprint: BTCAAAAA-36469 (AI Recs P1) — rewritten to use:
  * ``LlmClient`` for transport (retry/backoff/jitter/timeout/budget, no bare
    ``requests.post``).
  * ``AIResponse`` + ``parse_chat_completion_envelope`` for strict,
    schema-validated parsing (no fabricated defaults, no silent drops of
    unknown top-level fields).
  * ``sanitize_name`` for user-controlled strings (strategy / block / signal
    names) — neutralises prompt-injection patterns before they enter the
    request body.

Public interface preserved for downstream consumers (notably
``src.optimizer_v3.core.intelligent_recommendation_engine``):
  * ``AIEnhancedRecommendation`` dataclass — unchanged fields.
  * ``AIRecommendationEnhancer()`` — no-arg constructor.
  * ``enhancer.enabled`` / ``enhancer.model`` / ``enhancer.last_full_analysis``.
  * ``enhancer.enhance_recommendations(strategy_config, backtest_results,
    analysis_report, preliminary_recommendations)`` — returns
    ``List[AIEnhancedRecommendation]``.

The contract is exercised by
``tests/optimizer_v3/test_ai_recommendation_enhancer_p1.py``.
"""

from __future__ import annotations

import copy
import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests  # kept for the test-suite compatibility shim in `__main__`
from dotenv import load_dotenv

# ── P1 imports: unified client + strict schema + sanitization ───────────────
from src.optimizer_v3.core.ai_response_schema import (
    AIEnhancedRecommendationModel,
    AIResponse,
    AIResponseSchemaError,
    parse_chat_completion_envelope,
)
from src.optimizer_v3.core.llm_client import LlmClient, LlmError
from src.optimizer_v3.core.prompt_sanitizer import sanitize_name

# Import ComprehensiveAIRequestBuilder for institutional-grade prompts
from src.optimizer_v3.core.comprehensive_ai_request_builder import (
    ComprehensiveAIRequestBuilder,
)


# Module-level references are required so tests can monkeypatch
# ``mod.LlmClient`` (see ``tests/optimizer_v3/test_ai_recommendation_enhancer_p1.py``).
__all__ = [
    "AIEnhancedRecommendation",
    "AIRecommendationEnhancer",
    "LlmClient",
    "LlmError",
    "AIResponse",
    "AIResponseSchemaError",
]


# Load environment variables
load_dotenv()

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not any(
    isinstance(h, logging.FileHandler)
    and getattr(h, "baseFilename", "").endswith("ai_recommendations.log")
    for h in logger.handlers
):
    fh = logging.FileHandler(log_dir / "ai_recommendations.log")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)


# ── Public dataclass (interface preserved) ──────────────────────────────────


@dataclass
class AIEnhancedRecommendation:
    """AI-enhanced recommendation with specific configurations.

    Public field set is unchanged from the P0 release — downstream code
    (e.g. ``intelligent_recommendation_engine``) reads ``ai_confidence`` to
    distinguish AI-enhanced from data-driven recs.
    """

    type: str  # ADD_BLOCK, ADD_RECHECK, ADD_TIMING, ADJUST_PARAM
    primary: bool  # Is this the primary recommendation?
    block_name: Optional[str] = None
    signal_name: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None  # Specific settings
    reasoning: str = ""
    expected_impact: Optional[Dict[str, str]] = None
    confidence: float = 0.0
    ai_confidence: float = 0.0
    data_confidence: float = 0.0
    warnings: Optional[List[str]] = None

    def __post_init__(self):
        if self.configuration is None:
            self.configuration = {}
        if self.expected_impact is None:
            self.expected_impact = {}
        if self.warnings is None:
            self.warnings = []


# ── Enhancer ─────────────────────────────────────────────────────────────────


class AIRecommendationEnhancer:
    """
    AI-POWERED RECOMMENDATION ENHANCEMENT

    Uses OpenRouter API to enhance recommendations with:
    - Market context awareness
    - Nuanced configuration suggestions
    - Risk assessment
    - Optimal parameter values
    - Priority ordering

    Falls back gracefully if API key not available or the upstream call fails
    for any reason (timeout, 5xx, schema mismatch, etc.).
    """

    SYSTEM_PROMPT = (
        "You are an elite institutional quantitative strategist specializing in "
        "Bitcoin trading systems. You provide specific, actionable recommendations "
        "with exact configurations. You understand signal interactions, trade "
        "frequency impacts, and institutional risk management. Respond in valid "
        "JSON only."
    )

    def __init__(self, llm_client: Optional[LlmClient] = None):
        """Initialize AI enhancer.

        ``llm_client`` is injectable for tests; in production it is lazily
        constructed on first use so the enhancer never crashes at import time
        on a misconfigured environment.
        """
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.enabled = bool(self.api_key)
        self.model = os.getenv("AI_MODEL", "anthropic/claude-3.5-sonnet")
        # Stores the full AI diagnosis from the last successful response.
        # Initialised with the four P1 contract keys (assessment,
        # root_cause_analysis, implementation_order, extra_fields) so callers
        # can read them without first checking for presence.
        self.last_full_analysis: Dict[str, Any] = {
            "assessment": "",
            "root_cause_analysis": {},
            "implementation_order": [],
            "extra_fields": {},
        }
        self._llm_client: Optional[LlmClient] = llm_client

        if self.enabled:
            logger.info(f"✅ AI Enhancement ENABLED (Model: {self.model})")
        else:
            logger.info("ℹ️ AI Enhancement DISABLED (No OPENROUTER_API_KEY in .env)")

    # ── Public API ──────────────────────────────────────────────────────────

    def enhance_recommendations(
        self,
        strategy_config: Dict,
        backtest_results: Dict,
        analysis_report,  # StrategyAnalysisReport
        preliminary_recommendations: List,
    ) -> List[AIEnhancedRecommendation]:
        """
        Enhance recommendations with AI reasoning.

        Returns AI-enhanced recommendations when the upstream call succeeds
        and the response parses; otherwise returns a data-driven fallback
        derived from ``preliminary_recommendations``. Never raises on
        AI/transport failure.
        """
        if not self.enabled:
            logger.warning("⚠️ AI enhancement skipped (not enabled)")
            return self._convert_to_enhanced_format(preliminary_recommendations)

        try:
            logger.info("🤖 Querying AI for recommendation enhancement...")

            # Neutralise user-controlled strings before they enter the prompt.
            sanitized_strategy = self._sanitize_strategy_names(strategy_config)

            prompt = self._build_analysis_prompt(
                sanitized_strategy,
                backtest_results,
                analysis_report,
                preliminary_recommendations,
            )

            llm_client = self._get_llm_client()
            response_json = llm_client.chat(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=3000,
                response_format={"type": "json_object"},
            )

            parsed = parse_chat_completion_envelope(response_json)

            # Persist the full diagnosis (including unknown top-level fields
            # surfaced via ``extra_fields``) for UI display.
            self.last_full_analysis = {
                "assessment": parsed.assessment,
                "root_cause_analysis": dict(parsed.root_cause_analysis),
                "implementation_order": list(parsed.implementation_order),
                "extra_fields": dict(parsed.extra_fields),
            }
            logger.debug(
                f"[AI Response] assessment={bool(parsed.assessment)}, "
                f"root_cause_analysis={bool(parsed.root_cause_analysis)}, "
                f"implementation_order={len(parsed.implementation_order)} steps, "
                f"extra_fields={list(parsed.extra_fields)}"
            )

            enhanced_recs = self._build_enhanced_recs_from_schema(
                parsed.recommendations
            )
            validated_recs = self._validate_ai_recommendations(
                enhanced_recs, analysis_report
            )

            logger.info(
                f"✅ AI enhancement complete: {len(validated_recs)} recommendations"
            )
            return validated_recs

        except AIResponseSchemaError as exc:
            logger.error(f"⚠️ AI response failed schema validation: {exc}")
            logger.info("📊 Falling back to data-driven recommendations")
            return self._convert_to_enhanced_format(preliminary_recommendations)
        except LlmError as exc:
            logger.error(f"⚠️ LLM call failed: {exc}")
            logger.info("📊 Falling back to data-driven recommendations")
            return self._convert_to_enhanced_format(preliminary_recommendations)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(f"⚠️ AI response JSON parse error: {exc}")
            logger.info("📊 Falling back to data-driven recommendations")
            return self._convert_to_enhanced_format(preliminary_recommendations)
        except Exception as exc:  # noqa: BLE001 — defensive: never crash the caller
            logger.error(f"⚠️ AI enhancement failed: {exc}")
            logger.info("📊 Falling back to data-driven recommendations")
            return self._convert_to_enhanced_format(preliminary_recommendations)

    def format_recommendation_text(self, rec: AIEnhancedRecommendation) -> str:
        """Format enhanced recommendation as display text."""

        if rec.ai_confidence > 0:
            header = "🤖 AI-ENHANCED:"
        else:
            header = "📊 DATA-DRIVEN:"

        if rec.type == "ADD_BLOCK":
            text = f"{header} Add '{rec.block_name}' block"
        elif rec.type == "ADD_RECHECK":
            bar_delay = rec.configuration.get("bar_delay", 25)
            text = (
                f"{header} Add recheck to "
                f"'{rec.block_name}::{rec.signal_name}' (delay: {bar_delay} bars)"
            )
        elif rec.type == "ADD_TIMING":
            max_candles = rec.configuration.get("max_candles", 20)
            text = f"{header} Add timing dependency (within {max_candles} candles)"
        elif rec.type == "ADJUST_PARAM":
            text = (
                f"{header} Adjust "
                f"{rec.configuration.get('parameter_name', 'parameter')}"
            )
        else:
            text = f"{header} {rec.reasoning[:100]}"

        if rec.expected_impact:
            impacts = [f"{k}: {v}" for k, v in rec.expected_impact.items()]
            text += f" (Expected: {', '.join(impacts[:2])})"

        text += f" [Confidence: {rec.confidence:.0%}]"

        return text

    # ── Internals ───────────────────────────────────────────────────────────

    def _get_llm_client(self) -> LlmClient:
        """Lazily build a real LlmClient (env-driven) the first time we need one."""
        if self._llm_client is None:
            self._llm_client = LlmClient()
        return self._llm_client

    @staticmethod
    def _sanitize_strategy_names(strategy_config: Dict) -> Dict:
        """Return a deep-copy of ``strategy_config`` with all ``name`` strings
        passed through :func:`sanitize_name`. Non-string names are coerced
        to ``str`` first so we never pass ``None``/ints into the prompt.
        """
        if not isinstance(strategy_config, dict):
            return strategy_config

        scrubbed = copy.deepcopy(strategy_config)

        def _walk(node: Any) -> None:
            if isinstance(node, dict):
                for k, v in list(node.items()):
                    if k in {"name", "block_name", "signal_name"} and v is not None:
                        node[k] = sanitize_name(v if isinstance(v, str) else str(v))
                    else:
                        _walk(v)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)

        _walk(scrubbed)
        return scrubbed

    def _build_analysis_prompt(
        self,
        strategy_config: Dict,
        backtest_results: Dict,
        analysis_report,
        preliminary_recommendations: List,
    ) -> str:
        """
        Build comprehensive prompt using ComprehensiveAIRequestBuilder.
        """
        logger.info("🔧 Building institutional-grade AI prompt...")

        builder = ComprehensiveAIRequestBuilder()

        metrics_with_ratings: Dict[str, Dict[str, Any]] = {}

        metric_keys = [
            "total_pnl",
            "win_rate",
            "profit_factor",
            "sharpe_ratio",
            "max_drawdown_pct",
            "num_trades",
            "avg_win",
            "avg_loss",
            "largest_win",
            "largest_loss",
            "risk_reward_ratio",
            "recovery_factor",
            "sortino_ratio",
            "calmar_ratio",
            "max_consecutive_losses",
        ]

        for key in metric_keys:
            if key in backtest_results:
                value = backtest_results[key]
                rating = self._get_metric_rating(key, value, analysis_report)
                metrics_with_ratings[key] = {
                    "value": float(value) if value is not None else 0.0,
                    "rating": rating,
                    "category": "Performance",
                }

        request = builder.build_complete_request(
            strategy_config=strategy_config,
            backtest_results=backtest_results,
            metrics_with_ratings=metrics_with_ratings,
            backtest_config=backtest_results.get("config", {}),
            analysis_report=analysis_report,
        )

        prompt = builder.format_for_ai_prompt(request)

        logger.info(f"✅ Comprehensive prompt built: {len(prompt):,} characters")
        logger.info("   (Expected: 50,000+ for complete data)")

        return prompt

    @staticmethod
    def _get_metric_rating(metric_key: str, value, analysis_report) -> str:
        """Get rating for metric based on analysis."""
        try:
            val = float(value)

            if metric_key == "win_rate":
                return "✓ Good" if val >= 60 else ("⚠ Fair" if val >= 50 else "✗ Poor")
            if metric_key == "profit_factor":
                return (
                    "✓ Good"
                    if val >= 2.0
                    else ("⚠ Fair" if val >= 1.5 else "✗ Poor")
                )
            if metric_key == "sharpe_ratio":
                return (
                    "✓ Good"
                    if val >= 2.0
                    else ("⚠ Fair" if val >= 1.0 else "✗ Poor")
                )
            if metric_key == "max_drawdown_pct":
                return (
                    "✓ Good"
                    if val <= 10
                    else ("⚠ Fair" if val <= 20 else "✗ Poor")
                )
            if metric_key == "num_trades":
                return (
                    "✓ Good"
                    if val >= 30
                    else ("⚠ Fair" if val >= 15 else "✗ Poor")
                )
            return "-"
        except (TypeError, ValueError):
            return "-"

    def _build_enhanced_recs_from_schema(
        self, model_recs: List[AIEnhancedRecommendationModel]
    ) -> List[AIEnhancedRecommendation]:
        """Convert schema-validated models into the public dataclass.

        The combined ``confidence`` is the unweighted average of the AI's
        ``ai_confidence`` and the data-driven ``data_confidence`` — both
        must be present (the schema enforces that).
        """
        enhanced: List[AIEnhancedRecommendation] = []
        for m in model_recs:
            combined = max(0.0, min(1.0, 0.5 * m.ai_confidence + 0.5 * m.data_confidence))
            expected_impact = self._coerce_impact(m.expected_impact)
            enhanced.append(
                AIEnhancedRecommendation(
                    type=m.type,
                    primary=bool(m.primary),
                    block_name=m.block_name,
                    signal_name=m.signal_name,
                    configuration=dict(m.configuration),
                    reasoning=m.reasoning,
                    expected_impact=expected_impact,
                    confidence=combined,
                    ai_confidence=m.ai_confidence,
                    data_confidence=m.data_confidence,
                    warnings=list(m.warnings),
                )
            )
        return enhanced

    @staticmethod
    def _coerce_impact(raw: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Coerce ``expected_impact`` to ``Dict[str, str]`` (public contract)."""
        if not raw:
            return {}
        out: Dict[str, str] = {}
        for k, v in raw.items():
            if v is None:
                continue
            out[str(k)] = v if isinstance(v, str) else str(v)
        return out

    def _validate_ai_recommendations(
        self,
        ai_recommendations: List[AIEnhancedRecommendation],
        analysis_report,
    ) -> List[AIEnhancedRecommendation]:
        """
        Validate AI recommendations against our analysis.

        Safety check: ensure AI recommendations make sense given our data.
        """
        validated: List[AIEnhancedRecommendation] = []

        for rec in ai_recommendations:
            valid = True
            warnings = list(rec.warnings or [])

            # Check 1: If recommending new block, ensure not already in strategy
            if rec.type == "ADD_BLOCK" and rec.block_name:
                if rec.block_name in analysis_report.block_names:
                    valid = False
                    warnings.append(
                        f"Block '{rec.block_name}' already in strategy"
                    )

            # Check 2: If adding recheck, ensure block exists
            if rec.type == "ADD_RECHECK" and rec.block_name:
                if rec.block_name not in analysis_report.block_names:
                    valid = False
                    warnings.append(
                        f"Block '{rec.block_name}' not in strategy"
                    )

            # Check 3: Trade frequency warning
            if rec.type == "ADD_BLOCK":
                if analysis_report.trade_frequency.frequency_assessment in [
                    "TOO_LOW",
                    "LOW",
                ]:
                    warnings.append(
                        "WARNING: Trade frequency already low - "
                        "adding block will reduce further"
                    )

            # Check 4: Confidence sanity check
            if rec.confidence > 0.95:
                rec.confidence = 0.95  # Cap at 95% (never 100% certain)

            rec.warnings = warnings

            if valid:
                validated.append(rec)

        return validated

    def _convert_to_enhanced_format(
        self, preliminary_recommendations: List
    ) -> List[AIEnhancedRecommendation]:
        """
        Convert preliminary recommendations to enhanced format.
        Used when AI not available OR when the AI call fails.
        """
        enhanced: List[AIEnhancedRecommendation] = []

        for rec in preliminary_recommendations:
            rec_dict = rec if isinstance(rec, dict) else asdict(rec)

            enhanced_rec = AIEnhancedRecommendation(
                type=rec_dict.get("action_type", "ADD_BLOCK"),
                primary=True,
                block_name=rec_dict.get("block_name"),
                signal_name=None,
                configuration={},
                reasoning=rec_dict.get("description", ""),
                expected_impact={
                    rec_dict.get("metric", "win_rate"): (
                        f"{rec_dict.get('expected_improvement', 0):.1%}"
                    )
                },
                confidence=rec_dict.get("confidence", 0.75),
                ai_confidence=0.0,
                data_confidence=rec_dict.get("confidence", 0.75),
                warnings=[],
            )
            enhanced.append(enhanced_rec)

        return enhanced


# ── Live smoke test (unchanged surface; uses the unified client path) ───────


def test_ai_enhancer():
    """Test AI enhancer with sample data (live smoke test)."""
    import sys

    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))

    logger.info("\n" + "=" * 80)
    logger.info("AI RECOMMENDATION ENHANCER - LIVE TEST")
    logger.info("=" * 80)

    enhancer = AIRecommendationEnhancer()

    if not enhancer.enabled:
        logger.error("\n❌ AI Enhancement not available (no API key)")
        logger.info("Set OPENROUTER_API_KEY in .env to enable")
        return

    strategy_config = {
        "name": "HOD Rejection Test",
        "strategy_type": "Bearish",
        "blocks": [
            {"name": "hod", "signals": [{"name": "HOD_REJECTION"}]},
            {"name": "stochastic_rsi", "signals": [{"name": "BEARISH_CROSS"}]},
            {"name": "rsi_divergence", "signals": [{"name": "BEARISH_DIVERGENCE"}]},
        ],
    }

    backtest_results = {
        "total_pnl": 544.0,
        "win_rate": 58.3,
        "profit_factor": 1.97,
        "max_drawdown_pct": 5.58,
        "num_trades": 24,
        "avg_win": 78.75,
        "avg_loss": -55.85,
    }

    from src.optimizer_v3.core.strategy_deep_analyzer import (
        RootCause,
        RootCauseAnalysis,
        SignalInteraction,
        StrategyAnalysisReport,
        StrategyGaps,
        TradeFrequencyAnalysis,
    )
    from src.optimizer_v3.core.block_intelligence_extractor import BlockPurpose

    analysis_report = StrategyAnalysisReport(
        strategy_name="HOD Rejection Test",
        num_blocks=3,
        num_signals=3,
        block_names=["hod", "stochastic_rsi", "rsi_divergence"],
        trade_frequency=TradeFrequencyAnalysis(
            current_trades_per_year=48,
            current_trades_per_month=4.0,
            signal_frequency_product=0.0075,
            individual_signal_rates={
                "hod": 0.05,
                "stochastic_rsi": 0.15,
                "rsi_divergence": 0.10,
            },
            frequency_assessment="LOW",
            frequency_risk="MODERATE",
            minimum_needed_for_validation=30,
        ),
        gaps=StrategyGaps(
            missing_purposes=[BlockPurpose.RISK_MANAGEMENT, BlockPurpose.VOLATILITY_FILTER],
            coverage_score=0.25,
            critical_gaps=["Missing RISK_MANAGEMENT"],
            nice_to_have_gaps=["Missing VOLATILITY_FILTER"],
            redundant_blocks=[],
        ),
        signal_interactions=SignalInteraction(
            logic_type="AND",
            interaction_factor=0.0075,
            complementary=True,
            conflicting=False,
            sequence_matters=True,
            timing_dependencies=[],
        ),
        root_causes={
            "win_rate": RootCauseAnalysis(
                root_causes=[RootCause.TOO_FEW_TRADES],
                primary_cause=RootCause.TOO_FEW_TRADES,
                confidence=0.85,
                reasoning="Win rate 58.3% based on only 24 trades",
                supporting_evidence=[
                    "Only 4 trades/month",
                    "Need 30 trades minimum",
                ],
            )
        },
        strategy_quality_score=6.5,
        key_issues=["Trade frequency too low (4/month)", "Missing risk management"],
        strengths=["Good win rate (58.3%)", "Low drawdown (5.58%)"],
    )

    preliminary_recommendations = [
        {
            "action_type": "ADD_BLOCK",
            "block_name": "atr",
            "description": "ATR for volatility filtering",
            "expected_improvement": 0.15,
            "confidence": 0.75,
            "metric": "win_rate",
        }
    ]

    logger.info("\n🔬 Testing AI enhancement...")
    try:
        enhanced = enhancer.enhance_recommendations(
            strategy_config,
            backtest_results,
            analysis_report,
            preliminary_recommendations,
        )

        logger.info(f"\n✅ Received {len(enhanced)} enhanced recommendations:")
        for i, rec in enumerate(enhanced, 1):
            logger.info(f"\n{i}. {enhancer.format_recommendation_text(rec)}")
            logger.info(f"   Reasoning: {rec.reasoning[:200]}...")
            if rec.warnings:
                logger.warning(f"   ⚠️ Warnings: {', '.join(rec.warnings)}")

    except Exception as exc:  # noqa: BLE001
        logger.error(f"\n❌ Test failed: {str(exc)}")

    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    test_ai_enhancer()
