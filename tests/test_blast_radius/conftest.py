"""Ensure src/ is on sys.path before any blast_radius test module is imported.

Avoids namespace shadowing by tests/touch_index/__init__.py, which pytest
puts on sys.path[0] before conftest loading.  We forcibly insert src/ at
position 0 to override that.
"""
import sys
from pathlib import Path

_src = str(Path(__file__).resolve().parents[2] / "src")
# Always insert at front — even when pytest has already added src via
# pyproject.toml pythonpath, the tests/ directory may appear earlier.
sys.path.insert(0, _src)
