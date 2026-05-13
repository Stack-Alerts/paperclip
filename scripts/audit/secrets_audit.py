"""
Secrets Audit — Scan scripts/ for leaked credentials (DIAG-2).

Required patterns (case-insensitive where noted):
  1. api_key / aws_access_key_id / AWS_ACCESS_KEY = '...' (8+ chars)
  2. secret / aws_secret_access_key / AWS_SECRET_KEY = '...' (8+ chars)
  3. Binance literal strings (BNBBTC, api_key, secret_key) not via os.environ
  4. BINANCE_API_KEY / BINANCE_SECRET as string literals
  5. .env file tracked by git at repo root (ignored if gitignored)

Output format: {file_path}:{line_number}: {pattern_matched}: {snippet}
"""

import os
import re
import subprocess
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SRC_DIR = PROJECT_ROOT / "src"
DOCS_DIR = PROJECT_ROOT / "docs"

# ── Patterns ──────────────────────────────────────────────────────────────────
# AWS access key patterns
PAT_AWS_ACCESS_KEY = re.compile(
    r"(?:aws_access_key_id|AWS_ACCESS_KEY)\s*=\s*['\"]([^'\"]{8,})['\"]",
)
PAT_AWS_SECRET_KEY = re.compile(
    r"(?:aws_secret_access_key|AWS_SECRET_KEY)\s*=\s*['\"]([^'\"]{8,})['\"]",
)

PAT_API_KEY = re.compile(r"api_key\s*=\s*['\"]([^'\"]{8,})['\"]", re.IGNORECASE)
PAT_SECRET = re.compile(r"secret\s*=\s*['\"]([^'\"]{8,})['\"]", re.IGNORECASE)
PAT_STRING_LITERAL = re.compile(r"""['\"]([^'\"]{2,})['\"]""")
PAT_BINANCE_ENV_LITERAL = re.compile(r"""['\"](BINANCE_API_KEY|BINANCE_SECRET)['\"]""")

BINANCE_LITERALS = {"BNBBTC", "api_key", "secret_key"}
KNOWN_PLACEHOLDERS = {"your_key", "your_secret", "your_api_key", "secret_key"}


def _is_benign(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
        return True
    if "os.environ" in stripped or "os.getenv" in stripped or "environ.get" in stripped:
        return True
    if stripped.startswith("import ") or stripped.startswith("from "):
        return True
    return False


def _is_placeholder(val: str) -> bool:
    return val.lower() in KNOWN_PLACEHOLDERS or val.startswith("${")


def _redact_value(snippet: str, value: str) -> str:
    """Redact a matched credential value from the output snippet."""
    return snippet.replace(value, "[REDACTED]")


def _check_pattern(
    pattern: re.Pattern, line: str, lineno: int, file_str: str, label: str, findings: list[str]
) -> bool:
    m = pattern.search(line)
    if m:
        val = m.group(1)
        if not _is_placeholder(val):
            snippet = line.strip()[:80]
            redacted = _redact_value(snippet, val)
            findings.append(f"{file_str}:{lineno}: {label}: {redacted}")
        return True
    return False


def scan_file(path: Path) -> list[str]:
    findings: list[str] = []

    if path.resolve() == THIS_FILE:
        return findings

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return findings

    lines = text.split("\n")
    file_str = str(path)

    for lineno, line in enumerate(lines, 1):
        if _is_benign(line):
            continue

        if _check_pattern(PAT_AWS_ACCESS_KEY, line, lineno, file_str, "hardcoded_aws_access_key", findings):
            continue

        if _check_pattern(PAT_AWS_SECRET_KEY, line, lineno, file_str, "hardcoded_aws_secret_key", findings):
            continue

        if _check_pattern(PAT_API_KEY, line, lineno, file_str, "hardcoded_api_key", findings):
            continue

        if _check_pattern(PAT_SECRET, line, lineno, file_str, "hardcoded_secret", findings):
            continue

        m = PAT_BINANCE_ENV_LITERAL.search(line)
        if m:
            snippet = line.strip()[:80]
            findings.append(f"{file_str}:{lineno}: binance_env_literal: {_redact_value(snippet, m.group(1))}")
            continue

        for m in PAT_STRING_LITERAL.finditer(line):
            val = m.group(1)
            if val in BINANCE_LITERALS:
                if "==" in line or "!=" in line:
                    continue
                if re.search(r'\.(?:get|pop|setdefault)\s*\(\s*["'"'"']' + re.escape(val) + r'["'"'"']', line):
                    continue
                snippet = line.strip()[:80]
                findings.append(f"{file_str}:{lineno}: binance_literal_string: {_redact_value(snippet, val)}")
                break

    return findings


def main() -> None:
    all_findings: list[str] = []

    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        # Only flag .env if it is tracked by git (would be committed).
        # A gitignored .env is the intended safe state.
        try:
            result = subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(env_path)],
                capture_output=True,
                cwd=str(PROJECT_ROOT),
            )
            tracked = result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            tracked = False
        if tracked:
            all_findings.append(f"{env_path}:1: env_file_present: .env file is tracked by git")

    py_files = sorted(SCRIPTS_DIR.rglob("*.py"))
    py_files.extend(sorted(SRC_DIR.rglob("*.py")))
    for fpath in py_files:
        if "__pycache__" in str(fpath):
            continue
        # Note: archived/ directories are NOT excluded.
        # Archived scripts with hardcoded secrets are still a security risk
        # (git history exposure, accidental un-archiving).
        all_findings.extend(scan_file(fpath))

    md_files = sorted(DOCS_DIR.rglob("*.md"))
    for fpath in md_files:
        if "archive" in str(fpath):
            continue
        all_findings.extend(scan_file(fpath))

    for finding in all_findings:
        print(finding)

    if not all_findings:
        print("No secrets found.")

    sys.exit(0 if not all_findings else 1)


if __name__ == "__main__":
    main()
