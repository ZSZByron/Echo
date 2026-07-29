"""Narrative renderer - converts JudgmentResult to immersive text."""

from __future__ import annotations

import logging

from app.ai.prompts.renderer_prompt import build_renderer_messages
from app.ai.provider import LLMProvider
from app.models.action import JudgmentResult, ParsedIntent

logger = logging.getLogger(__name__)


class NarrativeRenderer:
    """Renders judgment results as cyberpunk narrative text."""

    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def render(
        self,
        judgment: JudgmentResult,
        intent: ParsedIntent,
        context: dict[str, object],
    ) -> str:
        """Generate narrative text from judgment result."""
        try:
            judgment_data = judgment.model_dump(mode="json")
            intent_data = intent.model_dump(mode="json")
            messages = build_renderer_messages(judgment_data, intent_data, context)
            text = await self._provider.chat(messages)
            return text if text else self._fallback_render(judgment)
        except Exception as e:
            logger.warning("Render failed, using fallback: %s", e)
            return self._fallback_render(judgment)

    def _fallback_render(self, judgment: JudgmentResult) -> str:
        """Simple template-based fallback rendering."""
        outcome = judgment.result.value
        return f"[SYSTEM] 判决完成。结果：{outcome}。原因：{judgment.reason}"
