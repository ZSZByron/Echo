"""Unit tests for identity key manager."""

import pytest
from uuid import uuid4
from unittest.mock import Mock


def test_register_returns_unique_user_id_and_free_tier():
    """Test that register() generates unique user_id and FREE tier.
    
    This test verifies:
    1. Each registration generates a unique user_id
    2. All new users start with FREE tier
    3. User ID format matches: u_{12_hex_chars}
    """
    # Import the function that doesn't exist yet - this will fail
    from app.domains.identity.key_manager import register, IdentityInfo
    
    # Mock a UserStore (will be implemented later)
    store = Mock()
    store.save = Mock()
    
    # Register two users
    user_a = register(store)
    user_b = register(store)
    
    # Verify user_ids are unique
    assert user_a.user_id != user_b.user_id, \
        "Each registration must generate a unique user_id"
    
    # Verify both have FREE tier
    assert user_a.tier == "FREE", \
        "New users must start with FREE tier"
    assert user_b.tier == "FREE", \
        "New users must start with FREE tier"
    
    # Verify user_id format: u_{12 hex characters}
    assert user_a.user_id.startswith("u_"), \
        "user_id must start with 'u_'"
    assert len(user_a.user_id) == 14, \
        "user_id must be 14 characters: 'u_' + 12 hex chars"
    assert user_a.user_id[2:].isalnum(), \
        "user_id suffix must be alphanumeric (hex)"
    
    # Verify store.save was called
    assert store.save.call_count == 2, \
        "store.save() must be called for each registration"


def test_register_user_id_format():
    """Test that user_id follows the exact format specification."""
    from app.domains.identity.key_manager import register
    from unittest.mock import Mock
    
    store = Mock()
    store.save = Mock()
    
    # Generate multiple user_ids to test format consistency
    user_ids = [register(store).user_id for _ in range(10)]
    
    for user_id in user_ids:
        # Verify prefix
        assert user_id.startswith("u_"), f"user_id {user_id} must start with 'u_'"
        
        # Verify total length
        assert len(user_id) == 14, f"user_id {user_id} must be 14 characters total"
        
        # Verify hex part is 12 characters
        hex_part = user_id[2:]
        assert len(hex_part) == 12, f"user_id {user_id} hex part must be 12 characters"
        
        # Verify hex part is valid hexadecimal
        assert hex_part.islower() or all(c in "0123456789abcdef" for c in hex_part), \
            f"user_id {user_id} hex part must be lowercase hex"


def test_identity_info_structure():
    """Test that IdentityInfo has correct Pydantic v2 structure."""
    from app.domains.identity.key_manager import IdentityInfo
    from pydantic import BaseModel
    
    # Verify it's a Pydantic model
    assert issubclass(IdentityInfo, BaseModel), \
        "IdentityInfo must be a Pydantic BaseModel"
    
    # Create instance and verify fields
    info = IdentityInfo(user_id="u_abc123def456", tier="FREE")
    
    assert info.user_id == "u_abc123def456"
    assert info.tier == "FREE"
    
    # Verify model_dump() works (Pydantic v2 API)
    dumped = info.model_dump()
    assert "user_id" in dumped
    assert "tier" in dumped
    assert dumped["user_id"] == "u_abc123def456"
    assert dumped["tier"] == "FREE"