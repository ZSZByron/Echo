"""Seed Routes — 双向概念映射 API 端点。

POST /api/seed/generate   — 从任意输入生成五维闭环世界
POST /api/seed/confirm    — 用户确认后回馈规则到规则表
GET  /api/seed/presets    — 列出所有可用 TRPG 预设
GET  /api/seed/rules      — 查看当前规则表
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_llm_provider
from app.models.concept import SeedType
from app.domains.creation.seed.seed_engine import GenerationResult, SeedEngine

router = APIRouter(prefix="/api/seed", tags=["seed"])


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------

class SeedRequest(BaseModel):
    """种子生成请求。

    Attributes:
        raw_input: 用户原始输入文本（如 "古代水晶祭坛"）。
        seed_type: 种子类型 (story/asset/event/culture/constraint/mixed)，
                   为 None 则自动检测。
        seed_content: 种子维度内容（为 None 则用 raw_input 构建）。
        tags: 语义标签（为 None 则自动提取）。
        preset_id: TRPG 预设 ID（可选）。
        enable_cycle_check: 是否启用循环一致性校验（默认 True）。
    """

    raw_input: str = Field(..., min_length=1, max_length=500)
    seed_type: str | None = Field(default=None, description="story|asset|event|culture|constraint|mixed")
    seed_content: dict[str, Any] | None = None
    tags: list[str] | None = None
    preset_id: str | None = None
    enable_cycle_check: bool = True


class ConfirmRequest(BaseModel):
    """用户确认请求。"""

    result: GenerationResult


class SeedResponse(BaseModel):
    """种子生成响应。"""

    success: bool
    summary: str
    concept_node: dict[str, Any]
    cycle_reports: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    elapsed_seconds: float = 0.0


class ConfirmResponse(BaseModel):
    """确认响应。"""

    success: bool
    learned_rule_ids: list[str] = Field(default_factory=list)


class PresetInfo(BaseModel):
    """预设摘要信息。"""

    id: str
    name: str
    genre: str
    rule_count: str
    lexicon_size: str


class RuleTableResponse(BaseModel):
    """规则表响应。"""

    rule_count: int
    rules: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=SeedResponse)
async def generate_seed(request: SeedRequest) -> SeedResponse:
    """从任意输入生成五维闭环世界。

    流程：概念解析 → 缺失检测 → 规则先导 → LLM 补全 → 循环校验
    """
    provider = get_llm_provider()
    engine = SeedEngine(provider)

    # 归一化 seed_type
    seed_type: SeedType | None = None
    if request.seed_type:
        try:
            seed_type = SeedType(request.seed_type)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid seed_type: {request.seed_type}. "
                       f"Valid: {[t.value for t in SeedType]}",
            )

    result = await engine.generate(
        raw_input=request.raw_input,
        seed_type=seed_type,
        seed_content=request.seed_content,
        tags=request.tags,
        preset_id=request.preset_id,
        enable_cycle_check=request.enable_cycle_check,
    )

    return SeedResponse(
        success=result.is_valid,
        summary=result.summary(),
        concept_node=result.concept_node.model_dump(),
        cycle_reports=[r.model_dump() for r in result.cycle_reports],
        errors=result.errors,
        elapsed_seconds=result.elapsed_seconds,
    )


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm_seed(request: ConfirmRequest) -> ConfirmResponse:
    """用户确认生成结果后，回馈规则到规则表。"""
    provider = get_llm_provider()
    engine = SeedEngine(provider)

    learned_ids = engine.confirm_and_learn(request.result)

    return ConfirmResponse(
        success=True,
        learned_rule_ids=learned_ids,
    )


@router.get("/presets", response_model=list[PresetInfo])
async def list_presets() -> list[PresetInfo]:
    """列出所有可用的 TRPG 预设。"""
    try:
        from experiments.trpg_presets import list_presets as _list

        raw = _list()
        return [PresetInfo(**p) for p in raw]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules", response_model=RuleTableResponse)
async def get_rules() -> RuleTableResponse:
    """查看当前规则表。"""
    from app.domains.creation.constraint.rule_mapper import RuleTable

    table = RuleTable.load()
    return RuleTableResponse(
        rule_count=table.size,
        rules=[r.model_dump() for r in table._rules],
    )
