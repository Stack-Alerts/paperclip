"""
Secrets Audit — Read-only scan for leaked credentials in scripts/.

Checks:
  1. Hardcoded credential patterns (API keys, passwords, tokens, secrets) in .py/.sh
  2. .env file tracked by git (should be gitignored)
  3. Archived scripts with committed credentials
  4. Shell scripts containing plaintext secrets
  5. Placeholder detection (your_*, change_me, sk- patterns that are real keys)
  6. Git history for committed .env files

Produces:
  - Console report
  - data/audit/secrets_audit_report.json (machine-readable findings)
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

KNOWN_PLACEHOLDERS = {
    "your_access_key_here",
    "your_secret_key_here",
    "your_testnet_api_key_here",
    "your_testnet_api_secret_here",
    "your_paperclip_api_key_here",
    "secure_password_change_me",
    "change_me_ai_readonly",
    "your@email.com",
}

SECRET_PATTERNS: list[tuple[str, str, str]] = [
    ("aws_access_key", r"(?i)aws_access_key_id\s*[=:]\s*['\"](?!your_)[^'\"]{10,}", "HIGH"),
    ("aws_secret_key", r"(?i)aws_secret_access_key\s*[=:]\s*['\"](?!your_)[A-Za-z0-9\/+=]{20,}", "HIGH"),
    ("lakeapi_secret", r"(?i)LAKEAPI_SECRET\s*[=:]\s*['\"](?!your_)[^'\"]{10,}", "HIGH"),
    ("openrouter_key", r"(?i)OPENROUTER_API_KEY\s*[=:]\s*['\"]sk-or-v1-[a-f0-9]{8,}", "HIGH"),
    ("binance_testnet_secret", r"(?i)BINANCE_TESTNET_API_SECRET\s*[=:]\s*['\"](?!your_)[^'\"]{10,}", "HIGH"),
    ("binance_mainnet_key", r"(?i)BINANCE_MAINNET_API_KEY\s*[=:]\s*['\"](?!your_)[^'\"]{10,}", "CRITICAL"),
    ("binance_mainnet_secret", r"(?i)BINANCE_MAINNET_API_SECRET\s*[=:]\s*['\"](?!your_)[^'\"]{10,}", "CRITICAL"),
    ("paperclip_api_key", r"(?i)PAPERCLIP_API_KEY\s*[=:]\s*['\"](?!your_)[^'\"]{10,}", "HIGH"),
    ("postgres_password", r"(?i)POSTGRES_PASSWORD\s*[=:]\s*['\"](?!secure_password|change_me|your_)[^'\"]{8,}", "HIGH"),
    ("generic_password", r"(?i)(?:password|passwd|pwd)\s*[=:]\s*['\"](?!your_|secure_|change_me)[^'\"]{6,}", "MEDIUM"),
    ("generic_api_key", r"(?i)(?:api_key|apikey|api_secret)\s*[=:]\s*['\"](?!your_)[A-Za-z0-9_\-]{16,}", "MEDIUM"),
    ("jwt_token", r"(?i)eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}", "HIGH"),
    ("private_key", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "CRITICAL"),
]

EXCLUDE_DIRS = {"__pycache__", ".git"}
EXCLUDE_PATTERNS = [re.compile(r"\.(pyc|pyo|so|dll|pkl|parquet|csv)$")]

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

findings: dict = {
    "audit_date": datetime.now(timezone.utc).isoformat(),
    "sections": {},
}


def _is_excluded(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    for part in rel.parts:
        if part in EXCLUDE_DIRS:
            return True
    for pat in EXCLUDE_PATTERNS:
        if pat.search(path.name):
            return True
    return False


def _is_placeholder(text: str) -> bool:
    stripped = text.strip().strip("'\"")
    # Shell variable expansion e.g. "${VAR:-}" or "${VAR}"
    if "${" in stripped and "}" in stripped:
        return True
    for ph in KNOWN_PLACEHOLDERS:
        if stripped.startswith(ph) or stripped == ph:
            return True
    return False


def _scan_file(path: Path) -> list[dict]:
    results: list[dict] = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [{"file": str(path), "error": str(e), "severity": "WARN"}]

    for name, pattern, severity in SECRET_PATTERNS:
        for match in re.finditer(pattern, content):
            matched = match.group(0)
            if _is_placeholder(matched):
                continue
            line_num = content[: match.start()].count("\n") + 1
            results.append({
                "file": str(path),
                "line": line_num,
                "pattern_name": name,
                "severity": severity,
                "match_snippet": matched[:60],
            })

    return results


def _check_git_tracked_env() -> list[dict]:
    results: list[dict] = []
    try:
        result = subprocess.run(
            ["git", "ls-files", ".env", ".env.example"],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=15,
        )
        tracked = [f for f in result.stdout.strip().split("\n") if f]
        for f in tracked:
            if f == ".env":
                results.append({
                    "file": f,
                    "issue": ".env is tracked by git — should be gitignored",
                    "severity": "CRITICAL",
                })
    except Exception as e:
        results.append({"error": f"git ls-files failed: {e}", "severity": "WARN"})
    return results


def _check_git_history_for_env() -> list[dict]:
    results: list[dict] = []
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--diff-filter=A", "--", ".env"],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=15,
        )
        if result.stdout.strip():
            results.append({
                "issue": ".env was previously committed in git history",
                "commits": result.stdout.strip().split("\n"),
                "severity": "HIGH",
            })
    except Exception as e:
        results.append({"error": f"git log failed: {e}", "severity": "WARN"})
    return results


def _check_gitignore() -> list[dict]:
    results: list[dict] = []
    gitignore_path = PROJECT_ROOT / ".gitignore"
    if not gitignore_path.exists():
        return [{"issue": ".gitignore not found", "severity": "CRITICAL"}]
    text = gitignore_path.read_text()
    has_env = any(line.strip() == ".env" for line in text.splitlines())
    has_env_star = any(line.strip() == ".env.*" for line in text.splitlines())
    if not has_env:
        results.append({
            "issue": ".env not listed in .gitignore",
            "severity": "CRITICAL",
        })
    if not has_env_star:
        results.append({
            "issue": ".env.* not listed in .gitignore (may leak .env.local etc.)",
            "severity": "MEDIUM",
        })
    return results


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: Hardcoded secrets in scripts/
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("SECTION 1: Hardcoded Secrets Scan (scripts/)")
print("=" * 70)

all_leaks: list[dict] = []
file_count = 0

for root, _dirs, files in os.walk(SCRIPTS_DIR):
    for fname in files:
        fpath = Path(root) / fname
        if _is_excluded(fpath, SCRIPTS_DIR):
            continue
        if not fname.endswith((".py", ".sh", ".env", ".txt", ".cfg", ".conf", ".yml", ".yaml", ".json", ".toml", ".ini")):
            continue
        file_count += 1
        leaks = _scan_file(fpath)
        all_leaks.extend(leaks)

seen = set()
deduped_leaks: list[dict] = []
for leak in all_leaks:
    key = (leak["file"], leak["line"], leak["pattern_name"], leak["match_snippet"])
    if key not in seen:
        seen.add(key)
        deduped_leaks.append(leak)

by_severity: dict[str, list[dict]] = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "WARN": []}
for leak in deduped_leaks:
    by_severity.setdefault(leak.get("severity", "MEDIUM"), []).append(leak)

print(f"  Files scanned: {file_count}")
print(f"  Total potential leaks: {len(deduped_leaks)}")
print(f"    CRITICAL: {len(by_severity.get('CRITICAL', []))}")
print(f"    HIGH:     {len(by_severity.get('HIGH', []))}")
print(f"    MEDIUM:   {len(by_severity.get('MEDIUM', []))}")
print(f"    WARN:     {len(by_severity.get('WARN', []))}")

for leak in deduped_leaks:
    print(f"  [{leak['severity']:>8}] {leak['file']}:{leak['line']} — {leak['pattern_name']}")
    print(f"          snippet: {leak['match_snippet'][:80]}")

sec1_status = FAIL if by_severity.get("CRITICAL") or by_severity.get("HIGH") else (WARN if by_severity.get("MEDIUM") else PASS)
findings["sections"]["1_hardcoded_secrets"] = {
    "status": sec1_status,
    "files_scanned": file_count,
    "total_leaks": len(deduped_leaks),
    "by_severity": {k: len(v) for k, v in by_severity.items()},
    "leaks": deduped_leaks,
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: Git tracking audit (.env files)
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("SECTION 2: Git Tracking Audit (.env files)")
print("=" * 70)

env_tracking_issues = _check_git_tracked_env()
for issue in env_tracking_issues:
    print(f"  [{issue.get('severity', 'INFO'):>8}] {issue.get('file', '')} — {issue.get('issue', issue.get('error', ''))}")

if not env_tracking_issues:
    print("  [OK] No .env files tracked by git")

findings["sections"]["2_git_tracking"] = {
    "status": FAIL if any(i.get("severity") == "CRITICAL" for i in env_tracking_issues) else PASS,
    "issues": env_tracking_issues,
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: Git history for .env
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("SECTION 3: Git History — .env file commits")
print("=" * 70)

git_history_issues = _check_git_history_for_env()
if git_history_issues:
    for issue in git_history_issues:
        print(f"  [{issue.get('severity', 'INFO'):>8}] {issue.get('issue', '')}")
        if "commits" in issue:
            for c in issue["commits"]:
                print(f"          {c}")
else:
    print("  [OK] No .env file found in git history")

findings["sections"]["3_git_history"] = {
    "status": (FAIL
               if any(i.get("severity") in ("CRITICAL", "HIGH") for i in git_history_issues)
               else PASS),
    "issues": git_history_issues,
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: .gitignore coverage
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("SECTION 4: .gitignore Coverage")
print("=" * 70)

gitignore_issues = _check_gitignore()
for issue in gitignore_issues:
    print(f"  [{issue.get('severity', 'INFO'):>8}] {issue.get('issue', '')}")

if not gitignore_issues:
    print("  [OK] .gitignore properly covers .env files")

sec4_status = PASS
if any(i.get("severity") == "CRITICAL" for i in gitignore_issues):
    sec4_status = FAIL
elif any(i.get("severity") == "MEDIUM" for i in gitignore_issues):
    sec4_status = WARN

findings["sections"]["4_gitignore_coverage"] = {
    "status": sec4_status,
    "issues": gitignore_issues,
}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: Archived scripts inspection
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("SECTION 5: Archived Scripts — Known Leaked Credentials")
print("=" * 70)

archived_dir = SCRIPTS_DIR / "archived"
archived_leaks: list[dict] = []
if archived_dir.exists():
    for root, _dirs, files in os.walk(archived_dir):
        for fname in files:
            fpath = Path(root) / fname
            if _is_excluded(fpath, SCRIPTS_DIR):
                continue
            leaks = _scan_file(fpath)
            archived_leaks.extend(leaks)

archived_deduped: list[dict] = []
seen_archived = set()
for leak in archived_leaks:
    key = (leak["file"], leak["line"], leak["pattern_name"], leak["match_snippet"])
    if key not in seen_archived:
        seen_archived.add(key)
        archived_deduped.append(leak)

if archived_deduped:
    print(f"  Found {len(archived_deduped)} credential leaks in archived scripts:")
    for leak in archived_deduped:
        print(f"    [{leak['severity']:>8}] {leak['file']}:{leak['line']} — {leak['pattern_name']}")
        print(f"            {leak['match_snippet'][:80]}")
else:
    print("  [OK] No credential leaks found in archived scripts")

findings["sections"]["5_archived_scripts"] = {
    "status": FAIL if archived_deduped else PASS,
    "total_leaks": len(archived_deduped),
    "leaks": archived_deduped,
}


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("SECRETS AUDIT SUMMARY")
print("=" * 70)

status_map: dict[str, str] = {}
for section_key, data in findings["sections"].items():
    if isinstance(data, dict):
        s = data.get("status")
        if s:
            status_map[section_key] = s

all_statuses = list(status_map.values())
overall = FAIL if FAIL in all_statuses else (WARN if WARN in all_statuses else PASS)

for sec, s in status_map.items():
    icon = chr(10004) if s == PASS else (chr(9888) if s == WARN else chr(10007))
    print(f"  {icon} {sec}: {s}")

print(f"\n  OVERALL: {overall}")
findings["overall_status"] = overall

report_path = AUDIT_DIR / "secrets_audit_report.json"
with open(report_path, "w") as f:
    json.dump(findings, f, indent=2, default=str)
print(f"\n  Report saved → {report_path}")
