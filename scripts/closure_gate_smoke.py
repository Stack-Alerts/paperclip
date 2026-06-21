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
        Create a temporary git worktree at SHA, install the requirements there
        if a fresh venv is requested via --fresh-venv, then run the in-tree
        smoke and emit the same JSON verdict. Used by the closure-gate routine
        before flipping an issue to `done`.

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
                ok = in_allow and not is_5xx
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


def _run_at_sha(sha: str, fresh_venv: bool) -> dict[str, Any]:
    """Create a git worktree at SHA and run the smoke from there.

    The worktree is removed before returning. When `fresh_venv` is true we
    install requirements.txt into a throwaway venv first (slow — only used
    when the operator explicitly asks for it). The default re-uses the
    current interpreter, which is the typical CI configuration.
    """
    work_root = Path(tempfile.mkdtemp(prefix=f"closure_gate_sha_{sha[:8]}_"))
    work_tree = work_root / "tree"
    verdict: dict[str, Any] = {
        "schema": "closure_gate_smoke.v1",
        "at_sha": sha,
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

        # Run the smoke from inside the worktree so the routine evaluates the
        # exact code at SHA (not the current main checkout).
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
