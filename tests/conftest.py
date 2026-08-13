"""Shared fixtures for the HarnessProbe test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the in-tree package is importable when tests run without install.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def tmp_state(tmp_path: Path) -> Path:
    """A throwaway state-file path."""
    return tmp_path / ".harnessprobe-last.json"
