"""Background removal utility for the Echo cyberpunk terminal demo.

Uses `rembg` (onnxruntime-based) for background removal.
rembg is a LAZY dependency -- it is imported inside the function so that
this module can be imported even when rembg is not installed.

Usage::

    success = remove_background("input.png", "output.png")
    if not success:
        print("rembg not installed or failed")
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def remove_background(input_path: str, output_path: str) -> bool:
    """Remove background from an image, outputting a transparent PNG.

    Args:
        input_path: Path to the source image file.
        output_path: Path to write the transparent PNG output.

    Returns:
        True if background removal succeeded, False if rembg is not
        installed or an error occurred.
    """
    try:
        from rembg import remove  # noqa: WPS433
    except ImportError:
        logger.warning(
            "rembg is not installed. "
            "Install it with: pip install rembg[gpu]  # or rembg for CPU-only"
        )
        return False

    try:
        from PIL import Image  # noqa: WPS433

        src = Path(input_path)
        if not src.exists():
            logger.error("Input file not found: %s", input_path)
            return False

        img = Image.open(src)
        output = remove(img)

        # Ensure output directory exists
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # Save as PNG with alpha channel
        output.save(out, "PNG")
        return True
    except Exception as exc:
        logger.error("Background removal failed: %s", exc)
        return False