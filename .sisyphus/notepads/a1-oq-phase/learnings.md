# Learnings

## T1 (2026-10-19) — Schema + 进入/闭合状态机

### 文件与行号
- A1Session 新字段：`backend/app/domains/creation/a1/guide_engine.py` ~L777-782（mirror_thread 后紧邻落位）：`oq_phase_active: bool = False` / `oq_round: int = 0`
- 状态机模块：`backend/app/domains/creation/a1/oq_phase.py`（零 LLM）— `OQ_ROUND_CAP=2` / `pending_count` / `continue_allowed` / `begin_or_reopen(session, oq_log)` / `maybe_close(session, oq_log)`
- 进入点：`closing_flow.advance_answer(session, text, oq_log=None)` Q1 "continue" 分支 → `begin_or_reopen`；达帽 → `OQ_ROUND_CAP_NOTICE`（"答满两轮"）+ 照常推进 Q2
- 透传链（全 additive kwarg，默认 None=旧行为逐字节）：routes `handle_message(session, text, interviewer, oq_log)` → `_handle_message_impl(oq_log=)` → `_round_end_signals(oq_log=)`（两处调用点 L2254/L2299）→ `closing_flow.interject(oq_log=)` → `advance_answer`
- 闭合点：`a1_routes.py` skip 分支（~L796）与 mark_answered 成功后（~L870）调 `maybe_close(session, oq_log)`

### 事件契约（T2/T3/T4 依赖）
- `oq_phase_entered`：`{session_id, event, round}`（round = 进入后计数：首进=1，重开=2）
- `oq_phase_closed`：`{session_id, event, round, answered, skipped}`（answered/skipped = 全日志累计计数，无 reason 枚举）
- 落盘：`backend/data/inspiration_log.jsonl`（经 inspiration_log.emit_event，异常静默）

### 语义决策
- round 编码 = "进入次数"（首进即 +1）而非 "重开次数"：仅两字段即可区分 fresh/closed-after-round-1，达帽判定 `oq_round >= 2` 恰好放行两轮
- 重开由 T3 的第二次收尾复用同一次 `advance_answer("继续访谈")` 路径——T1 无需单独接线
- begin_or_reopen 幂等：已在相位中返回 True 不再 +1；待问=0 返回 False（自由访谈语义保持）

### 锁测试扩容（additive 两键）
- `test_delivery_intent.py::_T9_SESSION_FIELDS` + `oq_phase_active, oq_round`
- `test_three_tier_contract.py::_A1SESSION_NEW_FIELDS` + 同两键

### 坑
- `test_d23_routes.py` monkeypatch `a1_routes.handle_message` 为 3 参 fake → 路由加第 4 参后 TypeError；已改 fake 签名 `(session, message, interviewer, oq_log=None)`
- 定向 pytest 需 `--no-cov`（全量 pyproject 80% 覆盖率门禁对定向跑必炸）
- ruff 基线：touched 文件 HEAD 上本有 49 错（存量），本批新码 0 增量（新文件不带 `-*- coding -*-`、import 按 isort 序、无嵌套 if/SIM300）

## T2 (2026-10-19) — chat 前置相位门（确定性路由）

### 落点与结构
- 门：`guide_engine._handle_message_impl`，F2 短指令 return 块之后、`PHASE_COMPLETED` 分支之前：
  `if session.oq_phase_active and text.strip(): gate_out = _oq_phase_gate(session, text, oq_log); not None → return`
- `_oq_phase_gate(session, text, oq_log)`（guide_engine 内，紧邻 `_chat_proposal_directive`）：
  - oq_log=None → None（旧调用方零改动放行级联）
  - next_pending()=None → `maybe_close`（竞态复位+closed 埋点）→ None 落回级联
  - 有待问 → `mark_answered(id, text.strip()[:2000])`（J4 截断先例）→ 回执模板；
    末题 → `maybe_close` + `ANSWER_LAST_NOTE`（T3 二次收尾话术接缝）
- 回执 dict 形状 = F2 同款：reply/next_question(_question_payload)/file_diff/progress/phase（零新键）
- routes skip 分支：相位激活时 reply 换 `SKIP_NEXT_TMPL`/`SKIP_LAST_NOTE`（模板常量在 oq_phase.py）

### 模板常量（oq_phase.py，T3/T4 依赖）
- `ANSWER_NEXT_TMPL = "已记下你的回答。下一问：{question}"`
- `ANSWER_LAST_NOTE = "已记下你的回答。开放问题都答完了，可以随时在这里收尾定稿。"` ← T3 在此注入重定稿语义
- `SKIP_NEXT_TMPL / SKIP_LAST_NOTE`

### 门序（共存矩阵 additive 行）
F2 短指令 > oq 相位门 > 六通道级联。证明方式：spy `_round_end_signals`（轮末定序零触达）+ interviewer.calls==0。
坑：不能 spy `_handle_message_impl` 本身（每条消息都进 impl，F2/门都在其内部）。

### 测试
- `tests/unit/a1/test_oq_phase_gate.py` 6 用例：确定性作答零 LLM / 16:21 病例守护（closing_step=2+原句→零 fills 零 proposals、作答落 oq、末题闭合）/ 提案共存消解回 oq / 末题闭合接缝 / 竞态兜底复位回级联 / 矩阵门序
- 全量 a1 套件 1368 passed；ruff 增量 0（新文件 I001/ARG001 已修：spy 签名 noqa）

## T3 (2026-10-19) — 第二次收尾触发 + 产物语义注入

### 落点
- `closing_flow.py`：`maybe_trigger(session, *, variant="first")` 参数化（默认 first 前缀逐字节不变）；新增 `REFINALIZE_PREFIX`（"开放问题都答完了。你的回答已并入设定，重新定稿后文档会同步更新：…"）+ `retrigger_after_oq(session) -> str | None`：
  - 收尾态进行中（1..3）→ None（幂等）；预设门禁未满（phase!=completed / pending_proposals 非空）→ None（>50% 只进不出零触碰）
  - 否则 settled 解锁一次 + closing_step=1 + refinalize 前缀 + Q1 原文案（QUESTIONS 零复制）
- 触发点（三处，全部 maybe_close==True 后）：T2 门末题作答（reply 追加 \n+prompt）/ routes 末题作答（out["reply"] 追加）/ routes 末题跳过（reply 追加）。竞态兜底复位**不**触发二次收尾。

### 契约（T4 前端消费）
- ChatResponse additive：`oq_phase_active: bool`（skip 分支 + 主路径均有）；既有 `closing` 信号在二次收尾触发后 = `{step:1, settled:false, triggered:true}` → ClosingPanel 复用判据
- GET /file additive：`oq_phase_active` + `pending_question {id,question}` + `pending_questions_count`（复用 _open_question_payload）
- 末题回执 reply 形态：`ANSWER_LAST_NOTE\nREFINALIZE_PREFIX+Q1文案`

### 测试坑
- retrigger 前提 = 收尾双条件：`session.phase == PHASE_COMPLETED`（"completed"）+ answers 真值填满（all_subfield_keys）+ pending_proposals 空——单测夹具须三件齐备（真实链路首次收尾时已满足）
- TestClient 契约测可直改 `a1_routes._SESSIONS[session_id]` / `_FILES[file_id]["open_questions"]` 绕过收尾链路直达门态

### 数字
- 新测 6 用例红→绿；全量 a1 套件 1374 passed；ruff 基线 19 持平（新文件 I001 已修）

## T4 (2026-10-19) — 前端相位驱动 UI

### 落点
- `A1Workspace.tsx`：**删竞态源** = 原 L548-560 file 派生 pendingQuestion effect 整段删除（`deriveOldestPendingQuestion` 函数保留导出，GoAnswerLoop.test 仍引用）；`openQuestions` state 转仅写（`const [, setOpenQuestions]`，读取面只剩 stableOpenQuestions→localFileData，与本 state 无关）
- 相位态：`oqPhaseActive`（chat 响应实时值优先）+ `closingVariant: 'first'|'refinalize'`（prevPhase=true 且响应 oq_phase_active=false 且 closing.triggered → refinalize）
- 冷启动恢复：hydrate 块读 file 新键 `oq_phase_active`/`pending_question`/`pending_questions_count`，active 时一次性 set（chat 响应随后覆盖，单源不竞态）
- 定稿禁用：`disabled={!finalizable || isChatLoading || oqPhaseActive}` + tooltip「先答完/跳过开放问题，从收尾处定稿」
- `GuidedChat.tsx`：新 prop `oqPhaseActive` → placeholder=当前待问文本、✦ 卡 `data-phase="active"` 高亮、顶部 `proposal-banner`（proposals 非空，输入可用）
- `ClosingPanel.tsx`：`variant?: 'first'|'refinalize'`（PANEL_COPY 常量表；缺省 first 文案字节不变；data-variant 属性供测试/E2E）
- ChatResponse 类型 + file fetch 泛型 additive `oq_phase_active`

### T4 → T5 E2E 钩子
- `pending-question-card[data-phase="active"]`：相位激活判据
- `proposal-banner`：横幅判据；`closing-panel[data-variant="refinalize"]`：二次收尾面板判据
- 定稿按钮 title=「先答完/跳过开放问题，从收尾处定稿」= 禁用判据
- placeholder = 当前问文本（直接 getByPlaceholderText(问题文本)）

### 数字
- 新测 9 用例（GuidedChat 4 + ClosingPanel 2 + A1Workspace 恢复 3）红→绿；全量 vitest **343 passed**（基线 334+9）
- tsc -b = 20 errors = 既有存量（先前 22 → 修掉本批引入的 merge_preview fixture + openQuestions 未读两枚 → delta 0）

## T5 (2026-10-20) — E2E 幕六 + 全门禁

### 幕六实现要点（tests/e2e/a1-wave3-frontend.spec.ts）
- 状态化 chat mock：按请求体路由（`body.skip_question_id` → skip 闭包响应；否则按 chatTurn 序号
  1 快进 / 2 首收 / 3 相位进入 / 4 作答回执）——比按 URL 分支更贴近真实会话序
- 幕六收尾流要发**两条**快进消息（turn1 普通 + turn2 首收 closing 信号）才有 ClosingPanel
- 相位内 placeholder 会替换掉 "Type your message..."：答题轮必须用 `getByPlaceholder(OQ_Q1)` 定位
- PW 1.62 API 名是 `getByPlaceholder`（不是 getByPlaceholderText）
- closing-state mock 需带 preview.consumers（P0-7 教训沿用）；注册顺序：专用路由晚于通配 file 路由

### 门禁数字（详见 evidence/oq-phase-t5-gate.txt）
- pytest 1875 passed / vitest 343 / tsc 20(delta 0) / ruff 463=HEAD(delta 0)
- wave3 五幕 5/5 绿；幕六唯一红点 = issues.md 登记的 skip→variant 真实 bug（frontend，未修）
- graph.spec.ts 36 failed 为存量遗留（/api/graph/* mock 缺失，与本批无关，零触碰）

## T5-FIX (2026-10-20) — skip→refinalize variant 修复
- 一行级镜像修复：skipPendingQuestion 与 sendMessage 共用同一条件式（prevPhase 捕获 + closing.triggered
  && prevPhase && oq_phase_active===false → refinalize）。同类双入口（send/skip）状态迁移判定今后应抽
  共用小函数防再漂移（记录，未顺手重构）。
- 锁定用例落在 A1Workspace.oqPhaseRestore.test.tsx（skip 末题 → panel data-variant="refinalize"），
  防回归。vitest 344 / playwright wave3 6/6 / tsc 20 delta0 / 后端零改动。

## T6 (2026-10-20) — 治理登记
- PROJECT_STATE.md「当前阶段」头部新增 a1-oq-phase 批综合节（病理链/状态机设计/Metis 六缺口/提交链/门禁数字/17 文件白名单/拍板注记/遗留/下一步）+「遗留问题」补两行（改已答内容 out-of-scope / 双入口判定抽函数建议）。diff +2 行纯追加。
- MOC（docs/README.md 变更记录）：最近两批（10-19 商业加固/配方图谱修复）均未加行 → 按惯例本批不加（且本批无新 docs/plans 文稿可链）。
- decision-log：产品方默认拍板=近批惯例仅 PROJECT_STATE 落痕，不新增 D 条目；批内注记 design 拍板 2026-10-19（二次收尾三联问文案复用只换产物语义）。
- 本批未提交（工作区待产品方真机验收后统一入库——与近批「验收后入库」惯例一致，T6 只做文档落痕）。
