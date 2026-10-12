# D21 后端阶段施工计划（D20 补完 + persona_card 清理 + 主次切换/收尾/对齐循环 + D22 通用投影三件）

## TL;DR

> **Quick Summary**: D21 施工期后端阶段四件套——补完在途 TDD 半成品 D20（16 红→34/34 绿并提交）、清理 persona_card 死线、实现主次配方切换/收尾双条件/三连问/对齐循环三项新机制、落地 D22 通用投影三件（世界圣经/人物志/故事大纲）并完成 B/C/O 发号字母全项目统一。
>
> **Deliverables**:
> - D20 动态模块调用六层缺口全部补完，test_dynamic_invites 34/34 绿，全局 pytest 全绿，首次提交落库
> - persona_card.py 及寄生端点清理，impulse_coords 完整保留
> - 主∪次联合边界 + 切换机制（session/start 落定 + 未访序调整）
> - 收尾双条件检测 + 输出前确定性图谱识别函数 + 收尾三连问状态机
> - 对齐循环：α 版本体系 + 图谱摘要注入（DN5 扩点评审先行）+ 四动作提案 + 触发定序
> - D22 三件：产出池注册 + 三个五件套渲染器 + 三对端点（全 optional 档）
> - StageCode 新增 B/C/O + 冻结注释翻案单独提交 + 台账登记 + 字母全局核查报告
> - PROJECT_STATE / 治理文档同步更新
>
> **Estimated Effort**: XL（20 任务 + 4 终审）
> **Parallel Execution**: YES - 5 波
> **Critical Path**: T1→T4→T6→T10→T17→T18→T19→F1-F4

---

## Context

### Original Request
产品方指令「根据 PROJECT_STATE，开始计划」。PROJECT_STATE「进行中」节明确：D21 施工期·后端阶段待启动，含①D20 动态模块调用补完（裁决 B=随本阶段补完再提交）②persona_card.py 清理③主次配方切换/收尾双条件/对齐循环实现④D22 通用投影三件。

### Interview Summary
**Key Discussions**:
- 范围（产品方已拍板）：**A 仅后端阶段**——四件全含；前端阶段（说人话文案整改+四组件）明确排除，另行规划。
- 测试策略（产品方已拍板）：**TDD** 契约测试先行；16 个红灯测试即 D20 的 RED 基线；延续甲计划纪律（全局 pytest 全绿 + 新代码覆盖率 ≥85%，全局门禁 80）。
- D22 发号字母（产品方已拍板）：**方案一 B/C/O**——世界圣经=B（Bible）/人物志=C（Character）/故事大纲=O（Outline）；**附加硬要求：字母在全项目结构中统一、避免歧义、全局核查**。

**Research Findings**（三路 explore 行号级取证 + Metis 实地复核）:
- **D20 根因高度集中**：`_apply_worldview_invites`（guide_engine.py:338-385）已完整实现但 `_handle_message_impl`（guide_engine.py:930-1147）零调用——单一接线点转绿约 12 个红测试；独立缺口仅两处：门禁接线（progress guide_engine.py:1146 与 finalize a1_routes.py:1280-1283 未用已实现的 `core_recipe_modules` guide_engine.py:327-335）、prompt 键域冲突（test_before_invite_zero_worldview_fields 红，需排查 interviewer.py:384-530 的 `f"{mid}."` 子串来源）。3 个「碰巧绿」测试接线后才成为真验证。
- **主次切换**：creator_secondary 全代码三处引用（声明 guide_engine.py:177/写 a1_routes.py:647/读 :666）零路由确认；start 只按 primary 落定（a1_routes.py:672-676）。
- **收尾双条件**：fills 待确认 = `session.pending_proposals`（guide_engine.py:190-201），清零判定须区分 auto fills 语义；「确定性图谱识别」可拼装 module_done_ratio（a1_question_tree.py:465-494）+ stale_marker.py 现成件。
- **对齐循环**：α 小数版本纯新增（现状 finalize 只发整型 v1/v2，graph_code_issuer.py:270-273）；interviewer 现状不读图谱；四动作交互先例 = pending_proposals/resolve_proposal（guide_engine.py:401-444）+ 概念边 confirm/reject（a1_routes.py:1960-2064）。
- **D22**：注册=纯数据追加 output_modules.py（:24-147）；渲染器复用 main_module.py 五件套模具（:29-32/:35-52/:139-176/:179-234）；端点照抄 doc 八步范式（a1_routes.py:2320-2374）；三件数据源全就绪（设定模块信号/角色.*/剧情.*）。
- **发号**：StageCode 封闭枚举（graph_code_issuer.py:29-43）已占 W/M/S/TD/TC/R/G；B/C/O 未占用无字面冲突；已持久化 SQLite graph_codes 表（加成员 schema 兼容）；需翻案双冻结声明（文件头 :8 + 行注释 :26）并同步 from_str 错误消息、前端 types 副本、DB 存量回归。
- **persona_card**：persona_card.py + tests/unit/a1/test_persona_card.py 独立成文件；graphify.py/interviewer.py/open_questions.py 有 "persona_card" 字样命中——清理时须逐一确认是 import/字符串/注释。

### Metis Review
**Identified Gaps** (addressed):
- 5 个应问产品问题 → 全部以权威文档+代码先例推导默认值（见下方 Defaults Applied，摘要呈交时可推翻）
- 护栏 6 条 → 全部写入 Must NOT Have / 任务边界
- 边界情况 6 个 → 全部转为契约测试要求（主次同模块重叠/invited×切换交互/D22 半空降级/收尾竞态/对齐×收尾定序/resolve 并发）
- 波次修正：DN5 扩点评审从 Wave 4 提前为对齐循环实现前置 gate；字母 grep 清单 Wave 2 生成（只读）、终审只做复核。

---

## Work Objectives

### Core Objective
完成 D21 后端阶段全部四件：D20 还债提交、persona_card 清理、三项访谈新机制（主次切换/收尾双条件+三连问/对齐循环）、D22 通用投影三件（含 B/C/O 字母全项目统一），全程 TDD，出口 = 全局 pytest 全绿 + F1-F4 四审 APPROVE。

### Concrete Deliverables
- 代码：guide_engine.py / interviewer.py / a1_routes.py / output_modules.py / graph_code_issuer.py / main_module.py 同族三个新渲染器文件 / 新对齐循环模块
- 删除：persona_card.py + test_persona_card.py + /persona-card 端点
- 测试：test_dynamic_invites 34/34 + 各新机制契约测试（甲新代码覆盖率 ≥85%）
- 治理：decision-log 施工登记（D20 提交补账已备、B/C/O 字母、DN5 第四处扩点）+ SYSTEM_DESIGN_SPEC v6 dated amendment（字母体系）+ PROJECT_STATE 收尾更新
- 证据：`.sisyphus/evidence/task-N-*`（字母核查清单+逐条判定表为 T19 必交证据）

### Definition of Done
- [ ] `pytest backend/tests` 全绿（1264 基线 + 新增，零失败）
- [ ] `test_dynamic_invites.py` 34/34 passed
- [ ] `grep -r "persona_card" backend/app backend/tests` 零命中（排除 .venv）
- [ ] StageCode 含 B/C/O，`from_str("B")` 可解析，DB 存量 stage 无 B/C/O 冲突回归通过
- [ ] D22 三端点在空图谱 session 上均 200 + 降级披露（非 500/404）
- [ ] 字母全局核查报告落盘 `.sisyphus/evidence/task-19-letter-audit.md`
- [ ] F1-F4 四审 APPROVE + 产品方 okay

### Must Have
- D20 六层缺口全部补完（提议消费/游走插入/门禁排除/prompt 目录/键域传播/审计事件）——34/34 绿是唯一验收口径
- 主∪次联合边界在 session/start 一次落定；切换 = 联合边界内未访序调整（D13 三杠杆第一条兼容）
- 收尾双条件 = 配方问完 + fills 待确认清零（auto fills 不计入 pending_proposals 判定）
- 输出前确定性图谱识别 = 纯代码盘点（模块覆盖/缺口/版本链/stale），零 LLM
- 对齐循环 = LLM 提议 + 确定性校验 + 用户确认；LLM 绝不直写图谱（单生产单消费 + graphify 单点产出铁律不动）
- D22 三件 signal_requirements 全 optional（薄图谱照出、缺料缺省+ledger 披露、不 409）
- B/C/O 字母：翻案冻结注释**单独一笔 commit** + 台账登记；C(人物志) ≠ TC(角色投影) 在代码注释与治理文档双声明
- 治理扩点评审先于图谱摘要注入实现（DN5 第四处 LLM 消费路径）

### Must NOT Have (Guardrails)
- **禁止** D20 半绿提交（「先提交接线再修键域」）——34/34 + 全局绿是提交唯一出口（裁决 B 语义）
- **禁止** α 小数版本进入 graph_codes 表或任何持久层——α 仅存在于 finalize 前的对齐循环会话态；finalize 落库仍只产生整型 vN
- **禁止** 对齐循环范围蔓延：锁死五要素（四动作 + α 版本 + 图谱摘要注入 + 触发时机 + 用户确认）；不做对齐历史 UI、对齐结果导出、多轮对齐嵌套
- **禁止** D22 渲染器出现五件套模具之外的新装配模式（冻结结构模板 + 信号键绑定 + 确定性装配 + LLM 只叠导语 + 失败降级骨架）
- **禁止** 确定性图谱识别函数引入打分/权重逻辑——只做 module_done_ratio + stale_marker 拼装
- **禁止** persona_card 清理顺手重构相邻代码、顺手补 impulse_coords 测试（白名单制：只删 persona_card.py / test_persona_card.py / a1_routes 端点+import / 残留引用）
- **禁止** T3 prompt 键域排查演变为 prompt 体系重构——若需结构性改动，停止回报另行立项
- **禁止** LLM 直写任何图谱/会话状态（对齐四动作与 D20 invites 同为「提议+校验+确认」模式）
- **禁止** 修改 impulse_coords.py 与 /impulse-coords 端点（删壳留本体）
- **禁止** 字母核查 grep 包含 .venv/node_modules/site-packages 目录

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES（pytest + pytest-cov，1264 基线全绿；契约测试 C1-C7 先例）
- **Automated tests**: TDD——每个任务先写/补契约测试（RED）再实现（GREEN）；D20 的 16 红即现成 RED 基线
- **Framework**: pytest（backend venv：`F:\Anaconda\envs\Deepcode\python.exe` 或 backend/.venv；运行方式照 verify.ps1 惯例）
- **覆盖率**：甲计划新代码单独 ≥85%（`--cov=app --cov-report=term-missing` 按新文件过滤）；全局门禁 80 不回退

### QA Policy
每任务必含 agent 执行 QA 场景（见各任务模板）。证据存 `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`。
- **后端 API**: Bash（pytest / curl 起栈直调）——发请求、断言状态码+响应字段
- **模块级**: Bash（pytest -k 精确到测试名）——精确数字断言
- **治理/文档**: Bash（grep 清单）+ Read 判定表
- 冒烟起栈：`backend/.venv/Scripts/python -m uvicorn app.main:app --port 8000`（workdir=backend）+ curl /api/health

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1（D20 还债批——3 并行 + 1 汇合，文件所有权互斥）:
├── Task 1: D20 ①提议消费接线（guide_engine.py） [deep]
├── Task 2: D20 ③门禁接线（guide_engine.py progress + a1_routes.py finalize） [quick]
├── Task 3: D20 ⑤prompt 键域排查与修复（interviewer.py） [deep]
└── Task 4: D20 全量回归 + 首次提交（裁决 B 出口） [quick]（depends: 1,2,3）

Wave 2（清理与地基批——4 并行）:
├── Task 5: persona_card 清理（白名单制） [quick]
├── Task 6: 收尾双条件判定 + 确定性图谱识别函数 [deep]
├── Task 7: D22 产出池注册（纯数据三件） [quick]
└── Task 8: StageCode B/C/O 扩展 + 字母核查清单生成 + 冻结翻案单独提交 [deep]

Wave 3（核心机制批——5 并行，依赖 Wave 2 地基）:
├── Task 9: 主次配方结合切换（联合边界+切换） [deep]（depends: 4）
├── Task 10: 收尾三连问状态机 + 预览按动机排序 [deep]（depends: 6,7,8）
├── Task 11: D22 世界圣经渲染器（B） [deep]（depends: 7,8）
├── Task 12: D22 人物志渲染器（C） [deep]（depends: 7,8）
└── Task 13: D22 故事大纲渲染器（O） [deep]（depends: 7,8）

Wave 4（对齐循环批——评审 gate + 3 任务）:
├── Task 14: DN5 扩点评审 + 图谱摘要构造器 [deep]（depends: 4）——评审为 15/16 前置 gate
├── Task 15: α 版本体系（会话态草稿版本） [deep]（depends: 4,14 评审结论）
├── Task 16: 对齐四动作提案 + 用户确认 + stale 预警 [deep]（depends: 14）
└── Task 17: 对齐触发时机 + 与收尾/轮次定序 [deep]（depends: 15,16,10）

Wave 5（端点接线与治理收尾批）:
├── Task 18: D22 三对端点（八步范式 ×3） [unspecified-high]（depends: 11,12,13）
├── Task 19: 字母全局统一终审 + 治理文档同步 [unspecified-high]（depends: 8,18）
└── Task 20: PROJECT_STATE 收尾更新 [quick]（depends: 全部）

Wave FINAL（四审并行 → 产品方 okay）:
├── F1: 计划合规审计（oracle）
├── F2: 代码质量审查（unspecified-high）
├── F3: 真实 QA 冒烟（unspecified-high）
└── F4: 范围忠实度检查（deep）

Critical Path: T1→T4→T6→T10→T17→T18→T19→T20→F1-F4→产品方 okay
Max Concurrent: 5（Wave 3）
```

### Dependency Matrix

| 任务 | 依赖 | 被依赖 |
|---|---|---|
| 1-3 | - | 4 |
| 4 | 1,2,3 | 9,14,15 |
| 5 | - | F4 |
| 6 | 4 | 10 |
| 7 | - | 10,11,12,13,18 |
| 8 | - | 10,11,12,13,19 |
| 9 | 4 | F1 |
| 10 | 6,7,8 | 17 |
| 11-13 | 7,8 | 18 |
| 14 | 4 | 15,16 |
| 15 | 4,14 | 17 |
| 16 | 14 | 17 |
| 17 | 10,15,16 | F1 |
| 18 | 11,12,13 | 19 |
| 19 | 8,18 | 20 |
| 20 | 全部 | F1-F4 |

### Agent Dispatch Summary

- **Wave 1**: 4 任务——T1→`deep`、T2→`quick`、T3→`deep`、T4→`quick`
- **Wave 2**: 4 任务——T5→`quick`、T6→`deep`、T7→`quick`、T8→`deep`
- **Wave 3**: 5 任务——T9-T13→`deep` ×5
- **Wave 4**: 4 任务——T14→`deep`、T15→`deep`、T16→`deep`、T17→`deep`
- **Wave 5**: 3 任务——T18→`unspecified-high`、T19→`unspecified-high`、T20→`quick`
- **FINAL**: 4 任务——F1→`oracle`、F2→`unspecified-high`、F3→`unspecified-high`、F4→`deep`

---

## TODOs

- [x] 1. D20 ①提议消费接线——最大杠杆单点

  **What to do**:
  - 在 `_handle_message_impl`（guide_engine.py:930-1147）中，`interviewer.interview()` 调用（:1016）拿到 result 后，调用已实现的 `_apply_worldview_invites`（:338-385）消费 `result.worldview_invites`
  - 将 `_invite_notice(accepted)`（:389）的披露文案追加进返回 reply（说人话基调——D20 接缝定盘：披露通知说人话）
  - TDD：先跑 `pytest tests/unit/a1/test_dynamic_invites.py -v` 确认 16 红基线；接线后预期转绿约 12 个（#1-7、#10-16 中除 #8/#9 外）
  - 验证 3 个「碰巧绿」测试（test_unknown_id_dropped / test_invited_incomplete_still_finalizable / test_invited_placeholder_never_satisfies_gate）在接线后**保持绿**（从平凡绿变真验证）

  **Must NOT do**:
  - 不改 `_apply_worldview_invites` 本体（已实现且含去重/cap4/stall 重置/审计 :380-384）
  - 不动 interviewer.py（T3 领域）
  - 不动 finalize/progress 门禁（T2 领域）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]（RED→GREEN 纪律）、[`systematic-debugging`]（接线点定位）

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 T2/T3 文件段互斥——T1 改 :930-1147 区间，T2 改 :1146 与 a1_routes.py，T3 改 interviewer.py）
  - **Parallel Group**: Wave 1（with Tasks 2, 3）
  - **Blocks**: Task 4
  - **Blocked By**: None（可立即开工）

  **References**:
  **Pattern References**:
  - `backend/app/domains/creation/a1/guide_engine.py:338-385` - `_apply_worldview_invites` 完整实现（消费/去重/cap4/插入/stall 重置/审计）——直接调用即可，勿重写
  - `backend/app/domains/creation/a1/guide_engine.py:389` - `_invite_notice` 披露文案生成器
  - `backend/app/domains/creation/a1/guide_engine.py:532` - `ai_fill_excluded` 事件先例（reply 追加披露的既有模式）
  **API/Type References**:
  - `backend/app/domains/creation/a1/interviewer.py:84-88` - `worldview_invites` 字段（提议来源）；:768-775 解析（非字符串丢弃）
  **Test References**:
  - `backend/tests/unit/a1/test_dynamic_invites.py` - 34 测试全文（414 行）；红#1-7/#10-16 即本任务验收

  **Acceptance Criteria**:
  - [ ] `pytest tests/unit/a1/test_dynamic_invites.py -v` → 约 28 passed / 6 failed（剩余 #8 归 T2、#9 归 T3；实际数字以接线后实测为准并记录）
  - [ ] 3 个碰巧绿测试保持 passed

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: D20 消费接线转绿验证
    Tool: Bash (pytest)
    Preconditions: 工作区 = D20 在途状态（16红/18绿）；T1 改动已写入
    Steps:
      1. cd backend && pytest tests/unit/a1/test_dynamic_invites.py -v
      2. 统计 passed/failed 数并与 16红/18绿 基线对比
      3. 确认 test_valid_invite_inserted_after_current_module / test_audit_event_logged / test_walk_covers_invited_module 均 PASSED
    Expected Result: failed 数 ≤ 6（且仅剩 #8 门禁类与 #9 prompt 类）
    Failure Indicators: 消费类测试仍红；或碰巧绿测试转红
    Evidence: .sisyphus/evidence/task-1-wiring-green.txt

  Scenario: 接线后回归——存量访谈不受邀约影响
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/a1/ -x -q
      2. 确认无新增失败（存量 1264 基线口径）
    Expected Result: 除已知 #8/#9 外零新失败
    Evidence: .sisyphus/evidence/task-1-regression.txt
  ```

  **Commit**: NO（随 Task 4 统一提交）

- [x] 2. D20 ③门禁排除接线——core_recipe_modules 落位

  **What to do**:
  - `progress()`（guide_engine.py:1106-1147，:1146 处）的 finalizable 判定改用 `core_recipe_modules(session)`（:327-335 已实现）替代全 walk
  - finalize 路由（a1_routes.py:1272-1289，:1280-1283 missing 计算处）同样改用 `core_recipe_modules` ——受邀模块不进 missing_sections、不阻塞定稿（D20 设计⑤门禁零强制）
  - TDD：先确认红 #8（test_invited_module_not_in_missing_sections），改后转绿；test_core_recipe_still_gated / test_invited_placeholder_never_satisfies_gate 保持绿（核心配方仍被门禁）

  **Must NOT do**:
  - 不改 `core_recipe_modules` 纯函数本体
  - 不改 is_module_over_half 阈值语义（FINALIZE_MODULE_THRESHOLD 不动）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 T1/T3 段互斥；注意 T1 若同文件 git 冲突则按段合并——T2 改 :1146 单行 + a1_routes.py）
  - **Parallel Group**: Wave 1（with Tasks 1, 3）
  - **Blocks**: Task 4
  - **Blocked By**: None

  **References**:
  **Pattern References**:
  - `backend/app/domains/creation/a1/guide_engine.py:327-335` - `core_recipe_modules`（配方内模块，invited 剔除）——唯一应接入的判定源
  - `backend/app/api/a1_routes.py:1272-1289` - finalize 门禁路由（missing_sections 计算）
  **Test References**:
  - `backend/tests/unit/a1/test_dynamic_invites.py::TestGateZeroForcing` - 全组 4 测试即本任务契约

  **Acceptance Criteria**:
  - [ ] `pytest tests/unit/a1/test_dynamic_invites.py::TestGateZeroForcing -v` → 4/4 passed
  - [ ] finalize 对含未完成受邀模块的会话返回 200（不再 409 missing invited）

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 受邀模块未完成不阻塞定稿
    Tool: Bash (pytest)
    Steps:
      1. pytest "tests/unit/a1/test_dynamic_invites.py::TestGateZeroForcing::test_invited_module_not_in_missing_sections" -v
      2. pytest "tests/unit/a1/test_dynamic_invites.py::TestGateZeroForcing::test_core_recipe_still_gated" -v
    Expected Result: 两条均 PASSED（受邀豁免 + 核心仍门禁同时成立）
    Failure Indicators: 任一 FAILED
    Evidence: .sisyphus/evidence/task-2-gate.txt

  Scenario: 存量定稿行为回归
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/a1/ -k "finalize or gate" -q
    Expected Result: 零失败（默认配方/设定线门禁字节级不变——m1_default_snapshot 类测试全绿）
    Evidence: .sisyphus/evidence/task-2-gate-regression.txt
  ```

  **Commit**: NO（随 Task 4 统一提交）

- [x] 3. D20 ⑤prompt 键域冲突排查与修复

  **What to do**:
  - 复现红 #9：`pytest "tests/unit/a1/test_dynamic_invites.py::TestG5Liveness::test_before_invite_zero_worldview_fields" -v`，取得断言输出的实际冲突子串
  - 排查 `_build_prompt`（interviewer.py:384-530）区间：D20 域目录注入块（:481-494，`WORLDVIEW_DOMAIN_CATALOG` :194-209）与 JSON 契约块（:522-529）中，哪一行产生了 `f"{mid}."` 形态子串（如「设定边界.」——疑注入文本某处半角点紧随模块名）
  - 修复方向二选一（以实测证据定）：(a) 调整注入措辞使目录行不含 `{模块id}.` 拼接形态；(b) 若目录语义必须保留，则与测试断言粒度对齐（须在测试注释中逐字记录裁决理由——引用 D19 灵魂契约：故事线 prompt 零世界建构字段键）
  - 保持 TestPromptContract 两测试绿（prompt 仍含域目录+invites 指令——D20 设计⑥披露）

  **Must NOT do**:
  - **禁止**演变为 prompt 体系重构——若发现需结构性改动（如整个注入块架构调整），停止并回报，另行立项
  - 不改 `_field_catalog`（:219/:239-243）与 fills 合法键判定（:714）——键域传播已随 T1 正确

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`systematic-debugging`]（先定位根因再动手——本任务唯一「先调查」型）、[`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（interviewer.py 与 T1/T2 文件段互斥）
  - **Parallel Group**: Wave 1（with Tasks 1, 2）
  - **Blocks**: Task 4
  - **Blocked By**: None

  **References**:
  **Pattern References**:
  - `backend/app/domains/creation/a1/interviewer.py:384-530` - `_build_prompt` 全区间（排查对象）
  - `backend/app/domains/creation/a1/interviewer.py:481-494` - D20 域目录注入块（最可能冲突源）
  - `backend/app/domains/creation/a1/interviewer.py:194-209` - `WORLDVIEW_DOMAIN_CATALOG`（目录数据；注意全角冒号「：」vs 半角点「.」的形态差异）
  **Test References**:
  - `test_dynamic_invites.py::TestG5Liveness::test_before_invite_zero_worldview_fields` - 红 #9 契约（断言 `f"{mid}." not in prompt` for 10 世界建构模块）
  - `test_dynamic_invites.py::TestPromptContract` - 两绿测试（修复后须保持）

  **Acceptance Criteria**:
  - [ ] `pytest "tests/unit/a1/test_dynamic_invites.py::TestG5Liveness::test_before_invite_zero_worldview_fields" -v` → PASSED
  - [ ] `pytest "tests/unit/a1/test_dynamic_invites.py::TestPromptContract" -v` → 2/2 PASSED
  - [ ] 修复说明（根因+方案 a/b 选择理由）写入证据文件

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: prompt 键域隔离双面验证
    Tool: Bash (pytest)
    Steps:
      1. pytest "tests/unit/a1/test_dynamic_invites.py::TestG5Liveness" -v
      2. pytest "tests/unit/a1/test_dynamic_invites.py::TestPromptContract" -v
    Expected Result: G5 三测全绿（含 after_invite 含受邀字段）+ PromptContract 两测全绿
    Failure Indicators: G5 before_invite 仍红（键域泄漏）或 PromptContract 转红（目录丢失）
    Evidence: .sisyphus/evidence/task-3-prompt-keydomain.txt（含根因分析文字）

  Scenario: 故事线 prompt 快照不受污染
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/a1/ -k "prompt and snapshot" -q（含既有 prompt 快照契约）
    Expected Result: 零失败（055da41 灵魂契约——故事线零世界建构字段键——保持）
    Evidence: .sisyphus/evidence/task-3-snapshot-regression.txt
  ```

  **Commit**: NO（随 Task 4 统一提交）

- [x] 4. D20 全量回归 + 首次提交（裁决 B 出口）

  **What to do**:
  - 全量回归：`pytest`（backend 全量）——1264 基线 + test_dynamic_invites 34 全绿，零失败
  - 覆盖率：`pytest --cov=app`——新改动文件（guide_engine.py/interviewer.py/a1_routes.py）≥85%，全局 ≥80%
  - ruff 触碰文件净、mypy 新文件净
  - 提交（D20 在途三件：guide_engine.py + interviewer.py + test_dynamic_invites.py；**不得混入** 09-26 文档批未提交移动——用 `git add` 白名单精确圈定）
  - 提交消息含「补记裁决 2026-09-25，台账 D20 已登记（09-27 补记）」注脚

  **Must NOT do**:
  - 34/34 未达成或全量有任何失败 → **禁止提交**（回 T1-T3 修复）
  - 不混入任何非 D20 文件（git add 白名单制）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`verification-before-completion`]（证据先于断言）

  **Parallelization**:
  - **Can Run In Parallel**: NO（汇合点）
  - **Parallel Group**: Sequential（after Tasks 1,2,3）
  - **Blocks**: Tasks 9, 14, 15
  - **Blocked By**: Tasks 1, 2, 3

  **References**:
  **Pattern References**:
  - `backend/scripts/verify.ps1`（如存在）或 PROJECT_STATE「一键体检」惯例——三命令+覆盖率口径
  **Test References**:
  - `backend/tests/unit/a1/test_dynamic_invites.py` - 34/34 终验

  **Acceptance Criteria**:
  - [ ] `pytest` → 全绿（输出数字记入证据）
  - [ ] `pytest tests/unit/a1/test_dynamic_invites.py -v` → 34 passed 0 failed
  - [ ] `git log -1 --stat` → 恰好 3 文件（guide_engine/interviewer/test_dynamic_invites）
  - [ ] `git status` → 09-26 文档批改动仍原样未动

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: D20 还债提交完成
    Tool: Bash (pytest + git)
    Steps:
      1. cd backend && pytest -q 2>&1 | tail -5   # 全量数字
      2. pytest tests/unit/a1/test_dynamic_invites.py -q  # 34/34
      3. git add backend/app/domains/creation/a1/guide_engine.py backend/app/domains/creation/a1/interviewer.py backend/tests/unit/a1/test_dynamic_invites.py
      4. git commit -m "feat(a1): D20 dynamic worldview invites - close six gaps, 34/34 green (补记裁决 2026-09-25, 台账 D20)"
      5. git show --stat HEAD
    Expected Result: 全量零失败；提交恰 3 文件
    Failure Indicators: 任一测试失败；提交文件数 ≠3
    Evidence: .sisyphus/evidence/task-4-commit-proof.txt（含全量数字+git show 输出）
  ```

  **Commit**: YES（本任务即提交任务）
  - Message: `feat(a1): D20 dynamic worldview invites - close six gaps, 34/34 green`
  - Files: 白名单三件
  - Pre-commit: 全量 pytest 绿

- [x] 5. persona_card 清理（白名单制，删壳留本体）

  **What to do**:
  - 删除 `backend/app/domains/creation/a1/persona_card.py` 整文件（含 render_persona_card + PERSONA_NAME_PLACEHOLDER + 入口单选 sunset 接口）
  - 删除 `backend/tests/unit/a1/test_persona_card.py`
  - 摘除 a1_routes.py 的 `/persona-card` 端点与 import
  - 全库残留核查：`grep -rn "persona_card" backend/app backend/tests`（排除 .venv）——graphify.py / interviewer.py / open_questions.py 有字样命中，逐一判定并清除（import/字符串/注释三类分别处置；**若命中属 impulse_coords 相关则属保留域，报告说明**）
  - **保留不动**：impulse_coords.py + `/impulse-coords` 端点（罗盘数据源，前端零引用人格卡已核查）
  - TDD 口径：先跑既有 persona_card 测试确认删除清单边界，删后全量回归

  **Must NOT do**:
  - 不动 impulse_coords.py / /impulse-coords（删壳留本体——D21⑫）
  - 不顺手重构 a1_routes 相邻代码；不顺手补 impulse_coords 测试
  - 不动前端（前端零引用已核查，前端阶段另行处理）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2（with Tasks 6,7,8）
  - **Blocks**: F4（终审零残留证据）
  - **Blocked By**: None

  **References**:
  **Pattern References**:
  - `backend/app/api/a1_routes.py` 的 /persona-card 端点段（grep persona_card 定位）——摘除模式参照 09-13 死码批次「活文件摘线」先例（main.py 摘 import+include_router）
  **API/Type References**:
  - `backend/app/domains/creation/a1/impulse_coords.py` - **保留域**（冲动坐标本体+锚点表+apply_signal）
  **External References**:
  - `docs/decision-log.md` D21⑫（L38）- 删壳留本体裁决原文
  - `PROJECT_STATE.md` 当前阶段第四批④ - 清理四步清单（本任务执行依据）

  **Acceptance Criteria**:
  - [ ] `grep -rn "persona_card" backend/app backend/tests --include="*.py"` → 零命中（排除 .venv；若 impulse_coords 相邻命中须逐条判定并在证据说明）
  - [ ] `pytest tests/unit/a1/ -q` → 零新失败
  - [ ] `/impulse-coords` 端点契约测试仍绿（存在性证明）

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 删壳留本体双验证
    Tool: Bash (grep + pytest)
    Steps:
      1. grep -rn "persona_card" backend/app backend/tests --include="*.py" | grep -v ".venv"   # Expected: 空输出
      2. cd backend && pytest -q -k "impulse_coords or coords"   # 罗盘数据源测试全绿
      3. pytest -q   # 全量回归
    Expected Result: grep 零命中；impulse_coords 测试绿；全量零失败
    Failure Indicators: grep 有残留；或 impulse_coords/coords 测试失败（误删本体）
    Evidence: .sisyphus/evidence/task-5-persona-card-removal.txt

  Scenario: /impulse-coords 端点存活
    Tool: Bash (pytest -k 或路由断言测试)
    Steps:
      1. pytest tests/unit/a1/ -k "impulse" -v
    Expected Result: 端点存在且响应契约不变
    Evidence: .sisyphus/evidence/task-5-coords-alive.txt
  ```

  **Commit**: NO（随 Wave 5 统一提交；或经 F 审后随批提交）

- [x] 6. 收尾双条件判定 + 输出前确定性图谱识别函数（共享地基）

  **What to do**:
  - 新建纯函数模块（建议 `backend/app/domains/creation/a1/closing_gate.py` 或并入 guide_engine 惯例位置——按代码库既有组织定）：
    - `is_preset_phase_complete(session)` = 配方问题问完（复用 module_done_ratio / 问题树游走状态）**且** fills 待确认清零（`len(session.pending_proposals)==0` 且**区分 auto fills 语义**——auto 填充项不计入 pending，写契约测试钉死：存在 auto fill 时即便 pending 为空也不触发收尾）
    - `build_output_preview(file_id)` = 输出前确定性图谱识别：纯代码盘点 模块覆盖（module_done_ratio）+ 缺口清单 + 版本链（graph_code/instance）+ stale（stale_marker 双信号）——**零 LLM、零打分权重**（只拼装）
  - 输出结构含：可生成物清单（消费侧 = D22 三件+跑团件排序输入，由 T10/T18 消费）、缺口披露、stale 预警
  - TDD：先写契约测试（双条件各自命中/不命中矩阵、auto fills 语义、stale 存在时识别返回 stale）

  **Must NOT do**:
  - 禁止引入打分/权重/优先级计算逻辑（识别=事实盘点）
  - 不做端点接线（T10 消费）不做排序规则（T10）不碰 D22（T18）
  - 不改 resolve_proposal / pending_proposals 结构

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2（with Tasks 5,7,8）
  - **Blocks**: Task 10
  - **Blocked By**: Task 4（基于 D20 提交后的干净基线）

  **References**:
  **Pattern References**:
  - `backend/app/domains/creation/a1/a1_question_tree.py:465-494` - is_module_done / module_done_ratio / is_module_over_half——覆盖盘点直接复用
  - `backend/app/domains/creation/shared/stale_marker.py` - is_stale / list_user_graphs——stale 盘点直接复用
  - `backend/app/api/a1_routes.py:2263-2296` - `_graph_is_stale` 双信号判定——版本/stale 拼装参照
  **API/Type References**:
  - `backend/app/domains/creation/a1/guide_engine.py:190-201` - pending_proposals 结构（清零判定源）；:201 auto 语义 + :430-431 FIELD_SOURCE_LLM_FILL——auto fills 区分依据
  **External References**:
  - `docs/plans/2026-09-18-impulse-entry-system-spec-v1.3.md` §5.4 L69-72 - 收尾双条件+确定性图谱识别权威原文（逐字）
  - `docs/plans/2026-09-26-三大类分组与参数反馈-问题说明书.md` L58/L187 - 双条件细化（续批八）+ 识别结果为预览唯一来源（续批五）

  **Acceptance Criteria**:
  - [ ] 契约测试：双条件矩阵（问完+清零→True；问完+未清零→False；未问完→False）全绿
  - [ ] 契约测试：auto fills 存在且 pending 空 → 不触发收尾
  - [ ] 契约测试：stale_marker 存在 → build_output_preview 返回 stale 预警字段
  - [ ] 新文件覆盖率 ≥85%

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 双条件矩阵验证
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/a1/ -k "closing or preset_phase or output_preview" -v
      2. 核对矩阵用例：四象限（问完×清零）+ auto fills 边界均有对应用例
    Expected Result: 全部 PASSED，矩阵覆盖完整
    Failure Indicators: 任一象限缺失或失败
    Evidence: .sisyphus/evidence/task-6-closing-gate.txt

  Scenario: 确定性验证——同输入同输出（零 LLM）
    Tool: Bash (pytest)
    Steps:
      1. 对同一 fixture 连续调用 build_output_preview 两次，断言结果相等（测试内置）
    Expected Result: 纯函数确定性断言 PASSED
    Evidence: .sisyphus/evidence/task-6-determinism.txt
  ```

  **Commit**: NO（随 Wave 5）

- [x] 7. D22 产出池注册——三件纯数据追加

  **What to do**:
  - `backend/app/domains/creation/modules/output_modules.py` 追加三条 `OutputModuleDef`（镜像既有 8 件格式）：
    - 世界圣经（id 建议 `world_bible`，label 中文）——signal_requirements：设定模块信号键（世界本体/文明与社会/历史时间线/地理空间/力量体系/设定边界 等，全 optional）
    - 人物志（id 建议 `character_codex`）——角色.*（M11：identity/desire/key_relations/arc_direction 等，全 optional）
    - 故事大纲（id 建议 `story_outline`）——剧情.*（M12：opening_event/core_dilemma/branch_trees/lead_chain/secret_layer/tension_hole，全 optional）
  - `OUTPUT_MODULE_IDS` 闭集（:141-147）同步 + `get_output_module()` 可查
  - 注册即入池（module_registry.py:111-143 自动）——验证 MODULE_POOL 含三件
  - TDD：三件注册契约测试（ids 闭集/三档语义 required=∅ optional=全部/hard=∅——**D22 权威文本「全 optional 档」**）

  **Must NOT do**:
  - 不写渲染逻辑（T11-13）、不写端点（T18）
  - 不给任何信号键设 required/hard（D22 原文：薄图谱照出、缺料缺省+ledger 披露、不 409）
  - 不 import module_registry（文件头 :4-6 纯数据纪律）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2（with Tasks 5,6,8）
  - **Blocks**: Tasks 10, 11, 12, 13, 18
  - **Blocked By**: None

  **References**:
  **Pattern References**:
  - `backend/app/domains/creation/modules/output_modules.py:41-138` - 既有 8 件逐件格式（id/label/signal_requirements+注释即「薄图谱照出、缺料披露」先例，:45 明言「缺省走骨架披露，不 409」）
  - `backend/app/domains/creation/modules/output_modules.py:24-32` - SIGNAL_LEVELS 三档闭集 + OutputModuleDef TypedDict
  - `backend/app/domains/creation/shared/module_registry.py:85-143` - ModuleDef 三档语义（:93-95）+ 入池自动机制
  **External References**:
  - `docs/decision-log.md` D22（L39）- 「signal_requirements 全 optional 档」逐字裁决
  - `docs/plans/2026-09-27-功能分级与成本基线.md:36` - D22 三件成本定位（≈¥0.03/件，提升级）

  **Acceptance Criteria**:
  - [ ] 注册契约测试：三 id 入闭集、signal_requirements 全部值为 "optional"、required/hard 零出现
  - [ ] MODULE_POOL 查询测试：三件可查、family="output"、tier 走 TIER_MAP
  - [ ] `pytest -q` 零新失败

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 三件注册+全 optional 契约
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/ -k "output_module and (world_bible or character_codex or story_outline)" -v
      2. 断言输出含三件、档位全 optional
    Expected Result: 三件契约测试全绿
    Evidence: .sisyphus/evidence/task-7-pool-registration.txt

  Scenario: 闭集完整性回归
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/ -k "output_modules or module_pool" -q
    Expected Result: 既有 8 件+闭集元数据测试零回归
    Evidence: .sisyphus/evidence/task-7-pool-regression.txt
  ```

  **Commit**: NO（随 Wave 5）

- [x] 8. StageCode B/C/O 扩展 + 字母核查清单 + 冻结翻案单独提交

  **What to do**:
  - `graph_code_issuer.py`：StageCode 枚举（:29-43）追加 `B = "B"`（世界圣经 World Bible）/ `C = "C"`（人物志 Character Codex）/ `O = "O"`（故事大纲 Story Outline）三成员
  - 翻案双冻结声明：文件头 :8「封闭枚举…不允许添加或修改」+ :26「DO NOT add or modify」行注释——改为注明「2026-09-28 D22 施工翻案：B/C/O 三字母经产品方裁决加入（decision-log D22③）；仍为封闭枚举，新字母须台账登记」
  - 每成员 docstring 写明 `C(人物志) ≠ TC(角色投影模板)` 语义区分（Metis 护栏）
  - 同步 `from_str` 错误消息（如枚举值清单文案含 B/C/O）
  - 回归测试：(a) `issuer.next(stage="B")` 返回 `IP{seq}-B{inst}-v1` 格式且 from_str 可回读（:253-260 非 S 分支自动覆盖验证）；(b) DB 存量回归——graph_codes 表 `SELECT DISTINCT stage` 无 B/C/O 存量冲突证明（对既有测试库跑或测试内断言既有 stage 值集 ⊆ {W,M,S,TD,TC,R,G}）
  - 前端 types 字母副本：grep frontend/src 若存在 StageCode/字母枚举副本 → 同步追加 B/C/O（**仅数据追加**，用户全局统一硬要求授权；非前端阶段功能开发）
  - **单独一笔提交**（翻案治理提交，不与任何功能混笔）
  - 生成字母全局核查清单（只读）：`grep -rn` B/C/O 三字母在 代码枚举/文档字母体系节/注释 的命中清单 → 存 `.sisyphus/evidence/task-8-letter-grep-list.md`（T19 终审消费；**排除 .venv/node_modules**）

  **Must NOT do**:
  - 不改发号逻辑（_issue/new_ip/next 本体零改动——枚举成员追加即全通）
  - 不动 S 的 parent_m 特殊拼接（:81-82）
  - 提交不得混入其他任务文件

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]、[`git-master`]（治理单独提交纪律）

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 T5/T6/T7 互斥文件）
  - **Parallel Group**: Wave 2（with Tasks 5,6,7）
  - **Blocks**: Tasks 10, 11, 12, 13, 19
  - **Blocked By**: None

  **References**:
  **Pattern References**:
  - `backend/app/domains/creation/shared/graph_code_issuer.py:29-43` - StageCode 枚举（扩展点本体）
  - `backend/app/domains/creation/shared/graph_code_issuer.py:253-260` - `_issue` 非 S 分支（新字母自动覆盖的机制证明）
  - `backend/app/domains/creation/shared/graph_code_issuer.py:270-273` - W 同实例版本自增（对照：B/C/O 每次产出新实例——与 M/TD/TC 同型）
  **Test References**:
  - 既有 graph_code_issuer 测试（grep 定位）——from_str/格式断言先例
  **External References**:
  - `docs/decision-log.md` D15③（L32）+ D22③（L39）- 字母体系权威（W=世界图/M=模组图族/S=场景图 + 新 B/C/O 延伸）

  **Acceptance Criteria**:
  - [ ] `from_str("B")/from_str("C")/from_str("O")` 解析成功；`from_str("X")` 仍报错
  - [ ] 发号测试：三字母各发一号，格式 `IP{seq}-{stage}{inst}-v{ver}` 断言逐字
  - [ ] DB 存量回归测试通过（既有 stage 值不因扩展歧义）
  - [ ] 冻结注释翻案文案含「D22③ 产品方裁决 2026-09-28」+ 台账指针
  - [ ] 单独提交：`git show --stat` 仅 graph_code_issuer.py + 测试 +（若有）前端 types 副本
  - [ ] grep 清单文件落盘 evidence

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: B/C/O 发号-回读闭环
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/ -k "graph_code or stage_code or issuer" -v
      2. 核对新增用例：B/C/O 发号格式断言 + from_str 回读 + 非法字母拒绝
    Expected Result: 全绿；既有 W/M/S/TD/TC/R/G 用例零回归
    Evidence: .sisyphus/evidence/task-8-issuer-bco.txt

  Scenario: 治理单独提交验证
    Tool: Bash (git)
    Steps:
      1. git log --oneline -3
      2. git show --stat HEAD
    Expected Result: HEAD = 翻案提交，文件仅 issuer/测试/前端 types 副本；无功能文件混入
    Evidence: .sisyphus/evidence/task-8-governance-commit.txt

  Scenario: 字母核查清单生成
    Tool: Bash (grep)
    Steps:
      1. grep -rn "StageCode" backend/app frontend/src --include="*.py" --include="*.ts" | grep -v node_modules > 清单
      2. grep -rniE "\b(W|TD|TC) (=|—|·|：).*?(世界|模组|场景|图)" docs/decision-log.md docs/SYSTEM_DESIGN_SPEC_v6.md docs/governance/0_index-v0.7.md >> 清单（字母体系文档节定位）
    Expected Result: 清单文件落盘，覆盖 代码+治理文档 两域
    Evidence: .sisyphus/evidence/task-8-letter-grep-list.md
  ```

  **Commit**: YES（单独治理提交）
  - Message: `governance(issuer): unfreeze StageCode, add B/C/O for D22 projections (D22③)`
  - Files: graph_code_issuer.py + 对应测试 +（若存在）前端 types 副本
  - Pre-commit: issuer 测试绿

- [x] 9. 主次配方结合切换——主∪次联合边界 + 未访序调整

  **What to do**:
  - session/start（a1_routes.py:641-676）：primary+secondary 均有效时构造**联合边界** = 主配方 module_ids ∪ 次配方 module_ids（**同模块重叠去重只计一次**，归属按主配方规则计）；session 落定联合有序集（主配方序为基、次配方独有模块追加其后）；仅 primary 或次无效 → 行为与现状逐字节一致（零回归）
  - 切换机制：新增轻量端点（建议 `POST /api/a1/file/{file_id}/recipe-switch`，风格照既有端点）或在 chat 内信号——**按代码库惯例定**，实现「切换 = 联合边界内未访序调整」（已访模块进度保留、不重复提问；D13 三杠杆第一条兼容：只重排未访模块、R6 只前移不跳过语义不破）
  - 次配方零路由现状改造：creator_secondary 从存档字段变为参与联合边界构造（保留 profile_source 判定逻辑不变）
  - **与 D20 invited 交互**（Metis 边界）：受邀模块独立于配方边界——切换不清除 invited_modules、不清零其进度；契约测试钉死「切换后 invite 仍可完成且计入 done_ratio」
  - TDD：先写契约测试——联合边界构造（含重叠 fixture）/切换后 visited_order 调整/已访不重复/单冲动零回归/invited 交互五组

  **Must NOT do**:
  - 不改默认配方与单冲动行为（m1_default_snapshot 六用例字节级不变——回归铁律）
  - 不改 TYPE_MODULE_PRIORITY 语义（前移机制复用，非重写）
  - 切换不得跳过未访模块（R6 可达性不变式）
  - 不做两级 UI / 不做前端（D21③ 已否决；前端阶段另行）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 T10-T13 文件互斥：本任务改 a1_routes.py start 段+guide_engine 队列段——**注意与 T18 同文件不同段**，T18 在 Wave 5 时序靠后无冲突）
  - **Parallel Group**: Wave 3（with Tasks 10,11,12,13）
  - **Blocks**: F1
  - **Blocked By**: Task 4（D20 已提交的干净基线）

  **References**:
  **Pattern References**:
  - `backend/app/api/a1_routes.py:641-676` - start 落定逻辑（改造点）；:647 creator_secondary 写入；:666 读取（profile_source）；:672-676 resolve_recipe_id 单源现状
  - `backend/app/domains/creation/a1/guide_engine.py:125` - TYPE_MODULE_PRIORITY 队列驱动（联合边界序的接入点）
  - `backend/app/domains/creation/shared/module_registry.py` - RECIPES/_STORY_RECIPES 结构（联合边界构造源）
  **API/Type References**:
  - `backend/app/api/a1_routes.py:205-211` - StartRequest.impulse_primary/impulse_secondary（已就绪入参）
  **Test References**:
  - m1_default_snapshot 六用例（grep 定位）——单冲动零回归铁律
  - `backend/tests/unit/a1/test_dynamic_invites.py` - invited 交互测试的既有 fixture 复用
  **External References**:
  - `docs/plans/2026-09-18-impulse-entry-system-spec-v1.3.md` §5.4 L67 - 主∪次联合边界权威原文（逐字）
  - `docs/decision-log.md` D21⑦（L38）- 「session/start 一次落定，切换=联合边界内未访序调整」

  **Acceptance Criteria**:
  - [ ] 契约测试：主=剧情+次=设定重度 → 联合边界含两配方并集且重叠模块（若有）只计一次
  - [ ] 契约测试：切换后已访模块不重复提问、未访序按新配方前移
  - [ ] 契约测试：单冲动（无 secondary）行为与 HEAD 基线逐字节一致
  - [ ] 契约测试：切换后 invited 模块保留可完成
  - [ ] 新代码覆盖率 ≥85%；全量零回归

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 主次联合边界+切换全链
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/a1/ -k "recipe and (switch or union or secondary)" -v
      2. 核对五组契约（联合/切换/去重/单冲动回归/invited 交互）各有对应用例且全绿
    Expected Result: 五组全 PASSED
    Failure Indicators: 任一组缺失或失败；m1_default_snapshot 回归红
    Evidence: .sisyphus/evidence/task-9-recipe-switch.txt

  Scenario: API 层冒烟——start 双冲动落定
    Tool: Bash (pytest -k 或 httpx 测试)
    Steps:
      1. 对 start 端点发 impulse_primary="plot" + impulse_secondary="setting_heavy"
      2. 断言会话 recipe_modules = plot 配方 ∪ 设定重度配方（去重）
    Expected Result: 联合边界在 API 层生效
    Evidence: .sisyphus/evidence/task-9-start-api.txt
  ```

  **Commit**: NO（随 Wave 5）

- [x] 10. 收尾三连问状态机 + 可生成物预览按动机排序

  **What to do**:
  - 收尾触发接线：chat 循环（_handle_message_impl）每轮末检测 T6 的 `is_preset_phase_complete`——命中则进入**收尾态**（非阻塞：见竞态默认语义）
  - 可生成物预览：消费 T6 `build_output_preview` + T7 产出池 + T8 字母——按动机排序（**D22⑤ 规则：通用投影三件排前、跑团件标「进阶可用」**）；排序依据 = session.creator_primary 的三线归类（故事线/设定线/通用线——按 spec v1.3 §5.2 三线口径）
  - 收尾三连问状态机（新状态存 session，字段名按代码惯例）：①「生成文档还是继续访谈录入设定」（预览先行）②「缺的部分让 AI 补吗」③「要不要改天继续」——三问答案落 session（改天继续 = 同会话持久化标记，**不建新会话**）
  - **竞态默认语义（默认值，产品方可推翻）**：收尾态为非阻塞提示态——用户若输入设定内容（超出三问作答）= 视为选择「继续」（进入自由流程），双条件再次满足时重新提示；用户明确选择 = 状态机推进
  - 「生成文档」应答 → 指向既有产出端点族（M3 doc 等）+ D22 三件（T18 落地后全量可见）
  - TDD：状态机转移矩阵测试（未触发→触发→三问逐答→落定；中途偏离→回自由流程；再满足→再提示）+ 预览排序测试（故事线用户/设定线用户/通用线用户三 fixture）

  **Must NOT do**:
  - 不改 pending_proposals 结构（复用 T6 判定）
  - 不做前端（收尾面板属前端阶段四组件）
  - 三连问文案不出现内部模块名（说人话——D21⑪；文案终稿前端阶段统一整改，本任务用说人话基线文案）
  - 不实现「AI 补充」的执行逻辑（三连问只收答案；AI 补充=推断包既有机制消费，不在本任务扩）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 T9/T11-13 文件段互斥；改 guide_engine 收尾检测段 + 新状态机模块）
  - **Parallel Group**: Wave 3（with Tasks 9,11,12,13）
  - **Blocks**: Task 17（对齐×收尾定序）
  - **Blocked By**: Tasks 6, 7, 8

  **References**:
  **Pattern References**:
  - `backend/app/domains/creation/a1/guide_engine.py:401-444` - resolve_proposal 状态机先例（收尾状态机参照：pending 存 session / 显式 resolve / 兜底语义）
  - `backend/app/api/a1_routes.py:1960-2064` - 概念边 confirm/reject 端点（用户确认交互先例）
  **API/Type References**:
  - T6 交付的 `is_preset_phase_complete` / `build_output_preview`（本任务唯一判定与预览数据源）
  - T7 三件 OutputModuleDef（预览清单数据源）
  **External References**:
  - `docs/plans/2026-09-18-impulse-entry-system-spec-v1.3.md` §5.4 L69-72 - 收尾三连问+预览先行权威原文
  - `docs/decision-log.md` D21⑧（L38）+ D22⑤（L39）- 三连问同会话持久化 + 预览按动机排序
  - `docs/governance/4_ux-flow-v0.3.md` Flow 0 权威流程节 - 收尾态在旅程中的位置

  **Acceptance Criteria**:
  - [ ] 状态机转移矩阵测试全绿（触发/三问/偏离回自由/再触发/落定）
  - [ ] 预览排序测试：三线用户 fixture 各自的清单顺序断言（通用投影前、跑团件带「进阶可用」标注字段）
  - [ ] 「改天继续」落 session 持久化标记（同 file 重新加载仍在——**执行时先验证 session 持久化机制**：研究报告称 _SESSIONS 内存 dict a1_routes.py:685，与 README「store 会话存储」存在出入，若纯内存则在证据中记录实际机制与改天继续的真实存活边界）
  - [ ] D20 接缝：受邀模块问题不计入不阻塞双条件（复用 T6 测试口径）

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 收尾全链——配方问完+fills 清零 → 三连问
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/a1/ -k "closing or wrapup or three_question" -v
      2. 核对转移矩阵用例齐备
    Expected Result: 全绿
    Evidence: .sisyphus/evidence/task-10-closing-statemachine.txt

  Scenario: 偏离竞态——收尾态中输入设定内容
    Tool: Bash (pytest)
    Steps:
      1. 构造收尾态 session，注入设定类回答（非三问选项）
      2. 断言：状态机退回自由流程、设定内容被正常录入、双条件再次满足后收尾提示重现
    Expected Result: 非阻塞语义成立，无死锁
    Evidence: .sisyphus/evidence/task-10-race-default.txt

  Scenario: 预览按动机排序
    Tool: Bash (pytest)
    Steps:
      1. 三线 fixture（plot/heavy_nostalgia 设定线/unsure 通用线）各调 build_output_preview 消费端
      2. 断言清单首位：故事线→故事大纲；设定线→世界圣经；通用线→世界圣经或按 D22⑤ 通用投影排前
    Expected Result: 排序符合 D22⑤
    Evidence: .sisyphus/evidence/task-10-preview-order.txt
  ```

  **Commit**: NO（随 Wave 5）

- [x] 11. D22 世界圣经渲染器（B——Markdown 设定集）

  **What to do**:
  - 新建 `backend/app/domains/creation/modules/world_bible.py`（文件名按代码库惯例），**逐字复用五件套模具**（main_module.py 结构镜像）：
    - 冻结结构模板：设定集章节树（模块级常量，顺序即契约——建议：世界本体/文明与社会/历史时间线/地理空间/力量体系/设定边界 六章，执行时按信号键覆盖定稿）
    - 信号键绑定表：`dict[章节, tuple[信号键]]`（世界本体.* 等，与 T7 注册的 signal_requirements 一致）
    - `compile_copy` LLM 导语层：单生产点、只产文案、任何失败返回 None（照 module_compile_copy :139-176 模式）
    - `compile_document` 总装：确定性装配（答案原文直投 `_skeleton_section_body` 模式）+ LLM 导语叠加 + 失败降级骨架 + ledger 披露 `world_bible_degraded`（照 :179-234 模式）
    - `render_markdown` 单向序列化 + 溯源行（graph_code ← upstream_graph_code，含 B 字母发号）
  - 薄图谱行为：全信号缺 → 各章 body 留空 + 缺省披露（**不 409 不编造**）；半空 → 有料章正常、缺料章留空披露（件内独立降级）
  - TDD：正常图谱全章 / 空图谱降级 / 半空独立降级 / LLM 失败降级骨架 / 章节树冻结（标题增删改即测试红）五组契约

  **Must NOT do**:
  - 模具外新装配模式（如引入多轮 LLM、引入打分、动态章节）
  - 信号缺省时编造内容（诚实留空铁律）
  - 不写端点（T18）、不动 output_modules 注册（T7 已定）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 T12/T13 文件互斥——三渲染器三新文件）
  - **Parallel Group**: Wave 3（with Tasks 9,10,12,13）
  - **Blocks**: Task 18
  - **Blocked By**: Tasks 7, 8

  **References**:
  **Pattern References**:
  - `backend/app/domains/creation/modules/main_module.py:29-32` - NINE_SECTION_HEADINGS 冻结模板模式（本件照抄结构）
  - `backend/app/domains/creation/modules/main_module.py:35-52` - _SECTION_SIGNALS 信号键绑定模式
  - `backend/app/domains/creation/modules/main_module.py:112-127` - _skeleton_section_body（答案直投不编造）
  - `backend/app/domains/creation/modules/main_module.py:139-176` - module_compile_copy（LLM 单点+失败 None）
  - `backend/app/domains/creation/modules/main_module.py:179-234` - compile_document（总装+降级+ledger）
  - `backend/app/domains/creation/modules/character_projector.py` / `dice_projector.py` - 确定性投影先例
  **API/Type References**:
  - T7 注册的 world_bible OutputModuleDef（signal_requirements 键集=本件绑定表来源）
  - `backend/app/domains/creation/modules/main_module.py:84-95` - ModuleDocument 模型（溯源字段照抄：graph_code/upstream_graph_code/used_stale/upstream_ledger）
  **External References**:
  - `docs/decision-log.md` D22①②（L39）- 三件定义+五件套模具复用逐字裁决

  **Acceptance Criteria**:
  - [ ] 五组契约测试全绿；章节树冻结测试存在
  - [ ] 空图谱 fixture：compile 成功 + 各章留空 + ledger 披露（无 409/无编造）
  - [ ] 新文件覆盖率 ≥85%

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 世界圣经正常编译
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/ -k "world_bible" -v
      2. 核对五组契约全绿
    Expected Result: 全 PASSED
    Evidence: .sisyphus/evidence/task-11-world-bible.txt

  Scenario: 空图谱降级（D22 核心 promises）
    Tool: Bash (pytest)
    Steps:
      1. 空 answers fixture 调 compile_document
      2. 断言：返回文档（非异常）+ 各章 body 空 + ledger 含 world_bible_degraded/缺省披露
    Expected Result: 薄图谱照出，缺料缺省+披露，零 409
    Failure Indicators: 抛异常 / body 有编造内容
    Evidence: .sisyphus/evidence/task-11-empty-degrade.txt
  ```

  **Commit**: NO（随 Wave 5）

- [x] 12. D22 人物志渲染器（C——角色数据小说化渲染）

  **What to do**:
  - 新建 `backend/app/domains/creation/modules/character_codex.py`，五件套模具复用（同 T11 结构）：
    - 冻结章节树：按角色信号域（identity/desire/key_relations/arc_direction 等 M11 字段——执行时按 STORY_MODULES 实际子字段定稿章节）
    - 信号键绑定：角色.* 键集（与 T7 注册一致）
    - LLM 导语层**小说化语气**（本件特有：导语 prompt 强调小说化渲染——角色数据小说化渲染，D22① 原文）；仍受「只产导语、失败降级」契约约束
    - 总装/降级/序列化/溯源（含 C 字母发号）照模具
  - 薄/半空降级同 T11（件内独立）
  - TDD：五组契约（同 T11 矩阵）+ 小说化导语 prompt 契约（快照断言：prompt 含小说化指令且不含章节树外的字段指令）

  **Must NOT do**:
  - 同 T11（模具纪律/不编造/不写端点）
  - LLM 不得改写用户原话事实（导语=渲染语气，数据=用户答案直投）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（三渲染器文件互斥）
  - **Parallel Group**: Wave 3（with Tasks 9,10,11,13）
  - **Blocks**: Task 18
  - **Blocked By**: Tasks 7, 8

  **References**:
  **Pattern References**:（同 T11 全套 main_module.py 模具行号）
  - 另参照 `backend/app/domains/creation/modules/output_modules.py:78` - 角色投影既有 角色.identity/key_relations 信号绑定先例
  **API/Type References**:
  - `backend/app/domains/creation/story/story_modules.py`（M11 角色字段定义——章节树数据源；路径以 grep 实际为准）
  **External References**:
  - `docs/decision-log.md` D22①（L39）- 「人物志（角色数据小说化渲染）」逐字

  **Acceptance Criteria**:
  - [ ] 五组契约全绿 + 小说化导语 prompt 快照契约绿
  - [ ] 空角色信号 → 文档照出+披露；新文件覆盖率 ≥85%

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 人物志编译+小说化导语
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/ -k "character_codex" -v
      2. 核对契约矩阵 + prompt 快照
    Expected Result: 全绿；prompt 含小说化指令、不含越权字段指令
    Evidence: .sisyphus/evidence/task-12-character-codex.txt

  Scenario: 空角色信号降级
    Tool: Bash (pytest)
    Steps:
      1. 无 角色.* 答案 fixture 编译 → 断言文档+空章+披露
    Expected Result: 薄图谱照出零 409
    Evidence: .sisyphus/evidence/task-12-empty-degrade.txt
  ```

  **Commit**: NO（随 Wave 5）

- [x] 13. D22 故事大纲渲染器（O——剧情信号叙事化渲染）

  **What to do**:
  - 新建 `backend/app/domains/creation/modules/story_outline.py`，五件套模具复用（同 T11 结构）：
    - 冻结章节树：按剧情信号域（opening_event/core_dilemma/branch_trees/lead_chain/secret_layer/tension_hole——M12 字段定稿章节）
    - 信号键绑定：剧情.* 键集（与 T7 一致）
    - LLM 导语层叙事化语气（D22①「剧情信号叙事化渲染」）；契约同模具
    - 总装/降级/序列化/溯源（含 O 字母发号）
  - 薄/半空降级同 T11
  - TDD：五组契约 + 叙事化导语 prompt 快照

  **Must NOT do**: 同 T11/T12

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（三渲染器文件互斥）
  - **Parallel Group**: Wave 3（with Tasks 9,10,11,12）
  - **Blocks**: Task 18
  - **Blocked By**: Tasks 7, 8

  **References**:
  **Pattern References**:（同 T11 全套 main_module.py 模具行号）
  - `backend/app/domains/creation/modules/main_module.py:36/:41` - 剧情.opening_event/core_dilemma 既有绑定先例
  **API/Type References**:
  - story_modules.py M12 剧情字段（章节树数据源）
  **External References**:
  - `docs/decision-log.md` D22①（L39）- 「故事大纲（剧情信号叙事化渲染）」逐字

  **Acceptance Criteria**:
  - [ ] 五组契约全绿 + prompt 快照绿；新文件覆盖率 ≥85%

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 故事大纲编译+叙事化导语
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/ -k "story_outline" -v
    Expected Result: 全绿
    Evidence: .sisyphus/evidence/task-13-story-outline.txt

  Scenario: 空剧情信号降级
    Tool: Bash (pytest)
    Steps:
      1. 无 剧情.* 答案 fixture 编译 → 文档+空章+披露
    Expected Result: 薄图谱照出零 409
    Evidence: .sisyphus/evidence/task-13-empty-degrade.txt
  ```

  **Commit**: NO（随 Wave 5）

- [x] 14. DN5 扩点评审（前置 gate）+ 图谱摘要构造器

  **What to do**:
  - **先评审后实现**（Metis 护栏：评审是 T15/T16 的前置 gate 非并行项）：
    - 评审对象：图谱摘要注入 interviewer = DN5 清单**第四处 LLM 消费路径**（既有三处 = interviewer/module_compile/inference_pack）
    - 评审产出：治理登记草案（decision-log DN5 条目扩点注记 + 单生产单消费契约表述——摘要为「只读消费」非生产方变更；graphify 单点产出不动）写入证据文件
    - 评审结论落 decision-log（本任务内完成登记——若需产品方终审格式，按台账元规则落盘即生效，施工不阻塞）
  - **图谱摘要构造器**（纯代码，非 LLM）：新模块（建议 `backend/app/domains/creation/a1/graph_digest.py`）：
    - 输入：会话图谱（_FILES[file_id]["graph_json"] 或阶段性编译产物）+ 受邀/配方上下文
    - 输出：**紧凑摘要**（每模块关键实体/条目清单——问题说明书 L181「紧凑摘要非全图」）+ 结构化标记（供 prompt 注入与测试断言）
    - 确定性：纯函数、同输入同输出
  - 注入路径：interviewer prompt 增加可选摘要块（有图谱时注入、无图谱零变化——**存量行为零回归**）；prompt 快照断言注入标记
  - TDD：摘要构造器纯函数测试（有图/无图/部分图）+ prompt 注入快照 + 无图零变化回归

  **Must NOT do**:
  - 摘要构造器不调用 LLM（纯代码装配）
  - 不实现四动作（T16）、不实现触发时机（T17）
  - 注入块不得破坏 G5 键域契约（D20/T3 的 prompt 键域隔离——摘要块内不出现 `{模块id}.` 裸键形态，用中文标签或标记包裹）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]、[`writing-plans`]（治理登记文本）

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 T9-T13 文件互斥；本任务先于 T15/T16 启动——Wave 4 首任务）
  - **Parallel Group**: Wave 4（gates Tasks 15, 16）
  - **Blocks**: Tasks 15, 16
  - **Blocked By**: Task 4

  **References**:
  **Pattern References**:
  - `backend/app/api/a1_routes.py:688/:1400` - graph_json 存取（摘要输入源）
  - `backend/app/domains/creation/graphify.py` - 图谱结构（GraphNode/EdgeType——摘要遍历依据）
  - `backend/app/domains/creation/a1/interviewer.py:481-529` - prompt 注入块先例（D20 域目录注入——摘要注入照此模式，注意键域教训）
  **API/Type References**:
  - DN5 既有三处：interviewer（访谈）/ module_compile（main_module.py:139-176）/ inference_pack——扩点评审对照清单
  **External References**:
  - `docs/plans/2026-09-26-三大类分组与参数反馈-问题说明书.md` L178/L181 - 「新 LLM 消费路径须治理扩点评审」+「紧凑摘要非全图」逐字
  - `docs/decision-log.md` D21⑬（L38）- 扩点评审随施工条款
  - `PROJECT_STATE.md` 遗留问题 DN5 行 - 第四处预告（本任务兑现）

  **Acceptance Criteria**:
  - [ ] decision-log DN5 条目扩点注记已落盘（第四处：图谱摘要注入，只读消费性质）
  - [ ] 摘要构造器测试：有图/无图/部分图三态 + 确定性断言全绿
  - [ ] prompt 快照：注入块存在（有图时）+ 无图时 prompt 与 HEAD 基线逐字节一致
  - [ ] G5 键域契约回归绿（test_before_invite_zero_worldview_fields 不因摘要块转红）

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: DN5 扩点评审登记
    Tool: Bash (git diff docs/decision-log.md)
    Steps:
      1. grep -n "第四处\|graph_digest\|图谱摘要" docs/decision-log.md
      2. 确认 DN5 扩点注记存在且表述为只读消费
    Expected Result: 注记落盘、单生产单消费铁律表述无破坏
    Evidence: .sisyphus/evidence/task-14-dn5-review.txt

  Scenario: 摘要三态+注入快照
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/a1/ -k "digest or graph_summary" -v
      2. pytest tests/unit/a1/test_dynamic_invites.py::TestG5Liveness -v   # 键域回归
    Expected Result: 摘要测试全绿 + G5 全绿
    Evidence: .sisyphus/evidence/task-14-digest.txt
  ```

  **Commit**: NO（治理注记随 Wave 5 docs 提交；构造器代码随 Wave 5）

- [x] 15. α 版本体系——会话态草稿版本递进

  **What to do**:
  - **会话内存态**草稿版本（Metis 护栏：α 不进 graph_codes 表/任何持久层）：新纯函数或轻状态（建议并入 graph_digest 同族模块或新 `draft_version.py`）：
    - 版本序：v1 会话定稿基线 → 对齐循环草稿 α0.1 → α0.11/α0.12…（D15③ α-β 语义延伸到输出层——**仅内存标记**）
    - finalize 落库仍只发整型 vN（graph_code_issuer 现行不变）；α 之后 finalize → 下一整型版本（v1.1 草稿期后 finalize 产 v2 而非 v1——序关系单测钉死）
  - **输出物 α 版本可见标记**（D21⑬）：一切输出物（含 D22 三件、主模组 doc）携带版本标记字段（α 期间可见「α0.1」、定稿后 vN）——ModuleDocument 类产物模型加可选 version_label 字段（additive，存量产物无字段=无标记，兼容）
  - TDD：版本序单测（v1→α0.1→α0.11→finalize→v2）/ α 不落库断言（graph_codes 表无小数版本）/ 输出物标记字段三态（α 期/定稿/存量无）

  **Must NOT do**:
  - **禁止** α 进持久层（唯一硬红线——Metis 护栏 + 治理登记）
  - 不改 graph_code_issuer 发号逻辑（整型 vN 机制零改动）
  - 不动既有产物存储结构（version_label 为 additive 可选字段）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（评审结论到达后与 T16 并行）
  - **Parallel Group**: Wave 4（with Tasks 16; after 14）
  - **Blocks**: Task 17
  - **Blocked By**: Tasks 4, 14（评审结论：α 语义与摘要标记的衔接）

  **References**:
  **Pattern References**:
  - `backend/app/domains/creation/shared/graph_code_issuer.py:270-273` - W 同实例版本自增（对照：α 与其语义差异——内存 vs 落库）
  - `backend/app/domains/creation/modules/main_module.py:84-95` - ModuleDocument（version_label additive 接入点）
  **External References**:
  - `docs/decision-log.md` D15③（L32）- α0.1→0.11/0.12→β→0.21→1.0 版本方案权威原文
  - `docs/decision-log.md` D21⑬（L38）- 「阶段性草稿编译复用 D15③ α-β 版本递进」+「输出物 α 版本可见标记」

  **Acceptance Criteria**:
  - [ ] 版本序单测全绿（含 v1.1 后 finalize → v2 断言）
  - [ ] α 不落库断言绿（graph_codes stage/version 值域测试）
  - [ ] version_label 三态测试绿；全量零回归

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: α 版本序+不落库
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/ -k "alpha or draft_version or version_label" -v
      2. 核对序关系用例（v1→α0.1→α0.11→finalize→v2）与不落库断言
    Expected Result: 全绿
    Evidence: .sisyphus/evidence/task-15-alpha-version.txt

  Scenario: 持久层零污染
    Tool: Bash (pytest)
    Steps:
      1. 跑一轮对齐循环草稿编译后，断言 graph_codes/issuer 状态与编译前一致
    Expected Result: α 全程内存态
    Evidence: .sisyphus/evidence/task-15-no-persistence.txt
  ```

  **Commit**: NO（随 Wave 5）

- [x] 16. 对齐四动作提案 + 用户确认 + stale 影响预警

  **What to do**:
  - 对齐提案数据模型：四动作（**关联/去重/矛盾/更新**——枚举封闭，逐字）：每提案 = {动作, 目标（图谱节点/边标识）, 内容, 影响预警（stale 链——「将使 M v1 过期」型文案）}
  - LLM 提议层（新 LLM 生产点评审已由 T14 覆盖）：输入 = 图谱摘要（T14）+ 用户新输入；输出 = 0-N 条结构化提案——**LLM 只提议**，确定性校验器（提案目标必须存在于图谱、动作合法、目标键域合法）单点过滤
  - 用户确认：复用推断包模式——提案入 `pending_proposals` 同族结构（新类型键或独立 pending 对齐容器，按 guide_engine 惯例）；确认端点照 /edge/{key}/confirm 模式（confirm 应用/decline 丢弃）；**应用 = 确定性代码执行**（改图谱摘要缓存/标记 stale/记录 open_question——**LLM 绝不直写图谱**）
  - stale 影响预警：提案携带将过期的下游产物清单（复用 stale_marker 派生关系）
  - TDD：四动作各一条提案→校验→确认→应用契约测试；非法提案（目标不存在/动作外）被确定性校验拒绝测试；decline 零副作用测试

  **Must NOT do**:
  - **禁止** LLM 直写图谱/会话状态（应用动作全部确定性代码——D21⑬ 铁律）
  - 不做对齐历史 UI / 对齐结果导出 / 多轮对齐嵌套（Metis 锁死）
  - 不实现触发时机（T17）
  - 提案文案说人话（D21⑪——引原话转述，不报模块/字段名；推测卡例外条款参照）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 T15 并行；T17 依赖本任务与 T15）
  - **Parallel Group**: Wave 4（with Task 15; after 14）
  - **Blocks**: Task 17
  - **Blocked By**: Task 14（评审 gate + 摘要构造器）

  **References**:
  **Pattern References**:
  - `backend/app/domains/creation/a1/guide_engine.py:401-444` - resolve_proposal（用户确认状态机先例——确认应用/拒绝丢弃语义照抄）
  - `backend/app/api/a1_routes.py:1960-2064` - 概念边 confirm/reject 端点（确认端点模式）
  - `backend/app/domains/creation/shared/stale_marker.py` - mark_downstream_stale（影响预警数据源）
  - `backend/app/domains/creation/a1/inference_pack.py`（M4a 推断包——grep 定位）- LLM 提议+用户判定的完整先例（本任务的最近亲）
  **API/Type References**:
  - T14 图谱摘要构造器（提案输入）+ T15 α 版本（草稿编译触发素材）
  **External References**:
  - `docs/plans/2026-09-26-三大类分组与参数反馈-问题说明书.md` L181-188 - 四动作+预警+确认交互建议方案（D21⑬ 已立项确认）
  - `docs/decision-log.md` D21⑬（L38）- 「LLM 提议+确定性校验+用户确认；LLM 绝不直写图谱」

  **Acceptance Criteria**:
  - [ ] 四动作契约测试各 ≥1 条全绿（提议→校验→确认→应用四段）
  - [ ] 非法提案拒绝测试绿（确定性校验器单点）
  - [ ] decline 零副作用绿；应用路径全程无 LLM 写入（断言图谱变更仅来自确定性代码）
  - [ ] stale 预警含下游产物清单断言

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 四动作全链（以「关联」为例 + 其三动作各一）
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/a1/ -k "align and (proposal or action)" -v
      2. 核对四动作用例齐备 + 校验拒绝 + decline 零副作用
    Expected Result: 全绿
    Evidence: .sisyphus/evidence/task-16-align-actions.txt

  Scenario: 铁律验证——LLM 零直写
    Tool: Bash (pytest)
    Steps:
      1. 注入 FakeLLM 提案（含一条非法目标提案）
      2. 断言：非法提案被确定性校验丢弃；合法提案仅经用户确认后由代码应用
    Expected Result: LLM 输出仅能到达「提案池」，无法触达图谱写入路径
    Failure Indicators: 任何测试路径显示 LLM 输出直接修改图谱
    Evidence: .sisyphus/evidence/task-16-no-llm-write.txt
  ```

  **Commit**: NO（随 Wave 5）

- [x] 17. 对齐触发时机 + 与收尾/轮次定序

  **What to do**:
  - **每轮轻量命中检测**：chat 每轮后，确定性检测用户新输入与图谱摘要的关键词/实体命中（复用 interviewer 既有锚定关键词机制 semantic_compiler guide_engine.py:53 同族——**轻量纯代码**，不调 LLM）；命中 → 触发 T16 提议流程
  - **模块边界深对齐**：模块完成边界处（sync_position 跨模块时）做一次深对齐（调 LLM 提议——消费 T14 摘要）
  - **定序规则**（Metis 边界——须显式定序并测试）：同帧多信号优先级 = **先对齐后收尾**（对齐提案 pending 时收尾提示延后至对齐 resolve；D20 受邀问题不计入收尾的接缝语义保持）
  - **resolve 并发**：对齐提案 pending 期间用户发新消息 → 照既有 resolve_proposal 先例（提案保留、新消息正常处理）；回归测试确认无死锁/无双花
  - TDD：轻量命中触发/不触发矩阵、模块边界深对齐触发、对齐×收尾同帧定序、pending 期间新消息四组

  **Must NOT do**:
  - 轻量检测不调 LLM（每轮 LLM 调用 = 0——成本纪律，功能分级「必须级」成本口径）
  - 不做多轮对齐嵌套
  - 定序不得破坏 D20 接缝（受邀问题不阻塞收尾）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`、`systematic-debugging`]

  **Parallelization**:
  - **Can Run In Parallel**: NO（Wave 4 汇合点）
  - **Parallel Group**: Sequential（after Tasks 10, 15, 16）
  - **Blocks**: F1
  - **Blocked By**: Tasks 10, 15, 16

  **References**:
  **Pattern References**:
  - `backend/app/domains/creation/a1/guide_engine.py:53` - semantic_compiler（锚定关键词编译——轻量命中检测扩展点）
  - `backend/app/domains/creation/a1/guide_engine.py:269-315` - sync_position（模块边界检测点）
  - T10 收尾状态机（定序对象）、T16 提议流程（触发对象）、T14 摘要（深对齐输入）
  **External References**:
  - `docs/plans/2026-09-26-三大类分组与参数反馈-问题说明书.md` L185 - 触发时机双档（每轮轻量 + 模块边界深对齐）
  - `docs/plans/2026-09-18-impulse-entry-system-spec-v1.3.md` §5.4 L74 - 自由流程与对齐循环衔接

  **Acceptance Criteria**:
  - [ ] 轻量命中矩阵测试绿（命中触发/未命中零调用）
  - [ ] 模块边界深对齐触发测试绿
  - [ ] 对齐×收尾同帧定序测试绿（先对齐后收尾；对齐 pending 时收尾延后）
  - [ ] pending 期间新消息回归绿（无死锁）；D20 接缝保持（受邀不阻塞收尾复测）

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 触发矩阵+定序
    Tool: Bash (pytest)
    Steps:
      1. pytest tests/unit/a1/ -k "align and (trigger or ordering or timing)" -v
      2. 核对四组测试齐备
    Expected Result: 全绿
    Evidence: .sisyphus/evidence/task-17-trigger-ordering.txt

  Scenario: 每轮零 LLM 纪律
    Tool: Bash (pytest)
    Steps:
      1. 无命中 fixture 跑 5 轮 chat，断言提议 LLM 调用计数 = 0（FakeLLM 计数器）
    Expected Result: 轻量检测纯代码
    Evidence: .sisyphus/evidence/task-17-zero-llm.txt
  ```

  **Commit**: NO（随 Wave 5）

- [x] 18. D22 三对端点——八步范式 ×3

  **What to do**:
  - a1_routes.py 追加三对端点（照 doc 端点 finalize 八步范式 a1_routes.py:2320-2374 逐字模式）：
    - `POST /api/a1/file/{file_id}/world-bible` + `GET .../world-bible?format=md|json`
    - `POST /api/a1/file/{file_id}/character-codex` + `GET .../character-codex?format=md|json`
    - `POST /api/a1/file/{file_id}/story-outline` + `GET .../story-outline?format=md|json`
  - 八步逐件复刻：校验 → stale 检测留痕 → provider 注入（失败降级 None）→ **issuer.next(stage="B"/"C"/"O")** 发号 → register_graph 注册 → 渲染器 compile（T11-13）→ md/json 双序列化 → `rec[...]` additive 键持久化
  - GET 端点：stored 无 → 409 pending_finalize 同语义；md → PlainTextResponse
  - 接入收尾预览：T10 的 build_output_preview 消费端清单纳入三件（若 T10 时端点未就绪留了占位，此处收口）
  - TDD：三端点各照 doc 端点既有测试模式写八步断言；**空图谱 session 调三 POST 均 200 + 降级披露**（D22 全 optional 核心 promises——不是 409/500）

  **Must NOT do**:
  - 不改 doc/dice-template 既有端点（纯追加）
  - 不引入新的门禁（_require_finalized 语义照抄——三件在 finalize 后可用，与 doc 同口径）
  - stale 永不 409（照 M3 区块注释 :2253-2260 惯例）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`test-driven-development`]

  **Parallelization**:
  - **Can Run In Parallel**: NO（三对端点同文件同任务；Wave 5 首任务）
  - **Parallel Group**: Sequential（after Tasks 11,12,13）
  - **Blocks**: Task 19
  - **Blocked By**: Tasks 11, 12, 13

  **References**:
  **Pattern References**:
  - `backend/app/api/a1_routes.py:2320-2374` - POST /doc 八步范式（**逐件照抄模式**）
  - `backend/app/api/a1_routes.py:2377-2386` - GET /doc?format 双序列化
  - `backend/app/api/a1_routes.py:2389+` - dice-template 零 LLM 四步法（对照）
  - `backend/app/api/a1_routes.py:2253-2260` - M3 产出端点区块注释（路径域/stale 永不 409 惯例）
  **API/Type References**:
  - T11-13 三渲染器 compile_document（装配核心）；T8 issuer B/C/O 发号
  **External References**:
  - `docs/decision-log.md` D22①⑤（L39）- 三件定义 + 收尾预览排前
  - `docs/plans/2026-09-27-功能分级与成本基线.md:36` - D22 三件 ≈¥0.03/件（免费线可跑通口径）

  **Acceptance Criteria**:
  - [ ] 三对端点八步测试各全绿（含发号格式 `IP*-B1-v1`/`-C1-v1`/`-O1-v1` 断言）
  - [ ] 空图谱 session：三 POST 均 200 + ledger 含降级披露
  - [ ] md/json 双格式 GET 测试绿；stale 场景留痕不 409 测试绿
  - [ ] 全量零回归

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 三端点正常+空图谱双路
    Tool: Bash (pytest + 起栈 curl)
    Steps:
      1. pytest tests/unit/a1/ -k "world_bible or character_codex or story_outline and endpoint" -v
      2. 起栈（uvicorn）+ curl -X POST /api/a1/file/{空图谱file}/world-bible、/character-codex、/story-outline
      3. 断言三响应 200 + 各含 degraded 披露字段
    Expected Result: 全 optional promises 兑现——薄图谱照出零 409
    Failure Indicators: 任一 409/500；响应无披露
    Evidence: .sisyphus/evidence/task-18-endpoints.txt

  Scenario: 发号与溯源
    Tool: Bash (curl + jq 或 pytest)
    Steps:
      1. 正常图谱 file 三 POST
      2. 断言响应 graph_code 形如 IP{seq}-B1-v1 / -C1-v1 / -O1-v1，upstream_graph_code 指向 W 图谱
    Expected Result: B/C/O 发号 + 血缘正确
    Evidence: .sisyphus/evidence/task-18-issuance.txt
  ```

  **Commit**: NO（随 Wave 5 统一功能提交）

- [x] 19. 字母全局统一终审 + 治理文档同步

  **What to do**:
  - 消费 T8 清单（`.sisyphus/evidence/task-8-letter-grep-list.md`）：逐条判定并处置——
    - 代码域：StageCode 枚举/from_str/错误消息/前端 types 副本 B/C/O 同步核验
    - 治理域：SYSTEM_DESIGN_SPEC_v6 **dated amendment**（照 v6.1 模式，字母体系节补 B=世界圣经/C=人物志/O=故事大纲 + C≠TC 声明 + 指针 decision-log D22③）；decision-log D22③ 补施工完成注记；0_index-v0.7 / MOC（docs/README.md）/ HUB.md 字母相关行同步（如涉及）；前端手册 §8 如有字母引用同步
  - 产出**字母核查报告**：`.sisyphus/evidence/task-19-letter-audit.md` = grep 清单 + 逐条判定表（命中处/是否需改/已改否/理由）——产品方「全局核查」硬要求的交付物
  - 起栈冒烟抽查：三产物发号-回读-导出全链含字母（消费 T18 端点）

  **Must NOT do**:
  - 不改 v6.1 既有注记正文（dated amendment 新增段，不动旧文）
  - 核查 grep 排除 .venv/node_modules
  - 不顺手做 B1 终审材料（另行）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`git-master`]（治理文档版本纪律）

  **Parallelization**:
  - **Can Run In Parallel**: NO（终审串行）
  - **Parallel Group**: Sequential（after Task 18）
  - **Blocks**: Task 20
  - **Blocked By**: Tasks 8, 18

  **References**:
  **Pattern References**:
  - `docs/SYSTEM_DESIGN_SPEC_v6.md` v6.1 dated amendment 段（2026-09-27）——本批 amendment 格式模板
  - `docs/decision-log.md` D15③/D22 - 字母权威基线（amendment 引用源）
  - `docs/HUB.md` / `docs/README.md` / `docs/governance/0_index-v0.7.md` - 同步目标（维护纪律：新文件登记/升版改行）
  **Test References**:
  - T8 issuer 测试（终审复核对象）
  **External References**:
  - 产品方 2026-09-28 指令——「字母在全项目结构中统一，避免歧义！全局核查」（本任务的直接授权与验收来源）

  **Acceptance Criteria**:
  - [ ] 核查报告落盘：清单逐条有判定（含「无需改」的判定理由），零未处置项
  - [ ] v6 dated amendment 含 B/C/O 定义 + C≠TC 声明
  - [ ] decision-log D22③ 施工完成注记 + DN5 第四处注记（T14 已落，复核）双在
  - [ ] 冒烟：B/C/O 三产物端到端发号-回读-导出成功

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: 字母全局核查报告完整性
    Tool: Bash (Read 报告 + grep 抽查)
    Steps:
      1. 读 .sisyphus/evidence/task-19-letter-audit.md
      2. 抽查 3 条判定：任选清单命中处 grep 实际代码/文档验证判定正确
    Expected Result: 报告逐条判定、抽查全符合
    Evidence: .sisyphus/evidence/task-19-audit-verify.txt

  Scenario: 治理文档三同步
    Tool: Bash (grep)
    Steps:
      1. grep -n "世界圣经\|人物志\|故事大纲" docs/SYSTEM_DESIGN_SPEC_v6.md docs/decision-log.md docs/HUB.md
      2. 确认三件+字母在各权威文档可检索
    Expected Result: 全项目字母体系统一——任一文档查 B/C/O 均有定义且互相一致
    Evidence: .sisyphus/evidence/task-19-docs-sync.txt
  ```

  **Commit**: YES（Wave 5 功能+治理统一提交的第二笔 docs 部分，或与 T18 同批分两笔）
  - Message: `feat(a1): D21 backend - lifecycle/switch/alignment + D22 projections` （代码笔）/ `docs(governance): letter system B/C/O unification + PROJECT_STATE sync`（文档笔）
  - Files: 代码全部新改文件 / 治理文档+PROJECT_STATE
  - Pre-commit: 全量 pytest 绿 + F 审前

- [x] 20. PROJECT_STATE 收尾更新

  **What to do**:
  - PROJECT_STATE.md 按既定格式更新：「当前阶段」新增本批条目（D21 后端阶段完成——四件+字母统一；提交链号）；「已完成」移入；「进行中」刷新（D21 前端阶段待启动——说人话文案整改+四组件，指针前端手册 §8）；「下一步」更新（前端阶段 → B1 重定义提案终审〔按 D21 产物增补〕+ DN1/DN2 追认 + ⭐ 终审项）
  - MOC（docs/README.md）变更记录行同步（若 T19 未覆盖）
  - 口径纪律：基线数字以 verify.ps1/pytest 实测输出为源，禁手抄

  **Must NOT do**:
  - 不嵌未经实测的数字（AI 数值人工验证纪律）
  - 不改其他历史条目

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO（终任务）
  - **Parallel Group**: Sequential（after all）
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 1-19 全部

  **References**:
  **Pattern References**:
  - `PROJECT_STATE.md` 当前阶段/已完成/进行中/下一步四节既有格式（照 09-27 各批条目风格）
  - `.sisyphus/evidence/baseline-latest.txt`（verify.ps1 快照——基线数字唯一源）

  **Acceptance Criteria**:
  - [ ] 四节更新完整；基线数字与实测输出一致
  - [ ] 前端阶段待启动指针明确（前端手册 §8 整改清单+四组件）

  **QA Scenarios (MANDATORY)**:
  ```
  Scenario: PROJECT_STATE 一致性
    Tool: Bash (Read + pytest 数字比对)
    Steps:
      1. 读 PROJECT_STATE 本批条目中的测试基线数字
      2. 与 task-4/F2 证据中的实测数字比对
    Expected Result: 数字逐字一致（禁手抄纪律兑现）
    Evidence: .sisyphus/evidence/task-20-state-consistency.txt
  ```

  **Commit**: NO（并入 T19 docs 笔；若 F 审后有修正随终批）

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval.**

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run pytest, curl endpoint). For each "Must NOT Have": grep codebase for forbidden patterns (α 进持久层 / LLM 直写图谱 / persona_card 残留 / 渲染器模具外模式) — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [20/20] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run 全量 pytest + 覆盖率（新文件 ≥85%）+ ruff + mypy（新文件净）. Review all changed files for: `as any` 型逃逸、empty catches、console.log 残留、注释掉的代码、未用 import. Check AI slop：过度注释、过度抽象、泛型命名（data/result/item/temp）. Output: `Tests [N pass/0 fail] | Cov [新文件 ≥85%] | Ruff [PASS] | Files [N clean] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  起栈（uvicorn + curl）。执行全部任务 QA 场景的端到端版本：D20 invites 全链（故事会话提及世界观→插入→门禁→审计）、主次切换、收尾三连问、对齐循环一轮、D22 三件空图谱+正常图谱双路。证据存 `.sisyphus/evidence/final-qa/`. Output: `Scenarios [N/N pass] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff since plan start). Verify 1:1——无遗漏无蔓延。检查 Must NOT do 合规。检测跨任务污染（文件所有权互斥）。Output: `Tasks [20/20 compliant] | Contamination [CLEAN] | VERDICT`

---

## Commit Strategy

| 批 | 提交 | 消息 | 前置 |
|---|---|---|---|
| Wave 1 后 | T4 | `feat(a1): D20 dynamic worldview invites - close six gaps, 34/34 green` | 34/34 + 全量绿 |
| T8 内 | 单独一笔 | `governance(issuer): unfreeze StageCode, add B/C/O for D22 projections` | 枚举回归绿 |
| Wave 5 后 | T19/T20 | `feat(a1): D21 backend - lifecycle/switch/alignment + D22 projections` + `docs: sync PROJECT_STATE & governance` | F 审前 |

> 治理纪律：D20 提交消息中注明「补记裁决 2026-09-25，台账 D20 已登记」；B/C/O 翻案单独提交不得与功能混笔。

---

## Success Criteria

### Verification Commands
```powershell
# 后端全量（workdir=backend）
pytest                                    # Expected: 全绿（1264 基线+新增，0 failed）
pytest tests/unit/a1/test_dynamic_invites.py -v   # Expected: 34 passed
pytest --cov=app --cov-report=term-missing # 新文件 ≥85%，全局 ≥80%
# persona_card 清零
grep -rn "persona_card" app tests         # Expected: 零命中
# 字母核查
grep -rn "StageCode" app ../frontend/src  # B/C/O 三处同步（枚举/from_str/前端 types 副本）
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass（含 34/34、字母回归、四动作契约、D22 降级）
- [ ] 字母全局核查报告 + 逐条判定表落盘
- [ ] PROJECT_STATE 已更新（本批四件 + 前端阶段待启动指针）
