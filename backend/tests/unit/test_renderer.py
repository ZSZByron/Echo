"""Tests for NarrativeRenderer and fallback_renderer."""  

from __future__ import annotations  

from unittest.mock import AsyncMock, call  

import pytest  

from app.ai.fallback_renderer import template_render  
from app.ai.renderer import NarrativeRenderer  
from app.ai.provider import LLMProvider  
from app.models.action import (  
    JudgmentOutcome,  
    JudgmentResult,  
    NarrativeContext,  
    ParsedIntent,  
    ActionType,  
)  


@pytest.fixture  
def mock_provider() -> LLMProvider:  
    """Create a mock LLMProvider."""  
    return AsyncMock(spec=LLMProvider)  


@pytest.fixture  
def renderer(mock_provider: LLMProvider) -> NarrativeRenderer:  
    """Create NarrativeRenderer with mock provider."""  
    return NarrativeRenderer(mock_provider)  


@pytest.fixture  
def sample_context() -> NarrativeContext:  
    """Create a sample narrative context."""  
    return NarrativeContext(  
        scene_id="temple_entrance",  
        atmosphere="阴暗潮湿",  
        tension_level=60,  
    )  


@pytest.fixture  
def sample_intent() -> ParsedIntent:  
    """Create a sample parsed intent."""  
    return ParsedIntent(  
        action_type=ActionType.BRUTE_FORCE,  
        target="ancient_locked_door",  
        intensity="maximum",  
        risk_acceptance=True,  
        raw_input="我砸开门",  
        confidence=0.9,  
    )  


@pytest.fixture  
def success_judgment(sample_context: NarrativeContext) -> JudgmentResult:  
    """Create a success judgment."""  
    return JudgmentResult(  
        result=JudgmentOutcome.SUCCESS,  
        reason="力量足够，门被砸开",  
        narrative_context=sample_context,  
    )  


@pytest.fixture  
def fail_judgment(sample_context: NarrativeContext) -> JudgmentResult:  
    """Create a fail judgment."""  
    return JudgmentResult(  
        result=JudgmentOutcome.FAIL,  
        reason="力量不足，门纹丝不动",  
        narrative_context=sample_context,  
    )  


@pytest.fixture  
def forced_fail_judgment(sample_context: NarrativeContext) -> JudgmentResult:  
    """Create a forced_fail judgment."""  
    return JudgmentResult(  
        result=JudgmentOutcome.FORCED_FAIL,  
        reason="神王阿努比斯介入",  
        god_intervention="阿努比斯",  
        narrative_context=sample_context,  
    )  


@pytest.mark.asyncio  
async def test_success_rendering(  
    renderer: NarrativeRenderer,  
    mock_provider: LLMProvider,  
    success_judgment: JudgmentResult,  
    sample_intent: ParsedIntent,  
    sample_context: NarrativeContext,  
) -> None:  
    """Mock returns text -> verify text returned."""  
    mock_provider.chat.return_value = "[SYSTEM] 门被暴力砸开，碎片四溅。"  
    result = await renderer.render(success_judgment, sample_intent, {"scene": "temple"})  
    assert result == "[SYSTEM] 门被暴力砸开，碎片四溅。"  
    mock_provider.chat.assert_called_once()  


@pytest.mark.asyncio  
async def test_fail_rendering(  
    renderer: NarrativeRenderer,  
    mock_provider: LLMProvider,  
    fail_judgment: JudgmentResult,  
    sample_intent: ParsedIntent,  
) -> None:  
    """Fail judgment uses different prompt path."""  
    mock_provider.chat.return_value = "[SYSTEM] 力量不足，门纹丝不动。"  
    result = await renderer.render(fail_judgment, sample_intent, {})  
    assert result == "[SYSTEM] 力量不足，门纹丝不动。"  
    # Verify the prompt contains fail-specific mood  
    call_args = mock_provider.chat.call_args  
    messages = call_args[0][0] if call_args else []  
    user_msg = messages[1]["content"] if len(messages) > 1 else ""  
    assert "物理失败" in user_msg  


@pytest.mark.asyncio  
async def test_forced_fail_rendering(  
    renderer: NarrativeRenderer,  
    mock_provider: LLMProvider,  
    forced_fail_judgment: JudgmentResult,  
    sample_intent: ParsedIntent,  
) -> None:  
    """Forced fail judgment includes god intervention prompt."""  
    mock_provider.chat.return_value = "[WARN] 低语声在耳边响起..."  
    result = await renderer.render(forced_fail_judgment, sample_intent, {})  
    assert result == "[WARN] 低语声在耳边响起..."  
    call_args = mock_provider.chat.call_args  
    messages = call_args[0][0] if call_args else []  
    user_msg = messages[1]["content"] if len(messages) > 1 else ""  
    assert "神王干涉" in user_msg  
    assert "低语" in user_msg  


@pytest.mark.asyncio  
async def test_llm_exception_fallback(  
    renderer: NarrativeRenderer,  
    mock_provider: LLMProvider,  
    success_judgment: JudgmentResult,  
    sample_intent: ParsedIntent,  
) -> None:  
    """Provider raises -> fallback template used."""  
    mock_provider.chat.side_effect = RuntimeError("API error")  
    result = await renderer.render(success_judgment, sample_intent, {})  
    assert "[SYSTEM]" in result  
    assert "success" in result  
    assert "力量足够" in result  


@pytest.mark.asyncio  
async def test_empty_response_fallback(  
    renderer: NarrativeRenderer,  
    mock_provider: LLMProvider,  
    success_judgment: JudgmentResult,  
    sample_intent: ParsedIntent,  
) -> None:  
    """Provider returns empty string -> fallback template used."""  
    mock_provider.chat.return_value = ""  
    result = await renderer.render(success_judgment, sample_intent, {})  
    assert "[SYSTEM]" in result  


def test_fallback_render_success(success_judgment: JudgmentResult) -> None:  
    """Fallback renderer for success."""  
    result = template_render(success_judgment)  
    assert "[SYSTEM]" in result  
    assert "成功" in result  
    assert "力量足够" in result  


def test_fallback_render_fail(fail_judgment: JudgmentResult) -> None:  
    """Fallback renderer for fail."""  
    result = template_render(fail_judgment)  
    assert "[SYSTEM]" in result  
    assert "失败" in result  
    assert "力量不足" in result  
    assert "[EVENT]" in result  


def test_fallback_render_forced_fail(  
    forced_fail_judgment: JudgmentResult,  
) -> None:  
    """Fallback renderer for forced_fail includes god name."""  
    result = template_render(forced_fail_judgment)  
    assert "[WARN]" in result  
    assert "阿努比斯" in result  
    assert "强制失败" in result  
    assert "[EVENT]" in result  


def test_fallback_render_no_god(sample_context: NarrativeContext) -> None:  
    """Forced fail with no god name uses default."""  
    judgment = JudgmentResult(  
        result=JudgmentOutcome.FORCED_FAIL,  
        reason="未知力量介入",  
        god_intervention=None,  
        narrative_context=sample_context,  
    )  
    result = template_render(judgment)  
    assert "未知力量" in result  


def test_renderer_fallback_render_method(  
    renderer: NarrativeRenderer, success_judgment: JudgmentResult,  
) -> None:  
    """Test _fallback_render directly."""  
    result = renderer._fallback_render(success_judgment)  
    assert "[SYSTEM]" in result  
    assert "success" in result