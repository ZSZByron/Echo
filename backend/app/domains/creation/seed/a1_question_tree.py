"""A1 question tree — 10 fixed sections with scripted questions.

The AI never invents questions (计划铁律: AI不发明问题) — this module is a
pure static structure + a simple sequential state machine.

Section ids are the 10 Chinese keys shared with preset_loader.SECTION_KEYS.
"""
from __future__ import annotations

from typing import TypedDict


class Section(TypedDict):
    id: str
    label: str
    question: str
    hint: str


SECTIONS: list[Section] = [
    {"id": "世界观", "label": "世界观", "question": "这个世界的底层秩序是什么？", "hint": "一两句话描述宇宙观与核心设定，例如'灵气枯竭的修真界'。"},
    {"id": "地理", "label": "地理", "question": "世界的主要地理格局是怎样的？", "hint": "大陆/星域/城邦的大致布局，例如'跃迁航道串联的殖民星域'。"},
    {"id": "力量体系", "label": "力量体系", "question": "力量从何而来，如何分级？", "hint": "魔法/科技/修炼体系与等级，例如'练气—筑基—金丹'。"},
    {"id": "历史纪元", "label": "历史纪元", "question": "世界正处在哪个历史阶段？", "hint": "关键历史事件与当前纪元，例如'王朝暮年的权力棋局'。"},
    {"id": "社会生态", "label": "社会生态", "question": "谁统治世界，人们如何共存？", "hint": "政治体制与族群关系，例如'宫廷派系、联姻与暗杀'。"},
    {"id": "经济", "label": "经济", "question": "财富以什么形式流动？", "hint": "货币与交易方式，例如'以物易物，子弹即货币'。"},
    {"id": "红线规则", "label": "红线规则", "question": "这个世界绝对禁止什么？", "hint": "内容红线与硬约束，例如'超自然遭遇附带理智检定'。"},
    {"id": "叙事基调", "label": "叙事基调", "question": "故事的整体情绪基调？", "hint": "压抑/热血/冷硬/浪漫等基调词，例如'冷硬、快节奏、黑色电影'。"},
    {"id": "美术风格", "label": "美术风格", "question": "世界的视觉风格关键词？", "hint": "画面风格词，例如'霓虹雨夜、义体改造、全息广告'。"},
    {"id": "核心冲突", "label": "核心冲突", "question": "驱动一切的根本矛盾是什么？", "hint": "核心对抗，例如'诸神苏醒与人类存续之争'。"},
]

_SECTION_ORDER: list[str] = [s["id"] for s in SECTIONS]
_SECTIONS_BY_ID: dict[str, Section] = {s["id"]: s for s in SECTIONS}


def first_section() -> Section:
    """Return the first section (世界观)."""
    return SECTIONS[0]


def get_section(section_id: str) -> Section | None:
    """Return a section by id, or None if unknown."""
    return _SECTIONS_BY_ID.get(section_id)


def next_section(current_id: str | None) -> Section | None:
    """Return the next section after *current_id*, or None at the end.

    Passing None returns the first section.
    """
    if current_id is None:
        return SECTIONS[0]
    if current_id not in _SECTION_ORDER:
        return None
    idx = _SECTION_ORDER.index(current_id)
    if idx + 1 >= len(_SECTION_ORDER):
        return None
    return SECTIONS[idx + 1]


def section_ids() -> list[str]:
    """Return the ordered list of all 10 section ids."""
    return list(_SECTION_ORDER)
