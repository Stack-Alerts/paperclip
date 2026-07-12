#!/usr/bin/env python3
"""Closure-gate smoke runner (BTCAAAAA-37739).

Imports `src.api.app` to catch import-time breakage, then hits a configured
canary endpoint list in-process via FastAPI's TestClient against an ephemeral
DB. Any response outside the per-endpoint `allow_status` list (especially any
5xx) is treated as smoke failure.

Two modes:
    python scripts/closure_gate_smoke.py
        Smoke the current working tree, write JSON verdict to stdout.

    python scripts/closure_gate_smoke.py --at-sha <SHA>
        Smoke `origin/main` HEAD (NOT <SHA>) in a temporary worktree, then emit
        the JSON verdict. Used by the closure-gate routine before flipping an
        issue to `done`. <SHA> is the historical Fix-SHA — it is recorded as
        `requested_fix_sha` for traceability but is NOT the code that gets
        smoked. The gate's job is to confirm the *current* tree is healthy;
        re-running the runner as it existed at an old Fix-SHA reintroduced
        stale bugs and caused false reopens (BTCAAAAA-38997 — see `_run_at_sha`).
        `--fresh-venv` installs requirements.txt at origin/main HEAD first.

Exit codes:
    0  all endpoints inside allow_status (smoke PASS)
    1  one or more endpoints outside allow_status (smoke FAIL)
    2  import-time / harness failure (treated as FAIL by the routine)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SMOKE_ENDPOINTS_PATH = REPO_ROOT / "scripts" / "closure_gate_smoke_endpoints.json"


def _load_endpoints(path: Path) -> dict[str, Any]:
    with path.open("r") as fh:
        return json.load(fh)


def _endpoint_ok(status_code: int, allow: set[int]) -> bool:
    """Return True iff the response status is in the per-endpoint allow list.

    The allow list is authoritative. A 5xx that is *deliberately* allow-listed
    (e.g. 503 dependency-not-ready on the strategy canaries — a tolerated
    transient) passes; any status not in the allow list, including an
    un-allow-listed 5xx crash, fails. (BTCAAAAA-38714: a prior
    `in_allow and not is_5xx` guard overrode the allow list and turned tolerated
    503s into false closure-gate reopens.)

    Note (BTCAAAAA-38997): fixing this classifier is necessary but not
    sufficient. When the gate re-ran the runner *as it existed at a historical
    Fix-SHA*, it resurrected the pre-38714 version of this function and produced
    false `closure-gate-smoke-failed` reopens on old, long-merged issues. The
    `--at-sha` path (`_run_at_sha`) now smokes `origin/main` HEAD so the current
    classifier — this one — is always the code that runs.
    """
    return status_code in allow


def _stub_auth(app: Any) -> None:
    """Bypass JWT auth for the in-process TestClient.

    All REST endpoints in src.api.app depend on `require_jwt`. We override it
    with a stub that returns a minimal claim dict so smoke calls never hit a
    401 (which would mask the 5xx we actually want to detect).
    """
    from src.api.auth import require_jwt

    async def _allow() -> dict[str, Any]:
        return {"sub": "closure-gate-smoke", "scope": "smoke"}

    app.dependency_overrides[require_jwt] = _allow


def _smoke_in_process(endpoints_doc: dict[str, Any]) -> dict[str, Any]:
    """Import src.api.app and hit each endpoint via TestClient.

    Returns a verdict dict; never raises — import errors become a synthetic
    `import_error` result so the routine can attribute the failure.
    """
    seed = endpoints_doc.get("seed_strategy_id", "closure-gate-smoke-seed")
    endpoints = endpoints_doc.get("endpoints", [])

    # Ephemeral DB scaffolding: point any DB-aware module at a temp dir so we
    # don't touch the operator's real Paperclip / strategy DB.
    tmp_data = Path(tempfile.mkdtemp(prefix="closure_gate_smoke_"))
    os.environ.setdefault("BTE_DATA_DIR", str(tmp_data))
    os.environ.setdefault("BTE_STRATEGY_DB_PATH", str(tmp_data / "smoke.sqlite"))
    os.environ.setdefault("BTE_DISABLE_REDIS", "1")

    verdict: dict[str, Any] = {
        "schema": "closure_gate_smoke.v1",
        "ok": False,
        "import_ok": False,
        "results": [],
    }

    # Insert repo root + src/ on sys.path so `src.api.app` resolves whether or
    # not the caller exported PYTHONPATH (CI does; ad-hoc local runs may not).
    for entry in (str(REPO_ROOT), str(REPO_ROOT / "src")):
        if entry not in sys.path:
            sys.path.insert(0, entry)

    try:
        from fastapi.testclient import TestClient
        from src.api import app as app_module
    except Exception as exc:  # noqa: BLE001 — import failure is the signal
        verdict["import_error"] = f"{type(exc).__name__}: {exc}"
        return verdict

    verdict["import_ok"] = True
    app = app_module.app

    try:
        _stub_auth(app)
    except Exception as exc:  # noqa: BLE001
        verdict["import_error"] = f"auth-stub: {type(exc).__name__}: {exc}"
        return verdict

    overall_ok = True
    with TestClient(app, raise_server_exceptions=False) as client:
        for ep in endpoints:
            name = ep.get("name", ep.get("path", "?"))
            method = (ep.get("method") or "GET").upper()
            path = (ep.get("path") or "").replace("{seed}", seed)
            body = ep.get("body")
            allow = set(ep.get("allow_status") or [200])

            try:
                resp = client.request(method, path, json=body)
                status_code = resp.status_code
                in_allow = status_code in allow
                is_5xx = 500 <= status_code < 600
                ok = _endpoint_ok(status_code, allow)
                snippet = ""
                try:
                    snippet = resp.text[:300]
                except Exception:
                    snippet = ""
                verdict["results"].append({
                    "name": name,
                    "method": method,
                    "path": path,
                    "status": status_code,
                    "ok": ok,
                    "in_allow_list": in_allow,
                    "is_5xx": is_5xx,
                    "snippet": snippet,
                })
                if not ok:
                    overall_ok = False
            except Exception as exc:  # noqa: BLE001 — request-level crash counts as fail
                verdict["results"].append({
                    "name": name,
                    "method": method,
                    "path": path,
                    "status": None,
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                })
                overall_ok = False

    verdict["ok"] = overall_ok
    return verdict


def _resolve_origin_main_sha() -> str | None:
    """Return the concrete `origin/main` HEAD SHA, or None if unresolvable.

    Validates the output is exactly 40 lowercase hex chars so a corrupt or
    empty stdout never leaks into the worktree checkout or the verdict.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:  # noqa: BLE001 — treated as unresolvable
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    if len(sha) == 40 and all(c in "0123456789abcdef" for c in sha):
        return sha
    return None


def _run_at_sha(requested_fix_sha: str, fresh_venv: bool) -> dict[str, Any]:
    """Smoke `origin/main` HEAD; `requested_fix_sha` is kept only for traceability.

    BTCAAAAA-38997: this function used to create a worktree AT `requested_fix_sha`
    and run the smoke runner *as it existed at that SHA*. When an issue's Fix-SHA
    merged before a later runner/allow-list fix, the gate ran the stale runner and
    produced false `closure-gate-smoke-failed` reopens. Concrete incident: BTC-38578
    looped in_review⇄reopen for ~12h because its 2026-06-27 Fix-SHA (07f6a87f…)
    predated the BTCAAAAA-38714 allow-listed-503 fix (ab122afe…); the pre-38714
    runner treated tolerated 503 canaries as failures even though origin/main tip
    passed cleanly.

    The gate's purpose is to confirm the *current* tree is healthy before closing,
    so we now smoke `origin/main` HEAD. Ancestry of `requested_fix_sha` is verified
    separately by the routine (`verify_sha_on_main`); this runner no longer executes
    historical test code. `at_sha` in the verdict is the SHA actually smoked
    (origin/main HEAD); the historical Fix-SHA is echoed as `requested_fix_sha`.

    The worktree is removed before returning. When `fresh_venv` is true we
    install requirements.txt into a throwaway venv first (slow — only used
    when the operator explicitly asks for it). The default re-uses the
    current interpreter, which is the typical CI configuration.
    """
    head_sha = _resolve_origin_main_sha()
    if head_sha is None:
        # origin/main unresolvable (missing remote-tracking ref, git failure).
        # Smoke the current in-process tree as the best available proxy for
        # "current" rather than resurrecting the stale historical SHA.
        verdict: dict[str, Any] = {
            "schema": "closure_gate_smoke.v1",
            "requested_fix_sha": requested_fix_sha,
            "smoked_ref": "working-tree",
            "at_sha": None,
            "origin_main_unresolved": True,
            "ok": False,
        }
        verdict.update(_smoke_in_process(_load_endpoints(SMOKE_ENDPOINTS_PATH)))
        return verdict

    sha = head_sha
    work_root = Path(tempfile.mkdtemp(prefix=f"closure_gate_sha_{sha[:8]}_"))
    work_tree = work_root / "tree"
    verdict = {
        "schema": "closure_gate_smoke.v1",
        "at_sha": sha,
        "requested_fix_sha": requested_fix_sha,
        "smoked_ref": "origin/main",
        "ok": False,
    }
    try:
        result = subprocess.run(
            ["git", "worktree", "add", "--detach", str(work_tree), sha],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            verdict["error"] = f"git worktree add failed: {result.stderr.strip()}"
            return verdict

        env = {**os.environ, "PYTHONPATH": f"{work_tree}{os.pathsep}{work_tree / 'src'}"}
        python_exe = sys.executable

        if fresh_venv:
            venv_dir = work_root / "venv"
            subprocess.run([python_exe, "-m", "venv", str(venv_dir)], check=False, timeout=60)
            python_exe = str(venv_dir / "bin" / "python")
            req = work_tree / "requirements.txt"
            if req.exists():
                subprocess.run(
                    [python_exe, "-m", "pip", "install", "-q", "-r", str(req)],
                    check=False,
                    timeout=600,
                )

        # Run the smoke from inside the origin/main HEAD worktree so the runner,
        # endpoint config, and app code are all the *current* tree (BTCAAAAA-38997).
        smoke_script = work_tree / "scripts" / "closure_gate_smoke.py"
        if not smoke_script.exists():
            smoke_script = Path(__file__).resolve()

        sub = subprocess.run(
            [python_exe, str(smoke_script), "--in-process-only"],
            cwd=work_tree,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        try:
            inner = json.loads(sub.stdout) if sub.stdout.strip() else {}
        except json.JSONDecodeError:
            inner = {}
        verdict.update(inner)
        verdict.setdefault("ok", sub.returncode == 0)
        if sub.returncode not in (0, 1):
            verdict["harness_stderr"] = sub.stderr[-500:]
    finally:
        try:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(work_tree)],
                cwd=REPO_ROOT,
                capture_output=True,
                timeout=60,
            )
        except Exception:
            pass
        try:
            shutil.rmtree(work_root, ignore_errors=True)
        except Exception:
            pass
    return verdict


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Closure-gate smoke runner")
    parser.add_argument("--at-sha", help="Smoke a specific commit SHA via a temp worktree")
    parser.add_argument("--fresh-venv", action="store_true", help="Create a venv from requirements.txt at the SHA")
    parser.add_argument(
        "--in-process-only",
        action="store_true",
        help="Skip the worktree branch even if --at-sha is set (used by recursion).",
    )
    parser.add_argument(
        "--endpoints",
        default=str(SMOKE_ENDPOINTS_PATH),
        help="Path to closure_gate_smoke_endpoints.json",
    )
    args = parser.parse_args(argv)

    if args.at_sha and not args.in_process_only:
        verdict = _run_at_sha(args.at_sha, fresh_venv=args.fresh_venv)
    else:
        endpoints_doc = _load_endpoints(Path(args.endpoints))
        verdict = _smoke_in_process(endpoints_doc)

    verdict.setdefault("run_id", uuid.uuid4().hex[:12])
    print(json.dumps(verdict, indent=2))
    return 0 if verdict.get("ok") else (1 if verdict.get("import_ok", True) else 2)


if __name__ == "__main__":
    sys.exit(main())
