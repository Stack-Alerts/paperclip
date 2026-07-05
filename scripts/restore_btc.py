#!/usr/bin/env python3
"""
BTC Trade Engine — Backup Restore CLI

Standalone tool for listing, inspecting, and restoring backups. Works when
the web UI is unreachable (UI-down fallback). Reads ``~/.btc-backup/config.json``
for provider configuration.

Exit codes
----------
  0  success
  1  generic error
  2  bad arguments
  3  nothing to restore / no backups found
  4  verification failed

Usage
-----
  python scripts/restore_btc.py list
  python scripts/restore_btc.py list --provider onedrive
  python scripts/restore_btc.py list --kind db
  python scripts/restore_btc.py list --since 2026-06-01
  python scripts/restore_btc.py inspect <backup-id>
  python scripts/restore_btc.py restore <backup-id>              # dry-run by default
  python scripts/restore_btc.py restore <backup-id> --yes        # skip prompt
  python scripts/restore_btc.py restore <backup-id> --target /restore/path
  python scripts/restore_btc.py restore-db <backup-id> --pg-url postgresql://...
  python scripts/restore_btc.py configure <provider>             # OAuth / local dir
  python scripts/restore_btc.py configure --list
  python scripts/restore_btc.py configure --remove <provider>

Design rules (P4 spec)
----------------------
* No deps on the running app process. Imports the importable P2 library
  ``src/backup/restore.py`` plus the provider modules.
* TTY-safe prompts — ``--yes`` flag bypasses them.
* Color output only when stdout is a TTY (``sys.stdout.isatty()``).
* Logs go to stderr; results to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── make project root importable when called as ``python scripts/restore_btc.py`` ──
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.backup.local_provider import LocalProvider  # noqa: E402
from src.backup.manifest import BackupManifest, ManifestEntry  # noqa: E402
from src.backup.provider import BackupProvider  # noqa: E402
from src.backup.rclone_provider import RcloneProvider  # noqa: E402
from src.backup.restore import (  # noqa: E402
    BackupContents,
    FileStatus,
    RestoreReport,
    inspect_backup,
    restore_db_dump,
    restore_to_path,
)

# ── exit codes ────────────────────────────────────────────────────────────────
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_BAD_ARGS = 2
EXIT_NOTHING = 3
EXIT_VERIFY_FAIL = 4

# ── colour helpers (stdout-only, TTY-gated) ───────────────────────────────────
_USE_COLOR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\\033[{code}m{text}\\033[0m" if _USE_COLOR else text


def _green(t: str) -> str:  return _c("32", t)
def _red(t: str) -> str:    return _c("31", t)
def _yellow(t: str) -> str: return _c("33", t)
def _bold(t: str) -> str:   return _c("1", t)
def _dim(t: str) -> str:    return _c("2", t)

# ── paths ─────────────────────────────────────────────────────────────────────
CONFIG_PATH = Path.home() / ".btc-backup" / "config.json"
RCLONE_CONFIG = Path.home() / ".config" / "rclone" / "rclone.conf"

_DEFAULT_CONFIG: dict = {"providers": []}


# ── logging helpers ───────────────────────────────────────────────────────────

def _err(*args: object) -> None:
    """Logs channel — stderr."""
    print(*args, file=sys.stderr)


# ── config I/O ────────────────────────────────────────────────────────────────

def _load_config(path: Path | None = None) -> dict:
    """Load JSON config; raise SystemExit(EXIT_ERROR) on parse failure."""
    cfg_path = path or CONFIG_PATH
    if not cfg_path.exists():
        return {"providers": []}
    try:
        return json.loads(cfg_path.read_text())
    except json.JSONDecodeError as exc:
        _err(f"Invalid config JSON at {cfg_path}: {exc}")
        sys.exit(EXIT_ERROR)


def _save_config(cfg: dict, path: Path | None = None) -> None:
    cfg_path = path or CONFIG_PATH
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2))


# ── provider factory ──────────────────────────────────────────────────────────

# Provider types handled by RcloneProvider.
_RCLONE_TYPES = {"rclone", "onedrive", "gdrive", "google", "s3", "b2"}


def _build_provider(entry: dict) -> BackupProvider:
    """Build a provider from a config entry dict."""
    ptype = entry.get("type", "local")
    if ptype == "local":
        backup_dir = entry.get("backup_dir") or entry.get("path")
        if not backup_dir:
            raise ValueError(
                f"local provider {entry.get('name')!r} missing 'backup_dir'"
            )
        return LocalProvider(Path(os.path.expanduser(backup_dir)))
    if ptype in _RCLONE_TYPES:
        remote = entry.get("remote")
        if not remote:
            raise ValueError(
                f"{ptype} provider {entry.get('name')!r} missing 'remote'"
            )
        cfg_path = entry.get("config_path") or str(RCLONE_CONFIG)
        return RcloneProvider(remote=remote, config_path=cfg_path)
    raise ValueError(f"Unknown provider type: {ptype!r}")


def _iter_providers(
    cfg: dict, *, filter_name: Optional[str] = None
) -> list[tuple[str, BackupProvider]]:
    providers_cfg = cfg.get("providers") or []
    result: list[tuple[str, BackupProvider]] = []
    for entry in providers_cfg:
        name = entry.get("name") or entry.get("type", "unnamed")
        if filter_name and name != filter_name:
            continue
        result.append((name, _build_provider(entry)))
    return result


# ── manifest bridging ─────────────────────────────────────────────────────────
# ``provider.list_backups()`` returns thin ``dict`` manifests written by each
# provider's ``upload()``. The rich pydantic ``BackupManifest`` consumed by the
# restore library needs ``kind``, ``contents``, ``host_fingerprint`` etc., which
# are NOT in those dicts. We bridge by reading ``.meta.json`` directly and
# optionally enriching it. When the file is the entire backup blob we model it
# as a single ``ManifestEntry`` — that's enough for restore_to_path to fan out.


def _infer_kind(meta: dict) -> str:
    """Infer BackupManifest.kind from meta dict; defaults to 'db'."""
    src = (meta.get("source") or meta.get("path") or "").lower()
    return "system" if "system" in src else "db"


def _manifest_from_meta(
    meta: dict, *, host_fingerprint: str = "0" * 32
) -> BackupManifest:
    """Build a rich BackupManifest from a thin list_backups dict."""
    remote_id = meta.get("remote_id", "")
    stored_filename = remote_id
    entry = ManifestEntry(
        path=stored_filename,
        size_bytes=int(meta.get("size", 0) or meta.get("size_bytes", 0) or 0),
        sha256=meta.get("sha256", "") or "",
    )
    src_path = meta.get("source") or meta.get("path")
    created_at_raw = meta.get("uploaded_at") or meta.get("created_at")
    if isinstance(created_at_raw, str):
        try:
            created_at = datetime.fromisoformat(
                created_at_raw.replace("Z", "+00:00")
            )
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
        except ValueError:
            created_at = datetime.now(timezone.utc)
    else:
        created_at = datetime.now(timezone.utc)
    return BackupManifest(
        provider=meta.get("provider", "local"),
        kind=_infer_kind(meta),  # type: ignore[arg-type]
        path=src_path or stored_filename,
        size_bytes=entry.size_bytes,
        sha256=entry.sha256,
        duration_seconds=0,
        host_fingerprint=host_fingerprint,
        created_at=created_at,
        contents=[entry],
    )


# ── formatting helpers ────────────────────────────────────────────────────────

def _fmt_size(n: int) -> str:
    try:
        n = float(n)
    except (TypeError, ValueError):
        return str(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _fmt_dt(value) -> str:
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    elif isinstance(value, datetime):
        dt = value
    else:
        return str(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


# ── find backup across providers ──────────────────────────────────────────────

def _find_backup(
    cfg: dict, backup_id: str, *, kind_filter: Optional[str] = None
) -> tuple[str, BackupProvider, BackupManifest] | int:
    """Return (provider_name, provider, manifest) on success, else an int exit code."""
    matches: list[tuple[str, BackupProvider, BackupManifest]] = []
    for pname, provider in _iter_providers(cfg):
        try:
            items = provider.list_backups()
        except Exception as exc:
            _err(f"Warning: failed to list backups from {pname!r}: {exc}")
            continue
        for meta in items:
            if meta.get("remote_id") != backup_id:
                continue
            manifest = _manifest_from_meta(meta)
            if kind_filter and manifest.kind != kind_filter:
                continue
            matches.append((pname, provider, manifest))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        _err(f"Backup {backup_id!r} not found in any configured provider.")
        return -EXIT_ERROR
    _err(
        f"Backup {backup_id!r} appears in multiple providers: "
        + ", ".join(pname for pname, _, _ in matches)
        + ". Disambiguate with --provider."
    )
    return -EXIT_BAD_ARGS


# ── list command ──────────────────────────────────────────────────────────────

def cmd_list(args: argparse.Namespace) -> int:
    cfg = _load_config()
    providers = _iter_providers(cfg, filter_name=args.provider)

    since_dt: Optional[datetime] = None
    if args.since:
        try:
            since_dt = datetime.fromisoformat(args.since).replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            _err(f"Invalid --since date: {args.since!r} (use YYYY-MM-DD)")
            return EXIT_BAD_ARGS

    rows: list[tuple[str, BackupManifest]] = []
    for pname, provider in providers:
        try:
            items = provider.list_backups()
        except Exception as exc:
            _err(f"Warning: failed to list backups from {pname!r}: {exc}")
            continue
        for meta in items:
            m = _manifest_from_meta(meta)
            if args.kind and m.kind != args.kind:
                continue
            if since_dt and m.created_at < since_dt:
                continue
            rows.append((pname, m))

    if not rows:
        print(_yellow("No backups found."))
        return EXIT_NOTHING

    rows.sort(key=lambda t: t[1].created_at, reverse=True)

    print(
        f"{'BACKUP ID':<40}  {'PROVIDER':<12}  "
        f"{'KIND':<8}  {'SIZE':>10}  CREATED"
    )
    print("-" * 90)
    for pname, m in rows:
        print(
            f"{_bold(str(m.id)):<40}  "
            f"{pname:<12}  "
            f"{m.kind:<8}  "
            f"{_fmt_size(m.size_bytes):>10}  "
            f"{_fmt_dt(m.created_at)}"
        )

    print()
    print(_dim(f"{len(rows)} backup(s) found."))
    return EXIT_OK


# ── inspect command ───────────────────────────────────────────────────────────

def cmd_inspect(args: argparse.Namespace) -> int:
    cfg = _load_config()
    backup_id: str = args.backup_id
    found = _find_backup(cfg, backup_id)
    if isinstance(found, int):
        return -found

    pname, provider, manifest = found
    contents: BackupContents = inspect_backup(provider, manifest)

    print(_bold(f"Backup: {contents.manifest.id}"))
    print(f"  Provider   : {pname}")
    print(f"  Kind       : {contents.manifest.kind}")
    print(f"  Created    : {_fmt_dt(contents.manifest.created_at)}")
    print(f"  Size       : {_fmt_size(contents.manifest.size_bytes)}")
    print(f"  SHA-256    : {contents.manifest.sha256 or _dim('(not stored)')}")
    if contents.entries:
        print(f"  Files      : {len(contents.entries)}")
        total = sum(e.size_bytes for e in contents.entries)
        print(f"  Total size : {_fmt_size(total)}")
        print()
        print(f"  {'PATH':<50}  {'SIZE':>10}  SHA-256")
        print("  " + "-" * 90)
        for e in contents.entries:
            sha_preview = (e.sha256[:16] + "…") if e.sha256 else "(none)"
            print(f"  {e.path:<50}  {_fmt_size(e.size_bytes):>10}  {sha_preview}")
    else:
        print(f"  Files      : (no file manifest)")

    return EXIT_OK


# ── restore command ───────────────────────────────────────────────────────────

def cmd_restore(args: argparse.Namespace) -> int:
    cfg = _load_config()
    backup_id: str = args.backup_id
    dry_run = not args.yes

    found = _find_backup(cfg, backup_id)
    if isinstance(found, int):
        return -found

    pname, provider, manifest = found
    display_target = (
        Path(args.target) if args.target
        else Path(tempfile.gettempdir()) / f"btc-restore-{uuid.uuid4().hex[:8]}"
    )

    print(_bold("Restore plan:"))
    print(f"  Backup   : {manifest.id}")
    print(f"  Provider : {pname}")
    print(f"  Target   : {display_target}")
    print(f"  Kind     : {manifest.kind}")
    print(f"  Size     : {_fmt_size(manifest.size_bytes)}")
    if manifest.contents:
        print(f"\n  Files to write ({len(manifest.contents)}):")
        dest_root = display_target / manifest.kind / str(manifest.id)
        for e in manifest.contents:
            print(f"    {dest_root / e.path}")
    else:
        print("\n  (no contents recorded — provider will be probed on execute)")

    if dry_run:
        print()
        print(
            _yellow(
                "Dry-run mode — no files written. Pass --yes to execute."
            )
        )
        return EXIT_OK

    target_dir = (
        Path(args.target) if args.target
        else Path(tempfile.mkdtemp(prefix="btc-restore-"))
    )

    if sys.stdin.isatty():
        try:
            answer = input(_bold("\nProceed with restore? [y/N] ")).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return EXIT_OK
        if answer not in ("y", "yes"):
            print("Restore cancelled.")
            return EXIT_OK

    _err(f"Restoring {manifest.id} to {target_dir} …")
    try:
        report: RestoreReport = restore_to_path(
            provider, manifest, target_dir, dry_run=False
        )
    except Exception as exc:
        _err(_red(f"Restore error: {exc}"))
        return EXIT_ERROR

    if not report.success:
        for e in report.errors:
            _err(_red(e))
        return EXIT_VERIFY_FAIL

    print(_green(f"Restore complete: {target_dir}"))
    for f in report.files:
        marker = "ok" if f.ok else ("skipped" if f.skipped else "FAIL")
        print(f"  {marker:<8}  {f.path}  ({_fmt_size(f.size_bytes)})")
    return EXIT_OK


# ── restore-db command ────────────────────────────────────────────────────────

def cmd_restore_db(args: argparse.Namespace) -> int:
    cfg = _load_config()
    backup_id: str = args.backup_id
    pg_url: str = args.pg_url
    dry_run = not args.yes

    found = _find_backup(cfg, backup_id, kind_filter="db")
    if isinstance(found, int):
        return -found

    pname, provider, manifest = found

    _err(f"Restoring {manifest.id} (from {pname}) to PostgreSQL …")
    try:
        report: RestoreReport = restore_db_dump(
            provider, manifest, pg_url, dry_run=dry_run
        )
    except Exception as exc:
        _err(_red(f"DB restore error: {exc}"))
        return EXIT_ERROR

    if dry_run:
        print(_yellow("Dry-run mode — no DB connection made. Pass --yes to execute."))
        for w in report.warnings:
            print(f"  warn  {w}")
        return EXIT_OK

    if not report.success:
        for e in report.errors:
            _err(_red(e))
        return EXIT_VERIFY_FAIL

    print(_green("Database restore complete."))
    return EXIT_OK


# ── configure command ─────────────────────────────────────────────────────────

def cmd_configure(args: argparse.Namespace) -> int:
    cfg = _load_config()

    if args.list:
        providers = cfg.get("providers") or []
        if not providers:
            print(_yellow("No providers configured."))
            return EXIT_OK
        print(_bold("Configured providers:"))
        for p in providers:
            name = p.get("name") or p.get("type", "?")
            ptype = p.get("type", "?")
            extra = {k: v for k, v in p.items() if k not in ("name", "type")}
            print(
                f"  {_green(name)}  ({ptype})  "
                f"{json.dumps(extra) if extra else ''}"
            )
        return EXIT_OK

    if args.remove:
        name = args.remove
        providers = cfg.get("providers") or []
        kept = [p for p in providers if p.get("name") != name]
        if len(kept) == len(providers):
            _err(f"Provider {name!r} not found in config.")
            return EXIT_ERROR
        cfg["providers"] = kept
        _save_config(cfg)
        print(_green(f"Provider {name!r} removed."))
        return EXIT_OK

    if not args.provider_name:
        _err("Specify a provider name or use --list / --remove.")
        return EXIT_BAD_ARGS

    name = args.provider_name
    ptype = _detect_provider_type(name)
    if ptype in _RCLONE_TYPES:
        return _configure_rclone(cfg, name, ptype)
    return _configure_local(cfg, name)


def _detect_provider_type(name: str) -> str:
    lower = name.lower()
    return lower.replace("google", "gdrive") if lower in _RCLONE_TYPES else "local"


def _configure_local(cfg: dict, name: str) -> int:
    default_dir = str(Path.home() / ".btc-backup" / "local")
    if sys.stdin.isatty():
        try:
            backup_dir = input(f"Local backup directory [{default_dir}]: ").strip()
        except EOFError:
            backup_dir = ""
    else:
        backup_dir = ""
    if not backup_dir:
        backup_dir = default_dir
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    entry = {"name": name, "type": "local", "backup_dir": backup_dir}
    _upsert_provider(cfg, name, entry)
    _save_config(cfg)
    print(_green(f"Local provider {name!r} configured at {backup_dir}"))
    return EXIT_OK


def _configure_rclone(cfg: dict, provider_name: str, ptype: str) -> int:
    remote = f"{provider_name}:btc-backups"
    _err(f"Configuring {ptype} provider via rclone …")
    _err(f"  rclone config file : {RCLONE_CONFIG}")
    _err(f"  Remote             : {remote}")
    _err()
    _err("Running: rclone config …")
    try:
        result = subprocess.run(
            ["rclone", f"--config={RCLONE_CONFIG}", "config"],
            env=os.environ.copy(),
        )
    except FileNotFoundError:
        _err(_red("rclone binary not found in $PATH."))
        return EXIT_ERROR
    if result.returncode != 0:
        _err(_red("rclone config exited with error."))
        return EXIT_ERROR
    entry = {"name": provider_name, "type": "rclone", "remote": remote}
    _upsert_provider(cfg, provider_name, entry)
    _save_config(cfg)
    print(
        _green(
            f"Provider {provider_name!r} configured. Remote: {remote}"
        )
    )
    return EXIT_OK


def _upsert_provider(cfg: dict, name: str, entry: dict) -> None:
    providers = cfg.setdefault("providers", [])
    for i, p in enumerate(providers):
        if p.get("name") == name:
            providers[i] = entry
            return
    providers.append(entry)


# ── argument parser ───────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="restore_btc.py",
        description=(
            "BTC Trade Engine backup restore CLI — works without the web UI."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  list                          List backups across all providers
  list --provider <name>        Filter by provider name
  list --kind db                Filter by backup kind (db, system)
  list --since 2026-06-01       Filter by creation date (UTC)
  inspect <backup-id>           Show contents + sha256
  restore <backup-id>           Dry-run by default; prints plan, exits 0
  restore <backup-id> --yes     Skip confirmation, execute restore
  restore <backup-id> --target <path>
  restore-db <backup-id> --pg-url postgresql://user:pass@host:5432/db
  configure <provider>          Local dir or rclone-backed provider setup
  configure --list              Show configured providers
  configure --remove <name>     Revoke / remove a configured provider

Exit codes:
  0  success
  1  generic error
  2  bad arguments
  3  nothing to restore / no backups found
  4  verification failed
""",
    )

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_list = sub.add_parser("list", help="List all backups")
    p_list.add_argument(
        "--provider", metavar="NAME", help="Filter by provider name"
    )
    p_list.add_argument(
        "--kind", metavar="KIND", help="Filter by backup kind (db, system)"
    )
    p_list.add_argument(
        "--since",
        metavar="DATE",
        help="Only backups created after DATE (YYYY-MM-DD UTC)",
    )

    p_inspect = sub.add_parser("inspect", help="Show backup contents + sha256")
    p_inspect.add_argument("backup_id", metavar="<backup-id>")

    p_restore = sub.add_parser(
        "restore", help="Restore a backup to a local directory (dry-run by default)"
    )
    p_restore.add_argument("backup_id", metavar="<backup-id>")
    p_restore.add_argument(
        "--yes", action="store_true", help="Skip confirmation prompt"
    )
    p_restore.add_argument(
        "--target", metavar="PATH", help="Target directory (default: temp dir)"
    )

    p_rdb = sub.add_parser(
        "restore-db", help="Restore a database backup via psql"
    )
    p_rdb.add_argument("backup_id", metavar="<backup-id>")
    p_rdb.add_argument(
        "--pg-url",
        required=True,
        metavar="URL",
        help="postgresql://user:pass@host:5432/db",
    )
    p_rdb.add_argument(
        "--yes",
        action="store_true",
        help="Skip dry-run (actually connect and pipe to psql)",
    )

    p_cfg = sub.add_parser("configure", help="Configure backup providers")
    p_cfg.add_argument(
        "provider_name",
        nargs="?",
        metavar="<provider>",
        help="Provider name (local, onedrive, gdrive, s3)",
    )
    p_cfg.add_argument(
        "--list", action="store_true", help="Show configured providers"
    )
    p_cfg.add_argument(
        "--remove", metavar="NAME", help="Remove / revoke a configured provider"
    )

    return parser


# ── entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(EXIT_BAD_ARGS)

    dispatch = {
        "list": cmd_list,
        "inspect": cmd_inspect,
        "restore": cmd_restore,
        "restore-db": cmd_restore_db,
        "configure": cmd_configure,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(EXIT_BAD_ARGS)

    try:
        code = handler(args)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        _err("\nInterrupted.")
        sys.exit(EXIT_ERROR)
    except Exception as exc:
        _err(_red(f"Error: {exc}"))
        sys.exit(EXIT_ERROR)

    sys.exit(code if isinstance(code, int) else EXIT_OK)


if __name__ == "__main__":
    main()
