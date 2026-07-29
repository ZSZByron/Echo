"""Unit tests for bg_remover module."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

from app.ai.bg_remover import remove_background


# -- rembg not installed --


def test_remove_background_returns_false_when_no_rembg() -> None:
    """Returns False when rembg is not installed (ImportError caught)."""
    real_rembg = sys.modules.pop("rembg", None)
    try:
        result = remove_background("fake.png", "out.png")
        assert result is False
    finally:
        if real_rembg is not None:
            sys.modules["rembg"] = real_rembg


# -- file not found --


def test_remove_background_missing_file(tmp_path) -> None:
    """Returns False when input file does not exist."""
    _install_fake_rembg()
    try:
        result = remove_background("/nonexistent/path/img.png", str(tmp_path / "out.png"))
        assert result is False
    finally:
        _uninstall_fake_rembg()


# -- happy path --


def test_remove_background_success(tmp_path) -> None:
    """When rembg and PIL are available, returns True and saves PNG."""
    input_file = tmp_path / "input.png"
    input_file.write_bytes(b"\x89PNG\r\n\x1a\n")
    mock_output_img = MagicMock()

    _install_fake_rembg()
    try:
        with patch("PIL.Image.open", return_value=MagicMock()):
            with patch("rembg.remove", return_value=mock_output_img):
                result = remove_background(
                    str(input_file), str(tmp_path / "output.png")
                )
        assert result is True
        mock_output_img.save.assert_called_once()
    finally:
        _uninstall_fake_rembg()


def test_remove_background_creates_output_dir(tmp_path) -> None:
    """Creates output directory if it does not exist."""
    input_file = tmp_path / "input.png"
    input_file.write_bytes(b"\x89PNG\r\n\x1a\n")
    output_path = str(tmp_path / "nested" / "deep" / "output.png")
    mock_output_img = MagicMock()

    _install_fake_rembg()
    try:
        with patch("PIL.Image.open", return_value=MagicMock()):
            with patch("rembg.remove", return_value=mock_output_img):
                result = remove_background(str(input_file), output_path)
        assert result is True
        assert (tmp_path / "nested" / "deep").exists()
    finally:
        _uninstall_fake_rembg()


def test_remove_background_exception_returns_false(tmp_path) -> None:
    """Returns False when processing raises an exception."""
    input_file = tmp_path / "input.png"
    input_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    _install_fake_rembg()
    try:
        with patch("PIL.Image.open", return_value=MagicMock()):
            with patch("rembg.remove", side_effect=RuntimeError("OOM")):
                result = remove_background(
                    str(input_file), str(tmp_path / "output.png")
                )
        assert result is False
    finally:
        _uninstall_fake_rembg()


# -- Helpers --


_fake_rembg_saved: object = None


_fake_pil_saved: dict[str, object] = {}
_fake_rembg_saved: object = None


def _install_fake_rembg() -> None:
    """Install fake rembg + PIL modules into sys.modules."""
    global _fake_pil_saved, _fake_rembg_saved
    # Save and fake PIL
    for key in ("PIL", "PIL.Image"):
        _fake_pil_saved[key] = sys.modules.pop(key, None)
    pil_mod = types.ModuleType("PIL")
    image_mod = types.ModuleType("PIL.Image")
    image_mod.open = MagicMock()  # placeholder; patch overrides it
    pil_mod.Image = image_mod  # type: ignore[attr-defined]
    sys.modules["PIL"] = pil_mod
    sys.modules["PIL.Image"] = image_mod
    # Save and fake rembg
    _fake_rembg_saved = sys.modules.pop("rembg", None)
    mod = types.ModuleType("rembg")
    mod.remove = MagicMock()  # type: ignore[attr-defined]
    sys.modules["rembg"] = mod


def _uninstall_fake_rembg() -> None:
    """Restore original rembg + PIL in sys.modules."""
    global _fake_pil_saved, _fake_rembg_saved
    for key in ("PIL", "PIL.Image"):
        sys.modules.pop(key, None)
        saved = _fake_pil_saved.get(key)
        if saved is not None:
            sys.modules[key] = saved  # type: ignore[assignment]
    _fake_pil_saved.clear()
    if "rembg" in sys.modules:
        del sys.modules["rembg"]
    if _fake_rembg_saved is not None:
        sys.modules["rembg"] = _fake_rembg_saved  # type: ignore[assignment]
    _fake_rembg_saved = None
