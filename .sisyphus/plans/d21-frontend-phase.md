# D21 前端阶段：说人话文案整改 + 四组件 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal**: 完成 D21 前端阶段——访谈体验说人话（清内部模块名）+ 四新组件（收尾三连问面板/对齐推测卡/罗盘/α 版本标记），含支撑它们的最小后端 HTTP 补面。

**Architecture**: 后端 D21 领域层已收官（closing_flow/alignment_flow/impulse_coords/draft_version 函数级就绪），但四个能力缺 HTTP 暴露——先补 3 个小端点任务（全部 additive，零既有字段改动），同时并行做前端文案整改（三文件三白名单点），最后四组件挂载（挂点已行号级定位）。

**Tech Stack**: FastAPI+Pydantic（后端补面）/ React 19+TS+Tailwind v4（前端）/ pytest（后端 TDD）/ vitest（前端 TDD）/ Playwright（QA）

---

## 背景与事实基座（探索已完成，施工者必读）

### 权威依据
- `docs/前端手册.md` §8（D21 前端施工依据：8.1 文案整改 / 8.2 四组件 / 8.3 四不做）
- `docs/governance/4_ux-flow-v0.3.md` §5（访谈体验铁则：说人话表含正反例 / 不提示 / 罗盘三值纠偏不做滑块 / α 标记）
- `docs/decision-log.md` D21 综合立项（⑦切换/⑧双条件/⑩静默/⑪说人话/⑫罗盘/⑬对齐+α）

### 后端就绪面（零改动，直连）
| 能力 | 现状 | 位置 |
|---|---|---|
| GET `/api/a1/file/{id}/impulse-coords` | 返回 `{axis, confidence, safety_flag, anchor, anchor_source, adjustments, reorder_count, audit}` | a1_routes.py:1054-1066 |
| POST `/api/a1/file/{id}/recipe-switch` | `{target}` → `{applied, recipe_modules, first_question}` | a1_routes.py:1075-1109 |
| 收尾三连问 | chat reply 文本追加（TRIGGER_PREFIX+问题文案已说人话）；closing_step/settled/answers 是 **A1Session 持久化字段** | closing_flow.py（QUESTIONS q1/q2/q3 + interject） |
| 对齐提案 | `_maybe_propose_alignment` 装包 `session.pending_alignments`，reply 追加 `_alignment_notice` 文本；`resolve_alignment(session, key, accept, registry_db)` 函数就绪 | alignment_flow.py:324-374 |
| D20 邀约 | reply 追加说人话通知文本 | guide_engine.py:1075-1181 |
| 定稿版本徽标 | 图谱页已解析 graph_code 后缀 `-v(\d+)$` 显示「已定稿 vX ✓」+ stale 黄条 | A1GraphSection.tsx:492-494/663-671 |

### 后端缺口（本计划 Wave 1 补齐，前端手册 §8.2 已预告「待建」）
1. chat 响应**不含** pending_alignments 结构化数据（仅文本通知）——前端无法渲染对齐卡
2. `resolve_alignment` 无 HTTP 端点——用户无法从 UI 裁决提案
3. closing 状态（step/settled）与 `build_output_preview(file_id)`（closing_gate.py:182）无端点——刷新后前端无法恢复收尾面板、无法展示可生成物预览
4. 罗盘三值纠偏（更像讲故事/差不多/更像建设定）无用户信号端点——现有 SIGNALS 五个全是间接信号（pack_applied/pack_rejected/fill_confirmed/fill_rejected/skipped）
5. draft_version（α）纯内存无 API 暴露

### 前端硬点（行号级）
| 硬点 | 位置 | 整改 |
|---|---|---|
| 问题头「【section_label · sub_label】」拼接 | `A1Workspace.tsx:269-276` formatQuestion() | 去头——直接问句（ux-flow §5.1：✅「你故事的开场是哪一幕？」） |
| 进度栏列模块名 | `DimensionProgress.tsx`（label 来自后端 progress()） | 改计数式「聊聊你的世界 N/M」——**无需映射表** |
| fills 字段暴露内部名 | `ProposalCard.tsx:56-57`：`字段：{fieldLabel \|\| `${module}.${subfield}`}` | fieldLabel 缺失时人话兜底，绝不暴露 `module.subfield` 形态 |
| 挂点：罗盘 | A1Workspace.tsx 右栏 1284-1341 区 | 常驻显示 |
| 挂点：收尾面板 | A1Workspace.tsx footer 1344-1375 区 | 双条件触发 |
| 挂点：对齐卡 | GuidedChat 消息流内（DiceRecommendationCard 先例 GuidedChat.tsx:51-79） | pending_alignments 渲染 |
| α 徽标 | IPPoster.tsx 无版本显示；A1GraphSection 已有 vX 徽标 | IPPoster 新增；图谱页复用 |
| api 层先例 | `frontend/src/api/`（fetchJson 封装模式） | 新增 client 函数 |

### 关键设计裁决（已定，施工者照办）
1. **不需要 section_label 映射表**——问题头直接删除（零模块名），进度栏用纯计数（N/M），彻底规避「未知模块漏出内部名」风险。
2. **StructuredFilePanel 冻结**：维持模块名不动（ux-flow §5.1 只点名进度条/问题头/fills；结构化面板=溯源性质，例外范围）。写为 MUST NOT。
3. **SIGNALS 扩枚举合法**：冻结闭集是 ALIGN_ACTIONS（四动作）与发号字母；SIGNALS 非冻结——additive 追加三个用户直纠信号，既有五个逐字不动。
4. **chat 响应只增不改**：新增 `closing` 与 `pending_alignments` 字段 additive；既有字段语义零触碰。
5. **对齐/收尾互斥由后端定序保证**（ROUND_SIGNAL_ORDER: 先对齐后收尾，guide_engine.py:1196），前端无需额外互斥逻辑。
6. **resolve 过期行为**：`resolve_alignment` 未知 key 返回 `{applied:false, error:"not_found"}`（幂等不抛错）——前端移除卡片+toast「这条已经处理过了」。注意经验教训：404 识别须兼容 ApiError(.status) 与 fetchWithTimeout 降级 Error('HTTP 404') 双路径。
7. **safety_flag=true 时罗盘纠偏按钮禁用**（单向棘轮=不可逆，纠偏无意义），坐标照常显示。
8. **三值纠偏重复点击**：后端已有护栏（每会话上限+冷却轮阻尼，impulse_coords.py:168-181），前端按钮保持可点、以响应的 applied 结果更新坐标——不做前端单选锁定。
9. **α 版本降级**：draft_version 内存态，端点无数据/会话重启后 → IPPoster 草稿徽标显示「草稿」字样不带数字（不渲染假版本号）；定稿产物继续用 -vN 解析（已有）。
10. **纯函数抽取**（经验库约束）：文案整整改抽导出纯函数，组件内只接线——测试断言纯函数而非快照。

### 明确不做（D21 §8.3，MUST NOT）
- 两级卡片分组 UI；人格卡任何形式前端（勿在 /persona-card 上建组件）；路线调整弹窗提示（静默）；新会话入口。
- 范围蔓延锁死：文案整改只限三白名单点（问题头/进度栏/ProposalCard 兜底）；罗盘无历史记录/趋势图；对齐卡无批量操作；收尾预览只读无下载；α 无版本 diff。

---

## 验证策略

- **测试决策**：基础设施存在（pytest 1502 基线 / vitest / Playwright）——**TDD**（每任务先红后绿）。
- **后端命令**：`cd backend && python -m pytest tests/ -x -q`（全量基线 1502 passed / cov 83.52% 门禁 80%，不允许跌破）；新端点先写契约测试。
- **前端命令**：`cd frontend && npx tsc -b --noEmit`（0 错基线）&& `npx vitest run`（全绿基线）。
- **QA 场景**：每任务附 agent 可执行场景（curl 冒烟/Playwright DOM 断言），证据存 `.sisyphus/evidence/task-{N}-*.{ext}`。

---

## 执行波次

```
Wave 1A（后端补面·串行——同文件 a1_routes.py，与 Wave 1B/2 并行启动）:
├── T1: closing-state GET 端点 + chat 响应 additive 收尾信号
├── T2: 对齐提案序列化进 chat 响应 + resolve POST 端点
└── T3: impulse-coords/signal POST（三值纠偏） + draft-version GET
Wave 1B（前端文案·三文件并行，与 Wave 1A 同时开工）:
├── T4: formatQuestion 去头（A1Workspace.tsx）
├── T5: DimensionProgress 计数式人话化
└── T6: ProposalCard fieldLabel 兜底
Wave 2（前端 api 层 + 四组件，依赖 Wave 1A+1B）:
├── T7: api/ 层五个新端点 client 封装（依赖 T1-T3）
├── T8: 罗盘组件（依赖 T7；挂 A1Workspace 右栏——T4 完成后）
├── T9: 收尾三连问面板（依赖 T7；挂 footer——T4 完成后）
├── T10: 对齐推测卡（依赖 T7；挂 GuidedChat 消息流）
└── T11: α 版本标记（依赖 T7；IPPoster + 图谱页复用）
Wave FINAL: F1-F4 四审 → 用户确认
```

- Wave 1A 三个任务**串行**（同一文件 a1_routes.py，避免编辑冲突）；Wave 1A 与 Wave 1B 两轨并行。
- Wave 2 五任务并行（不同文件）；T8/T9 挂 A1Workspace 须待 T4 完（单文件编辑权纪律）。
- 临界路径：T1→T7→T8/T9/T11 → FINAL。

---

## TODOs

- [x] 1. closing-state GET 端点 + chat 响应收尾信号（additive）

  **What to do**:
  - 新增 `GET /api/a1/file/{file_id}/closing-state`：返回 `{file_id, closing_step, closing_settled, triggered, preview}`——`triggered = closing_step > 0 and not closing_settled`；`preview` = `build_output_preview(file_id)`（closing_gate.py:182，按动机分层的可生成物清单）输出。会话不存在 → 404（沿用 `_session_for_file_or_404` 先例）。
  - chat 响应（a1_routes.py:746 chat() 出口处）additive 注入 `closing: {step, settled, triggered}`——数据取自 `session.closing_step/closing_settled`。**既有字段一个不动**。
  - TDD：先写契约测试 `tests/unit/api/test_a1_closing_state.py`（或并入既有 a1 路由测试文件，跟随同目录先例）：①未触发会话 GET → step=0/triggered=False/preview 非空（preview 结构断言到具体键）；②触发中会话（构造 closing_step=2）→ step=2/triggered=True；③settled 会话 → triggered=False；④chat 响应含 closing 键且既有键齐全（断言既有键清单逐字）。

  **Must NOT do**: 不改 closing_flow.py 文案与状态机；不动 chat 既有字段语义；不建独立 router 文件（并入 a1_routes.py 既有结构）。

  **Recommended Agent Profile**: **Category**: `deep`（响应契约变更需谨慎）；**Skills**: [`test-driven-development`]
  **Parallelization**: 可与 T4-T6 并行；与 T2/T3 串行（同文件）。**Blocks**: T7, T9。**Blocked By**: 无。
  **References**: a1_routes.py:746-865（chat 出口注入点）、a1_routes.py:1054（`_session_for_file_or_404` + 端点定义先例）、backend/app/domains/creation/a1/closing_flow.py（QUESTIONS/状态字段）、closing_gate.py:182（build_output_preview 签名与返回形状——先读它确定 preview 键名再写测试）。
  **Acceptance**:
  - [ ] 新契约测试 4 例先红后绿
  - [ ] `python -m pytest tests/ -x -q` 全量全绿（≥1502）；若既有 chat 响应测试因 additive 字段全等断言失败 → 最小改该断言为子集断言并在提交信息注明
  **QA Scenarios**:
  ```
  Scenario: curl 冒烟 closing-state
    Tool: Bash (curl)
    Steps: 起后端 → POST /api/a1/session/start 建会话 → GET /api/a1/file/{id}/closing-state
    Expected: 200 且 JSON 含 closing_step=0, triggered=false, preview 非空对象
    Evidence: .sisyphus/evidence/task-1-closing-state-curl.txt
  Scenario: 404 错误路径
    Steps: GET /api/a1/file/nonexistent/closing-state → 断言 404
    Evidence: .sisyphus/evidence/task-1-closing-state-404.txt
  ```
  **Commit**: YES `feat(a1): closing-state endpoint + chat closing signal (additive)`

- [x] 2. 对齐提案序列化 + resolve POST 端点

  **What to do**:
  - chat 响应 additive 注入 `pending_alignments: [{key, action, content, quote, stale_warning}]`——从 `session.pending_alignments` 序列化（AlignProposal 字段，alignment_flow.py:60-77）；**target（节点 id）与 graph_code 绝不外露**（G5 雷区，文案契约见 alignment_flow.py docstring）。key = pending_alignments 的 dict 键（resolve_proposal 惯例）。
  - 新增 `POST /api/a1/file/{file_id}/alignment/{key}/resolve`，body `{accept: bool}` → 调 `resolve_alignment(session, key, accept, registry_db=会话对应 db 路径——参照既有 registry 接线先例查找)`，返回 `{applied, accept}`；not_found → 200 + `{applied:false, error:"not_found"}`（幂等不抛错，领域函数已如此）。
  - TDD：`tests/unit/api/test_a1_alignment_resolve.py`：①构造 pending_alignments 一条 → chat 响应序列化字段逐字断言（含人话 content、无 target 字段）；②accept=True → applied=True 且 pending 清空；③accept=False → 零副作用；④未知 key → 200 not_found；⑤action 枚举逐字 ∈ {link,dedupe,contradict,update}（闭集断言，不允许添加或修改）。

  **Must NOT do**: ALIGN_ACTIONS 四动作枚举逐字冻结不动；不外露 target/graph_code；不改 resolve_alignment 领域函数签名（端点适配它，不是它适配端点）。
  **Recommended Agent Profile**: **Category**: `deep`；**Skills**: [`test-driven-development`]
  **Parallelization**: 与 T4-T6 并行；接 T1 后串行。**Blocks**: T7, T10。**Blocked By**: T1。
  **References**: alignment_flow.py:324-374（resolve 签名/幂等语义）、alignment_flow.py:40-77（AlignProposal 字段）、a1_routes.py:868-953（chat/confirm 的 resolve_proposal 端点先例——key 从 dict 取的习惯）、guide_engine.py:1270-1291（_round_end_signals 定序）。
  **Acceptance**:
  - [ ] 契约测试 5 例先红后绿；全量 pytest 全绿
  **QA Scenarios**:
  ```
  Scenario: curl 对齐全循环
    Tool: Bash (curl)（或 pytest 内构造——若 LLM 提议无法 curl 触发，用测试夹具直接注入 pending_alignments 后起服务验证端点）
    Steps: 注入提案 → GET chat 响应含 pending_alignments → POST resolve accept=true → 再 GET 已清空
    Expected: 三步各自 200，字段如上
    Evidence: .sisyphus/evidence/task-2-alignment-curl.txt
  Scenario: 幂等双击
    Steps: 同一 key resolve 两次 → 第二次 {applied:false, error:"not_found"}
    Evidence: .sisyphus/evidence/task-2-alignment-idempotent.txt
  ```
  **Commit**: YES `feat(a1): alignment serialization + resolve endpoint`

- [x] 3. impulse-coords/signal POST（三值纠偏）+ draft-version GET

  **What to do**:
  - `backend/app/domains/creation/a1/impulse_coords.py` SIGNALS 表 additive 追加三个用户直纠信号（**逐字，不允许添加或修改既有五个**）：`user_nudge_story`（更像讲故事，axis 向叙事侧）/ `user_nudge_builder`（更像建设定，axis 向建构侧）/ `user_nudge_confirm`（差不多，只升置信度不动轴或最小动——按既有 spec 字段 conf_d/axis_base 模式定参数，读 §10.1 设计注释后落定并在测试中固化）。
  - 新增 `POST /api/a1/file/{file_id}/impulse-coords/signal`，body `{signal: str}` → 白名单校验（只收上述三个，其余 400）→ `apply_signal(session, signal)` → 返回 `{applied, axis, confidence}`（dashboard 字段子集即可，含阻尼 applied=false 情形——护栏语义透传不隐藏）。
  - 新增 `GET /api/a1/file/{file_id}/draft-version`：读会话 draft_version 内存态（`new_draft_state` 域，guide_engine.py:278 注释所指），无 → `{available: false}`；有 → `{available: true, version: "α0.x", baseline, round}`（版本串格式按 draft_version 域实际函数输出，先读再定）。
  - TDD：`tests/unit/api/test_a1_coords_signal.py` + `test_a1_draft_version.py`：①三信号各一例 axis 方向断言（story 与 builder 方向相反）；②非法 signal → 400；③阻尼路径（构造 adjustments 超限）→ applied=false 且 200；④draft-version 两态。

  **Must NOT do**: 既有 SIGNALS 五枚举与护栏逻辑零改动；不做前端滑块配套的连续值端点（离散三值 only）。
  **Recommended Agent Profile**: **Category**: `unspecified-high`；**Skills**: [`test-driven-development`]
  **Parallelization**: 与 T4-T6 并行；接 T2 后串行。**Blocks**: T7, T8, T11。**Blocked By**: T2。
  **References**: impulse_coords.py:62-66（SIGNALS 常量区）、:147-204（apply_signal 护栏）、:302-314（dashboard_data）、draft_version 域文件（git grep `new_draft_state` 定位，先读其函数签名与状态形状）、a1_routes.py:1054（端点先例）。
  **Acceptance**:
  - [ ] 契约测试先红后绿；全量 pytest 全绿 + cov ≥80%
  **QA Scenarios**:
  ```
  Scenario: curl 三值信号
    Steps: POST signal=user_nudge_story → 断言 200 且 axis 移动方向正确（对比 GET impulse-coords 前后值）
    Evidence: .sisyphus/evidence/task-3-signal-curl.txt
  Scenario: 非法信号 400
    Steps: POST signal=slider_0.7 → 400
    Evidence: .sisyphus/evidence/task-3-signal-400.txt
  ```
  **Commit**: YES `feat(a1): coords nudge signal + draft-version endpoints`

- [x] 4. formatQuestion 去头（A1Workspace.tsx）

  **What to do**:
  - `A1Workspace.tsx:269-276` formatQuestion()：**删除「【section_label · sub_label】」头**，返回 `${nq.question}${example}`（问句+示例直接呈现，ux-flow §5.1 ✅例「你故事的开场是哪一幕？」）。
  - 抽纯函数：新建 `frontend/src/labels/plainQuestion.ts` 导出 `plainQuestion(nq)`，A1Workspace 内 formatQuestion 改为薄接线（经验库：纯函数抽导出优先于快照测试）。
  - TDD：`frontend/src/labels/__tests__/plainQuestion.test.ts`：①输出不含 `【`；②输出不含 section_label/sub_label 值（传入含模块名的 fixture 断言零泄漏）；③question+example 拼接保持。先红（函数不存在）后绿。
  - 排查既有测试对问题头格式的断言（`git grep "【" frontend/src -- *_test*`）并同步更新为无头断言。

  **Must NOT do**: 只允许改动 A1Workspace.tsx 的 formatQuestion 函数区与新增 labels 文件——**不碰该文件其它区域**（右栏/footer 挂点归 T8/T9）；QuestionPayload 接口零改动（后端契约不动）；不删 hint 字段消费（QuestionHint 组件另议——本期维持现状）。
  **Recommended Agent Profile**: **Category**: `quick`；**Skills**: [`test-driven-development`]
  **Parallelization**: 可与 T1-T3、T5、T6 并行。**Blocks**: T8, T9（A1Workspace 单文件编辑权）。**Blocked By**: 无。
  **References**: A1Workspace.tsx:269-276（整改点）、A1Workspace.tsx:42-44（QuestionPayload）、frontend/src/labels/relationLabel.ts + 其 __tests__（纯函数+测试同居先例）、4_ux-flow-v0.3.md §5.1（正反例逐字）。
  **Acceptance**:
  - [ ] 新测试先红后绿；`npx tsc -b --noEmit` 0 错；`npx vitest run` 全绿
  - [ ] `git grep "【" -- frontend/src/pages/a1/A1Workspace.tsx` 零命中（图谱页等例外文件不在范围）
  **QA Scenarios**:
  ```
  Scenario: 浏览器断言问题头人话化
    Tool: Playwright（起前后端，走 /a1 选卡开始会话）
    Steps: 等首个问题渲染 → 读取消息区文本 → 断言不含 "【" 且不含模块 label（如 "IP定位"）
    Expected: 纯问句呈现
    Evidence: .sisyphus/evidence/task-4-question-plain.png（截图）+ .txt（文本抓取）
  Scenario: 回归——问句本体未被误删
    Steps: 断言问句文本非空且以问号/句号结尾
    Evidence: 同上文件
  ```
  **Commit**: YES `refactor(a1-ui): strip module-name question header (D21-11)`

- [x] 5. DimensionProgress 计数式人话化

  **What to do**:
  - `frontend/src/components/structured/DimensionProgress.tsx`：进度显示改为「聊聊你的世界 {done}/{total}」主行（ux-flow §5.1 ✅例）+ 完成/未完成格子（保留格子视觉，**去掉模块名 label 文本**，可保留 done 状态样式）。总数用 props 的 sections.length 动态取——**禁止硬编码 /10 假设**（Metis 边界 7）。
  - 抽纯函数 `plainProgressLabel(done, total)` 入 `frontend/src/labels/plainQuestion.ts`（同居，或新建 plainProgress.ts——跟随 labels 目录单一职责判断）。
  - TDD：`DimensionProgress.test.tsx` 增例：①渲染文本含「聊聊你的世界 3/7」（构造 3/7 fixture——非 10 总数防硬编码）；②无任何模块 label 文本泄漏（传入含「IP定位」等 label 的 fixture，断言 queryByText 为 null）。

  **Must NOT do**: **StructuredFilePanel.tsx 零改动（冻结令——溯源例外维持模块名）**；不改组件 props 接口（数据照旧传入，只是不渲染 label）；不动 A1Workspace 组装 progress 的代码。
  **Recommended Agent Profile**: **Category**: `quick`；**Skills**: [`test-driven-development`]
  **Parallelization**: 与 T1-T4、T6 并行。**Blocks**: 无。**Blocked By**: 无。
  **References**: DimensionProgress.tsx:10-26（受控组件）、A1Workspace.tsx:1034-1045 及 chat 响应处（sections 组装——只读参考）、DimensionProgress.test.tsx（既有测试先例）。
  **Acceptance**:
  - [ ] 测试先红后绿；vitest 全绿 + tsc 0 错
  **QA Scenarios**:
  ```
  Scenario: 浏览器断言进度栏人话
    Tool: Playwright（/a1 访谈态）
    Steps: 断言右栏进度区文本匹配 /聊聊你的世界 \d+\/\d+/ 且不含任一模块 label（"IP定位"/"历史时间线" 等清单逐字排除）
    Evidence: .sisyphus/evidence/task-5-progress-plain.png
  ```
  **Commit**: YES `refactor(a1-ui): count-based plain progress label (D21-11)`

- [x] 6. ProposalCard fieldLabel 兜底

  **What to do**:
  - `ProposalCard.tsx:56-57`：字段显示改为 `fieldLabel || '你刚才说的内容'`（人话兜底）——**绝不渲染 `${module}.${subfield}` 形态**。优先级：有 fieldLabel 用真值（后端修复后自动受益，Metis 边界 5）、无则兜底。
  - TDD：`ProposalCard.test.tsx` 增例：①无 fieldLabel → 渲染含「你刚才说的内容」且文本不含 `.` 连接的 module.subfield 形态（正则断言无 `[\u4e00-\u9fa5]+\.[\u4e00-\u9fa5]+` 式内部键——用 ASCII 点加字母形态断言更稳：无 `/[a-z_]+\.[a-z_]+/`）；②有 fieldLabel → 显示真值。

  **Must NOT do**: 不改 A1Proposal 类型；不动提案的「原设定 vs 新内容」双盒与三动作（替换/合并/放弃）——那是既有交互。
  **Recommended Agent Profile**: **Category**: `quick`；**Skills**: [`test-driven-development`]
  **Parallelization**: 与 T1-T5 并行。**Blocks**: 无。**Blocked By**: 无。
  **References**: ProposalCard.tsx:13-22（props）与 :56-57（兜底点）、ProposalCard.test.tsx（既有断言风格）。
  **Acceptance**:
  - [ ] 测试先红后绿；vitest 全绿 + tsc 0 错
  **QA Scenarios**:
  ```
  Scenario: 组件测试即证据（无独立浏览器场景——fills 需 LLM 真实提案）
    Tool: vitest（组件测试渲染断言如上两例）
    Evidence: .sisyphus/evidence/task-6-proposal-fallback.txt（vitest 输出）
  ```
  **Commit**: YES `refactor(a1-ui): human fallback for proposal field label (D21-11)`

- [x] 7. 前端 api 层五端点 client 封装

  **What to do**:
  - `frontend/src/api/`（跟随既有 fetchJson 封装模式）新增：`getClosingState(fileId)`、`resolveAlignment(fileId, key, accept)`、`nudgeCoords(fileId, signal)`、`getDraftVersion(fileId)`、`getImpulseCoords(fileId)`（既有 impulse-coords 也一并接——前端零引用至今）。
  - `frontend/src/types/` 增对应 TS 接口（与 T1-T3 契约逐字段对齐——C2 类型对齐三先例纪律：TS 接口 ↔ Pydantic 响应逐字对齐）。
  - TDD：api client 单测（mock fetch）覆盖方法/路径/体/响应解析 + 404 双路径错误形态（ApiError 与降级 Error——经验教训）。

  **Must NOT do**: 不引入 axios/新依赖（原生 fetch 封装既有模式）；不动既有 api 函数。
  **Recommended Agent Profile**: **Category**: `quick`；**Skills**: [`test-driven-development`]
  **Parallelization**: 依赖 T1-T3 完成。与 T8-T11 中先完成者解耦（T8-T11 依赖本任务）。**Blocks**: T8, T9, T10, T11。**Blocked By**: T1, T2, T3。
  **References**: frontend/src/api/ 既有文件（fetchJson/fetchWithTimeout 双路径——先读）、frontend/src/types/a1.ts（类型对齐先例 WarningLedgerEntry）、T1-T3 契约（本计划上文响应形状）。
  **Acceptance**:
  - [ ] client 测试全绿；tsc 0 错；类型与后端响应字段逐字对齐（人工核对清单入证据）
  **QA Scenarios**:
  ```
  Scenario: 真实端点联通
    Tool: Bash（起后端 + node 脚本或 vitest integration）
    Steps: 依次调用五个 client → 断言各自 200/404 形态
    Evidence: .sisyphus/evidence/task-7-api-clients.txt
  ```
  **Commit**: YES `feat(a1-ui): api clients for D21 endpoints`

- [x] 8. 罗盘独立组件

  **What to do**:
  - 新建 `frontend/src/components/guided/ImpulseCompass.tsx`：一句话坐标「目前感觉你更像：讲故事的 70%」（axis 数值 → 百分比/倾向文案的纯函数 `compassPhrase(axis)` 抽出可测；阈值语义读 impulse spec §10.1 轴定义后定：叙事-建构轴两端映射「讲故事的/建设定的」，>70% 显示主导侧+百分数）+ 三值纠偏按钮（**按钮不是滑块**——ux-flow §5.3 逐字：更像讲故事 / 差不多 / 更像建设定）。
  - 点击 → `nudgeCoords(fileId, signal)` → 以响应 `{applied, axis, confidence}` 更新显示（applied=false 阻尼时坐标不动——诚实透传，无错误弹窗）。
  - `safety_flag=true` → 三按钮禁用 + 灰显提示「当前以你的感受为准」（不显示安全术语）。
  - 挂载：A1Workspace 右栏（T4 完成后进场）——访谈态常驻、全员显示；挂载时 GET 一次 + 每次 chat 响应后可轻量刷新（复用父级既有 fetch 时序，不加轮询）。
  - TDD：`ImpulseCompass.test.tsx`：①axis=0.7 → 文案含「讲故事的 70%」式断言；②三按钮各点击 → 断言请求 signal 枚举逐字（user_nudge_story/user_nudge_confirm/user_nudge_builder）；③safety_flag=true → 按钮 disabled；④applied=false 响应 → 显示值不变。

  **Must NOT do**: 不做滑块/连续值输入；无历史记录趋势图；不做坐标变化的动画提示（D21⑩ 静默——显示归显示，不弹提示）；不挂 /persona-card（不存在）。
  **Recommended Agent Profile**: **Category**: `visual-engineering`；**Skills**: [`test-driven-development`, `frontend-ui-ux`]
  **Parallelization**: 依赖 T4+T7。与 T9-T11 并行。**Blocks**: 无。**Blocked By**: T4, T7。
  **References**: A1Workspace.tsx:1284-1341（右栏挂点——T4 后行号或有偏移，按结构定位）、impulse_coords.py dashboard 字段（axis 0-1 语义）、impulse spec §10.1（轴定义——docs/plans/2026-09-18-impulse-entry-system-spec-v1.3* 最新 amendment）、GuidedChat.tsx 组件 props 风格。
  **Acceptance**:
  - [ ] 组件测试 4 例全绿；vitest 全绿 + tsc 0 错
  **QA Scenarios**:
  ```
  Scenario: 罗盘渲染+纠偏全流程
    Tool: Playwright（/a1 访谈态）
    Steps: 断言右栏含「目前感觉你更像」文案 → 点击「更像讲故事」→ 等响应 → 断言坐标文案变化或保持（依 applied）
    Evidence: .sisyphus/evidence/task-8-compass.png + network.txt（请求体断言）
  Scenario: 降级——端点不可达
    Steps: 停后端点纠偏 → 断言组件不崩溃、显示原值
    Evidence: .sisyphus/evidence/task-8-compass-degraded.png
  ```
  **Commit**: YES `feat(a1-ui): impulse compass component (D21-12)`

- [x] 9. 收尾三连问面板

  **What to do**:
  - 新建 `frontend/src/components/guided/ClosingPanel.tsx`：数据 = `getClosingState(fileId)`；`triggered=true` 时在 footer 区（A1Workspace.tsx:1344-1375，T4 后进场）渲染面板：
    - ⓪ 预览区：preview 可生成物清单只读展示（人话名——按 build_output_preview 输出的名称字段直显，无下载按钮）；
    - ①-③ 三问：问题文案**不用后端 QUESTIONS 文本硬拷**——优先从 chat 响应文本流呈现（后端 interject 已把说人话问句追加到 reply）；面板提供三个显式动作入口：「生成文档」（→ 触发既有 finalize 流）/「继续访谈录入设定」（→ 关闭面板继续 chat）/「改天继续」（→ 显示「好的，进度都保存在这个会话里，随时回来」提示——**不建新会话、无新入口**）。
    - 用户回答也可走正常聊天输入（后端 closing_flow 解析自然语言）——面板与聊天输入二途并存，不互斥。
  - 刷新恢复：挂载时若 closing-state triggered → 直接渲染面板（closing_step 持久化保证）。
  - TDD：`ClosingPanel.test.tsx`：①triggered=false → 不渲染；②triggered=true → 含 preview 项与三动作；③点「生成文档」→ 调用 onFinalize 回调（props 注入，A1Workspace 接既有 finalize 逻辑）；④点「改天继续」→ 提示文案断言 + 无路由跳转。

  **Must NOT do**: 不新建「新会话」按钮/路由；预览无下载/导出；不改后端 closing 状态机；不在面板里报模块名（preview 项名称若含模块名 → 显示前过 plainQuestion 同款纯函数兜底）。
  **Recommended Agent Profile**: **Category**: `visual-engineering`；**Skills**: [`test-driven-development`, `frontend-ui-ux`]
  **Parallelization**: 依赖 T4+T7。与 T8/T10/T11 并行。**Blocks**: 无。**Blocked By**: T4, T7（T1 传递）。
  **References**: A1Workspace.tsx:1344-1375（footer 挂点）、closing_flow.py（QUESTIONS 文本/状态语义——只读参考）、closing_gate.py:182（preview 形状——读实函数定字段）、4_ux-flow-v0.3 §2 收尾阶段图（交互权威）。
  **Acceptance**:
  - [ ] 组件测试 4 例全绿；vitest 全绿 + tsc 0 错
  **QA Scenarios**:
  ```
  Scenario: 收尾触发全流程（构造路径）
    Tool: Playwright + 测试夹具（后端测试内将会话推至 closing_step>0——用 pytest fixture 写入状态后起服务，或 vitest mock getClosingState）
    Steps: 访谈态刷新 → 面板出现 → 断言预览区与三按钮 → 点「继续访谈录入设定」→ 面板消失、聊天可输入
    Evidence: .sisyphus/evidence/task-9-closing-panel.png
  Scenario: 未触发不渲染
    Steps: 正常访谈中段 → 断言 footer 无面板元素（data-testid=closing-panel 不存在）
    Evidence: .sisyphus/evidence/task-9-closing-hidden.png
  ```
  **Commit**: YES `feat(a1-ui): closing triple-question panel (D21-08)`

- [x] 10. 对齐推测卡

  **What to do**:
  - 新建 `frontend/src/components/guided/AlignmentCard.tsx`（消息流内卡片，DiceRecommendationCard 先例 GuidedChat.tsx:51-79）：props = `{item: {key, action, content, quote, stale_warning}, onResolve(key, accept)}`。
  - 渲染：动作徽标（关联/去重/矛盾/更新——四标签逐字，闭集）+ content 人话转述 + quote 原话引用（引号样式）+ stale_warning 若有则琥珀色预警行（「将使 … 过期」型原文直显）+ 两动作按钮：**采纳 / 不是这样**（accept=true/false）。
  - GuidedChat 接线：chat 响应 `pending_alignments` 非空 → 渲染卡片列表（数组）；resolve 后从列表移除——`{applied:false, error:"not_found"}` 响应同样移除 + 行内提示「这条已经处理过了」（幂等路径，无报错弹窗）。
  - TDD：`AlignmentCard.test.tsx`：①四动作各渲染对应徽标；②content 不含 `module.subfield` 内部键形态（正则 `/[a-z_]+\.[a-z_]+/`）与不含节点 id（`term:`/`:` 前缀形态）；③点采纳 → onResolve(key, true)；④stale_warning 渲染琥珀行。集成测试（GuidedChat 级）：pending_alignments 数组渲染 N 卡；resolve 后移除。

  **Must NOT do**: 四动作枚举/文案不增不改（闭集）；无批量 accept/reject；卡内无「查看图谱」跳转（YAGNI——后续迭代再说）；quote 为空时不渲染空引号。
  **Recommended Agent Profile**: **Category**: `visual-engineering`；**Skills**: [`test-driven-development`, `frontend-ui-ux`]
  **Parallelization**: 依赖 T7（T2 传递）。与 T8/T9/T11 并行。**Blocks**: 无。**Blocked By**: T7。
  **References**: GuidedChat.tsx:51-79（DiceRecommendationCard 消息流卡片先例——渲染挂点与 props 风格）、alignment_flow.py:40-77（序列化字段——T2 已定只含 key/action/content/quote/stale_warning）、ProposalCard.tsx（双盒对照先例——对齐卡更简，无需原设定对照）、4_ux-flow-v0.3 Flow 0 step 6（交互权威：四动作+三值判定——**注：后端 resolve 是 accept 布尔二值，「接近」三值判定已由 D21 后端收敛为确认/拒绝两途，前端跟随端点，勿自造第三按钮**）。
  **Acceptance**:
  - [ ] 组件+集成测试全绿；vitest 全绿 + tsc 0 错
  **QA Scenarios**:
  ```
  Scenario: 对齐卡渲染与裁决
    Tool: vitest（mock chat 响应含 pending_alignments 两条）+ Playwright 真渲染截图
    Steps: 断言两卡各含动作徽标与人话 content → 点「不是这样」→ 断言 resolve 请求体 {accept:false} → 卡移除
    Evidence: .sisyphus/evidence/task-10-alignment-card.png + vitest.txt
  Scenario: 过期幂等
    Steps: mock resolve 返回 not_found → 断言卡移除 + 「已经处理过了」提示出现
    Evidence: .sisyphus/evidence/task-10-alignment-stale.txt
  ```
  **Commit**: YES `feat(a1-ui): alignment proposal card (D21-13)`

- [x] 11. α 版本标记

  **What to do**:
  - `IPPoster.tsx`：顶部新增版本徽标行——挂载时 `getDraftVersion(fileId)`：`available=true` → 显示 `α 草稿 v{version}`（version 串直显）；`available=false` 且文件 status=draft → 显示「草稿」二字徽标（无假数字）；finalized 状态 → 显示「已定稿」（版本数字走既有 -vN 解析路径若可得）。
  - `A1GraphSection.tsx`：既有「已定稿 vX ✓」徽标旁，草稿/重定稿途中的 stale 状态下补「α」前缀标记（最小改动——stale 黄条文案追加「（当前为 α 草稿期）」或徽标前缀，取视觉最小方案）。
  - 纯函数 `draftBadge(state, version)` 抽出可测。
  - TDD：`IPPoster.test.tsx`/徽标纯函数测试：①available+version → 「α 草稿 vα0.1」式断言；②draft 无版本 → 仅「草稿」；③finalized → 「已定稿」；④图谱 stale → 含 α 标记。

  **Must NOT do**: 无版本 diff 视图；不改后端 draft_version 域；不在访谈页显示版本（只输出物：展板/图谱）。
  **Recommended Agent Profile**: **Category**: `quick`；**Skills**: [`test-driven-development`]
  **Parallelization**: 依赖 T7。与 T8-T10 并行。**Blocks**: 无。**Blocked By**: T7（T3 传递）。
  **References**: IPPoster.tsx（页首结构——读后定插入点）、A1GraphSection.tsx:492-494/663-671（既有徽标先例——样式复用）、draft-version 端点契约（T3）。
  **Acceptance**:
  - [ ] 测试先红后绿；vitest 全绿 + tsc 0 错
  **QA Scenarios**:
  ```
  Scenario: 展板 α 徽标
    Tool: Playwright（/a1/poster?fileId=…——构造 draft 会话）
    Steps: 断言徽标文本匹配 /α 草稿|草稿|已定稿/ 三态之一且与后端状态一致
    Evidence: .sisyphus/evidence/task-11-alpha-badge.png
  Scenario: 降级——draft-version 端点失败
    Steps: mock 网络错误 → 徽标显示「草稿」不崩溃
    Evidence: .sisyphus/evidence/task-11-alpha-degraded.png
  ```
  **Commit**: YES `feat(a1-ui): alpha version badges on outputs (D21-13)`

---

## Final Verification Wave（全部任务完成后）

- [x] F1. **计划合规审计** — `oracle`：逐条 Must Have/Must NOT Have 核验（读文件/curl/跑命令）；证据文件存在性检查。输出 `Must Have [N/N] | Must NOT Have [N/N] | VERDICT`
- [x] F2. **代码质量审查** — `unspecified-high`：`tsc --noEmit` + `npx vitest run` + `pytest 全量`（≥1502+新增全绿，cov ≥80%）；AI slop 检查（as any/空 catch/console.log 残留/无用 import）。输出 `Build | Lint | Tests | VERDICT`
- [x] F3. **真实 QA** — `unspecified-high`（+playwright skill）：起前后端服务，跑全部 QA 场景（含跨组件集成：访谈到收尾到产物全链路）。证据存 `.sisyphus/evidence/final-qa/`。输出 `Scenarios [N/N] | VERDICT`
- [x] F4. **范围保真检查** — `deep`：逐任务比对 What to do vs git diff；检查 8.3 四不做零违反；跨任务文件污染检查。输出 `Tasks [N/N] | VERDICT`

> F1-F4 全 APPROVE 后呈交用户，**等用户明确 okay 才标记完成**。

---

## 提交策略

| 波次 | 提交 | 消息 |
|---|---|---|
| T1-T3 | 每任务一提交 | `feat(a1): expose closing/alignment/coords HTTP surface (D21 frontend prep)` |
| T4-T6 | 每任务一提交 | `refactor(a1-ui): plain-language interview copy (D21-11)` |
| T7 | 一提交 | `feat(a1-ui): api clients for D21 endpoints` |
| T8-T11 | 每任务一提交 | `feat(a1-ui): compass/closing-panel/alignment-card/alpha-badge (D21)` |
| FINAL | 审后一提交 | `docs(state): D21 frontend phase complete` |

---

## 成功标准

- [x] vitest 全绿 + tsc 0 错；pytest 全量全绿且 ≥1502 基线、cov ≥80%（F2 实测：vitest 300 passed / pytest 1556 / cov 84.20%；tsc 零新增，基线 20 条均为本阶段前存量）
- [x] 整改三组件零内部模块名泄漏（反向断言过）；StructuredFilePanel 模块名原样保留（F1 §7 零提交 + F3 S7/S8 实测）
- [x] 四组件按 ux-flow v0.3 §5 铁则工作（罗盘三值无滑块/收尾双条件/对齐四动作×确认拒绝/α 可见于输出物）（F3 13/13 场景实测）
- [x] 8.3 四不做零违反（F4 grep 累计 diff 零命中 + 受保护文件零提交）
- [x] PROJECT_STATE.md 更新（会话结束前）
