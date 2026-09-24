# E0 冲动承接入口系统实施计划

## TL;DR

> **Quick Summary**: 在 A1 前端 seed_selector 之前插入冲动卡层（8+1 卡、主+次多选、可跳过），按型分组种子、怀旧上传包装、疗愈种子直达，并从零建 localStorage 埋点三项（含导出回收）。前置 D9 闸门清零并入本计划第一波。**零后端改动（硬约束）**。
>
> **Deliverables**:
> - D9 闸门清零（tsc 0 错误 + vitest 全绿 + Playwright 独立可跑）
> - 冲动卡 8+1 屏（新组件文件，含 skip 常驻、主+次多选）
> - 8+1 张卡场景意象文案 + R3/R4/D5/禁功能词审查清单（交产品方裁决）
> - 类型→种子分组映射（前端侧，按名称运行时匹配）
> - custom_idea 引导语中文化（含 E0 诚实框架）
> - 怀旧型：卡片→直达上传 + "它认出了你的世界"预填确认页（含零预填诚实降级文案）
> - 疗愈型：卡片→破晓之剑（seed_id=7）种子直达 + 陪伴引导语
> - 埋点三项（跳过率/完成度/自报-行为错位地图）localStorage 事件日志 + 导出 JSON 按钮（含 R1 对照组指标预置）
> - Playwright E2E 验收套件（9 卡路由 + skip + 三条既有路径回归）
>
> **Estimated Effort**: Medium（D9 ≤1 天 + E0 1-2 天，按 spec §10）
> **Parallel Execution**: YES - 5 波（Wave 0 闸门 → Wave 1 三件并行 → Wave 2 两件并行 → Wave 3 串行 wiring → Wave 4 QA → FINAL 四审）
> **Critical Path**: T1(D9) → T2(文案配置) → T5(卡片UI) → T7(wiring) → T8(E2E) → F1-F4

---

## Context

### Original Request
用户指令（2026-09-20）："根据 H:\UGC\docs\plans\2026-09-18-impulse-entry-system-spec.md，开始计划 e0"——为已冻结规格书 v1.2（D12/D13）的 E0 阶段生成正式工作计划。

### Interview Summary
**Key Discussions**:
- D9 闸门并入本计划：用户裁决 **①A**（作为第一波任务，D9 完成即 E0 解锁）
- 埋点回收通道：用户裁决 **②A**（localStorage 事件日志 + 导出 JSON 按钮，外测员手动回传，对齐 D8）
- 冲动卡文案：用户裁决 **③A**（计划内新撰 + 审查清单交产品方裁决后接 UI）
- 多选交互：默认接受（spec §2 方法论修正"主冲动 1 + 次冲动 0-1 多选，禁单选贴标签"；完成度埋点"选卡数"需要）

**Research Findings**（探索代理 + 直查取证）:
- 前端状态机：`WorkspaceState = 'seed_selector' | 'guided_chat' | 'graph_view'`（A1Workspace.tsx:261）；插入 `'impulse_cards'` 前置态，接线点仅 3 处（类型 :261 / lazy initializer :281-297 / render dispatch :1364-1366）
- `startSession(seedId?, customIdeaText?)`（:494-540）POST `/api/a1/session/start`，body `{ user_id, seed_id?, custom_idea? }`——冲动卡复用此通道，零后端
- 种子目录：8 个预设全在（id 1-8 整数），§5.2 推荐**零缺员**；种子无类型元数据 → 分组必须前端侧映射
- 上传链：UploadToolbar → handleFileUpload（:841-886）→ parsed → handleUploadSuccess（:889-927）→ **直接进 guided_chat**，无独立确认页
- **前端零遥测**（sendBeacon/analytics/track 全零命中）——埋点从零建
- 冲动卡 v0.1 完整文案**从未入 git，不可恢复**——必须新撰
- 存量失败（D9 范围）：tsc 16 基线错误、useTypewriter 6 失败、vitest 全量收集 Playwright spec 需排除

### Metis Review
**Identified Gaps**（已全部处置）:
- A1Workspace.tsx 单体并行冲突 → 全部新逻辑落新文件，A1Workspace 修改收敛为**单一串行 wiring 任务**（T7，diff <100 行）
- 怀旧零预填时"它认出了你的世界"= 不诚实文案 → 必须有零字段降级文案（诚实纪律，T6 内强制）
- 遥测回收现实约束（手动导出难以达 ≥100 样本/卡）→ 计划内明示：E0 数据为方向性（<500 样本纪律），完整统计靠 E1+
- 返回用户劫持风险 → impulse_cards 态**不持久化**，仅无存量状态的新用户默认落入
- a1_return_intent 优先级高于卡片默认（既有回退路径不破坏）
- §5.2"设定-重度 E0=种子详情页"与 §10 范围表不一致 → **默认不纳入**（§10 为落地分期权威），标记 DECISION NEEDED 待产品方
- useTypewriter 修/删 → 默认**修**（行为保持），标记 DECISION NEEDED

---

## Work Objectives

### Core Objective
按 spec v1.2 §10 E0 行交付全部六项（冲动卡 8+1 / 种子分组 / custom_idea 引导语 / 怀旧上传包装 / 疗愈直达 / 埋点三项），零后端改动，D9 闸门先行清零。

### Concrete Deliverables
- 新文件：`frontend/src/pages/a1/impulse/ImpulseCards.tsx`、`impulseCards.config.ts`、`seedGrouping.ts`、`telemetry.ts`、`NostalgiaConfirmPage.tsx`、文案审查清单 `.sisyphus/evidence/task-2-copy-review-checklist.md`
- 修改文件：**仅** `A1Workspace.tsx`（wiring，<100 行 diff）+ D9 相关存量文件 + vitest 配置 + 新增 E2E 测试文件
- 既有三路径（种子直选 / 上传 / custom_idea）+ a1_return_intent 回退路径行为不变（回归验证）

### Definition of Done
- [ ] `cd frontend && npx tsc --noEmit` → 0 errors（D9 后保持）
- [ ] `cd frontend && npx vitest run` → 全绿（含既有 185+ 用例，无新失败）
- [ ] `cd frontend && npx playwright test` → 全绿（E2E 套件含新增 9 卡路由场景）
- [ ] `git diff --stat <本计划起点> -- backend/` → **空输出**（零后端铁证）
- [ ] 文案违禁词 grep 零命中 + 审查清单交付
- [ ] 埋点导出 JSON 可离线算出 R1 三指标（跳过率/完成度/错位对照）

### Must Have
- skip 控件在卡片屏常驻（D2-③：AI/问卷永不阻塞主路径），落点 = 现有 seed_selector 平铺视图
- 主冲动 1 + 次冲动 0-1 多选；次冲动不可与主冲动同卡（UI 禁用同卡重选）
- R1 对照组预置：`impulse_card_shown / impulse_card_selected / impulse_card_skipped / first_question_answered` 四事件齐备（选卡 vs 未选卡 → 首答完成率可离线计算）
- 错位地图数据：`module_completed` 事件（模块 done ratio 首达 ≥0.5 时每模块发一次）
- 零预填诚实降级：上传 parsed 后有效预填字段数为 0 时，确认页降级文案（不得使用"它认出了你的世界"）
- 返回用户保护：`a1_workspace_v1` 已有状态（guided_chat/graph_view/seed_selector）恢复时**不**落入卡片屏；`a1_return_intent` 优先级最高
- 种子分组按名称运行时匹配（fetch GET /api/a1/seeds 后按 name 匹配映射表），失配降级平铺 + console.warn，不阻塞
- 枚举逐字锁定（见 T2），sub-agent 任务描述中原样引用，不允许增删改写

### Must NOT Have (Guardrails)
- ❌ 任何 `backend/` 目录改动（每 Wave 末 `git diff --stat -- backend/` 断言空）
- ❌ 遥测发起任何网络请求（sendBeacon/fetch 上报均禁止——零后端 + D8 无登录双约束）
- ❌ Q2 动态追问 / Q3 投射题 / 推断包 / 语气锚点 / creator_profile / onboarding_quiz 正式分态（全部 E1）
- ❌ 年龄门 / content_guard / 危机词 / 时长提醒（E2+；E0 爱情卡只做文案纪律）
- ❌ 冲动坐标三件套任何落库/计算/聚合（E2 只看不判；E0 只记原始事件）
- ❌ 遥测看板 / 图表 / 聚合分析层（E0 只有 export JSON）
- ❌ A1Workspace.tsx 内做重构/重排格式/提取既有代码（wiring 任务 diff <100 行）
- ❌ 修改门禁语义 / 35 字段 / MODULES 列表 / 任何后端契约
- ❌ 文案 A/B 多版本（E0 无 A/B 机制）
- ❌ 种子详情页（§5.2/§10 不一致，默认排除，待 DECISION 1 裁决）
- ❌ localStorage 遥测加锁防多标签竞态（接受为已知限制并留档，防过度工程）

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed.
> 唯一计划外人工步骤：产品方对 8+1 文案的终审（③A 裁决流程）——文案以违禁词 grep + 审查清单走查代替"人工确认风格"类标准。

### Test Decision
- **Infrastructure exists**: YES（Vitest + Playwright + tsc，前端 185+ 单测基线）
- **Automated tests**: Tests-after（E0 = 文案级 UI 层；组件逻辑轻，Playwright E2E 为主验收 + 新纯函数模块配 Vitest 单测）
- **Framework**: vitest（单测）/ playwright（E2E）

### QA Policy
- 每任务附 agent 执行的 QA 场景（见各 TODO），证据存 `.sisyphus/evidence/task-{N}-{slug}.{ext}`
- **Frontend/UI**: Playwright —— 导航、点击、断言 DOM、截图
- **纯函数模块**（seedGrouping/telemetry）: Vitest 单测 + Node REPL 导入验证
- **命令验证**: bash 跑 tsc/vitest/playwright/git diff
- 每 Wave 末（T1/T4/T6/T7/T8 完成时）：`git diff --stat -- backend/` 输出为空

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 0（闸门，串行）:
└── T1: D9 清零——tsc 16 + useTypewriter 6 失败 + vitest 排除 e2e [unspecified-high]

Wave 1（三件并行，全部新文件，互不依赖）:
├── T2: 冲动卡配置 + 8+1 文案 + 审查清单 [writing]
├── T3: 埋点工具 telemetry.ts（schema/存储/导出） [quick]
└── T4: 种子分组映射 seedGrouping.ts [quick]

Wave 2（两件并行，消费 Wave 1 接口）:
├── T5: ImpulseCards 卡片屏组件 [visual-engineering]（依赖 T2/T3/T4）
└── T6: NostalgiaConfirmPage 预填确认页组件 [visual-engineering]（依赖 T2 文案纪律/T3）

Wave 3（串行 wiring，唯一触碰 A1Workspace.tsx 的任务）:
└── T7: A1Workspace 接线（状态机三处 + custom_idea 文案 + 上传确认页插入 + 首答/模块完成埋点） [deep]（依赖 T5/T6）

Wave 4（验收）:
└── T8: Playwright E2E 套件（9 卡路由 + skip + 回归 + 埋点导出验证） [unspecified-high]（依赖 T7）

Wave FINAL（四审并行 → 用户终审）:
├── F1: 计划合规审计 [oracle]
├── F2: 代码质量审查 [unspecified-high]
├── F3: 真实手动 QA（Playwright 全场景重放） [unspecified-high]
└── F4: 范围忠实检查 [deep]
→ 呈交结果 → 用户明确 okay 后才算完成

Critical Path: T1 → T2 → T5 → T7 → T8 → F1-F4 → user okay
Max Concurrent: 3（Wave 1）
```

### Dependency Matrix

| 任务 | 依赖 | 被依赖（下游） |
|---|---|---|
| T1 | — | T2-T8, F1-F4 |
| T2 | T1 | T5, T6, T7 |
| T3 | T1 | T5, T6, T7 |
| T4 | T1 | T5 |
| T5 | T2, T3, T4 | T7 |
| T6 | T2, T3 | T7 |
| T7 | T5, T6 | T8 |
| T8 | T7 | F1-F4 |
| F1-F4 | T8（及全部） | user okay |

### Agent Dispatch Summary

- **Wave 0**: 1 —— T1 → `unspecified-high`
- **Wave 1**: 3 —— T2 → `writing`，T3 → `quick`，T4 → `quick`
- **Wave 2**: 2 —— T5 → `visual-engineering`，T6 → `visual-engineering`
- **Wave 3**: 1 —— T7 → `deep`
- **Wave 4**: 1 —— T8 → `unspecified-high`
- **FINAL**: 4 —— F1 → `oracle`，F2 → `unspecified-high`，F3 → `unspecified-high`（+playwright skill），F4 → `deep`

---

## TODOs

- [x] 1. D9 闸门清零（tsc 16 + 存量测试失败 + vitest 排除 e2e）

  **What to do**:
  - 运行 `cd frontend && npx tsc --noEmit`，收集全部 16 个基线错误，逐个修复（行为保持——只修类型不改变运行时逻辑；若个别错误源于已死代码路径，优先最小类型修复而非删除）
  - 运行 `cd frontend && npx vitest run`，定位 useTypewriter 6 个失败用例并修复（**默认裁决：修而非删**——行为保持优先；仅当某用例断言的是确证已死行为时才可删，须在证据中留依据）[DECISION 2 待产品方，默认=修]
  - 修复 vitest 全量跑收集 Playwright spec 的问题：vitest 配置排除 `tests/e2e`（PROJECT_STATE 遗留问题第一条）——确认 `npx playwright test` 仍可独立运行
  - 时间盒 ≤1 天（D9 纪律）：若某错误修复超时/爆炸半径过大，停下留档并在任务输出中标注升级，**不得**为绿灯而删测试或加 `@ts-ignore`/`as any`

  **Must NOT do**:
  - 不得用 `@ts-ignore`、`as any`、`eslint-disable`、跳过测试（skip/test.skip）等方式"清零"
  - 不得动 backend/（零后端从 Wave 0 即生效）
  - 不得顺手重构无关代码

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`（存量债调试需要判断力与耐心，非模板化工作）
  - **Skills**: [`systematic-debugging`]（逐错误归因而非盲改）

  **Parallelization**:
  - **Can Run In Parallel**: NO（一切的前置）
  - **Blocks**: T2, T3, T4, T5, T6, T7, T8, F1-F4
  - **Blocked By**: None

  **References**:
  - `PROJECT_STATE.md` 遗留问题节——三条存量失败的确切描述（useTypewriter 前序遗留 / vitest 收集 e2e / tsc 16）
  - `frontend/src/hooks/useTypewriter*`（或组件内 hook）——6 个失败用例所在
  - `frontend/vitest.config.ts` / `frontend/vite.config.ts`——排除 glob 的落点
  - `docs/decision-log.md` D9——闸门定义原文

  **Acceptance Criteria**:
  - [ ] `npx tsc --noEmit` → 0 errors
  - [ ] `npx vitest run` → 0 failed（0 skipped 新增）
  - [ ] `npx playwright test` → 可独立运行不报收集错误
  - [ ] `git diff --stat -- backend/` → 空

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: D9 三命令全绿
    Tool: Bash
    Preconditions: 工作区干净（git status 无未预期改动）
    Steps:
      1. cd frontend; npx tsc --noEmit; echo "tsc exit: $LASTEXITCODE"
      2. npx vitest run 2>&1 | Select-String "Test Files|Tests "
      3. git diff --stat -- ../backend/
    Expected Result: tsc exit 0；vitest "X passed | 0 failed"；git diff 输出为空
    Failure Indicators: 任一命令非零退出；vitest 出现 failed/skipped 计数；backend diff 非空
    Evidence: .sisyphus/evidence/task-1-d9-green.txt（三命令完整输出）

  Scenario: 失败路径——修复过程不得引入禁用手段
    Tool: Bash
    Preconditions: T1 已完成
    Steps:
      1. git diff <T1起点>..HEAD -- frontend/src | Select-String "@ts-ignore|as any|\.skip\(|eslint-disable"
    Expected Result: 0 命中
    Failure Indicators: 出现任一禁用模式
    Evidence: .sisyphus/evidence/task-1-no-suppression.txt
  ```

  **Commit**: YES
  - Message: `chore(frontend): clear D9 gate - tsc 0 errors, fix legacy test failures, exclude e2e from vitest`
  - Pre-commit: `npx tsc --noEmit && npx vitest run`

- [x] 2. 冲动卡配置 + 8+1 张场景意象文案 + 审查清单

  **What to do**:
  - 新建 `frontend/src/pages/a1/impulse/impulseCards.config.ts`，定义：
    - 类型枚举（**逐字锁定，不允许增删改写**）：`setting_heavy`(设定-重度) / `character_driven`(角色驱动线) / `plot`(剧情) / `philosophy`(哲理) / `exploration`(探索) / `romance`(爱情) / `nostalgia`(怀旧) / `healing`(疗愈) / `unsure`(说不清)
    - 每卡字段：`{ id: ImpulseTypeId, label: string, tagline: string }`——label = 卡片标题（≤6 字），tagline = 场景意象一句话（2-4 秒可读完，约 15-30 字）
    - 卡片顺序：8 型按 spec §2 顺序 + `unsure` 殿后（+1 位置固定最后，视觉弱化为"都不像？"式兜底入口）
  - **新撰 8+1 张卡文案**（v0.1 原文不可恢复，按以下纪律创作）：
    - **场景意象**：描述一个画面/冲动瞬间，不解释功能（剧情示例风格来自 spec §3.1："我推断开场适合【一个必须立刻做的抉择】"——卡片文案同风格：如剧情卡 tagline "我想看故事开场——一个必须立刻做的抉择"式）
    - **禁功能词**：不出现 AI/算法/推荐/测评/个性化/分析类词汇
    - **D5 共鸣**：第一人称冲动口吻（"我想…"式），用户看到即认领
    - **R3 言情框架（爱情卡）**：锚定"感情故事/言情叙事"——如"我想写一段感情故事，在某个世界里发酵"；**不得**任何暧昧擦边措辞
    - **R4 无诱导性承诺（疗愈卡）**：禁止"这里永远有人陪你/一直陪着你/最懂你"类措辞；用低压力中性表述——如"想轻松一会儿，不想答的都可以跳过"
    - **说不清卡**：宽恕式措辞（备忘 §7 社会期许偏差缓解）——如"说不清？先聊聊你世界里发生的事"
    - **E1 诚实框架（R1 缓解）**：卡片屏顶部引导语明示"帮我们了解你"（如"先告诉我，你为什么想创造一个世界？"），不伪装个性化承诺
  - 新建审查清单文档 `.sisyphus/evidence/task-2-copy-review-checklist.md`：五节（场景意象/禁功能词/D5 共鸣/R3 言情框架/R4 无诱导承诺）× 9 卡逐卡走查表 + 违禁词 grep 命令与预期结果——**交产品方终审（计划外人工步骤，③A 裁决流程）**
  - 同文件导出卡片屏引导语常量（`IMPULSE_SCREEN_INTRO`，供 T5 消费）

  **Must NOT do**:
  - 不得写 A/B 多版本；不得为 Q2 题库写文案（E1）
  - 不得出现违禁词清单内任何词（见 QA）
  - 不得改动既有文件（本任务只新建 config + 清单文档）

  **Recommended Agent Profile**:
  - **Category**: `writing`（创意文案 + 纪律约束下的写作）
  - **Skills**: []（无匹配技能；纪律全部内置于任务描述）

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 T3、T4 同 Wave）
  - **Parallel Group**: Wave 1（with T3, T4）
  - **Blocks**: T5, T6, T7
  - **Blocked By**: T1

  **References**:
  - `docs/plans/2026-09-18-impulse-entry-system-spec.md` §3.1（推断包示例的文案语感）、§2（分类学与学术背书——每型兴奋点）、§4 铁律 6/7（具体意象/三值信号）、§12.1.3 R3、§12.1.4 R4（两卡专属纪律详释）
  - `docs/plans/2026-09-20-动机规模调研备忘.md` §7（宽恕式措辞、社会期许偏差）、§5（各型卡片钩子——文案需让该型用户"认领"）
  - `docs/decision-log.md` D5（共鸣原则）、D12（言情叙事化硬约束）
  - 类型顺序与命名依据：spec §2（8 冲动型定义）+ §5.2（v1.2 通用线行）

  **Acceptance Criteria**:
  - [ ] `impulseCards.config.ts` 存在且导出 9 卡配置 + 枚举 + 屏幕引导语常量
  - [ ] `npx tsc --noEmit` 通过（新文件零类型错误）
  - [ ] 违禁词 grep 零命中（见 QA）
  - [ ] 审查清单文档交付（9 卡 × 5 节走查表完整）

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 违禁词零命中（可执行文案纪律）
    Tool: Bash
    Preconditions: impulseCards.config.ts 已提交
    Steps:
      1. Select-String -Path frontend/src/pages/a1/impulse/impulseCards.config.ts -Pattern "永远有人陪|一直陪你|最懂你|智能推荐|个性化推荐|AI 测评|算法分析|精准匹配|AI 为你"
      2. Select-String -Path frontend/src/pages/a1/impulse/impulseCards.config.ts -Pattern " erotik|色情|擦边"
    Expected Result: 两组均 0 命中
    Failure Indicators: 任何命中行
    Evidence: .sisyphus/evidence/task-2-forbidden-words-zero.txt

  Scenario: 枚举完整性
    Tool: Bash (node)
    Preconditions: 同上
    Steps:
      1. node -e "const c = require('./frontend/src/pages/a1/impulse/impulseCards.config.ts')" 或经 vitest 单测断言：
         9 个 id 逐字等于 [setting_heavy, character_driven, plot, philosophy, exploration, romance, nostalgia, healing, unsure]；每卡 label ≤6 字、tagline 15-30 字；unsure 位于数组末位
    Expected Result: 断言全过（写成 vitest 单测文件 frontend/src/pages/a1/impulse/__tests__/impulseCards.config.test.ts）
    Failure Indicators: 枚举增删、顺序错、长度越界
    Evidence: .sisyphus/evidence/task-2-config-test.txt（vitest 输出）

  Scenario: 失败路径——爱情卡/疗愈卡专项纪律走查
    Tool: Read（人工代理走查，输出到清单）
    Steps:
      1. 读 romance 卡 tagline，对照 R3：是否锚定"感情故事"框架、是否无暧昧措辞
      2. 读 healing 卡 tagline，对照 R4：是否无陪伴承诺、是否低压力
      3. 结果逐条写入 task-2-copy-review-checklist.md 对应行
    Expected Result: 两卡走查结论 PASS；任何 FAIL 项回修文案后重查
    Evidence: .sisyphus/evidence/task-2-copy-review-checklist.md
  ```

  **Commit**: YES
  - Message: `feat(a1-entry): impulse card config with 8+1 scene-imagery copy + review checklist`
  - Files: `frontend/src/pages/a1/impulse/impulseCards.config.ts`、`frontend/src/pages/a1/impulse/__tests__/impulseCards.config.test.ts`、`.sisyphus/evidence/task-2-copy-review-checklist.md`
  - Pre-commit: `npx tsc --noEmit && npx vitest run`

- [x] 3. 埋点工具 telemetry.ts（localStorage 事件日志 + 导出）

  **What to do**:
  - 新建 `frontend/src/pages/a1/impulse/telemetry.ts`，实现（**接口签名逐字锁定，T5/T6/T7 消费时不得改**）：
    ```ts
    export type ImpulseTelemetryEventName =
      | 'impulse_card_shown'        // 卡片屏曝光（R1 对照组分母）
      | 'impulse_card_selected'     // 选卡完成 { primary, secondary: string | null }
      | 'impulse_card_skipped'      // 跳过（R1 对照组 + 备忘"跳过率"指标）
      | 'first_question_answered'   // 首问作答 { elapsed_ms }（R1：卡片→首问完成率分子）
      | 'module_completed';         // 模块完成 { module_id }（错位地图：首完成模块）
    export interface ImpulseTelemetryEvent {
      schema_version: 1;
      event: ImpulseTelemetryEventName;
      ts: number;            // Date.now()
      user_id: string;       // localStorage 'user_id' 现有键（本地标识非身份，D8）
      session_id?: string;   // a1 会话 id（可得时）
      data?: Record<string, unknown>;
    }
    export function logImpulseEvent(event: ImpulseTelemetryEventName, data?: Record<string, unknown>): void;
    export function exportImpulseTelemetry(): void;  // Blob 下载 a1-telemetry-{YYYYMMDD-HHmm}.json，内容=存储全量，导出后不清空
    export function getImpulseTelemetry(): ImpulseTelemetryEvent[];  // 测试/导出共用读取
    ```
  - 存储规则：localStorage 键 `a1_telemetry_v1`（键名逐字锁定）；JSON 数组追加写；**FIFO 容量上限 500 条**（超出丢最旧）；损坏/缺失时重置为空数组（store 备份轮转同款容错精神）
  - `module_completed` 触发语义（供 T7 消费）：模块 done ratio **首次** ≥0.5 时每模块发一次（去重：同 session 同模块只发一次）
  - **零网络**：本模块不得 import fetch 封装、不得 sendBeacon、不得任何 XHR
  - 配套 Vitest 单测：追加/上限 FIFO/损坏恢复/导出内容=存储内容/schema_version 恒为 1

  **Must NOT do**:
  - 不得发起任何网络请求；不得收集 PII（答案内容、上传文本均不得入 data）
  - 不得做聚合/统计/图表层（离线人工分析，E0 边界）

  **Recommended Agent Profile**:
  - **Category**: `quick`（单文件纯函数工具 + 单测，接口已逐字给定）
  - **Skills**: [`test-driven-development`]（接口锁定，先写测试最稳）

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 T2、T4 同 Wave）
  - **Parallel Group**: Wave 1（with T2, T4）
  - **Blocks**: T5, T6, T7
  - **Blocked By**: T1

  **References**:
  - `docs/plans/2026-09-20-动机规模调研备忘.md` §6 层2——三项埋点的语义定义（跳过率=信号非误差/完成度=选卡数/错位地图=卡片vs首完成模块交叉）
  - `docs/plans/2026-09-18-impulse-entry-system-spec.md` §12.1.7 立即行动②——R1 对照组指标预置（本任务是其数据层实现）
  - 现有 localStorage 键惯例：`a1_workspace_v1` / `a1_return_intent` / `user_id`（A1Workspace.tsx:273/298——命名与容错风格对齐）
  - 后端门禁阈值 0.5 语义：`FINALIZE_MODULE_THRESHOLD=0.5`（spec §1.2——module_completed 的 0.5 阈值与之对齐）

  **Acceptance Criteria**:
  - [ ] `telemetry.ts` + 单测文件存在，`npx vitest run` 全绿
  - [ ] 单测覆盖：5 事件名类型化、FIFO 500、损坏重置、导出=存储、schema_version=1

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 事件写入与读取（happy path）
    Tool: Bash (node/vitest)
    Preconditions: telemetry.ts 已实现
    Steps:
      1. vitest 单测：logImpulseEvent('impulse_card_selected', { primary: 'plot', secondary: null }) 后 getImpulseTelemetry() 长度 1，字段逐字断言（schema_version/event/ts/user_id/data）
    Expected Result: 断言通过
    Evidence: .sisyphus/evidence/task-3-vitest.txt

  Scenario: FIFO 上限与损坏恢复（edge）
    Tool: vitest
    Steps:
      1. 写入 502 条 → 读取长度 = 500 且首条为第 3 条
      2. 手动 setItem('a1_telemetry_v1', 'not-json') → logImpulseEvent 正常追加不抛错，长度 = 1
    Expected Result: 两断言通过
    Evidence: .sisyphus/evidence/task-3-fifo-corruption.txt

  Scenario: 零网络铁律（failure 路径）
    Tool: Bash
    Steps:
      1. Select-String -Path frontend/src/pages/a1/impulse/telemetry.ts -Pattern "fetch|sendBeacon|XMLHttpRequest|axios"
    Expected Result: 0 命中
    Failure Indicators: 任何网络 API 出现
    Evidence: .sisyphus/evidence/task-3-zero-network.txt
  ```

  **Commit**: YES
  - Message: `feat(a1-entry): localStorage telemetry utility with schema v1 + JSON export`
  - Pre-commit: `npx tsc --noEmit && npx vitest run`

- [x] 4. 种子分组映射 seedGrouping.ts

  **What to do**:
  - 新建 `frontend/src/pages/a1/impulse/seedGrouping.ts`：
    ```ts
    export const TYPE_SEED_NAMES: Record<ImpulseTypeId, string[]> = {
      setting_heavy:   ['群星彼岸', '碎天录'],        // spec §5.2 设定-重度行
      character_driven:['破晓之剑', '鸩酒与玫瑰'],    // 角色驱动线行
      plot:            ['霓虹窃案', '鸩酒与玫瑰'],    // 剧情行
      philosophy:      ['深渊低语', '灰烬之路'],      // 哲理行
      exploration:     ['腐化深渊', '灰烬之路'],      // 探索行
      romance:         ['鸩酒与玫瑰', '群星彼岸'],    // 爱情行
      nostalgia:       [],                            // 怀旧 = 直达上传，不走种子
      healing:         ['破晓之剑'],                  // 疗愈 = 种子直达
      unsure:          ['霓虹窃案', '鸩酒与玫瑰'],    // 通用线：故事侧优先展示（D13）
    };
    export function groupSeedsByType(seeds: Seed[], type: ImpulseTypeId): { matched: Seed[]; rest: Seed[]; degraded: boolean };
    ```
  - 匹配规则：按 **name 精确匹配**（运行时 fetch 的 seeds 列表 vs 映射表名称，名称逐字来自 preset_loader.py 已取证名单）；`matched` = 该型推荐且在返回列表中（按映射表顺序），`rest` = 其余种子；**任一推荐名未命中 → degraded=true + console.warn（列出失配名），不抛错不阻塞**
  - 说不清（unsure）特殊语义：`matched` = 故事侧种子（映射表已列），分组视图将 matched 置于最前（故事侧优先，依据 D13 通用线行）
  - 配套 Vitest 单测：9 型映射完整性、部分失配降级、全失配降级（matched 空 + degraded true）、顺序保持

  **Must NOT do**:
  - 不得硬编码 seed id→type（必须名称匹配，防后端 id 变动）
  - 不得改后端 / 不得给后端种子加 type 字段
  - 不得修改 `Seed` 类型定义（消费 frontend 现有类型）

  **Recommended Agent Profile**:
  - **Category**: `quick`（单文件纯函数 + 单测，映射表逐字给定）
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 T2、T3 同 Wave）
  - **Parallel Group**: Wave 1（with T2, T3）
  - **Blocks**: T5
  - **Blocked By**: T1（T2 的枚举类型在此消费——若 T2 未完成则先以枚举字符串字面量对齐，T5 前必须收敛）

  **References**:
  - `backend/app/domains/creation/seed/preset_loader.py:47-104`——8 种子权威名单（id 1-8 整数：深渊低语/霓虹窃案/腐化深渊/灰烬之路/碎天录/群星彼岸/破晓之剑/鸩酒与玫瑰）
  - `docs/plans/2026-09-18-impulse-entry-system-spec.md` §5.2 路由表"种子推荐"列——映射表逐行出处
  - `frontend/src/pages/a1/A1Workspace.tsx:23-29`——`Seed` 类型消费（id/name/genre/description/dimension_defaults）
  - `docs/decision-log.md` D13——通用线故事侧优先的裁决依据

  **Acceptance Criteria**:
  - [ ] `seedGrouping.ts` + 单测存在，vitest 全绿
  - [ ] 单测断言 9 型映射与名称逐字一致（防拼写漂移）

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 9 型分组正确（happy path）
    Tool: vitest
    Preconditions: 用 preset_loader 真名构造 8 个 Seed 输入
    Steps:
      1. groupSeedsByType(seeds, 'plot') → matched = [霓虹窃案, 鸩酒与玫瑰]，rest = 其余 6 个，degraded = false
      2. groupSeedsByType(seeds, 'healing') → matched = [破晓之剑]
      3. groupSeedsByType(seeds, 'unsure') → matched 首位 = 霓虹窃案
    Expected Result: 断言通过
    Evidence: .sisyphus/evidence/task-4-grouping-test.txt

  Scenario: 名称失配降级（edge）
    Tool: vitest
    Steps:
      1. 构造 seeds 列表缺失 '鸩酒与玫瑰' → groupSeedsByType(seeds, 'plot') → matched = [霓虹窃案]，degraded = true，不抛错
      2. 构造空列表 → matched = []，degraded = true，不抛错
    Expected Result: 优雅降级，console.warn 被调用
    Evidence: .sisyphus/evidence/task-4-degraded-test.txt
  ```

  **Commit**: YES
  - Message: `feat(a1-entry): type-to-seed grouping map (name-matched, graceful fallback)`
  - Pre-commit: `npx tsc --noEmit && npx vitest run`

- [x] 5. ImpulseCards 卡片屏组件（多选 + skip 常驻）

  **What to do**:
  - 新建 `frontend/src/pages/a1/impulse/ImpulseCards.tsx`——纯展示+交互组件，**不 import A1Workspace 任何内部状态**，通过 props 与外界通信：
    ```ts
    interface ImpulseCardsProps {
      seeds: Seed[];                       // 由父级传入（fetch 结果）
      onCardCommit: (selection: { primary: ImpulseTypeId; secondary: ImpulseTypeId | null }) => void;
      onSkip: () => void;                  // 跳过 → 父级决定落点（wiring = seed_selector）
    }
    ```
  - 交互规则：
    - 首次点击任意卡 = 主冲动（选中态高亮）；再点另一卡 = 次冲动（最多 1 个，第二选中态）；**点击已选中卡 = 取消该选中**；**主卡不可与次卡同卡**（同卡二重点击即取消，不升级为次选）
    - 确认按钮文案如"就这样，开始"——主冲动已选时可用；无选中时禁用
    - **skip 控件常驻**（D2-③）：文案如"跳过，直接开始"——始终可见可点，点击即 onSkip
    - 顶部引导语 = `IMPULSE_SCREEN_INTRO`（T2 产出，诚实框架"帮我们了解你"）
  - 卡片布局：8 卡网格 + `unsure` 卡独立一行兜底（视觉弱化）；选中卡用现有 glass-card 风格 + 令牌色描边（对齐 Tailwind v4 令牌，禁一次性色值）
  - **页脚埋点导出入口（位置定死，不许自由发挥）**：卡片屏页脚低调放"导出使用数据"文字按钮 → `exportImpulseTelemetry()`（测试员工具，视觉弱化不打扰真实用户；导出不清空）
  - 卡片屏挂载时 `logImpulseEvent('impulse_card_shown')`；确认时 `logImpulseEvent('impulse_card_selected', { primary, secondary })`；跳过时 `logImpulseEvent('impulse_card_skipped')`
  - 各卡类型的行为差异（卡片屏内完成，路由动作经 onCardCommit 由 wiring 决定）：
    - 怀旧卡确认 → wiring 层聚焦上传入口（T7 接线）；卡片屏本身不感知上传细节
    - 疗愈卡确认 → wiring 层直达种子（T7）；同理
    - 其余型确认 → wiring 层展示该型种子分组视图（T7）
  - 组件级 Vitest（@testing-library/react）：渲染 9 卡、主+次选择状态机、同卡取消、skip 可达、unsure 殿后

  **Must NOT do**:
  - 不得修改 A1Workspace.tsx（wiring 归 T7）
  - 不得在组件内 fetch /api/a1/seeds（seeds 由 props 传入）
  - 不得实现 Q2 追问 / 推断包 / 年龄门（E1+）
  - 不得引入新依赖库

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`（前端 UI 组件 + 交互状态机）
  - **Skills**: [`frontend-ui-ux`]（卡片视觉与选中态需要设计判断）

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 T6 同 Wave，二者互不依赖）
  - **Parallel Group**: Wave 2（with T6）
  - **Blocks**: T7
  - **Blocked By**: T2, T3, T4

  **References**:
  - `frontend/src/pages/a1/A1Workspace.tsx:984-1062`——现有 seed_selector 卡片网格的样式基准（glass-card、网格布局——新组件视觉对齐）
  - `frontend/src/pages/a1/A1Workspace.tsx:1004-1019`——卡片点击交互惯例
  - `impulseCards.config.ts`（T2）——9 卡数据源与引导语
  - `telemetry.ts`（T3）——三事件 API
  - `seedGrouping.ts`（T4）——分组数据源（本组件可选用显示推荐种子预览，最小实现可不显示）
  - `docs/plans/2026-09-18-impulse-entry-system-spec.md` §4 铁律 1（≤4 问、2-4 秒可答）——卡片屏一屏完成不翻页
  - P2 视觉原则（decision-log）——每屏最多一个魔法时刻；令牌制

  **Acceptance Criteria**:
  - [ ] 组件 + Vitest 全绿；tsc 零错误
  - [ ] 9 卡渲染、主+次状态机、同卡互斥、skip 常驻断言通过

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 主+次选择状态机（happy path）
    Tool: vitest (@testing-library/react)
    Preconditions: 渲染 <ImpulseCards seeds={8真实名Seed} onCardCommit={jest.fn()} onSkip={jest.fn()} />
    Steps:
      1. 点击"剧情"卡 → 断言 data-selected="primary"
      2. 点击"爱情"卡 → 断言"剧情"=primary 且"爱情"=secondary
      3. 再点击"爱情"卡 → secondary 取消，primary 不变
      4. 再点击"剧情"卡 → 全部取消
      5. 仅选主卡时点击确认按钮 → onCardCommit({ primary: 'plot', secondary: null }) 被调用
    Expected Result: 状态机断言全过
    Failure Indicators: 同卡被选为 primary+secondary；无主选时确认可点
    Evidence: .sisyphus/evidence/task-5-select-machine.txt

  Scenario: skip 常驻可达（D2-③）
    Tool: vitest
    Steps:
      1. 渲染后不选任何卡 → 断言 skip 按钮存在于 DOM 且 enabled
      2. 点击 skip → onSkip 被调用 + logImpulseEvent('impulse_card_skipped') 已写入 localStorage
    Expected Result: 两断言通过
    Evidence: .sisyphus/evidence/task-5-skip-always.txt

  Scenario: unsure 卡兜底位置（edge）
    Tool: vitest
    Steps:
      1. 断言"说不清"卡是第 9 张且渲染于独立兜底行（data-slot="fallback"）
    Expected Result: 通过
    Evidence: .sisyphus/evidence/task-5-unsure-position.txt
  ```

  **Commit**: YES
  - Message: `feat(a1-entry): ImpulseCards screen component (multi-select + skip)`
  - Pre-commit: `npx tsc --noEmit && npx vitest run`

- [x] 6. NostalgiaConfirmPage 预填确认页组件（含零预填诚实降级）

  **What to do**:
  - 新建 `frontend/src/pages/a1/impulse/NostalgiaConfirmPage.tsx`——纯展示组件，props：
    ```ts
    interface NostalgiaConfirmPageProps {
      prefillCount: number;              // 有效预填字段数（非空非占位）
      seedName: string;                  // 上传文件名（现有 handleUploadSuccess 伪 seedInfo.name 同源）
      onContinue: () => void;            // 继续进入访谈
    }
    ```
  - 文案规则（**诚实纪律为本任务核心**）：
    - prefillCount > 0：标题"它认出了你的世界"（spec §8.2 逐字）+ 副文案展示"认出了 N 处设定"（N = prefillCount）
    - **prefillCount === 0：降级文案**——标题不得使用"它认出了你的世界"（零字段时 = 不诚实，违反三铁律之诚实 + R1 精神）；降级为如"我们读完了你的文档"+ 引导"让我们在访谈里一起聊出这个世界"——**降级是硬性要求，不是可选项**
    - 确认按钮"继续"→ onContinue
  - 挂载时 `logImpulseEvent` 不需要（该页属于上传链后段；是否补事件见 T7——本组件不发埋点，保持纯展示）
  - 组件级 Vitest：两分支文案断言（含 prefillCount=0 时"它认出了你的世界"**不出现**）

  **Must NOT do**:
  - 不得修改 A1Workspace.tsx / UploadToolbar.tsx（插入点归 T7）
  - 不得调用任何后端 API
  - prefillCount=0 时不得渲染"认出"类文案

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 T5 同 Wave）
  - **Parallel Group**: Wave 2（with T5）
  - **Blocks**: T7
  - **Blocked By**: T2（文案纪律参照）, T3（类型依赖——若 T3 未毕可先行以类型 stub，T7 前收敛）

  **References**:
  - `frontend/src/pages/a1/A1Workspace.tsx:889-927`——handleUploadSuccess：parsed 响应消费方式（answers/innovations/progressSections 计算）——**本组件的插入位置上下文**（T7 在此插入）
  - `frontend/src/pages/a1/A1Workspace.tsx:232-240`——UploadResponseParsed 结构（prefillCount 的数据来源：answers 中非占位值计数的现成口径需在 T7 对齐——组件只接收数字）
  - `docs/plans/2026-09-18-impulse-entry-system-spec.md` §8.2 怀旧行——"预填确认页'它认出了你的世界'（E0 即可，借现有上传链）"逐字出处
  - Metis 评审边缘⑥——零预填诚实降级的裁决来源（本任务 Must NOT do 第三条）

  **Acceptance Criteria**:
  - [ ] 组件 + Vitest 全绿（两分支）
  - [ ] prefillCount=0 时"它认出了你的世界"字符串零渲染（断言级，非走查级）

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 有预填确认页（happy path）
    Tool: vitest
    Steps:
      1. 渲染 <NostalgiaConfirmPage prefillCount={23} seedName="明华修仙.txt" onContinue={fn} />
      2. 断言文本含"它认出了你的世界"；断言含"23"；断言"继续"按钮点击 → fn 调用
    Expected Result: 通过
    Evidence: .sisyphus/evidence/task-6-prefill-page.txt

  Scenario: 零预填诚实降级（edge——本任务核心纪律）
    Tool: vitest
    Steps:
      1. 渲染 prefillCount={0}
      2. 断言文本不含"它认出了你的世界"；断言降级标题"我们读完了你的文档"出现；onContinue 仍可用
    Expected Result: 通过（降级文案生效且流程不阻断）
    Failure Indicators: "认出"字样在 0 预填分支出现
    Evidence: .sisyphus/evidence/task-6-zero-prefill-honesty.txt
  ```

  **Commit**: YES
  - Message: `feat(a1-entry): nostalgia prefill confirmation page with zero-prefill honesty fallback`
  - Pre-commit: `npx tsc --noEmit && npx vitest run`

- [x] 7. A1Workspace 接线（唯一触碰 A1Workspace.tsx 的任务）

  **What to do**:
  - 修改 `frontend/src/pages/a1/A1Workspace.tsx`，**改动收敛为六处、总 diff <100 行**：
    1. **状态机**（:261）：`WorkspaceState` 联合类型加 `'impulse_cards'`
    2. **lazy initializer**（:281-297）：默认分支改为——仅当**无持久化状态**（a1_workspace_v1 无值或解析失败）时返回 `'impulse_cards'`；既有分支零改动（**返回用户保护**：持久化为 seed_selector/guided_chat/graph_view 的用户照旧恢复；`a1_return_intent='chat'` 优先级最高不劫持；`'poster_view'`→`'graph_view'` 迁移保留）。**注意：`'impulse_cards'` 不持久化**——useEffect 保存时（:368-374）若当前态为 impulse_cards 则跳过保存或保存为 seed_selector 等价语义（选卡片屏刷新 = 重显卡片，E0 最简）
    3. **render dispatch**（:1364-1366）：加分支渲染 `<ImpulseCards seeds={seeds} onCardCommit={...} onSkip={() => setWorkspaceState('seed_selector')} />`
    4. **onCardCommit 路由**（新增回调，规则逐字）：
       - `nostalgia` → `setWorkspaceState('seed_selector')` 并聚焦/高亮上传入口（UploadToolbar 所在区域 scrollIntoView + 高亮描边；不自动弹文件选择器）
       - `healing` → 直接 `startSession('7')`（破晓之剑 seed_id=7，整数）+ 陪伴引导语（T2 配置中的 healing 引导文案以 toast/横幅展示）
       - 其余型（含 unsure）→ `setWorkspaceState('seed_selector')` 且种子列表按 `groupSeedsByType(seeds, type)` 排序（matched 置顶 + "为你推荐"分组标题；degraded 时平铺 + 不显示分组标题）
    5. **custom_idea 引导语**（:1029-1047）：中文重写——面板标题（如"或者，从一个念头开始"）、placeholder（如"用一句话描述你想创造的世界…"）、按钮（"开始"）；grep 断言旧英文串清除
    6. **上传确认页插入 + 埋点钩子**：
       - handleUploadSuccess（:889-927）：parsed 后**不直接** setWorkspaceState('guided_chat')——先计算 prefillCount（answers 中非空非占位值计数——与现有 finalize 门禁计数口径对齐，若已有现成函数则复用），渲染 `<NostalgiaConfirmPage prefillCount={n} seedName={filename} onContinue={原进入聊天逻辑} />`（新局部状态 `pendingUploadConfirm` 承载；确认后走原 handleUploadSuccess 后半段逻辑 + 进 chat）
       - **首答埋点**：既有发送用户答案的函数中，首次发送时 `logImpulseEvent('first_question_answered', { elapsed_ms: Date.now() - cardShownTs })`（cardShownTs 存 ref，卡片屏挂载时打点；仅本地状态不持久化）
       - **模块完成埋点**：progressSections 重算处，模块 done ratio 首达 ≥0.5 时 `logImpulseEvent('module_completed', { module_id })`（已发过的模块跳过——ref 记录 Set）
  - 接线完成后手工冒烟（Playwright 在 T8 全面覆盖，此处只做烟测）：新用户路径出卡片屏、老用户（预置 localStorage a1_workspace_v1='guided_chat'）不劫持

  **Must NOT do**:
  - **总 diff <100 行**（不含空行/纯新增行可放宽至 120，但必须能在 F2 复核说明）
  - 不得重构/重排/提取 A1Workspace 任何既有代码；不得改 startSession / handleFileUpload / handleUploadSuccess 的既有签名与既有调用点语义（handleUploadSuccess 内部插入确认页除外——对 UploadToolbar 的回调契约不变）
  - 不得动 guided_chat/graph_view 的既有渲染逻辑（除两个埋点钩子各一行级插入）
  - 不得动 backend/；不得改 Seed 类型；不得 fetch 新端点

  **Recommended Agent Profile**:
  - **Category**: `deep`（单体文件精确手术 + 多接线点 + 回归保护，责任最重）
  - **Skills**: [`systematic-debugging`]（回退路径验证需系统化）+ [`verification-before-completion`]

  **Parallelization**:
  - **Can Run In Parallel**: NO（串行——A1Workspace 唯一所有权）
  - **Blocks**: T8
  - **Blocked By**: T5, T6（组件就绪）；T2/T3/T4（消费其导出）

  **References**:
  - `frontend/src/pages/a1/A1Workspace.tsx:261`（类型联合）、`:281-297`（initializer——**逐行读懂三个既有分支再动手**）、`:368-374`（持久化保存）、`:494-540`（startSession 签名与 body 构造）、`:889-927`（handleUploadSuccess 全文）、`:1029-1047`（custom_idea 面板）、`:1364-1366`（dispatch）
  - `frontend/src/pages/a1/UploadToolbar.tsx`——上传入口 DOM（nostalgia 聚目标的）
  - T2/T3/T4/T5/T6 产出文件——全部消费接口
  - `docs/plans/2026-09-18-impulse-entry-system-spec.md` §11.1 接线清单①（插入点定义）、§5.2 疗愈行（破晓之剑直达）、§12.1.7 行动②（R1 对照埋点）
  - Metis 评审边缘①②③——返回用户/a1_return_intent/持久化语义三裁决（已内化于上文规则）

  **Acceptance Criteria**:
  - [ ] tsc/vitest 全绿（既有测试无一破坏）
  - [ ] `git diff --stat` 本任务对 A1Workspace.tsx 改动 <100 行（F2 复核）
  - [ ] 老用户（预置 localStorage）不劫持；a1_return_intent 路径原样
  - [ ] 旧英文 custom_idea 文案 grep 零命中

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 新用户全链（happy path）
    Tool: Playwright（playwright skill）
    Preconditions: 清空 localStorage；后端 uvicorn 运行
    Steps:
      1. goto http://localhost:5173/a1 → 断言卡片屏可见（data-testid="impulse-cards"）且 9 卡渲染
      2. 点"剧情"卡 → 点确认 → 断言进入种子页且"霓虹窃案"位于首位（推荐分组）
      3. localStorage.getItem('a1_telemetry_v1') 解析 → 含 impulse_card_shown 与 impulse_card_selected（primary=plot）
    Expected Result: 三断言通过；截图卡片屏
    Failure Indicators: 卡片屏未出现（劫持失败或持久化污染）；推荐序未变
    Evidence: .sisyphus/evidence/task-7-new-user-flow.png + task-7-telemetry-check.json

  Scenario: 老用户不被劫持（回归——Metis 边缘①②）
    Tool: Playwright
    Preconditions: localStorage 预置 a1_workspace_v1 = '{"workspaceState":"guided_chat",...}'（按实际存储结构构造）
    Steps:
      1. goto /a1 → 断言直接进入 guided_chat，卡片屏不出现
    Expected Result: 通过
    Evidence: .sisyphus/evidence/task-7-returning-user.png

  Scenario: 疗愈直达 + 怀旧路由（型特化）
    Tool: Playwright
    Steps:
      1. 清 localStorage → /a1 → 点"疗愈"卡 → 确认 → 断言发出 POST /api/a1/session/start 且 body 含 "seed_id":7（page.on('request') 拦截断言）→ 陪伴引导语可见
      2. 清 localStorage → /a1 → 点"怀旧"卡 → 确认 → 断言停在种子页且上传区高亮（data-testid 或 class 断言）
    Expected Result: 两型路由正确
    Evidence: .sisyphus/evidence/task-7-healing-nostalgia.png

  Scenario: 上传确认页 + 零预填降级（edge）
    Tool: Playwright
    Preconditions: 后端运行；准备一个含真实设定文本的 .txt 与一个近乎空白的 .txt
    Steps:
      1. 走上传链（有内容文件）→ 断言确认页出现"它认出了你的世界"与计数 → 点继续 → 进入访谈
      2. （若空白文件能产生 0 预填——按后端实际行为）断言降级标题"我们读完了你的文档"且无"认出"字样
    Expected Result: 两分支正确；流程不阻断
    Evidence: .sisyphus/evidence/task-7-upload-confirm.png

  Scenario: startSession 网络失败回退（failure）
    Tool: Playwright（route abort）
    Steps:
      1. 疗愈卡确认前 page.route('**/api/a1/session/start', { abort }) → 点确认 → 断言错误提示可见且回到可操作状态（不白屏）
    Expected Result: 优雅失败
    Evidence: .sisyphus/evidence/task-7-startsession-fail.png
  ```

  **Commit**: YES
  - Message: `feat(a1-entry): wire impulse_cards state into A1Workspace (entry + routes + telemetry hooks)`
  - Pre-commit: `npx tsc --noEmit && npx vitest run`

- [x] 8. Playwright E2E 验收套件（9 卡路由 + skip + 回归 + 埋点导出）

  **What to do**:
  - 新建 `frontend/tests/e2e/a1-impulse-entry.spec.ts`，覆盖：
    - **9 卡路由矩阵**：每型一张场景——8 型断言推荐分组序（matched 首位名称逐字断言）、nostalgia 断言上传区聚焦、healing 断言 seed_id=7 请求、unsure 断言故事侧首位（霓虹窃案）
    - **主+次多选 E2E**：选主+次后 telemetry 含 secondary 值
    - **skip 路径**：不选卡点跳过 → 落 seed_selector 平铺视图 → telemetry 含 impulse_card_skipped
    - **三条既有路径回归**：直接选种子（不经卡片确认按钮——经 skip 后）/ custom_idea 一句话开始（新中文文案断言）/ a1_return_intent 回退（预置键 → 直达 guided_chat）
    - **埋点导出**：操作若干事件后点导出按钮 → 断言下载触发且文件内容 = localStorage 内容（page.waitForEvent('download') + 读文件解析 JSON 断言 schema_version=1）
    - **R1 指标可计算性验证脚本**：新增 `frontend/scripts/verify-telemetry-metrics.mjs`（node 脚本）——输入导出 JSON，输出跳过率/选卡分布/首答完成率（选卡组 vs 跳过组）——用 Playwright 场景导出的真实文件跑通即证明"离线可算 R1 三指标"
  - E2E 需要后端运行（setup 脚本或 webServer 配置复用现有 Playwright 配置）

  **Must NOT do**:
  - 不得为让测试通过改产品代码（发现 bug 回 T5/T6/T7 修）
  - 不得删/改既有 e2e 用例（只加新的；既有用例若因接线破损，修复属于本任务但需留档说明）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`（E2E 编写 + 真实浏览器操作 + 调试）
  - **Skills**: [`playwright`]（浏览器自动化核心技能）

  **Parallelization**:
  - **Can Run In Parallel**: NO（依赖 T7 全部完成）
  - **Blocks**: F1-F4
  - **Blocked By**: T7

  **References**:
  - `frontend/tests/e2e/`——既有 e2e 用例风格与配置（T1 已确认 vitest 排除、playwright 独立跑）
  - T7 的五个 QA 场景——本任务是其实践化 + 全覆盖化（T7 烟测的正式版）
  - `docs/plans/2026-09-20-动机占比预测基线.md` §1——9 型分布预期（**验证脚本输出格式对齐该表口径**：第一冲动单一口径/选卡分布百分比——供外测员数据回传后对照）
  - `docs/plans/2026-09-20-动机规模调研备忘.md` §6 层2——三指标定义（脚本计算口径依据）

  **Acceptance Criteria**:
  - [ ] `npx playwright test` 全绿（含既有用例）
  - [ ] verify-telemetry-metrics.mjs 对导出文件输出三指标且数字自洽
  - [ ] 9 卡矩阵场景全部存在（spec 文件逐型 describe 块）

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 全套件绿（happy path）
    Tool: Bash
    Preconditions: 后端 uvicorn + 前端 dev server（或 Playwright webServer 自管）
    Steps:
      1. cd frontend; npx playwright test tests/e2e/a1-impulse-entry.spec.ts --reporter=line
    Expected Result: 全部 passed；失败数 0
    Evidence: .sisyphus/evidence/task-8-playwright-full.txt

  Scenario: R1 指标离线可算（核心验收）
    Tool: Bash (node)
    Preconditions: 已由 Playwright 场景导出 a1-telemetry-*.json 至已知路径
    Steps:
      1. node frontend/scripts/verify-telemetry-metrics.mjs <导出文件路径>
    Expected Result: stdout 输出跳过率 X%、选卡分布（9 型计数）、首答完成率（选卡组/跳过组分列）；无 NaN/异常
    Failure Indicators: 脚本报错；指标字段缺失
    Evidence: .sisyphus/evidence/task-8-metrics-script.txt

  Scenario: 既有用例零破坏（回归）
    Tool: Bash
    Steps:
      1. npx playwright test（全套件，不只新文件）
    Expected Result: 既有用例全过（或与 T1 基线完全一致，无新增失败）
    Evidence: .sisyphus/evidence/task-8-regression.txt
  ```

  **Commit**: YES
  - Message: `test(a1-entry): Playwright E2E for 9 card routes + skip + regressions + telemetry export`
  - Pre-commit: `npx tsc --noEmit && npx vitest run`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 个审查代理并行。ALL must APPROVE。呈交合并结果给用户，取得明确 "okay" 前不得标记完成。
> **不得在用户 okay 前勾选 F1-F4。** 拒绝或用户反馈 → 修复 → 重跑 → 再呈交 → 再等 okay。

- [x] F1. **Plan Compliance Audit** — `oracle`
  通读本计划。逐条核对 "Must Have"：实现存在性（读文件/跑命令/curl）。逐条核对 "Must NOT Have"：全仓搜索禁止模式——命中即 REJECT 并给出 file:line。核对 `.sisyphus/evidence/` 证据文件齐全。对照 deliverables 清单。
  输出：`Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  跑 `npx tsc --noEmit`（0 错误）+ `npx vitest run`（全绿）+ `npx playwright test`（全绿）。审查全部改动文件：`as any`/`@ts-ignore`、空 catch、prod 代码 console.log（console.warn 降级路径允许）、注释掉的代码、未用 import。AI slop 检查：过度注释、过度抽象、泛型命名（data/result/item/temp）。A1Workspace.tsx diff 行数复核（<100）。
  输出：`Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`（+ `playwright` skill）
  从干净状态起（清 localStorage）。执行**每个任务的每个 QA 场景**——按确切步骤走、捕获证据。跨任务集成测试：冲动卡→种子→访谈→上传→确认页全链。边缘用例：跳过、刷新中断、零预填、seeds 接口失败模拟（route abort）、双开标签页。存 `.sisyphus/evidence/final-qa/`。
  输出：`Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  逐任务：读 "What to do"，读实际 diff（git log/diff）。验证 1:1——规格内全做了（无遗漏）、规格外的没做（无蔓延）。核对 "Must NOT do" 合规。跨任务污染检查：T2-T6 是否越界改了 A1Workspace.tsx。未入账改动清点（`git status` 逐文件核对）。
  输出：`Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **T1**: `chore(frontend): clear D9 gate - tsc 0 errors, fix legacy test failures, exclude e2e from vitest`
- **T2**: `feat(a1-entry): impulse card config with 8+1 scene-imagery copy + review checklist`
- **T3**: `feat(a1-entry): localStorage telemetry utility with schema v1 + JSON export`
- **T4**: `feat(a1-entry): type-to-seed grouping map (name-matched, graceful fallback)`
- **T5**: `feat(a1-entry): ImpulseCards screen component (multi-select + skip)`
- **T6**: `feat(a1-entry): nostalgia prefill confirmation page with zero-prefill honesty fallback`
- **T7**: `feat(a1-entry): wire impulse_cards state into A1Workspace (entry + routes + telemetry hooks)`
- **T8**: `test(a1-entry): Playwright E2E for 9 card routes + skip + regressions + telemetry export`
- 每个 commit 前：`npx tsc --noEmit && npx vitest run` 必须通过（T1 之后）

---

## Success Criteria

### Verification Commands
```bash
cd frontend && npx tsc --noEmit          # Expected: 0 errors
cd frontend && npx vitest run            # Expected: all pass, 0 failed
cd frontend && npx playwright test       # Expected: all pass
git diff --stat <base> -- backend/       # Expected: empty output
# 文案违禁词（在 frontend/src/pages/a1/impulse/ 下）:
#   Select-String -Path ... -Pattern "永远有人陪|一直陪你|最懂你|智能推荐|个性化推荐|AI 测评|算法分析|精准匹配"
#   Expected: 0 hits
# 旧英文文案清除:
#   Select-String -Path frontend/src -Pattern "Describe your creative concept" -Recurse
#   Expected: 0 hits
```

### Final Checklist
- [ ] §10 E0 六项全部交付（冲动卡/种子分组/custom_idea 引导语/怀旧包装/疗愈直达/埋点三项）
- [ ] D9 闸门清零并保持
- [ ] 零后端铁证（git diff 空）
- [ ] All "Must Have" present / All "Must NOT Have" absent
- [ ] 全部测试绿
- [ ] 文案审查清单已交付（产品方终审为计划外人工步骤，不阻塞本计划完成）

- [x] 9. E0.1 入口分流修正（用户实测反馈，2026-09-20）：故事侧 5 型（plot/romance/philosophy/unsure/character_driven）确认后以主冲动 tagline 走 custom_idea 通道直达访谈 + entryNotice 引导横幅；设定侧 2 型（setting_heavy/exploration）保持分组种子页；healing/nostalgia/skip 零改动。Commit bc86fb5（A1Workspace +18/-8 + E2E 矩阵同步 + f3a 场景 1/1b）。验证：tsc 0 / vitest 223 / E2E 16 passed / 后端零 diff。
