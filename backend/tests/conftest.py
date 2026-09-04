"""
Pytest Configuration and Shared Fixtures
"""

import os
import tempfile

import pytest
from pathlib import Path


@pytest.fixture(autouse=True, scope="session")
def _session_a1_store_isolation():
    """Process-wide guard: pin A1_STORE_PATH to a throwaway session tmp file.

    Rationale: background threads (visual-bg pregenerate) can outlive a
    per-test monkeypatch fixture and fire ``_save_store()`` AFTER teardown,
    which once wiped the user's real ``backend/data/a1_store.json`` with an
    empty skeleton. A session-scoped env var covers every code path in the
    test process - including zombie threads - for the whole run.
    """
    old = os.environ.get("A1_STORE_PATH")
    tmpdir = tempfile.mkdtemp(prefix="a1_store_session_")
    os.environ["A1_STORE_PATH"] = str(Path(tmpdir) / "a1_store.json")
    yield
    if old is None:
        os.environ.pop("A1_STORE_PATH", None)
    else:
        os.environ["A1_STORE_PATH"] = old


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
