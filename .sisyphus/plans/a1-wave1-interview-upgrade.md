# A1 访谈体验升级·波次一施工计划（P3 止血 + 50 问文案说人话 + 投递一期）

## TL;DR

> **Quick Summary**: 执行总基线计划波次一——三个纯后端子任务串行施工（1.1 P3 序号跨题错配止血 → 1.2 50 问文案说人话替换 → 1.3 投递一期规则 6 改写），每批 TDD + 全量门禁 + 治理登记。
>
> **Deliverables**:
> - 1.1 P3 数据事故修复（guide_engine options 序列化时序对齐，病理回归用例闭合）
> - 1.2 50 问 question/hint/example 三件套按④稿 before→after 全量替换 + severity 枚举移除 + 后端开场引导语替换
> - 1.3 interviewer 规则 6「引回」改「接住-归位-回题」+ 投递意图分类 + 3 式激活话术（零 schema 变更）
> - 每批治理登记（MOC/PROJECT_STATE/decision-log 拍板落痕）
>
> **Estimated Effort**: Medium（三锤，项目纪律单锤单日）
> **Parallel Execution**: NO - 串行三批（项目「单锤单日禁同日双工地」纪律 + 1.2/1.3 共享 interviewer.py 文件面交叠）
> **Critical Path**: T1→T2→T3→T4（批次1.1）→ T5→T6→T7→T8→T9（批次1.2）→ T10→T11→T12（批次1.3）→ F1-F4 → 用户验收

---

## Context

### Original Request
用户指令（2026-10-10）：「根据 oc://renderer/SDpcVUdD/session/ses_edc0a1395ffeuR3Lbg3CAYFB9y 最后的计划，开工」。
随后两项拍板确认：**波次一 5 项全按推荐落；本次范围 = 仅波次一**。

### Interview Summary
**Key Discussions**:
- 拍板方式：波次一 5 项（拍1-1 示范稿四题采用 / 拍1-2 骰子术语分级 / 拍1-3 severity 移除 / 拍1-4 规则 6 改写 / 拍1-5 投递一期纯后端先行）→ **全按推荐（是）**
- 开工范围：仅波次一（1.1→1.2→1.3），完工验收后再拍波次二 17 项
- 波次二/三：不在本计划内（2.1 结构大锤 / 3.1-3.2 前端，等波次一验收后另立施工单）

**Research Findings**:
- P3 病理（docs/plans/2026-10-09-访谈知识求助搜索-问题说明书.md L39/L80/L104）：弧光题自由文本作答 → 回复附 3 选项 → 下一问「外形记忆点」→ 用户回「3」→ 被记录成**弧光**的选项 3，外形记忆点仍空
- 代码实况（guide_engine.py）：L425 `current_options` 字段 / L476 序列化 / L480-507 `_render_option_invite`+`_attach_default_options` / **L1344-1362 直选硬匹配**（`cur_key` 与 `session.current_options` 两来源解耦——cur_key 是当前题、options 是序列化时快照）/ L1362 pick 后清空 / L1394-1428 reroll 通道
- severity 依赖（Metis 验证）：`SEVERITY_VALUES`（a1_question_tree.py:349）在 app 运行时**零消费**（graphify/semantic_compiler 无引用）；但被契约锁测试 `tests/unit/a1/test_question_tree.py:145 test_severity_values_locked` 锁定；L212 hint 文本含 severity 注记；仓库根目录 3 个一次性生成脚本（`_bq3.py`/`_build_qt_full.py`/`_write_qt.py`）含重复定义（遗留，不动）
- D24 病理回归锚点：`backend/tests/unit/a1/test_knowledge_request.py` 四用例（L39 触发二段式 / L63 失败降级 / L99 冻结丢 fills / **L202 腕带两幕重放**）
- 测试基线：后端 pytest **1627 passed / cov 84.82%**（D24 收锤后）；前端 vitest 310 / tsc 0（本波次前端零触碰）

### Metis Review
**Identified Gaps** (addressed):
- 1.2 severity 移除必然触发契约锁测试红灯 → 测试更新列入变更白名单（预期内红灯转绿项）
- 1.2 与 1.3 共享 interviewer.py → 硬性串行理由，1.2 门禁通过前 1.3 禁止开工
- 1.1 reroll gap 同根债务 → 明确本期不修（防一锤多钉）
- 契约锁粒度未定义 → 定义为：结构契约（键名/枚举值/multi 标注/锚点）锁测试保护，文案字符串（question/hint/example）按④稿目录替换
- D24 回归红线落到具体 pytest node id
- 存量 stale 会话兼容 + 直选越界数字行为锁定 + 1.3 直选/撤销优先级定义

---

## Work Objectives

### Core Objective
按已拍板的总基线波次一路线，完成三个纯后端子任务的 TDD 施工，消除正在丢数据的 P3 事故、让 50 问文案说人话、让离题想法被接住而非弹开——全部不改前端、不动 schema、不触碰波次二范畴。

### Concrete Deliverables
1. `backend/app/domains/creation/a1/guide_engine.py` P3 修复 + 病理回归用例
2. `backend/app/domains/creation/seed/story_modules.py` 15 问文案替换
3. `backend/app/domains/creation/seed/a1_question_tree.py` 35 问文案替换 + severity 移除
4. `backend/app/domains/creation/a1/interviewer.py` 开场引导语替换（~L457）+ 规则 6 投递改写
5. 对应测试文件更新/新增 + 每批治理登记（MOC/PROJECT_STATE/decision-log）

### Definition of Done
- [ ] 全量 pytest ≥ 1627 passed / 0 failed（新增用例计入，门禁 cov ≥ 80%）
- [ ] P3 病理用例（弧光→外形记忆点→"3"）从红到绿，答案写入当前题 key
- [ ] 50 问替换后契约锁测试全绿（severity 锁测试按白名单更新）
- [ ] D24 四用例（test_knowledge_request.py）逐字全绿
- [ ] `git diff --stat` 范围 = 白名单文件，零超范围
- [ ] 每批治理登记落位（MOC 变更记录 + PROJECT_STATE 两节 + decision-log）

### Must Have
- TDD 纪律：每批先红后绿，契约锁定先于文案替换
- 串行纪律：1.1 → 1.2 → 1.3，前批门禁全绿后批才开工（单锤单日）
- 独立提交：每子任务独立 commit（组内可多提交），禁止合并跨批提交
- 治理登记：每批完工回写 MOC/PROJECT_STATE；波次一收官记 decision-log 综合条目（含 5 项拍板落痕）

### Must NOT Have (Guardrails)
- **不修 reroll gap**（1.1 已知同根债务，归方向A二期遗留清单，本期只修 stale 匹配）
- **50 题封闭集合**：1.2 只改④稿目录内的 50 问 + 开场拼接；执行中看到「这句也不顺」一律不许改（含 L1377「已按示例记录」等引擎拼接文案——不在④稿目录，观察到的不协调记入施工日志供二期）
- **零 schema 变更**：1.3 不预留任何波次二槽位（material_pool/半填 schema 连数据结构影子都不留）；休眠话术只存治理文档，不进代码常量
- **不碰根目录生成脚本**（`_bq3.py`/`_build_qt_full.py`/`_write_qt.py`——遗留一次性脚本）
- **不碰前端**（A1Workspace.tsx L647 开场语前端处 = 波次三）
- **不动九型语气锚点**（spec §5.2 逐字锁定）、**不动 multi: True 标注**、**不动 label 层**
- **不触碰规则 6.5（D24 知识通道）/ 规则 7（user_confused）语义**
- **不推翻 D19-D24 任何既有裁决**

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed.
> 真机 LLM 冒烟（可选加强项）仅在产品方环境执行，不作为任务完成的阻塞条件。

### Test Decision
- **Infrastructure exists**: YES（pytest + pytest-cov，1000+ 基线；ruff/mypy）
- **Automated tests**: TDD（项目标准纪律：契约锁定 → 红 → 绿 → 全量门禁）
- **Framework**: pytest（后端）；前端零触碰故无前端测试变更
- **基线口径**: 开工前全量复跑确认当日基线（≥1627 passed）；每批收门禁 = 全量 + cov ≥ 80% + ruff 增量清零

### QA Policy
每个任务含 agent-executed QA scenarios（见各 TODO）。
证据保存到 `.sisyphus/evidence/`（本批子目录 `wave1-*`）。
- **后端逻辑**: Bash（pytest 指定 node id + 全量）
- **文案替换**: Bash（契约测试 + grep 断言 + git diff --stat 白名单核对）
- **prompt 改写**: Bash（pytest 意图分类用例 + D24 回归 node id + Fake provider 病理重放——项目惯例 LLM 用例均 Fake/monkeypatch）

---

## Execution Strategy

### Parallel Execution Waves

> **⚠️ 本计划为串行结构——有意偏离最大并行原则**，理由（项目治理压倒默认）：
> 1. 项目纪律「单锤单日禁同日双工地」（方向A一期施工单确立）
> 2. 1.2 与 1.3 共享 `interviewer.py` 文件面（Metis 确认的硬性串行理由）
> 3. 总基线 §2.1 明定「串行施工（同文件纪律），顺序建议 1.1→1.2→1.3（止血最优先）」
>
> 唯一并行点：终验波 F1-F4 四审并行。

```
批次 1.1【P3 止血·最急】guide_engine.py 序列化区
├── T1 开工基线复跑 [quick]
├── T2 P3 病理红测（弧光→外形记忆点→"3"） [deep]
├── T3 引擎侧修复 + 绿 + 边界锁定 [deep]
└── T4 批次门禁 + 治理登记 [quick]

批次 1.2【文案说人话】seed/ 两文件 + interviewer 开场区（T4 门禁全绿后才可开工）
├── T5 前置验证（severity 零依赖复核 + 50 题清单逐题核对行号 + 契约锁盘点） [quick]
├── T6 故事线 15 问替换（story_modules.py） [unspecified-high]
├── T7 世界观 35 问替换 + severity 移除 + 契约锁测试白名单更新（a1_question_tree.py） [unspecified-high]
├── T8 开场引导语后端拼接替换（interviewer.py ~L457）+ 拼接断言 [quick]
└── T9 批次门禁（字节 diff 白名单）+ 治理登记 [quick]

批次 1.3【投递一期】interviewer 规则 6 区（T9 门禁全绿后才可开工）
├── T10 规则 6 改写 + 投递意图分类 + 3 式激活话术（红→绿） [deep]
├── T11 回归护栏（D24 四用例 + 直选优先级锁 + schema 不变断言） [unspecified-high]
└── T12 批次门禁 + 治理登记 + decision-log 波次一综合条目 [quick]

终验波（全部完工后，四审并行）
├── F1 计划合规审计 [oracle]
├── F2 代码质量审查 [unspecified-high]
├── F3 真实 QA 重放 [unspecified-high]
└── F4 范围保真检查 [deep]
→ 呈报用户 → 用户明确验收 → 波次二拍板另议
```

### Dependency Matrix

| 任务 | 依赖 | 解锁 |
|---|---|---|
| T1 | - | T2 |
| T2 | T1 | T3 |
| T3 | T2 | T4 |
| T4 | T3 | T5（批次 1.2 解锁） |
| T5 | T4 | T6, T7 |
| T6 | T5 | T9 |
| T7 | T5 | T9 |
| T8 | T5 | T9 |
| T9 | T6, T7, T8 | T10（批次 1.3 解锁） |
| T10 | T9 | T11 |
| T11 | T10 | T12 |
| T12 | T11 | F1-F4 |
| F1-F4 | T12 | 用户验收 |

注：T6/T7/T8 理论上可并行（不同文件），但项目单锤纪律下按 T6→T7→T8 串行执行；若执行环境允许同日多工地，允许 T6/T7 并行（T8 必须最后——interviewer.py 在 T7 契约测试语境稳定后再动）。

### Agent Dispatch Summary

- **批次 1.1**: 4 任务 — T1 → `quick`，T2 → `deep`，T3 → `deep`，T4 → `quick`
- **批次 1.2**: 5 任务 — T5 → `quick`，T6 → `unspecified-high`，T7 → `unspecified-high`，T8 → `quick`，T9 → `quick`
- **批次 1.3**: 3 任务 — T10 → `deep`，T11 → `unspecified-high`，T12 → `quick`
- **终验**: 4 任务 — F1 → `oracle`，F2 → `unspecified-high`，F3 → `unspecified-high`，F4 → `deep`

---

## TODOs

- [x] 1. 开工基线复跑（批次 1.1 前置）

  **What to do**:
  - 全量 pytest 复跑确认当日基线（预期 ≥1627 passed / cov ≥ 84%）
  - 记录基线数字到 `.sisyphus/evidence/wave1-baseline.txt`（后续三批门禁的对照锚点）
  - `git status` 确认工作区干净（08/09 前批 untracked 遗留除外——不触碰）

  **Must NOT do**: 不修任何测试；不顺手清理任何遗留。

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []（纯命令执行，无技能域重叠）
  - **Skills Evaluated but Omitted**: `test-driven-development`（本任务只跑不改，TDD 纪律在 T2 起生效）

  **Parallelization**:
  - **Can Run In Parallel**: NO（全计划串行头）
  - **Parallel Group**: 批次 1.1（with T2/T3/T4 串行）
  - **Blocks**: T2
  - **Blocked By**: None

  **References**:
  - `backend/` — pytest 运行目录（项目 venv：`.venv\Scripts\python -m pytest --cov=app`）
  - `PROJECT_STATE.md` L13 — D24 收锤基线「1627 passed / cov 84.82%」为本任务对照值。**WHY**: 基线数字漂移意味着工作区有未登记变更，必须先查明再开工

  **Acceptance Criteria**:
  - [ ] pytest 全量输出落盘 `.sisyphus/evidence/wave1-baseline.txt`，passed ≥ 1627，failed = 0

  **QA Scenarios**:
  ```
  Scenario: 基线健康检查
    Tool: Bash
    Preconditions: backend/.venv 存在且可运行
    Steps:
      1. cd backend && .venv\Scripts\python -m pytest --cov=app -q 2>&1 | tail -20
      2. 比对 passed 数与 1627 基线
    Expected Result: ≥1627 passed / 0 failed / cov ≥ 80%；输出存证 wave1-baseline.txt
    Failure Indicators: failed > 0 或 passed < 1627 → 停工查明，不得带病开工
    Evidence: .sisyphus/evidence/wave1-baseline.txt
  ```

  **Commit**: NO（纯验证任务，无产物提交）

- [x] 2. P3 病理红测（先红后修的 RED 阶段）

  **What to do**:
  - 新建测试文件 `backend/tests/unit/a1/test_option_cross_question.py`（或并入既有 options 相关测试文件——先盘点 `tests/unit/a1/` 既有命名惯例再定）
  - 病理复现用例（照说明书 L39 逐字场景）：
    1. 构造会话 → 弧光题（arc_direction）自由文本作答「堂堂正正的生活」
    2. 引擎推进 → 下一问「外形记忆点」（character_visual）reply 附 3 选项
    3. 用户发送 `"3"`（意图选外形记忆点的选项 3）
    4. **断言（当前为红）**：答案写入 `character_visual`（当前题 key）——实际现状写入 `arc_direction` 的弧光选项 3
  - 辅助用例：直选越界数字 `"0"` / `"4"`（超出 len(current_options)）走常规文本路径不进直选分支（现状行为锁定）
  - 辅助用例：存量 stale 会话容忍——session 带旧 current_options 恢复后不崩溃、安全降级
  - 全部用例按项目惯例 Fake provider / monkeypatch（不依赖真实 LLM）

  **Must NOT do**: 不改 guide_engine.py 任何生产代码（RED 阶段只写测试）；不修 reroll gap（不写「pick 后首问无 options」相关用例——那是二期遗留）。

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 病理复现需要精确理解 guide_engine 会话流转时序（L1344-1362 直选区 + L487-507 附加区 + L476 序列化），红测必须钉准 stale 根因而非表象
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: RED 阶段纪律——测试先行、一次一个断言面、红得有意义
  - **Skills Evaluated but Omitted**: `systematic-debugging`（根因已由说明书+Metis 定位，非本任务职责）

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: 批次 1.1（串行）
  - **Blocks**: T3
  - **Blocked By**: T1

  **References**:
  **Pattern References**:
  - `backend/app/domains/creation/a1/guide_engine.py:1344-1362` — 直选硬匹配区（`stripped` → `idx` → `session.current_options[idx]` → fills + `options_digest` 审计 + L1362 清空）。**WHY**: 病理第一现场——「cur_key 是当前题、current_options 是序列化时快照」两来源解耦即 stale 根因
  - `backend/app/domains/creation/a1/guide_engine.py:425,476,480-507` — `current_options` 字段定义 / next_question 序列化 / `_attach_default_options`（白名单外 examples 非空 → 写 options + 渲染邀请；白名单内 → 只清零渲染）。**WHY**: 序列化时序即疑因(a)，红测必须覆盖「新问题推进后 options 与 cur_key 的绑定关系」
  - `backend/app/domains/creation/a1/guide_engine.py:1394-1428` — reroll 通道（同区参照，**只读不动**）
  **Test References**:
  - `backend/tests/unit/a1/test_knowledge_request.py:202` — 腕带两幕重放的 Fake/monkeypatch 组织方式。**WHY**: 同类「逐字病理重放」用例的项目写法范本
  - `docs/plans/2026-10-09-访谈知识求助搜索-问题说明书.md:39,80,104` — P3 病理逐字记录与嫌疑两处。**WHY**: 红测场景的唯一权威来源（弧光→外形记忆点→"3"）

  **Acceptance Criteria**:
  - [ ] 病理用例运行结果为 RED（AssertionError：期望 character_visual 实得 arc_direction）
  - [ ] 越界数字用例 GREEN（现状行为锁定）
  - [ ] stale 会话容忍用例 GREEN
  - [ ] 全量 pytest 除新红测外零新失败

  **QA Scenarios**:
  ```
  Scenario: 病理复现红测（RED）
    Tool: Bash
    Preconditions: T1 基线健康
    Steps:
      1. 运行 cd backend && .venv\Scripts\python -m pytest tests/unit/a1/test_option_cross_question.py -v
      2. 核对病理用例失败信息：assert 期望写入 character_visual、实际写入 arc_direction
    Expected Result: 1 failed（病理用例，失败原因=stale options 错配）+ 2 passed（边界锁定）
    Failure Indicators: 病理用例意外 GREEN（说明根因判断错误，回头重查序列化时序）或边界用例 RED（现状被误改）
    Evidence: .sisyphus/evidence/wave1-t2-red.txt
  ```

  **Commit**: YES（红测独立提交）
  - Message: `test(a1): P3 序号跨题错配病理红测（弧光→外形记忆点→"3"）`
  - Files: `backend/tests/unit/a1/test_option_cross_question.py`（新）
  - Pre-commit: 新测试文件单独运行可复现红

- [x] 3. P3 引擎侧修复（GREEN 阶段）

  **What to do**:
  - 修复 `guide_engine.py` 直选通道 stale 匹配：直选消费的 `current_options` 必须与 `cur_key`（当前题）严格绑定——推进到新问题时旧 options 立即失效（清空或标记轮次），`"3"` 只对当前题的 options 生效
  - 修复方案自选（轮次戳绑定 / 推进时清空 / 序列化同步对齐——以最小改动、存量会话安全为先），**只动引擎侧疑因(a)**
  - 保留并核对：`option_pick` 遥测的 `options_digest` 修复后记录**当前题** options（语义修正，记入施工日志）
  - T2 病理用例转 GREEN，全量回归零破坏
  - 若红测揭示根因含 prompt 侧疑因(b)（规则 8.6 示例与当前题脱钩）：**不在本任务修**——记录证据到施工日志，归 T10（1.3 prompt 改写区）处理

  **Must NOT do**: 不修 reroll gap（pick 后首问 options 缺失维持现状）；不改 interviewer.py（prompt 侧归 1.3）；不改任何文案字符串。

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 会话状态时序修复，需在存量会话兼容/遥测契约/最小改动三约束下做工程判断
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: GREEN 阶段纪律——最小实现转绿、不镀金
  - **Skills Evaluated but Omitted**: `systematic-debugging`（定位已完成，本任务为修复执行）

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: 批次 1.1（串行）
  - **Blocks**: T4
  - **Blocked By**: T2

  **References**:
  **Pattern References**:
  - `backend/app/domains/creation/a1/guide_engine.py:1344-1362` — 直选区（修复主战场）
  - `backend/app/domains/creation/a1/guide_engine.py:476,487-507,1462,1473` — 序列化点 / options 附加与清理点（时序对齐的对接面）
  - `backend/tests/unit/a1/test_option_cross_question.py`（T2 产物）— 转绿判据
  **API/Type References**:
  - `docs/plans/2026-10-10-A1访谈体验升级-总基线计划.md` §4 批 1.1 行 — 「序号跨题回归用例 + 全量门禁」为验收口径

  **Acceptance Criteria**:
  - [ ] T2 病理用例 GREEN（答案写入 character_visual）
  - [ ] 全量 pytest ≥ 基线+3 passed / 0 failed
  - [ ] ruff 对 guide_engine.py 增量清零

  **QA Scenarios**:
  ```
  Scenario: 修复转绿（GREEN）
    Tool: Bash
    Steps:
      1. .venv\Scripts\python -m pytest tests/unit/a1/test_option_cross_question.py -v → 全绿
      2. .venv\Scripts\python -m pytest --cov=app -q → 全量 ≥ 基线+3 / 0 failed
    Expected Result: 病理用例答案断言命中 character_visual；options_digest 与当前题 options 一致
    Failure Indicators: 任何既有用例转红（时序修复破坏了 reroll/confirm 路径）
    Evidence: .sisyphus/evidence/wave1-t3-green.txt

  Scenario: 存量会话安全降级
    Tool: Bash
    Preconditions: 构造带 stale current_options 的持久化会话（store 层直插）
    Steps:
      1. 加载该会话 → 发送普通文本回答 → 发送 "3"
      2. 断言不崩溃、"3" 不误填旧字段
    Expected Result: 安全降级为常规文本处理，零异常
    Evidence: .sisyphus/evidence/wave1-t3-legacy-session.txt
  ```

  **Commit**: YES
  - Message: `fix(a1): P3 直选通道 options 与当前题绑定，消除跨题错配`
  - Files: `backend/app/domains/creation/a1/guide_engine.py` + `backend/tests/unit/a1/test_option_cross_question.py`（如补用例）
  - Pre-commit: 全量 pytest

- [x] 4. 批次 1.1 门禁 + 治理登记

  **What to do**:
  - 终门禁：全量 pytest + cov ≥ 80% + ruff 增量清零 + `git diff --stat` 核对（只允许 guide_engine.py + 测试文件）
  - 治理登记：PROJECT_STATE 两节（当前阶段 + 已完成追加批次 1.1 条目）；docs/README.md 变更记录一行（批次 1.1 完工）；decision-log **暂不立综合条目**（波次一收官 T12 统一记，本批只在 PROJECT_STATE 留痕）
  - 施工日志：reroll gap 不修声明 + options_digest 语义修正 + 疑因(b)（如有）证据，写入 evidence 收执

  **Must NOT do**: 不动 decision-log（综合条目归 T12）；不改 MOC plans 表（总基线行已有，不重复）。

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []（门禁命令 + 治理文档编辑，惯例明确）

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: T5（批次 1.2 解锁闸）
  - **Blocked By**: T3

  **References**:
  - `PROJECT_STATE.md` 头部 — 「当前阶段」节格式（照 L4-L13 惯例）
  - `docs/README.md` 变更记录节 — 追加行格式
  **WHY**: 治理回写走项目既有格式，防格式漂移引发后续会话误读

  **Acceptance Criteria**:
  - [ ] 全量门禁绿 + diff 范围白名单内
  - [ ] PROJECT_STATE 两节 + MOC 变更记录落位
  - [ ] evidence 收执含 reroll gap 声明

  **QA Scenarios**:
  ```
  Scenario: 批次收门禁与登记核验
    Tool: Bash
    Steps:
      1. git diff --stat → 断言仅 guide_engine.py / 测试 / PROJECT_STATE / docs/README.md
      2. grep -c "批次 1.1" PROJECT_STATE.md → ≥1
    Expected Result: 范围干净、登记落位
    Evidence: .sisyphus/evidence/wave1-t4-gate.txt
  ```

  **Commit**: YES
  - Message: `docs(governance): 波次一批次1.1 P3修复完工登记`
  - Files: `PROJECT_STATE.md`, `docs/README.md`

- [x] 5. 批次 1.2 前置验证（severity 零依赖 + 50 题清单核对 + 契约锁盘点）

  **What to do**:
  - **severity 复核**（Metis 已验，本任务落痕固化）：grep 全 app 运行时代码确认 `SEVERITY_VALUES` 零消费（graphify.py / semantic_compiler.py 无引用）；定位契约锁测试 `tests/unit/a1/test_question_tree.py:145 test_severity_values_locked` 与 `a1_question_tree.py:349` 枚举定义 + **L212 hint 文本中的 severity 注记**（随 T7 同步清理）
  - **50 题清单逐题核对**：④稿 §2（故事 15）+ §3（世界观 35）的每题 before 原文，逐题在 `story_modules.py` / `a1_question_tree.py` 中定位行号，产出「④稿题号 → 文件:行号」映射表（T6/T7 的施工索引）；发现④稿 before 与代码不一致的题 → 记录并 STOP 上报（以代码现状为准需人工确认改法）
  - **契约锁盘点**：清点两文件现有保护性测试（键名/枚举/multi 标注/锚点类），确认「结构锁住、文案放开」的改造面
  - **根目录生成脚本确认不动**：`_bq3.py` / `_build_qt_full.py` / `_write_qt.py` 含重复 SEVERITY_VALUES——标注遗留不动

  **Must NOT do**: 不改任何生产代码或测试（纯验证任务）。

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []（grep/读文档/制表）

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: T6, T7
  - **Blocked By**: T4

  **References**:
  - `docs/plans/2026-10-10-访谈问题文案说人话-逐句分析优化.md` §2/§3 — 50 题 before→after 唯一权威目录（**施工只认这份**）
  - `backend/app/domains/creation/seed/a1_question_tree.py:349,212` — SEVERITY_VALUES 定义 / hint 注记
  - `backend/tests/unit/a1/test_question_tree.py:145` — 契约锁测试（T7 白名单更新目标）
  **WHY**: 映射表是 T6/T7 高保真替换的前提；severity 三处联动（枚举/锁测试/hint）漏一处留幽灵引用

  **Acceptance Criteria**:
  - [ ] 映射表 50/50 题全部定位（存 `.sisyphus/evidence/wave1-t5-mapping.md`）
  - [ ] severity 零依赖复核落痕（grep 输出存证）
  - [ ] 不一致题清单（如有）单独呈报

  **QA Scenarios**:
  ```
  Scenario: 清单完整性
    Tool: Bash
    Steps:
      1. 统计映射表行数 = 50（故事 15 + 世界观 35）
      2. Select-String -Path app 递归 "SEVERITY_VALUES" → 仅 a1_question_tree.py 与测试文件命中
    Expected Result: 50/50 定位；零运行时消费
    Failure Indicators: 映射 < 50 或发现新的运行时消费点 → STOP 上报
    Evidence: .sisyphus/evidence/wave1-t5-mapping.md + wave1-t5-severity.txt
  ```

  **Commit**: NO（验证产物入 evidence，不入库）

- [x] 6. 故事线 15 问文案替换（story_modules.py）

  **What to do**:
  - 按④稿 §2 替换 M11 角色 6 问 + M12 剧情 9 问的 question/hint/example（重写 5：opening_event/core_dilemma/tension_hole/lead_chain/bound_characters；微调 10）
  - **示范稿四题逐字采用**（拍1-1）：core_dilemma / tension_hole / lead_chain / bound_characters 按会话示范稿 + 例句同宇宙展开
  - 红线执行：单问句铁律（不新增问号堆叠）/ `multi: True` 标注不动 / 林澈·守夜人·仙侠三套示例宇宙维持原分配只做同宇宙展开
  - 契约先行：替换前先跑既有 story_modules 相关测试确认绿（结构锁定），替换后逐题 diff 核对与④稿 after 一致
  - 新增守门测试：断言替换后的 15 问与④稿 after 文本一致（防手滑漏改/多改）+ multi 标注存在性断言

  **Must NOT do**: 不改 50 题之外任何文案（含 L1377 引擎拼接语）；不改键名/枚举/结构；不动 a1_question_tree.py（归 T7）。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 15 题逐题高保真替换，量大且红线多，需要强执行力与自查纪律
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: 契约锁定→替换→回归的项目既定节奏
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`（文案为后端数据，无 UI 层）

  **Parallelization**:
  - **Can Run In Parallel**: NO（单锤纪律；若执行环境允许同日多工地可与 T7 并行——不同文件）
  - **Blocks**: T9
  - **Blocked By**: T5

  **References**:
  **Pattern References**:
  - `docs/plans/2026-10-10-访谈问题文案说人话-逐句分析优化.md:38-215`（§2 全节）— 15 题逐题 before→after。**WHY**: 唯一施工目录，逐字保真源
  - `backend/app/domains/creation/seed/story_modules.py` — M11+M12 定义（T5 映射表给出行号）
  - `docs/plans/2026-10-10-故事向创作指南.md` — 教学层同声口语径。**WHY**: after 措辞与之互校过的同源稿，替换遇到④稿歧义时的参照
  **Test References**:
  - `backend/tests/unit/a1/` 既有 story_modules 测试 — 结构契约基线
  - `docs/plans/2026-10-10-访谈问题文案说人话-逐句分析优化.md:347-355`（§6 施工红线）— 七条红线逐条过

  **Acceptance Criteria**:
  - [ ] 15 问替换后：守门测试 GREEN（与④稿 after 一致 + multi 标注在位）
  - [ ] 全量 pytest 零新失败（既有文案断言测试如有引用旧文案——逐个核对属预期内更新，记入提交说明）
  - [ ] `git diff` 仅 story_modules.py + 测试

  **QA Scenarios**:
  ```
  Scenario: 替换保真（Happy）
    Tool: Bash
    Steps:
      1. pytest tests/unit/a1/ -k "story_modules or story_copy" -v → 全绿
      2. git diff backend/app/domains/creation/seed/story_modules.py → 逐题对照④稿 after
    Expected Result: 15/15 题文本与④稿 after 逐字一致；multi: True 原样
    Failure Indicators: 任一题与④稿不符 / multi 标注丢失 / 出现④稿外的改动行
    Evidence: .sisyphus/evidence/wave1-t6-diff.txt

  Scenario: 示例宇宙不迁移（Edge）
    Tool: Bash
    Steps:
      1. 替换前后分别统计 "林澈"/"守夜人" 在 story_modules.py 的出现分布
      2. 断言题号-宇宙分配与替换前一致
    Expected Result: 三宇宙维持原分配，零迁移
    Evidence: .sisyphus/evidence/wave1-t6-universes.txt
  ```

  **Commit**: YES
  - Message: `copy(a1): 故事线 15 问说人话替换（示范稿四题采用）`
  - Files: `backend/app/domains/creation/seed/story_modules.py` + 守门测试
  - Pre-commit: 守门测试 + 全量

- [x] 7. 世界观 35 问替换 + severity 移除（a1_question_tree.py）

  **What to do**:
  - 按④稿 §3 替换 35 问（红色重写 13 / 黄色微调 21 / 绿色保留 1=keywords 不动）+ §4 后端开场引导语（见 T8——本任务不碰 interviewer）
  - **骰子术语分级**（拍1-2）：d20/3d6/Roll-under/Roll-over/骰池保留，全部配中文解释；砍「映射/线性/钟形/本体/客体」包装语
  - **severity 移除**（拍1-3，三处联动）：L349 `SEVERITY_VALUES` 枚举移除 / L212 hint 中 severity 注记同步删 / `test_question_tree.py:145 test_severity_values_locked` 更新为「枚举已移除」断言（**预期内红灯转绿项——白名单变更**）；key_nodes 的 question/hint 按④稿去 severity 表述
  - 守门测试：35 问与④稿 after 一致性断言（keywords 题断言未变）
  - 全量回归：上传解析（worldview_upload）相关测试如受 severity 表述影响——核对属预期内更新

  **Must NOT do**: 不碰根目录 `_bq3.py`/`_build_qt_full.py`/`_write_qt.py`；不改键名/树结构/锚点；keywords（保留题）零改动。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 35 题 + severity 三处联动 + 上传解析回归面，批次内最大单任务
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: 与 T6 理论并行（不同文件），单锤纪律下串行
  - **Blocks**: T9
  - **Blocked By**: T5（映射表）, 建议 T6 后

  **References**:
  - `docs/plans/2026-10-10-访谈问题文案说人话-逐句分析优化.md:216-334`（§3 全节 + §5 统计）— 35 题目录与三色判定
  - `backend/app/domains/creation/seed/a1_question_tree.py:212,349` — severity 两处
  - `backend/tests/unit/a1/test_question_tree.py:145` — 契约锁测试（白名单更新）
  - `docs/plans/2026-10-10-世界观向创作指南.md` — TRPG 术语扫盲与同声口参照。**WHY**: 骰子题 after 措辞的互校源
  **WHY**: severity 移除的三处联动漏一处即幽灵引用；三色判定决定 35 题的改动深度

  **Acceptance Criteria**:
  - [ ] 35 问守门测试 GREEN（34 改 + 1 保留断言）
  - [ ] severity 三处清零：`Select-String "SEVERITY|severity" app/` 仅剩测试文件的白名单断言
  - [ ] 全量 pytest 零非预期失败

  **QA Scenarios**:
  ```
  Scenario: severity 三处联动清零
    Tool: Bash
    Steps:
      1. Select-String -Path backend\app -Recurse -Pattern "SEVERITY_VALUES" → 零命中
      2. pytest tests/unit/a1/test_question_tree.py -v → 更新后锁测试绿
    Expected Result: 运行时代码零 severity 残留；锁测试断言「已移除」
    Failure Indicators: app 内任何残留命中 / graphify 相关测试转红
    Evidence: .sisyphus/evidence/wave1-t7-severity-clean.txt

  Scenario: keywords 保留题零改动
    Tool: Bash
    Steps:
      1. git diff 中定位 keywords 题 → 断言无 diff 行
    Expected Result: 绿色保留题字节级不变
    Evidence: .sisyphus/evidence/wave1-t7-keywords-unchanged.txt
  ```

  **Commit**: YES
  - Message: `copy(a1): 世界观 35 问替换 + severity 枚举移除（含锁测试白名单更新）`
  - Files: `backend/app/domains/creation/seed/a1_question_tree.py` + `backend/tests/unit/a1/test_question_tree.py`
  - Pre-commit: 守门 + 全量

- [x] 8. 开场引导语后端拼接替换（interviewer.py）

  **What to do**:
  - 按④稿 §4（L328）替换 interviewer.py seed 区（~L457 附近，**实际行号施工时以 grep 定位为准**）开场拼接：
    - before：`用户的初始创意：{种子}。我将围绕它引导你展开世界观。`
    - after：`记下你的创意了：{种子}。\n接下来我会一次问你一个问题，帮你把它变成一个完整的世界。每题都可以自己写、从我给的选项里挑，或者跳过。`
  - 新增拼接断言测试：构造种子会话 → 断言首条 reply 含新开场全文
  - **范围注记**：前端 A1Workspace.tsx L647 同源文案 = 波次三（拍3-1 另议），本任务**零前端触碰**

  **Must NOT do**: 不动 interviewer 规则区（规则 6/7/8.x 归 T10）；不改除开场拼接外的任何字符串。

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []（单点字符串替换 + 一条断言测试）

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: T9
  - **Blocked By**: T7（interviewer.py 在批次内最后动，防止与 T7 回归窗口交叠）

  **References**:
  - `docs/plans/2026-10-10-访谈问题文案说人话-逐句分析优化.md:322-331`（§4 开场引导语专项）— before→after 逐字稿。**WHY**: 唯一权威替换文本
  - `backend/app/domains/creation/a1/interviewer.py`（~L457 seed 拼接区）— 替换点
  **WHY**: ④稿明示「实际渲染链路施工时以页面为准」——施工时先 grep「我将围绕它引导你展开世界观」精确定位

  **Acceptance Criteria**:
  - [ ] grep 旧开场语零命中（后端范围）
  - [ ] 拼接断言测试 GREEN
  - [ ] 全量 pytest 零新失败

  **QA Scenarios**:
  ```
  Scenario: 开场语替换与衔接
    Tool: Bash
    Steps:
      1. Select-String "我将围绕它引导你展开世界观" backend\app → 零命中
      2. pytest 拼接断言用例 → 绿；reply 首条含「记下你的创意了」+「一次问你一个问题」
    Expected Result: 新开场逐字落位，与首问文案衔接通顺（断言含首问前缀）
    Failure Indicators: 模板变量 {种子} 丢失 / 换行符转义错误（\n 字面化）
    Evidence: .sisyphus/evidence/wave1-t8-opening.txt
  ```

  **Commit**: YES
  - Message: `copy(a1): 访谈开场引导语后端替换（说人话）`
  - Files: `backend/app/domains/creation/a1/interviewer.py` + 断言测试
  - Pre-commit: 断言 + 全量

- [x] 9. 批次 1.2 门禁（字节 diff 白名单）+ 治理登记

  **What to do**:
  - 终门禁：全量 pytest + cov ≥ 80% + ruff 三源文件增量清零 + **字节 diff 白名单核对**：`git diff --stat` 恰好 = story_modules.py / a1_question_tree.py / interviewer.py + 对应测试 + 治理文档，零超范围
  - 例句宇宙 grep 断言：三宇宙分布与 T6 存证一致
  - 治理登记：PROJECT_STATE 两节 + MOC 变更记录（批次 1.2 完工）
  - 施工日志：④稿外观察到的不协调文案清单（含 L1377）→ 记录供二期，不动代码

  **Must NOT do**: 不立 decision-log 条目（归 T12）。

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: T10（批次 1.3 解锁闸——interviewer.py 文件面交叠解除）
  - **Blocked By**: T6, T7, T8

  **References**: 同 T4 治理惯例（PROJECT_STATE 头部 / docs/README.md 变更记录）

  **Acceptance Criteria**:
  - [ ] 白名单 diff 核对通过 + 全量绿
  - [ ] 治理登记落位

  **QA Scenarios**:
  ```
  Scenario: 批次收白名单核对
    Tool: Bash
    Steps:
      1. git diff --stat → 文件清单恰为白名单集合
      2. 全量 pytest → ≥ 基线+守门用例数 / 0 failed
    Expected Result: 范围干净、门禁绿、登记落位
    Evidence: .sisyphus/evidence/wave1-t9-gate.txt
  ```

  **Commit**: YES
  - Message: `docs(governance): 波次一批次1.2 文案替换完工登记`
  - Files: `PROJECT_STATE.md`, `docs/README.md`

- [x] 10. 规则 6 投递改写 + 意图分类 + 3 式激活话术（红→绿）

  **What to do**:
  - **规则 6 文案改写**（拍1-4）：interviewer.py 规则 6 从「引回主题」改写为「**接住-归位-回题**」——用户说出离题想法时：接住（确认收到）→ 归位（D23 语义三判泛化到全树槽位：想法属于树上已有槽 → fills 投递该槽 + 轻披露）→ 回题（找连接词自然引回当前问，找不到就温和回题，**绝不指责跑题**）
  - **投递意图分类（解析侧）**：interviewer 返回 schema **additive** 扩展（先例：D24 knowledge_request 键）——新增投递意图键，fills 可指向非当前题的树上已有槽位；**零 schema 变更** = 不动 A1Session/store/持久化结构
  - **3 式激活话术落位**（⑨§3，模板变量化进 prompt）：落位确认（「好想法——我记进【槽位名】了（一句话复述）。回到刚才：【当前问题】」）/ 回题桥接（「这正好和【当前模块】是一对——」）/ 撤销护栏（D23 披露沿用：「刚才那笔记错了地方？说一声，我挪走。」）
  - **休眠话术隔离**（Metis 护栏）：灵感入架 / 半填补问▶⇄ / 追加循环 4 式**不进代码**——只存于治理文档，随波次二 2.1 机制激活时再落
  - **直选优先级锁定**：直选精确匹配（"1"/"2"/"3" 对当前题 options）优先级不变；投递判定不拦截直选；撤销走显式词——测试锁住
  - 红测先行：投递意图用例（离题想法 → 落既有槽 + 轻披露 + 回题）先红后绿；T3 若记录了 prompt 侧疑因(b)（规则 8.6 示例与当前题脱钩）→ 本任务一并核正（示例序号只对当前题 options）
  - 全部用例 Fake provider / monkeypatch

  **Must NOT do**: 不动规则 6.5（D24 知识通道）与规则 7（user_confused）语义；不预留 material_pool/半填任何数据结构；不动 guide_engine（直选已由 1.1 修）；不改前端。

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: prompt 工程规则改写 + additive schema 扩展 + 多通道共存（知识/投递/直选/答当前）优先级设计——本波次最需推理深度的一锤
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: 意图分类与话术的行为契约先红后绿
  - **Skills Evaluated but Omitted**: `systematic-debugging`（非缺陷修复，是特性施工）

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: T11
  - **Blocked By**: T9

  **References**:
  **Pattern References**:
  - `docs/plans/2026-10-10-结构接住想象-投递式访谈机制设计.md:32-44,97-101`（§2.1 五通道 + §5 施工序一期定义）— **一期边界唯一权威**：「规则 6 改写 + 投递意图分类，零 schema，落位仍写现有槽」
  - `docs/plans/2026-10-10-新结构引导话术设计.md:134-145`（§3 投递话术族）— 3 式激活 + 4 式休眠的句式表。**WHY**: 话术逐字源，变量化即【槽位名】【当前问题】占位
  - `backend/app/domains/creation/a1/interviewer.py` 规则 6 区 — 改写主战场；**规则 6.5/7 区只读红线**
  **Test References**:
  - `backend/tests/unit/a1/test_knowledge_request.py:39-99` — additive 键扩展 + 二段式 + 冻结的组织范本。**WHY**: D24 同文件同模式先例，意图分类键照此接入
  - `docs/plans/2026-10-10-A1访谈体验升级-总基线计划.md:114`（§4 批 1.3 行）— 验收口径「投递意图用例 + 真机冒烟」

  **Acceptance Criteria**:
  - [ ] 投递意图用例 GREEN：离题想法 → fills 落树上既有槽 + reply 含落位确认话术 + 回题
  - [ ] schema 不变断言：A1Session 字段集与 T9 后完全一致（测试锁）
  - [ ] 直选优先级用例 GREEN（"3" 直选不被投递拦截）
  - [ ] 规则 6.5 / 7 文本 diff 为零（git diff 行级核对）

  **QA Scenarios**:
  ```
  Scenario: 投递落位（Happy）
    Tool: Bash
    Preconditions: Fake provider 按⑦§3 现场一编排返回
    Steps:
      1. 会话进行中当前问=获取方式，用户输入「对了！主角最后把师姐的剑挂在城门口了」
      2. 断言：fills 指向树上既有槽（如支线/意象槽）非当前问字段
      3. 断言：reply 含「记进」式落位确认 + 回题句（含当前问关键词）
    Expected Result: 接住-归位-回题三段完整，fills 零丢失
    Failure Indicators: 想法被旧规则 6 弹开（「我们先围绕…推进」话术残留）/ fills 写入当前问字段
    Evidence: .sisyphus/evidence/wave1-t10-delivery.txt

  Scenario: 无近槽想法的温和处理（Edge）
    Tool: Bash
    Steps:
      1. 用户输入完全无近槽的抽象想法（如「我想让读者哭」）
      2. 断言：不崩溃、不拒收——LLM 落最近既有槽或温和回应，reply 无指责语
    Expected Result: 永不出现「想法被弹开」体感（一期范围内以现有槽兜底）
    Evidence: .sisyphus/evidence/wave1-t10-nohome.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): 规则6 投递改写——接住-归位-回题 + 意图分类（零 schema）`
  - Files: `backend/app/domains/creation/a1/interviewer.py` + 测试
  - Pre-commit: 新用例 + D24 四用例 + 全量

- [x] 11. 回归护栏（D24 病理 + 直选/投递共存 + schema 锁）

  **What to do**:
  - D24 四用例逐 node id 全绿：`test_knowledge_request_triggers_search_second_pass` / `test_knowledge_search_failure_degrades` / `test_freeze_drops_fills_in_knowledge_thread` / `test_two_act_wristband_transcript_replay`
  - 共存矩阵用例：知识求助 + 投递 + 直选 + 答当前四通道在同会话交错运行互不污染（知识通道 fills 冻结不被投递绕过 / 投递后直选仍可用 / 腕带病理两幕重放后投递正常）
  - schema hash 断言：interviewer 返回键集 = 既有键 + 投递键（additive）；A1Session 序列化字段 hash 与 T9 后一致
  - P3 病理用例复跑（1.1 产物）确认 1.3 改动未回退

  **Must NOT do**: 不为修护栏而改 D24 生产语义（发现真冲突 → STOP 上报，不得绕行）。

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 多通道共存矩阵测试设计量大面细，需穷举组合纪律
  - **Skills**: [`verification-before-completion`]
    - `verification-before-completion`: 收官证据纪律——每个断言有命令输出支撑

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: T12
  - **Blocked By**: T10

  **References**:
  - `backend/tests/unit/a1/test_knowledge_request.py:39,63,99,202` — 四 node id 逐字锚点
  - `backend/tests/unit/a1/test_option_cross_question.py`（T2/T3 产物）— P3 回退检查
  **WHY**: D24 是本批最高风险回归面（规则 6 与 6.5 物理相邻）；P3 是本波次立项起因，防修 A 破 B

  **Acceptance Criteria**:
  - [ ] D24 四用例 + P3 用例 + 共存矩阵全绿
  - [ ] schema hash 断言 GREEN
  - [ ] 全量 pytest ≥ 前批 + 新增 / 0 failed

  **QA Scenarios**:
  ```
  Scenario: D24 回归红线
    Tool: Bash
    Steps:
      1. .venv\Scripts\python -m pytest tests/unit/a1/test_knowledge_request.py -v
      2. 四用例逐条 GREEN，失败信息零「rule 6」相关断言变化
    Expected Result: 4/4 全绿
    Failure Indicators: 任一转红 → T10 改写侵入 6.5/7 语义，回退审查
    Evidence: .sisyphus/evidence/wave1-t11-d24-regression.txt
  ```

  **Commit**: YES（如补用例）
  - Message: `test(a1): 投递一期回归护栏——D24/直选/投递共存矩阵`
  - Files: `backend/tests/unit/a1/`
  - Pre-commit: 全量

- [x] 12. 批次 1.3 门禁 + 波次一收官治理登记

  **What to do**:
  - 终门禁：全量 pytest + cov ≥ 80% + ruff 三源文件增量清零 + 白名单 diff
  - **decision-log 波次一综合条目**：5 项拍板落痕（拍1-1 至 拍1-5 按推荐闭卷）+ 三批提交链 + 遗留清单（reroll gap / L1377 等二期观察项 / 波次二 17 项待拍）
  - PROJECT_STATE 两节（批次 1.3 完工 + 波次一收官态）+ MOC 变更记录
  - 真机冒烟指引（**非阻塞**）：产品方环境重启后端 → 访谈中说出离题想法验证落位 → 记录体感（E0 观察台照常取数）

  **Must NOT do**: 不自动开工波次二（等用户验收 + 17 项拍板）。

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: F1-F4（终验解锁）
  - **Blocked By**: T11

  **References**:
  - `docs/decision-log.md` — D 条目格式（照 D23/D24 惯例）
  - `docs/plans/2026-10-10-A1访谈体验升级-总基线计划.md` §3 — 5 项拍板的推荐值即闭卷值
  **WHY**: 决策台账是 D/B/P 唯一源；波次一全部拍板与提交链在此闭环，波次二开工的依据链

  **Acceptance Criteria**:
  - [ ] 全量门禁绿 + 白名单 diff
  - [ ] decision-log 波次一条目落位（含 5 拍板 + 提交链 + 遗留）
  - [ ] PROJECT_STATE/MOC 收官登记

  **QA Scenarios**:
  ```
  Scenario: 收官登记核验
    Tool: Bash
    Steps:
      1. Select-String "波次一" docs\decision-log.md → 综合条目命中
      2. git log --oneline -15 → 三批提交链完整
    Expected Result: 台账/状态/MOC 三处落位，提交链可追溯
    Evidence: .sisyphus/evidence/wave1-t12-closeout.txt
  ```

  **Commit**: YES
  - Message: `docs(governance): 波次一收官——综合台账 + 拍板落痕`
  - Files: `docs/decision-log.md`, `PROJECT_STATE.md`, `docs/README.md`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval.**

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found（重点：reroll gap 是否被动过 / 50 问外文案是否被改 / schema 是否零变更 / 根目录生成脚本是否被碰 / 前端是否零触碰）. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest --cov=app`（全量 + cov ≥ 80%）+ ruff（本批三源文件增量清零）+ mypy。Review all changed files for: `as any` 等价物、空 catch、console.log 残留、注释掉的代码、未用 import。Check AI slop：过度注释、无谓抽象、泛型命名。
  Output: `Tests [N pass/N fail] | Lint [PASS/FAIL] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  From clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Cross-task integration: P3 修复后文案批的选项渲染一致性 / 投递改写后知识通道共存。Edge cases: 直选越界数字 / 空会话 / 跳过路径。Save to `.sisyphus/evidence/wave1-final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built, nothing beyond spec. Check "Must NOT do" compliance. Detect cross-batch contamination（批次间文件面互斥是否保持）. Flag unaccounted changes（对照④稿目录逐题核对替换保真）.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| 批次 | 提交组 | Message 模式 | 前置门禁 |
|---|---|---|---|
| 1.1 | 2-3 提交 | `fix(a1): P3 序号跨题错配——直选通道绑定当前题 options`（红测+修复分提） | 批内 pytest 全绿 |
| 1.2 | 2-4 提交 | `copy(a1): 故事线 15 问说人话替换` / `copy(a1): 世界观 35 问替换+severity 移除` / `copy(a1): 开场引导语后端替换` | 契约锁+全量 |
| 1.3 | 2-3 提交 | `feat(a1): 规则6 投递改写——接住-归位-回题` | D24 回归+全量 |
| 治理 | 每批 1 提交 | `docs(governance): 波次一 1.X 批次登记` | git diff --stat 白名单核对 |

> 提交纪律：白名单 pathspec 提交（项目惯例）；每批完工 `git diff --stat` 核对零超范围。

---

## Success Criteria

### Verification Commands
```bash
# 后端全量（每批收 + 终验）
cd backend && .venv\Scripts\python -m pytest --cov=app
# Expected: ≥1627+新增 passed / 0 failed / cov ≥ 80%

# P3 病理回归
cd backend && .venv\Scripts\python -m pytest tests/unit/a1/ -k "cross_question or stale_options" -v
# Expected: 全绿

# D24 回归（1.3 收门禁）
cd backend && .venv\Scripts\python -m pytest tests/unit/a1/test_knowledge_request.py -v
# Expected: 4 用例全绿

# 范围核对（每批收）
git diff --stat  # 只允许白名单文件
```

### Final Checklist
- [ ] 全部 Must Have 落实（TDD/串行/独立提交/治理登记）
- [ ] 全部 Must NOT Have 未违反（reroll gap 未修 / 50 问封闭集合 / 零 schema / 前端零触碰 / 锚点-multi-label 未动 / D24 语义未破）
- [ ] 三批门禁全绿 + F1-F4 四审 APPROVE
- [ ] 用户明确验收后，本计划关闭；波次二 17 项拍板另议

