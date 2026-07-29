"""API-related Pydantic models for Echo system."""

from typing import Optional
from pydantic import BaseModel, Field

from app.models.action import ParsedIntent, JudgmentResult as ActionJudgmentResult
from app.models.player import PlayerState


class ActionRequest(BaseModel):
    """Request from frontend to process a player action.
    
    ActionRequest encapsulates player input for processing by the
    game engine.
    
    Attributes:
        player_input: Raw text input from the player
        player_id: ID of the player making the request
        current_scene: ID of the scene the player is currently in
    """
    
    player_input: str = Field(
        ...,
        min_length=1,
        description="Raw text input from the player"
    )
    player_id: str = Field(default="player_001", description="ID of the player")
    current_scene: str = Field(default="temple_ruins", description="Current scene ID")


class ActionResponse(BaseModel):
    """Response from backend to frontend after processing an action.
    
    ActionResponse contains all information needed for the frontend
    to update the game state and display narrative content.
    
    Attributes:
        judgment: The judgment result of the player's action
        narrative: Generated narrative text to display
        updated_state: New player state after applying the action
        parsed_intent: How the system interpreted the player's input
        echo_vision: Optional echo vision text if triggered
        available_actions: List of actions the player can take next
    """
    
    judgment: ActionJudgmentResult = Field(
        ...,
        description="The judgment result of the player's action"
    )
    narrative: str = Field(..., description="Generated narrative text")
    updated_state: PlayerState = Field(
        ...,
        description="New player state after applying the action"
    )
    parsed_intent: ParsedIntent = Field(
        ...,
        description="How the system interpreted the player's input"
    )
    echo_vision: Optional[str] = Field(
        default=None,
        description="Optional echo vision text if triggered"
    )
    available_actions: list[str] = Field(
        default_factory=list,
        description="List of actions the player can take next"
    )
