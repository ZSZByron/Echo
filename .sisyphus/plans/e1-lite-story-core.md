# E1-Lite 故事核心三件套实施计划

## TL;DR

> **Quick Summary**: E0 冲动卡层已上线（9 提交 fd6f687..bc86fb5），但冲动类型止步于前端——后端访谈对类型完全无感（R1 空窗命门）。E1-Lite 把类型结构化送达后端并兑现三件最小可感差异：①`A1Session` 加 `creator_profile` 字段组（仿 `seed_*` 三字段模式，spec §11.1-①）+ `StartRequest` 可选 impulse 字段；②`sync_position` 类型驱动前移式重排（spec §11.1-⑥ + §5.2 各型"模块优先序"列逐字；**只前移不跳过**，R6 保守模式；`MODULES` 列表与 `test_module_ids_match_spec` 零触碰）；③`_seed_block` 语气锚点模板变量注入（spec §11.1-②，一份 prompt 防 R2 prompt 爆炸）。前端小改：冲动卡确认时 primary/secondary 类型 ID 随 `session/start` 结构化上送（扩展请求体，非新端点）。**门禁语义零变化**（`FINALIZE_MODULE_THRESHOLD` 不动）。
>
> **Deliverables**:
> - 后端：`A1Session` 三新字段 + `StartRequest.impulse_primary/impulse_secondary` + start_session 结构化写入（9 型枚举白名单校验）
> - 后端：类型优先序映射 + `sync_position` 前移式重排（故事 5 型 main_plot/文明先行；无 profile 会话原序零变化）
> - 后端：`_seed_block` 锚点变量注入（9 型锚点文案逐字取自 spec §5.2"语气锚点"列）
> - 前端：冲动卡确认路径结构化上送 impulse ID（含设定侧 2 型分组种子页点击路径的上下文保持）
> - 前端：telemetry `attachSessionId` 既有事件回填（不新增事件名/指标）
> - 契约测试扩展（session/start impulse 面）+ 全量验证收尾
>
> **Estimated Effort**: Medium（后端三件相互耦合但文件可分；前端小改；按 spec §10 E1 子集）
> **Parallel Execution**: YES - 4 波（Wave 1 落库先行 → Wave 2 四件并行 → Wave 3 收尾验证 → FINAL 四审）
> **Critical Path**: T1(落库) → T2(队列) → T6(收尾) → F1-F4

---

## Context

### Original Request
用户指令（2026-09-21）：生成 E1-Lite「故事核心」三件套正式工作计划。E1-Lite 是 spec v1.2 §10 E1 全量范围的**产品方已裁决子集**（三件 IN / 全部 OUT 见 Work Objectives）——推断包、character_sketch、field_sources、看门狗等明确排除出 Lite。

### Interview Summary
**Key Discussions**（均为产品方已裁决，逐字遵守）：
- 故事侧 5 型直达访谈已在 **E0.1 落地**（commit bc86fb5：plot/romance/philosophy/unsure/character_driven 确认后以主冲动 tagline 走 custom_idea 通道直达访谈 + entryNotice 横幅）
- **B1 基线顺延至 ~10 月初**（顺序 = E1-Lite → A2 P0 → B1 验收；产品方 2026-09-20 口头裁决，台账改写归产品方）
- **推断包明确排除出 Lite**（E1 全量项，Lite 只做三件套）
- E0 的"零后端约束"在 E1-Lite **解除**，但 A1 契约面任何改动必须契约测试同步扩展
- 埋点衔接：E0 telemetry 的 `impulse_card_selected` 已含 primary/secondary——creator_profile 落库后仅补 session_id 关联（轻量，不扩指标）

**Research Findings**（全部实读取证，file:line 已核对）:
- `A1Session` 定义在 `guide_engine.py:60-101`（**不在 store.py**——store.py 只是 JSON 持久层，`model_dump` 全量透传 :130-136，新字段默认值即自动落盘，store.py 零改动）；`seed_*` 三字段模式在 :72-74
- `sync_position` 在 `guide_engine.py:138-162`：两段式（①门禁未达 50% 模块优先遍历 :146-154 → ②全局首个未答 fallback :156-161 → 完毕置 COMPLETED :162）；被 start_session（a1_routes.py:644）与每轮 chat（guide_engine.py:441/523/554/599）调用
- `MODULES` 列表在 `backend/app/domains/creation/seed/a1_question_tree.py:32`，模块 id 为中文字符串（IP定位/世界本体/力量体系/地理空间/文明与社会/历史时间线/视觉设计/玩法设计DNA/骰子设定/设定边界），锁序测试 `backend/tests/unit/a1/test_question_tree.py:28` `test_module_ids_match_spec`；关键子字段 id：`main_plot`（历史时间线，:209，问题原文"当前时间段里世界正在发生什么？"——即"你的世界里正在发生什么事"级故事问题）、`reality_rule`（世界本体 :86）、`core_value`/`conflict`（文明 :160/:167）、`cost`（力量 :120）
- `StartRequest` 在 `a1_routes.py:175-178`（user_id/seed_id/custom_idea）；`start_session` 在 :617-682：custom_idea 前 500 字进 `seed_description`（:642）、`sync_position` 后返回 `first_question`（:671）、`log_event("session_start", ...)` 留痕（:657-665）
- `_seed_block` 在 `interviewer.py:305-315`（@staticmethod，getattr 容错），`_build_prompt` 在 :317+ 以"【种子起点】"块注入（:326-327）；同函数还被 suggestion prompt 复用（:449/:495-503）
- 契约测试 C1-C5 在 `backend/tests/unit/a1/test_contracts/`（c1_answers_smoke/c2_sir_schema/c3_dualtree_invariants/c4_vocab_closed/c5_tier_map）
- 前端：`WorkspaceState` 含 `impulse_cards`（A1Workspace.tsx:266）；`STORY_SIDE_TYPES`（:281）；`startSession(seedId?, customIdeaText?)`（:528-574，请求体 :534-538）；`handleImpulseCommit`（:577-599：nostalgia→聚焦上传 / healing→startSession('7') / 故事侧 5 型→custom_idea 直达 / 设定侧 2 型→分组种子页）；`first_question_answered` 埋点（:670）；impulse 层五文件已存在（ImpulseCards/impulseCards.config/telemetry/seedGrouping/NostalgiaConfirmPage）
- E0 收官经验（learnings.md）：E2E 全 A1 端点 page.route mock（seeds/session-start/chat/upload/file hydration）；**file 水合 mock 坑**（不 mock /api/a1/file/** 则 404 破坏测试）；证据归 .sisyphus/evidence（已 gitignore，过程留档不提交）；契约测试同步义务

### Metis Review
> ⚠️ **降级声明**：Metis 代理经 3 次同步调用超时 + 2 次后台启动失败（工具故障），本节以**主会话内化缺口自审**替代，全部缺口转交 Momus 终审复核。

**Identified Gaps**（自审，已全部处置）:
- **G1 口径冲突（产品 prompt vs 规格表）**：产品方口头口径"剧情/爱情/哲理/说不清/角色驱动 → main_plot 前置"与 spec §5.2 逐型列表冲突（哲理行=reality_rule 先、爱情行=IP定位 先）。**处置：以 §5.2 各型"模块优先序"列逐字为准**（MUST DO 明文要求"逐字"，§5.2 为队列与锚点权威；口头口径是对剧情/说不清行 + 角色驱动"历史主线"行的概括）。标记 **DECISION NEEDED 1** 交产品方确认。
- **G2 角色驱动第 0 模块缺位**：§5.2 角色驱动行首元素"第 0 模块"= character_sketch（Lite 明确 OUT）。**处置：取该行去掉第 0 模块后的逐字剩余序**（文明冲突 → 历史主线 → 世界本体 → 力量）。标记 **DECISION NEEDED 2**。
- **G3 未知 impulse 枚举值语义**：**处置：忽略降级默认序，不 400**——前端是唯一发送方且 9 型枚举逐字锁定；400 会在前后端版本漂移时把新用户完全堵在开局（违 D2-③"AI/问卷永不阻塞主路径"精神）。主冲动未知 → creator_profile 不落、原序；次冲动未知 → 置空；均留 interaction log warning。标记 **DECISION NEEDED 3**（若产品方坚持严格校验，改为 400，改动一处）。
- **G4 门禁逻辑与类型序的复合（R6 可达性）**：`sync_position` 第一段"门禁未达模块优先"是可达性保障核心。**处置：类型序只替换遍历的外层顺序**——①门禁段在"类型序 module 列表"上遍历（is_module_over_half 检查原样保留）、②fallback 段在"类型序全字段键列表"上遍历。数学保证：重排 = 置换，全部字段仍被遍历（前移不跳过），偏科 = 顺序靠后但必达（§12.1.6 保守模式原文）；门禁语义零变化（is_module_over_half / FINALIZE_MODULE_THRESHOLD 未触碰）。
- **G5 T2/T3 同文件冲突**：T2（guide_engine 优先序映射+sync_position）与 T3（interviewer 锚点表+_seed_block）落**不同文件**，锚点表定义在 interviewer.py（T3 独占），guide_engine 仅由 T2 独占，可并行。
- **G6 T4/T5 同文件冲突**：telemetry.ts 的 `attachSessionId`（T5 独占 telemetry.ts + 单测）与 A1Workspace wiring（T4 独占）分离；wiring 里调用 attachSessionId 的一行归 **T4**（接口在计划内逐字锁定）。
- **G7 设定侧 2 型上下文丢失**：设定-重度/探索确认后进分组种子页，用户稍后点种子 → startSession(seedId)，此时 impulse 上下文会丢。**处置：commit 时存 `pendingImpulseRef`，所有开 session 的路径（种子直选/分组种子/custom_idea 直达/healing 直达）统一附带，session start 成功后清除**。
- **G8 存量会话/存量测试回归**：三新字段默认空串（旧持久化 JSON 可 `model_validate` 反序列化，对齐 prefill_fields 先例 guide_engine.py:95-101）；`_seed_block` 空锚点时输出与现状**逐字节相同**（不注入锚点行）；`sync_position` 空 profile 时遍历序 = `module_ids()` 原序 → 存量会话零行为变化。
- **G9 E2E mock 兼容**：session/start 请求体新增可选字段、**响应结构零新增**——既有 page.route mock 天然兼容；T6 仅核查不重写。

---

## Work Objectives

### Core Objective
按产品方裁决的 E1-Lite 子集交付三件套（creator_profile 落库 / 类型驱动队列 / 语气锚点），使冲动类型在 90 秒内产生后端可感的差异（队列序 + 语气），同时保持门禁语义、MODULES 锁序、1020+ pytest 基线、契约 C1-C5 存活、vitest 223 基线全部不动摇。

### Concrete Deliverables
- 修改：`backend/app/domains/creation/a1/guide_engine.py`（A1Session 三字段 + 类型优先序映射 + sync_position 重排）——T1 改字段区、T2 改队列区
- 修改：`backend/app/api/a1_routes.py`（StartRequest 两字段 + start_session 写入 + log_event 留痕）——仅 T1 触碰
- 修改：`backend/app/domains/creation/a1/interviewer.py`（锚点表 + _seed_block 注入）——仅 T3 触碰
- 修改：`frontend/src/pages/a1/A1Workspace.tsx`（startSession 签名扩展 + pendingImpulseRef + 三处调用点 + attachSessionId 一行）——仅 T4 触碰，diff <80 行
- 修改：`frontend/src/pages/a1/impulse/telemetry.ts`（attachSessionId 导出）——仅 T5 触碰
- 新增：后端测试 `backend/tests/unit/a1/`（creator_profile 落库/枚举降级、队列前移+R6 可达、锚点注入）；前端单测 telemetry 回填
- 既有测试零删除；契约 C1-C5 原样存活

### Definition of Done
- [ ] `cd backend && pytest` → 1020+ 全绿（含新增用例，0 failed）
- [ ] `cd frontend && npx tsc --noEmit` → 0 errors
- [ ] `cd frontend && npx vitest run` → 223+ 全绿（0 failed，0 新增 skip）
- [ ] 契约测试 C1-C5 存活（文件清单与用例数与基线一致）
- [ ] `git diff` 核查：`a1_question_tree.py` MODULES 区零改动（`test_module_ids_match_spec` 未触碰即铁证）+ FINALIZE_MODULE_THRESHOLD 未出现于 diff
- [ ] 无 profile 会话（healing 直达除外其 profile=healing；skip/nostalgia 链）队列序与锚点输出与 E0 现状逐字节一致（回归用例证明）
- [ ] 9 型锚点文案与 spec §5.2"语气锚点"列逐字一致

### Must Have
- `A1Session` 新字段组（**命名逐字锁定**）：`creator_primary: str = ""` / `creator_secondary: str = ""` / `creator_profile_source: str = ""`（取值仅 `"impulse_cards"`，预留扩展；空 = 无 profile）
- `StartRequest` 新字段（**命名逐字锁定**）：`impulse_primary: str | None = None` / `impulse_secondary: str | None = None`
- 9 型枚举白名单（**逐字锁定，不允许增删改写**）：`setting_heavy` / `character_driven` / `plot` / `philosophy` / `exploration` / `romance` / `nostalgia` / `healing` / `unsure`
- 类型优先序映射（**模块 id 用问卷树中文字符串逐字**，元素为模块 id；前移 = 置换，不增删模块）：
  - `plot`：历史时间线 → 文明与社会 → 世界本体 → 其余原序
  - `unsure`：历史时间线 → 文明与社会 → 世界本体 → 其余原序（§5.2 通用线行"同剧情行骨架"）
  - `philosophy`：世界本体 → 文明与社会 → 力量体系 → 历史时间线 → 其余原序（§5.2 哲理行四元素逐字）
  - `romance`：IP定位 → 历史时间线 → 视觉设计 → 其余原序（§5.2 爱情行去掉 E2 第 0 模块，DECISION NEEDED 2）
  - `character_driven`：文明与社会 → 历史时间线 → 世界本体 → 力量体系 → 其余原序（§5.2 角色驱动行去掉 E2 第 0 模块）
  - `setting_heavy`：视觉设计 → 其余原序（§5.2"默认序，视觉设计提前"）
  - `exploration`：玩法设计DNA → 骰子设定 → 力量体系 → 世界本体 → 其余原序（§5.2 探索行四元素逐字）
  - `nostalgia` / `healing` / 无 profile：**原序**（怀旧=上传优先差额访谈无型化队列；疗愈=最少问话不重排——§5.2 两行均未定义前移序）
- **入口子字段前置**（模块级前置的自然结果修正——否则 plot 首问会是 `time_span` 而非故事问题）：`TYPE_ENTRY_SUBFIELD: dict[str, tuple[str, str]]`——`plot`/`unsure` → `("历史时间线", "main_plot")`：该型队列首模块内的子字段序做**一次置换**（main_plot 提到模块内首位，其余子字段保持原序跟随）。仅此两型、仅此一子字段；置换完备性不变（R6 可达）。philosophy/character_driven/romance 的首问依 §5.2 各自首模块的首个子字段自然产生（origin/conflict/name），**不额外前置**——与"5 故事型都 main_plot 首问"口头口径的差异由 DECISION NEEDED 1 裁决
- 语气锚点映射 `ANCHOR_BY_TYPE`（**文案逐字取自 spec §5.2"语气锚点"列**，经 `_seed_block` 注入"【种子起点】"块内新行）：
  - `plot`：`节奏导向："这个设定会制造什么事件？"`
  - `unsure`：`中性引导"先聊聊你世界里发生的事。"`
  - `philosophy`：`追问"如果这条规则被违反会怎样"`
  - `romance`：`情感张力导向；保持极轻量与合规边界。`
  - `character_driven`：`一切围绕"这如何影响 TA 的命运"`
  - `setting_heavy`：`机制自洽："这里的力量为什么成立？"`
  - `exploration`：`能力边界展示："AI 可以替你试三种方案。"`
  - `nostalgia`：`风格保真："我在保护原作的味道。"`
  - `healing`：`陪伴低压力："不想答的都可以跳过，我会替你补上。"`
- 首问效果：`plot`/`unsure` 新会话首问 = 历史时间线.main_plot（问题原文"当前时间段里世界正在发生什么？"）——由队列前置 + 入口子字段前置自然达成，不写特判
- R6 保守模式：只前移不跳过（重排=置换）；门禁未达模块优先逻辑原样保留（在类型序上执行）
- 前端：所有开 session 路径结构化上送 impulse（healing 直达 / 故事 5 型 custom_idea 直达 / 设定 2 型分组种子页点击）；次冲动为空 → 请求体**不含** `impulse_secondary` 键（缺省语义 = 后端置空串）；skip / nostalgia 路径不上送（无 profile，默认序）
- 埋点衔接：session start 成功后 `attachSessionId(session_id)` 回填 localStorage 既有事件缺失的 session_id（不新增事件名、不改 schema_version）
- log_event("session_start") 增补 `impulse_primary`/`impulse_secondary` 留痕（interaction log 观测面）

### Must NOT Have (Guardrails)
- ❌ 推断包端点 / Q2 追问 / 公理卡 / 骰子三方案 / character_sketch / field_sources / onboarding_quiz 正式分态 / 看门狗 / 开场叙事端点（全部 E1 全量或 E2）
- ❌ 冲动坐标任何计算/聚合/落库（§10.1 是 E2；Lite 只存前端已选的原始类型 ID）
- ❌ 新 LLM 生产方 / 新端点 / 新 LLM 调用（Lite 全部确定性代码；锚点是模板变量不是 prompt 变体——prompt 变体数必须恒为 1，R2 红线）
- ❌ 门禁语义变化：`FINALIZE_MODULE_THRESHOLD` / `is_module_over_half` / 409 missing_sections 契约零触碰
- ❌ `a1_question_tree.py` 任何改动（MODULES 列表/子字段/question 文案零触碰；`test_module_ids_match_spec` 零改动）
- ❌ 任何 A2 域文件；❌ 新建 `creator_profile.py`（枚举白名单内联在消费侧，独立枚举模块属 E1 全量 §11.1-③）
- ❌ 子字段级重排**超出入口子字段机制之外**（Lite 只允许 `TYPE_ENTRY_SUBFIELD` 定义的单置换——plot/unsure 的 main_plot；其余任何字段跳位禁止）
- ❌ 删除/跳过任何既有测试；❌ 为绿灯引入 `@ts-ignore`/`as any`/`pytest.mark.skip`
- ❌ 前端 A1Workspace 重构/重排既有代码（wiring diff <80 行）；❌ 遥测新增事件名/网络上报

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed.
> 计划外人工步骤：仅 DECISION NEEDED 1/2/3 的产品方确认（均有安全默认值，不阻塞执行——默认值已内置于各任务）。

### Test Decision
- **Infrastructure exists**: YES（pytest 1020+ 基线 / vitest 223 基线 / tsc）
- **Automated tests**: Tests-after（后端为确定性纯函数与数据流改造，既有极限病理/契约测试网密集；新增行为用针对性 pytest + 前端 vitest 锁定）
- **Framework**: pytest（后端）/ vitest + tsc（前端）

### QA Policy
- 每任务附 agent 执行的 QA 场景（happy + failure 双路径），证据存 `.sisyphus/evidence/task-{N}-{slug}.{ext}`（已 gitignore，过程留档不提交）
- **后端**: pytest 单测 + 全量回归；**前端**: vitest + tsc；**集成**: T6 全量三命令 + E2E mock 核查
- 每 Wave 末跑全量命令（T1 后：pytest；T4/T5 后：tsc+vitest；T6：全部）

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1（后端落库，串行先行——队列与锚点的数据源）:
└── T1: A1Session creator_profile 字段组 + StartRequest impulse 字段 + start_session 写入 [deep]

Wave 2（四件并行，文件所有权互斥）:
├── T2: sync_position 类型驱动前移式重排（guide_engine 队列区） [deep]
├── T3: _seed_block 语气锚点注入（interviewer.py 独占） [quick]
├── T4: 前端 impulse 结构化上送（A1Workspace.tsx 独占） [deep]
└── T5: telemetry attachSessionId + 单测（telemetry.ts 独占） [quick]

Wave 3（收尾验证，串行）:
└── T6: 全量验证 + 契约测试审计 + E2E mock 核查 [unspecified-high]

Wave FINAL（四审并行 → 用户终审）:
├── F1: 计划合规审计 [oracle]
├── F2: 代码质量审查 [unspecified-high]
├── F3: 真实手动 QA（pytest/vitest/关键场景重放） [unspecified-high]
└── F4: 范围忠实检查 [deep]
→ 呈交结果 → 用户明确 okay 后才算完成

Critical Path: T1 → T2 → T6 → F1-F4 → user okay
Max Concurrent: 4（Wave 2）
```

### Dependency Matrix

| 任务 | 依赖 | 被依赖（下游） |
|---|---|---|
| T1 | — | T2, T3, T4, T6, F1-F4 |
| T2 | T1 | T6 |
| T3 | T1 | T6 |
| T4 | T1（契约已在计划内锁定，实现层依赖 T1 联调） | T6 |
| T5 | —（接口锁定，与 T4 wiring 汇合于 T4） | T6 |
| T6 | T1-T5 | F1-F4 |
| F1-F4 | T6（及全部） | user okay |

### Agent Dispatch Summary

- **Wave 1**: 1 —— T1 → `deep`
- **Wave 2**: 4 —— T2 → `deep`，T3 → `quick`，T4 → `deep`，T5 → `quick`
- **Wave 3**: 1 —— T6 → `unspecified-high`
- **FINAL**: 4 —— F1 → `oracle`，F2 → `unspecified-high`，F3 → `unspecified-high`，F4 → `deep`

---

## TODOs

- [x] 1. creator_profile 落库：A1Session 字段组 + StartRequest 扩展 + start_session 写入

  **What to do**:
  - `backend/app/domains/creation/a1/guide_engine.py`：`A1Session`（:60-101）在 `seed_*` 三字段（:72-74）之后追加字段组（**命名与默认值逐字锁定**）：
    ```python
    # E1-Lite 冲动类型档案（仿 seed_* 三字段模式，spec §11.1-①）。
    # 空串 = 无 profile（存量会话/未走冲动卡路径）→ 队列与锚点全部走默认。
    creator_primary: str = ""
    creator_secondary: str = ""
    creator_profile_source: str = ""  # 仅 "impulse_cards"
    ```
  - `backend/app/api/a1_routes.py`：
    - `StartRequest`（:175-178）追加：`impulse_primary: str | None = None` / `impulse_secondary: str | None = None`
    - 模块级常量 `IMPULSE_TYPE_IDS: frozenset[str]`（9 型逐字：`setting_heavy/character_driven/plot/philosophy/exploration/romance/nostalgia/healing/unsure`）
    - `start_session`（:617-682）：`session = A1Session(...)` 之后、`sync_position(session)`（:644）之前写入——`impulse_primary` 非空且在白名单 → `creator_primary = impulse_primary`；`impulse_secondary` 非空且在白名单且 ≠ primary → `creator_secondary`；任一生效 → `creator_profile_source = "impulse_cards"`；**未知值不报错**：主冲动未知 → 三字段全空（降级默认序），次冲动未知 → 置空，各记一条 `logger.warning`（G3 处置）
    - `log_event("session_start", ...)`（:657-665）增补 `impulse_primary=req.impulse_primary, impulse_secondary=req.impulse_secondary` 留痕
  - `store.py` **零改动**（`model_dump` 全量透传 :130-136，新字段自动持久化；先 Read 确认后不触碰）
  - 新增 pytest（建议 `backend/tests/unit/a1/test_creator_profile.py`）：
    - happy：带合法 impulse_primary=plot 开局 → session.creator_primary=="plot"、source=="impulse_cards"、落盘 JSON（A1Store round-trip）含三字段
    - failure/降级：未知主冲动值 → 三字段空 + session 正常创建（HTTP 200）；次冲动==主冲动 → secondary 空；次冲动未知 → secondary 空
    - 回归：无 impulse 字段开局（E0 旧客户端形态）→ 三字段空、响应结构与基线一致
    - 存量反序列化：不含新键的旧 session JSON → `A1Session.model_validate` 成功（默认空串）

  **Must NOT do**:
  - 不得动 `sync_position` / `first_question` / 门禁任何代码（归 T2，且语义不变）
  - 不得 400 拒绝未知枚举（G3 默认裁决：忽略降级）
  - 不得新建 `creator_profile.py` / 任何新文件（枚举内联消费侧）
  - 不得改 session/start 响应结构（新增字段为零）

  **Recommended Agent Profile**:
  - **Category**: `deep`（A1 契约面改动，责任最重）
  - **Skills**: [`test-driven-development`]（先写降级/回归用例再实现最稳）

  **Parallelization**:
  - **Can Run In Parallel**: NO（Wave 1 独占——T2/T3 的数据源，且 guide_engine.py 的字段区由本任务独占）
  - **Blocks**: T2, T3, T4, T6, F1-F4
  - **Blocked By**: None

  **References**:
  - `backend/app/domains/creation/a1/guide_engine.py:60-101`（A1Session 全文——**先逐行读**，注意 :95/:101 prefill_fields 重复声明的既有瑕疵，勿模仿勿修复）+ `:72-74`（seed_* 模式）
  - `backend/app/api/a1_routes.py:175-178`（StartRequest）+ `:617-682`（start_session 全流程）+ `:657-665`（log_event）
  - `backend/app/domains/creation/a1/store.py:117-144`（save/model_dump 透传——零改动证据）
  - spec `docs/plans/2026-09-18-impulse-entry-system-spec.md` §11.1-①（插入点与字段组定义）、§12.1 红线
  - `docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md` 三铁律（NL 不携带机器格式的先例——本任务字段为元数据不入 answers）

  **Acceptance Criteria**:
  - [ ] 三字段存在于 A1Session 且默认空；StartRequest 两可选字段存在
  - [ ] 新 pytest 全过 + `cd backend && pytest` 全绿（1020+ 基线无新增失败）
  - [ ] 未知枚举降级路径有测试覆盖且行为=HTTP 200 + 空字段
  - [ ] store.py / a1_question_tree.py / 门禁代码 diff 为零

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 落库 happy path
    Tool: Bash (pytest)
    Preconditions: T1 改动完成
    Steps:
      1. cd backend; pytest tests/unit/a1/test_creator_profile.py -v --tb=short
    Expected Result: 全部 passed（含 round-trip 落盘断言：A1Store.save→load 后 creator_primary=="plot"）
    Failure Indicators: 任一断言失败；round-trip 丢字段
    Evidence: .sisyphus/evidence/task-1-creator-profile-pytest.txt

  Scenario: 未知枚举降级（failure 路径）
    Tool: pytest
    Steps:
      1. POST /api/a1/session/start body {"user_id":"u1","custom_idea":"x","impulse_primary":"hacker_vibes"}
    Expected Result: 200；session.creator_primary==""；logger.warning 被调用（caplog 断言）；first_question 正常返回
    Failure Indicators: 4xx/5xx；字段被写入非法值
    Evidence: .sisyphus/evidence/task-1-unknown-enum-degrade.txt

  Scenario: 契约面零意外扩散
    Tool: Bash
    Steps:
      1. git diff --stat -- backend/app/domains/creation/seed/a1_question_tree.py backend/app/domains/creation/a1/store.py
      2. git diff -- backend/app | Select-String "FINALIZE_MODULE_THRESHOLD|is_module_over_half"
    Expected Result: 步骤1 输出为空；步骤2 零命中
    Failure Indicators: 任一文件出现在 diff；门禁符号被触碰
    Evidence: .sisyphus/evidence/task-1-no-spread.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): creator_profile field group on A1Session + structured impulse fields on StartRequest`
  - Pre-commit: `cd backend && pytest`

- [x] 2. 类型驱动队列：sync_position 前移式重排（只前移不跳过）

  **What to do**:
  - `backend/app/domains/creation/a1/guide_engine.py`（本任务独占该文件队列区；字段区改动归 T1，冲突时以 git 合并纪律处理——**Wave 2 与 T3/T4/T5 并行安全，T1 已合入**）：
    - 模块级常量 `TYPE_MODULE_PRIORITY: dict[str, list[str]]`——键 = 9 型 id（逐字，见 Must Have），值 = 该型**前置模块 id 有序列表**（中文字符串逐字取自问卷树模块 id）：
      ```python
      TYPE_MODULE_PRIORITY: dict[str, list[str]] = {
          "plot":             ["历史时间线", "文明与社会", "世界本体"],
          "unsure":           ["历史时间线", "文明与社会", "世界本体"],
          "philosophy":       ["世界本体", "文明与社会", "力量体系", "历史时间线"],
          "romance":          ["IP定位", "历史时间线", "视觉设计"],
          "character_driven": ["文明与社会", "历史时间线", "世界本体", "力量体系"],
          "setting_heavy":    ["视觉设计"],
          "exploration":      ["玩法设计DNA", "骰子设定", "力量体系", "世界本体"],
          # nostalgia / healing 不入表 → 原序（§5.2 两行未定义前移序）
      }
      # 入口子字段前置（模块内置换，仅 plot/unsure——否则首问是 time_span 非故事问题）
      TYPE_ENTRY_SUBFIELD: dict[str, tuple[str, str]] = {
          "plot":   ("历史时间线", "main_plot"),
          "unsure": ("历史时间线", "main_plot"),
      }
      ```
    - 辅助函数 `_type_ordered_modules(session) -> list[Module]`（或返回 id 序列）：`creator_primary` 在表内 → **前置列表 + 其余按 MODULES 原序去重拼接**；不在表内/空 → `module_ids()` 原序。**纯置换，不增删模块**。
    - `sync_position`（:138-162）重排：①门禁段遍历序从 `module_ids()` 换成 `_type_ordered_modules(session)`（`is_module_over_half` 判断与未答子字段扫描逻辑逐行保留）；②fallback 段在"类型序模块 × 各自原序子字段"的键列表上遍历（`all_subfield_keys()` 的调用改为基于类型序构建，或等价实现——子字段在模块内仍按问卷树原序，**唯一例外**：creator_primary 命中 `TYPE_ENTRY_SUBFIELD` 且遍历到该模块时，入口子字段置换到模块内首位）；③COMPLETED 判定不变。docstring 更新注明 E1-Lite 类型驱动前移（R6 保守模式：只前移不跳过）。
  - 新增 pytest（建议 `backend/tests/unit/a1/test_type_driven_queue.py`）：
    - happy：plot 新会话（无答案）→ `current_module=="历史时间线"` 且 `current_subfield=="main_plot"`（即首问 = "当前时间段里世界正在发生什么？"）
    - 逐型矩阵：8 型（nostalgia/healing 除外）新会话 current_module 逐字断言 = 各型前置模块首元素
    - R6 可达性：plot 会话全模块作答模拟——所有 35 字段键最终全部可答、phase 能达 COMPLETED（置换完备性：`sorted(类型序) == sorted(原序)` 断言 + 遍历到 COMPLETED 的端到端用例）
    - 门禁保持：构造部分答案使门禁未达模块在类型序后段 → 门禁段仍优先命中该模块
    - 回归：无 profile 会话 → current_module/subfield 与重构前计算结果一致（原序行为逐字节等价）
    - 存量：跨 chat 轮次 sync_position 幂等（作答后指针按类型序前进不回跳错乱）

  **Must NOT do**:
  - 不得改 `MODULES` 列表 / 子字段定义 / question 文案 / `all_subfield_keys` / `module_ids` 等问卷树函数（a1_question_tree.py 零 diff）
  - 不得改门禁阈值或 `is_module_over_half` 语义
  - 不得做子字段级重排 / 跳过任何模块 / 引入"访问过即跳过"状态
  - 不得动 interviewer.py（T3 独占）；不得动 start_session（T1 已完成）

  **Recommended Agent Profile**:
  - **Category**: `deep`（确定性路由 + 门禁复合语义 + R6 可达性论证，本计划最重任务）
  - **Skills**: [`test-driven-development`] + [`systematic-debugging`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 2——guide_engine 队列区独占，与 T3 interviewer.py / T4 前端 / T5 telemetry.ts 互斥文件）
  - **Parallel Group**: Wave 2（with T3, T4, T5）
  - **Blocks**: T6
  - **Blocked By**: T1

  **References**:
  - `backend/app/domains/creation/a1/guide_engine.py:138-162`（sync_position 全文逐行读懂再动手）+ `:34-43`（module_ids/first_module 等 import 面）+ `:441/523/554/599`（四个 chat 侧调用点——**签名不变则零触碰**）
  - `backend/app/domains/creation/seed/a1_question_tree.py:32-341`（MODULES 全表——只读！模块 id 中文字符串与子字段序的权威）+ `:343-348`（_MODULE_ORDER/module_ids）
  - `backend/tests/unit/a1/test_question_tree.py:28`（test_module_ids_match_spec——零触碰铁证）
  - spec §5.2 路由映射表"模块优先序"列（**逐字权威**）+ §11.1-⑥（sync_position 接线）+ §12.1.6 R6（"前移模块问完 sync_position 回问卷原序遍历，偏科=顺序靠后但数学上必达"）
  - Metis 自审 G1/G2/G4（口径冲突/第0模块缺位/门禁复合——处置已内置于本任务规格）

  **Acceptance Criteria**:
  - [ ] plot 新会话首问 = 历史时间线.main_plot；逐型矩阵断言全过
  - [ ] 置换完备性断言（sorted 相等）通过——R6 数学证明
  - [ ] 无 profile 会话行为与基线逐字节一致（回归用例绿）
  - [ ] `git diff --stat -- backend/app/domains/creation/seed/` 空；pytest 全绿

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 剧情型首问即故事问题（happy path——本任务灵魂）
    Tool: pytest
    Preconditions: T2 完成；T1 已合入
    Steps:
      1. start_session(custom_idea="赛博朋克都市", impulse_primary="plot")
      2. 断言 first_question.section=="历史时间线" 且 sub_id=="main_plot"
      3. 断言 first_question.question 含 "正在发生"
    Expected Result: 三断言通过
    Failure Indicators: 首问仍是 IP定位.name
    Evidence: .sisyphus/evidence/task-2-plot-first-question.txt

  Scenario: R6 只前移不跳过（failure 路径——偏科可达）
    Tool: pytest
    Steps:
      1. plot 会话：模拟只答类型序前段模块全部字段（历史/文明/世界）
      2. 断言 sync_position 落到前段之后的首个未答模块（按类型序）而非跳向最后
      3. 继续作答至全 35 键 filled → 断言 phase=="completed"
      4. 断言中途任一时刻 finalize 门禁 missing_sections 语义与基线一致（未达 50% 模块照常列出）
    Expected Result: 全部通过——队列前移不造成任何字段不可达
    Failure Indications: 出现字段永不被遍历；门禁列表缺失本应缺失的模块
    Evidence: .sisyphus/evidence/task-2-r6-reachability.txt

  Scenario: 无 profile 回归零变化
    Tool: pytest
    Steps:
      1. 无 impulse 开局（旧客户端形态）+ healing 型开局（不在优先表）
      2. 断言 current_module=="IP定位"（原序首个）且全模块遍历序 == module_ids() 原序
    Expected Result: 通过
    Evidence: .sisyphus/evidence/task-2-default-order-regression.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): type-driven forward-only queue reordering in sync_position (R6 conservative mode)`
  - Pre-commit: `cd backend && pytest`

- [x] 3. 语气锚点：_seed_block 模板变量注入

  **What to do**:
  - `backend/app/domains/creation/a1/interviewer.py`（本任务独占）：
    - 模块级常量 `ANCHOR_BY_TYPE: dict[str, str]`——9 型锚点文案**逐字取自 spec §5.2"语气锚点"列**（全文见本计划 Must Have，一个字不许改写）
    - `_seed_block`（:305-315）：在既有 seed_lines 逻辑**之后**追加——`creator_primary` 非空且在 `ANCHOR_BY_TYPE` → 追加一行 `f"语气锚点（引导与反馈的基调，务必贯彻）：{anchor}"`；**creator_primary 为空时函数输出与现状逐字节相同**（不追加任何行、不多一个换行——回归铁律）
    - 注意 `_seed_block` 是 @staticmethod 且被 interview（:317-334 的"【种子起点】"块 :326-327）与 suggestion（:449/:495-503）两处 prompt 复用——注入在 `_seed_block` 内即两处自动生效，**不改任何 prompt 骨架文本**（prompt 变体数恒为 1，R2）
  - 新增 pytest（建议 `backend/tests/unit/a1/test_tone_anchor.py`）：
    - happy：creator_primary=="plot" 的 session → `_build_prompt` 输出含 "节奏导向" 锚点行；suggestion prompt 同样含（复用生效证明）
    - 逐型矩阵：9 型锚点串与 `ANCHOR_BY_TYPE` 值逐字断言（防拼写漂移）
    - failure/回归：creator_primary=="" → `_seed_block` 输出与改动前快照逐字节相等（用改前录制的期望串硬断言）；未知 creator_primary 值 → 不追加锚点行不抛错
    - prompt 变体审计：grep 断言 interviewer.py 中 prompt 模板字符串仅一份（无按型分支的 prompt 复制）

  **Must NOT do**:
  - 不得创建第二份 prompt / 按型 if-else 分支 prompt 骨架（R2 红线：差异是数据不是代码）
  - 不得改写锚点文案（逐字纪律）；不得动 guide_engine.py（T2 独占）
  - 不得改 _seed_block 既有 seed_lines 输出顺序

  **Recommended Agent Profile**:
  - **Category**: `quick`（单文件模板变量注入 + 逐字断言测试，规格完全给定）
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 2——interviewer.py 独占）
  - **Parallel Group**: Wave 2（with T2, T4, T5）
  - **Blocks**: T6
  - **Blocked By**: T1（消费 creator_primary 字段——字段名契约已在计划锁定，实现须待 T1 合入）

  **References**:
  - `backend/app/domains/creation/a1/interviewer.py:305-315`（_seed_block）+ `:317-334`（_build_prompt 注入点）+ `:449/:495-503`（suggestion 复用点）
  - spec §5.2"语气锚点"列（逐字文案权威）+ §11.1-②（模板变量注入）+ §12.1.2 R2（一型一 prompt 爆炸——本任务是其反面实现）
  - `docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md`（NL 不携带机器格式——锚点进 prompt 不进 answers，铁律兼容）

  **Acceptance Criteria**:
  - [ ] 9 型锚点逐字断言全过；plot 会话 interview+suggestion 双 prompt 均含锚点
  - [ ] 空 profile 输出逐字节回归等价（快照断言绿）
  - [ ] interviewer.py 内 prompt 骨架份数 = 1
  - [ ] pytest 全绿

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 锚点注入 happy path
    Tool: pytest
    Preconditions: T3 完成
    Steps:
      1. 构造 creator_primary="philosophy" 的 A1Session
      2. 调 Interviewer._build_prompt(世界本体模块, reality_rule, session)
      3. 断言输出含 '追问"如果这条规则被违反会怎样"'
    Expected Result: 通过；且 suggestion prompt 同样命中
    Evidence: .sisyphus/evidence/task-3-anchor-injected.txt

  Scenario: 空 profile 逐字节回归（failure 路径）
    Tool: pytest
    Steps:
      1. creator_primary="" 的 session → _seed_block 输出 == 改前快照串（硬编码期望）
      2. creator_primary="bogus" → 输出 == 空串快照（不追加行）
    Expected Result: 两断言通过
    Failure Indicators: 多出空行/锚点行；未知值抛 KeyError
    Evidence: .sisyphus/evidence/task-3-empty-profile-regression.txt

  Scenario: R2 prompt 变体审计
    Tool: Bash
    Steps:
      1. git diff -- backend/app/domains/creation/a1/interviewer.py | Select-String "你是TRPG世界观设计的访谈引导者"
    Expected Result: 该 prompt 骨架串零出现在 diff（未被复制/分支）
    Evidence: .sisyphus/evidence/task-3-single-prompt.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): tone anchor injection via _seed_block template variable (single-prompt, R2-safe)`
  - Pre-commit: `cd backend && pytest`

- [x] 4. 前端 impulse 结构化上送（A1Workspace 唯一触碰任务）

  **What to do**:
  - `frontend/src/pages/a1/A1Workspace.tsx`（本任务独占，总 diff <80 行）：
    - **impulse 上送类型**（局部 type 或复用）：`type ImpulsePayload = { primary: string; secondary?: string }`——primary 取值 = 9 型枚举（`ImpulseTypeId` 已存在于 impulseCards.config.ts:23 导入，直接复用其类型）
    - **startSession 扩展**（:528-574）：签名改为 `startSession(seedId?: string, customIdeaText?: string, impulse?: ImpulsePayload)`；请求体（:534-538）追加 `...(impulse && { impulse_primary: impulse.primary, ...(impulse.secondary ? { impulse_secondary: impulse.secondary } : {}) })`——次冲动为空 → **不含** `impulse_secondary` 键（缺省语义，后端置空串）
    - **pendingImpulseRef**（G7）：`useRef<ImpulsePayload | null>`；`handleImpulseCommit`（:577-599）确认时设置：
      - healing → `pendingImpulseRef.current = { primary: 'healing' }` → `startSession('7', undefined, pendingImpulseRef.current)`（或直接传参）
      - 故事侧 5 型 → `{ primary, secondary?: secondary ?? undefined }` 随 custom_idea 直达传入
      - 设定侧 2 型 → 存入 ref（不开 session）；分组种子页的种子点击调用点改为 `startSession(seedId, undefined, pendingImpulseRef.current ?? undefined)`，start 成功后 `pendingImpulseRef.current = null`
      - nostalgia / skip → **不设 ref 不上送**（无 profile，默认序——skip 用户与怀旧用户诚实走默认访谈）
    - **埋点衔接**：startSession 成功回调内（:546 附近）`attachSessionId(response.session_id)`（T5 产出接口，逐字锁定）——仅一行
    - 上传链开 session 的路径（如有）：不附带 impulse（nostalgia 语义）
  - 配套：检查 `frontend/src/pages/a1/impulse/__tests__/` 与 `frontend/tests/e2e/a1-impulse-entry.spec.ts` 中 session-start 相关断言——请求体新增可选键不破坏既有断言；若 E2E 有请求体全等断言（罕见）→ 允许最小更新并留档（不算删测试）
  - 新增/扩展前端单测：startSession 请求体含 impulse 键（happy）、次冲动空时无 impulse_secondary 键（failure/edge）、skip/nostalgia 路径请求体不含 impulse 键

  **Must NOT do**:
  - **总 diff <80 行**；不得重构/重排/提取既有代码；不得改既有函数签名语义（startSession 仅追加可选第三参，既有调用点零破坏）
  - 不得动 telemetry.ts（T5 独占）/ 不得动 impulse/ 组件文件（仅消费）
  - 不得新增端点/网络调用；不得把 impulse 塞进 custom_idea 文本（结构化字段与 NL 文本分离——三铁律精神）

  **Recommended Agent Profile**:
  - **Category**: `deep`（单体文件精确手术 + 多调用点 + E0.1 分流语义保护）
  - **Skills**: [`verification-before-completion`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 2——A1Workspace.tsx 独占）
  - **Parallel Group**: Wave 2（with T2, T3, T5）
  - **Blocks**: T6
  - **Blocked By**: T1（联调依赖；契约已在计划锁定）

  **References**:
  - `frontend/src/pages/a1/A1Workspace.tsx:528-574`（startSession 全文）+ `:577-599`（handleImpulseCommit 全文——E0.1 四路分流逐行读懂）+ `:281`（STORY_SIDE_TYPES）+ `:306`（lazy initializer——本任务零触碰）
  - `frontend/src/pages/a1/impulse/impulseCards.config.ts`（ImpulseTypeId 类型复用）
  - `frontend/src/pages/a1/impulse/telemetry.ts`（T5 的 attachSessionId 签名——消费不修改）
  - spec §11.1-①（session/start 结构化上送）、learnings.md E2E mock 兼容项

  **Acceptance Criteria**:
  - [ ] tsc 0 错误；vitest 223+ 全绿
  - [ ] healing 直达请求体含 `impulse_primary:"healing"`；故事 5 型含 primary+secondary（有次选时）；skip/nostalgia 不含 impulse 键
  - [ ] 设定侧 2 型：确认→分组种子页→点种子 → 请求体含对应 primary（上下文保持 G7）
  - [ ] A1Workspace.tsx diff <80 行（F2 复核）

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 故事 5 型结构化上送（happy path）
    Tool: vitest（mock fetch 断言请求体）
    Preconditions: T4 完成
    Steps:
      1. 渲染 A1Workspace → impulse_cards → 选 plot 主 + romance 次 → 确认
      2. 断言 POST /api/a1/session/start body: impulse_primary=="plot" 且 impulse_secondary=="romance" 且 custom_idea 为 tagline 文本
    Expected Result: 断言通过——结构化字段与 NL 文本并存不互斥
    Evidence: .sisyphus/evidence/task-4-structured-send.txt

  Scenario: 次冲动缺省 + 路径分流（edge/failure）
    Tool: vitest
    Steps:
      1. 仅选 healing 主 → 确认 → body 含 impulse_primary=="healing" 且 **无 impulse_secondary 键**（`"impulse_secondary" in body === false`）
      2. skip → seed_selector → 选任意种子 → body 不含 impulse_primary 键
      3. nostalgia 确认 → 聚焦上传（不开 session）→ 无 session/start 调用
    Expected Result: 三断言通过
    Evidence: .sisyphus/evidence/task-4-default-semantics.txt

  Scenario: 设定侧上下文保持（G7）
    Tool: vitest
    Steps:
      1. 选 setting_heavy → 确认（进分组种子页）→ 点击"群星彼岸"种子
      2. 断言请求体含 seed_id 且 impulse_primary=="setting_heavy"
    Expected Result: 通过
    Evidence: .sisyphus/evidence/task-4-setting-side-context.txt
  ```

  **Commit**: YES
  - Message: `feat(a1-entry): structured impulse IDs on session/start (primary/secondary, empty-secondary omission)`
  - Pre-commit: `npx tsc --noEmit && npx vitest run`

- [x] 5. telemetry attachSessionId（session_id 回填）

  **What to do**:
  - `frontend/src/pages/a1/impulse/telemetry.ts`（本任务独占）：新增导出（**签名逐字锁定**，T4 消费）：
    ```ts
    export function attachSessionId(sessionId: string): void;
    ```
    语义：遍历 `getImpulseTelemetry()` 全量，`session_id` 为空的就地补 `sessionId`（含 FJSON 重写 localStorage `a1_telemetry_v1`）；不新增事件名、不改 `ImpulseTelemetryEvent` 结构（session_id 本就是可选字段）、schema_version 恒 1；损坏存储容错与既有规则一致
  - wiring 调用归 T4（本任务不触碰 A1Workspace.tsx）
  - 扩展 telemetry 单测：追加事件→attachSessionId→读取断言全量回填；重复调用幂等；损坏存储不抛错

  **Must NOT do**:
  - 不得新增事件名/指标/上报通道（零网络铁律不变）；不得改既有导出函数签名
  - 不得触碰 A1Workspace.tsx / impulse 其他文件

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 2——telemetry.ts 独占；wiring 侧由 T4 在 Wave 2 内以锁定签名预接，T6 联调验证）
  - **Parallel Group**: Wave 2（with T2, T3, T4）
  - **Blocks**: T6
  - **Blocked By**: None

  **References**:
  - `frontend/src/pages/a1/impulse/telemetry.ts`（E0 schema v1 全文——ImpulseTelemetryEvent.session_id 本就可选字段）
  - spec §12.1.1 R1（对照组需要 session 级归因——本任务为其数据补全，不扩指标）
  - E0 裁决（Interview Summary）：仅 session_id 关联，轻量

  **Acceptance Criteria**:
  - [ ] attachSessionId 存在且单测全绿（回填/幂等/损坏容错）
  - [ ] vitest 223+ 全绿；零网络 API 引入

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 回填与幂等（happy）
    Tool: vitest
    Steps:
      1. logImpulseEvent('impulse_card_selected', {...})（无 session_id）
      2. attachSessionId('a1_abc123') → getImpulseTelemetry()[0].session_id=='a1_abc123'
      3. 再 attachSessionId('a1_def456') → 已有值不被覆盖
    Expected Result: 三断言通过
    Evidence: .sisyphus/evidence/task-5-attach-session-id.txt

  Scenario: 零网络回归（failure 路径）
    Tool: Bash
    Steps:
      1. Select-String -Path frontend/src/pages/a1/impulse/telemetry.ts -Pattern "fetch|sendBeacon|XMLHttpRequest|axios"
    Expected Result: 0 命中
    Evidence: .sisyphus/evidence/task-5-zero-network.txt
  ```

  **Commit**: YES
  - Message: `feat(a1-entry): telemetry attachSessionId backfill for impulse events`
  - Pre-commit: `npx tsc --noEmit && npx vitest run`

- [x] 6. 集成收尾：全量验证 + 契约审计 + E2E mock 核查

  **What to do**:
  - 三命令全量：`cd backend && pytest`（1020+ 全绿）/ `cd frontend && npx tsc --noEmit`（0）/ `cd frontend && npx vitest run`（223+ 全绿）
  - 契约审计：C1-C5 五文件存在且用例数与基线一致（`git diff --stat -- backend/tests/unit/a1/test_contracts/` 应为空——Lite 不需扩展 C1-C5 本体，因其契约面 = answers/SIR/双树/词表/tier，均未触碰；**若 F4 发现契约面意外触碰则在此补扩展**）；`test_module_ids_match_spec` 未改动
  - E2E mock 核查：grep `frontend/tests/e2e/` 中 session-start mock——确认请求体新增可选键不破坏（响应结构零新增 → 应天然兼容）；若 Playwright 可本地起后端则跑既有 e2e 套件回归，不可起则以 mock 静态核查 + 留档说明（learnings：E2E 依赖后端运行环境）
  - 交叉验证端到端（pytest 级）：plot impulse 开局 → 首问 main_plot → `_build_prompt` 含"节奏导向"锚点 → 作答推进队列 → finalize 门禁语义不变（三件套集成冒烟，一个测试串起 T1/T2/T3 产出）
  - 汇总证据清单 + `git status` 逐文件核对无未入账改动

  **Must NOT do**:
  - 不得为绿灯改产品代码（发现 bug 回对应任务修）；不得删/跳过测试
  - 不得顺手扩展 C1-C5 之外的新契约测试面（范围纪律）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`（全量验证 + 审计判断）
  - **Skills**: [`verification-before-completion`] + [`systematic-debugging`]

  **Parallelization**:
  - **Can Run In Parallel**: NO（收尾串行）
  - **Blocks**: F1-F4
  - **Blocked By**: T1-T5

  **References**:
  - 全部 T1-T5 产出；`backend/tests/unit/a1/test_contracts/`（C1-C5）；`backend/tests/unit/a1/test_question_tree.py:28`
  - `.sisyphus/notepads/e0-impulse-entry/learnings.md`（E2E mock 依赖/file 水合坑/证据归档纪律）
  - 本计划 Definition of Done 全表

  **Acceptance Criteria**:
  - [ ] 三命令全绿（pytest 1020+ / tsc 0 / vitest 223+）
  - [ ] C1-C5 与 test_module_ids_match_spec 零 diff；FINALIZE_MODULE_THRESHOLD 零触碰
  - [ ] 端到端集成冒烟测试绿（impulse→队列→锚点→门禁）
  - [ ] `git status` 无未入账文件

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 三命令全绿（happy path）
    Tool: Bash
    Steps:
      1. cd backend; pytest 2>&1 | Select-String "passed|failed"
      2. cd ../frontend; npx tsc --noEmit; echo "exit=$LASTEXITCODE"
      3. npx vitest run 2>&1 | Select-String "Test Files|Tests "
    Expected Result: pytest 0 failed；tsc exit 0；vitest 0 failed
    Evidence: .sisyphus/evidence/task-6-all-green.txt

  Scenario: 端到端集成冒烟（三件套串测）
    Tool: pytest
    Steps:
      1. start_session(custom_idea, impulse_primary="plot", impulse_secondary="romance")
      2. 断言 creator_primary/secondary 落库 + 首问 main_plot + prompt 含锚点
      3. 作答推进 + finalize 门禁行为与基线一致
    Expected Result: 全链断言通过
    Evidence: .sisyphus/evidence/task-6-e2e-smoke.txt
  ```

  **Commit**: YES（若有测试补齐）
  - Message: `test(a1): E1-Lite integration smoke + full-suite verification`
  - Pre-commit: `cd backend && pytest`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 个审查代理并行。ALL must APPROVE。呈交合并结果给用户，取得明确 "okay" 前不得标记完成。
> **不得在用户 okay 前勾选 F1-F4。** 拒绝或用户反馈 → 修复 → 重跑 → 再呈交 → 再等 okay。

- [x] F1. **Plan Compliance Audit** — `oracle`
  通读本计划。逐条核对 "Must Have"：实现存在性（读文件/跑命令/pytest）。逐条核对 "Must NOT Have"：全仓搜索禁止模式（MODULES diff/FINALIZE_MODULE_THRESHOLD/新端点/新 LLM 调用/A2 文件/creator_profile.py/skip 标记）——命中即 REJECT 并给出 file:line。核对 `.sisyphus/evidence/` 证据文件齐全。对照 deliverables 清单。
  输出：`Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  跑三命令全量（pytest/tsc/vitest）。审查全部改动文件：`as any`/`@ts-ignore`、空 catch、prod console.log（console.warn 降级允许）、注释掉的代码、未用 import。AI slop 检查：过度注释/过度抽象/泛型命名。A1Workspace.tsx diff 行数复核（<80）。prompt 变体数复核（interviewer 骨架恒 1 份）。
  输出：`Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  执行每个任务的每个 QA 场景——按确切步骤走、捕获证据。集成场景：9 型逐型开局（pytest 直调 API）验证首问/锚点/队列三件套矩阵；前端 plot+romance 双选上送；skip 回归。存 `.sisyphus/evidence/final-qa/`。
  输出：`Scenarios [N/N pass] | Integration [N/N] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  逐任务：读 "What to do"，读实际 diff。验证 1:1——三件套全做了（无遗漏）、OUT 清单全没做（无蔓延：重点排查推断包/看门狗/子字段级重排/枚举模块新文件）。跨任务污染检查：T2 不碰 interviewer.py、T3 不碰 guide_engine.py、T4 不碰 telemetry.ts。未入账改动清点（`git status` 逐文件核对）。
  输出：`Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **T1**: `feat(a1): creator_profile field group on A1Session + structured impulse fields on StartRequest`
- **T2**: `feat(a1): type-driven forward-only queue reordering in sync_position (R6 conservative mode)`
- **T3**: `feat(a1): tone anchor injection via _seed_block template variable (single-prompt, R2-safe)`
- **T4**: `feat(a1-entry): structured impulse IDs on session/start (primary/secondary, empty-secondary omission)`
- **T5**: `feat(a1-entry): telemetry attachSessionId backfill for impulse events`
- **T6**: `test(a1): E1-Lite integration smoke + full-suite verification`
- 每个 commit 前：后端任务 → `cd backend && pytest` 必须通过；前端任务 → `npx tsc --noEmit && npx vitest run` 必须通过
- 提交纪律（继承 E0）：原子提交、每任务独立 commit、不混入无关文件

---

## Success Criteria

### Verification Commands
```bash
cd backend && pytest                       # Expected: 1020+ passed, 0 failed
cd frontend && npx tsc --noEmit            # Expected: 0 errors
cd frontend && npx vitest run              # Expected: 223+ passed, 0 failed
git diff --stat <base> -- backend/app/domains/creation/seed/a1_question_tree.py
#   Expected: empty output（MODULES 零触碰铁证）
git diff <base> -- backend/app | Select-String "FINALIZE_MODULE_THRESHOLD"
#   Expected: 0 hits（门禁语义零变化铁证）
```

### Final Checklist
- [ ] 三件套全部交付：creator_profile 落库 / 类型驱动队列（只前移不跳过）/ 语气锚点（单 prompt）
- [ ] 前端结构化上送 + 缺省语义 + 设定侧上下文保持
- [ ] plot/unsure 新会话首问 = 历史时间线.main_plot（"你的世界里正在发生什么事"级故事问题）- [ ] 门禁语义 / MODULES 锁序 / 契约 C1-C5 / 三命令基线全部零破坏
- [ ] All "Must Have" present / All "Must NOT Have" absent
- [ ] DECISION NEEDED 1/2/3 已呈交产品方（默认值已生效，不阻塞）
- [ ] 全部证据归档 `.sisyphus/evidence/`（过程留档，gitignore 不提交）

### DECISION NEEDED（呈交产品方，均已有安全默认值）
1. **队列口径**：产品口头"5 故事型都 main_plot 前置" vs spec §5.2 逐型表（哲理=reality_rule 先/爱情=IP定位 先）。默认 = **§5.2 逐字**（MUST DO 明文权威）。
2. **角色驱动序**：Lite 无第 0 模块（character_sketch OUT）。默认 = §5.2 行去掉第 0 模块：文明冲突→历史主线→世界本体→力量。
3. **未知枚举语义**：默认 = **忽略降级默认序 + warning**（不 400——防版本漂移堵死开局，D2-③ 精神）。若需严格校验改 400，改动一处。
