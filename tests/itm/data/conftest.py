"""
conftest.py for ITM Section B data tests.

Ensures ``src/`` is on sys.path for all data-layer test imports.
"""
import sys
import os

_SRC_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src")
)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
