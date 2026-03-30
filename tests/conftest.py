# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_data():
    return {
        "id": 1,
        "name": "test"
    }

@pytest.fixture
def data_file_path():
    return Path(__file__).parent / "fixtures" / "sample.json"
