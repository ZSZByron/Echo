"""Asset models for visual generation pipeline."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

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


class AssetClassification(str, Enum):
    """资产分类 — 由来源图决定。"""

    STORY = "story"  # 来自 StoryGraph
    EVENT = "event"  # 来自 EventGraph
    ENVIRONMENT = "environment"  # 无明确来源


class Candidate(BaseModel):
    """A single candidate image for multi-candidate generation."""
    index: int
    seed: int
    file_path: str | None = None
    url: str | None = None
    score: float | None = None


class SceneStyleProfile(BaseModel):
    """Structured style profile for scene consistency."""
    palette: list[str] = Field(default_factory=list)
    lighting: dict[str, Any] = Field(default_factory=dict)
    material: list[str] = Field(default_factory=list)
    rendering: dict[str, Any] = Field(default_factory=dict)
    atmosphere: dict[str, Any] = Field(default_factory=dict)


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
    file_path: str | None = None
    parent_scene: str
    seed: int | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    approved_at: datetime | None = None
    reviewer_note: str | None = None
    error_message: str | None = None
    candidates: list[Candidate] = Field(default_factory=list)
    selected_candidate_index: int | None = None
    reference_asset_ids: list[str] = Field(default_factory=list)
    style_profile: SceneStyleProfile | None = None

    # Embedded LOD views structure
    views: dict[str, dict[str, Any]] | None = None  # {"far": {...}, "mid": {...}, "near": {...}}
    lod_level: str | None = None  # Currently active LOD level ("far" | "mid" | "near")

    # Puzzle and spatial metadata
    puzzle_role: str | None = None  # "clue" | "consumable" | "reward" | "obstacle"
    parent_object: str | None = None  # Parent object ID if this is derived from another object
    depth: str | None = None  # "near" | "mid" | "mid_far" | "far"

    # Asset classification and graph node links
    classification: AssetClassification = AssetClassification.ENVIRONMENT
    related_story_node: str | None = None
    related_event_node: str | None = None

    @field_validator("candidates", "reference_asset_ids", mode="before")
    @classmethod
    def _coerce_none_to_list(cls, v: object) -> object:
        if v is None:
            return []
        return v

    @field_validator("selected_candidate_index", "style_profile", mode="before")
    @classmethod
    def _coerce_undefined_to_none(cls, v: object) -> object:
        if v == "" or v == "null":
            return None
        return v

    def get_view(self, lod_level: str) -> dict[str, Any] | None:
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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str | None:
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
