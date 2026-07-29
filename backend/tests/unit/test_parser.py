"""Tests for IntentParser."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.ai.parser import IntentParser
from app.ai.provider import LLMProvider
from app.models.action import ActionType, ParsedIntent


@pytest.fixture
def mock_provider() -> LLMProvider:
    """Create a mock LLMProvider."""
    provider = AsyncMock(spec=LLMProvider)
    return provider


@pytest.fixture
def parser(mock_provider: LLMProvider) -> IntentParser:
    """Create IntentParser with mock provider."""
    return IntentParser(mock_provider)


@pytest.mark.asyncio
async def test_normal_parse(parser: IntentParser, mock_provider: LLMProvider) -> None:
    """Mock returns valid JSON -> correct ParsedIntent."""
    mock_provider.chat_json.return_value = {
        "action_type": "brute_force",
        "target": "ancient_locked_door",
        "intensity": "maximum",
        "risk_acceptance": True,
        "tool_used": None,
    }
    result = await parser.parse("我强行砸开这个锁")
    assert isinstance(result, ParsedIntent)
    assert result.action_type == ActionType.BRUTE_FORCE
    assert result.target == "ancient_locked_door"
    assert result.intensity == "maximum"
    assert result.risk_acceptance is True
    assert result.tool_used is None
    assert result.raw_input == "我强行砸开这个锁"
    assert result.confidence == 0.9


@pytest.mark.asyncio
async def test_invalid_action_type(
    parser: IntentParser, mock_provider: LLMProvider
) -> None:
    """Mock returns invalid action_type -> fallback intent."""
    mock_provider.chat_json.return_value = {
        "action_type": "invalid_type",
        "target": "door",
        "intensity": "medium",
        "risk_acceptance": False,
        "tool_used": None,
    }
    result = await parser.parse("做点什么")
    assert result.action_type == ActionType.PROBE
    assert result.confidence == 0.0
    assert result.intensity == "low"


@pytest.mark.asyncio
async def test_missing_fields(
    parser: IntentParser, mock_provider: LLMProvider
) -> None:
    """Mock returns partial JSON -> uses defaults or fallback."""
    # Missing intensity but valid action_type -> ParsedIntent uses default
    mock_provider.chat_json.return_value = {
        "action_type": "probe",
        "target": None,
        "risk_acceptance": False,
        "tool_used": None,
    }
    result = await parser.parse("看看这里")
    assert result.action_type == ActionType.PROBE
    assert result.intensity == "medium"  # default


@pytest.mark.asyncio
async def test_llm_exception(parser: IntentParser, mock_provider: LLMProvider) -> None:
    """Provider raises exception -> fallback intent."""
    mock_provider.chat_json.side_effect = RuntimeError("API down")
    result = await parser.parse("我砸门")
    assert result.action_type == ActionType.PROBE
    assert result.confidence == 0.0
    assert result.raw_input == "我砸门"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action_value",
    [
        "brute_force",
        "stealth",
        "read_memory",
        "negotiate",
        "probe",
        "god_provoke",
        "investigate",
    ],
)
async def test_all_valid_action_types(
    action_value: str,
    parser: IntentParser,
    mock_provider: LLMProvider,
) -> None:
    """All 7 valid action types parse correctly."""
    mock_provider.chat_json.return_value = {
        "action_type": action_value,
        "target": None,
        "intensity": "medium",
        "risk_acceptance": False,
        "tool_used": None,
    }
    result = await parser.parse("test input")
    assert result.action_type.value == action_value
    assert result.confidence == 0.9


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("player_input", "expected_action"),
    [
        ("砸门", "brute_force"),
        ("暴力破门", "brute_force"),
        ("撞开", "brute_force"),
    ],
)
async def test_synonym_handling(
    player_input: str,
    expected_action: str,
    parser: IntentParser,
    mock_provider: LLMProvider,
) -> None:
    """Synonym inputs all map to brute_force (mock different responses)."""
    mock_provider.chat_json.return_value = {
        "action_type": expected_action,
        "target": "ancient_locked_door",
        "intensity": "maximum",
        "risk_acceptance": True,
        "tool_used": None,
    }
    result = await parser.parse(player_input)
    assert result.action_type == ActionType.BRUTE_FORCE
    assert result.target == "ancient_locked_door"


@pytest.mark.asyncio
async def test_validation_error_fallback(
    parser: IntentParser, mock_provider: LLMProvider
) -> None:
    """LLM returns valid action_type but invalid intensity -> fallback."""
    mock_provider.chat_json.return_value = {
        "action_type": "probe",
        "target": None,
        "intensity": "extreme",  # invalid literal
        "risk_acceptance": False,
        "tool_used": None,
    }
    result = await parser.parse("探查")
    # Pydantic rejects invalid intensity literal -> fallback
    assert result.action_type == ActionType.PROBE
    assert result.confidence == 0.0


def test_fallback_intent_directly(parser: IntentParser) -> None:
    """Test _fallback_intent produces correct defaults."""
    result = parser._fallback_intent("test")
    assert result.action_type == ActionType.PROBE
    assert result.intensity == "low"
    assert result.risk_acceptance is False
    assert result.confidence == 0.0
    assert result.raw_input == "test"
    assert result.target is None
    assert result.tool_used is None


def test_validate_intent_empty_action(parser: IntentParser) -> None:
    """Empty action_type string -> fallback."""
    result = parser._validate_intent({}, "input")
    assert result.confidence == 0.0


def test_validate_intent_valid(parser: IntentParser) -> None:
    """Valid data -> proper ParsedIntent."""
    data = {
        "action_type": "stealth",
        "target": "door",
        "intensity": "low",
        "risk_acceptance": True,
        "tool_used": "cloak",
    }
    result = parser._validate_intent(data, "悄悄过去")
    assert result.action_type == ActionType.STEALTH
    assert result.target == "door"
    assert result.tool_used == "cloak"
