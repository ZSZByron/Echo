"""
Pytest Configuration and Shared Fixtures
"""

import pytest
from pathlib import Path


@pytest.fixture
def project_root() -> Path:
    """Provide project root directory path"""
    return Path(__file__).parent.parent


@pytest.fixture
def backend_root(project_root: Path) -> Path:
    """Provide backend directory path"""
    return project_root


@pytest.fixture
def tests_dir(backend_root: Path) -> Path:
    """Provide tests directory path"""
    return backend_root / "tests"


@pytest.fixture
def app_dir(backend_root: Path) -> Path:
    """Provide app directory path"""
    return backend_root / "app"
