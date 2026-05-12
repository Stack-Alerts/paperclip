"""Ensure src/ is on sys.path before any blast_radius test module is imported."""

import sys
from pathlib import Path

_src = str(Path(__file__).resolve().parents[2] / "src")
sys.path.insert(0, _src)
