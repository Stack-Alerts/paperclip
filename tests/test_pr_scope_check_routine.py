"""Unit tests for pr_scope_check_routine — Phase 6b (BTCAAAAA-30054).

Network paths (GitHub + Paperclip APIs) are not exercised here; this locks
the scope-creep detection logic so any regression on the core invariants —
branch identifier extraction and offending-commit filtering — fails CI.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "pr_scope_check_routine.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "pr_scope_check_routine", MODULE_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


MODULE = _load_module()


def _commit(sha: str, subject: str, body: str = "") -> dict:
    message = subject if not body else f"{subject}\n\n{body}"
    return {"sha": sha, "commit": {"message": message}}


def test_branch_identifier_extracts_first_id():
    assert MODULE.branch_identifier("feat/BTCAAAAA-30054-pr-scope-detector") == (
        "BTCAAAAA-30054"
    )


def test_branch_identifier_returns_none_for_main():
    assert MODULE.branch_identifier("main") is None


def test_branch_identifier_returns_none_for_empty():
    assert MODULE.branch_identifier("") is None


def test_offending_commits_clean_list_returns_empty():
    commits = [
        _commit("a" * 40, "feat(BTCAAAAA-30054): add lint script"),
        _commit("b" * 40, "chore(BTCAAAAA-30054): wire pre-push hook"),
    ]
    assert MODULE.offending_commits("BTCAAAAA-30054", commits) == []


def test_offending_commits_flags_foreign_identifier():
    commits = [
        _commit("a" * 40, "feat(BTCAAAAA-30054): add lint script"),
        _commit("b" * 40, "feat(BTCAAAAA-30034): add token-gap escalation routine"),
    ]
    offenders = MODULE.offending_commits("BTCAAAAA-30054", commits)
    assert len(offenders) == 1
    assert offenders[0]["sha"] == "b" * 40
    assert offenders[0]["foreign"] == ["BTCAAAAA-30034"]


def test_offending_commits_ignores_unidentified_subject():
    """Commits with no BTCAAAAA-NNN reference are out of scope here.

    A missing identifier is a closure-gate concern (Phase 3, BTCAAAAA-30040);
    this routine only fires on demonstrably wrong identifiers so the two
    gates remain non-overlapping.
    """
    commits = [
        _commit("a" * 40, "feat(BTCAAAAA-30054): add lint script"),
        _commit("b" * 40, "feat: Add token-gap escalation routine"),
    ]
    assert MODULE.offending_commits("BTCAAAAA-30054", commits) == []


def test_offending_commits_dedupes_foreign_ids_per_commit():
    commits = [
        _commit(
            "a" * 40,
            "merge(BTCAAAAA-30034, BTCAAAAA-30034): noisy duplicate",
        ),
    ]
    offenders = MODULE.offending_commits("BTCAAAAA-30054", commits)
    assert offenders == [
        {
            "sha": "a" * 40,
            "subject": "merge(BTCAAAAA-30034, BTCAAAAA-30034): noisy duplicate",
            "foreign": ["BTCAAAAA-30034"],
        }
    ]


def test_offending_commits_only_inspects_subject_not_body():
    """Refs: trailers in the commit body are intentional cross-references."""
    commits = [
        _commit(
            "a" * 40,
            "feat(BTCAAAAA-30054): add lint script",
            "Refs: BTCAAAAA-30038\nRefs: BTCAAAAA-30046",
        ),
    ]
    assert MODULE.offending_commits("BTCAAAAA-30054", commits) == []


def test_offending_commits_multiple_foreign_ids_in_one_subject():
    commits = [
        _commit(
            "a" * 40,
            "merge(BTCAAAAA-30030, BTCAAAAA-30028): combined hover fix",
        ),
    ]
    offenders = MODULE.offending_commits("BTCAAAAA-30054", commits)
    assert offenders == [
        {
            "sha": "a" * 40,
            "subject": "merge(BTCAAAAA-30030, BTCAAAAA-30028): combined hover fix",
            "foreign": ["BTCAAAAA-30028", "BTCAAAAA-30030"],
        }
    ]


if __name__ == "__main__":
    import traceback

    funcs = [v for k, v in globals().items() if k.startswith("test_")]
    failed = 0
    for fn in funcs:
        try:
            fn()
            print(f"ok    {fn.__name__}")
        except AssertionError:
            failed += 1
            print(f"FAIL  {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(funcs)-failed}/{len(funcs)} passed")
    sys.exit(1 if failed else 0)
