"""概念关系词典 (Task T-A 用户产品决策).

设计要点：
- 节点 = 从回答内容中拆出的概念词（两阶段抽取，见 concept_edge_extractor.py V2 部分）
- 边关系名 = 本词典（不用 v0.4 槽位词表 concept_edge_vocab.py 那套）
- 种子 10 条：★rule 3条 / ◆semantic 5条 / ◇structure 2条（name 逐字对应用户决策）
- 运行时可增长：LLM 提议新关系 → 用户确认 → RelationRegistry.add（默认◆semantic）

与 concept_edge_vocab.py 的区别：
- concept_edge_vocab: v0.4 静态封闭词表（槽位→槽位的派生边，不可增长）
- 本模块: 概念词→概念词的关系名词典，运行时经用户确认入典

Reference:
- concept_edge_vocab.py (静态词典样式参照)
- concept_edge_extractor.py (extract_concept_relations 消费本词典)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RelationSpec:
    """一条概念关系的规格。

    Attributes:
        name: 关系名（如 "引发"）
        level: 可信度层级（★=rule, ◆=semantic, ◇=structure）
        gloss: 语义说明
        example: 示例（如 "业报→反弹"）
    """

    name: str
    level: Literal["rule", "semantic", "structure"]
    gloss: str
    example: str = ""


# =============================================================================
# RELATION_VOCAB: 种子表 10 条（逐字录入用户决策）
# Level counts: 3 ★ (rule) + 5 ◆ (semantic) + 2 ◇ (structure)
# =============================================================================

RELATION_VOCAB: list[RelationSpec] = [
    # ★ rule (3) - 机器可执行/确定性判定
    RelationSpec(
        name="隶属",
        level="rule",
        gloss="A是B的组成部分/实例",
        example="星舰文明→阿努比斯结社",
    ),
    RelationSpec(
        name="对立",
        level="rule",
        gloss="A与B互斥对抗",
        example="观星城↔铸环城",
    ),
    RelationSpec(
        name="等同",
        level="rule",
        gloss="A与B是同一概念的不同表述",
        example="死亡轮回=转生",
    ),
    # ◆ semantic (5) - LLM 推断+用户确认
    RelationSpec(
        name="引发",
        level="semantic",
        gloss="A导致/触发B",
        example="业报→反弹",
    ),
    RelationSpec(
        name="转化",
        level="semantic",
        gloss="A可变为B",
        example="死亡→转生",
    ),
    RelationSpec(
        name="依赖",
        level="semantic",
        gloss="A的存在需要B",
        example="精神共鸣→共同理念",
    ),
    RelationSpec(
        name="象征",
        level="semantic",
        gloss="A代表/隐喻B",
        example="轮回之门→死亡真理",
    ),
    RelationSpec(
        name="制约",
        level="semantic",
        gloss="A限制/约束B",
        example="业报守恒→力量使用",
    ),
    # ◇ structure (2) - 结构性共在/分支
    RelationSpec(
        name="共现",
        level="structure",
        gloss="A与B在同一设定中共现",
        example="黑曜石+荧光苔藓",
    ),
    RelationSpec(
        name="分型",
        level="structure",
        gloss="A是B的变体/分支",
        example="星阶→星海主宰",
    ),
]

RELATION_NAMES: frozenset[str] = frozenset(spec.name for spec in RELATION_VOCAB)


class RelationRegistry:
    """运行时概念关系词典（种子 10 条 + 用户确认入典的新词）。

    用法（两阶段流程阶段2）：
        registry = RelationRegistry()
        registry.is_known("引发")   # True
        registry.add("反噬")        # 用户确认新词入典，默认◆semantic
    """

    def __init__(self) -> None:
        self._specs: dict[str, RelationSpec] = {s.name: s for s in RELATION_VOCAB}

    def is_known(self, name: str) -> bool:
        """关系名是否已在词典中（含种子+运行时入典）。"""
        return name in self._specs

    def add(
        self,
        name: str,
        level: Literal["rule", "semantic", "structure"] = "semantic",
        gloss: str = "",
    ) -> RelationSpec:
        """用户确认新关系词入典（默认◆semantic）。已存在则原样返回。"""
        if name in self._specs:
            return self._specs[name]
        spec = RelationSpec(name=name, level=level, gloss=gloss, example="")
        self._specs[name] = spec
        return spec

    def all_specs(self) -> list[RelationSpec]:
        """当前词典全部关系规格（种子+新增）。"""
        return list(self._specs.values())
