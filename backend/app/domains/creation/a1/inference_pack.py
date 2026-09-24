"""推断包（inference pack）——M4a，D12 冻结设计 ②。

单次 LLM 调用（同 interviewer 模式：provider.chat_json + 健壮解析 +
无条件降级），输入 = 冲动类型 + 会话上下文，输出 3-5 条补全建议。

三铁律约束：
- **不直写 answers**：建议只装入 session.pending_proposals（复用既有
  write-guard proposal/confirm 机制，D12 ②逐字），confirm 是用户动作；
- J1 真值闸：占位值建议在装包前即被拦截，placeholder 永不成为提案；
- 零 LLM（无 provider / 异常 / 形状不符）→ 空包 + 披露 note，绝不 crash
  （M3 module_compile 免费线范式）。

判定双写（confirm 后，路由层调用 apply_pack_feedback）：
- creator_profile 置信修正（creator_confidence 棘轮 [0,1]，确定性，只看不判）；
- fills 通道写入由 resolve_proposal 完成（经 J1，溯源 llm_fill）。
"""
from __future__ import annotations

import asyncio
import inspect
from typing import Any

from pydantic import BaseModel, Field

from app.domains.creation.a1.guide_engine import A1Session, is_truthy_answer
from app.domains.creation.a1.interaction_log import log_event
from app.domains.creation.a1.interviewer import Proposal, _answers_digest
from app.domains.creation.seed.a1_question_tree import (
    all_subfield_keys,
    get_subfield,
)

# 建议 → 提案 装包上限（spec：输出 3-5 条）。
PACK_MAX_SUGGESTIONS = 5

# 置信修正步长（确定性；棘轮边界 [0.0, 1.0]）。
_CONFIDENCE_STEP = 0.1


class PackSuggestion(BaseModel):
    """一条补全建议（候选提案的纯数据形态）。"""

    module: str
    subfield: str
    value: str
    reason: str = ""


class InferencePack(BaseModel):
    """一次推断包构建的结果（建议列表 + 降级披露）。"""

    suggestions: list[PackSuggestion] = Field(default_factory=list)
    note: str = ""


class InferencePacker:
    """LLM 推断包构建器（单生产方；确定性过滤与装包）。"""

    def __init__(self, provider: Any) -> None:
        self._provider = provider

    # ---------- LLM ----------

    def build(self, session: A1Session) -> InferencePack:
        """单次 LLM 调用生成建议；任何失败路径降级为空包 + note。"""
        if self._provider is None:
            return InferencePack(
                note="无 LLM provider，推断包降级为空（访谈不受影响）"
            )
        system = self._build_prompt(session)
        try:
            out = self._provider.chat_json(
                [{"role": "system", "content": system}]
            )
            if inspect.isawaitable(out):  # 同步/异步 provider 双兼容（M3 先例）
                out = asyncio.run(out)
        except Exception as e:  # noqa: BLE001 — degrade, never crash
            log_event(
                session.session_id, "error", stage="inference_pack", error=str(e)[:300]
            )
            return InferencePack(note=f"推断包生成失败，已降级为空：{str(e)[:120]}")
        if not isinstance(out, dict):
            return InferencePack(note="推断包响应形状不符，已降级为空")

        raw = out.get("suggestions")
        if not isinstance(raw, list):
            return InferencePack(note="推断包响应形状不符，已降级为空")

        suggestions = self._filter_valid(session, raw)
        log_event(
            session.session_id,
            "inference_pack_built",
            total=len(raw),
            kept=len(suggestions),
        )
        note = "" if suggestions else "推断包无有效建议（占位/配方外/已答字段被过滤）"
        return InferencePack(suggestions=suggestions, note=note)

    # ---------- 确定性过滤（LLM 不进控制流） ----------

    @staticmethod
    def _filter_valid(
        session: A1Session, raw: list[Any]
    ) -> list[PackSuggestion]:
        recipe = session.recipe_modules or None
        legal = set(all_subfield_keys(recipe=recipe))
        valid: list[PackSuggestion] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            module, subfield, value = (
                item.get("module"), item.get("subfield"), item.get("value")
            )
            if not all(isinstance(x, str) and x.strip() for x in (module, subfield, value)):
                continue
            key = f"{module}.{subfield}"
            if key not in legal:
                continue
            if get_subfield(module, subfield) is None:
                continue
            # 已答（真值）字段不再建议——推断包只补空
            if is_truthy_answer(session.answers.get(key, "")):
                continue
            # J1 真值闸：占位值在装包前拦截
            if not is_truthy_answer(value):
                continue
            valid.append(
                PackSuggestion(
                    module=module,
                    subfield=subfield,
                    value=value,
                    reason=str(item.get("reason", ""))[:200],
                )
            )
            if len(valid) >= PACK_MAX_SUGGESTIONS:
                break
        return valid

    # ---------- 装包（复用 pending_proposals——绝不直写 answers） ----------

    @staticmethod
    def install(session: A1Session, pack: InferencePack) -> list[str]:
        """把建议装入 pending_proposals（write-guard 三连由既有 confirm 消费）。

        返回 proposal key 列表。此函数是推断包与 answers 之间唯一许可的
        交互面，且只写 pending_proposals——契约测试断言 answers 不变。
        """
        from app.domains.creation.a1.guide_engine import _proposal_key

        keys: list[str] = []
        for sug in pack.suggestions:
            key = f"{sug.module}.{sug.subfield}"
            if is_truthy_answer(session.answers.get(key, "")):
                continue  # 装包间隙被并发写入 → 跳过（不覆盖已答字段）
            pk = _proposal_key(sug.module, sug.subfield, sug.value)
            session.pending_proposals[pk] = {
                "proposal": Proposal(
                    module=sug.module,
                    subfield=sug.subfield,
                    old=session.answers.get(key, ""),
                    new=sug.value,
                    conflict_note=sug.reason or None,
                ),
                "options": ["replace", "drop"],
                # M4a：推断包提案标记——confirm 路由据此做判定双写
                "source": "inference_pack",
            }
            keys.append(pk)
        return keys

    # ---------- prompt ----------

    @staticmethod
    def _build_prompt(session: A1Session) -> str:
        recipe = session.recipe_modules or None
        unfilled: list[str] = []
        for key in all_subfield_keys(recipe=recipe):
            if not is_truthy_answer(session.answers.get(key, "")):
                module_id, sub_id = key.split(".", 1)
                sf = get_subfield(module_id, sub_id)
                if sf:
                    unfilled.append(f"- {key}（{sf['label']}：{sf['question']}）")
            if len(unfilled) >= 20:
                break
        impulse = session.creator_primary or "（未判定）"
        return "\n".join(
            [
                "你是世界观工坊的推断助手。基于用户的冲动类型与已答内容，"
                "推断最可能的 3-5 个未答字段答案，作为**建议**供用户确认。",
                f"用户冲动类型：{impulse}",
                f"种子：{session.seed_name or '无'}"
                f"（{session.seed_genre or ''}）{session.seed_description[:200]}",
                "已答内容摘要：",
                _answers_digest(session.answers) or "（暂无）",
                "待补字段（只允许从这里选择）：",
                "\n".join(unfilled) or "（无）",
                '输出 JSON：{"suggestions": [{"module": "模块id", '
                '"subfield": "字段id", "value": "一句话推断", "reason": "依据"}]}',
                "规则：value 必须是具体内容（禁止占位词如『待补充』）；"
                "只建议待补字段；宁缺毋滥。",
            ]
        )


def apply_pack_feedback(session: A1Session, applied: bool) -> float:
    """推断包 confirm 判定双写之置信修正（确定性，只看不判）。

    applied=True（用户确认采纳）→ 该冲动类型置信 +0.1；
    applied=False（放弃）→ -0.1。棘轮边界 [0.0, 1.0]，永不越界。
    返回修正后的置信值。bucket = creator_primary，无 profile 用 "unprofiled"。
    """
    bucket = session.creator_primary or "unprofiled"
    current = session.creator_confidence.get(bucket, 0.5)
    current = max(0.0, min(1.0, current + (_CONFIDENCE_STEP if applied else -_CONFIDENCE_STEP)))
    session.creator_confidence[bucket] = current
    log_event(
        session.session_id,
        "inference_pack_feedback",
        bucket=bucket,
        applied=applied,
        confidence=current,
    )
    return current
