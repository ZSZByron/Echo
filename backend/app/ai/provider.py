"""LLM Provider implementations - unified interface for 6 providers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, cast

from anthropic.types import TextBlock
from app.ai.config import ProviderConfig


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Send messages and get a text response."""

    @abstractmethod
    async def chat_json(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        """Send messages and get a JSON dict response."""


class OpenAICompatibleProvider(LLMProvider):
    """Adapter using openai SDK. Covers: OpenAI, DeepSeek, Qwen, Kimi, GLM."""

    COMPATIBLE_TYPES = frozenset({"openai", "deepseek", "qwen", "kimi", "glm"})

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Send messages and return text content from first choice."""
        response = await self._client.chat.completions.create(
            model=self._config.model,
            messages=cast(Any, messages),
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            **kwargs,
        )
        content = response.choices[0].message.content
        return content if content else ""

    async def chat_json(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        """Send messages requesting JSON output, return parsed dict."""
        response = await self._client.chat.completions.create(
            model=self._config.model,
            messages=cast(Any, messages),
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            response_format={"type": "json_object"},
            **kwargs,
        )
        content = response.choices[0].message.content
        return json.loads(content) if content else {}


class AnthropicProvider(LLMProvider):
    """Adapter using anthropic SDK natively."""

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=config.api_key)

    def _split_messages(
        self, messages: list[dict[str, str]]
    ) -> tuple[str, list[dict[str, str]]]:
        """Extract system message and return (system_prompt, remaining_messages)."""
        system_parts: list[str] = []
        rest: list[dict[str, str]] = []

        for msg in messages:
            if msg.get("role") == "system":
                system_parts.append(msg.get("content", ""))
            else:
                rest.append(msg)

        return "\n".join(system_parts), rest

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Send messages with system prompt separated per Anthropic API convention."""
        system_prompt, rest = self._split_messages(messages)

        create_kwargs: dict[str, Any] = {
            "model": self._config.model,
            "messages": rest,
            "max_tokens": self._config.max_tokens,
            **kwargs,
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt

        response = await self._client.messages.create(**create_kwargs)
        if response.content:
            block = response.content[0]
            if hasattr(block, "text"):
                return cast(str, block.text)
        return ""

    async def chat_json(self, messages: list[dict[str, str]], **kwargs: Any) -> dict[str, Any]:
        """Force JSON output using prefill technique, return parsed dict."""
        # Prefill: add assistant message starting with "{" to steer JSON output
        extended = list(messages) + [{"role": "assistant", "content": "{"}]
        _, rest = self._split_messages(extended)

        # Remove the last assistant message from rest and set as prefill
        # The split doesn't touch assistant messages, so the prefill is last in rest
        prefill_messages = rest[:-1]  # all messages except our prefill
        prefill_text = rest[-1]["content"] if rest else "{"

        response = await self._client.messages.create(
            model=self._config.model,
            messages=cast(Any, prefill_messages),
            max_tokens=self._config.max_tokens,
            **kwargs,
        )
        if response.content:
            block = response.content[0]
            if hasattr(block, "text"):
                raw = cast(str, block.text)
                result: dict[str, Any] = json.loads("{" + raw)
                return result
        return {}


def create_provider(config: ProviderConfig) -> LLMProvider:
    """Factory function: dispatch based on config.provider_type.

    Returns:
        OpenAICompatibleProvider for openai/deepseek/qwen/kimi/glm.
        AnthropicProvider for anthropic.

    Raises:
        ValueError: If provider_type is not recognized.
    """
    if config.provider_type in OpenAICompatibleProvider.COMPATIBLE_TYPES:
        return OpenAICompatibleProvider(config)
    if config.provider_type == "anthropic":
        return AnthropicProvider(config)
    raise ValueError(f"Unknown provider type: {config.provider_type}")
