"""Cycle Checker — 循环一致性校验。

灵感来自 CycleGAN 的 cycle-consistency loss：
    正向：A → G(A)    （seed → generated）
    反向：G(A) → F(G(A))  （generated → reconstructed）
    一致性：A ≈ F(G(A))   （reconstructed ≈ seed?）

在概念映射中：
    1. 用户输入 seed (Asset: 水晶祭坛)
    2. 系统生成 story (星光复苏的仪式)
    3. 反向推理：从 story 再推回 asset' (星辉法器)
    4. 比较：原始 asset vs 反推 asset' — 它们语义一致吗？

如果一致 → 循环验证通过，内容可信。
如果不一致 → 存在语义漂移，需要标记冲突。

一致性检测使用 LLM 做语义比较（非精确匹配）。
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from app.ai.provider import LLMProvider
from app.domains.creation.seed.backward_generator import backward_generate

# ---------------------------------------------------------------------------
# 结果模型
# ---------------------------------------------------------------------------

class CycleReport(BaseModel):
    """单次循环一致性校验报告。

    Attributes:
        seed_dim: 种子维度。
        target_dim: 目标维度。
        reconstructed: 反推回 seed_dim 的内容。
        consistency_score: 一致性分数 [0.0, 1.0]。
        is_consistent: 是否通过一致性阈值。
        differences: 检测到的语义差异列表。
        raw_llm_response: LLM 原始响应（调试用）。
    """

    seed_dim: str
    target_dim: str
    reconstructed: dict[str, Any] | None = None
    consistency_score: float = Field(default=0.0, ge=0.0, le=1.0)
    is_consistent: bool = False
    differences: list[str] = Field(default_factory=list)
    raw_llm_response: str = ""

    @property
    def passed(self) -> bool:
        """是否通过（is_consistent 的别名）。"""
        return self.is_consistent


# ---------------------------------------------------------------------------
# 默认参数
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLD = 0.7  # 一致性通过阈值


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

async def cycle_check(
    seed_content: dict[str, Any],
    seed_dim: str,
    generated_content: dict[str, Any],
    target_dim: str,
    provider: LLMProvider,
    threshold: float = DEFAULT_THRESHOLD,
) -> CycleReport:
    """执行循环一致性校验。

    流程：
        1. 正向已有：seed_dim → target_dim (generated_content)
        2. 反向推理：target_dim → seed_dim (reconstructed)
        3. 语义比较：seed_content vs reconstructed

    Args:
        seed_content: 原始种子维度内容。
        seed_dim: 种子维度名称。
        generated_content: 正向生成的目标维度内容。
        target_dim: 目标维度名称。
        provider: LLM Provider 实例。
        threshold: 一致性通过阈值 (默认 0.7)。

    Returns:
        CycleReport: 校验报告。
    """
    # Step 1: 反向推理 — 从 generated 推回 seed_dim
    reconstructed = await backward_generate(
        seed_dim=target_dim,
        seed_content=generated_content,
        target_dim=seed_dim,
        provider=provider,
    )

    # Step 2: 语义比较
    comparison = await _semantic_compare(
        original=seed_content,
        reconstructed=reconstructed,
        dim=seed_dim,
        provider=provider,
    )

    score = comparison.get("consistency_score", 0.0)
    differences = comparison.get("differences", [])

    return CycleReport(
        seed_dim=seed_dim,
        target_dim=target_dim,
        reconstructed=reconstructed,
        consistency_score=score,
        is_consistent=score >= threshold,
        differences=differences,
        raw_llm_response=json.dumps(comparison, ensure_ascii=False),
    )


async def cycle_check_multi(
    seed_content: dict[str, Any],
    seed_dim: str,
    generated: dict[str, dict[str, Any]],
    provider: LLMProvider,
    threshold: float = DEFAULT_THRESHOLD,
) -> list[CycleReport]:
    """对多个目标维度执行批量循环一致性校验。

    Args:
        seed_content: 原始种子维度内容。
        seed_dim: 种子维度名称。
        generated: {target_dim: content} 映射。
        provider: LLM Provider 实例。
        threshold: 一致性通过阈值。

    Returns:
        每个目标维度的校验报告列表。
    """
    reports: list[CycleReport] = []
    for target_dim, content in generated.items():
        report = await cycle_check(
            seed_content=seed_content,
            seed_dim=seed_dim,
            generated_content=content,
            target_dim=target_dim,
            provider=provider,
            threshold=threshold,
        )
        reports.append(report)
    return reports


# ---------------------------------------------------------------------------
# 语义比较
# ---------------------------------------------------------------------------

async def _semantic_compare(
    original: dict[str, Any],
    reconstructed: dict[str, Any],
    dim: str,
    provider: LLMProvider,
) -> dict[str, Any]:
    """使用 LLM 做语义比较，返回一致性分数和差异列表。

    Args:
        original: 原始内容。
        reconstructed: 反推内容。
        dim: 比较的维度名称。
        provider: LLM Provider。

    Returns:
        {"consistency_score": float, "differences": list[str]}
    """
    system_prompt = (
        "你是一个语义一致性评估器。给定两个{dim}维度的内容（原始 vs 反推重建），"
        "请评估它们的语义一致性。\n\n"
        "评估标准：\n"
        "- 1.0：完全一致（反推内容描述的是同一个事物）\n"
        "- 0.7-0.9：高度一致（核心一致，细节有差异但可接受）\n"
        "- 0.4-0.6：部分一致（有共同元素，但存在明显矛盾）\n"
        "- 0.0-0.3：不一致（描述的是完全不同的事物）\n\n"
        "输出 JSON：{{\"consistency_score\": 0.0-1.0, \"differences\": [\"差异1\", \"差异2\"]}}\n"
        "differences 为空列表表示完全一致。"
    ).replace("{dim}", dim)

    user_content = (
        f"原始 {dim} 内容：\n"
        f"{json.dumps(original, ensure_ascii=False, indent=2)}\n\n"
        f"反推重建的 {dim} 内容：\n"
        f"{json.dumps(reconstructed, ensure_ascii=False, indent=2)}\n\n"
        f"请评估语义一致性。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    result = await provider.chat_json(messages)
    return {
        "consistency_score": float(result.get("consistency_score", 0.0)),
        "differences": result.get("differences", []),
    }
