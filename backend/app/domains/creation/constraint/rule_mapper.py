"""Rule Mapper — 标签→维度确定性映射规则库。

规则先导层：在 LLM 补全之前，先查规则表获取确定性映射，
LLM 只补规则覆盖不到的部分。用户确认后回馈新规则到表（自学习）。

数据持久化：backend/data/rule_table.json

核心流程：
    tags=["crystal","magical"] + target_dim="constraint"
        ↓ match()
    命中 R001 (confidence=0.9) → 注入生成上下文
        ↓ learn()
    用户确认 → 新规则追加到 rule_table.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.models.concept import FIVE_DIMENSIONS

# ---------------------------------------------------------------------------
# 数据文件路径
# ---------------------------------------------------------------------------

_DEFAULT_RULE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "rule_table.json"


# ---------------------------------------------------------------------------
# 规则模型
# ---------------------------------------------------------------------------

class RuleEntry(BaseModel):
    """单条映射规则。

    Attributes:
        id: 规则唯一 ID（如 "R001"）。
        source_tags: 触发此规则的标签集合（任一命中即匹配）。
        target_dim: 此规则映射到的目标维度。
        rule: 规则文本描述（注入 LLM 的确定性指令）。
        template: 输出模板（含 {placeholder} 供填充）。
        confidence: 置信度 [0.0, 1.0]，越高越优先。
        hit_count: 被匹配命中的次数（用于排序和自学习权重）。
        source_seeds: 来源种子 ID 列表（追溯）。
    """

    id: str
    source_tags: list[str] = Field(default_factory=list)
    target_dim: str
    rule: str
    template: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    hit_count: int = 0
    source_seeds: list[str] = Field(default_factory=list)


class RuleMatch(BaseModel):
    """单次规则匹配结果。

    Attributes:
        rule: 命中的规则条目。
        matched_tags: 实际命中的标签子集。
        score: 匹配分数 = confidence × (matched_tags / source_tags)。
    """

    rule: RuleEntry
    matched_tags: list[str] = Field(default_factory=list)
    score: float = 0.0


# ---------------------------------------------------------------------------
# 规则表
# ---------------------------------------------------------------------------

class RuleTable:
    """标签→维度确定性映射规则库。

    支持从 JSON 文件加载、匹配查询、学习新规则。
    所有操作在内存中进行，显式调用 save() 持久化。
    """

    def __init__(self, rules: list[RuleEntry] | None = None) -> None:
        """初始化规则表。

        Args:
            rules: 初始规则列表，为 None 则空表。
        """
        self._rules: list[RuleEntry] = rules or []

    # --- 加载/保存 ---

    @classmethod
    def load(cls, path: Path | None = None) -> RuleTable:
        """从 JSON 文件加载规则表。

        Args:
            path: JSON 文件路径，默认为 backend/data/rule_table.json。

        Returns:
            加载后的 RuleTable 实例。
        """
        rule_path = path or _DEFAULT_RULE_PATH
        if not rule_path.exists():
            return cls(rules=[])

        data = json.loads(rule_path.read_text(encoding="utf-8"))
        rules = [RuleEntry(**r) for r in data.get("rules", [])]
        return cls(rules=rules)

    def save(self, path: Path | None = None) -> None:
        """将当前规则表保存到 JSON 文件。

        Args:
            path: 目标文件路径，默认为 backend/data/rule_table.json。
        """
        rule_path = path or _DEFAULT_RULE_PATH
        rule_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0.0",
            "description": "标签→维度确定性映射规则库。",
            "rules": [r.model_dump() for r in self._rules],
        }
        rule_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # --- 查询 ---

    @property
    def size(self) -> int:
        """规则总数。"""
        return len(self._rules)

    def match(
        self,
        tags: list[str],
        target_dim: str,
        min_score: float = 0.1,
    ) -> list[RuleMatch]:
        """从 tags 匹配规则，返回候选列表（按分数降序）。

        匹配算法：
            1. 过滤 target_dim 一致的规则
            2. 计算 tags 与 rule.source_tags 的交集
            3. 交集非空 → score = confidence × (交集大小 / source_tags大小)
            4. 过滤 score < min_score 的结果
            5. 按 score 降序排列

        Args:
            tags: 输入标签列表。
            target_dim: 目标维度（必须是 FIVE_DIMENSIONS 之一）。
            min_score: 最低匹配分数阈值。

        Returns:
            匹配结果列表，按分数降序。
        """
        if target_dim not in FIVE_DIMENSIONS:
            return []

        tag_set = set(tags)
        matches: list[RuleMatch] = []

        for rule in self._rules:
            if rule.target_dim != target_dim:
                continue

            source_set = set(rule.source_tags)
            matched = tag_set & source_set

            if not matched:
                continue

            coverage = len(matched) / len(source_set) if source_set else 0
            score = rule.confidence * coverage

            if score >= min_score:
                matches.append(RuleMatch(
                    rule=rule,
                    matched_tags=list(matched),
                    score=round(score, 4),
                ))

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches

    def best_match(
        self,
        tags: list[str],
        target_dim: str,
    ) -> RuleMatch | None:
        """返回最高分的单条匹配。

        Args:
            tags: 输入标签列表。
            target_dim: 目标维度。

        Returns:
            最佳匹配，无匹配则 None。
        """
        matches = self.match(tags, target_dim)
        return matches[0] if matches else None

    # --- 自学习 ---

    def learn(self, confirmed_mapping: dict[str, Any]) -> RuleEntry:
        """用户确认后回馈新规则到表。

        从已确认的标签→维度映射中提取规则，如果相似规则已存在则增加
        hit_count，否则创建新规则。

        Args:
            confirmed_mapping: 包含以下字段：
                - source_tags: list[str] — 触发标签
                - target_dim: str — 目标维度
                - rule: str — 规则文本
                - template: str — 输出模板
                - source_seed: str — 来源种子 ID（可选）

        Returns:
            被更新或新建的 RuleEntry。
        """
        source_tags = confirmed_mapping.get("source_tags", [])
        target_dim = confirmed_mapping.get("target_dim", "")
        rule_text = confirmed_mapping.get("rule", "")
        template = confirmed_mapping.get("template", "")
        source_seed = confirmed_mapping.get("source_seed")

        # 查找是否已有高度相似的规则
        existing = self._find_similar(source_tags, target_dim, rule_text)

        if existing:
            existing.hit_count += 1
            existing.confidence = min(1.0, existing.confidence + 0.05)
            if source_seed and source_seed not in existing.source_seeds:
                existing.source_seeds.append(source_seed)
            return existing

        # 创建新规则
        new_id = self._next_rule_id()
        new_rule = RuleEntry(
            id=new_id,
            source_tags=list(source_tags),
            target_dim=target_dim,
            rule=rule_text,
            template=template,
            confidence=0.6,  # 新规则初始置信度
            hit_count=1,
            source_seeds=[source_seed] if source_seed else [],
        )
        self._rules.append(new_rule)
        return new_rule

    # --- 内部 ---

    def _find_similar(
        self,
        source_tags: list[str],
        target_dim: str,
        rule_text: str,
        threshold: float = 0.6,
    ) -> RuleEntry | None:
        """查找与给定参数高度相似的已有规则。

        相似度 = Jaccard(tags) × 0.6 + 文本相似度 × 0.4
        """
        tag_set = set(source_tags)
        best: RuleEntry | None = None
        best_score = 0.0

        for rule in self._rules:
            if rule.target_dim != target_dim:
                continue

            existing_set = set(rule.source_tags)
            if not existing_set:
                continue

            # Jaccard 相似度
            intersection = tag_set & existing_set
            union = tag_set | existing_set
            tag_sim = len(intersection) / len(union) if union else 0

            # 文本相似度（简单词重叠）
            rule_words = set(rule_text.split())
            new_words = set(rule_text.split())
            # 简化：如果 rule_text 相同就直接匹配
            text_sim = 1.0 if rule.rule == rule_text else 0.3

            score = tag_sim * 0.6 + text_sim * 0.4

            if score > best_score and score >= threshold:
                best_score = score
                best = rule

        return best

    def _next_rule_id(self) -> str:
        """生成下一个规则 ID（R001, R002, ...）。"""
        if not self._rules:
            return "R001"

        # 提取已有最大编号
        max_num = 0
        for rule in self._rules:
            if rule.id.startswith("R"):
                try:
                    num = int(rule.id[1:])
                    max_num = max(max_num, num)
                except ValueError:
                    pass

        return f"R{max_num + 1:03d}"
