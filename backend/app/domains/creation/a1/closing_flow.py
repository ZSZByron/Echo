"""closing_flow — 收尾三连问状态机 + 可生成物按动机排序（D21 Task 10）。

spec v1.3 §5.4 L69-72（D21⑧）+ D22⑤：

1. **三连问状态机**：预设双条件命中（T6 ``is_preset_phase_complete``）后
   依次询问 ①生成文档还是继续访谈录入设定 ②缺的部分让 AI 补吗 ③要不要
   改天继续。答案存会话（``closing_answers``）；「改天继续」= 同会话
   持久化标记（``resume_later``，D21⑨——经 A1Store 落盘，不建新会话）。

2. **竞态默认语义（非阻塞）**：收尾态中用户输入若为设定内容（非三问
   显式作答）= 视作「继续」自由流——本轮照常走访谈管线，轮末条件仍
   满足则重新提示当前问题；显式选择才推进状态机。

3. **可生成物按动机排序**（D22⑤「先给想要的，再让他看见向上的楼梯」）：
   以 ``session.creator_primary`` 三线分类（故事线/设定线/通用线，
   spec v1.3 §5.2）重排 T6 ``CONSUMER_ARTIFACTS``——故事线
   story_outline 打头 / 设定线 world_bible 打头 / 通用线（含无 profile
   兜底）通用投影三件按声明序打头；跑团件恒排末并标「进阶可用」。

「AI 补充」执行不在本模块范围——三问只收集答案。本模块零 LLM。
"""
from __future__ import annotations

from typing import Any

from app.domains.creation.a1.closing_gate import (
    CONSUMER_ARTIFACTS,
    is_preset_phase_complete,
)
from app.domains.creation.a1.guide_engine import A1Session

# ---------------------------------------------------------------------------
# 三连问文案（说人话 baseline——不出现内部模块 id；终稿润色归前端阶段）
# ---------------------------------------------------------------------------

#: 收尾触发时的能力告知前缀（数据源 = T6 确定性图谱识别的能力面概述）。
TRIGGER_PREFIX = (
    "预设的问题都聊完了。你现在的设定已经可以生成："
    "世界圣经、人物志、故事大纲这些文档（还有面向跑团的进阶件）。"
)

#: 三连问：step → {key, text}。key 即 closing_answers 的存取键。
QUESTIONS: tuple[dict[str, str], ...] = (
    {"key": "q1", "text": "想现在生成文档，还是继续访谈、补充设定？"},
    {"key": "q2", "text": "还缺的部分，要让 AI 帮你补上吗？"},
    {"key": "q3", "text": "要不要改天再继续？你的进度会保留在这个会话里。"},
)


def _question(step: int) -> dict[str, str]:
    return QUESTIONS[step - 1]


def _question_text(step: int) -> str:
    return _question(step)["text"]


# ---------------------------------------------------------------------------
# 1. 状态机：触发 / 作答 / 轮末钩子
# ---------------------------------------------------------------------------


def closing_settled(session: A1Session) -> bool:
    """三问全部落定（settled 后永不重触发）。"""
    return session.closing_settled


def _rack_inventory_line(session: A1Session) -> str:
    """批D 回收时机②：收尾盘点——摊开灵感架存量（空架返回空串，字节不变）。

    设计稿 §2.3：「收尾三连问前统一盘点（架上有 3 件宝贝还没安家）」。
    """
    if not session.material_pool:
        return ""
    items = "；".join(
        f"「{(m.get('text') or '')[:30]}」" for m in session.material_pool
    )
    return (
        f"灵感架上还有 {len(session.material_pool)} 件宝贝没安家：{items}。"
        "先记着，回头随时安家。"
    )


def maybe_trigger(session: A1Session) -> str | None:
    """轮末检查：双条件命中且未进入收尾态 → 进入 Q1，返回提示文案。

    已在收尾态（1..3）或已 settled → None（幂等，不重置进度）。
    批D additive：灵感架非空 → 提示前先摊开存量盘点（回收时机②）。
    """
    if session.closing_settled or session.closing_step != 0:
        return None
    if not is_preset_phase_complete(session):
        return None
    session.closing_step = 1
    return f"{_rack_inventory_line(session)}{TRIGGER_PREFIX}{_question_text(1)}"


def _match_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(k in text for k in keywords)


_Q1_GENERATE = ("生成文档", "文档", "导出", "出文档")
#: Q1「继续」= 显式整句短语集（非子串匹配）：含内容词的输入
#（如「继续聊聊主角」）是设定内容，走自由流（竞态默认语义）。
_Q1_CONTINUE_PHRASES = frozenset({
    "继续", "继续访谈", "继续访谈录入设定", "继续录入设定",
    "再补充点设定", "补充设定", "接着聊", "接着聊设定",
    "再聊", "再聊聊", "录入设定",
})
_Q2_NO = ("不用", "先不", "不要", "不补", "算了", "不好", "暂时不", "不麻烦")
_Q2_YES = ("补", "让ai", "让 ai", "好", "要", "可以", "麻烦", "嗯", "行", "ok", "是")
_Q3_RESUME = ("改天", "下次", "明天", "改日", "好", "要", "嗯", "行", "ok")
_Q3_TODAY = ("今天", "现在", "就到这", "就到这里", "不用", "不了", "不用了")


def _classify(step: int, text: str) -> str | None:
    """显式作答分类。返回语义答案或 None（= 设定内容，自由流）。"""
    t = text.strip().lower()
    if step == 1:
        if _match_any(t, _Q1_GENERATE):
            return "generate_doc"
        if t in _Q1_CONTINUE_PHRASES:
            return "continue"
        return None
    if step == 2:
        if _match_any(t, _Q2_NO):
            return "ai_fill_no"
        if _match_any(t, _Q2_YES):
            return "ai_fill_yes"
        return None
    if step == 3:
        if _match_any(t, _Q3_RESUME):
            return "resume_later"
        if _match_any(t, _Q3_TODAY):
            return "today_end"
        return None
    return None


#: 文档端点族引用（D15：端点资源名 = doc；端点本体落地归 T18，先留引用）。
DOC_ENDPOINTS: tuple[str, ...] = (
    "/api/a1/file/{file_id}/doc",
    "/api/a1/file/{file_id}/doc/render",
)
#: 生成文档回复中点名的 D22 通用投影三件（人话名）。
DOC_ARTIFACT_NAMES = "世界圣经、人物志、故事大纲"


def _after_answer(session: A1Session, step: int, ans: str) -> str:  # noqa: ARG001 (session: 状态机签名约定，供调用方统一传参)
    """作答后的确认 + 下一问文案（覆盖本轮闲聊噪声回复，说人话）。"""
    if step == 1:
        if ans == "generate_doc":
            return (
                f"好。文档随时可以在「文档输出」里生成：{DOC_ARTIFACT_NAMES}"
                f"（接口 {' / '.join(DOC_ENDPOINTS)}，跑团件为进阶件）。"
                f"先再问一句——{_question_text(2)}"
            )
        return f"好，那就继续聊。{_question_text(2)}"
    if step == 2:
        if ans == "ai_fill_yes":
            return "好，缺的部分后面让 AI 帮你搭把手。" + _question_text(3)
        return "好，缺的部分先留着不硬编。" + _question_text(3)
    # step 3 → 落定
    if ans == "resume_later":
        return "好，那就改天继续——这个会话会保留你的进度，随时回来说一声就行。"
    return "好，那今天就到这——想继续随时回来，进度都在。"


def advance_answer(session: A1Session, text: str) -> str | None:
    """收尾态中对用户输入做显式作答判定并推进状态机。

    返回值：
    - 语义答案字符串（显式选择）：已落 ``closing_answers``、推进 step、
      三问答完置 settled（q3=resume_later 同时置同会话持久化标记
      ``resume_later``）；返回值 = 确认 + 下一问的人话回复文案（说人话，
      直接可作本轮 reply）；
    - None：输入是设定内容 → 视作「继续」自由流，状态机不动（竞态默认
      语义；调用方本轮照常走访谈管线）。
    """
    step = session.closing_step
    if not 1 <= step <= 3:
        return None
    ans = _classify(step, text)
    if ans is None:
        return None
    session.closing_answers[_question(step)["key"]] = ans
    if step == 3:
        session.closing_step = 0
        session.closing_settled = True
        session.resume_later = ans == "resume_later"
    else:
        session.closing_step = step + 1
    return _after_answer(session, step, ans)


def interject(session: A1Session, text: str, out: dict[str, Any]) -> dict[str, Any]:
    """``_handle_message_impl`` 轮末钩子（非阻塞，追加/覆盖 reply 文案）。

    - 收尾态中显式作答 → 推进状态机，**覆盖**本轮回复（闲聊噪声对三问
      无意义）；确认 + 下一问 / 落定语。
    - 收尾态中设定内容 → 自由流原回复保留；条件仍满足 → 追加重提示
      当前问题（re-hit re-prompt）。
    - 未触发 → 双条件命中则进入 Q1：原回复保留 + 追加能力告知 + 首问。
    - settled / 未命中 → 原样返回。
    """
    if 1 <= session.closing_step <= 3:
        step = session.closing_step
        reply = advance_answer(session, text)
        if reply is not None:
            out["reply"] = reply
            return out
        if is_preset_phase_complete(session):
            out["reply"] = out.get("reply", "") + "\n" + _question_text(step)
        return out
    if session.closing_settled:
        return out
    prompt = maybe_trigger(session)
    if prompt is not None:
        out["reply"] = out.get("reply", "") + "\n" + prompt
    return out


# ---------------------------------------------------------------------------
# 2. 可生成物按动机排序（D22⑤）
# ---------------------------------------------------------------------------


def creator_line(session: A1Session) -> str:
    """creator_primary → 三线分类（spec v1.3 §5.2，十类闭合）。

    - "story"   = 纯故事三型（plot/romance/character_driven）
    - "setting" = 世界建构重型五型（setting_heavy/philosophy/
      exploration/nostalgia/healing）
    - "general" = unsure 通用线 + 无 profile/未知兜底（通用投影排前）
    """
    p = session.creator_primary or ""
    if p in ("plot", "romance", "character_driven"):
        return "story"
    if p in ("setting_heavy", "philosophy", "exploration", "nostalgia", "healing"):
        return "setting"
    return "general"


#: 三线打头件（D22⑤：动机件排最前；general = 通用投影三件声明序）。
_LINE_FIRST: dict[str, str] = {"story": "story_outline", "setting": "world_bible"}


def order_artifacts(session: A1Session) -> list[dict[str, Any]]:
    """按会话动机重排 T6 ``CONSUMER_ARTIFACTS``（纯函数，零打分）。

    动机件（如有）→ 其余 D22 通用投影三件（声明序）→ 跑团件（恒排末，
    标「进阶可用」）。
    """
    first = _LINE_FIRST.get(creator_line(session))
    d22 = [dict(c) for c in CONSUMER_ARTIFACTS if c["kind"] == "d22"]
    trpg = [
        dict(c, note="进阶可用") for c in CONSUMER_ARTIFACTS if c["kind"] == "trpg"
    ]
    ordered = [c for c in d22 if c["id"] == first]
    ordered += [c for c in d22 if c["id"] != first]
    return ordered + trpg
