"""User tier enumeration for identity domain.

This module defines the UserTier enum which represents user access levels.
Following MVP strategy: all users default to FREE tier with no differences.
The enum is closed - only FREE, VIP, SVIP values are allowed.
"""

from enum import Enum


class UserTier(str, Enum):
    """User access tier levels.
    
    Closed enum - exactly these three values are allowed:
    - FREE: Default tier for all new users (MVP: no tier differences)
    - VIP: Reserved for future tier-based routing logic
    - SVIP: Reserved for future tier-based routing logic
    
    Note: Tier routing logic is NOT implemented in MVP.
    TODO: Add tier-based routing logic in future waves
    """
    
    FREE = "FREE"
    VIP = "VIP"
    SVIP = "SVIP"
    
    @classmethod
    def default(cls) -> "UserTier":
        """Return the default tier for new users.
        
        MVP strategy: All users start with FREE tier.
        No tier-based differences in current implementation.
        
        Returns:
            UserTier.FREE: The default tier for all new registrations
        """
        return cls.FREE