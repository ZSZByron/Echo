"""Identity key management for user registration.

This module handles user_id generation and registration.
Following TDD principles with minimal implementation to pass tests.
"""

from uuid import uuid4
from pydantic import BaseModel, Field


class IdentityInfo(BaseModel):
    """User identity information returned from registration.
    
    Uses Pydantic v2 patterns with model_config and model_dump().
    
    Attributes:
        user_id: Unique user identifier in format u_{12_hex_chars}
        tier: User tier level (always "FREE" for MVP)
    """
    
    model_config = {
        "str_strip_whitespace": True,
        "validate_assignment": True,
        "extra": "forbid"
    }
    
    user_id: str = Field(..., description="Unique user identifier")
    tier: str = Field(..., description="User tier level")


def register(store) -> IdentityInfo:
    """Register a new user with unique user_id and default tier.
    
    Generates a unique user_id in format: u_{12_hex_characters}
    All new users start with FREE tier (MVP: no tier differences).
    
    Args:
        store: UserStore instance for persistence (will be implemented in T3)
    
    Returns:
        IdentityInfo: Contains user_id and tier="FREE"
        
    Note:
        Tier routing logic is NOT implemented in MVP.
        TODO: Add tier-based routing logic in future waves
    """
    # Generate unique user_id: u_{12 hex characters from uuid4}
    user_id = f"u_{uuid4().hex[:12]}"
    
    # TODO: Implement tier routing logic based on UserTier enum
    # MVP: All users get FREE tier
    tier = "FREE"
    
    # Persist to store (store.save will be implemented in T3)
    store.save(user_id, tier)
    
    return IdentityInfo(user_id=user_id, tier=tier)