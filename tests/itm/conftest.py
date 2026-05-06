"""
conftest.py for ITM tests.

Ensures ``src/`` is on sys.path so that both import styles work:
  - ``from itm.domain.entities import ...``  (pre-existing tests)
  - ``from src.itm.domain.entities import ...``  (new tests)
"""

import sys
import os

# Add <project_root>/src to sys.path so "from itm.domain..." imports resolve.
_SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "src")
_SRC_DIR = os.path.normpath(_SRC_DIR)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
