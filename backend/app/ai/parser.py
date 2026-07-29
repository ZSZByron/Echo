"""Intent parser - converts player text to structured ParsedIntent."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from app.ai.prompts.parser_prompt import build_parser_messages
from app.ai.provider import LLMProvider
from app.models.action import ActionType, ParsedIntent

logger = logging.getLogger(__name__)

# Valid action type values - runtime enforcement
VALID_ACTION_TYPES = frozenset(e.value for e in ActionType)


class IntentParser:
    """Parses player natural language input into structured ParsedIntent."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def parse(self, player_input: str) -> ParsedIntent:
        """Parse player input into ParsedIntent. Falls back on any error."""
        try:
            messages = build_parser_messages(player_input)
            result = await self._provider.chat_json(messages)
            return self._validate_intent(result, player_input)
        except Exception as e:
            logger.warning("Parse failed, using fallback: %s", e)
            return self._fallback_intent(player_input)

    def _validate_intent(self, data: dict[str, Any], raw_input: str) -> ParsedIntent:
        """Validate and construct ParsedIntent from LLM output."""
        action_type = data.get("action_type", "")
        if action_type not in VALID_ACTION_TYPES:
            return self._fallback_intent(raw_input)

        try:
            return ParsedIntent(
                action_type=ActionType(action_type),
                target=data.get("target"),
                intensity=data.get("intensity", "medium"),
                risk_acceptance=bool(data.get("risk_acceptance", False)),
                tool_used=data.get("tool_used"),
                raw_input=raw_input,
                confidence=0.9,
            )
        except (ValidationError, ValueError) as e:
            logger.warning("Validation failed: %s", e)
            return self._fallback_intent(raw_input)

    def _fallback_intent(self, raw_input: str) -> ParsedIntent:
        """Return a safe fallback intent when parsing fails."""
        return ParsedIntent(
            action_type=ActionType.PROBE,
            target=None,
            intensity="low",
            risk_acceptance=False,
            tool_used=None,
            raw_input=raw_input,
            confidence=0.0,
        )
