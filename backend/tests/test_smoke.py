"""
Smoke Tests - Verify Toolchain Functionality
Ensures all quality tools are properly configured and working
"""

from pathlib import Path


def test_project_structure() -> None:
    """Verify essential project directories exist"""
    root = Path(__file__).parent.parent
    required = [
        "app",
        "app/api",
        "app/engine",
        "app/ai",
        "app/models",
        "app/state",
        "tests",
        "tests/unit",
        "tests/features",
    ]

    for path in required:
        full_path = root / path
        assert full_path.exists(), f"Required directory missing: {path}"
        assert full_path.is_dir(), f"Path is not a directory: {path}"


def test_config_files_exist() -> None:
    """Verify essential configuration files exist"""
    root = Path(__file__).parent.parent
    required = [
        "pyproject.toml",
        ".env.example",
        "app/__init__.py",
        "app/main.py",
    ]

    for filename in required:
        filepath = root / filename
        assert filepath.exists(), f"Required config missing: {filename}"
        assert filepath.is_file(), f"Path is not a file: {filename}"


def test_pyproject_toml_content() -> None:
    """Verify pyproject.toml contains required configurations"""
    root = Path(__file__).parent.parent
    pyproject = root / "pyproject.toml"
    content = pyproject.read_text()

    # Check for essential dependencies
    required_deps = [
        "fastapi",
        "uvicorn",
        "httpx",
        "openai",
        "anthropic",
        "pydantic",
        "sqlalchemy",
    ]

    for dep in required_deps:
        assert dep in content, f"Missing dependency: {dep}"

    # Check for quality tools
    quality_tools = ["ruff", "mypy", "pytest", "mutmut"]
    for tool in quality_tools:
        assert tool in content, f"Missing quality tool: {tool}"

    # Check for quality gate configurations
    assert "max-complexity" in content, "Missing mccabe complexity config"
    assert "fail_under" in content, "Missing coverage threshold config"
    assert "strict = true" in content, "Missing mypy strict mode config"


def test_main_py_import() -> None:
    """Verify main.py can be imported without errors"""
    import sys
    from pathlib import Path

    root = Path(__file__).parent.parent
    sys.path.insert(0, str(root))

    try:
        import app.main  # noqa: F401
    except ImportError as e:
        assert False, f"Failed to import app.main: {e}"


def test_env_example_completeness() -> None:
    """Verify .env.example contains all provider configurations."""
    root = Path(__file__).parent.parent
    env_example = root / ".env.example"
    content = env_example.read_text(encoding="utf-8")

    required_providers = [
        "OPENAI_",
        "ANTHROPIC_",
        "DEEPSEEK_",
        "QWEN_",
        "KIMI_",
        "GLM_",
    ]

    for provider in required_providers:
        assert f"{provider}API_KEY" in content, f"Missing {provider}API_KEY"
        assert f"{provider}BASE_URL" in content, f"Missing {provider}BASE_URL"
        assert f"{provider}MODEL" in content, f"Missing {provider}MODEL"

    # Check for ACTIVE_PROVIDER
    assert "ACTIVE_PROVIDER=" in content, "Missing ACTIVE_PROVIDER variable"
