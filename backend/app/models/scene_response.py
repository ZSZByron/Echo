"""DTO models for the GET /api/scene endpoint."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Position(BaseModel):
    """Percentage-based position on the scene canvas (0-100)."""

    x: float
    y: float


class SceneObjectDTO(BaseModel):
    """A single object in the scene response, with visual metadata."""

    id: str
    name: str
    type: str
    description: str
    position: Position
    asset: Optional[str] = None  # file path/URL if approved, else None
    is_primary: bool = False
    is_dangerous: bool = False


class SceneResponse(BaseModel):
    """Top-level scene payload returned by GET /api/scene."""

    scene_id: str
    name: str
    description: str
    atmosphere: str
    background_asset: Optional[str] = None  # path if approved, else None
    objects: list[SceneObjectDTO] = []
