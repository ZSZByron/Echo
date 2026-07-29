"""World-related Pydantic models for Echo system."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class GodKing(BaseModel):
    """Represents a God King entity in the Echo world.
    
    God Kings are powerful entities that hold dominion over specific domains
    and can intervene when players attempt to change protected future events.
    
    Attributes:
        id: Unique identifier for the God King
        name: Display name of the God King
        domain: The sphere of influence this God King controls
        intervention_threshold: Minimum severity level that triggers intervention
        penalty: Damage or consequences applied when intervention occurs
    """
    
    id: str = Field(..., description="Unique identifier for the God King")
    name: str = Field(..., description="Display name of the God King")
    domain: str = Field(..., description="The sphere of influence this God King controls")
    intervention_threshold: int = Field(
        ..., 
        ge=0, 
        le=100,
        description="Minimum severity level (0-100) that triggers intervention"
    )
    penalty: int = Field(
        ...,
        ge=0,
        description="Damage or consequences applied when intervention occurs"
    )


class WorldRule(BaseModel):
    """Defines physical or metaphysical laws governing a world region.
    
    WorldRules establish the constraints and properties that apply to
    specific regions within the Echo world.
    
    Attributes:
        rule_id: Unique identifier for this rule
        region: The geographical or conceptual area this rule applies to
        description: Human-readable explanation of the rule
        physical_constraints: List of physical limitations in this region
        magic_modifier: Modifier to magical effectiveness (default 1.0)
    """
    
    rule_id: str = Field(..., description="Unique identifier for this rule")
    region: str = Field(..., description="The area this rule applies to")
    description: str = Field(..., description="Human-readable explanation of the rule")
    physical_constraints: List[str] = Field(
        default_factory=list,
        description="Physical limitations in this region"
    )
    magic_modifier: float = Field(
        default=1.0,
        ge=0.0,
        description="Modifier to magical effectiveness (1.0 = normal)"
    )


class InteractionTarget(BaseModel):
    """Represents an object or entity that can be interacted with.
    
    InteractionTargets define the specific points within a scene that
    players can interact with, along with any special properties.
    
    Attributes:
        object_id: Reference to the GameObject being targeted
        is_dangerous: Whether interaction poses inherent risks
        required_tools: Tools needed to interact safely (optional)
    """
    
    object_id: str = Field(..., description="Reference to the GameObject being targeted")
    is_dangerous: bool = Field(
        default=False,
        description="Whether interaction poses inherent risks"
    )
    required_tools: Optional[List[str]] = Field(
        default=None,
        description="Tools needed to interact safely"
    )


class GameObject(BaseModel):
    """Represents a physical object within the game world.
    
    GameObjects are items, structures, or entities that exist in scenes
    and can be interacted with, potentially affecting the timeline.
    
    Attributes:
        id: Unique identifier for this object
        name: Display name of the object
        type: Category of object (door, container, item, etc.)
        hardness: Resistance to interaction (0-100 scale)
        energy_cost: Physical energy required to interact
        is_future_anchor: Whether this object is a fixed point in time
        description: Human-readable description
    """
    
    id: str = Field(..., description="Unique identifier for this object")
    name: str = Field(..., description="Display name of the object")
    type: str = Field(..., description="Category of object")
    hardness: int = Field(
        ...,
        ge=0,
        le=100,
        description="Resistance to interaction (0-100 scale)"
    )
    energy_cost: int = Field(
        ...,
        ge=0,
        description="Physical energy required to interact"
    )
    is_future_anchor: bool = Field(
        default=False,
        description="Whether this object is a fixed point in time"
    )
    description: str = Field(..., description="Human-readable description")
    position: Optional[dict[str, float]] = Field(
        default=None,
        description="Percentage-based position {x, y} on the scene canvas"
    )


class Scene(BaseModel):
    """Defines a location within the Echo world.
    
    Scenes contain the environment, objects, and interaction possibilities
    that players encounter during their journey.
    
    Attributes:
        scene_id: Unique identifier for this scene
        name: Display name of the location
        description: Human-readable scene description
        atmosphere: Mood or feeling of the scene
        accessible_objects: List of GameObjects in this scene
        interaction_targets: Specific points that can be interacted with
        region: Which WorldRule governs this scene
    """
    
    scene_id: str = Field(..., description="Unique identifier for this scene")
    name: str = Field(..., description="Display name of the location")
    description: str = Field(..., description="Human-readable scene description")
    atmosphere: str = Field(..., description="Mood or feeling of the scene")
    accessible_objects: List[GameObject] = Field(
        default_factory=list,
        description="List of GameObjects in this scene"
    )
    interaction_targets: List[InteractionTarget] = Field(
        default_factory=list,
        description="Specific points that can be interacted with"
    )
    region: Optional[str] = Field(
        default=None,
        description="Which WorldRule governs this scene"
    )
