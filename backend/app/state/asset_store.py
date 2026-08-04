"""JSON-file-backed asset manifest store."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from app.config.paths import (
    PROJECT_ROOT as _PROJECT_ROOT,
    PROMPTS_PATH as _PROMPTS_PATH,
    SCENES_DIR as _SCENES_DIR,
)
from app.models.asset import Asset, AssetStatus, AssetType


class InvalidTransitionError(Exception):
    """Raised when an asset status transition is not allowed."""


def _load_prompts() -> dict[str, Any]:
    """Load ``data/visual/prompts.yaml`` if present, else return ``{}``.

    Returns a dict shaped as ``{"background": {...}, "objects": {...}}``.
    Missing file or unreadable content yields an empty dict — callers
    fall back to scene YAML descriptions.
    """
    if not _PROMPTS_PATH.exists():
        return {}
    with open(_PROMPTS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# Allowed status transitions: (current, target) pairs
_ALLOWED_TRANSITIONS: set[tuple[AssetStatus, AssetStatus]] = {
    (AssetStatus.PENDING, AssetStatus.GENERATING),
    (AssetStatus.GENERATING, AssetStatus.COMPLETED),
    (AssetStatus.GENERATING, AssetStatus.FAILED),
    (AssetStatus.COMPLETED, AssetStatus.APPROVED),
    (AssetStatus.COMPLETED, AssetStatus.REJECTED),
    (AssetStatus.REJECTED, AssetStatus.PENDING),
    (AssetStatus.FAILED, AssetStatus.PENDING),
    (AssetStatus.FAILED, AssetStatus.GENERATING),
    (AssetStatus.APPROVED, AssetStatus.PENDING),
    (AssetStatus.GENERATING, AssetStatus.CANDIDATES_READY),
    (AssetStatus.CANDIDATES_READY, AssetStatus.SELECTED),
    (AssetStatus.SELECTED, AssetStatus.APPROVED),
    (AssetStatus.SELECTED, AssetStatus.REJECTED),
    (AssetStatus.CANDIDATES_READY, AssetStatus.GENERATING),
}


class AssetStore:
    """CRUD interface over ``data/assets/manifest.json``."""

    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = _PROJECT_ROOT / "data" / "assets" / "manifest.json"
        self._path = path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_assets(self) -> list[Asset]:
        """Return all assets in the manifest."""
        data = self._load()
        return [Asset.model_validate(a) for a in data.get("assets", [])]

    def get_asset(self, asset_id: str) -> Asset | None:
        """Return a single asset by ID, or ``None``."""
        for asset in self.list_assets():
            if asset.id == asset_id:
                return asset
        return None

    def update_asset(self, asset_id: str, **fields: Any) -> Asset:
        """Update an asset's fields with transition validation.

        If ``status`` is among *fields* and differs from the current
        status, ``_transition`` is called to validate the change.

        Returns the updated ``Asset``.
        Raises ``KeyError`` if the asset is not found.
        Raises ``InvalidTransitionError`` for disallowed transitions.
        """
        data = self._load()
        assets_raw: list[dict[str, Any]] = data.get("assets", [])

        for idx, raw in enumerate(assets_raw):
            if raw["id"] == asset_id:
                current = Asset.model_validate(raw)

                new_status = fields.get("status")
                if new_status is not None and new_status != current.status:
                    if isinstance(new_status, str):
                        new_status = AssetStatus(new_status)
                    self._transition(current.status, new_status)

                # Apply updates
                merged = {**raw, **fields}
                # Sync generation_status when status changes to generating/completed/failed
                if "status" in fields:
                    status_val = (
                        fields["status"].value
                        if isinstance(fields["status"], AssetStatus)
                        else fields["status"]
                    )
                    if status_val == "generating":
                        merged["generation_status"] = "generating"
                    elif status_val == "completed":
                        merged["generation_status"] = "completed"
                    elif status_val == "failed":
                        merged["generation_status"] = "failed"
                # Set approved_at automatically when transitioning to approved
                if (
                    "status" in fields
                    and (
                        fields["status"] == AssetStatus.APPROVED
                        or fields["status"] == "approved"
                    )
                    and merged.get("approved_at") is None
                ):
                    merged["approved_at"] = datetime.now(timezone.utc).isoformat()

                updated = Asset.model_validate(merged)
                assets_raw[idx] = updated.model_dump(mode="json")
                data["assets"] = assets_raw
                data["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save(data)
                return updated

        raise KeyError(f"Asset not found: {asset_id}")

    def init_manifest(self) -> list[Asset]:
        """Scan ``data/scenes/*.yaml`` and build the manifest.

        Idempotent: if the manifest already contains assets, only missing
        scene assets are added — existing entries are never overwritten.
        """
        existing = {a.id for a in self.list_assets()}
        new_assets: list[Asset] = []

        # Load prompt templates once (shared across scenes).
        prompts_data = _load_prompts()

        for yaml_path in sorted(_SCENES_DIR.glob("*.yaml")):
            with open(yaml_path, encoding="utf-8") as f:
                scene_data = yaml.safe_load(f)

            scene_id: str = scene_data["scene_id"]
            scene_name: str = scene_data.get("name", scene_id)

            # Background asset
            bg_id = f"{scene_id}_bg"
            if bg_id not in existing:
                bg_prompt = prompts_data.get("background", {}).get(bg_id, {})
                new_assets.append(
                    Asset(
                        id=bg_id,
                        type=AssetType.BACKGROUND,
                        name=scene_name,
                        prompt=bg_prompt.get("full_prompt", ""),
                        negative_prompt=bg_prompt.get("negative", ""),
                        parent_scene=scene_id,
                    )
                )

            # Object assets
            for obj in scene_data.get("accessible_objects", []):
                obj_id = obj["id"]
                asset_id = f"{scene_id}_{obj_id}"
                if asset_id not in existing:
                    obj_prompt = prompts_data.get("objects", {}).get(asset_id, {})
                    new_assets.append(
                        Asset(
                            id=asset_id,
                            type=AssetType.OBJECT,
                            name=obj.get("name", obj_id),
                            prompt=obj_prompt.get("full_prompt", obj.get("description", "")),
                            negative_prompt=obj_prompt.get("negative", ""),
                            parent_scene=scene_id,
                        )
                    )

        if new_assets:
            data = self._load()
            data.setdefault("assets", [])
            data["assets"].extend(a.model_dump(mode="json") for a in new_assets)
            data["version"] = "1.0"
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save(data)

        return self.list_assets()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        """Load the manifest JSON, returning an empty skeleton if missing."""
        if not self._path.exists():
            return {"assets": [], "version": "1.0", "updated_at": ""}
        with open(self._path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data: dict[str, Any]) -> None:
        """Write the manifest JSON, creating parent dirs as needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _transition(
        self, current: AssetStatus, target: AssetStatus
    ) -> None:
        """Validate that *current* → *target* is an allowed transition."""
        if (current, target) not in _ALLOWED_TRANSITIONS:
            raise InvalidTransitionError(
                f"Disallowed status transition: {current.value} → {target.value}"
            )
