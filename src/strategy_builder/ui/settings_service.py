"""
Settings Service — BTC Trade Engine Strategy Builder

Provides secure persistence for application settings:
- User-editable settings (API keys, preferences) stored in OS keyring
- Admin-only settings (DB config, performance tuning) stored in OS keyring
- Admin PIN stored as bcrypt hash in keyring (never plaintext)
- Non-secret settings stored in .env file via python-dotenv

Security architecture per BTCAAAAA-79 SecurityAnalyst recommendations:
  - OS keyring (GNOME Keyring / Keychain / Windows Credential Manager) for all
    secret fields — no plaintext secrets written to .env via the UI save path
  - bcrypt PIN hash for admin role gate — hash stored in keyring
  - .env file permissions enforced to 600 on every save

Author: UIEngineer (BTCAAAAA-80)
"""

from __future__ import annotations

import enum
import os
import stat
from typing import Any, Optional

import bcrypt
import keyring
from dotenv import load_dotenv, set_key

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KEYRING_SERVICE = "btc-trade-engine"
ENV_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)
    )))),
    ".env"
)

# Secret field names stored in keyring (never written to .env)
SECRET_KEYS = {
    "OPENROUTER_API_KEY",
    "LAKEAPI_KEY",
    "LAKEAPI_SECRET",
    "POSTGRES_PASSWORD",
}

# Admin-only settings (hidden from user role)
ADMIN_ONLY_KEYS = {
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_POOL_SIZE",
    "POSTGRES_MAX_OVERFLOW",
    "POSTGRES_POOL_TIMEOUT",
    "POSTGRES_POOL_RECYCLE",
    "LAKEAPI_REGION",
    "LAKEAPI_LIMIT_GB",
    "MULTICORE_WORKERS",
    "LOG_LEVEL",
    "ENABLE_ALERTS",
    "STRATEGY_ANALYSIS_LOG_LEVEL",
}

# User-editable settings (always visible)
USER_KEYS = {
    "OPENROUTER_API_KEY",
    "LAKEAPI_KEY",
    "LAKEAPI_SECRET",
    "AI_MODEL",
    "DARK_THEME_ENABLED",
    "ALERT_EMAIL",
}

# Default non-secret user-editable values
USER_DEFAULTS = {
    "AI_MODEL": "anthropic/claude-4.5-sonnet",
    "DARK_THEME_ENABLED": "true",
    "ALERT_EMAIL": "",
}

# Default non-secret admin-editable values
ADMIN_DEFAULTS = {
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "optimizer_v3",
    "POSTGRES_USER": "optimizer_admin",
    "LAKEAPI_REGION": "eu-west-1",
    "LAKEAPI_LIMIT_GB": "300",
    "LOG_LEVEL": "INFO",
    "ENABLE_ALERTS": "false",
}


# ---------------------------------------------------------------------------
# Role enum
# ---------------------------------------------------------------------------

class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"


# ---------------------------------------------------------------------------
# SettingsService
# ---------------------------------------------------------------------------

class SettingsService:
    """
    Central service for loading, saving, and securing application settings.

    Secrets are stored in the OS keyring; non-secret settings go to .env.
    Admin access is gated by a PIN hash stored in the keyring.
    """

    def __init__(self) -> None:
        self._role: UserRole = UserRole.USER
        load_dotenv(ENV_FILE, override=False)

    # ------------------------------------------------------------------
    # Role / authentication
    # ------------------------------------------------------------------

    @property
    def role(self) -> UserRole:
        return self._role

    def is_admin(self) -> bool:
        return self._role == UserRole.ADMIN

    def authenticate_admin(self, pin: str) -> bool:
        """
        Verify PIN and elevate to ADMIN role if correct.

        .. deprecated::
            Prefer :meth:`elevate_to_admin` which is the canonical public
            entry-point for PIN-based role elevation.  This method is kept
            for backwards compatibility and delegates to ``elevate_to_admin``.

        Returns True if authentication succeeded, False otherwise.
        Stores nothing to disk — session role only.
        """
        return self.elevate_to_admin(pin)

    def elevate_to_admin(self, pin: str) -> bool:
        """
        Validate *pin* against the stored bcrypt hash and, on success,
        elevate the session role to ADMIN.

        This is the **single authorised entry-point** for granting admin
        access via PIN.  No external caller should write ``_role`` directly.

        Returns:
            ``True``  — PIN matched; session role is now ADMIN.
            ``False`` — PIN wrong or no PIN stored; role unchanged.

        Stores nothing to disk — session role only.
        """
        stored_hash = keyring.get_password(KEYRING_SERVICE, "admin_pin_hash")
        if not stored_hash:
            # No PIN set yet — first-time setup path
            return False
        try:
            ok = bcrypt.checkpw(pin.encode("utf-8"), stored_hash.encode("utf-8"))
            if ok:
                self._role = UserRole.ADMIN
            return ok
        except Exception:
            return False

    def elevate_to_admin_first_run(self) -> None:
        """
        Temporarily grant ADMIN role for the first-run PIN-setup flow.

        Only valid when **no** admin PIN has been stored yet.  Raises
        ``PermissionError`` if a PIN already exists (use
        :meth:`elevate_to_admin` in that case).

        The caller is responsible for calling :meth:`drop_admin` if the
        subsequent :meth:`set_admin_pin` call fails.
        """
        if self.has_admin_pin():
            raise PermissionError(
                "elevate_to_admin_first_run() is only valid before a PIN is set. "
                "Use elevate_to_admin(pin) to authenticate with an existing PIN."
            )
        self._role = UserRole.ADMIN

    def drop_admin(self) -> None:
        """Revoke admin session — returns role to USER."""
        self._role = UserRole.USER

    def set_admin_pin(self, new_pin: str) -> None:
        """
        Set (or change) the admin PIN.  Requires caller to already be ADMIN
        or there must be no existing PIN (first-run setup).

        Stores bcrypt hash in OS keyring — never in .env.
        """
        if not self.is_admin():
            existing = keyring.get_password(KEYRING_SERVICE, "admin_pin_hash")
            if existing:
                raise PermissionError("Must be admin to change the PIN")
        hashed = bcrypt.hashpw(new_pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        keyring.set_password(KEYRING_SERVICE, "admin_pin_hash", hashed)

    def has_admin_pin(self) -> bool:
        """Return True if an admin PIN has been configured."""
        return keyring.get_password(KEYRING_SERVICE, "admin_pin_hash") is not None

    # ------------------------------------------------------------------
    # Reading settings
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[str]:
        """
        Read a setting value.

        - Secret keys: read from keyring
        - Non-secret keys: read from environment / .env
        """
        self._check_access(key)
        if key in SECRET_KEYS:
            return keyring.get_password(KEYRING_SERVICE, key)
        return os.getenv(key)

    def get_with_default(self, key: str, default: str = "") -> str:
        value = self.get(key)
        if value is None:
            return default
        return value

    def get_masked(self, key: str) -> str:
        """
        Return a masked representation for UI display (last 4 chars visible).

        Example: "sk-or-v1-...ac84"  →  "••••••••••••••••ac84"
        Returns empty string if no value stored.
        """
        self._check_access(key)
        value: Optional[str]
        if key in SECRET_KEYS:
            value = keyring.get_password(KEYRING_SERVICE, key)
        else:
            value = os.getenv(key)

        if not value:
            return ""
        if len(value) <= 4:
            return "•" * len(value)
        return "•" * (len(value) - 4) + value[-4:]

    # ------------------------------------------------------------------
    # Writing settings
    # ------------------------------------------------------------------

    def set(self, key: str, value: str) -> None:
        """
        Persist a setting value.

        - Secret keys: written to keyring ONLY (never to .env)
        - Non-secret keys: written to .env file; .env permissions set to 600
        """
        self._check_access(key)
        if key in SECRET_KEYS:
            keyring.set_password(KEYRING_SERVICE, key, value)
        else:
            set_key(ENV_FILE, key, value)
            self._enforce_env_permissions()
            # Reload so os.getenv picks up the new value in the current process
            load_dotenv(ENV_FILE, override=True)

    def save_user_settings(self, values: dict[str, str]) -> None:
        """
        Persist all user-editable settings in one call.

        values: {setting_key: new_value_or_sentinel}
        Sentinel "••••" (all bullets) means "unchanged — skip".
        """
        for key, value in values.items():
            if key not in USER_KEYS:
                continue
            if set(value) == {"•"}:
                # Masked sentinel — user did not change the field
                continue
            self.set(key, value)

    def save_admin_settings(self, values: dict[str, str]) -> None:
        """
        Persist all admin-editable settings in one call.

        Requires admin role.
        """
        if not self.is_admin():
            raise PermissionError("Admin role required to save admin settings")
        for key, value in values.items():
            if key not in ADMIN_ONLY_KEYS and key not in USER_KEYS:
                continue
            if set(value) == {"•"}:
                continue
            self.set(key, value)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_access(self, key: str) -> None:
        """Raise PermissionError if current role cannot access the key."""
        if key in ADMIN_ONLY_KEYS and not self.is_admin():
            raise PermissionError(
                f"Setting '{key}' requires admin role. "
                "Authenticate via the Admin section in Settings."
            )

    @staticmethod
    def _enforce_env_permissions() -> None:
        """Set .env file permissions to 600 (owner read/write only)."""
        if os.path.exists(ENV_FILE):
            try:
                os.chmod(ENV_FILE, stat.S_IRUSR | stat.S_IWUSR)
            except OSError:
                pass  # Non-fatal on read-only filesystems or non-POSIX
