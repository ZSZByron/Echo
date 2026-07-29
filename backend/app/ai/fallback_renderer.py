"""Standalone fallback renderer - no LLM needed."""

from __future__ import annotations

from app.models.action import JudgmentOutcome, JudgmentResult


def template_render(judgment: JudgmentResult) -> str:
    """Render judgment using simple templates. No AI required."""
    outcome = judgment.result
    reason = judgment.reason

    if outcome == JudgmentOutcome.FORCED_FAIL:
        god = judgment.god_intervention or "未知力量"
        return (
            f"[WARN] 系统警告：检测到超自然干涉\n"
            f"[EVENT] 神王「{god}」的意志降临\n"
            f"[SYSTEM] 判决：强制失败\n"
            f"原因：{reason}"
        )
    if outcome == JudgmentOutcome.FAIL:
        return (
            f"[SYSTEM] 判决：失败\n"
            f"原因：{reason}\n"
            f"[EVENT] 行动未能成功完成"
        )
    return f"[SYSTEM] 判决：成功\n[EVENT] {reason}"
