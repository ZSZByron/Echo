"""Player-related Pydantic models for Echo system."""

from typing import Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class PlayerStatus(str, Enum):
    """Current status of the player character."""
    
    NORMAL = "normal"
    INJURED = "injured"
    EXHAUSTED = "exhausted"
    DYING = "dying"
    DEAD = "dead"
    ECHO_ACTIVE = "echo_active"
    ECHO_OVERLOAD = "echo_overload"


class PlayerState(BaseModel):
    """Complete state of a player in the Echo world.
    
    PlayerState tracks all physical and mental attributes, resources,
    and special abilities that define the player's current condition.
    
    Attributes:
        id: Unique player identifier
        energy: Current physical energy (0-100)
        health: Current health points (0-100)
        strength: Physical power attribute (affects interaction success)
        intelligence: Mental acuity attribute (affects puzzle solving)
        echo_mode_enabled: Whether time-echo vision is active
        mental_stability: Saneness (0-100), affects reality perception
        location: Current scene_id where player is located
        inventory: List of object IDs currently possessed
        status: Current player status condition
        max_energy: Maximum possible energy
        max_health: Maximum possible health
    """
    
    id: str = Field(..., description="Unique player identifier")
    energy: int = Field(
        ...,
        ge=0,
        le=100,
        description="Current physical energy (0-100)"
    )
    health: int = Field(
        ...,
        ge=0,
        le=100,
        description="Current health points (0-100)"
    )
    strength: int = Field(
        ...,
        ge=0,
        le=100,
        description="Physical power attribute"
    )
    intelligence: int = Field(
        ...,
        ge=0,
        le=100,
        description="Mental acuity attribute"
    )
    echo_mode_enabled: bool = Field(
        default=False,
        description="Whether time-echo vision is active"
    )
    mental_stability: int = Field(
        ...,
        ge=0,
        le=100,
        description="Saneness (0-100), affects reality perception"
    )
    location: str = Field(..., description="Current scene_id")
    inventory: list[str] = Field(
        default_factory=list,
        description="List of object IDs currently possessed"
    )
    status: PlayerStatus = Field(
        default=PlayerStatus.NORMAL,
        description="Current player status condition"
    )
    max_energy: int = Field(
        default=100,
        ge=0,
        description="Maximum possible energy"
    )
    max_health: int = Field(
        default=100,
        ge=0,
        description="Maximum possible health"
    )
