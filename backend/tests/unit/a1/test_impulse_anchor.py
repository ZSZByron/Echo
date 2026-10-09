"""方向A一期 T6：冲动型语气锚点注入选项生成 prompt（契约测试）。

两个注入点（plan direction-a-option-forward T6）：
1. RealLLMInterviewer._build_prompt 的 8.6 默认示例生成段；
2. suggest_examples（「换一批」重摇引擎）。

注入格式（单行，条件）：session.creator_primary 命中
module_registry.ANCHOR_BY_TYPE 才追加
「示例风格贴合该冲动类型的语气锚点：{锚点原文}」；缺省不注入
（prompt 与改动前逐字节一致）。锚点九句原文零改写（数据同源）。
"""
from __future__ import annotations

from app.domains.creation.a1 import interviewer as it_mod
from app.domains.creation.a1.guide_engine import A1Session
from app.domains.creation.a1.interviewer import RealLLMInterviewer
from app.domains.creation.seed.a1_question_tree import (
    get_module,
    get_subfield,
)
from app.domains.creation.shared import module_registry as reg
from app.domains.creation.shared.module_registry import ANCHOR_BY_TYPE

ANCHOR_PREFIX = "示例风格贴合该冲动类型的语气锚点："


def make_session(creator_primary: str = "") -> A1Session:
    s = A1Session(session_id="s1", user_id="u1", ip_code="IP0001")
    if creator_primary:
        s.creator_primary = creator_primary
    return s


class _CaptureProvider:
    """捕获 chat_json 收到的 system prompt 并返回合法 examples JSON。"""

    def __init__(self) -> None:
        self.system: str = ""

    async def chat_json(self, messages: list[dict[str, str]]) -> str:
        self.system = messages[0]["content"]
        return '{"examples": ["甲", "乙", "丙"]}'


def _session_with_valid_primary() -> A1Session:
    # 测试时从真实表中取一个键，保持与数据同源
    return make_session(sorted(ANCHOR_BY_TYPE)[0])


def test_anchor_injected_in_interview_prompt() -> None:
    s = _session_with_valid_primary()
    it = RealLLMInterviewer(None)
    prompt = it._build_prompt(get_module(s.current_module) or {},
                              get_subfield(s.current_module, s.current_subfield) or {},
                              s)
    expected = ANCHOR_PREFIX + ANCHOR_BY_TYPE[s.creator_primary]
    assert expected in prompt


def test_anchor_injected_in_suggest_examples_prompt() -> None:
    s = _session_with_valid_primary()
    provider = _CaptureProvider()
    it = RealLLMInterviewer(provider)
    it.suggest_examples(s, s.current_module, s.current_subfield)
    expected = ANCHOR_PREFIX + ANCHOR_BY_TYPE[s.creator_primary]
    assert expected in provider.system


def test_anchor_absent_without_creator_primary() -> None:
    s = make_session("")  # creator_primary 缺省
    it = RealLLMInterviewer(None)
    prompt = it._build_prompt(get_module(s.current_module) or {},
                              get_subfield(s.current_module, s.current_subfield) or {},
                              s)
    assert ANCHOR_PREFIX not in prompt
    provider = _CaptureProvider()
    it2 = RealLLMInterviewer(provider)
    it2.suggest_examples(s, s.current_module, s.current_subfield)
    assert ANCHOR_PREFIX not in provider.system


def test_anchor_sentences_verbatim() -> None:
    # 九型齐全、非空、互不相同
    assert len(ANCHOR_BY_TYPE) == 9
    assert all(v.strip() for v in ANCHOR_BY_TYPE.values())
    assert len(set(ANCHOR_BY_TYPE.values())) == 9
    # interviewer 导入的就是注册表对象本身（数据同源，非拷贝）
    assert it_mod.ANCHOR_BY_TYPE is reg.ANCHOR_BY_TYPE


def test_nine_anchors_verbatim() -> None:
    """逐键构建 prompt：九句锚点原文必须逐字出现（防意外改写）。"""
    s0 = A1Session(session_id="s1", user_id="u1", ip_code="IP0001")
    it = RealLLMInterviewer(None)
    module = get_module(s0.current_module) or {}
    subfield = get_subfield(s0.current_module, s0.current_subfield) or {}
    for key, anchor in ANCHOR_BY_TYPE.items():
        s = make_session(key)
        prompt = it._build_prompt(module, subfield, s)
        assert (ANCHOR_PREFIX + anchor) in prompt, f"anchor rewritten for {key}"
