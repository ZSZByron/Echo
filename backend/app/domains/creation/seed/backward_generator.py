"""Backward Generator — 跨维度反向推理生成。

核心创新：从任意维度反推其他维度。
    Asset → Story   (从物体反推叙事)
    Event → Asset   (从事件反推物体)
    Constraint → Culture  (从约束反推文化)
    ...

不同于正向填充（种子→LLM→四维），反向推理是定向的：
它从一个已填充的维度出发，推理一个特定目标维度。

算法流程：
    1. 构建维度对 prompt（source_dim → target_dim）
    2. 注入规则映射 hints（确定性基线）
    3. 注入风格指令（preset voice + lexicon）
    4. 调用 LLM chat_json
    5. 返回结构化内容
"""
from __future__ import annotations

import json
from typing import Any

from app.ai.provider import LLMProvider
from app.models.concept import FIVE_DIMENSIONS

# ---------------------------------------------------------------------------
# 维度对 prompt 模板
# ---------------------------------------------------------------------------

# 每个 (source_dim, target_dim) 对有专属的推理指令
# key 格式: "{source_dim}->{target_dim}"
# 未命中时使用通用模板

_DIRECTIONAL_PROMPTS: dict[str, str] = {
    # === Asset → other ===
    "asset->story": (
        "你是一个游戏叙事设计师。给定一个具体的物体/资产，请反推它可能属于什么故事。\n"
        "重点思考：这个物体为什么存在？谁制造了它？它引发了什么冲突？\n"
        "输出 JSON，包含 name（故事名）、description（剧情梗概）、type（main_quest/side_quest）、"
        "key_elements（关键元素列表）。"
    ),
    "asset->event": (
        "你是一个游戏事件设计师。给定一个具体的物体/资产，请设计围绕它发生的动态事件。\n"
        "重点思考：玩家如何与它互动？什么情况下触发事件？后果是什么？\n"
        "输出 JSON，包含 name（事件名）、description（事件描述）、"
        "trigger（含 type 和 condition）、event_type（combat/exploration/social/quest）。"
    ),
    "asset->culture": (
        "你是一个世界观设计师。给定一个具体的物体/资产，请反推它背后的文化/文明。\n"
        "重点思考：什么样的社会会制造/崇拜/使用这个物体？他们的价值观是什么？\n"
        "输出 JSON，包含 name（文化名）、values（价值观列表3项）、aesthetic_principles（美学原则列表3项）。"
    ),
    "asset->constraint": (
        "你是一个游戏规则设计师。给定一个具体的物体/资产，请推导围绕它的使用约束/规则。\n"
        "重点思考：使用它的前提条件是什么？滥用会有什么后果？\n"
        "输出 JSON，包含 rule（规则描述文本）、type（hard/soft）、priority（0-100）、"
        "applicable_types（适用类型列表）。"
    ),

    # === Story → other ===
    "story->asset": (
        "你是一个游戏资产设计师。给定一个剧情/任务描述，请设计这个故事中需要的核心物体/资产。\n"
        "重点思考：玩家需要什么关键道具？它长什么样？有什么特殊属性？\n"
        "输出 JSON，包含 name（资产名）、description（外观描述）、tags（标签列表3-4个）。"
    ),
    "story->event": (
        "你是一个游戏事件设计师。给定一个剧情/任务描述，请设计这个故事中的一个关键动态事件。\n"
        "重点思考：剧情推进中的高潮时刻是什么？什么触发了它？\n"
        "输出 JSON，包含 name（事件名）、description（事件描述）、"
        "trigger（含 type 和 condition）、event_type（combat/exploration/social/quest）。"
    ),
    "story->culture": (
        "你是一个世界观设计师。给定一个剧情/任务描述，请反推这个故事发生的文化背景。\n"
        "重点思考：什么样的社会价值观导致了这个冲突？故事中的人物信奉什么？\n"
        "输出 JSON，包含 name（文化名）、values（价值观列表3项）、aesthetic_principles（美学原则列表3项）。"
    ),
    "story->constraint": (
        "你是一个游戏规则设计师。给定一个剧情/任务描述，请推导这个故事中隐含的约束/规则。\n"
        "重点思考：故事世界中有什么物理法则/社会禁忌在起作用？\n"
        "输出 JSON，包含 rule（规则描述文本）、type（hard/soft）、priority（0-100）、"
        "applicable_types（适用类型列表）。"
    ),

    # === Event → other ===
    "event->story": (
        "你是一个游戏叙事设计师。给定一个动态事件描述，请反推它可能属于什么更大故事。\n"
        "重点思考：这个事件是更大叙事的哪个环节？前因后果是什么？\n"
        "输出 JSON，包含 name（故事名）、description（剧情梗概）、type（main_quest/side_quest）、"
        "key_elements（关键元素列表）。"
    ),
    "event->asset": (
        "你是一个游戏资产设计师。给定一个动态事件描述，请设计事件中涉及的核心物体/资产。\n"
        "重点思考：事件围绕什么物体展开？玩家需要什么道具来应对？\n"
        "输出 JSON，包含 name（资产名）、description（外观描述）、tags（标签列表3-4个）。"
    ),
    "event->culture": (
        "你是一个世界观设计师。给定一个动态事件描述，请反推事件发生社会的文化特征。\n"
        "重点思考：什么样的文化会催生或容忍这样的事件？\n"
        "输出 JSON，包含 name（文化名）、values（价值观列表3项）、aesthetic_principles（美学原则列表3项）。"
    ),
    "event->constraint": (
        "你是一个游戏规则设计师。给定一个动态事件描述，请推导事件隐含的约束/规则。\n"
        "重点思考：事件触发的条件暗示了什么世界法则？\n"
        "输出 JSON，包含 rule（规则描述文本）、type（hard/soft）、priority（0-100）、"
        "applicable_types（适用类型列表）。"
    ),

    # === Culture → other ===
    "culture->story": (
        "你是一个游戏叙事设计师。给定一个文化/文明描述，请设计一个体现该文化核心冲突的故事。\n"
        "重点思考：这个文化的内在矛盾是什么？什么危机在考验他们的价值观？\n"
        "输出 JSON，包含 name（故事名）、description（剧情梗概）、type（main_quest/side_quest）、"
        "key_elements（关键元素列表）。"
    ),
    "culture->asset": (
        "你是一个游戏资产设计师。给定一个文化/文明描述，请设计该文化的代表性物体/资产。\n"
        "重点思考：这个文化会制造什么标志性物品？它的美学风格是什么？\n"
        "输出 JSON，包含 name（资产名）、description（外观描述）、tags（标签列表3-4个）。"
    ),
    "culture->event": (
        "你是一个游戏事件设计师。给定一个文化/文明描述，请设计体现该文化特征的动态事件。\n"
        "重点思考：这个文化有什么仪式/传统/禁忌可以在游戏中触发？\n"
        "输出 JSON，包含 name（事件名）、description（事件描述）、"
        "trigger（含 type 和 condition）、event_type（combat/exploration/social/quest）。"
    ),
    "culture->constraint": (
        "你是一个游戏规则设计师。给定一个文化/文明描述，请推导该文化的社会约束/法则。\n"
        "重点思考：这个文化有什么行为禁忌？违反了会怎样？\n"
        "输出 JSON，包含 rule（规则描述文本）、type（hard/soft）、priority（0-100）、"
        "applicable_types（适用类型列表）。"
    ),

    # === Constraint → other ===
    "constraint->story": (
        "你是一个游戏叙事设计师。给定一条规则/约束，请设计一个被这条约束深刻影响的故事。\n"
        "重点思考：谁因为这个规则受苦？谁在挑战它？后果是什么？\n"
        "输出 JSON，包含 name（故事名）、description（剧情梗概）、type（main_quest/side_quest）、"
        "key_elements（关键元素列表）。"
    ),
    "constraint->asset": (
        "你是一个游戏资产设计师。给定一条规则/约束，请设计一个体现或绕过这条约束的物体/资产。\n"
        "重点思考：在这个规则下，人们发明了什么替代品？什么物品是规则的核心？\n"
        "输出 JSON，包含 name（资产名）、description（外观描述）、tags（标签列表3-4个）。"
    ),
    "constraint->event": (
        "你是一个游戏事件设计师。给定一条规则/约束，请设计一个由这条约束触发或违反它的动态事件。\n"
        "重点思考：什么情况下这条规则会被考验？违反它的即时后果是什么？\n"
        "输出 JSON，包含 name（事件名）、description（事件描述）、"
        "trigger（含 type 和 condition）、event_type（combat/exploration/social/quest）。"
    ),
    "constraint->culture": (
        "你是一个世界观设计师。给定一条规则/约束，请反推什么文化会制定并执行这条规则。\n"
        "重点思考：什么样的价值观导致了这条规则？违反者被如何对待？\n"
        "输出 JSON，包含 name（文化名）、values（价值观列表3项）、aesthetic_principles（美学原则列表3项）。"
    ),
}

_GENERIC_PROMPT = (
    "你是一个游戏世界设计师。请根据给定的{source_dim}内容，推理生成对应的{target_dim}内容。\n"
    "确保生成内容与源内容在主题、风格和逻辑上一致。"
)


def _get_directional_prompt(source_dim: str, target_dim: str) -> str:
    """获取维度对的专属推理指令。"""
    key = f"{source_dim}->{target_dim}"
    template = _DIRECTIONAL_PROMPTS.get(key)
    if template:
        return template
    return _GENERIC_PROMPT.replace("{source_dim}", source_dim).replace(
        "{target_dim}", target_dim
    )


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

async def backward_generate(
    seed_dim: str,
    seed_content: dict[str, Any],
    target_dim: str,
    provider: LLMProvider,
    style_guide: dict[str, Any] | None = None,
    rule_hints: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """从 seed_dim 反推 target_dim。

    Args:
        seed_dim: 种子维度名称（如 "asset"）。
        seed_content: 种子内容（如 {"name": "水晶祭坛", "description": "..."} ）。
        target_dim: 目标维度名称（如 "story"）。
        provider: LLM Provider 实例。
        style_guide: 风格指令（voice_prompt + lexicon），可选。
        rule_hints: 规则映射表的匹配结果列表，可选。
            每项含 {"rule": str, "template": str}。

    Returns:
        目标维度内容（dict），结构由目标维度决定。

    Raises:
        ValueError: 如果 seed_dim 或 target_dim 不在 FIVE_DIMENSIONS 中，
                    或 seed_dim == target_dim。
    """
    if seed_dim not in FIVE_DIMENSIONS:
        raise ValueError(f"Invalid seed_dim: {seed_dim!r}")
    if target_dim not in FIVE_DIMENSIONS:
        raise ValueError(f"Invalid target_dim: {target_dim!r}")
    if seed_dim == target_dim:
        raise ValueError("seed_dim and target_dim must differ")

    messages = _build_messages(
        seed_dim, seed_content, target_dim,
        style_guide, rule_hints,
    )
    return await provider.chat_json(messages)


# ---------------------------------------------------------------------------
# Prompt 构建
# ---------------------------------------------------------------------------

def _build_messages(
    seed_dim: str,
    seed_content: dict[str, Any],
    target_dim: str,
    style_guide: dict[str, Any] | None,
    rule_hints: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    """构建 LLM 调用的 messages 列表。

    结构：
        system: 方向指令 + 风格指令 + 规则 hints
        user: 种子内容 JSON
    """
    # --- System prompt ---
    system_parts: list[str] = []

    # 1. 方向指令
    directional = _get_directional_prompt(seed_dim, target_dim)
    system_parts.append(directional)

    # 2. 风格指令
    if style_guide:
        voice = style_guide.get("voice_prompt", "")
        lexicon = style_guide.get("lexicon", {})
        if voice:
            system_parts.append(f"\n## 叙述风格\n{voice}")
        if lexicon:
            system_parts.append(
                f"\n## 词汇约束\n请使用以下词汇库中的专有名词：\n"
                f"{json.dumps(lexicon, ensure_ascii=False, indent=2)}"
            )

    # 3. 规则 hints
    if rule_hints:
        hints_text = []
        for hint in rule_hints:
            rule_text = hint.get("rule", "")
            template_text = hint.get("template", "")
            hints_text.append(f"- 规则：{rule_text}")
            if template_text:
                hints_text.append(f"  模板：{template_text}")
        system_parts.append(
            f"\n## 确定性映射规则（请严格遵循）\n"
            + "\n".join(hints_text)
        )

    # 4. 通用约束
    system_parts.append(
        "\n## 输出要求\n"
        "- 输出必须是合法 JSON\n"
        "- 所有文本使用中文\n"
        "- 内容必须与种子内容主题一致\n"
        "- 不要输出任何 JSON 以外的文本"
    )

    system_prompt = "\n\n".join(system_parts)

    # --- User message ---
    seed_json = json.dumps(seed_content, ensure_ascii=False, indent=2)
    user_content = (
        f"请根据以下{seed_dim}维度的内容，\n"
        f"推理生成{target_dim}维度的内容：\n\n"
        f"{seed_json}"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
