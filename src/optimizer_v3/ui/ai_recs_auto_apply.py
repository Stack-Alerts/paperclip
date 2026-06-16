"""
AI Recommendations — One-Click Auto-Apply Orchestrator
Sprint 1.9.4 (child of BTCAAAAA-260, sibling of S1/S2/S3)

Owns the "Apply All" workflow that the persistent results panel (S2)
triggers from a single button. Lifecycle:

  1. backup_strategy (AutoFixSafety)            — snapshot for rollback
  2. dry_run(recs, opt_in_destructive_ids)      — classify + opt-in filter
  3. for each SAFE / opted-in DESTRUCTIVE rec:
        a. dispatch to Sprint 1.9.2 algorithm    — mutate config
        b. verify_fix_result (InstitutionalValidator) — no new blockers
        c. on verify failure → rollback_if_needed + return
        d. mark_applied (AIRecommendationsManager) — audit trail
        e. emit progress(percent, stage_label)   — S1 modal hook

Design contract (per ADR-0006):
  - SAFE:    maps to a Sprint 1.9.2 algorithm (auto_fix_strategy_type /
             auto_fix_recheck_delay / auto_fix_duplicate_exits /
             auto_fix_dead_code). Auto-applied, no user opt-in needed.
  - DESTRUCTIVE: no 1.9.2 algorithm (Sprint 1.9.3 deferred). User MUST
                 opt-in by id. Without opt-in: skipped, not failed.
  - UNSUPPORTED: unknown rec type. Skipped, not failed.

The orchestrator is Qt-free: it takes a `_ProgressCallback(percent,
stage_label)` Protocol that mirrors S1's `update_send_progress` public
API, so the S2 panel can wire S1's progress modal without coupling S4
to PyQt.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol

from src.strategy_builder.validation.auto_fix import (
    AutoFixSafety,
    auto_fix_strategy_type,
    auto_fix_recheck_delay,
    auto_fix_duplicate_exits,
    auto_fix_dead_code,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dispatcher signals
# ---------------------------------------------------------------------------

class SilentNoOp(Exception):
    """Raised by `_apply_one` when the rec is a silent no-op.

    Distinct from a real failure: a "block not found" or "signal not
    found" rec reflects the *current state* of the strategy (the target
    may have been renamed or removed by a prior fix), not a bug in the
    rec. The caller should route the rec to `skipped[]`, not `failed[]`,
    so the S2 results panel can present it as informational rather than
    alarming.

    A `False` return from `_apply_one`, by contrast, signals a *real*
    failure (the rec was malformed, the algo raised, the destructive
    path has no 1.9.3 implementation yet, etc.) and goes to `failed[]`.
    """
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


# ---------------------------------------------------------------------------
# Rec-type taxonomy
# ---------------------------------------------------------------------------
# These constants are the public rec-type strings emitted by the
# IntelligentRecommendationEngine. The S4 orchestrator uses the same
# strings so it can stay decoupled from the engine's internals.
FIX_STRATEGY_TYPE = "FIX_STRATEGY_TYPE"
REDUCE_RECHECK_DELAY = "REDUCE_RECHECK_DELAY"
CONSOLIDATE_DUPLICATE_EXITS = "CONSOLIDATE_DUPLICATE_EXITS"
REMOVE_DEAD_CODE = "REMOVE_DEAD_CODE"

# Destructive (no Sprint 1.9.2 algo; opt-in required once Sprint 1.9.3 lands)
ADD_SIGNAL = "ADD_SIGNAL"
CONFIGURE_SIGNAL = "CONFIGURE_SIGNAL"
REMOVE_SIGNAL = "REMOVE_SIGNAL"
ADD_BLOCK = "ADD_BLOCK"
REMOVE_BLOCK = "REMOVE_BLOCK"
ADJUST_PARAM = "ADJUST_PARAM"
ADD_RECHECK = "ADD_RECHECK"
ADD_TIMING = "ADD_TIMING"

_SAFE_REC_TYPES = frozenset({
    FIX_STRATEGY_TYPE,
    REDUCE_RECHECK_DELAY,
    CONSOLIDATE_DUPLICATE_EXITS,
    REMOVE_DEAD_CODE,
})

_DESTRUCTIVE_REC_TYPES = frozenset({
    ADD_SIGNAL, CONFIGURE_SIGNAL, REMOVE_SIGNAL,
    ADD_BLOCK, REMOVE_BLOCK, ADJUST_PARAM,
    ADD_RECHECK, ADD_TIMING,
})


class ApplyClassification(str, Enum):
    """How a rec is classified for the apply lifecycle."""
    SAFE = "safe"              # Sprint 1.9.2 algo available; auto-apply
    DESTRUCTIVE = "destructive"  # No 1.9.2 algo; user opt-in required
    UNSUPPORTED = "unsupported"  # Unknown rec type; skip


def classify(rec: Any) -> ApplyClassification:
    """Pure function: classify a rec for the apply lifecycle.

    Accepts either a dict (raw rec shape from DB) or an object with a
    `.type` attribute (the IntegratedRecommendation Pydantic-like model
    used in tests). Always returns an ApplyClassification enum member.
    """
    rec_type = _coerce_rec(rec).get("type")
    if rec_type in _SAFE_REC_TYPES:
        return ApplyClassification.SAFE
    if rec_type in _DESTRUCTIVE_REC_TYPES:
        return ApplyClassification.DESTRUCTIVE
    return ApplyClassification.UNSUPPORTED


def _coerce_rec(rec: Any) -> Dict[str, Any]:
    """Return a dict view of a rec whether it is dict-shaped or object-shaped."""
    if isinstance(rec, dict):
        return rec
    if hasattr(rec, "__dict__"):
        return {k: v for k, v in rec.__dict__.items() if not k.startswith("_")}
    return {}


def _build_target_label(rec: Any) -> str:
    """Human-readable target string for the confirmation modal.

    E.g. "block=hod", "signal=HOD_REJECTION@hod", "param=stop_loss_pct",
    or "rec" if nothing specific is available.
    """
    r = _coerce_rec(rec)
    block = r.get("block_name")
    signal = r.get("signal_name")
    param = r.get("parameter_name")
    if block and signal:
        return f"signal={signal}@block={block}"
    if block:
        return f"block={block}"
    if param:
        return f"param={param}"
    return "rec"


def _destructive_reason(rec_type: str) -> str:
    """Plain-language reason a rec is classified as destructive."""
    if rec_type in (ADD_BLOCK, REMOVE_BLOCK):
        return "Adds or removes a strategy block; cannot be undone without snapshot."
    if rec_type in (ADD_SIGNAL, REMOVE_SIGNAL):
        return "Adds or removes a signal; cannot be undone without snapshot."
    if rec_type == CONFIGURE_SIGNAL:
        return "Rewrites a signal's parameters; cannot be undone without snapshot."
    if rec_type == ADJUST_PARAM:
        return "Changes a top-level strategy parameter; cannot be undone without snapshot."
    if rec_type in (ADD_RECHECK, ADD_TIMING):
        return "Attaches a recheck/timing sub-config; cannot be undone without snapshot."
    return "Mutates strategy state; cannot be undone without snapshot."


# ---------------------------------------------------------------------------
# Result shapes
# ---------------------------------------------------------------------------

@dataclass
class DryRunEntry:
    """One rec's classification, for the confirmation modal."""
    rec_id: Optional[str]
    rec_type: str
    classification: ApplyClassification
    target: str
    reasoning: str
    requires_opt_in: bool
    destructive_reason: Optional[str] = None


@dataclass
class DryRunResult:
    """Outcome of dry_run(). Feeds the confirmation modal."""
    entries: List[DryRunEntry] = field(default_factory=list)
    safe_count: int = 0
    destructive_count: int = 0
    unsupported_count: int = 0

    @property
    def requires_any_opt_in(self) -> bool:
        return self.destructive_count > 0

    def to_payload(self) -> Dict[str, Any]:
        return {
            "entries": [
                {
                    "rec_id": e.rec_id,
                    "rec_type": e.rec_type,
                    "classification": e.classification.value,
                    "target": e.target,
                    "reasoning": e.reasoning,
                    "requires_opt_in": e.requires_opt_in,
                    "destructive_reason": e.destructive_reason,
                }
                for e in self.entries
            ],
            "safe_count": self.safe_count,
            "destructive_count": self.destructive_count,
            "unsupported_count": self.unsupported_count,
            "requires_any_opt_in": self.requires_any_opt_in,
        }


@dataclass
class AppliedEntry:
    """One rec's apply outcome."""
    rec_id: Optional[str]
    rec_type: str
    success: bool
    message: str


@dataclass
class ApplyResult:
    """Outcome of run_apply_all(). Feeds the post-apply results panel refresh."""
    applied: List[AppliedEntry] = field(default_factory=list)
    skipped: List[AppliedEntry] = field(default_factory=list)
    failed: List[AppliedEntry] = field(default_factory=list)
    rolled_back: bool = False

    @property
    def applied_count(self) -> int:
        return len(self.applied)

    @property
    def failed_count(self) -> int:
        return len(self.failed)

    def to_payload(self) -> Dict[str, Any]:
        return {
            "applied": [e.__dict__ for e in self.applied],
            "skipped": [e.__dict__ for e in self.skipped],
            "failed": [e.__dict__ for e in self.failed],
            "rolled_back": self.rolled_back,
            "applied_count": self.applied_count,
            "failed_count": self.failed_count,
        }


# ---------------------------------------------------------------------------
# Protocol boundaries (Qt-free; testable with stubs)
# ---------------------------------------------------------------------------

class _ProgressCallback(Protocol):
    """Mirrors S1's `update_send_progress(percent, stage_label)` public API.

    The S2 panel can wire this straight to S1's `QProgressDialog` once
    both modules land. Pure-Python callers (tests, headless runs) can
    pass any callable that accepts (percent: int, stage_label: str).
    """
    def __call__(self, percent: int, stage_label: str) -> None: ...


class _RecommendationsManagerLike(Protocol):
    """Subset of AIRecommendationsManager the orchestrator depends on.

    Defined as a Protocol so tests can pass a fake manager without
    importing SQLAlchemy. The real implementation lives in
    src/optimizer_v3/database/ai_recommendations_manager.py.
    """
    def mark_applied(
        self,
        recommendation_id: str,
        applied_version_id: str,
        applied_by: Optional[str] = None,
    ) -> bool: ...


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class AutoApplyOrchestrator:
    """Drives the Apply All lifecycle for a batch of AI recommendations.

    Lifecycle (run_apply_all):
        1. backup_strategy → snapshot for rollback
        2. for each rec (in input order):
             a. classify; UNSUPPORTED → skipped
             b. DESTRUCTIVE without opt-in → skipped
             c. dispatch to Sprint 1.9.2 algo (SAFE) or future algo (DESTRUCTIVE)
             d. verify_fix_result; on blocker > 0 → rollback + return
             e. mark_applied via manager (audit trail)
             f. emit progress(percent, stage_label)
        3. on any per-rec exception → capture in failed[], continue

    Threading: not thread-safe. The S2 panel must call run_apply_all from
    the Qt main thread (or marshal it back). The progress callback is
    invoked synchronously; S1's QProgressDialog is already main-thread.
    """

    def __init__(
        self,
        manager: Optional[_RecommendationsManagerLike] = None,
        safety: Optional[AutoFixSafety] = None,
        progress_cb: Optional[_ProgressCallback] = None,
        applied_by: str = "ai_recs_auto_apply",
    ) -> None:
        self._manager = manager
        self._safety = safety or AutoFixSafety()
        self._progress_cb = progress_cb
        self._applied_by = applied_by

    def set_progress_callback(self, cb: _ProgressCallback) -> None:
        """Allow the S2 panel to wire the S1 progress modal after construction."""
        self._progress_cb = cb

    def _emit(self, percent: int, stage_label: str) -> None:
        if self._progress_cb is not None:
            try:
                self._progress_cb(percent, stage_label)
            except Exception as exc:  # noqa: BLE001
                # A broken progress UI must not break the apply lifecycle.
                logger.warning("progress callback raised: %s", exc)

    # ------------------------------------------------------------------ dry_run

    def dry_run(
        self,
        recs: List[Any],
        opt_in_destructive_ids: Optional[List[str]] = None,
    ) -> DryRunResult:
        """Classify every rec and flag which ones need user opt-in.

        Does NOT mutate strategy state. Pure read of `recs` shape.
        `opt_in_destructive_ids` is accepted here so the modal can preview
        "if you opt in to these, X will be applied" without running
        the apply.
        """
        opted_in = set(opt_in_destructive_ids or [])
        result = DryRunResult()

        for rec in recs:
            r = _coerce_rec(rec)
            rec_id = r.get("recommendation_id") or r.get("rec_id") or r.get("id")
            rec_type = r.get("type", "<missing>")
            classification = classify(rec)

            entry = DryRunEntry(
                rec_id=str(rec_id) if rec_id is not None else None,
                rec_type=rec_type,
                classification=classification,
                target=_build_target_label(rec),
                reasoning=str(r.get("reasoning") or r.get("rationale") or ""),
                requires_opt_in=(classification is ApplyClassification.DESTRUCTIVE),
                destructive_reason=(
                    _destructive_reason(rec_type)
                    if classification is ApplyClassification.DESTRUCTIVE
                    else None
                ),
            )
            result.entries.append(entry)

            if classification is ApplyClassification.SAFE:
                result.safe_count += 1
            elif classification is ApplyClassification.DESTRUCTIVE:
                if rec_id is not None and str(rec_id) in opted_in:
                    # Destructive but opted-in: still counted as destructive
                    # so the modal can show "you opted in to N destructive".
                    pass
                result.destructive_count += 1
            else:
                result.unsupported_count += 1

        return result

    # ------------------------------------------------------------- run_apply_all

    def run_apply_all(
        self,
        recs: List[Any],
        strategy_config: Any,
        opt_in_destructive_ids: Optional[List[str]] = None,
    ) -> ApplyResult:
        """Apply a batch of recs with backup + verify + rollback guarantees.

        The single rollback boundary covers the whole batch: if any rec
        introduces a new blocking issue, the entire batch is rolled back
        to the pre-batch snapshot and ApplyResult.rolled_back = True.
        """
        result = ApplyResult()
        opted_in = set(opt_in_destructive_ids or [])

        if not recs:
            self._emit(100, "Nothing to apply")
            return result

        # 1. Snapshot for rollback
        self._safety.backup_strategy(strategy_config)
        self._emit(2, "Snapshot saved")

        # 2. Pre-classify for the progress range
        applicable: List[tuple[int, Any]] = []
        for idx, rec in enumerate(recs):
            cls = classify(rec)
            r = _coerce_rec(rec)
            rec_id = r.get("recommendation_id") or r.get("rec_id") or r.get("id")
            rec_id_str = str(rec_id) if rec_id is not None else None

            if cls is ApplyClassification.UNSUPPORTED:
                result.skipped.append(AppliedEntry(
                    rec_id=rec_id_str,
                    rec_type=r.get("type", "<missing>"),
                    success=False,
                    message="unsupported rec type; skipped",
                ))
                continue

            if cls is ApplyClassification.DESTRUCTIVE and rec_id_str not in opted_in:
                result.skipped.append(AppliedEntry(
                    rec_id=rec_id_str,
                    rec_type=r.get("type", "<missing>"),
                    success=False,
                    message="destructive rec; user did not opt in",
                ))
                continue

            applicable.append((idx, rec))

        if not applicable:
            self._emit(100, "Nothing applicable to apply")
            return result

        # 3. Apply each applicable rec
        total = len(applicable)
        for step, (orig_idx, rec) in enumerate(applicable, start=1):
            r = _coerce_rec(rec)
            rec_id = r.get("recommendation_id") or r.get("rec_id") or r.get("id")
            rec_id_str = str(rec_id) if rec_id is not None else None
            rec_type = r.get("type", "<missing>")

            # Reserve 5%..95% for the apply loop; 0%..5% for backup, 95%..100% for verify
            percent = int(5 + (step - 1) * (90 / total))
            self._emit(percent, f"Applying {rec_type} ({step}/{total})")

            try:
                ok = self._apply_one(rec, strategy_config)
            except SilentNoOp as nop:
                # Silent no-op (e.g. target block/signal not present in the
                # current strategy config). Not a failure -- the strategy
                # is in an unexpected state for this rec, not the rec
                # itself being broken. Route to skipped[] so the S2
                # results panel can render it as informational.
                result.skipped.append(AppliedEntry(
                    rec_id=rec_id_str,
                    rec_type=rec_type,
                    success=False,
                    message=nop.message,
                ))
                continue
            except Exception as exc:  # noqa: BLE001
                logger.exception("apply raised for rec %s", rec_id_str)
                result.failed.append(AppliedEntry(
                    rec_id=rec_id_str,
                    rec_type=rec_type,
                    success=False,
                    message=f"exception: {exc}",
                ))
                # Per spec, capture in failed, do NOT crash the batch
                continue

            if not ok:
                result.failed.append(AppliedEntry(
                    rec_id=rec_id_str,
                    rec_type=rec_type,
                    success=False,
                    message="apply returned False",
                ))
                # A non-ok apply could be a silent no-op or a partial fix;
                # continue applying the rest. The verify step below is the
                # real gate that triggers a rollback.
                continue

            # 4. Verify after each fix (per AutoFixSafety contract)
            if not self._safety.verify_fix_result(strategy_config):
                logger.error(
                    "fix verification failed after %s — rolling back entire batch",
                    rec_type,
                )
                self._safety.rollback_if_needed(strategy_config)
                result.rolled_back = True
                # The system state is back to pre-batch: nothing in
                # `applied[]` is actually applied anymore. Clear it so
                # the S2 panel can render the rollback honestly (and
                # applied_count reads 0, matching the snapshot state).
                result.applied.clear()
                # Mark all already-applied + remaining as failed
                result.failed.append(AppliedEntry(
                    rec_id=rec_id_str,
                    rec_type=rec_type,
                    success=False,
                    message="verify_fix_result failed; batch rolled back",
                ))
                self._emit(100, "Rolled back")
                return result

            # 5. Mark applied (audit trail)
            if self._manager is not None and rec_id_str is not None:
                try:
                    audit_ok = self._manager.mark_applied(
                        recommendation_id=rec_id_str,
                        applied_version_id=str(
                            getattr(strategy_config, "version_id", "") or ""
                        ),
                        applied_by=self._applied_by,
                    )
                except Exception as exc:  # noqa: BLE001
                    # Audit failure must not roll back an already-applied fix.
                    logger.warning("mark_applied raised for %s: %s", rec_id_str, exc)
                    result.failed.append(AppliedEntry(
                        rec_id=rec_id_str,
                        rec_type=rec_type,
                        success=False,
                        message=f"apply succeeded but mark_applied raised: {exc}",
                    ))
                    continue
                if not audit_ok:
                    # Manager refused the audit write (e.g. constraint
                    # violation). The fix is still in effect; surface
                    # the audit failure to the S2 panel and continue.
                    logger.warning("mark_applied returned False for %s", rec_id_str)
                    result.failed.append(AppliedEntry(
                        rec_id=rec_id_str,
                        rec_type=rec_type,
                        success=False,
                        message="apply succeeded but mark_applied failed",
                    ))
                    continue

            result.applied.append(AppliedEntry(
                rec_id=rec_id_str,
                rec_type=rec_type,
                success=True,
                message="applied",
            ))

        self._emit(100, "Apply complete")
        return result

    # --------------------------------------------------------- _apply_one dispatch

    def _apply_one(self, rec: Any, strategy_config: Any) -> bool:
        """Dispatch a single rec to its Sprint 1.9.2 algorithm.

        Returns True on successful apply, False on silent no-op. Raises
        on programmer error (unknown rec type, missing required field),
        which the run_apply_all loop catches and records in failed[].
        """
        r = _coerce_rec(rec)
        rec_type = r.get("type")

        if rec_type == FIX_STRATEGY_TYPE:
            suggested = r.get("suggested_value") or r.get("configuration", {}).get("strategy_type")
            if not suggested:
                logger.warning("FIX_STRATEGY_TYPE missing suggested_value; no-op")
                return False
            return auto_fix_strategy_type(strategy_config, str(suggested))

        if rec_type == REDUCE_RECHECK_DELAY:
            window = (
                r.get("timing_window")
                or r.get("configuration", {}).get("timing_window")
            )
            block_name = r.get("block_name")
            signal_name = r.get("signal_name")
            if not (window and block_name and signal_name and hasattr(strategy_config, "blocks")):
                logger.warning("REDUCE_RECHECK_DELAY missing fields; no-op")
                return False
            block = next((b for b in strategy_config.blocks if b.name == block_name), None)
            if block is None:
                logger.warning("REDUCE_RECHECK_DELAY block=%s not found; no-op", block_name)
                raise SilentNoOp(
                    f"REDUCE_RECHECK_DELAY block={block_name} not found; skipped"
                )
            signal = next((s for s in getattr(block, "signals", []) if s.name == signal_name), None)
            if signal is None or not hasattr(signal, "recheck_config"):
                logger.warning("REDUCE_RECHECK_DELAY signal=%s not found; no-op", signal_name)
                raise SilentNoOp(
                    f"REDUCE_RECHECK_DELAY signal={signal_name} not found; skipped"
                )
            return auto_fix_recheck_delay(signal.recheck_config, int(window))

        if rec_type == CONSOLIDATE_DUPLICATE_EXITS:
            signal_name = r.get("signal_name")
            if not (signal_name and hasattr(strategy_config, "exit_conditions")):
                logger.warning("CONSOLIDATE_DUPLICATE_EXITS missing fields; no-op")
                return False
            new_conditions = auto_fix_duplicate_exits(
                strategy_config.exit_conditions, str(signal_name)
            )
            strategy_config.exit_conditions = new_conditions
            return True

        if rec_type == REMOVE_DEAD_CODE:
            block_name = r.get("block_name")
            dead = r.get("dead_signal_names") or r.get("configuration", {}).get("dead_signal_names")
            if not (block_name and dead and hasattr(strategy_config, "blocks")):
                logger.warning("REMOVE_DEAD_CODE missing fields; no-op")
                return False
            block = next((b for b in strategy_config.blocks if b.name == block_name), None)
            if block is None:
                logger.warning("REMOVE_DEAD_CODE block=%s not found; no-op", block_name)
                raise SilentNoOp(
                    f"REMOVE_DEAD_CODE block={block_name} not found; skipped"
                )
            return auto_fix_dead_code(block, list(dead))

        # Destructive recs (Sprint 1.9.3 territory) — not yet implemented.
        # Caller should have gated these on opt-in; reaching here means
        # the dispatcher doesn't know how to apply this type yet.
        if rec_type in _DESTRUCTIVE_REC_TYPES:
            logger.warning(
                "destructive rec type %s reached dispatcher; Sprint 1.9.3 algo not yet implemented",
                rec_type,
            )
            return False

        raise ValueError(f"unknown rec type: {rec_type!r}")
