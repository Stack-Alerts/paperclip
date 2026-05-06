"""
Root conftest.py — shared pytest fixtures for headless CI.

Provides a session-scoped QApplication instance so PyQt5 UI tests can run
in a headless environment (DISPLAY=:0 via Xvfb, or QT_QPA_PLATFORM=offscreen).

Individual test modules that define their own `qapp` fixture at module scope
take precedence over this session fixture — that is expected and fine.
"""

import sys
import os
import pytest


# ---------------------------------------------------------------------------
# Qt headless platform selection
# ---------------------------------------------------------------------------

# Allow environment override; default to 'xcb' when a display is available
# or 'offscreen' when no display is set (pure CI headless).
if not os.environ.get("QT_QPA_PLATFORM"):
    if os.environ.get("DISPLAY"):
        # X display is available — use xcb (default Qt backend on Linux)
        pass  # Leave QT_QPA_PLATFORM unset; xcb is the default
    else:
        # No display — force offscreen rendering so tests don't crash
        os.environ["QT_QPA_PLATFORM"] = "offscreen"


# ---------------------------------------------------------------------------
# Session-scoped QApplication fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp_session():
    """Session-scoped QApplication for tests that need a Qt event loop.

    Prefer module-scoped ``qapp`` fixtures in individual test files; this
    session fixture is a fallback for files that don't define their own.
    """
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        yield app
    except ImportError:
        pytest.skip("PyQt5 not available — skipping Qt tests")
