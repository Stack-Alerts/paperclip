"""Tests for the P5 ``/api/backup/*`` endpoint surface.

Covers (P5 hard-gate):
* Every endpoint rejects missing/expired JWT (401).
* Provider CRUD never echoes back the on-disk ``path``/``remote``/``config_path``.
* Validation rejects malformed cron expressions and bad provider specs (422).
* /run-now returns a UUID ``run_id`` plus a self-link; /runs/{id} reaches
  a terminal status (``complete``/``failed``/``skipped``) without hanging.
* PUT /config hot-reloads the scheduler cron (caller cannot crash it).
"""

from __future__ import annotations

import re
import time
import uuid

import pytest

from .conftest import make_token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fresh_config(tmp_path, monkeypatch):
    """Point ``backup.config`` at a temp file and clear any cached state."""
    cfg_path = tmp_path / "config.json"
    meta_path = tmp_path / "provider_tests.json"

    import src.backup.config as cfg_mod
    monkeypatch.setattr(cfg_mod, "CONFIG_PATH", cfg_path)
    monkeypatch.setattr(cfg_mod, "CONFIG_DIR", cfg_path.parent)

    import src.backup.api_router as router_mod
    monkeypatch.setattr(router_mod, "_PROVIDER_TEST_PATH", meta_path)

    # Reset module-level singleton so tests start clean.
    import src.backup.scheduler as sched_mod
    sched_mod.reset_scheduler_instance()
    return cfg_path


def _auth(token: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {token or make_token()}"}
    return headers


# All P5 endpoints + the two legacy endpoints preserved in the router.
ALL_ENDPOINTS_GET = [
    "/api/backup/config",
    "/api/backup/history",
    "/api/backup/status",
    "/api/backup/runs/nonexistent-run-id",  # 404 here is fine — we only test auth
]
ALL_ENDPOINTS_POST = [
    "/api/backup/providers",
    "/api/backup/run-now",
    "/api/backup/validate-cron",
]
ALL_ENDPOINTS_PUT = ["/api/backup/config"]
ALL_ENDPOINTS_DELETE = ["/api/backup/providers/x"]


# ---------------------------------------------------------------------------
# Auth (hard gate: every endpoint behind require_jwt)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ALL_ENDPOINTS_GET)
def test_get_401_without_token(sync_client, path):
    client, _ = sync_client
    resp = client.get(path)
    assert resp.status_code == 401, f"{path} must 401 without JWT"


@pytest.mark.parametrize("path", ALL_ENDPOINTS_POST)
def test_post_401_without_token(sync_client, path):
    client, _ = sync_client
    resp = client.post(path, json={})
    assert resp.status_code == 401, f"{path} must 401 without JWT"


@pytest.mark.parametrize("path", ALL_ENDPOINTS_PUT)
def test_put_401_without_token(sync_client, path):
    client, _ = sync_client
    resp = client.put(path, json={})
    assert resp.status_code == 401, f"{path} must 401 without JWT"


@pytest.mark.parametrize("path", ALL_ENDPOINTS_DELETE)
def test_delete_401_without_token(sync_client, path):
    client, _ = sync_client
    resp = client.delete(path)
    assert resp.status_code == 401, f"{path} must 401 without JWT"


def test_get_401_with_expired_token(sync_client, expired_token):
    client, _ = sync_client
    resp = client.get("/api/backup/config", headers=_auth(expired_token))
    assert resp.status_code == 401


def test_post_401_with_expired_token(sync_client, expired_token):
    client, _ = sync_client
    resp = client.post(
        "/api/backup/validate-cron",
        json={"expression": "0 3 * * *"},
        headers=_auth(expired_token),
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Secret-redaction: no provider response leaks path/remote/config_path
# ---------------------------------------------------------------------------


_SECRET_FIELDS = {"path", "remote", "config_path", "rclone_config", "password"}


def _scrub(obj):
    """Yield every string value in a nested dict/list — for redaction assertions."""
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _scrub(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _scrub(v)
    elif isinstance(obj, str):
        yield obj


def test_get_config_redacts_secrets(sync_client, fresh_config, tmp_path):
    """A /config response never carries on-disk-only provider fields."""
    target = tmp_path / "secredir"
    target.mkdir()
    import src.backup.config as cfg_mod
    cfg = cfg_mod.BackupConfig(
        providers=[
            {"name": "localbox", "type": "local", "path": str(target)}
        ]
    )
    cfg_mod.save_config(cfg, config_path=fresh_config)

    client, _ = sync_client
    resp = client.get("/api/backup/config", headers=_auth())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    blob = "\n".join(_scrub(body))
    assert "secredir" not in blob, f"path component leaked: {blob!r}"
    for fld in _SECRET_FIELDS:
        for provider in body.get("providers", []):
            assert fld not in provider, (
                f"{fld} must not appear in provider view"
            )


def test_provider_view_shape_after_add(sync_client, fresh_config, tmp_path):
    target = tmp_path / "redact-test-path"
    target.mkdir()
    client, _ = sync_client
    body = {"name": "alpha", "type": "local", "path": str(target)}
    resp = client.post("/api/backup/providers", headers=_auth(), json=body)
    assert resp.status_code == 201, resp.text
    view = resp.json()
    assert set(view.keys()) == {"name", "type", "last_test_at", "last_test_ok"}
    for fld in _SECRET_FIELDS:
        assert fld not in view
    assert view["name"] == "alpha"
    assert view["type"] == "local"


# ---------------------------------------------------------------------------
# GET /config / POST /providers / DELETE /providers/{name}
# ---------------------------------------------------------------------------


def test_get_config_empty(sync_client, fresh_config):
    client, _ = sync_client
    resp = client.get("/api/backup/config", headers=_auth())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["providers"] == []
    assert body["schedule_cron"] == "0 3 * * *"
    assert body["scope"] == "db"
    assert body["retention_days"] == 30
    assert body["retention_count"] == 100


def test_add_and_delete_provider(sync_client, fresh_config, tmp_path):
    target = tmp_path / "alpha-dir"
    target.mkdir()
    client, _ = sync_client
    add = client.post(
        "/api/backup/providers",
        headers=_auth(),
        json={"name": "alpha", "type": "local", "path": str(target)},
    )
    assert add.status_code == 201, add.text
    assert add.json()["name"] == "alpha"

    # Duplicate name → 409.
    dup = client.post(
        "/api/backup/providers",
        headers=_auth(),
        json={"name": "alpha", "type": "local", "path": str(target)},
    )
    assert dup.status_code == 409, dup.text

    # Delete → returns the redacted removed-vendor dict.
    rm = client.delete("/api/backup/providers/alpha", headers=_auth())
    assert rm.status_code == 200, rm.text
    assert rm.json() == {
        "name": "alpha",
        "removed": True,
        "last_test_at": None,
        "last_test_ok": None,
    }

    # Subsequent delete is 404.
    rm2 = client.delete("/api/backup/providers/alpha", headers=_auth())
    assert rm2.status_code == 404


def test_add_provider_422_when_path_missing(sync_client, fresh_config):
    client, _ = sync_client
    resp = client.post(
        "/api/backup/providers",
        headers=_auth(),
        json={"name": "no-path", "type": "local"},
    )
    assert resp.status_code == 422, resp.text


def test_add_provider_422_on_unknown_type(sync_client, fresh_config, tmp_path):
    target = tmp_path / "x"
    target.mkdir()
    client, _ = sync_client
    resp = client.post(
        "/api/backup/providers",
        headers=_auth(),
        json={"name": "x", "type": "ftp", "path": str(target)},
    )
    assert resp.status_code == 422, resp.text


def test_add_provider_rejects_traversal_name(sync_client, fresh_config, tmp_path):
    target = tmp_path / "y"
    target.mkdir()
    client, _ = sync_client
    bad = client.post(
        "/api/backup/providers",
        headers=_auth(),
        json={"name": "-bad", "type": "local", "path": str(target)},
    )
    assert bad.status_code == 422

    bad2 = client.post(
        "/api/backup/providers",
        headers=_auth(),
        json={"name": "with..dots", "type": "local", "path": str(target)},
    )
    assert bad2.status_code == 422


# ---------------------------------------------------------------------------
# POST /providers/{name}/test
# ---------------------------------------------------------------------------


def test_provider_test_unknown_returns_404(sync_client, fresh_config):
    client, _ = sync_client
    resp = client.post(
        "/api/backup/providers/ghost/test", headers=_auth()
    )
    assert resp.status_code == 404


def test_provider_test_local_succeeds(sync_client, fresh_config, tmp_path):
    target = tmp_path / "backups-target"
    target.mkdir()
    client, _ = sync_client
    add = client.post(
        "/api/backup/providers",
        headers=_auth(),
        json={"name": "alpha", "type": "local", "path": str(target)},
    )
    assert add.status_code == 201

    resp = client.post(
        "/api/backup/providers/alpha/test", headers=_auth()
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["name"] == "alpha"
    assert body["latency_ms"] >= 0.0
    assert body["free_space_bytes"] is None or body["free_space_bytes"] >= 0
    assert "backups-target" not in str(body)

    # Subsequent GET /config surfaces last_test_at/last_test_ok.
    cfg = client.get("/api/backup/config", headers=_auth()).json()
    view = next(p for p in cfg["providers"] if p["name"] == "alpha")
    assert view["last_test_ok"] is True
    assert view["last_test_at"] is not None


# ---------------------------------------------------------------------------
# PUT /config
# ---------------------------------------------------------------------------


def test_put_config_rejects_bad_cron_with_422(sync_client, fresh_config):
    client, _ = sync_client
    resp = client.put(
        "/api/backup/config",
        headers=_auth(),
        json={"schedule_cron": "this is not cron"},
    )
    assert resp.status_code == 422, resp.text


def test_put_config_updates_and_returns_redacted(sync_client, fresh_config):
    client, _ = sync_client
    resp = client.put(
        "/api/backup/config",
        headers=_auth(),
        json={
            "schedule_cron": "*/15 * * * *",
            "scope": "system",
            "retention_days": 7,
            "retention_count": 50,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["schedule_cron"] == "*/15 * * * *"
    assert body["scope"] == "system"
    assert body["retention_days"] == 7
    assert body["retention_count"] == 50


# ---------------------------------------------------------------------------
# POST /validate-cron (legacy)
# ---------------------------------------------------------------------------


def test_validate_cron_valid_returns_fire_times(sync_client, fresh_config):
    client, _ = sync_client
    resp = client.post(
        "/api/backup/validate-cron",
        headers=_auth(),
        json={"expression": "0 3 * * *"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["valid"] is True
    assert len(body["fire_times"]) == 3


def test_validate_cron_invalid_returns_200_with_error(sync_client, fresh_config):
    client, _ = sync_client
    resp = client.post(
        "/api/backup/validate-cron",
        headers=_auth(),
        json={"expression": "not a cron"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["valid"] is False
    assert body["error"]


# ---------------------------------------------------------------------------
# GET /status (legacy)
# ---------------------------------------------------------------------------


def test_status_with_no_scheduler_yields_graceful(sync_client, fresh_config):
    """A fresh process has no running scheduler — endpoint must still respond 200."""
    client, _ = sync_client
    resp = client.get("/api/backup/status", headers=_auth())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "schedule_cron" in body
    assert "running" in body
    assert "next_fire_times" in body


# ---------------------------------------------------------------------------
# POST /run-now + GET /runs/{id}
# ---------------------------------------------------------------------------


def _drain_run(client, run_id: str, *, timeout_s: float = 5.0) -> dict:
    """Poll /runs/{run_id} until terminal. Returns the final body."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        resp = client.get(f"/api/backup/runs/{run_id}", headers=_auth())
        if resp.status_code != 200:
            return {"_status": resp.status_code, "_body": resp.text}
        body = resp.json()
        if body["status"] in {"complete", "failed", "skipped"}:
            return body
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} never reached terminal state in {timeout_s}s")


def test_run_now_returns_run_id_and_completes(sync_client, fresh_config, tmp_path):
    target = tmp_path / "rt"
    target.mkdir()
    client, _ = sync_client
    add = client.post(
        "/api/backup/providers",
        headers=_auth(),
        json={"name": "beta", "type": "local", "path": str(target)},
    )
    assert add.status_code == 201

    trig = client.post("/api/backup/run-now", headers=_auth(), json={})
    assert trig.status_code == 200, trig.text
    body = trig.json()
    assert "run_id" in body
    assert re.fullmatch(r"[0-9a-f]{32}", body["run_id"]), body["run_id"]
    assert body["status_url"] == f"/api/backup/runs/{body['run_id']}"
    assert body["status"] == "pending"

    final = _drain_run(client, body["run_id"])
    assert final["status"] == "complete", final


def test_run_now_with_invalid_kind_is_422(sync_client, fresh_config):
    client, _ = sync_client
    resp = client.post(
        "/api/backup/run-now", headers=_auth(), json={"kind": "bogus"}
    )
    assert resp.status_code == 422, resp.text


def test_get_run_unknown_404(sync_client, fresh_config):
    client, _ = sync_client
    fake = uuid.uuid4().hex
    resp = client.get(f"/api/backup/runs/{fake}", headers=_auth())
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# GET /history
# ---------------------------------------------------------------------------


def test_history_returns_empty_for_unconfigured_providers(
    sync_client, fresh_config
):
    client, _ = sync_client
    resp = client.get("/api/backup/history", headers=_auth())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["count"] == 0
    assert body["entries"] == []


def test_history_ok_when_provider_configured_no_manifests(
    sync_client, fresh_config, tmp_path
):
    target = tmp_path / "hist-dir"
    target.mkdir()
    client, _ = sync_client
    add = client.post(
        "/api/backup/providers",
        headers=_auth(),
        json={"name": "hist", "type": "local", "path": str(target)},
    )
    assert add.status_code == 201

    resp = client.get("/api/backup/history", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["count"] == 0
