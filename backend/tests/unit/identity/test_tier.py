"""Unit tests for identity tier system."""

import pytest
from enum import Enum


def test_tier_enum_closed():
    """Test that UserTier enum has exactly the required values.
    
    This test ensures the enum is closed - no additional values allowed.
    Only FREE, VIP, SVIP are permitted.
    """
    # Import the enum that doesn't exist yet - this will fail
    from app.domains.identity.tier import UserTier
    
    # Verify exactly three values exist
    assert {t.value for t in UserTier} == {"FREE", "VIP", "SVIP"}, \
        "UserTier must contain exactly FREE, VIP, SVIP - no additions allowed"
    
    # Verify default() classmethod exists and returns FREE
    assert UserTier.default() is UserTier.FREE, \
        "UserTier.default() must return UserTier.FREE for MVP"
    
    # Verify it's a proper Enum
    assert issubclass(UserTier, Enum), "UserTier must inherit from Enum"
    
    # Verify it's a string enum for Pydantic compatibility
    assert issubclass(UserTier, str), "UserTier must inherit from str for JSON serialization"


def test_tier_enum_values_are_strings():
    """Test that all enum values are proper strings."""
    from app.domains.identity.tier import UserTier
    
    assert UserTier.FREE.value == "FREE"
    assert UserTier.VIP.value == "VIP"
    assert UserTier.SVIP.value == "SVIP"
    
    # Verify they work as string enums (inherited from str)
    # str+Enum behaves such that EnumMember == "value" works
    assert UserTier.FREE == "FREE"  # String comparison works
    assert UserTier.VIP == "VIP"
    assert UserTier.SVIP == "SVIP"
    
    # Verify .value gives the actual string value
    assert isinstance(UserTier.FREE.value, str)
    assert isinstance(UserTier.VIP.value, str)
    assert isinstance(UserTier.SVIP.value, str)