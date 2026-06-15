"""
AI Response Schema
==================

Sprint: BTCAAAAA-36469 (AI Recs P1)

Strict, schema-validated parsing of LLM responses for the AI recommendation
enhancer. The previous implementation (``_parse_ai_response`` in
``ai_recommendation_enhancer.py``) silently fabricated defaults like
``confidence=0.75`` when the AI omitted a field. P1 replaces that with:

- **No fabricated defaults** — every recommendation must include the fields
  the rest of the system relies on. A missing field is a parse error.
- **Strict type checking** — ``type`` must be one of
  ``{ADD_BLOCK, ADD_RECHECK, ADD_TIMING, ADJUST_PARAM}``.
- **Confidence in [0, 1]** — both ``ai_confidence`` and ``data_confidence``
  must be numeric and in-range.
- **Registry-aware validation** — block names and signal names can be checked
  against the project's known sets; unknown names are a parse error, not a
  silent acceptance.
- **No silent drops** — unknown top-level fields (e.g. a future model that
  emits a new key) are surfaced via ``extra_fields`` so the UI / callers can
  decide what to do. Same for unknown keys inside a recommendation.

The contract is exercised by ``tests/optimizer_v3/test_ai_recommendation_enhancer_p1.py``.
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


# ── Public constants ────────────────────────────────────────────────────────

ALLOWED_REC_TYPES: Tuple[str, ...] = (
    "ADD_BLOCK",
    "ADD_RECHECK",
    "ADD_TIMING",
    "ADJUST_PARAM",
)

ALLOWED_DIAGNOSIS_TOP_LEVEL_KEYS: Set[str] = {
    "recommendations",
    "assessment",
    "understanding",
    "root_cause_analysis",
    "implementation_order",
    "risk_assessment",
    "estimated_improvement_timeline",
    "overall_confidence",
    "next_steps",
}


# ── Errors ──────────────────────────────────────────────────────────────────


class AIResponseSchemaError(ValueError):
    """Raised when an AI response fails schema validation.

    Carries the failing field path (e.g. ``"recommendations[0].ai_confidence"``)
    in ``field_path`` for diagnostics.
    """

    def __init__(self, message: str, *, field_path: str = "<root>"):
        super().__init__(f"{field_path}: {message}")
        self.field_path = field_path
        self.message = message


# ── Helpers ─────────────────────────────────────────────────────────────────


def _coerce_float(value: Any, *, field_path: str) -> float:
    if isinstance(value, bool):
        raise AIResponseSchemaError(
            f"expected number, got bool {value!r}", field_path=field_path
        )
    if not isinstance(value, (int, float)):
        raise AIResponseSchemaError(
            f"expected number, got {type(value).__name__} ({value!r})",
            field_path=field_path,
        )
    return float(value)


def _ensure_unit_interval(value: Any, *, field_path: str) -> float:
    """Coerce to float and ensure the value is within [0.0, 1.0]."""
    f = _coerce_float(value, field_path=field_path)
    if f < 0.0 or f > 1.0:
        raise AIResponseSchemaError(
            f"value {f!r} outside [0.0, 1.0]", field_path=field_path
        )
    return f


def _coerce_optional_str(value: Any, *, field_path: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AIResponseSchemaError(
            f"expected str or null, got {type(value).__name__}",
            field_path=field_path,
        )
    return value


def _coerce_str(value: Any, *, field_path: str) -> str:
    if not isinstance(value, str):
        raise AIResponseSchemaError(
            f"expected str, got {type(value).__name__} ({value!r})",
            field_path=field_path,
        )
    return value


def _coerce_dict(
    value: Any, *, field_path: str, allow_none: bool = True
) -> Dict[str, Any]:
    if value is None and allow_none:
        return {}
    if not isinstance(value, dict):
        raise AIResponseSchemaError(
            f"expected object, got {type(value).__name__}",
            field_path=field_path,
        )
    return dict(value)


def _coerce_str_list(
    value: Any, *, field_path: str, allow_none: bool = True
) -> List[str]:
    if value is None and allow_none:
        return []
    if not isinstance(value, list):
        raise AIResponseSchemaError(
            f"expected array, got {type(value).__name__}",
            field_path=field_path,
        )
    out: List[str] = []
    for i, item in enumerate(value):
        if not isinstance(item, str):
            raise AIResponseSchemaError(
                f"item {i} expected str, got {type(item).__name__}",
                field_path=f"{field_path}[{i}]",
            )
        out.append(item)
    return out


# ── Recommendation model ────────────────────────────────────────────────────


@dataclass
class AIEnhancedRecommendationModel:
    """Schema-validated AI recommendation. No fabricated defaults."""

    type: str
    primary: bool
    ai_confidence: float
    data_confidence: float
    block_name: Optional[str] = None
    signal_name: Optional[str] = None
    parameter_name: Optional[str] = None
    configuration: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    expected_impact: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(
        cls,
        data: Any,
        *,
        field_path: str = "recommendation",
        known_block_names: Optional[Iterable[str]] = None,
        known_signal_names: Optional[Iterable[str]] = None,
    ) -> "AIEnhancedRecommendationModel":
        if not isinstance(data, dict):
            raise AIResponseSchemaError(
                f"expected object, got {type(data).__name__}",
                field_path=field_path,
            )

        if "type" not in data:
            raise AIResponseSchemaError(
                "missing required field 'type'",
                field_path=f"{field_path}.type",
            )
        rec_type = _coerce_str(data["type"], field_path=f"{field_path}.type")
        if rec_type not in ALLOWED_REC_TYPES:
            raise AIResponseSchemaError(
                f"unknown type {rec_type!r}; allowed: {ALLOWED_REC_TYPES}",
                field_path=f"{field_path}.type",
            )

        if "ai_confidence" not in data:
            raise AIResponseSchemaError(
                "missing required field 'ai_confidence'",
                field_path=f"{field_path}.ai_confidence",
            )
        ai_conf = _ensure_unit_interval(
            data["ai_confidence"], field_path=f"{field_path}.ai_confidence"
        )

        if "data_confidence" not in data:
            raise AIResponseSchemaError(
                "missing required field 'data_confidence'",
                field_path=f"{field_path}.data_confidence",
            )
        data_conf = _ensure_unit_interval(
            data["data_confidence"], field_path=f"{field_path}.data_confidence"
        )

        primary = bool(data.get("primary", False))

        block_name = _coerce_optional_str(
            data.get("block_name"), field_path=f"{field_path}.block_name"
        )
        signal_name = _coerce_optional_str(
            data.get("signal_name"), field_path=f"{field_path}.signal_name"
        )
        parameter_name = _coerce_optional_str(
            data.get("parameter_name"),
            field_path=f"{field_path}.parameter_name",
        )

        if known_block_names is not None and block_name is not None:
            if block_name not in set(known_block_names):
                raise AIResponseSchemaError(
                    f"unknown block_name {block_name!r}",
                    field_path=f"{field_path}.block_name",
                )

        if known_signal_names is not None and signal_name is not None:
            if signal_name not in set(known_signal_names):
                raise AIResponseSchemaError(
                    f"unknown signal_name {signal_name!r}",
                    field_path=f"{field_path}.signal_name",
                )

        configuration = _coerce_dict(
            data.get("configuration"),
            field_path=f"{field_path}.configuration",
            allow_none=True,
        )
        reasoning = data.get("reasoning", "")
        if not isinstance(reasoning, str):
            raise AIResponseSchemaError(
                f"expected str, got {type(reasoning).__name__}",
                field_path=f"{field_path}.reasoning",
            )
        expected_impact = _coerce_dict(
            data.get("expected_impact"),
            field_path=f"{field_path}.expected_impact",
            allow_none=True,
        )
        warnings = _coerce_str_list(
            data.get("warnings"),
            field_path=f"{field_path}.warnings",
            allow_none=True,
        )

        known_keys = {
            "type",
            "primary",
            "block_name",
            "signal_name",
            "parameter_name",
            "configuration",
            "reasoning",
            "expected_impact",
            "ai_confidence",
            "data_confidence",
            "warnings",
        }
        extra_fields = {k: v for k, v in data.items() if k not in known_keys}

        return cls(
            type=rec_type,
            primary=primary,
            ai_confidence=ai_conf,
            data_confidence=data_conf,
            block_name=block_name,
            signal_name=signal_name,
            parameter_name=parameter_name,
            configuration=configuration,
            reasoning=reasoning,
            expected_impact=expected_impact,
            warnings=warnings,
            extra_fields=extra_fields,
        )


# ── Top-level response model ────────────────────────────────────────────────


@dataclass
class AIResponse:
    """Schema-validated AI response. Captures diagnosis + recommendations."""

    recommendations: List[AIEnhancedRecommendationModel]
    assessment: str = ""
    root_cause_analysis: Dict[str, Any] = field(default_factory=dict)
    implementation_order: List[str] = field(default_factory=list)
    extra_fields: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(
        cls,
        data: Any,
        *,
        known_block_names: Optional[Iterable[str]] = None,
        known_signal_names: Optional[Iterable[str]] = None,
    ) -> "AIResponse":
        if not isinstance(data, dict):
            raise AIResponseSchemaError(
                f"expected object, got {type(data).__name__}",
                field_path="<root>",
            )

        assessment = data.get("assessment", "")
        if not isinstance(assessment, str):
            raise AIResponseSchemaError(
                f"expected str, got {type(assessment).__name__}",
                field_path="assessment",
            )

        root_cause_analysis = _coerce_dict(
            data.get("root_cause_analysis"),
            field_path="root_cause_analysis",
            allow_none=True,
        )

        implementation_order = _coerce_str_list(
            data.get("implementation_order"),
            field_path="implementation_order",
            allow_none=True,
        )

        recs_raw = data.get("recommendations", [])
        if not isinstance(recs_raw, list):
            raise AIResponseSchemaError(
                f"expected array, got {type(recs_raw).__name__}",
                field_path="recommendations",
            )
        recommendations: List[AIEnhancedRecommendationModel] = []
        for i, rec in enumerate(recs_raw):
            recommendations.append(
                AIEnhancedRecommendationModel.from_dict(
                    rec,
                    field_path=f"recommendations[{i}]",
                    known_block_names=known_block_names,
                    known_signal_names=known_signal_names,
                )
            )

        extra_fields = {
            k: v
            for k, v in data.items()
            if k not in ALLOWED_DIAGNOSIS_TOP_LEVEL_KEYS
        }

        return cls(
            recommendations=recommendations,
            assessment=assessment,
            root_cause_analysis=root_cause_analysis,
            implementation_order=implementation_order,
            extra_fields=extra_fields,
        )


# ── Convenience: parse the OpenAI-style chat-completion JSON envelope ──────


def parse_chat_completion_envelope(
    response_json: Dict[str, Any],
    *,
    known_block_names: Optional[Iterable[str]] = None,
    known_signal_names: Optional[Iterable[str]] = None,
) -> AIResponse:
    """Extract the assistant message content and parse it as ``AIResponse``.

    Accepts the standard OpenAI/OpenRouter envelope::

        {"choices": [{"message": {"content": "<json string>"}}]}

    Markdown ``\`\`\`json ... \`\`\`` wrappers are tolerated. If the content
    is not valid JSON, raises ``AIResponseSchemaError`` (NOT a generic
    ``json.JSONDecodeError``).
    """
    if not isinstance(response_json, dict):
        raise AIResponseSchemaError(
            f"expected response object, got {type(response_json).__name__}",
            field_path="<envelope>",
        )
    choices = response_json.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIResponseSchemaError(
            "missing 'choices' in response envelope",
            field_path="choices",
        )
    first = choices[0]
    if not isinstance(first, dict):
        raise AIResponseSchemaError(
            "first choice is not an object",
            field_path="choices[0]",
        )
    message = first.get("message")
    if not isinstance(message, dict):
        raise AIResponseSchemaError(
            "missing 'message' in first choice",
            field_path="choices[0].message",
        )
    content = message.get("content")
    if not isinstance(content, str):
        raise AIResponseSchemaError(
            "missing 'content' string in message",
            field_path="choices[0].message.content",
        )

    stripped = content.strip()
    if stripped.startswith("```json"):
        stripped = stripped[len("```json"):].strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
    elif stripped.startswith("```"):
        stripped = stripped[3:].strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()

    try:
        parsed = _json.loads(stripped)
    except _json.JSONDecodeError as exc:
        raise AIResponseSchemaError(
            f"assistant content is not valid JSON: {exc}",
            field_path="choices[0].message.content",
        ) from exc

    return AIResponse.from_dict(
        parsed,
        known_block_names=known_block_names,
        known_signal_names=known_signal_names,
    )
