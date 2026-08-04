"""Template-based prompt builder for asset image generation.

Assembles 8-layer prompts from template fragments stored in YAML data files.
Layers: World, Location, Camera, Subject, GameplayFunction, InteractionDetails, Material, Lighting
"""
from __future__ import annotations

from typing import Any, Dict

import yaml

from app.config.paths import (
    PALETTE_PATH as _PALETTE_PATH,
    PROMPTS_PATH as _PROMPTS_PATH,
    SCENES_DIR as _SCENES_DIR,
    STYLE_BIBLE_PATH as _STYLE_BIBLE_PATH,
)


class PromptBuilder:
    """Builds image generation prompts from template fragments + data injection."""

    def __init__(self) -> None:
        self._prompts_data = self._load_prompts()
        self._palette_data = self._load_palette()

    # ------------------------------------------------------------------
    # Data loaders
    # ------------------------------------------------------------------

    def _load_prompts(self) -> dict:
        with open(_PROMPTS_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_palette(self) -> dict:
        with open(_PALETTE_PATH, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_scene(self, scene_id: str) -> dict:
        path = _SCENES_DIR / f"{scene_id}.yaml"
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        asset_id: str,
        lod_level: str,
        context: Dict[str, Any] | None = None,
    ) -> str:
        """Build a complete 8-layer prompt for the given asset and LOD level.

        Parameters
        ----------
        asset_id:
            Composite identifier ``"{scene_id}_{object_id}"`` matching
            keys in ``prompts.yaml`` under ``objects``.
        lod_level:
            One of ``far``, ``mid``, ``near``.
        context:
            Optional override dict. Supported keys shadow the corresponding
            layer values (e.g. ``world``, ``camera``, ``material``, …).

        Returns
        -------
        str
            Comma-separated prompt string. Partial prompts are returned
            gracefully when some layers are missing data.
        """
        if context is None:
            context = {}

        # Parse asset_id: "{scene_id}_{object_id}"
        # Scene IDs may contain underscores (e.g. temple_ruins), so we
        # resolve by finding the matching scene YAML file on disk.
        scene_id, object_id = self._parse_asset_id(asset_id)
        if not scene_id:
            return ""

        # Load data sources
        segments = self._prompts_data.get("segments", {})
        style_words = self._prompts_data.get("style_words", "")
        camera_templates = self._prompts_data.get("camera_templates", {})
        objects = self._prompts_data.get("objects", {})
        obj_data = objects.get(asset_id, {})

        # Load scene data (gracefully handle missing scene file)
        scene_data: dict = {}
        if _SCENES_DIR.is_dir():
            scene_path = _SCENES_DIR / f"{scene_id}.yaml"
            if scene_path.exists():
                scene_data = self._load_scene(scene_id)

        # ------------------------------------------------------------------
        # Layer 1 – World
        # ------------------------------------------------------------------
        world = context.get("world", segments.get("world_prefix", ""))

        # ------------------------------------------------------------------
        # Layer 2 – Location
        # ------------------------------------------------------------------
        location = context.get("location", segments.get("space_prefix", ""))

        # ------------------------------------------------------------------
        # Layer 3 – Camera
        # ------------------------------------------------------------------
        camera = context.get(
            "camera",
            camera_templates.get(lod_level, camera_templates.get("mid", "")),
        )

        # ------------------------------------------------------------------
        # Layer 4 – Subject
        # ------------------------------------------------------------------
        subject = self._resolve_subject(
            obj_data, lod_level, scene_data, object_id
        )
        subject = context.get("subject", subject)

        # ------------------------------------------------------------------
        # Layer 5 – Gameplay Function
        # ------------------------------------------------------------------
        gameplay = self._resolve_gameplay(scene_data, object_id)
        gameplay = context.get("gameplay", gameplay)

        # ------------------------------------------------------------------
        # Layer 6 – Interaction Details
        # ------------------------------------------------------------------
        interaction = self._resolve_interaction(scene_data, object_id)
        interaction = context.get("interaction", interaction)

        # ------------------------------------------------------------------
        # Layer 7 – Material
        # ------------------------------------------------------------------
        material = context.get("material", segments.get("material_prefix", ""))

        # ------------------------------------------------------------------
        # Layer 8 – Lighting & Style
        # ------------------------------------------------------------------
        lighting = context.get("lighting", style_words)

        # ------------------------------------------------------------------
        # Assemble
        # ------------------------------------------------------------------
        layers = [world, location, camera, subject, gameplay, interaction, material, lighting]

        return ", ".join(layer for layer in layers if layer)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_asset_id(asset_id: str) -> tuple[str, str]:
        """Split *asset_id* into ``(scene_id, object_id)``.

        Scene IDs may contain underscores (e.g. ``temple_ruins``), so
        a naive ``split("_", 1)`` is not sufficient.  Instead we probe
        the scenes directory for an existing YAML file whose name is a
        prefix of *asset_id*.
        """
        if not _SCENES_DIR.is_dir():
            # Fallback: simple split
            parts = asset_id.split("_", 1)
            return (parts[0], parts[1]) if len(parts) == 2 else ("", "")

        # Collect available scene IDs (stem without extension)
        available = {p.stem for p in _SCENES_DIR.glob("*.yaml")}

        # Try progressively longer prefixes until we find a match
        for i, ch in enumerate(asset_id):
            if ch == "_":
                candidate = asset_id[:i]
                if candidate in available:
                    return (candidate, asset_id[i + 1 :])

        return ("", "")

    @staticmethod
    def _find_scene_object(scene_data: dict, object_id: str) -> dict | None:
        """Look up an accessible_object entry by its ``id``."""
        for obj in scene_data.get("accessible_objects", []):
            if obj.get("id") == object_id:
                return obj
        return None

    def _resolve_subject(
        self,
        obj_data: dict,
        lod_level: str,
        scene_data: dict,
        object_id: str,
    ) -> str:
        """Resolve the subject description from prompts.yaml or scene YAML."""
        # Prefer prompts.yaml object-level LOD
        lod_map = obj_data.get("lod", {})
        if lod_level in lod_map:
            return lod_map[lod_level]

        # Fall back to full_prompt in prompts.yaml
        if "full_prompt" in obj_data:
            return obj_data["full_prompt"]

        # Fall back to scene YAML accessible_objects LOD
        scene_obj = self._find_scene_object(scene_data, object_id)
        if scene_obj:
            lod_data = scene_obj.get("lod", {})
            if lod_level in lod_data:
                return lod_data[lod_level]
            return scene_obj.get("description", "")

        return ""

    @classmethod
    def _resolve_gameplay(cls, scene_data: dict, object_id: str) -> str:
        """Extract puzzle_role as gameplay function hint."""
        scene_obj = cls._find_scene_object(scene_data, object_id)
        if scene_obj:
            role = scene_obj.get("puzzle_role", "")
            if role:
                return f"gameplay role: {role}"
        return ""

    @classmethod
    def _resolve_interaction(cls, scene_data: dict, object_id: str) -> str:
        """Extract new_assets_hint as interaction context."""
        scene_obj = cls._find_scene_object(scene_data, object_id)
        if scene_obj:
            hint = scene_obj.get("new_assets_hint", "")
            if hint:
                return f"interaction context: {hint}"
        return ""
