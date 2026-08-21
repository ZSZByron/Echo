"""A1 preset loader — 8 presets from seed-presets-catalog.md authority.

10 dimension sections (Chinese keys):
    worldview/地理/力量体系/历史纪元/社会生态/
    经济/红线规则/叙事基调/美术风格/核心冲突
"""

from __future__ import annotations

from dataclasses import dataclass, field


_TEN_SECTIONS: list[str] = [
    "世界观",
    "地理",
    "力量体系",
    "历史纪元",
    "社会生态",
    "经济",
    "红线规则",
    "叙事基调",
    "美术风格",
    "核心冲突",
]

_EMPTY_DEFAULTS: dict[str, str] = {s: "" for s in _TEN_SECTIONS}


@dataclass(frozen=True)
class PresetSeed:
    """Immutable preset seed with 10 dimension defaults."""

    id: int
    name: str
    genre: str
    description: str
    dimension_defaults: dict[str, str] = field(default_factory=lambda: dict(_EMPTY_DEFAULTS))


def load_presets() -> list[PresetSeed]:
    """Return the 8 authority presets.

    Source of truth: docs/governance/seed-presets-catalog.md
    dimension_defaults use 10 Chinese section keys; values are empty
    strings (to be filled by user via guided chat).
    """
    return [
        PresetSeed(
            id=1,
            name="深渊低语",
            genre="克苏鲁恐怖",
            description="压抑恐惧、理智崩溃、不可名状",
            dimension_defaults=dict(_EMPTY_DEFAULTS),
        ),
        PresetSeed(
            id=2,
            name="霓虹窃案",
            genre="赛博朋克",
            description="冷酷快节奏、科技驱动、愤世嫉俗",
            dimension_defaults=dict(_EMPTY_DEFAULTS),
        ),
        PresetSeed(
            id=3,
            name="腐化深渊",
            genre="黑暗奇幻",
            description="沉重宿命、腐化代价、史诗悲剧",
            dimension_defaults=dict(_EMPTY_DEFAULTS),
        ),
        PresetSeed(
            id=4,
            name="灰烬之路",
            genre="废土生存",
            description="务实求生、资源匮乏、道德困境",
            dimension_defaults=dict(_EMPTY_DEFAULTS),
        ),
        PresetSeed(
            id=5,
            name="碎天录",
            genre="东方仙侠",
            description="古雅超然、修仙逆天、因果业力",
            dimension_defaults=dict(_EMPTY_DEFAULTS),
        ),
        PresetSeed(
            id=6,
            name="群星彼岸",
            genre="太空歌剧",
            description="宏大辽阔、文明史诗、星际政治",
            dimension_defaults=dict(_EMPTY_DEFAULTS),
        ),
        PresetSeed(
            id=7,
            name="破晓之剑",
            genre="传统奇幻",
            description="明快史诗、英雄主义、魔法冒险",
            dimension_defaults=dict(_EMPTY_DEFAULTS),
        ),
        PresetSeed(
            id=8,
            name="鸩酒与玫瑰",
            genre="权谋阴谋",
            description="优雅锋利、信息博弈、政治暗流",
            dimension_defaults=dict(_EMPTY_DEFAULTS),
        ),
    ]
