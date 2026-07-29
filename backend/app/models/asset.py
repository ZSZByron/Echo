"""Asset models for visual generation pipeline."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, computed_field, field_validator


class AssetStatus(str, Enum):
    """Lifecycle status of a visual asset."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    CANDIDATES_READY = "candidates_ready"
    SELECTED = "selected"


class AssetType(str, Enum):
    """Type of generated visual asset."""

    BACKGROUND = "background"
    OBJECT = "object"


class Candidate(BaseModel):
    """A single candidate image for multi-candidate generation."""
    index: int
    seed: int
    file_path: Optional[str] = None
    url: Optional[str] = None
    score: Optional[float] = None


class SceneStyleProfile(BaseModel):
    """Structured style profile for scene consistency."""
    palette: list[str] = Field(default_factory=list)
    lighting: dict = Field(default_factory=dict)
    material: list[str] = Field(default_factory=list)
    rendering: dict = Field(default_factory=dict)
    atmosphere: dict = Field(default_factory=dict)


class Asset(BaseModel):
    """A single visual asset tracked in the manifest.

    Attributes:
        id: Unique asset identifier (e.g. ``temple_ruins_bg``).
        type: Background or object asset.
        name: Human-readable name.
        prompt: Generation prompt text.
        negative_prompt: Negative prompt for generation.
        status: Review lifecycle status.
        generation_status: Pipeline status (pending/generating/completed/failed).
        file_path: Path to generated file once available.
        parent_scene: Scene ID this asset belongs to.
        seed: Optional generation seed.
        created_at: UTC timestamp of creation.
        approved_at: UTC timestamp of approval.
        reviewer_note: Optional note from reviewer.
        error_message: Optional error message on failure.
    """

    id: str
    type: AssetType
    name: str
    prompt: str = ""
    negative_prompt: str = ""
    status: AssetStatus = AssetStatus.PENDING
    generation_status: str = "pending"
    file_path: Optional[str] = None
    parent_scene: str
    seed: Optional[int] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    approved_at: Optional[datetime] = None
    reviewer_note: Optional[str] = None
    error_message: Optional[str] = None
    candidates: list[Candidate] = Field(default_factory=list)
    selected_candidate_index: Optional[int] = None
    reference_asset_ids: list[str] = Field(default_factory=list)
    style_profile: Optional[SceneStyleProfile] = None

    # Embedded LOD views structure
    views: Optional[Dict[str, Dict[str, Any]]] = None  # {"far": {...}, "mid": {...}, "near": {...}}
    lod_level: Optional[str] = None  # Currently active LOD level ("far" | "mid" | "near")

    # Puzzle and spatial metadata
    puzzle_role: Optional[str] = None  # "clue" | "consumable" | "reward" | "obstacle"
    parent_object: Optional[str] = None  # Parent object ID if this is derived from another object
    depth: Optional[str] = None  # "near" | "mid" | "mid_far" | "far"

    @field_validator("candidates", "reference_asset_ids", mode="before")
    @classmethod
    def _coerce_none_to_list(cls, v):
        if v is None:
            return []
        return v

    @field_validator("selected_candidate_index", "style_profile", mode="before")
    @classmethod
    def _coerce_undefined_to_none(cls, v):
        if v == "" or v == "null":
            return None
        return v

    def get_view(self, lod_level: str) -> Dict[str, Any] | None:
        """Get view data for specific LOD level.

        Args:
            lod_level: "far" | "mid" | "near"

        Returns:
            View dict for that level, or None if not exists
        """
        if self.views is None:
            return None
        return self.views.get(lod_level)

    def set_view(self, lod_level: str, **fields: Any) -> None:
        """Update view data for specific LOD level.

        Args:
            lod_level: "far" | "mid" | "near"
            **fields: View fields to update (prompt, file_path, status, etc.)
        """
        if self.views is None:
            self.views = {}

        if lod_level not in self.views:
            self.views[lod_level] = {}

        self.views[lod_level].update(fields)

    @computed_field  # type: ignore[misc]
    @property
    def url(self) -> Optional[str]:
        if (
            self.selected_candidate_index is not None
            and 0 <= self.selected_candidate_index < len(self.candidates)
        ):
            candidate = self.candidates[self.selected_candidate_index]
            if candidate.url:
                return candidate.url

        if not self.file_path:
            return None

        try:
            path = Path(self.file_path)
            if not path.is_absolute():
                return None
            parts = path.parts
            try:
                assets_index = parts.index("assets")
                if assets_index > 0 and parts[assets_index - 1] == "data":
                    filename = path.name
                    return f"/assets/{filename}"
            except ValueError:
                return None
        except (OSError, ValueError):
            return None

        return None
