"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

import pytest

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def default_safe_z() -> float:
    """Standard safe Z height."""
    return 50.0


@pytest.fixture
def default_feedrate() -> int:
    """Standard feedrate in mm/min."""
    return 3000
