"""
Settings Dialog — BTC Engine v3 Strategy Builder

Implements the full Settings page under Tools → Settings...

Security architecture per BTCAAAAA-79 SecurityAnalyst recommendations:
  - User section: always visible, shows only user-editable fields
  - Admin section: entirely HIDDEN (not just disabled) until PIN verified
  - Secret fields: masked display (last 4 chars), re-entry required to change
  - No plaintext secrets in editable fields on open — only masked display labels
  - On save: masked sentinel values are skipped (field unchanged)

Author: UIEngineer (BTCAAAAA-80)
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QTabWidget,
    QVBoxLayout, QWidget, QMessageBox, QFrame
)

from src.strategy_builder.ui.settings_service import SettingsService
from src.strategy_builder.ui.styles import (
    COLORS,
    get_main_stylesheet,
    get_primary_button_stylesheet,
    get_secondary_button_stylesheet,
    get_danger_button_stylesheet,
    get_input_field_stylesheet,
    get_tab_widget_stylesheet,
    get_panel_title_stylesheet,
    get_label_style,
    get_transparent_scroll_area_stylesheet,
    create_font,
    apply_hand_cursor_to_buttons,
)

# ---------------------------------------------------------------------------
# Secret field widget
# ---------------------------------------------------------------------------

class SecretFieldWidget(QWidget):
    """
    A compound widget for secret (API key) fields.

    Displays: [ ••••••••••••••last4 ]  [Show 10s]  [Edit]

    - Show: toggles plain-text reveal for 10 seconds then auto-masks.
    - Edit: opens an inline edit mode with a QLineEdit (password echo).
      Saving an unchanged masked value is a no-op (sentinel detection
      handled by SettingsService).
    """

    def __init__(self, key: str, service: SettingsService, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._key = key
        self._service = service
        self._edit_mode = False
        self._show_timer: Optional[QTimer] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Display label (masked)
        self._display_label = QLabel()
        self._display_label.setFont(create_font(10))
        self._display_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-family: monospace;"
        )
        self._display_label.setMinimumWidth(260)
        layout.addWidget(self._display_label, stretch=1)

        # Edit field (hidden by default)
        self._edit_field = QLineEdit()
        self._edit_field.setEchoMode(QLineEdit.Password)
        self._edit_field.setPlaceholderText("Enter new value…")
        self._edit_field.setStyleSheet(get_input_field_stylesheet())
        self._edit_field.setFont(create_font(10))
        self._edit_field.setMinimumWidth(260)
        self._edit_field.hide()
        layout.addWidget(self._edit_field, stretch=1)

        # Show button
        self._show_btn = QPushButton("Show 10s")
        self._show_btn.setFont(create_font(9))
        self._show_btn.setStyleSheet(get_secondary_button_stylesheet())
        # BTCAAAAA-87: setMinimumWidth instead of setFixedWidth so button can
        # grow with content / DPI scaling rather than being clipped.
        self._show_btn.setMinimumWidth(80)
        self._show_btn.clicked.connect(self._on_show)
        layout.addWidget(self._show_btn)

        # Edit / Cancel button
        self._edit_btn = QPushButton("Edit")
        self._edit_btn.setFont(create_font(9))
        self._edit_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        # BTCAAAAA-87: setMinimumWidth instead of setFixedWidth.
        self._edit_btn.setMinimumWidth(60)
        self._edit_btn.clicked.connect(self._on_edit_toggle)
        layout.addWidget(self._edit_btn)

        self._refresh_display()

    # ------------------------------------------------------------------

    def _refresh_display(self) -> None:
        try:
            masked = self._service.get_masked(self._key)
        except PermissionError:
            # Admin-only field accessed before auth — show locked indicator.
            # This is safe: the widget is inside the admin tab which is hidden
            # until PIN is verified.
            self._display_label.setText("(locked — admin access required)")
            self._display_label.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-family: monospace;"
            )
            return
        if masked:
            self._display_label.setText(masked)
        else:
            self._display_label.setText("(not set)")
            self._display_label.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-family: monospace;"
            )

    def _on_show(self) -> None:
        """Reveal plaintext for 10 seconds."""
        if self._edit_mode:
            return
        value = self._service.get(self._key)
        if not value:
            return
        self._display_label.setText(value)
        self._show_btn.setEnabled(False)
        if self._show_timer:
            self._show_timer.stop()
        self._show_timer = QTimer(self)
        self._show_timer.setSingleShot(True)
        self._show_timer.timeout.connect(self._auto_mask)
        self._show_timer.start(10_000)

    def _auto_mask(self) -> None:
        self._refresh_display()
        self._show_btn.setEnabled(True)
        if self._show_timer:
            self._show_timer = None

    def _on_edit_toggle(self) -> None:
        if not self._edit_mode:
            self._enter_edit_mode()
        else:
            self._exit_edit_mode()

    def _enter_edit_mode(self) -> None:
        self._edit_mode = True
        self._display_label.hide()
        self._show_btn.hide()
        self._edit_field.clear()
        self._edit_field.show()
        self._edit_field.setFocus()
        self._edit_btn.setText("Cancel")
        self._edit_btn.setStyleSheet(get_danger_button_stylesheet())

    def _exit_edit_mode(self) -> None:
        self._edit_mode = False
        self._edit_field.clear()
        self._edit_field.hide()
        self._display_label.show()
        self._show_btn.show()
        self._edit_btn.setText("Edit")
        self._edit_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        self._refresh_display()

    # ------------------------------------------------------------------
    # Public interface

    def get_value(self) -> str:
        """
        Return the current value for this field.

        - If in edit mode and the user typed something: return the typed text.
        - Otherwise: return the masked sentinel so SettingsService skips it.
        """
        if self._edit_mode and self._edit_field.text().strip():
            return self._edit_field.text()
        # Return all-bullets sentinel — SettingsService will skip
        return "••••"

    def clear_edit(self) -> None:
        """Called after save — leave edit mode and re-mask."""
        if self._edit_mode:
            self._exit_edit_mode()
        self._refresh_display()


# ---------------------------------------------------------------------------
# Admin PIN dialog
# ---------------------------------------------------------------------------

class AdminPinDialog(QDialog):
    """
    PIN entry dialog for admin authentication or first-run PIN setup.

    Authentication mode (setup_mode=False, service provided):
    - Validates the PIN against SettingsService.elevate_to_admin().
    - Accepts (Accepted result) only on a correct PIN.
    - After 3 consecutive failures the dialog locks for 30 seconds.
    - A visible countdown label shows remaining seconds.
    - Input fields and the OK button are disabled during lockout.
    - Failure count resets when lockout expires or dialog closes.

    Setup mode (setup_mode=True):
    - No service needed; no lockout — user is creating the PIN fresh.
    - Dialog accepts with the entered PIN/confirm values for the caller
      to process.
    """

    _MAX_FAILURES: int = 3
    _LOCKOUT_SECONDS: int = 30

    def __init__(
        self,
        setup_mode: bool = False,
        service: Optional["SettingsService"] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        # Defect 5: Create as independent top-level window so dragging does not
        # move the Strategy Browser.  Qt.Tool keeps it always-on-top of the app
        # without parenting it into the main-window widget tree.
        super().__init__(None, Qt.Tool)
        self._setup_mode = setup_mode
        self._service = service  # Only used in auth mode
        self.setWindowTitle("Admin Authentication" if not setup_mode else "Set Admin PIN")
        self.setModal(True)
        # BTCAAAAA-87: Use layout-driven sizing — setMinimumWidth as a floor
        # only; let Qt measure the layout for actual width and height.
        # setup_mode adds a Confirm PIN field so needs a taller floor.
        # BTCAAAAA-91: Raised minimum width from 360 → 440 so the full title
        # "Admin Authentication", instruction text, PIN input, and both
        # "Cancel" / "Authenticate" buttons are visible without clipping.
        # BTCAAAAA-202: Lockout countdown label adds height — raise auth floor.
        min_h = 220 if setup_mode else 230
        self.setMinimumWidth(440)
        self.setMinimumHeight(min_h)
        self.setStyleSheet(get_main_stylesheet())

        # Brute-force lockout state (auth mode only)
        self._fail_count: int = 0
        self._lockout_remaining: int = 0
        self._lockout_timer: Optional[QTimer] = None

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 16)

        if setup_mode:
            msg = QLabel("No admin PIN set. Create one to enable admin access.")
        else:
            msg = QLabel("Enter your admin PIN to access restricted settings.")
        msg.setFont(create_font(10))
        msg.setStyleSheet(get_label_style("secondary"))
        msg.setWordWrap(True)
        layout.addWidget(msg)

        self._pin_field = QLineEdit()
        self._pin_field.setEchoMode(QLineEdit.Password)
        self._pin_field.setPlaceholderText("PIN…")
        self._pin_field.setStyleSheet(get_input_field_stylesheet())
        self._pin_field.setFont(create_font(10))
        layout.addWidget(self._pin_field)

        if setup_mode:
            self._confirm_field: Optional[QLineEdit] = QLineEdit()
            self._confirm_field.setEchoMode(QLineEdit.Password)
            self._confirm_field.setPlaceholderText("Confirm PIN…")
            self._confirm_field.setStyleSheet(get_input_field_stylesheet())
            self._confirm_field.setFont(create_font(10))
            self._confirm_field.returnPressed.connect(self.accept)
            layout.addWidget(self._confirm_field)
        else:
            self._confirm_field = None

        # Lockout countdown label (hidden until lockout activates; auth mode only)
        self._lockout_label = QLabel("")
        self._lockout_label.setFont(create_font(9))
        self._lockout_label.setStyleSheet(get_label_style("error"))
        self._lockout_label.setAlignment(Qt.AlignCenter)
        self._lockout_label.hide()
        layout.addWidget(self._lockout_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal
        )
        self._ok_button = buttons.button(QDialogButtonBox.Ok)
        self._ok_button.setText("Authenticate" if not setup_mode else "Set PIN")
        if setup_mode:
            # Setup mode: OK accepts directly (no lockout or validation here).
            self._pin_field.returnPressed.connect(self.accept)
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
        else:
            # Auth mode: wire OK and Return key to _attempt_auth; do NOT connect
            # buttons.accepted so it stays silent.  Cancel still rejects.
            # Disconnect the default QDialogButtonBox OK→accepted internal link
            # by not using accepted at all and blocking the OK click directly.
            self._ok_button.clicked.disconnect()
            self._ok_button.clicked.connect(self._attempt_auth)
            self._pin_field.returnPressed.connect(self._attempt_auth)
            buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # BTCAAAAA-87: Let Qt size the window to fit the layout; the minimum
        # size set above acts as a floor, not the final size.
        QTimer.singleShot(0, self.adjustSize)

    # ------------------------------------------------------------------
    # Brute-force lockout (auth mode only)
    # ------------------------------------------------------------------

    def _attempt_auth(self) -> None:
        """
        Validate the entered PIN via SettingsService.elevate_to_admin().

        - On success: accepts the dialog (QDialog.Accepted).
        - On failure: increments the failure counter; after _MAX_FAILURES
          consecutive failures, locks the dialog for _LOCKOUT_SECONDS.
        - During lockout: guard against keyboard shortcuts bypassing the
          disabled OK button.
        """
        if self._lockout_remaining > 0:
            return  # Lockout active — do nothing (OK should already be disabled)

        if self._service is None:
            # Safety: no service in auth mode — reject to prevent bypass.
            self.reject()
            return

        pin = self._pin_field.text()
        if self._service.elevate_to_admin(pin):
            self.accept()
        else:
            self._fail_count += 1
            self._pin_field.clear()
            if self._fail_count >= self._MAX_FAILURES:
                self._start_lockout()

    def _start_lockout(self) -> None:
        """Disable input and start the countdown timer."""
        self._lockout_remaining = self._LOCKOUT_SECONDS
        self._pin_field.setEnabled(False)
        self._ok_button.setEnabled(False)
        self._lockout_label.setText(
            f"Too many incorrect attempts. Try again in {self._lockout_remaining}s."
        )
        self._lockout_label.show()
        QTimer.singleShot(0, self.adjustSize)

        self._lockout_timer = QTimer(self)
        self._lockout_timer.setInterval(1000)
        self._lockout_timer.timeout.connect(self._on_lockout_tick)
        self._lockout_timer.start()

    def _on_lockout_tick(self) -> None:
        """Decrement countdown; unlock when it reaches zero."""
        self._lockout_remaining -= 1
        if self._lockout_remaining <= 0:
            self._end_lockout()
        else:
            self._lockout_label.setText(
                f"Too many incorrect attempts. Try again in {self._lockout_remaining}s."
            )

    def _end_lockout(self) -> None:
        """Re-enable input after the lockout period expires."""
        if self._lockout_timer is not None:
            self._lockout_timer.stop()
            self._lockout_timer = None
        self._fail_count = 0
        self._lockout_remaining = 0
        self._pin_field.setEnabled(True)
        self._ok_button.setEnabled(True)
        self._lockout_label.hide()
        self._lockout_label.setText("")
        self._pin_field.setFocus()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Stop the lockout timer cleanly when the dialog is closed."""
        if self._lockout_timer is not None:
            self._lockout_timer.stop()
            self._lockout_timer = None
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_pin(self) -> str:
        return self._pin_field.text()

    def get_confirm_pin(self) -> str:
        if self._confirm_field:
            return self._confirm_field.text()
        return ""


# ---------------------------------------------------------------------------
# Settings Dialog
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):
    """
    Main Settings dialog opened via Tools → Settings...

    Tab layout:
      - "API Keys"     — always visible, secret API key fields with Show/Edit
      - "Preferences"  — always visible, non-secret user preferences
      - "Admin"        — HIDDEN until PIN verified; shown/hidden on role change
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        # Defect 5: Use Qt.Tool so the Settings window is an independent
        # top-level window — dragging it does NOT move the Strategy Browser.
        super().__init__(None, Qt.Tool)
        self.setWindowTitle("Settings")
        self.setModal(True)
        # BTCAAAAA-87: Replace fixed pixel size with layout-driven sizing.
        # setMinimumWidth/Height are floors only; adjustSize() (called after
        # _build_ui populates all tabs) lets Qt expand to fit the content,
        # preventing horizontal scrollbars and clipped banners/buttons.
        # BTCAAAAA-90: Raised minimum width floor from 820 to 860px to ensure
        # the widest row ("OpenRouter AI Key: (not set) | Show 10s | Edit")
        # fits with comfortable padding at default size.
        self.setMinimumWidth(860)
        self.setMinimumHeight(600)
        self.setStyleSheet(get_main_stylesheet())

        self._service = SettingsService()

        # Will hold all secret widgets for value retrieval on save
        self._secret_widgets: dict[str, SecretFieldWidget] = {}
        # Plain text fields (non-secret)
        self._plain_fields: dict[str, QLineEdit] = {}
        # Admin section tab widget reference for hide/show
        self._admin_tab_index: int = -1

        self._build_ui()
        self._check_env_permissions()
        # BTCAAAAA-87: Size the window to its content after layout is built.
        # The minimum sizes set above act as floors; adjustSize() lets Qt
        # compute the ideal size so content is never clipped.
        QTimer.singleShot(0, self.adjustSize)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(12)

        # Title
        title = QLabel("Application Settings")
        title.setFont(create_font(14, bold=True))
        title.setStyleSheet(get_panel_title_stylesheet())
        root.addWidget(title)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setFont(create_font(10))
        self._tabs.setStyleSheet(get_tab_widget_stylesheet())
        # BTCAAAAA-92: resize the window when the user switches tabs so that
        # the Admin tab (which has more content than API Keys / Preferences)
        # never clips its contents.  adjustSize() asks Qt to recompute the
        # ideal window size from the current sizeHint of visible widgets.
        self._tabs.currentChanged.connect(lambda _index: QTimer.singleShot(0, self.adjustSize))
        root.addWidget(self._tabs, stretch=1)

        # Tab 1: API Keys (user-editable secret fields)
        self._tabs.addTab(self._build_api_keys_tab(), "API Keys")

        # Tab 2: Preferences (non-secret user settings)
        self._tabs.addTab(self._build_preferences_tab(), "Preferences")

        # Tab 3: Admin (hidden until PIN)
        admin_tab = self._build_admin_tab()
        self._tabs.addTab(admin_tab, "Admin")
        self._admin_tab_index = 2  # Tab 0=API Keys, 1=Preferences, 2=Admin
        self._tabs.setTabVisible(self._admin_tab_index, False)

        # Admin access row
        admin_row = self._build_admin_access_row()
        root.addWidget(admin_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']}; max-height: 1px;")
        root.addWidget(sep)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFont(create_font(10))
        cancel_btn.setStyleSheet(get_secondary_button_stylesheet())
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save && Close")
        save_btn.setFont(create_font(10, bold=True))
        save_btn.setStyleSheet(get_primary_button_stylesheet())
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        root.addLayout(btn_layout)

        QTimer.singleShot(100, lambda: apply_hand_cursor_to_buttons(self))

    # ------------------------------------------------------------------

    def _build_api_keys_tab(self) -> QWidget:
        """User-visible API key settings — secret fields with Show/Edit."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        # BTCAAAAA-90: suppress horizontal scrollbar artifact — content areas
        # in this dialog must never show a horizontal scrollbar.
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(get_transparent_scroll_area_stylesheet())

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # --- API Keys group ---
        api_group = QGroupBox("API Keys")
        api_group.setFont(create_font(10, bold=True))
        api_form = QFormLayout(api_group)
        api_form.setSpacing(10)
        api_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # OpenRouter API key
        self._secret_widgets["OPENROUTER_API_KEY"] = SecretFieldWidget(
            "OPENROUTER_API_KEY", self._service
        )
        api_form.addRow(self._make_label("OpenRouter AI Key:"), self._secret_widgets["OPENROUTER_API_KEY"])

        # LakeAPI key
        self._secret_widgets["LAKEAPI_KEY"] = SecretFieldWidget(
            "LAKEAPI_KEY", self._service
        )
        api_form.addRow(self._make_label("LakeAPI Key:"), self._secret_widgets["LAKEAPI_KEY"])

        # LakeAPI secret
        self._secret_widgets["LAKEAPI_SECRET"] = SecretFieldWidget(
            "LAKEAPI_SECRET", self._service
        )
        api_form.addRow(self._make_label("LakeAPI Secret:"), self._secret_widgets["LAKEAPI_SECRET"])

        layout.addWidget(api_group)
        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ------------------------------------------------------------------

    def _build_preferences_tab(self) -> QWidget:
        """User-editable preferences — non-secret settings."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        # BTCAAAAA-90: suppress horizontal scrollbar artifact.
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(get_transparent_scroll_area_stylesheet())

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # --- Preferences group ---
        pref_group = QGroupBox("Preferences")
        pref_group.setFont(create_font(10, bold=True))
        pref_form = QFormLayout(pref_group)
        pref_form.setSpacing(10)
        pref_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # AI Model
        self._plain_fields["AI_MODEL"] = QLineEdit()
        self._plain_fields["AI_MODEL"].setText(
            self._service.get_with_default("AI_MODEL", "anthropic/claude-4.5-sonnet")
        )
        self._plain_fields["AI_MODEL"].setStyleSheet(get_input_field_stylesheet())
        self._plain_fields["AI_MODEL"].setFont(create_font(10))
        pref_form.addRow(self._make_label("AI Model:"), self._plain_fields["AI_MODEL"])

        # Alert email
        self._plain_fields["ALERT_EMAIL"] = QLineEdit()
        self._plain_fields["ALERT_EMAIL"].setText(
            self._service.get_with_default("ALERT_EMAIL", "")
        )
        self._plain_fields["ALERT_EMAIL"].setPlaceholderText("your@email.com (optional)")
        self._plain_fields["ALERT_EMAIL"].setStyleSheet(get_input_field_stylesheet())
        self._plain_fields["ALERT_EMAIL"].setFont(create_font(10))
        pref_form.addRow(self._make_label("Alert Email:"), self._plain_fields["ALERT_EMAIL"])

        layout.addWidget(pref_group)
        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ------------------------------------------------------------------

    def _build_admin_tab(self) -> QWidget:
        """Admin-only settings: DB, performance, logging.

        IMPORTANT: this method must NOT call self._service.get() or
        get_with_default() for any admin-only key.  Those calls go through
        _check_access() which raises PermissionError for non-admin sessions
        and would crash the dialog on open (BTCAAAAA-82).

        Fields are initialised with static placeholder defaults here and
        populated with live values only after PIN authentication succeeds
        in _populate_admin_fields().
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        # BTCAAAAA-90: suppress horizontal scrollbar artifact.
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(get_transparent_scroll_area_stylesheet())

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Admin badge
        badge = QLabel("ADMIN ACCESS REQUIRED — Changes here affect database and system behaviour.")
        badge.setFont(create_font(9, bold=True))
        badge.setStyleSheet(
            f"color: {COLORS['warning']}; "
            f"background-color: {COLORS['bg_medium']}; "
            f"border: 1px solid {COLORS['warning']}; "
            f"border-radius: 4px; padding: 6px 10px;"
        )
        badge.setWordWrap(True)
        layout.addWidget(badge)

        # --- Database group ---
        db_group = QGroupBox("Database Connection")
        db_group.setFont(create_font(10, bold=True))
        db_form = QFormLayout(db_group)
        db_form.setSpacing(10)
        db_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Use static defaults — do NOT call service.get*() here (role not yet
        # elevated; admin keys raise PermissionError for non-admin users).
        for key, label, placeholder in [
            ("POSTGRES_HOST", "Host:", "localhost"),
            ("POSTGRES_PORT", "Port:", "5432"),
            ("POSTGRES_DB", "Database:", "optimizer_v3"),
            ("POSTGRES_USER", "User:", "optimizer_admin"),
        ]:
            self._plain_fields[key] = QLineEdit()
            self._plain_fields[key].setText(placeholder)
            self._plain_fields[key].setStyleSheet(get_input_field_stylesheet())
            self._plain_fields[key].setFont(create_font(10))
            db_form.addRow(self._make_label(label), self._plain_fields[key])

        # DB password (secret field)
        self._secret_widgets["POSTGRES_PASSWORD"] = SecretFieldWidget(
            "POSTGRES_PASSWORD", self._service
        )
        db_form.addRow(self._make_label("Password:"), self._secret_widgets["POSTGRES_PASSWORD"])

        layout.addWidget(db_group)

        # --- LakeAPI admin group ---
        lake_group = QGroupBox("LakeAPI Admin")
        lake_group.setFont(create_font(10, bold=True))
        lake_form = QFormLayout(lake_group)
        lake_form.setSpacing(10)
        lake_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        for key, label, placeholder in [
            ("LAKEAPI_REGION", "Region:", "eu-west-1"),
            ("LAKEAPI_LIMIT_GB", "Monthly Limit (GB):", "300"),
        ]:
            self._plain_fields[key] = QLineEdit()
            self._plain_fields[key].setText(placeholder)
            self._plain_fields[key].setStyleSheet(get_input_field_stylesheet())
            self._plain_fields[key].setFont(create_font(10))
            lake_form.addRow(self._make_label(label), self._plain_fields[key])

        layout.addWidget(lake_group)

        # --- System group ---
        sys_group = QGroupBox("System")
        sys_group.setFont(create_font(10, bold=True))
        sys_form = QFormLayout(sys_group)
        sys_form.setSpacing(10)
        sys_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._plain_fields["LOG_LEVEL"] = QLineEdit()
        self._plain_fields["LOG_LEVEL"].setText("INFO")
        self._plain_fields["LOG_LEVEL"].setStyleSheet(get_input_field_stylesheet())
        self._plain_fields["LOG_LEVEL"].setFont(create_font(10))
        sys_form.addRow(self._make_label("Log Level:"), self._plain_fields["LOG_LEVEL"])

        layout.addWidget(sys_group)

        # --- Change PIN group ---
        pin_group = QGroupBox("Admin PIN")
        pin_group.setFont(create_font(10, bold=True))
        pin_layout = QVBoxLayout(pin_group)
        pin_layout.setSpacing(8)

        pin_note = QLabel(
            "Change the admin PIN that gates access to this section. "
            "Keep it safe — there is no recovery path."
        )
        pin_note.setFont(create_font(9))
        pin_note.setStyleSheet(get_label_style("muted"))
        pin_note.setWordWrap(True)
        pin_layout.addWidget(pin_note)

        change_pin_btn = QPushButton("Change Admin PIN…")
        change_pin_btn.setFont(create_font(9))
        change_pin_btn.setStyleSheet(get_secondary_button_stylesheet())
        # BTCAAAAA-87: setMinimumWidth instead of setFixedWidth so button
        # can grow with content / DPI scaling.
        change_pin_btn.setMinimumWidth(200)
        change_pin_btn.clicked.connect(self._on_change_pin)
        pin_layout.addWidget(change_pin_btn)

        layout.addWidget(pin_group)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ------------------------------------------------------------------

    def _build_admin_access_row(self) -> QWidget:
        """Row at the bottom of the dialog for admin auth / lock controls."""
        row = QWidget()
        row.setStyleSheet(f"background-color: {COLORS['bg_medium']}; border-radius: 4px;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self._admin_status_label = QLabel("Admin access: locked")
        self._admin_status_label.setFont(create_font(9))
        self._admin_status_label.setStyleSheet(get_label_style("muted"))
        layout.addWidget(self._admin_status_label)

        layout.addStretch()

        # Defect 3: Use clear, unambiguous labels; setMinimumWidth prevents
        # truncation while allowing the button to grow with content.
        self._admin_auth_btn = QPushButton("Unlock Admin")
        self._admin_auth_btn.setFont(create_font(9))
        self._admin_auth_btn.setStyleSheet(get_primary_button_stylesheet(compact=True))
        self._admin_auth_btn.setMinimumWidth(130)
        self._admin_auth_btn.clicked.connect(self._on_admin_auth)
        layout.addWidget(self._admin_auth_btn)

        self._admin_lock_btn = QPushButton("Lock Admin")
        self._admin_lock_btn.setFont(create_font(9))
        self._admin_lock_btn.setStyleSheet(get_danger_button_stylesheet())
        self._admin_lock_btn.setMinimumWidth(110)
        self._admin_lock_btn.hide()
        self._admin_lock_btn.clicked.connect(self._on_admin_lock)
        layout.addWidget(self._admin_lock_btn)

        return row

    # ------------------------------------------------------------------
    # Admin gate logic
    # ------------------------------------------------------------------

    def _on_admin_auth(self) -> None:
        """Prompt for PIN and unlock admin tab if correct."""
        if not self._service.has_admin_pin():
            # First-time setup — no PIN exists yet.
            dlg = AdminPinDialog(setup_mode=True, parent=self)
            if dlg.exec_() != QDialog.Accepted:
                return
            pin = dlg.get_pin()
            confirm = dlg.get_confirm_pin()
            if not pin:
                QMessageBox.warning(self, "PIN Required", "PIN cannot be empty.")
                return
            if pin != confirm:
                QMessageBox.warning(self, "PIN Mismatch", "The two PIN values do not match.")
                return
            try:
                # Grant admin temporarily so set_admin_pin first-run path is allowed.
                # elevate_to_admin_first_run() is only valid before any PIN is set.
                self._service.elevate_to_admin_first_run()
                self._service.set_admin_pin(pin)
                self._reveal_admin_tab()
            except Exception as e:
                self._service.drop_admin()
                QMessageBox.critical(self, "Error", f"Failed to set PIN:\n{e}")
        else:
            # Auth mode — pass service so AdminPinDialog validates internally
            # and applies brute-force lockout after repeated failures.
            dlg = AdminPinDialog(setup_mode=False, service=self._service, parent=self)
            if dlg.exec_() == QDialog.Accepted:
                # Dialog already called elevate_to_admin() on success.
                self._reveal_admin_tab()

    def _on_admin_lock(self) -> None:
        self._service.drop_admin()
        self._conceal_admin_tab()

    def _populate_admin_fields(self) -> None:
        """Load live admin setting values into the admin tab fields.

        Must only be called after PIN authentication (role == ADMIN).
        Using the service before auth raises PermissionError for admin keys.
        """
        admin_plain_defaults = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "optimizer_v3",
            "POSTGRES_USER": "optimizer_admin",
            "LAKEAPI_REGION": "eu-west-1",
            "LAKEAPI_LIMIT_GB": "300",
            "LOG_LEVEL": "INFO",
        }
        for key, default in admin_plain_defaults.items():
            if key in self._plain_fields:
                try:
                    value = self._service.get_with_default(key, default)
                except PermissionError:
                    value = default
                self._plain_fields[key].setText(value)

        # Refresh the secret display for POSTGRES_PASSWORD now that admin is active
        if "POSTGRES_PASSWORD" in self._secret_widgets:
            self._secret_widgets["POSTGRES_PASSWORD"]._refresh_display()

    def _reveal_admin_tab(self) -> None:
        # Populate admin fields with live values now that role is elevated.
        self._populate_admin_fields()
        self._tabs.setTabVisible(self._admin_tab_index, True)
        # BTCAAAAA-92: switch to the Admin tab and let adjustSize expand the
        # window to accommodate its extra content (badge, DB fields, etc.).
        self._tabs.setCurrentIndex(self._admin_tab_index)
        QTimer.singleShot(0, self.adjustSize)
        self._admin_status_label.setText("Admin access: unlocked")
        self._admin_status_label.setStyleSheet(
            f"color: {COLORS['warning']}; font-weight: bold;"
        )
        self._admin_auth_btn.hide()
        self._admin_lock_btn.show()

    def _conceal_admin_tab(self) -> None:
        # Switch away from admin tab before hiding it
        if self._tabs.currentIndex() == self._admin_tab_index:
            self._tabs.setCurrentIndex(0)
        self._tabs.setTabVisible(self._admin_tab_index, False)
        self._admin_status_label.setText("Admin access: locked")
        self._admin_status_label.setStyleSheet(get_label_style("muted"))
        self._admin_auth_btn.show()
        self._admin_lock_btn.hide()

    # ------------------------------------------------------------------
    # Save logic
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        """Collect all field values and persist via SettingsService."""
        errors: list[str] = []

        # Collect user values
        user_values: dict[str, str] = {}
        for key, widget in self._secret_widgets.items():
            if key in ("POSTGRES_PASSWORD",):
                # Skip admin-only secrets if not admin
                if not self._service.is_admin():
                    continue
            user_values[key] = widget.get_value()

        for key, field in self._plain_fields.items():
            user_values[key] = field.text().strip()

        # Persist user settings
        try:
            self._service.save_user_settings(
                {k: v for k, v in user_values.items()
                 if k in ("OPENROUTER_API_KEY", "LAKEAPI_KEY", "LAKEAPI_SECRET",
                           "AI_MODEL", "ALERT_EMAIL")}
            )
        except Exception as e:
            errors.append(f"User settings: {e}")

        # Persist admin settings (only if admin role active)
        if self._service.is_admin():
            admin_values = {
                k: v for k, v in user_values.items()
                if k not in ("OPENROUTER_API_KEY", "LAKEAPI_KEY", "LAKEAPI_SECRET",
                              "AI_MODEL", "ALERT_EMAIL")
            }
            try:
                self._service.save_admin_settings(admin_values)
            except PermissionError:
                pass  # Should not happen — admin is active
            except Exception as e:
                errors.append(f"Admin settings: {e}")

        if errors:
            QMessageBox.warning(
                self,
                "Save Errors",
                "Some settings could not be saved:\n\n" + "\n".join(errors)
            )
        else:
            # Reset all secret widgets to masked display, then close the dialog.
            for widget in self._secret_widgets.values():
                widget.clear_edit()
            self.accept()  # BTCAAAAA-98: close dialog on successful save

    # ------------------------------------------------------------------
    # Change PIN
    # ------------------------------------------------------------------

    def _on_change_pin(self) -> None:
        if not self._service.is_admin():
            QMessageBox.warning(self, "Admin Required", "Unlock admin access first.")
            return
        dlg = AdminPinDialog(setup_mode=True, parent=self)
        dlg.setWindowTitle("Change Admin PIN")
        if dlg.exec_() != QDialog.Accepted:
            return
        pin = dlg.get_pin()
        confirm = dlg.get_confirm_pin()
        if not pin:
            QMessageBox.warning(self, "PIN Required", "PIN cannot be empty.")
            return
        if pin != confirm:
            QMessageBox.warning(self, "PIN Mismatch", "The two PIN values do not match.")
            return
        try:
            self._service.set_admin_pin(pin)
            QMessageBox.information(self, "PIN Changed", "Admin PIN updated successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to change PIN:\n{e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(create_font(10))
        lbl.setStyleSheet(get_label_style("default"))
        return lbl

    def _check_env_permissions(self) -> None:
        """Silently enforce 600 on .env on dialog open."""
        SettingsService._enforce_env_permissions()

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        QTimer.singleShot(200, lambda: apply_hand_cursor_to_buttons(self))
