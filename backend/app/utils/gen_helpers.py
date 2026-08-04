"""Shared utilities for image generation, metadata persistence, and lazy imports.

Extracted from ImageGenerator and LocalImageGenerator to eliminate duplication.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

from app.config.paths import ASSETS_META_DIR, GRAPH_ALGO_DIR

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Size parsing
# ---------------------------------------------------------------------------

def parse_size(size_str: str) -> tuple[int, int]:
    """Parse a size string like ``"1024x1024"`` into ``(1024, 1024)``.

    Returns ``(1024, 1024)`` as a safe fallback on any parse error.
    """
    try:
        width, height = size_str.lower().split("x")
        return int(width), int(height)
    except (ValueError, AttributeError):
        return 1024, 1024


# ---------------------------------------------------------------------------
# Metadata persistence
# ---------------------------------------------------------------------------

def save_generation_meta(
    asset_id: str,
    index: int,
    seed: int,
    prompt: str,
    negative_prompt: str,
    size: str,
    provider: str,
    *,
    meta_dir: Path | None = None,
) -> None:
    """Save generation metadata to a JSON file.

    Writes ``{meta_dir}/{asset_id}_{index}.json`` with seed, prompt,
    negative_prompt, size, provider, asset_id, and index.

    Does nothing if *asset_id* is empty.
    """
    if not asset_id:
        return

    if meta_dir is None:
        meta_dir = ASSETS_META_DIR

    meta_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "seed": seed,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "size": size,
        "provider": provider,
        "asset_id": asset_id,
        "index": index,
    }
    filepath = meta_dir / f"{asset_id}_{index}.json"
    filepath.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Saved metadata: %s", filepath)


# ---------------------------------------------------------------------------
# Lazy module imports for graph_algorithm test modules
# ---------------------------------------------------------------------------

def import_cycle_detector():
    """Lazy-import and return the ``cycle_detector`` module.

    Inserts the graph_algorithm directory into ``sys.path`` if needed.
    """
    if str(GRAPH_ALGO_DIR) not in sys.path:
        sys.path.insert(0, str(GRAPH_ALGO_DIR))
    import cycle_detector

    return cycle_detector


def import_topo_sort():
    """Lazy-import and return the ``topo_sort`` module.

    Inserts the graph_algorithm directory into ``sys.path`` if needed.
    """
    if str(GRAPH_ALGO_DIR) not in sys.path:
        sys.path.insert(0, str(GRAPH_ALGO_DIR))
    import topo_sort

    return topo_sort
