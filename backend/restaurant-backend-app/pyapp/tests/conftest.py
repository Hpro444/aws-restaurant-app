"""Pytest configuration: add Lambda source packages to sys.path for all tests."""

import sys
from pathlib import Path

_SRC = str(Path(__file__).parent.parent / "src")
if _SRC not in sys.path:
    sys.path.append(_SRC)
