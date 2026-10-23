# A1 开放问题阶段状态机施工单（P2 合并批：oq_phase + proposal 显式相位 + pendingQuestion 单源 + 二次收尾）

## TL;DR

> **Quick Summary**: 把「开放问题作答」从 LLM 碰巧分类升级为显式会话相位——第一次收尾选「继续访谈」进入 oq_phase，chat 走确定性作答通道，逐题答/跳，清结触发第二次收尾（复用 D21 三联问，产物语义=重定稿+文档再生成）；前端 pendingQuestion 单源化 + proposal 显式横幅。P2 三件（单源/显式相位/阶段机）合一，因三层同刀不可分拆。
> **Deliverables**:
> - A1Session.oq_phase_active / oq_round（additive）+ 状态机（进入/推进/闭合/轮次上限 2）
> - chat 前置相位门：oq_phase 内确定性作答路由（零 LLM 分类）+ 提案短指令仍最高优先
> - 第二次收尾触发器（复用 D21，产物语义注入）+ E0 埋点 oq_phase_entered / oq_phase_closed
> - 前端：删 file 派生竞态 effect（L539-548）、✦ 卡与输入框由相位驱动、proposal 横幅、二次收尾面板复用、oq_phase 期间定稿按钮禁用
> - 回归基线：16:21 病例（收尾态同消息）additive 守护用例 + E2E 幕六全链
> **Estimated Effort**: Large（后端状态机 + 前端绑定 + E2E，与商业加固批同量级）
> **Parallel Execution**: PARTIAL（后端先行，前端随后，E2E 收口）
> **Critical Path**: T1 schema → T2 路由 → T3 二次收尾 → T4 前端 → T5 E2E/门禁 → T6 治理

---

## Context

### Original Request
产品方真机验收连续病理 + 设计拍板（2026-10-19）：
1. 「应该是在回答待问开放问题阶段」——收尾后继续访谈的输入应绑定开放问题，而非被访谈填充管线吸走
2. 「你能分清楚第一次收尾和第二次开放问题阶段的收尾吗」——两类收尾须显式区分（预设问卷收尾 vs 开放问题清结收尾）
3. 「检查 P2 能否合并修复」→ 核查结论：三件在 A1Session/chat 路由/A1Workspace 三层同刀，**必须合一**

### Interview Summary
- 病理链实证：oq 作答靠 interviewer `_pending_open_question`（iv:168/180/734）软路由——同一消息路由取决于内部状态残影（16:21 碰巧对、收尾态下被 `角色.character_visual` 填充分类吸走生成占位提案）
- 已修底层（正交不重叠）：F1 占位闸 / F2 提案短指令消解 / F3 已答不重问 / ErrorBoundary / 看门狗
- 产品方默认拍板：二次收尾三联问文案**复用**，只换产物语义

### Metis Review（2026-10-19，全部吸收）
- **循环防护（最关键）**：重定稿 graphify 再产新 oq → 不自动重开；仅当用户在第二次收尾再选「继续访谈」才开新一轮，`oq_round` 硬上限 **2**（达限不再提供重开，诚实提示「开放问题已答满两轮」）
- **进入条件**：oq_log 待问 ≥1 才进入（=0 时「继续访谈」维持原自由访谈语义，不进相位）
- **非作答输入 fallback**：oq_phase 内一切非空文本=作答当前题（确定性）+ 回执确认话术（模板零 LLM：「已记下：{answer 摘要}」+ 下一问）；skip 按钮=唯一逃生口；不做闲聊分支（防 creep）
- **门禁交互**：oq_phase 期间前端定稿按钮禁用（tooltip 说明）——定稿只能从第二次收尾进入
- **刷新恢复**：oq_phase_active 落盘（mirror_thread 先例）；GET /file 响应 additive 带 `oq_phase_active` + 当前待问题 → 前端冷启动恢复
- **改已答内容**：oq_phase 内 out-of-scope（UI 不提供入口，留待后续轮）
- **closed 埋点载荷**：`{round, answered_count, skipped_count}`（无 reason 枚举，防过度设计）
- **复用验证点**：D21 收尾触发器参数化 / ClosingPanel props 不硬编码首收文案——若硬编码则最小抽 prop 注入
- **护栏**：oq_phase 不得反向影响收尾态既有路径（16:21 病例守护用例）；答>50% 门禁只进不出；重定稿产物 additive

---

## Work Objectives

### Core Objective
让「回答开放问题」成为一等会话相位：路由确定性、UI 显式绑定、收尾可区分、循环有界。

### Must Have
1. `A1Session.oq_phase_active: bool = False` + `oq_round: int = 0`（additive，pydantic 自动落盘）
2. 进入：第一次收尾「继续访谈」且 oq 待问 ≥1 → 置位 + `oq_phase_entered` 埋点
3. 路由前置门：oq_phase 内 chat——提案短指令（F2）最优先 → `skip_question_id` 跳过 → 非空文本确定性记为当前 oq 作答（零 LLM 分类、不进六通道级联）→ 推进下一问
4. 闭合：`next_pending()=None` → 复位相位 + 触发第二次收尾（D21 复用、产物语义=重定稿+再生成）+ `oq_phase_closed{round,answered,skipped}` 埋点
5. 轮次：第二次收尾再选「继续访谈」且有待问 → `oq_round+1` 重开；round≥2 不再提供
6. 前端：删 L539-548 竞态 effect；✦ 卡/输入框 placeholder/回执流由相位驱动；`proposals` 非空→顶部横幅（输入保持可用）；oq_phase 定稿禁用
7. GET /file additive 带 `oq_phase_active`（刷新恢复）；ChatResponse additive 带 `oq_phase_active`

### Must NOT Have（红线）
- 不改六通道级联内部顺序（前置门在级联之前；共存矩阵既有断言零触碰，只 additive 补 oq 行）
- 不动 InterviewResult/ChatResponse 既有键语义（新键全 additive）
- 不做 oq_phase 内改已答内容 / 闲聊分支 / reason 枚举（Metis 防 creep 三连）
- 不动已修 F1-F4 / ErrorBoundary / 看门狗任何代码
- 不动 D21 三联问既有文案本体（复用=参数化注入产物语义，不复制粘贴第二份）
- 后端不新增 LLM 调用（作答回执=确定性模板）
- 不顺手重构 A1Workspace 其他 effect（单源化仅删 L539-548 + 接相位）

---

## Verification Strategy (MANDATORY)

> 全部 agent 可执行。TDD：每任务红测先行。

### Test Decision
- Infrastructure exists: YES（pytest 1854 / vitest 334 / Playwright 五幕）
- Automated tests: TDD
- Framework: pytest + vitest + Playwright

### QA Policy
- 后端红测：进入/推进/闭合/轮次上限/循环防护/16:21 病例守护/门禁不回落，≥10 用例
- 前端：相位驱动卡、横幅、定稿禁用、刷新恢复，≥5 用例
- E2E 幕六全链 + 既有五幕不回归
- 证据：`.sisyphus/evidence/oq-phase-t{N}-*.txt`

---

## Execution Strategy

```
Wave 1（后端状态机，串行）: T1 schema+进入/闭合 → T2 路由门 → T3 二次收尾+埋点
Wave 2（前端绑定）:        T4 相位驱动 UI（依赖 T1-T3 契约）
Wave 3（收口）:            T5 E2E 幕六 + 全门禁 → T6 治理
Critical Path: T1→T2→T3→T4→T5→T6；Max Concurrent: 2（T4 内部前端件并行）
```

## TODOs

- [x] 1. T1 Schema + 进入/闭合状态机（后端）

  **What to do**:
  - A1Session 增 `oq_phase_active: bool = False`、`oq_round: int = 0`（additive；pydantic 自动随 store 落盘——mirror_thread 先例）
  - 进入点：第一次收尾「继续访谈」分支（D21 收尾继续路径）——`oq_log 待问 ≥1` 才置位；=0 维持原语义；进入时 `emit_event("oq_phase_entered", session, round=session.oq_round)`
  - 闭合点：`oq_log.next_pending() is None` 时复位 + `emit_event("oq_phase_closed", session, round=, answered=, skipped=)`
  - 轮次：第二次收尾「继续访谈」且有待问 → `oq_round+1` 重开；`oq_round >= 2` 时该选项不再下发（响应中该选项缺席或 disabled 标记——选最小实现）
  - 红测 ≥4：进入条件（有/无待问两分支）/ 闭合复位 / 轮次重开 / 轮次上限拒绝；断言 A1Session 键集 additive（沿用既有 additive 锁测试模式）

  **Must NOT do**: 不动既有 phase 字段语义；不新增 LLM。

  **Acceptance / QA**:
  ```
  Scenario: 进入与闭合
    Tool: Bash(pytest)
    Steps: 构造 closing_step=1 会话+待问 2 条 → 走「继续访谈」→ 断言 oq_phase_active=True 且 entered 埋点；
           逐条作答至 next_pending=None → 断言复位 + closed 埋点载荷 {round,answered,skipped}
    Evidence: .sisyphus/evidence/oq-phase-t1.txt
  Scenario: 轮次上限
    Steps: round=2 时选「继续访谈」→ 断言不重开（active 仍 False）且响应无该选项
  ```

- [x] 2. T2 chat 前置相位门——确定性路由（后端）

  **What to do**:
  - `handle_message`（guide_engine L1768）入口最前（提案短指令 F2 之后、六通道级联之前）加相位门：
    `if session.oq_phase_active:` →
    a) `skip_question_id` → 既有跳过路径推进下一问；
    b) 非空文本 → **确定性**记为当前 oq 作答（oq_log mark_answered；不调 interviewer fills/不作 LLM 意图分类）；回执=模板「已记下你的回答。下一问：{q}」（末题时接 T3 二次收尾话术）；
    c) 当前无待问（防竞态）→ 复位相位走原级联
  - 提案短指令优先级保持最高（oq_phase 内提案可并存，F2 消解后回 oq 流）
  - 16:21 病例守护红测：closing_step>0 + oq_phase 会话发「工程行业吧.光辉我不知道，我不愿意面对」→ 断言**零 fills/零 proposals**，作答落在当前 oq
  - 共存矩阵 additive 补行：oq_phase 路由不触碰既有六通道断言
  - 红测 ≥4：确定性作答（自然语言任意文本不进填充）/ skip 推进 / 提案并存消解回 oq / 病例守护

  **Must NOT do**: 不改 L1905/2073/2115 级联内部顺序与条件；InterviewResult 既有键零触碰（如需新键走 additive——原则上作答回执复用 reply 文本无需新键）。

  **Acceptance / QA**:
  ```
  Scenario: 病例守护（本批最重要用例）
    Tool: Bash(pytest)
    Steps: 复刻 16:21 病例状态（收尾态+相位激活）发原句 → 断言 pending_proposals 空、answers['角色.character_visual'] 不变、oq_log 当前题 answered
    Evidence: .sisyphus/evidence/oq-phase-t2.txt
  ```

- [x] 3. T3 第二次收尾触发 + 产物语义注入（后端）

  **What to do**:
  - 相位闭合时触发第二次收尾：复用 D21 收尾机制（closing 触发器参数化——验证现有触发点，若硬编码首次语义则最小抽参注入「重定稿+文档再生成」措辞；**不复制第二份三联问文案**）
  - ClosingPanel 复用验证：props 若硬编码首收文案 → 最小抽 prop（`variant: 'first' | 'refinalize'`）
  - 重定稿产物走既有 finalize v2 机制（IP0077-W1-v2 先例）；门禁 >50% 只进不出（oq_phase 不重算答题比）
  - ChatResponse additive 带 `oq_phase_active`（前端驱动契约）；GET /file additive 带 `oq_phase_active`
  - 红测 ≥3：闭合即触发二次收尾（closing 信号/step）/ 变体文案注入 / file 端点新键

  **Must NOT do**: 不动 finalize/graphify 本体；三联问既有文案字节不动。

  **Acceptance / QA**:
  ```
  Scenario: 二次收尾触发
    Steps: 相位会话清结最后一条 → 断言响应 closing 信号 + closing_step 进入收尾步 + variant=refinalize 面板语义
    Evidence: .sisyphus/evidence/oq-phase-t3.txt
  ```

- [x] 4. T4 前端相位驱动 UI（前端）

  **What to do**:
  - **删竞态源**：A1Workspace L539-548 file 派生 effect 整段删除；pendingQuestion/pendingQuestionsCount 改由 chat 响应 + 相位契约（`oq_phase_active`）驱动
  - 冷启动恢复：GET /file 带回 `oq_phase_active` 时恢复相位 UI（一次性，非竞态源——与 chat 实时值以「相位激活期间 chat 响应优先」为序）
  - GuidedChat：oq_phase 激活时输入框 placeholder=当前问题文本；✦ 卡升级为对话主体（当前题突出显示）
  - proposal 横幅：`proposals` 非空 → 顶部「有一条待确认修改待处理」横幅（输入框保持可用，F2 短指令可消解）
  - 定稿禁用：oq_phase_active 期间定稿按钮 disabled + tooltip「先答完/跳过开放问题，从收尾处定稿」
  - 二次收尾面板：ClosingPanel variant=refinalize 渲染（依赖 T3 的 prop 注入）
  - 红测 ≥5：相位卡驱动 / placeholder 绑定 / 横幅渲染且输入可用 / 定稿禁用 / 刷新恢复（mock file 响应带相位 → 断言 UI 恢复）

  **Must NOT do**: 不动 A1Workspace 其他 effect；不动 ErrorBoundary/看门狗代码。

  **Acceptance / QA**:
  ```
  Scenario: 刷新恢复
    Tool: Bash(vitest)
    Steps: mock GET /file 返回 oq_phase_active=true + 待问 → 渲染 A1Workspace → 断言 ✦ 卡在 + placeholder=问题文本 + 定稿 disabled
    Evidence: .sisyphus/evidence/oq-phase-t4.txt
  ```

- [x] 5. T5 E2E 幕六 + 全门禁

  **What to do**:
  - `a1-wave3-frontend.spec.ts` 增幕六「开放问题全链」：路由 mock——访谈快进 → 第一次收尾（closing 响应）→ 选继续（oq_phase_entered，mock 带待问 2）→ 答 1 题（断言回执「已记下」+下一问 placeholder）→ 跳 1 题 → 断言二次收尾面板（refinalize 语义）→ 全程页面存活（error-boundary 不在）
  - 既有五幕断言零改动仍绿；closing-state mock 后注册顺序保持
  - 全门禁：定向红测 → pytest 全量（≥1854+新增）→ vitest 全量（≥334+新增）→ tsc -b delta=0（20/11 存量）→ Playwright 六幕 → ruff 增量 0 → 白名单核对
  - 证据四件：oq-phase-t2/t4/t5-e2e/t5-gate

  **Acceptance / QA**:
  ```
  Scenario: 幕六全链
    Tool: Bash(playwright --project=chromium)
    Expected: 6 passed；幕六断言含 entered 回执/跳过推进/二次收尾文案/页面存活四要素
    Evidence: .sisyphus/evidence/oq-phase-t5-e2e.txt
  ```

- [x] 6. T6 治理登记

  **What to do**:
  - PROJECT_STATE 新节：病理链（软路由残影→占位提案循环）+ 状态机设计 + Metis 六缺口吸收 + 提交链 + 门禁数字 + 遗留（改已答内容 out-of-scope 记后续轮）
  - decision-log 视产品方令：若要求立 D 条目则补（默认仅 PROJECT_STATE，遵循近批惯例）

  **Acceptance**: PROJECT_STATE 落痕 + MOC 变更记录行；白名单含本批全部文件。

---

## Final Verification Wave

- [x] F1 计划合规（oracle）：Must Have 7/7 / 红线 7/7 / 证据链
- [x] F2 质量：pytest/vitest/tsc delta=0/ruff 增量 0/AI slop 扫描
- [x] F3 真实 QA：六幕 E2E 全绿 + 幕六全链重放
- [x] F4 范围：白名单逐文件 + 六通道字节锁零触碰证明

---

## Commit Strategy

- T1-T3: `feat(a1): oq_phase 状态机——schema/进入闭合/确定性路由/二次收尾/埋点（分两笔：schema+路由 / 收尾+埋点）`
- T4: `feat(frontend): 开放问题相位驱动 UI——单源化/输入绑定/提案横幅/定稿禁用/刷新恢复`
- T5: `test(e2e): 幕六开放问题全链——进入→答/跳→二次收尾→重定稿`
- T6: `docs(governance): oq_phase 批登记`

## Success Criteria
- [x] 全部 Must Have 存在、红线缺席
- [x] pytest ≥1854+10 全绿 / vitest ≥334+5 全绿 / tsc delta=0 / Playwright 六幕绿
- [x] 16:21 病例守护用例锁定（收尾态同消息不再生成字段提案）
