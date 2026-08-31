"""LLM Provider implementations - unified interface for 6 providers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, cast

from anthropic.types import TextBlock
from app.ai.config import ProviderConfig


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract JSON from text, handling markdown fences and prose wrapping.

    Args:
        text: Raw text that may contain JSON wrapped in markdown fences or prose.

    Returns:
        Parsed dict if JSON found, None otherwise (never raises).

    Examples:
        _extract_json('```json\\n{"a":1}\\n```') → {"a": 1}
        _extract_json('Result: {"a":1} done.') → {"a": 1}
        _extract_json('not json') → None
        _extract_json('   ') → None
    """
    if not text or not text.strip():
        return None

    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        # Find closing fence
        lines = text.split("\n", 1)  # Split first line only
        if len(lines) > 1:
            # Remove first line (opening fence) and find closing
            remaining = lines[1]
            if "```" in remaining:
                text = remaining.split("```")[0].rstrip()
            else:
                text = remaining
        else:
            # Single line with just fence
            return None

    # Find first '{' and last '}'
    first_brace = text.find("{")
    if first_brace == -1:
        return None
    last_brace = text.rfind("}")
    if last_brace == -1 or last_brace <= first_brace:
        return None

    # Extract the substring
    json_str = text[first_brace : last_brace + 1]

    try:
        return json.loads(json_str)  # noqa: S103 (we own the input)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


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
        # DeepSeek V4 defaults to thinking=on; reasoning tokens share the
        # max_tokens budget, which truncates/empties the JSON content for
        # large prompts (upload pipeline schema). Disable via BOTH param
        # styles: "thinking" (DeepSeek V4 native) and "enable_thinking"
        # (Qwen/GLM-compatible, harmless if ignored).
        self._default_extra_body: dict[str, Any] = {}
        if config.provider_type == "deepseek":
            self._default_extra_body["thinking"] = {"type": "disabled"}
            self._default_extra_body["enable_thinking"] = False
        elif config.provider_type == "qwen":
            # Qwen3 uses enable_thinking param; disable to prevent token burn
            self._default_extra_body["enable_thinking"] = False
        elif config.provider_type == "glm":
            # GLM-4.5+ uses both param styles; disable to prevent token burn
            self._default_extra_body["thinking"] = {"type": "disabled"}
            self._default_extra_body["enable_thinking"] = False

    def _merge_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Merge default extra_body with caller-provided kwargs."""
        if not self._default_extra_body:
            return kwargs
        merged = dict(kwargs)
        existing = dict(self._default_extra_body)
        caller_body = merged.get("extra_body")
        if isinstance(caller_body, dict):
            existing.update(caller_body)
        merged["extra_body"] = existing
        return merged

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Send messages and return text content from first choice."""
        kwargs = self._merge_kwargs(kwargs)
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
        kwargs = self._merge_kwargs(kwargs)
        attempted_without_response_format = False

        try:
            response = await self._client.chat.completions.create(
                model=self._config.model,
                messages=cast(Any, messages),
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
                response_format={"type": "json_object"},
                **kwargs,
            )
        except Exception as e:
            # Only retry on BadRequestError (400) for response_format rejection
            from openai import BadRequestError

            if isinstance(e, BadRequestError) and not attempted_without_response_format:
                # Retry once without response_format
                attempted_without_response_format = True
                kwargs_no_format = {k: v for k, v in kwargs.items() if k != "response_format"}
                response = await self._client.chat.completions.create(
                    model=self._config.model,
                    messages=cast(Any, messages),
                    temperature=self._config.temperature,
                    max_tokens=self._config.max_tokens,
                    **kwargs_no_format,
                )
            else:
                # Re-raise all other exceptions immediately
                raise

        content = response.choices[0].message.content

        # Empty content → return {}
        if not content:
            return {}

        # Parse with _extract_json
        parsed = _extract_json(content)

        # If parse failed and we haven't retried without response_format yet
        if parsed is None and not attempted_without_response_format:
            attempted_without_response_format = True
            kwargs_no_format = {k: v for k, v in kwargs.items() if k != "response_format"}
            response = await self._client.chat.completions.create(
                model=self._config.model,
                messages=cast(Any, messages),
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
                **kwargs_no_format,
            )
            content = response.choices[0].message.content
            parsed = _extract_json(content) if content else None

        # Still None → raise RuntimeError
        if parsed is None:
            raise RuntimeError(f"chat_json: no parseable JSON in response: {content[:200]!r}")

        return parsed


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
        system_prompt, rest = self._split_messages(extended)

        # Remove the last assistant message from rest and set as prefill
        # The split doesn't touch assistant messages, so the prefill is last in rest
        prefill_messages = rest[:-1]  # all messages except our prefill
        prefill_text = rest[-1]["content"] if rest else "{"

        # FIX: If prefill_messages is empty (system-only input), substitute
        # a user message so the API never receives an empty messages list.
        if not prefill_messages:
            prefill_messages = [{"role": "user", "content": system_prompt or "Return a strict JSON object only."}]

        response = await self._client.messages.create(
            model=self._config.model,
            messages=cast(Any, prefill_messages),
            max_tokens=self._config.max_tokens,
            **kwargs,
        )

        if not response.content:
            return {}

        # Concatenate ALL text blocks (not just the first one)
        all_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                all_text += cast(str, block.text)

        if not all_text:
            return {}

        # First try: prefill continuation ("{" + text)
        try:
            result = json.loads("{" + all_text)  # noqa: S103
            return result
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        # Second try: model emitted complete object despite prefill
        parsed = _extract_json(all_text)
        if parsed is not None:
            return parsed

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
