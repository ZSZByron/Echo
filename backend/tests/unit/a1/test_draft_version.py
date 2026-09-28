"""T15：会话态草稿版本递进（α 体系）单测。

D15③ α-β 语义延伸到输出层 + D21⑬ 产出物 α 版本可见标记。
硬红线：α 绝不进 graph_codes 表或任何持久层——测试 2 钉死。
"""
from __future__ import annotations

import sqlite3

import pytest

from app.domains.creation.a1.draft_version import (
    draft_label,
    finalize_version,
    new_draft_state,
    next_draft,
    start_draft_round,
)
from app.domains.creation.shared.graph_code_issuer import GraphCodeIssuer
from app.domains.creation.modules.character_codex import CharacterCodex
from app.domains.creation.modules.main_module import ModuleDocument
from app.domains.creation.modules.story_outline import StoryOutlineDocument
from app.domains.creation.modules.world_bible import BibleDocument


USER = "u1"


# ── 1. 版本序：v1 → α0.1 → α0.11 → finalize → v2（序关系钉死）──────────


def test_version_sequence_v1_alpha01_alpha11_finalize_v2():
    state = new_draft_state(baseline=1)  # v1 会话定稿基线

    # 第一轮草稿：对齐循环首个草稿 = α0.1
    assert start_draft_round(state) == "α0.1"
    assert draft_label(state) == "α0.1"
    # 循环内后续草稿 = α0.11 / α0.12 …
    assert next_draft(state) == "α0.11"
    assert next_draft(state) == "α0.12"
    assert draft_label(state) == "α0.12"

    # finalize → 下一整型 v2（不是 v1，也不是小数）
    assert finalize_version(state) == 2
    # 收口后无草稿标记
    assert draft_label(state) is None


def test_second_round_uses_02_series():
    state = new_draft_state(baseline=1)
    start_draft_round(state)
    finalize_version(state)  # → v2

    # 第二轮草稿 = 0.2 系（D15：第二轮草稿 = α0.21/0.22）
    assert start_draft_round(state) == "α0.2"
    assert next_draft(state) == "α0.21"
    assert next_draft(state) == "α0.22"
    assert finalize_version(state) == 3


def test_fresh_session_no_draft():
    state = new_draft_state(baseline=0)
    assert draft_label(state) is None
    # 尚未开轮时 finalize 直接给 baseline+1
    assert finalize_version(state) == 1


def test_alpha_state_is_pure_memory_dict():
    """α 状态只是一个普通 dict——可作 A1Session 内存字段，零持久结构。"""
    state = new_draft_state(baseline=5)
    assert state == {"baseline": 5, "round": 0, "step": 0}


# ── 2. α 不落库：草稿循环前后 graph_codes/issuer 状态逐行一致 ──────────


def _rows(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT user_id, ip, stage, instance_no, version, parent_m, code "
            "FROM graph_codes ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


def test_alpha_never_touches_graph_codes(tmp_path):
    issuer = GraphCodeIssuer(tmp_path / "codes.db")
    ip = issuer.new_ip(USER)
    v1 = issuer.next(USER, ip, "W")
    assert v1 == "IP0001-W1-v1"

    before = _rows(tmp_path / "codes.db")

    # 一整轮草稿编译：只动内存 α 标记，绝不调 issuer
    state = new_draft_state(baseline=1)
    for _ in range(3):
        start_draft_round(state)
        for _ in range(4):
            next_draft(state)
        finalize_version(state)  # 记账层面的序推进，仍不发码

    assert _rows(tmp_path / "codes.db") == before, "α 草稿循环不得写 graph_codes"

    # finalize 真正落库仍走 issuer 现行整型链：v1 → v2
    v2 = issuer.next(USER, ip, "W")
    assert v2 == "IP0001-W1-v2"


def test_finalize_after_draft_yields_next_integer_from_issuer(tmp_path):
    """v1.1 草稿期后 finalize 产 v2 而非 v1（序关系，硬红线旁证）。"""
    issuer = GraphCodeIssuer(tmp_path / "codes.db")
    ip = issuer.new_ip(USER)
    assert issuer.next(USER, ip, "W") == "IP0001-W1-v1"

    state = new_draft_state(baseline=1)
    start_draft_round(state)  # α0.1（"v1.1 草稿期"）

    # α 期间 issuer 零调用；finalize 发的码 = issuer 整型自增 v2
    assert issuer.next(USER, ip, "W") == "IP0001-W1-v2"
    assert finalize_version(state) == 2


# ── 3. version_label 三态（D21⑬）───────────────────────────────────────


DOC_FACTORIES = [
    (ModuleDocument, dict(
        title="t", module_fantasy="f",
        sections=[], scope_boundary={},  # type: ignore[arg-type]
        graph_code="IP0001-M1-v1", upstream_graph_code="IP0001-W1-v1",
    )),
    (BibleDocument, dict(
        title="t", overview="o", chapters=[],
        graph_code="IP0001-B1-v1", upstream_graph_code="IP0001-W1-v1",
    )),
    (CharacterCodex, dict(
        title="t", codex_fantasy="f", chapters=[],
        graph_code="IP0001-C1-v1", upstream_graph_code="IP0001-W1-v1",
    )),
    (StoryOutlineDocument, dict(
        title="t", lead_in="l", sections=[],
        graph_code="IP0001-O1-v1", upstream_graph_code="IP0001-W1-v1",
    )),
]


@pytest.mark.parametrize("cls,kwargs", DOC_FACTORIES,
                         ids=["module", "bible", "codex", "outline"])
def test_version_label_alpha_state(cls, kwargs):
    """α 期：草稿产物带 version_label（如 α0.1）。"""
    doc = cls(version_label="α0.1", **kwargs)  # type: ignore[call-arg]
    assert doc.version_label == "α0.1"


@pytest.mark.parametrize("cls,kwargs", DOC_FACTORIES,
                         ids=["module", "bible", "codex", "outline"])
def test_version_label_finalized_default_none(cls, kwargs):
    """定稿：不发 α 标记，默认 None。"""
    doc = cls(**kwargs)  # type: ignore[call-arg]
    assert doc.version_label is None


@pytest.mark.parametrize("cls,kwargs", DOC_FACTORIES,
                         ids=["module", "bible", "codex", "outline"])
def test_version_label_legacy_payload_without_field(cls, kwargs):
    """存量产物：序列化 payload 无该字段 → model_validate 零迁移兼容。"""
    legacy = cls(**kwargs).model_dump()  # type: ignore[call-arg]
    legacy.pop("version_label", None)
    doc = cls.model_validate(legacy)  # type: ignore[attr-defined]
    assert doc.version_label is None
