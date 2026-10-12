# D23 施工计划：访谈语义理解（A）+ 条目层级化（B）一次施工

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> **裁决依据**: decision-log D23 / 问题说明书修订 2 / v6.3 / 4_ux-flow v0.4 §5.5 / 前端手册 §9
> **目标**: fills 语义分流（等价自动合并+豁免、补充进多值子条目、矛盾人话三连问、判定缺失回落）+ AnswerNode 层级条目 + 澄清意图理解 + 撤销。
> **架构**: 判定权 LLM（fill 可选键）/ 执行权引擎（guide_engine 单点消费，D20 模式）；树=真相源、字符串=确定性渲染（单生产单消费）；全部 additive——旧数据零迁移、判定缺失逐字节回落现行行为。
> **技术栈**: FastAPI + Pydantic v2 / React19+TS / pytest+vitest。
> **门禁**: pytest 全量 ≥1556+新增全绿；tsc 零新增（存量 20 条不增）；vitest 300+全绿；C1-C5 存量断言不删改。

## 红线（Must NOT）
- 不改 Branch 1（空字段首填）/ Branch 2（同值跳过）/ prefill 豁免逻辑。
- 不豁免真矛盾（conflict 必须走三选一确认）。
- 不动 graphify / 图谱装配 / 不可动清单。
- 既有测试断言不删改（只允许因新行为新增测试）。
- relation 缺失/未知值 → 现行拦截行为（字符串比较 + 模板问题）。

---

## T1 [后端] C10 病理回归测试（先红后绿）

**Files:**
- Create: `backend/tests/unit/a1/test_d23_semantic_merge.py`

**测试清单（对应问题说明书四撞墙 + 兜底）**：
1. `test_equivalent_fill_auto_merges_without_proposal`：已填字段 + relation="equivalent" + merged_value → answers=融合值、pending_proposals 空、披露记录含 undo token。
2. `test_equivalent_missing_relation_falls_back`：relation=None → 现行为（拦截成提案）。
3. `test_complement_appends_child_on_multi_field`：角色.key_relations + relation="complement" → 值变 AnswerNode，children 追加新条目，无提案。
4. `test_complement_on_scalar_goes_proposal`：角色.desire + complement → 提案（question_text 用 LLM 问题，缺失用模板常量）。
5. `test_auto_merge_not_consumed_by_cap`：连续 5 次 equivalent 合并 → merge_counts 不增。
6. `test_undo_restores_previous_value`：undo(token) → 恢复旧值、披露记录移除。
7. `test_answer_view_deterministic`（C11）：AnswerNode{text,children} → "a；b；c" 稳定；str 直通。
8. `test_conflict_keeps_proposal_with_llm_question`：relation="conflict" + conflict_question → 提案带 question_text。
9. `test_children_cap_six`：已有 6 子条目再 complement → 走提案不追加。
10. `test_confirm_keyword_miss_intent_classified`：confirm 回复「这两个是一个东西」+ 分类器桩返回 merge → merge 执行不复读。

**Steps**: 写测试（FakeInterviewer 直接构造带 relation 的 InterviewFill）→ `pytest backend/tests/unit/a1/test_d23_semantic_merge.py` 全红 → 进入 T2/T3。

## T2 [后端] interviewer：schema + 提示词

**Files:**
- Modify: `backend/app/domains/creation/a1/interviewer.py`（InterviewFill L42-49；规则 3.5 L460-463）

**InterviewFill 增可选键（向前兼容先例 G10/G6b）**：
```python
relation: str | None = None          # equivalent|complement|conflict（对已填字段；空字段不填）
merged_value: str | None = None      # relation=equivalent 必给：融合表述（保留双方信息要点）
merge_target: str | None = None      # 多值字段：等价命中的既有子条目文本（前 12 字即可定位）
conflict_question: str | None = None # relation=conflict 时：结合语境的人话提问（三选一）
```

**规则 3.5 升级为 3.5R（语义分流判定）**——替换原文，要点：
> 3.5R 语义分流：fills 落点字段已在【用户已确定的内容】中有值时，必须判定 relation 并填写：
> ① equivalent（等价/细化：同一意思换述或加深）→ merged_value 必填=融合双方要点后的完整表述（保留用户原话质感，不得丢信息）；多值字段若只与其中一条等价 → 同时填 merge_target=那条的开头文字，merged_value 只融合那一条。
> ② complement（补充：新信息，不修改旧内容；多值字段的新一段）→ 不需要 merged_value。
> ③ conflict（真矛盾）→ conflict_question 必填=面向用户的人话提问（呈现旧值与新值的语境化对照，给出 替换/都要/先放着 三条路，禁用系统术语）。
> ④ 落点为空字段的 fill 不填 relation。判定拿不准时填 conflict（宁可问不可猜）。

**Steps**: 改模型 → 旧测试跑绿（可选键零破坏）→ 写 3.5R 文案 → commit。

## T3 [后端] guide_engine：AnswerNode + 语义路由 + 撤销

**Files:**
- Modify: `backend/app/domains/creation/a1/guide_engine.py`

**新增模型与函数**：
```python
class AnswerNode(BaseModel):
    """D23 层级条目：叶=无 children；旧 str 数据读时视为叶（零迁移）。"""
    text: str = ""
    children: list["AnswerNode"] = Field(default_factory=list)
    source: str = ""

def answer_view(value: "str | AnswerNode") -> str:  # C11 确定性渲染
    ...
def is_multi_value(module_id: str, subfield_id: str) -> bool:  # 读 subfield["multi"]
    ...
PROPOSAL_QUESTION_TEMPLATE = (  # 三副本收敛单点（文案与现行逐字一致，保测试）
    "你之前定过【{subfield}】是『{old}』。这次的『{new}』——"
    "是要**替换**它，还是两者**合并**（同一条里都保留），还是先**放弃**这条修改？"
)
```
A1Session 增（additive 默认值）：`auto_merge_log: list[dict]`（≤20 滚动）、`merge_undo: dict[str, dict]`（token→{key, prev}）。
Proposal 增：`question_text: str = ""`。

**_apply_fills Branch 3 语义路由**（保持 prefill 豁免在最前）：
```python
relation = (getattr(fill, "relation", "") or "").strip().lower()
if relation == "equivalent":
    if fill.merge_target and isinstance(old, AnswerNode):
        # 命中子条目合并（同类自动归并的等价路径）
        child = _find_child_by_prefix(old, fill.merge_target)
        if child is not None:
            child.text = (fill.merged_value or fill.value)  # + undo 快照/披露
            ...
    else:
        merged = (fill.merged_value or "").strip() or f"{answer_view(old)}；{fill_value}"
        # 写入 merged（str）、记 undo 快照、追加披露、file_diff、mark_field_source
        # 不消耗 merge_counts
    continue
if relation == "complement" and is_multi_value(fill.module, fill.subfield):
    node = old if isinstance(old, AnswerNode) else AnswerNode(text=answer_view(old) if old else "")
    if len(node.children) >= 6:      # 拍板 4 上限
        pass                          # 落到下方提案路径
    else:
        node.children.append(AnswerNode(text=fill_value, source=...))
        # + undo 快照/披露/file_diff/mark；continue
# conflict / complement(标量) / relation 缺失或未知 → 现行拦截路径
proposal = Proposal(..., question_text=fill.conflict_question or "")
```

**撤销函数**：
```python
def undo_auto_merge(session, token: str) -> dict:  # 恢复 prev、移披露记录；幂等 not_found
```
**resolve_proposal**：merge 分支——多值字段改为追加 child（children<6），标量维持 `f"{old}；{new}"` 拼接（存量断言零改动）。

**披露出口**：`handle_message` 返回 dict 增 `auto_merges: list[dict]`（additive；无则空表）。

**Steps**: 实现 → T1 测试逐个转绿 → 既有 write-guard 相关套件跑绿 → commit。

## T4 [后端] a1_routes：意图分类 + 披露 + 撤销端点

**Files:**
- Modify: `backend/app/api/a1_routes.py`（chat/confirm L872-950；chat 端点响应组装处）

1. **confirm 关键词失配**（现 L896-917 needs_clarification 复读替换）：
   - 意图分类器：interviewer 增 `classify_confirm_intent(old, new, reply) -> str`（chat_json 小调用：replace/merge/drop/other）；
   - other → **转发走访谈主线**（调用与 /api/a1/chat 同一处理函数，提案保持 pending），响应带转发标记；
   - 分类器异常 → 回落现行 needs_clarification（模板常量来自 T3 单点）。
2. **chat 响应 additive**：`auto_merges` 透传（序列化 dict）。
3. **新端点** `POST /api/a1/merge/undo` `{session_id, token}` → `undo_auto_merge`；幂等 not_found 200（对齐 resolve 先例）。
4. **answers 序列化兼容**：凡 API 输出 answers 字符串处改用 `answer_view()`；新增 `answers_tree`（结构化树，前端条目树用）。

**Steps**: 实现 + 单测（含 T1#10）→ commit。

## T5 [后端] 多值字段标注

**Files:**
- Modify: `backend/app/domains/creation/seed/story_modules.py`（M11 key_relations L146-152 增 `"multi": True`）
- 检查 `a1_question_tree.get_subfield` 是否透传自定义键；不透传则补。

## T6 [后端] 全量验证

`cd backend && .venv\Scripts\python -m pytest`（全量 ≥1556+新增全绿）；C1-C5 与 write-guard 存量套件零失败。

## T7-T10 [前端]（占位——探索代理回填精确 file:line 后补全）

- T7 types/a1.ts：`AnswerNode`/`AutoMergeDisclosure`/chat 响应 additive 字段/Proposal.question_text。
- T8 披露条组件（行内、非弹窗、带撤销按钮→POST /merge/undo）+ 挂载到聊天流（复用 D21 additive 信号接线先例）。
- T9 条目树渲染：answers 面板多值字段多条子条目可展开（消费 answers_tree）。
- T10 ProposalCard：question_text 优先展示（缺失回落现行文案）；vitest 用例。

## 验证与提交
- 每任务一提交：`feat(d23): ...` / `test(d23): ...`
- 终验：pytest 全绿 + tsc 零新增 + vitest 全绿 + 四撞墙场景手工回归
- PROJECT_STATE 收尾更新
