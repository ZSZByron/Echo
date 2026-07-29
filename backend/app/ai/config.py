"""Configuration for LLM provider abstraction.

Reads provider settings from environment variables.
Supports: openai, anthropic, deepseek, qwen, kimi, glm.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    """Immutable configuration for an LLM provider.

    Attributes:
        provider_type: Provider identifier (openai|anthropic|deepseek|qwen|kimi|glm).
        base_url: API endpoint URL for the provider.
        api_key: API key for authentication.
        model: Model identifier string.
        temperature: Sampling temperature (0.0-2.0).
        max_tokens: Maximum tokens in the response.
    """

    provider_type: str
    base_url: str
    api_key: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 1000


# Default model names per provider (used as fallbacks)
_DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-20241022",
    "deepseek": "deepseek-chat",
    "qwen": "qwen-plus",
    "kimi": "moonshot-v1-8k",
    "glm": "glm-4",
}

# Default base URLs per provider
_DEFAULT_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "deepseek": "https://api.deepseek.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "kimi": "https://api.moonshot.cn/v1",
    "glm": "https://open.bigmodel.cn/api/paas/v4",
}

_VALID_PROVIDERS = frozenset(_DEFAULT_MODELS.keys())


def load_provider_config() -> ProviderConfig:
    """Read provider configuration from environment variables.

    Reads ACTIVE_PROVIDER to determine which provider to use,
    then loads the corresponding {PROVIDER}_API_KEY, {PROVIDER}_BASE_URL,
    and {PROVIDER}_MODEL environment variables.

    Returns:
        ProviderConfig with settings from environment.

    Raises:
        ValueError: If ACTIVE_PROVIDER is not set or is invalid.
    """
    provider_type = os.environ.get("ACTIVE_PROVIDER", "").strip().lower()

    if not provider_type:
        raise ValueError(
            "ACTIVE_PROVIDER environment variable is not set. "
            f"Must be one of: {', '.join(sorted(_VALID_PROVIDERS))}"
        )

    if provider_type not in _VALID_PROVIDERS:
        raise ValueError(
            f"Unknown provider '{provider_type}'. "
            f"Must be one of: {', '.join(sorted(_VALID_PROVIDERS))}"
        )

    prefix = provider_type.upper()
    api_key = os.environ.get(f"{prefix}_API_KEY", "")
    base_url = os.environ.get(
        f"{prefix}_BASE_URL", _DEFAULT_BASE_URLS[provider_type]
    )
    model = os.environ.get(f"{prefix}_MODEL", _DEFAULT_MODELS[provider_type])

    if not api_key:
        raise ValueError(
            f"{prefix}_API_KEY environment variable is not set for provider '{provider_type}'"
        )

    return ProviderConfig(
        provider_type=provider_type,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )
