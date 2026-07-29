"""Prompt templates for intent parsing."""

import json

SYSTEM_PROMPT = """你是一个游戏意图解析器。将玩家的自然语言输入解析为结构化JSON。
必须返回以下格式的JSON：
{
  "action_type": "brute_force|stealth|read_memory|negotiate|probe|god_provoke|investigate",
  "target": "目标对象ID或null",
  "intensity": "low|medium|maximum",
  "risk_acceptance": true|false,
  "tool_used": "使用的工具或null"
}

action_type白名单（ ONLY these values, no others）：
- brute_force: 暴力破坏、砸、撞、强行打开
- stealth: 潜行、偷窃、悄悄、隐蔽
- read_memory: 读取记忆、回响模式、查看历史
- negotiate: 谈判、交涉、沟通、对话
- probe: 探查、检查、观察、分析
- god_provoke: 挑衅神王、亵渎、挑战神
- investigate: 调查、搜索、探索

已知目标对象：
- ancient_locked_door (古锁门)
- priest_corpse_01 (祭司尸体)
- holographic_altar (全息祭坛)
- neon_circuit_pillar (霓虹电路柱)
"""

_FewShotExample = dict[str, str | dict[str, str | bool | None]]

FEW_SHOT_EXAMPLES: list[_FewShotExample] = [
    {
        "input": "我强行砸开这个锁",
        "output": {
            "action_type": "brute_force",
            "target": "ancient_locked_door",
            "intensity": "maximum",
            "risk_acceptance": True,
            "tool_used": None,
        },
    },
    {
        "input": "我想悄悄绕过这扇门",
        "output": {
            "action_type": "stealth",
            "target": "ancient_locked_door",
            "intensity": "low",
            "risk_acceptance": False,
            "tool_used": None,
        },
    },
    {
        "input": "我用回响模式读取尸体的记忆",
        "output": {
            "action_type": "read_memory",
            "target": "priest_corpse_01",
            "intensity": "medium",
            "risk_acceptance": True,
            "tool_used": "echo_mode",
        },
    },
    {
        "input": "我向神王挑衅",
        "output": {
            "action_type": "god_provoke",
            "target": None,
            "intensity": "maximum",
            "risk_acceptance": True,
            "tool_used": None,
        },
    },
]


def build_parser_messages(player_input: str) -> list[dict[str, str]]:
    """Build the message list for the LLM parser."""
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for example in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": str(example["input"])})
        messages.append({
            "role": "assistant",
            "content": json.dumps(example["output"], ensure_ascii=False),
        })
    messages.append({"role": "user", "content": player_input})
    return messages
