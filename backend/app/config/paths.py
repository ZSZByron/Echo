"""Centralized project path constants.

All modules that need filesystem paths relative to the project root
should import from here instead of computing their own ``_PROJECT_ROOT``.

Usage::

    from app.config.paths import PROJECT_ROOT, SCENES_DIR, ASSETS_DIR
"""
from __future__ import annotations

from pathlib import Path

# app/config/paths.py -> app/ -> backend/ -> UGC/
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent

# Data directories
DATA_DIR: Path = PROJECT_ROOT / "data"
SCENES_DIR: Path = DATA_DIR / "scenes"
ASSETS_DIR: Path = DATA_DIR / "assets"
ASSETS_META_DIR: Path = ASSETS_DIR / "meta"
ASSETS_CANDIDATES_DIR: Path = ASSETS_DIR / "candidates"

# Visual data
VISUAL_DIR: Path = DATA_DIR / "visual"
PROMPTS_PATH: Path = VISUAL_DIR / "prompts.yaml"
STYLE_BIBLE_PATH: Path = VISUAL_DIR / "style_bible.md"
PALETTE_PATH: Path = VISUAL_DIR / "palette.yaml"

# Defaults
DEFAULT_PLAYER_PATH: Path = DATA_DIR / "default_player.json"
GODS_TABLE_PATH: Path = DATA_DIR / "gods" / "gods_table.yaml"
INTERVENTION_TABLE_PATH: Path = DATA_DIR / "rules" / "intervention_table.yaml"

# Graph algorithm test modules
GRAPH_ALGO_DIR: Path = PROJECT_ROOT / "tests" / "graph_algorithm"

# Dimension weight matrix
WEIGHT_MATRIX_PATH: Path = Path(__file__).parent / "weight_matrix.yaml"
