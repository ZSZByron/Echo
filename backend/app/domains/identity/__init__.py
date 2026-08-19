"""Identity domain for user registration and tier management.

This domain handles user_id generation, tier assignment, and identity persistence.
Part of A模块公用模块 (A1-v0.5) implementation.

Components:
- UserTier: Closed enum with FREE, VIP, SVIP values
- register(): User registration with unique user_id generation
- IdentityInfo: Pydantic v2 model for user identity data

Note: Tier routing logic is NOT implemented in MVP.
TODO: Add tier-based routing logic in future waves.
"""

from app.domains.identity.tier import UserTier
from app.domains.identity.key_manager import register, IdentityInfo

__all__ = [
    "UserTier",
    "register", 
    "IdentityInfo"
]