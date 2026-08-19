"""Identity registration API routes.

This module provides the POST /api/identity/register endpoint
which allows new users to register and receive a unique user_id.

Following MVP strategy: All registrations return FREE tier.
Tier routing logic is NOT implemented in this wave.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.domains.identity import register, IdentityInfo

# Create router for identity endpoints
router = APIRouter(prefix="/api/identity", tags=["identity"])


class RegisterResponse(BaseModel):
    """Response model for user registration.
    
    Uses Pydantic v2 patterns with model_config.
    
    Attributes:
        user_id: Unique user identifier in format u_{12_hex_chars}
        tier: User tier level (always "FREE" for MVP)
    """
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "u_a1b2c3d4e5f6",
                    "tier": "FREE"
                }
            ]
        }
    }
    
    user_id: str
    tier: str


class RegisterRequest(BaseModel):
    """Request model for user registration.
    
    MVP: Empty request body - no input required for basic registration.
    Future waves may add registration fields (email, password, etc.).
    """
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {}  # Empty request for MVP
            ]
        }
    }


# TODO: Implement UserStore for persistence (will be done in T3)
# For now, use a mock store to satisfy register() signature
class MockUserStore:
    """Temporary mock store for register() function.
    
    TODO: Replace with real UserStore implementation in T3
    """
    
    def save(self, user_id: str, tier: str) -> None:
        """Mock save method - does nothing for now.
        
        TODO: Implement actual persistence in T3
        """
        pass


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register_user(request: RegisterRequest = RegisterRequest()) -> RegisterResponse:
    """Register a new user and return their identity information.
    
    This endpoint creates a new user with:
    - Unique user_id in format: u_{12_hex_characters}
    - Default tier: FREE (MVP: no tier differences)
    
    Request Body:
        Empty {} for MVP (no input required)
    
    Returns:
        RegisterResponse: Contains user_id and tier="FREE"
    
    Example:
        POST /api/identity/register
        {}
        
        Response:
        {
            "user_id": "u_a1b2c3d4e5f6",
            "tier": "FREE"
        }
    
    Note:
        Tier routing logic is NOT implemented in MVP.
        All users receive FREE tier regardless of request content.
        TODO: Add tier-based routing logic in future waves
    """
    try:
        # Create mock store (TODO: replace with real UserStore in T3)
        store = MockUserStore()
        
        # Register user and get identity info
        identity_info: IdentityInfo = register(store)
        
        # Return response with user_id and tier
        return RegisterResponse(
            user_id=identity_info.user_id,
            tier=identity_info.tier
        )
        
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )