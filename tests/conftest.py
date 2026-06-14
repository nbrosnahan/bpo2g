# tests/conftest.py
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def omron_csv_path() -> Path:
    """A real Omron BP export CSV with the canonical header and three rows."""
    return FIXTURES / "Your Requested OMRON Report from Jan 01 2025 to Jan 22 2025.csv"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES
