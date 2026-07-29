"""Action-related Pydantic models for Echo system."""

from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ActionType(str, Enum):
    """Types of actions players can perform."""
    BRUTE_FORCE = "brute_force"
    STEALTH = "stealth"
    READ_MEMORY = "read_memory"
    NEGOTIATE = "negotiate"
    PROBE = "probe"
    GOD_PROVOKE = "god_provoke"
    INVESTIGATE = "investigate"


class JudgmentOutcome(str, Enum):
    """Possible outcomes of action judgment."""
    
    SUCCESS = "success"
    FAIL = "fail"
    FORCED_FAIL = "forced_fail"
    PARTIAL = "partial"
    GOD_INTERVENTION = "god_intervention"


class ParsedIntent(BaseModel):
    """Represents a parsed player action intent.
    
    ParsedIntent captures the system's understanding of what the player
    is attempting to do, including all relevant parameters.
    
    Attributes:
        action_type: The category of action being attempted
        target: What object or entity the action is directed at
        intensity: How forceful or aggressive the action is (0-100)
        risk_acceptance: How much risk the player is willing to accept (0-100)
        tool_used: Any item or tool being used to perform the action
        raw_input: Original player input string
        confidence: How confident the parser is in this interpretation (0-1)
    """
    
    action_type: ActionType = Field(
        ...,
        description="The category of action being attempted"
    )
    target: Optional[str] = Field(
        default=None,
        description="What object or entity the action is directed at"
    )
    intensity: Literal["low", "medium", "maximum"] = Field(
        ...,
        description="How forceful the action is (low/medium/maximum)"
    )
    risk_acceptance: bool = Field(
        ...,
        description="How much risk the player accepts"
    )
    tool_used: Optional[str] = Field(
        default=None,
        description="Any item or tool being used"
    )
    raw_input: str = Field(..., description="Original player input string")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Parser confidence (0-1)"
    )


class StateChange(BaseModel):
    """Represents a change to player or world state.
    
    StateChanges are applied when actions succeed or fail.
    
    Attributes:
        target_type: What kind of entity is changing
        target_id: ID of the entity being changed
        property_name: Which property is being modified
        old_value: Previous value
        new_value: New value to apply
    """
    
    target_type: Literal["player", "object", "scene"] = Field(
        ...,
        description="What kind of entity is changing"
    )
    target_id: str = Field(..., description="ID of the entity being changed")
    property_name: str = Field(..., description="Which property is being modified")
    old_value: Any = Field(..., description="Previous value")
    new_value: Any = Field(..., description="New value to apply")


class NarrativeContext(BaseModel):
    """Contextual information for narrative generation.
    
    NarrativeContext provides the narrative system with the information
    needed to generate compelling story responses.
    
    Attributes:
        scene_id: Where the action is taking place
        previous_action: What the player did last
        active_gods: Which gods are paying attention
        atmosphere: Current mood or feeling
        tension_level: How tense the situation is (0-100)
    """
    
    scene_id: str = Field(..., description="Where the action is taking place")
    previous_action: Optional[str] = Field(
        default=None,
        description="What the player did last"
    )
    active_gods: list[str] = Field(
        default_factory=list,
        description="Which gods are paying attention"
    )
    atmosphere: str = Field(..., description="Current mood or feeling")
    tension_level: int = Field(
        ...,
        ge=0,
        le=100,
        description="How tense the situation is (0-100)"
    )


class JudgmentResult(BaseModel):
    """Result of judging a player's action.
    
    JudgmentResult contains the outcome, reasons, and consequences
    of an attempted action.
    
    Attributes:
        result: The final judgment on the action
        reason: Human-readable explanation of why this result occurred
        damage: Any damage dealt to the player
        state_changes: List of state changes to apply
        god_intervention: Whether a god intervened (which god)
        narrative_context: Context for generating narrative response
        echo_triggered: Whether this triggered an echo vision
    """
    
    result: JudgmentOutcome = Field(
        ...,
        description="The final judgment on the action"
    )
    reason: str = Field(
        ...,
        description="Human-readable explanation of the result"
    )
    damage: int = Field(
        default=0,
        ge=0,
        description="Any damage dealt to the player"
    )
    state_changes: list[StateChange] = Field(
        default_factory=list,
        description="List of state changes to apply"
    )
    god_intervention: Optional[str] = Field(
        default=None,
        description="Which god intervened, if any"
    )
    narrative_context: NarrativeContext = Field(
        ...,
        description="Context for generating narrative response"
    )
    echo_triggered: bool = Field(
        default=False,
        description="Whether this triggered an echo vision"
    )
