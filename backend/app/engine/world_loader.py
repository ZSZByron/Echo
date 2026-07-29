"""Load YAML world data into typed Pydantic objects."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from app.models.world import GameObject, GodKing, Scene


class WorldLoader:
    """Loads world data from YAML/JSON files."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            # engine/ -> app/ -> backend/ -> UGC/ -> data/
            data_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"
        self._data_dir = data_dir

    def load_scene(self, scene_id: str) -> Scene:
        """Load a scene from YAML."""
        path = self._data_dir / "scenes" / f"{scene_id}.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return Scene.model_validate(data)

    def load_gods(self) -> list[GodKing]:
        """Load all gods from YAML."""
        path = self._data_dir / "gods" / "gods_table.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return [GodKing.model_validate(g) for g in data["gods"]]

    def load_intervention_table(self) -> dict[str, str]:
        """Load intervention rules: object_id -> god_id mapping."""
        path = self._data_dir / "rules" / "intervention_table.yaml"
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return {
            rule["object_id"]: rule["protected_by"]
            for rule in data["intervention_rules"]
        }

    def load_default_player_data(self) -> dict[str, Any]:
        """Load default player state from JSON."""
        path = self._data_dir / "default_player.json"
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data
