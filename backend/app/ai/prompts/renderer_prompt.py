"""Prompt templates for narrative rendering."""

import json

SYSTEM_PROMPT = """你是"回声系统"的终端播报员。你的任务是将以冷酷的规则判决转化为沉浸式的赛博朋克叙事。

风格要求：
- 客观但略带悲悯的语调
- 使用[SYSTEM]、[WARN]、[EVENT]标签格式
- 赛博朋克+神话氛围
- 不超过500字
- 根据判决结果调整语气

判决分支语气：
- success: 简洁有力的成功描述
- fail: 带有物理细节的失败描述
- forced_fail: 神秘、压迫感的神王干涉描述，包含"低语"和"超自然"元素
"""


def build_renderer_messages(
    judgment_result: dict[str, object],
    intent: dict[str, object],
    context: dict[str, object],
) -> list[dict[str, str]]:
    """Build messages for narrative rendering based on judgment outcome."""
    outcome = judgment_result.get("result", "success")

    if outcome == "forced_fail":
        mood = (
            "神王干涉。用神秘、压迫感的语调描述。"
            "包含低语声、超自然现象。玩家的行动被不可抗拒的力量阻止。"
        )
    elif outcome == "fail":
        mood = "物理失败。描述力量不足的细节，环境的反馈。"
    else:
        mood = "成功。简洁描述行动的结果和环境的反应。"

    user_content = (
        f"判决结果: {json.dumps(judgment_result, ensure_ascii=False)}\n"
        f"玩家意图: {json.dumps(intent, ensure_ascii=False)}\n"
        f"场景上下文: {json.dumps(context, ensure_ascii=False)}\n"
        f"叙事要求: {mood}\n"
        "\n请生成终端播报文本："
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
