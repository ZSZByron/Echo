"""Unit tests for LLM provider abstraction layer."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.config import ProviderConfig, load_provider_config
from app.ai.provider import (
    AnthropicProvider,
    LLMProvider,
    OpenAICompatibleProvider,
    create_provider,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_config(
    provider_type: str = "openai",
    api_key: str = "test-key",
    base_url: str = "https://api.example.com/v1",
    model: str = "test-model",
) -> ProviderConfig:
    return ProviderConfig(
        provider_type=provider_type,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )


def _make_openai_mock_client() -> AsyncMock:
    """Create a mock OpenAI client with proper async chat completions."""
    mock_client = AsyncMock()
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock()
    return mock_client


def _make_anthropic_mock_client() -> AsyncMock:
    """Create a mock Anthropic client with proper async messages."""
    mock_client = AsyncMock()
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock()
    return mock_client


# ── Factory dispatch tests ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "ptype",
    ["openai", "deepseek", "qwen", "kimi", "glm"],
)
@patch("openai.AsyncOpenAI", autospec=True)
def test_create_provider_openai_compatible(
    mock_openai_cls: MagicMock, ptype: str
) -> None:
    config = _make_config(provider_type=ptype)
    provider = create_provider(config)
    assert isinstance(provider, OpenAICompatibleProvider)


@patch("anthropic.AsyncAnthropic", autospec=True)
def test_create_provider_anthropic(mock_anthropic_cls: MagicMock) -> None:
    config = _make_config(provider_type="anthropic")
    provider = create_provider(config)
    assert isinstance(provider, AnthropicProvider)


def test_create_provider_invalid() -> None:
    config = _make_config(provider_type="unknown")
    with pytest.raises(ValueError, match="Unknown provider type: unknown"):
        create_provider(config)


# ── OpenAICompatibleProvider tests ───────────────────────────────────────────


@patch("openai.AsyncOpenAI", autospec=True)
async def test_openai_chat_returns_text(mock_openai_cls: MagicMock) -> None:
    mock_client = _make_openai_mock_client()
    mock_openai_cls.return_value = mock_client

    mock_message = MagicMock()
    mock_message.content = "Hello world"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    config = _make_config()
    provider = OpenAICompatibleProvider(config)

    result = await provider.chat([{"role": "user", "content": "Hi"}])
    assert result == "Hello world"

    mock_client.chat.completions.create.assert_awaited_once()
    call_kwargs = mock_client.chat.completions.create.call_args
    assert call_kwargs.kwargs["model"] == "test-model"


@patch("openai.AsyncOpenAI", autospec=True)
async def test_openai_chat_json_returns_dict(mock_openai_cls: MagicMock) -> None:
    mock_client = _make_openai_mock_client()
    mock_openai_cls.return_value = mock_client

    json_str = '{"key": "value", "num": 42}'
    mock_message = MagicMock()
    mock_message.content = json_str
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    config = _make_config()
    provider = OpenAICompatibleProvider(config)

    result = await provider.chat_json([{"role": "user", "content": "Give JSON"}])
    assert result == {"key": "value", "num": 42}

    call_kwargs = mock_client.chat.completions.create.call_args
    assert call_kwargs.kwargs["response_format"] == {"type": "json_object"}


@patch("openai.AsyncOpenAI", autospec=True)
async def test_openai_chat_empty_content(mock_openai_cls: MagicMock) -> None:
    mock_client = _make_openai_mock_client()
    mock_openai_cls.return_value = mock_client

    mock_message = MagicMock()
    mock_message.content = None
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    provider = OpenAICompatibleProvider(_make_config())
    result = await provider.chat([{"role": "user", "content": "Hi"}])
    assert result == ""


# ── AnthropicProvider tests ──────────────────────────────────────────────────


@patch("anthropic.AsyncAnthropic", autospec=True)
async def test_anthropic_chat_converts_messages(
    mock_anthropic_cls: MagicMock,
) -> None:
    mock_client = _make_anthropic_mock_client()
    mock_anthropic_cls.return_value = mock_client

    mock_block = MagicMock()
    mock_block.text = "Response text"
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_client.messages.create.return_value = mock_response

    config = _make_config(provider_type="anthropic")
    provider = AnthropicProvider(config)

    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
    ]
    result = await provider.chat(messages)
    assert result == "Response text"

    call_kwargs = mock_client.messages.create.call_args
    assert call_kwargs.kwargs["system"] == "You are helpful."
    assert call_kwargs.kwargs["messages"] == [{"role": "user", "content": "Hello"}]


@patch("anthropic.AsyncAnthropic", autospec=True)
async def test_anthropic_chat_no_system(mock_anthropic_cls: MagicMock) -> None:
    mock_client = _make_anthropic_mock_client()
    mock_anthropic_cls.return_value = mock_client

    mock_block = MagicMock()
    mock_block.text = "OK"
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_client.messages.create.return_value = mock_response

    provider = AnthropicProvider(_make_config(provider_type="anthropic"))
    result = await provider.chat([{"role": "user", "content": "Hi"}])
    assert result == "OK"

    call_kwargs = mock_client.messages.create.call_args
    assert "system" not in call_kwargs.kwargs


@patch("anthropic.AsyncAnthropic", autospec=True)
async def test_anthropic_chat_json_parses_response(
    mock_anthropic_cls: MagicMock,
) -> None:
    mock_client = _make_anthropic_mock_client()
    mock_anthropic_cls.return_value = mock_client

    # Provider prepends "{" so the raw text is the rest of JSON
    raw_tail = '"key": "val", "n": 1}'
    mock_block = MagicMock()
    mock_block.text = raw_tail
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_client.messages.create.return_value = mock_response

    provider = AnthropicProvider(_make_config(provider_type="anthropic"))
    messages = [{"role": "user", "content": "Give JSON"}]
    result = await provider.chat_json(messages)
    assert result == {"key": "val", "n": 1}

    # Verify the prefill assistant message was NOT included in the API call
    call_kwargs = mock_client.messages.create.call_args
    sent_messages = call_kwargs.kwargs["messages"]
    assert all(m["role"] != "assistant" for m in sent_messages)


# ── Config loading tests ─────────────────────────────────────────────────────


def test_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACTIVE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://custom.api.com/v1")

    config = load_provider_config()
    assert config.provider_type == "openai"
    assert config.api_key == "sk-test-key"
    assert config.model == "gpt-4o-mini"
    assert config.base_url == "https://custom.api.com/v1"


def test_config_invalid_provider_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ACTIVE_PROVIDER", "invalid_provider")
    monkeypatch.setenv("INVALID_PROVIDER_API_KEY", "some-key")

    with pytest.raises(ValueError, match="Unknown provider"):
        load_provider_config()


def test_config_missing_provider_raises() -> None:
    env_copy = dict(os.environ)
    env_copy.pop("ACTIVE_PROVIDER", None)
    with patch.dict(os.environ, env_copy, clear=True):
        with pytest.raises(ValueError, match="ACTIVE_PROVIDER"):
            load_provider_config()


# ── Abstract class tests ─────────────────────────────────────────────────────


def test_llm_provider_is_abstract() -> None:
    """LLMProvider cannot be instantiated directly."""
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]


def test_subclass_must_implement_chat() -> None:
    """Subclass missing chat() raises TypeError."""

    class Incomplete(LLMProvider):
        async def chat_json(self, messages, **kwargs):  # type: ignore[override]
            return {}

    with pytest.raises(TypeError):
        Incomplete(_make_config())  # type: ignore[abstract]


def test_subclass_must_implement_chat_json() -> None:
    """Subclass missing chat_json() raises TypeError."""

    class Incomplete(LLMProvider):
        async def chat(self, messages, **kwargs):  # type: ignore[override]
            return ""

    with pytest.raises(TypeError):
        Incomplete(_make_config())  # type: ignore[abstract]


# ── OpenAICompatibleProvider chat_json robustness tests ───────────────────────


@patch("openai.AsyncOpenAI", autospec=True)
async def test_openai_chat_json_parses_fenced_json(mock_openai_cls: MagicMock) -> None:
    """Fenced JSON (```json {...}```) should be extracted and parsed."""
    mock_client = _make_openai_mock_client()
    mock_openai_cls.return_value = mock_client

    fenced_json = '```json\n{"result": "success", "value": 42}\n```'
    mock_message = MagicMock()
    mock_message.content = fenced_json
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    config = _make_config()
    provider = OpenAICompatibleProvider(config)

    result = await provider.chat_json([{"role": "user", "content": "Give JSON"}])
    assert result == {"result": "success", "value": 42}


@patch("openai.AsyncOpenAI", autospec=True)
async def test_openai_chat_json_parses_prose_wrapped_json(
    mock_openai_cls: MagicMock,
) -> None:
    """JSON wrapped in prose should be extracted and parsed."""
    mock_client = _make_openai_mock_client()
    mock_openai_cls.return_value = mock_client

    prose_wrapped = "好的，以下是结果：{\"answer\": true, \"score\": 95} 希望有帮助"
    mock_message = MagicMock()
    mock_message.content = prose_wrapped
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    provider = OpenAICompatibleProvider(_make_config())
    result = await provider.chat_json([{"role": "user", "content": "Give JSON"}])
    assert result == {"answer": True, "score": 95}


@patch("openai.AsyncOpenAI", autospec=True)
async def test_openai_chat_json_bad_request_falls_back_to_no_response_format(
    mock_openai_cls: MagicMock,
) -> None:
    """BadRequestError on response_format should retry without it and succeed."""
    mock_client = _make_openai_mock_client()
    mock_openai_cls.return_value = mock_client

    # First call with response_format raises BadRequestError
    from openai import BadRequestError
    bad_request_error = BadRequestError(
        message="400 Bad Request: response_format not supported",
        response=MagicMock(status_code=400),
        body={},
    )
    mock_client.chat.completions.create.side_effect = [
        bad_request_error,  # First call fails
        MagicMock(  # Second call succeeds
            choices=[
                MagicMock(
                    message=MagicMock(content='{"fallback": "worked"}')
                )
            ]
        ),
    ]

    provider = OpenAICompatibleProvider(_make_config())
    result = await provider.chat_json([{"role": "user", "content": "Give JSON"}])
    assert result == {"fallback": "worked"}

    # Verify create was called twice: first with response_format, second without
    assert mock_client.chat.completions.create.call_count == 2
    first_call_kwargs = mock_client.chat.completions.create.call_args_list[0].kwargs
    assert first_call_kwargs["response_format"] == {"type": "json_object"}
    second_call_kwargs = mock_client.chat.completions.create.call_args_list[1].kwargs
    assert "response_format" not in second_call_kwargs


@patch("openai.AsyncOpenAI", autospec=True)
async def test_openai_chat_json_garbage_raises_runtime_error(
    mock_openai_cls: MagicMock,
) -> None:
    """Non-JSON garbage after both attempts should raise RuntimeError."""
    mock_client = _make_openai_mock_client()
    mock_openai_cls.return_value = mock_client

    garbage_response = "This is definitely not JSON, just random text here."
    mock_message = MagicMock()
    mock_message.content = garbage_response
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    provider = OpenAICompatibleProvider(_make_config())
    with pytest.raises(RuntimeError, match="chat_json: no parseable JSON"):
        await provider.chat_json([{"role": "user", "content": "Give JSON"}])


@patch("openai.AsyncOpenAI", autospec=True)
async def test_openai_chat_json_empty_content_returns_empty_dict(
    mock_openai_cls: MagicMock,
) -> None:
    """Empty content should return empty dict (existing behavior)."""
    mock_client = _make_openai_mock_client()
    mock_openai_cls.return_value = mock_client

    mock_message = MagicMock()
    mock_message.content = None
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    provider = OpenAICompatibleProvider(_make_config())
    result = await provider.chat_json([{"role": "user", "content": "Give JSON"}])
    assert result == {}


@patch("openai.AsyncOpenAI", autospec=True)
async def test_openai_thinking_disabled_deepseek(mock_openai_cls: MagicMock) -> None:
    """DeepSeek provider should disable thinking in extra_body."""
    mock_client = _make_openai_mock_client()
    mock_openai_cls.return_value = mock_client

    mock_message = MagicMock()
    mock_message.content = '{"ok": 1}'
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    config = _make_config(provider_type="deepseek")
    provider = OpenAICompatibleProvider(config)
    await provider.chat([{"role": "user", "content": "Hi"}])

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert "extra_body" in call_kwargs
    assert call_kwargs["extra_body"]["thinking"] == {"type": "disabled"}
    assert call_kwargs["extra_body"]["enable_thinking"] is False


@patch("openai.AsyncOpenAI", autospec=True)
async def test_openai_thinking_disabled_qwen(mock_openai_cls: MagicMock) -> None:
    """Qwen provider should disable enable_thinking in extra_body."""
    mock_client = _make_openai_mock_client()
    mock_openai_cls.return_value = mock_client

    mock_message = MagicMock()
    mock_message.content = '{"ok": 1}'
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    config = _make_config(provider_type="qwen")
    provider = OpenAICompatibleProvider(config)
    await provider.chat([{"role": "user", "content": "Hi"}])

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert "extra_body" in call_kwargs
    assert call_kwargs["extra_body"]["enable_thinking"] is False


@patch("openai.AsyncOpenAI", autospec=True)
async def test_openai_thinking_disabled_glm(mock_openai_cls: MagicMock) -> None:
    """GLM provider should disable both thinking and enable_thinking."""
    mock_client = _make_openai_mock_client()
    mock_openai_cls.return_value = mock_client

    mock_message = MagicMock()
    mock_message.content = '{"ok": 1}'
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_response

    config = _make_config(provider_type="glm")
    provider = OpenAICompatibleProvider(config)
    await provider.chat([{"role": "user", "content": "Hi"}])

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert "extra_body" in call_kwargs
    assert call_kwargs["extra_body"]["thinking"] == {"type": "disabled"}
    assert call_kwargs["extra_body"]["enable_thinking"] is False


# ── AnthropicProvider chat_json robustness tests ───────────────────────────────


@patch("anthropic.AsyncAnthropic", autospec=True)
async def test_anthropic_chat_json_system_only_messages_nonempty(
    mock_anthropic_cls: MagicMock,
) -> None:
    """System-only input should not result in empty messages list to API."""
    mock_client = _make_anthropic_mock_client()
    mock_anthropic_cls.return_value = mock_client

    raw_tail = '"result": "ok"}'
    mock_block = MagicMock()
    mock_block.text = raw_tail
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_client.messages.create.return_value = mock_response

    provider = AnthropicProvider(_make_config(provider_type="anthropic"))
    # System-only message (real use case: interviewer.py suggest_examples)
    messages = [{"role": "system", "content": "Return JSON only."}]
    result = await provider.chat_json(messages)
    assert result == {"result": "ok"}

    # Verify API received non-empty messages
    call_kwargs = mock_client.messages.create.call_args
    sent_messages = call_kwargs.kwargs["messages"]
    assert len(sent_messages) > 0, "API should receive non-empty messages"


@patch("anthropic.AsyncAnthropic", autospec=True)
async def test_anthropic_chat_json_multi_block_concatenated(
    mock_anthropic_cls: MagicMock,
) -> None:
    """Multiple text blocks should be concatenated before parsing."""
    mock_client = _make_anthropic_mock_client()
    mock_anthropic_cls.return_value = mock_client

    # Two blocks: first part + second part
    block1 = MagicMock()
    block1.text = '"key":'
    block2 = MagicMock()
    block2.text = ' "value"}'
    mock_response = MagicMock()
    mock_response.content = [block1, block2]
    mock_client.messages.create.return_value = mock_response

    provider = AnthropicProvider(_make_config(provider_type="anthropic"))
    messages = [{"role": "user", "content": "Give JSON"}]
    result = await provider.chat_json(messages)
    # After prepending "{" we get {"key": "value"}
    assert result == {"key": "value"}


@patch("anthropic.AsyncAnthropic", autospec=True)
async def test_anthropic_chat_json_complete_object_despite_prefill(
    mock_anthropic_cls: MagicMock,
) -> None:
    """Model may emit complete object despite prefill; should still parse."""
    mock_client = _make_anthropic_mock_client()
    mock_anthropic_cls.return_value = mock_client

    # Model ignores prefill and returns complete JSON
    complete_json = '{"answer": 42}'
    mock_block = MagicMock()
    mock_block.text = complete_json
    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_client.messages.create.return_value = mock_response

    provider = AnthropicProvider(_make_config(provider_type="anthropic"))
    messages = [{"role": "user", "content": "Give JSON"}]
    result = await provider.chat_json(messages)
    assert result == {"answer": 42}
