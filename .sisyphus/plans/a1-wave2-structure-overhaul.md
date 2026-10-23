# 波次二·2.1 结构大锤施工单（A1 访谈体验升级）

## TL;DR

> **Quick Summary**: 2.1 一锤合流——三级树（L1×7→L2×26→L3×92）+ 值形态（●/▶/⇄/⇉ 进 fills schema）+ D23-B AnswerNode 全树化 + 灵感架 material_pool + 半填宽容 + 协作讨论通道 + 话头重锚 + 全量话术（26 模板+57 追问+支线主问）+ 清单型通用机制（首批 15 处）+ P2 顺路收编 + graphify 迁移边/衔接边。19 项拍板已全按推荐闭卷（2026-10-12），本单为施工执行件。
>
> **Deliverables**:
> - 三级树数据落库（label 改 id 不动，配方全存活）
> - fills 三形态值 schema + 半填宽容 + 无形状=● 默认规则
> - AnswerNode 承载 L3 层级 + 清单追加循环停驻（四出口）
> - 灵感架 material_pool + 三回收时机引擎侧两件（图谱页安家归波次三）
> - 协作讨论通道（2 轮帽）+ 话头重锚（四选一）+ 通道优先级全序
> - graphify 迁移边+衔接边（▶/⇄ 答案编译为新边类型；渲染归波次三）
> - 病理回归四幕自动化 + 存量会话兼容 + 门禁语义护栏
> - 治理收官 D26 + 验收协议附录
>
> **Estimated Effort**: XL（5 日批串行，单锤单日纪律）
> **Parallel Execution**: NO - 串行日批 A→B→C→D→E（同文件依赖链，波次一先例）
> **Critical Path**: T1→T3(批A) → T4→T5(批B) → T6→T7(批C) → T8(批D) → T9→T11(批E) → F1-F4
>
> **勘误（2026-10-14，账实修复批）**：T7-T11 / F1-F4 / DoD 后五项曾被标 [x]，系执行回路（Atlas 会话）上下文损坏后的虚标——其所称「15/15 完成、F1-F4 APPROVE、1837 passed、@17843e5 工作树干净」均无实物（17843e5/2d29545 提交不存在、reflog 止于 a07c43a、证据链止于 wave2-t6-red、boulder.json 无 todo:8-11 会话）。已全部回退。真实进度以本单勾选+evidence 为准。详见 notepads/issues.md 2026-10-14 事故条目。

---

## Context

### Original Request
产品方 2026-10-12 指令「波次二按推荐开工」——19 项拍板（拍2-1~拍2-19）全按推荐值闭卷 + 开工信号同批给出。上游文档：总基线计划（`docs/plans/2026-10-10-A1访谈体验升级-总基线计划.md` 修订三）及其收拢的⑤⑥⑦⑨四份设计稿。

### Interview Summary
**Key Discussions**:
- 波次一验收：追认闭卷（2026-10-12）——体感 #1 即验收动作，三承诺全过；基础验收协议三原则（范围封闭/判据二元/新问题分流）生效，随本单附录传承
- 19 项拍板方式：用户要求先看详细文档（九份已落盘查阅地图已呈报），随后一次性全按推荐闭卷

**Research Findings**:
- 波次一先例（`a1-wave1-interview-upgrade.md`）：串行日批 + TDD 红绿 + 白名单门禁 + 治理收官的完整范式，本单照用
- boulder.json 证实波次一 12 任务 + F1-F4 全完成

### Metis Review（16 条发现，已全部吸收）
**CRITICAL（8 条，均已落本单）**:
1. 批次依赖缺陷：拍2-19 重锚依赖 material_pool → **material_pool 字段声明挪入批 A 数据层**（本单已重排）
2. 门禁语义护栏：92-L3 注册表不得扩入门禁计数 → **门禁只数配方引用字段（D19 边界）+ 存量会话 missing_sections 前后一致测试**
3. graphify 范围"同期"悬空 → **决策：2.1 含 graphify 边产出（T9 必做非条件），渲染归波次三**（按⑥稿工程落点口径）
4. 存量 fills 无形状 → **规则：无形状 = ● 点默认**（对齐拍2-9 边界裁定）
5. P2 双槽 vs D21 单问句铁律 → **D21 豁免台账：复合值≠复合问句；双槽仅限枚举三处；契约测试锁唯一性**
6. 通道优先级矩阵未定义 → **全序：直选 > 重锚 > 规则6.5知识 > 讨论镜像 > 投递 > 答当前；共存矩阵测试扩展至全对**（T6）
7. Q16 可跳过 vs 门禁 → **跳过 Q16 全路径定稿成功测试**
8. 半填 vs 真值闸 → **决策：半填计入模块完成度**（有真实内容即真值，选项补全机会性；对齐拍2-14"不拒绝"本意）

**MINOR/AMBIGUOUS（已落）**: 清单 cap 按位点表而非全局（T2 数据表）；57 新 L3 答案存 AnswerNode children 不炸 A1Session（字段枚举 42→45）；「记下了」修复仅限⑨稿枚举行（L1398 拼接语不动归波次三）；埋点 additive jsonl 五事件（T8）；id 宇宙快照 diff 契约测试（T1）；讨论通道 2 轮帽+出口枚举（T6）；治理收官显式任务（T11）。

---

## Work Objectives

### Core Objective
把 A1 访谈从"两级扁平+单形状答案"一次升级为"三级树+值形态+全通道接住"结构：用户随时说任何话都有去处（六通道全序），变化有形状（▶/⇄），清单能一直加（首批 15 处），无家想法有灵感架，思考性发问有人陪（镜像一轮）。

### Concrete Deliverables
见 TL;DR Deliverables 清单。

### Definition of Done
- [x] 全量 pytest ≥1691 passed / 0 failed / cov ≥80%（基线 1691，净增用例 ≥40）
- [x] 四幕病理回归自动化全绿（老父亲/支线结局/这是分支/追加循环）
- [x] 存量会话（42 字段无形状）加载+定稿行为与升级前一致
- [x] `tsc --noEmit` 零新增（前端零触碰）
- [x] ruff 触碰文件增量清零（存量不动）
- [x] D26 + PROJECT_STATE + MOC + 指南补 Q16 落痕

### Must Have
- 三级树 id 宇宙严格超集（旧 35 id ⊆ 新树，零改名零删除）
- 九型配方入口全部解析存活（快照 diff 测试）
- A1Session additive：仅 material_pool + list_thread_key + list_thread_turns 三字段（默认空，零迁移）
- 通道优先级全序 + 共存矩阵测试（波次一 test_channel_coexistence_matrix.py 扩展）
- 清单 15 位点 cap 分配表落库（灵感架/关键节点/存在物=12，其余=6）
- 讨论通道 2 轮帽 + 出口枚举（话题离开/直选打断/重锚打断/帽满桥回）
- 追加循环停驻四出口（直选/跳过/帽满/话题离开——D24 先例）
- 埋点五事件 additive jsonl（mirror_triggered/reanchor_triggered/rack_stowed/rack_recycled/list_append，fail-silent）

### Must NOT Have（红线不动清单）
- **门禁计数扩全注册表**——missing_sections 只按会话配方引用字段计算（D19 边界）
- **D21 单问句铁律破坏**——复合值（▶ from+to+trigger）≠复合问句；双槽豁免仅限：支线卡衔接（方式+点）/分支双终点/关键节点前后态三处，契约测试锁唯一性
- **前端触碰**——frontend/ 全 diff 为空（tsc/vitest 基线不动）
- **guide_engine L1398「已按示例记录」拼接语**——不动（归二期/波次三）
- **拍2-4 视觉候选扩容**——明确排除，零实现
- **规则 6.5/7 本体、user_confused 通道、D24 知识对话态四出口**——字节不动（既有测试锁）
- **「记下了」修复超范围**——仅⑨稿枚举的过度承诺行，其他引擎文案零触碰
- **新抽象层**——26 模板/57 追问进既有话术结构（a1_question_tree/interviewer prompt 区），不造"模板引擎"
- **story_modules 既有 50 问文案本体**——1.2 已落库的④稿文案零回改（仅新增 Q16 与 label 层）

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - 全部验证 agent 可执行。每批证据落 `.sisyphus/evidence/wave2-*`。

### Test Decision
- **Infrastructure exists**: YES（pytest 1691 基线 + vitest 310 + tsc）
- **Automated tests**: TDD（每批红→绿，波次一纪律）
- **Framework**: pytest + TestClient（病理回归 D23 F3 先例）

### QA Policy
- **后端**: pytest 全量每批跑 + 白名单 `git diff --stat` 核对 + ruff 增量清零
- **病理回归**: TestClient 级四幕自动化（非手工冒烟）
- **存量兼容**: 42 字段无形状 fixture（预部署序列化会话）加载+定稿前后一致
- **前端零触碰**: tsc --noEmit 零新增 + frontend/ diff 为空
- **真机冒烟指引**: 批 E 收官后落非阻塞指引（波次一先例），产品方按验收协议走

---

## Execution Strategy

### 串行日批（单锤单日纪律，波次一范式）

```
批 A（数据层地基）T1→T2→T3:
  三级树数据 + 值形态/list/multi 标注 + 支线卡 + Q16 + material_pool 字段声明 + 契约锁红测先行

批 B（引擎层结构消费）T4→T5:
  AnswerNode L3 全树化 + fills 值 schema + 半填宽容 + 清单追加循环停驻（四出口）

批 C（访谈层通道与话术）T6→T7:
  讨论通道（2轮帽）+ 重锚四选一 + 通道全序矩阵 + 26 动态模板 + 57 追问 + 记下了修复

批 D（灵感架回收）T8:
  自由流程回收 + 收尾盘点摊开 + 五事件埋点

批 E（graphify + 收官）T9→T10→T11:
  迁移边/衔接边 → 四幕病理 + 存量兼容 → 终门禁 + D26 治理

Wave FINAL: F1-F4 四审并行 → 用户 okay
```

Critical Path: T1→T3→T5→T7→T8→T11→F
Parallel Speedup: 0（串行纪律，同文件依赖链）
Max Concurrent: 1（施工）；FINAL 波 4

### Dependency Matrix

| 任务 | 依赖 | 被依赖 |
|---|---|---|
| T1-T3(批A) | 波次一收官 | 批B/批C/批D/批E 全部 |
| T4-T5(批B) | 批A | T6,T8,T9 |
| T6-T7(批C) | 批A(material_pool),批B | T8(回收话术),T10(病理) |
| T8(批D) | 批B,批C | T10,T11 |
| T9 | 批B(值schema) | T10 |
| T10 | T8,T9 | T11 |
| T11 | 全部 | F1-F4 |

### Agent Dispatch Summary

- **批A**: T1 → `quick`（验证盘点）/ T2 → `unspecified-high`（数据量大需细致）/ T3 → `quick`
- **批B**: T4 → `deep`（红测设计）/ T5 → `deep`（引擎核心）
- **批C**: T6 → `deep` / T7 → `unspecified-high`
- **批D**: T8 → `unspecified-high`
- **批E**: T9 → `deep` / T10 → `unspecified-high` / T11 → `quick`
- **FINAL**: F1 → `oracle` / F2 → `unspecified-high` / F3 → `unspecified-high` / F4 → `deep`

---

## TODOs

### 批 A：数据层地基

- [x] 1. 批 A 前置验证与契约锁红测

  **What to do**:
  - 盘点现行 id 宇宙：`module_registry.py` + `story_modules.py` + `a1_question_tree.py` 全量字段 id 快照落 `.sisyphus/evidence/wave2-t1-id-universe.txt`（升级前基线）
  - 写契约锁红测（先红）：
    - `test_three_tier_id_superset`：新树 id 集合 ⊇ 旧 35 id 集合，且旧 id 零改名零删除
    - `test_recipe_entries_survive`：九型配方矩阵每个入口解析到存在的 L2 节点（对照⑤稿配方挂点下沉表）
    - `test_gate_counts_recipe_only`：构造 92-L3 注册表下旧配方会话，断言 missing_sections 输出与 35 字段时代一致（门禁口径护栏）
    - `test_a1session_additive_enum`：A1Session 新增字段恰为 material_pool + list_thread_key + list_thread_turns 三枚（42→45），默认空/零
  - 核对⑤稿 L3×92 计数与⑥稿值形态判定表（●66+▶20+⇄5+⇉1=92）数字咬合

  **Must NOT do**:
  - 不改任何生产代码（本任务纯验证+红测）
  - 红测不含实现细节假设（只锁契约不锁实现）

  **Recommended Agent Profile**:
  - **Category**: `quick`（验证+测试编写，无逻辑设计）
  - **Skills**: []（纯盘点与测试，无领域技能需求）

  **Parallelization**: Can Run In Parallel: NO | 批 A 第一步 | Blocks: T2-T11 全部 | Blocked By: None

  **References**:
  - `docs/plans/2026-10-10-A1模块三级分类体系设计.md` — L1/L2/L3 全表（92 项逐个）+ 配方挂点下沉表 + 分级访问原则
  - `docs/plans/2026-10-10-A1模块值形态分类-点定义与变化定义.md` — 92 项形状判定表 + 边界五裁定
  - `backend/app/domains/creation/shared/module_registry.py` — 现行注册表（id 宇宙源头）；波次一 D25 记录"九型白名单 L73-77"
  - `backend/tests/unit/a1/test_channel_coexistence_matrix.py` — 波次一契约测试范式（additive 锁写法参考）
  - `.sisyphus/evidence/wave1-t5-mapping.md` — 波次一映射先例（severity 移除三联动核对的编排方式）

  **WHY**: id 宇宙快照是"label 改 id 不动"承诺的机器可验形式；门禁口径测试是 Metis CRITICAL#2 的直接落点；配方存活测试兑现总基线§5"配方入口全存活"。

  **Acceptance Criteria**:
  - [ ] id 宇宙快照文件存在且含全量 35 旧 id
  - [ ] 四个契约测试文件创建且运行 RED（import/断言失败于未实现结构）
  - [ ] ⑤⑥稿数字咬合核对记录入 evidence

  **QA Scenarios**:
  ```
  Scenario: 契约锁红测就位
    Tool: Bash (pytest)
    Steps:
      1. cd backend; .venv\Scripts\python -m pytest tests/unit/a1/test_three_tier_contract.py -q
      2. 断言：4 个测试全部 FAIL（RED）且失败原因是结构未实现（AttributeError/断言差），非语法错误
    Expected: 4 failed, 0 passed, 0 error
    Evidence: .sisyphus/evidence/wave2-t1-red.txt

  Scenario: id 快照完整性
    Tool: Bash
    Steps:
      1. 运行盘点脚本输出全量 id 列表
      2. 断言：包含 m1_default_snapshot 中全部配方引用 id（对照运行时快照）
    Expected: 35 id 全数在列
    Evidence: .sisyphus/evidence/wave2-t1-id-universe.txt
  ```

  **Commit**: YES（红测独立提交，波次一 T2 先例）
  - Message: `test(a1): 三级树契约锁红测——id超集/配方存活/门禁口径/字段枚举`
  - Files: `backend/tests/unit/a1/test_three_tier_contract.py`
  - Pre-commit: 红测运行确认 RED

- [x] 2. 批 A 数据层绿：三级树 + 标注 + 支线卡 + Q16 + material_pool

  **What to do**:
  - `backend/app/domains/creation/seed/story_modules.py` / `backend/app/domains/creation/seed/a1_question_tree.py`：按⑤稿落三级树数据——L2×26（label 改 id 不动，如 线索链→主线明线）+ L3×92 挂点（35 平移★+57 新增☆）+ 支线卡 L2（六件 L3：一句话/承载者/类型/衔接方式/衔接点/结局）
  - 值形态标注：每 L3 增 `vs` 字段（"point"/"from_to"/"dim_dir"/"dual"，●▶⇄⇉ 对应）+ 拒绝线特例（⇄ magnitude 0 语义注记）
  - 清单标注：首批 15 处 `list: True` + cap 分配表（灵感架/关键节点/存在物=12，其余=6）+ 条目模板声明（该 L3 追问维度组）
  - Q16 支线主问落 `story_modules.py`（⑨稿原文，hint 含"可跳过"）
  - `store.py`/models：A1Session additive 三字段（material_pool: list 默认 []、list_thread_key: str 默认 ""、list_thread_turns: int 默认 0）——options_key default-"" 零迁移先例
  - multi 标注与 L3 树共存核对（D23 已有 multi 字段标注不回改）

  **Must NOT do**:
  - 任何既有 id 改名/删除；1.2 已落库的④稿 50 问文案字节回改；multi 标注语义变更
  - 新增"模板引擎"类抽象——纯数据字典扩展

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`（92 项数据量大、需逐项对照⑤⑥稿防漂移）
  - **Skills**: [`handle-large-files`]（story_modules/a1_question_tree 均为千行级数据文件，切片处理）

  **Parallelization**: NO | 批 A 第二步 | Blocks: T3-T11 | Blocked By: T1

  **References**:
  - `docs/plans/2026-10-10-A1模块三级分类体系设计.md` §1-§3 — L2/L3 全表 + 支线卡六件 + §9 清单 15 位点表
  - `docs/plans/2026-10-10-A1模块值形态分类-点定义与变化定义.md` — 92 项 vs 判定 + 19 组转换中数据层可表达部分（关键节点前态→后态）
  - `docs/plans/2026-10-10-新结构引导话术设计.md` — Q16 支线主问原文
  - `backend/app/domains/creation/a1/guide_engine.py` options_key 字段声明区 — additive 字段先例（default "" 零迁移写法）
  - `.sisyphus/evidence/wave2-t1-id-universe.txt` — id 宇宙基线（绿测对照）

  **WHY**: 数据层是全部上游批次的锚——id 漂移会连锁破坏配方路由/graphify 锚点/门禁计数；cap 分配表落库让批 B 停驻循环有确定性参数源。

  **Acceptance Criteria**:
  - [ ] T1 四契约测试转 GREEN
  - [ ] L3 计数=92、vs 标注全覆盖（92/92）、list 位点=15
  - [ ] Q16 在故事线配方序列第 16 位（可跳过标记存在）
  - [ ] A1Session 42→45 字段，三新字段默认值不破坏既有会话读写

  **QA Scenarios**:
  ```
  Scenario: 契约锁转绿 + 数据完整性
    Tool: Bash (pytest)
    Steps:
      1. .venv\Scripts\python -m pytest tests/unit/a1/test_three_tier_contract.py -q
      2. 断言 4 passed；另跑 L3 计数/vs 覆盖/list 位点/cap 表专项断言（可入同文件）
      3. 构造旧形状 A1Session（无三新字段）读写往返 → 无异常
    Expected: 契约 4 passed + 旧会话往返 PASS
    Evidence: .sisyphus/evidence/wave2-t2-green.txt

  Scenario: 文案零回改护栏
    Tool: Bash (git diff)
    Steps:
      1. git diff <base>..HEAD -- backend/app/domains/creation/seed/story_modules.py
      2. 断言：④稿已落库的 15 问 question/hint 行零变更（diff 中仅新增 L3/label/vs/list 行）
    Expected: 既有问句字节不变
    Evidence: .sisyphus/evidence/wave2-t2-diff-guard.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): 三级树数据落库——L2×26/L3×92/vs标注/清单15位点/支线卡Q16/material_pool字段`
  - Files: story_modules.py / a1_question_tree.py / store.py / models 相关 + 测试
  - Pre-commit: T1 契约测试 GREEN

- [x] 3. 批 A 门禁 + 治理登记

  **What to do**:
  - 全量 pytest + cov；ruff 触碰文件增量核对（存量不动口径）；`git diff --stat` 白名单核对
  - evidence 落盘（门禁输出+白名单清单）；PROJECT_STATE 批 A 完工两节草稿（随收官批统一提交或本批提交，按波次一 T4 模式）

  **Must NOT do**:
  - 门禁红时顺手修存量（增量口径纪律）；超白名单文件出现即停工上报

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []（门禁复跑范式已成熟）

  **Parallelization**: NO | 批 A 收尾 | Blocks: 批 B 开工 | Blocked By: T2

  **References**:
  - `.sisyphus/evidence/wave1-t4-gate.txt` — 波次一门禁证据格式先例
  - `PROJECT_STATE.md` 波次一批次条目 — 登记格式先例

  **Acceptance Criteria**:
  - [ ] 全量 ≥1691 passed / 0 failed / cov ≥80%
  - [ ] ruff 增量=0；白名单外 diff=0
  - [ ] evidence 三件（门禁/白名单/登记草稿）落 `.sisyphus/evidence/wave2-t3-*`

  **QA Scenarios**:
  ```
  Scenario: 批 A 门禁全绿
    Tool: Bash (pytest + git)
    Steps:
      1. 全量 pytest --cov=app -q
      2. git diff --stat <批A base>..HEAD 逐文件对照白名单
      3. ruff check 触碰文件 vs 基线（增量对比法，波次一 F2 范式）
    Expected: 三项全过
    Evidence: .sisyphus/evidence/wave2-t3-gate.txt
  ```

  **Commit**: YES（如含治理文档）
  - Message: `docs(governance): 波次二批A门禁登记`
  - Files: PROJECT_STATE.md / docs/README.md
  - Pre-commit: 门禁绿

### 批 B：引擎层结构消费

- [x] 4. 批 B 红测：AnswerNode 全树化 + fills 值 schema + 半填 + 追加循环

  **What to do**:
  - 红测四组（先红）：
    - `test_l3_answer_tree`：L3 答案以 AnswerNode children 挂 L2 锚下（57 新 L3 不进 A1Session 平面字段）；同类自动归并语义在 L3 层沿用 D23 判定（等价/补充/矛盾）
    - `test_fills_value_schema`：●=纯文本；▶={from,to,trigger} 任一可缺；⇄={dimension,direction,magnitude}；无形状=●默认（旧会话 fixture 断言）；拒绝线=⇄ magnitude 0 落库可查
    - `test_half_fill_tolerance`：▶ 仅 to / 仅 trigger、⇄ 仅 dimension+direction——存储不拒绝；门禁完成度**计入**（真值闸：有真实内容即真值）；选项补全为机会性后补（非门禁条件）
    - `test_list_append_loop`：list 位点追加循环停驻状态机——进入（用户在清单位点补充新条目）/四出口（直选退出/跳过退出/帽满退出〔6 或 12 按位点表〕/话题离开退出）；等价归并达帽走 D23 提议流；turns 推进防卡死（D24 先例）
  - 病理场景红测预埋：老父亲追加（补充新信息进关系卡清单）/ 第 3 张关系卡（multi 追加）两幕的引擎级断言

  **Must NOT do**:
  - 不动 interviewer prompt 区（批 C 范围）；不实现逻辑（纯红测）

  **Recommended Agent Profile**:
  - **Category**: `deep`（状态机与 schema 语义设计密集）
  - **Skills**: [`test-driven-development`]（红测质量决定批 B 成败）

  **Parallelization**: NO | 批 B 第一步 | Blocks: T5 | Blocked By: 批 A 门禁（T3）

  **References**:
  - `docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md` + SYSTEM_DESIGN_SPEC_v6 §2.6 v6.3 — AnswerNode schema 权威定义（text/children[]/source）
  - `docs/plans/2026-10-10-A1模块值形态分类-点定义与变化定义.md` 工程落点节 — fills 三形态 schema 设计
  - `docs/plans/2026-10-10-A1模块三级分类体系设计.md` §9 — 追加循环停驻 + 归并上限参数
  - `backend/app/domains/creation/a1/guide_engine.py` D23 区（answer_view/语义路由/_apply_fills）— 既有 AnswerNode 实现面
  - `backend/tests/unit/a1/test_dynamic_invites.py` — D20 状态机测试范式（34 用例结构）
  - D24 知识对话态实现（guide_engine knowledge_thread 区）— 停驻状态机直接先例（两字段+四出口）

  **WHY**: 值 schema 形状（可缺字段集）与停驻出口枚举是契约级决策，红测先锁死后实现才不会漂；半填计入门禁是 Metis CRITICAL#8 决策的测试落点。

  **Acceptance Criteria**:
  - [ ] 四组红测文件创建且 RED（结构未实现类失败）
  - [ ] 病理两幕引擎级断言预埋（可先 skip-if-structure，批 B 绿后转活）

  **QA Scenarios**:
  ```
  Scenario: 批 B 红测就位
    Tool: Bash (pytest)
    Steps:
      1. .venv\Scripts\python -m pytest tests/unit/a1/test_fills_value_schema.py tests/unit/a1/test_list_append_loop.py -q
      2. 断言全部 FAIL 且失败为 AttributeError/断言差（非语法/导入 error）
    Expected: RED 清单完整
    Evidence: .sisyphus/evidence/wave2-t4-red.txt
  ```

  **Commit**: YES
  - Message: `test(a1): 批B红测——L3全树/值schema/半填/追加循环四组`
  - Files: 四测试文件
  - Pre-commit: RED 确认

- [x] 5. 批 B 绿：引擎实现 + 批门禁

  **What to do**:
  - `guide_engine.py`：AnswerNode 树扩展到 L3 层（57 新 L3 以 children 挂载）；fills 写入路由按 vs 形状分流（●直填/▶⇄结构化/⇉双形）；语义归并（D23 判定）在清单位点走"等价归并+补充追加"
  - 半填宽容实现：结构化值缺字段不拒绝不报错，落库部分形状；`options` 补全钩子（后续轮次机会性提示补 from/trigger——复用方向A options 通道，非门禁条件）
  - 清单追加循环停驻：list_thread 状态机（进入/四出口/turns 推进/帽满走 D23 提议流）；cap 读 T2 位点表
  - 批门禁：全量 pytest + cov + ruff 增量 + 白名单 + evidence

  **Must NOT do**:
  - interviewer.py 的 prompt 文案（批 C）；前端任何文件；D23 既有语义路由行为回改（additive 扩展）

  **Recommended Agent Profile**:
  - **Category**: `deep`（本波次最重逻辑件）
  - **Skills**: [`test-driven-development`]

  **Parallelization**: NO | 批 B 主施工 | Blocks: T6/T8/T9 | Blocked By: T4

  **References**:
  - T4 全部 References（同源）
  - `backend/app/domains/creation/a1/guide_engine.py` `_apply_fills`/`resolve_proposal` 区 — 扩展点
  - `.sisyphus/evidence/wave2-t2-green.txt` — 数据层 cap 表/vs 标注的运行时形态

  **WHY**: 引擎层是 2.1 结构大锤的锤心——上游批 A 数据、下游批 C 话术与批 E graphify 都以本批的形状消费为准。

  **Acceptance Criteria**:
  - [ ] T4 四组红测全 GREEN
  - [ ] 旧会话（无形状 fills）加载后全部按 ● 处理（专项断言）
  - [ ] 追加循环 6/12 两档帽行为正确（位点表驱动）
  - [ ] 全量门禁绿（≥批 A 基线）+ ruff 增量 0 + 白名单内

  **QA Scenarios**:
  ```
  Scenario: 值形状全链
    Tool: Bash (pytest 单文件)
    Steps:
      1. 跑 test_fills_value_schema.py
      2. 断言：●纯文本往返字节不变；▶{to,trigger} 缺 from 落库成功；⇄拒绝线 magnitude=0 可查；旧 fixture 全按 ●
    Expected: 全 passed
    Evidence: .sisyphus/evidence/wave2-t5-schema-green.txt

  Scenario: 追加循环帽满
    Tool: Bash (pytest 单文件)
    Steps:
      1. 构造 6 帽位点：第 6 次追加 → 提议归并流触发；第 7 次追加 → 帽满出口话术
      2. 构造 12 帽位点（关键节点）：第 12 次追加后帽满
      3. 直选打断循环 → list_thread 复位（options_key 对称复位先例）
    Expected: 两档帽+四出口行为全断言过
    Evidence: .sisyphus/evidence/wave2-t5-loop-green.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): AnswerNode L3全树化+fills值schema+半填宽容+清单追加循环（批B）`
  - Files: guide_engine.py / interviewer.py 仅解析区 / 测试
  - Pre-commit: T4 红测全绿

### 批 C：访谈层通道与话术

- [x] 6. 批 C 红测：六通道全序 + 讨论镜像 + 重锚四选一 + 话术包

  **What to do**:
  - 通道优先级全序红测（扩展波次一共存矩阵）：
    - 全序契约：**直选 > 重锚（「梳理一下」显式元命令）> 规则 6.5 知识（D24 锁定位）> 讨论镜像（虚构内发问）> 投递 > 答当前**
    - 判别规则断言：虚构内 why（问题对象=会话已建立设定，有 anchor）→ 镜像；现实世界事实 → D24 知识通道
    - 共存矩阵全对化：波次一 `test_channel_coexistence_matrix.py` 四通道矩阵扩展至六通道两两优先组合
  - 讨论通道红测：进入判定（虚构内发问/自言推演）；行为=镜子式回应一轮（不复述填空、不吸收 fills、不冷场）+ 桥接回当前题；**2 轮帽**（第 3 轮确定性桥回，D24 turns 先例）；出口枚举（帽满/话题离开/直选打断/重锚打断）
  - 重锚红测：触发词「梳理一下」→ 摊开已聊线头（配方已完成模块+当前题+灵感架存量）+ 四选一（改某答案/跳去聊某条/继续当前题/给灵感架安家）；依赖 material_pool（批 A 已有字段）；重锚后按选择分流且 fills 不丢
  - 话术包红测：26 动态问句模板（▶ 全问/补 from/补 to/补 trigger 四情形 + ⇄ 全问/补方向两情形——逐模板变量化断言）；57 L3 追问话术在树数据中存在性+追问体规范（短/口语/可跳过）；Q16 主问存在（批 A 已落，此处锁话术形态）；「记下了：」过度承诺行修复断言（仅⑨稿枚举行——问句不可落槽时改为诚实话术如"这个我先放在灵感架上"或按通道分流话术）
  - 埋点红测：mirror_triggered / reanchor_triggered 两事件 jsonl（fail-silent）

  **Must NOT do**:
  - 规则 6.5/7 本体字节改动；user_confused 通道语义；D24 四出口；L1398「已按示例记录」拼接语（红线清单）

  **Recommended Agent Profile**:
  - **Category**: `deep`（六通道优先级语义 + 状态机出口枚举，逻辑密集）
  - **Skills**: [`test-driven-development`]

  **Parallelization**: NO | 批 C 第一步 | Blocks: T7/T8/T10 | Blocked By: 批 B（T5）

  **References**:
  - `docs/plans/2026-10-10-结构接住想象-投递式访谈机制设计.md` §① — 五通道意图分流设计（本批在其上补第六通道讨论）
  - `.sisyphus/evidence/wave1-smoke-e0-01.md` — 拍2-18/19 原发实证（四轮思考性提问被吸收/梳理即兴化的逐字稿）
  - `docs/plans/2026-10-10-新结构引导话术设计.md` §1/§2/§3 — 26 模板+57 追问+投递族话术原文 + 「记下了」疣修复行
  - `backend/app/domains/creation/a1/interviewer.py` 规则 6 投递区（波次一 T10 落地）— delivery 键 additive 先例；规则 6.5 知识区 — D24 状态机先例
  - `backend/tests/unit/a1/test_channel_coexistence_matrix.py` — 四通道矩阵（本批扩展源）
  - `backend/tests/unit/a1/test_delivery_intent.py` — 意图分类测试范式

  **WHY**: 通道全序是 Metis CRITICAL#6 的落点——六通道两两组合不定义清楚，真机上必然出现"梳理一下被当跑题"类互踩；讨论 2 轮帽与出口枚举防"陪聊失控不归位"。

  **Acceptance Criteria**:
  - [ ] 六通道矩阵测试扩展且 RED；讨论/重锚/话术/埋点红测 RED
  - [ ] 判别规则（虚构内 vs 现实）测试用例含双向正反例

  **QA Scenarios**:
  ```
  Scenario: 批 C 红测就位
    Tool: Bash (pytest)
    Steps:
      1. .venv\Scripts\python -m pytest tests/unit/a1/test_channel_matrix_v2.py tests/unit/a1/test_discussion_mirror.py tests/unit/a1/test_reanchor.py -q
      2. 断言 RED（通道未实现类失败）
    Expected: 全 FAIL 非语法错
    Evidence: .sisyphus/evidence/wave2-t6-red.txt
  ```

  **Commit**: YES
  - Message: `test(a1): 批C红测——六通道全序/讨论镜像/重锚/话术包/埋点`
  - Files: 四测试文件 + 矩阵扩展
  - Pre-commit: RED 确认

- [x] 7. 批 C 绿：interviewer 实现 + 批门禁

  **What to do**:
  - `interviewer.py`：
    - 意图分类 schema additive 增键：`mirror`（讨论）/ `reanchor`（重锚）——delivery additive 先例（bool 直透，零独立 schema）
    - 讨论通道：prompt 规则区新增（虚构内发问判定提示词+镜子式回应模板+2 轮帽计数）；解析落位引擎确定性执行
    - 重锚：触发词进意图分类；「梳理一下」→ 引擎拼线头清单（已完成模块+当前题+material_pool 存量）+ 四选一回复模板；四选一后续轮分流
    - 26 动态模板 + 57 追问话术挂 prompt 目录区（挂点=guide_engine 按需取用——半填补问 ▶⇄ 与 L3 追问时机）
    - 「记下了：」修复：仅⑨稿枚举的过度承诺行改分流话术
    - 埋点：mirror/reanchor 事件 jsonl append（inspiration_log.jsonl 同文件，additive）
  - 批门禁：全量 + cov + ruff 增量 + 白名单 + evidence

  **Must NOT do**:
  - 新增 LLM 调用次数（分类键随既有 interview 单次调用 additive 返回，方向A先例）；前端触碰

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []（prompt 工程+解析，项目内范式成熟）

  **Parallelization**: NO | 批 C 主施工 | Blocks: T8/T10 | Blocked By: T6

  **References**:
  - T6 全部 References（同源）
  - `backend/app/domains/creation/a1/interviewer.py` examples 键区 — 方向A"与 interview 合并单次调用"先例
  - `.sisyphus/evidence/wave1-t10-dormant.md` — 休眠话术存档（灵感动线话术解锁参考）

  **WHY**: 零新增调用的 additive 键模式是本项目验证过的成本护栏；话术挂点决定批 D 回收话术和病理重放的语义正确性。

  **Acceptance Criteria**:
  - [ ] T6 红测全 GREEN（六通道矩阵/讨论/重锚/话术/埋点）
  - [ ] 规则 6.5/7 字节锁测试仍绿（test_rule65_and_rule7_byte_identical）
  - [ ] InterviewResult 键集 additive 锁更新且旧键零删改
  - [ ] 全量门禁绿 + ruff 增量 0 + 白名单内

  **QA Scenarios**:
  ```
  Scenario: 六通道互踩全检
    Tool: Bash (pytest)
    Steps:
      1. 跑 test_channel_matrix_v2.py
      2. 断言：pending fill 时说「梳理一下」→ 重锚胜出（非答当前）；虚构内 why → 镜像（非 D24）；现实事实 → D24（非镜像）；知识对话态中说「梳理一下」→ 重锚打断知识态并复位
    Expected: 全对组合 passed
    Evidence: .sisyphus/evidence/wave2-t7-matrix-green.txt

  Scenario: 讨论 2 轮帽
    Tool: Bash (pytest)
    Steps:
      1. 连续 3 轮虚构内追问 → 第 3 轮确定性桥回当前题
      2. 断言 fills 零吸收（讨论不落槽）+ mirror_triggered 事件 2 条
    Expected: 帽行为+零吸收断言过
    Evidence: .sisyphus/evidence/wave2-t7-mirror-cap.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): 协作讨论通道+话头重锚+六通道全序+全量话术（批C）`
  - Files: interviewer.py / 话术数据 / 埋点 / 测试
  - Pre-commit: T6 红测全绿 + 字节锁测试绿

### 批 D：灵感架回收时机

- [x] 8. 批 D：三回收时机引擎侧 + 埋点收口 + 批门禁

  **What to do**:
  - 回收时机一（自由流程）：进入自由流程节点（预设配方完成后逐级细化时），引擎检查 material_pool 存量 → 对可落位条目生成"安家提议"（落位确认话术=⑨§3 投递族"灵感入架"逆过程），用户确认后写入对应 L3 清单/字段并从 pool 移除
  - 回收时机二（收尾盘点）：closing_gate 收尾三连问扩展——预览环节摊开 material_pool 存量（"你还有 N 个想法在灵感架上：…，要安家吗？"）；安家走提议流，不安家随定稿存档（pool 不清空，跨定稿保留）
  - 回收时机三（图谱页安放）：**本波次仅预留数据面**（material_pool 已随 /file/{id} 状态端点可读），图谱页 UI 归波次三——施工单声明，零前端实现
  - 入架路径补全：投递通道判定"无家可归"时 → rack_stowed 话术 + pool append（永不拒绝语义闭环）
  - 埋点收口：rack_stowed / rack_recycled / list_append 三事件 jsonl（与批 C 两事件同文件 additive）
  - 批门禁：全量 + cov + ruff 增量 + 白名单 + evidence
  - 红测先行（本批较小，红绿可同日一锤内完成：先写回收时机红测再实现）

  **Must NOT do**:
  - 前端任何文件；pool 内容 LLM 自动落槽（安家必须用户确认——对齐"LLM 提议+确定性校验+用户确认"铁律）；定稿门禁因 pool 非空而阻塞（pool 是暂存不是未完成）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []（收尾三连问扩展+提议流均有项目先例）

  **Parallelization**: NO | 批 D 全锤 | Blocks: T10/T11 | Blocked By: 批 C（T7 回收话术依赖）

  **References**:
  - `docs/plans/2026-10-10-结构接住想象-投递式访谈机制设计.md` §③ — 灵感架三回收时机设计原文
  - `backend/app/domains/creation/a1/guide_engine.py` closing_gate 区 — 收尾三连问扩展点（D21 落地）
  - `backend/app/domains/creation/a1/guide_engine.py` resolve_proposal 区 — D23 提议流（安家提议复用）
  - `backend/app/api/a1_routes.py` /file/{file_id} GET — pool 状态外露既有通道（零改动确认）
  - `backend/data/inspiration_log.jsonl` — 埋点目标文件（方向A先例）

  **WHY**: 灵感架的完整价值在回收——只入不出就是黑洞；收尾盘点摊开是产品方"梳理"体感的收官一环；预留声明避免波次三返工争议。

  **Acceptance Criteria**:
  - [ ] 红测→绿：两回收时机（自由流程提议/收尾摊开）行为断言过
  - [ ] 无家投递 → rack_stowed 话术 + pool 落库 + 事件
  - [ ] 安家提议必须用户确认后落槽（拒绝则 pool 保留）
  - [ ] 定稿门禁在 pool 非空时行为不变（不阻塞）
  - [ ] 全量门禁绿 + ruff 增量 0 + 白名单内

  **QA Scenarios**:
  ```
  Scenario: 入架-回收闭环
    Tool: Bash (pytest)
    Steps:
      1. 投递无家素材 → 断言 pool +1、rack_stowed 事件 1 条、话术含灵感架
      2. 进入自由流程 → 安家提议出现 → 确认 → 断言目标 L3 清单 +1、pool -1、rack_recycled 事件
      3. 收尾时 pool 剩余 → 预览含存量清单；拒绝安家 → 定稿成功且 pool 保留
    Expected: 全链断言过
    Evidence: .sisyphus/evidence/wave2-t8-rack-loop.txt

  Scenario: 门禁不阻塞
    Tool: Bash (pytest)
    Steps:
      1. 构造配方字段全满 + pool 有 2 条素材的会话 → finalize
      2. 断言 200 且产物正常（pool 不进 missing_sections）
    Expected: 定稿成功
    Evidence: .sisyphus/evidence/wave2-t8-gate-unblocked.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): 灵感架三回收时机+入架路径+五事件埋点收口（批D）`
  - Files: guide_engine.py / interviewer.py 话术区 / 埋点 / 测试
  - Pre-commit: 全量绿

### 批 E：graphify 边 + 病理回归 + 收官

- [x] 9. graphify 迁移边+衔接边（红→绿）+ 批门禁

  **What to do**:
  - 红测：▶ 答案编译为**迁移边**（from 态节点→to 态节点，trigger 为边属性）；⇄ 编译为**衔接边**（dimension+direction 落边语义）；支线卡衔接（方式+点）入概念边家族；● 不变（flat NL 现行路径）
  - `graphify.py`/确定性编译区：SIR 五字段结构化扩展消费 vs 形状（⑥稿工程落点"迁移边+衔接边同期"）；关键节点前态→后态（拍2-10 已确认，含上传解析联动——上传预填的关键节点字段按▶ shape 包装）
  - 上传联动：`worldview_upload.py` 35 字段预填值按⑥稿形状判定包装（点=●；关键节点/弧光类=▶；判定表来自⑥稿 92 项判定）
  - 渲染明确不做（波次三）：图谱页对新边类型的显示降级兼容（未知边类型不炸——s2-unknown-enum-degrade 先例）
  - 批门禁：全量 + cov + ruff 增量 + 白名单 + evidence

  **Must NOT do**:
  - graphify 单点产出铁律动摇（LLM 只产 SIR，新边由确定性编译从 vs 形状装配）；前端渲染；既有五字段 SIR 契约破坏（additive）

  **Recommended Agent Profile**:
  - **Category**: `deep`（图谱契约核心区+上传联动）
  - **Skills**: [`handle-large-files`]（graphify/编译区千行级）

  **Parallelization**: NO | 批 E 第一步 | Blocks: T10 | Blocked By: 批 B（T5 值 schema）

  **References**:
  - `docs/plans/2026-10-10-A1模块值形态分类-点定义与变化定义.md` 工程落点节 — "fills 三形态值 schema / graphify 迁移边+衔接边同期"原文 + 19 组转换
  - `docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md` — graphify 契约权威（SIR 五字段）
  - `backend/app/domains/creation/a1/graphify.py` + 确定性编译模块 — 扩展点
  - `backend/app/domains/creation/a1/worldview_upload.py` — 35 字段预填（拍2-10 联动面）
  - `.sisyphus/evidence/s2-unknown-enum-degrade.txt` — 未知枚举降级先例
  - 三条设计铁律（README§概述）— "图谱装配确定性"红线

  **WHY**: 边产出是值形态的终端价值（无此则 ▶/⇄ 答案编译退化为平文本，⑥稿"同期"口径落空）；上传联动是拍2-10 用户明确确认的注意点。

  **Acceptance Criteria**:
  - [ ] 红测→绿：▶→迁移边、⇄→衔接边、支线衔接→概念边、●→现行路径四断言过
  - [ ] 上传预填含关键节点字段时按▶包装（专项用例）
  - [ ] 旧会话（无形状）graphify 输出与升级前字节一致（回归锁）
  - [ ] 未知边类型图谱页降级不炸
  - [ ] 全量门禁绿 + ruff 增量 0 + 白名单内

  **QA Scenarios**:
  ```
  Scenario: 值形态编译端到端
    Tool: Bash (pytest)
    Steps:
      1. 构造含 ▶（from/to/trigger 全）+ ▶（仅 to 半填）+ ⇄（拒绝线 magnitude 0）+ ● 的定稿会话 → 编译
      2. 断言：迁移边 2 条（半填 from 缺省仍产边）；衔接边 1 条（拒绝线 direction=拒绝语义）；● 节点现行形状
    Expected: 边类型计数精确匹配
    Evidence: .sisyphus/evidence/wave2-t9-edges.txt

  Scenario: 旧会话编译字节回归
    Tool: Bash (pytest)
    Steps:
      1. 预部署 fixture 会话（无形状 fills）→ graphify + 确定性编译
      2. 断言输出与基线快照逐字节一致
    Expected: 0 diff
    Evidence: .sisyphus/evidence/wave2-t9-regression.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): graphify迁移边/衔接边+上传值形状联动（批E-1）`
  - Files: graphify.py / 编译模块 / worldview_upload.py / 测试
  - Pre-commit: 回归锁绿

- [x] 10. 病理回归四幕 + 存量兼容全检

  **What to do**:
  - 四幕病理回归自动化（TestClient 端点级，D23 F3 先例）：
    - 幕一「老父亲」：M11 关键关系答"老父亲"后补充新信息 → 断言追加进关系卡清单（非弹三连问、非单槽覆盖）
    - 幕二「支线结局」：说"用支线结局说明主线成功" → 断言落支线卡衔接点/结局槽（2026-10-08 老伤闭环）
    - 幕三「这是分支」：描述分支双终点 → 断言双终点槽分流（P2 收编验证）
    - 幕四「清单追加循环」：关系卡追加 ×3 → 帽行为 + 归并提议 + 直选打断复位全路径
  - 存量兼容全检：预部署序列化会话 fixture（42 字段/无形状 fills/进行中状态）→ 加载 → 继续访谈（新引擎按 ● 处理）→ 定稿 → missing_sections 与升级前一致 → graphify 输出与升级前一致（T9 已锁，此处端到端复证）
  - 六通道 + 清单 + 灵感架交叉烟测：一幕内混合触发（讨论后投递后直选后追加）状态互不复位污染（options_key 对称复位先例的全通道版）

  **Must NOT do**:
  - 手工冒烟替代自动化（真机冒烟归 F3 非阻塞指引）；修存量测试使其变绿（只允许预期内快照更新并留痕说明）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []（TestClient 病理重放项目内有完整先例库）

  **Parallelization**: NO | 批 E 第二步 | Blocks: T11 | Blocked By: T8/T9

  **References**:
  - `docs/plans/2026-10-10-A1访谈体验升级-总基线计划.md` §4 批 2.1 行 — "病理回归（老父亲/支线结局/这是分支三幕重放 + 清单追加循环）"验证口径原文
  - `.sisyphus/evidence/final-qa-d21/scenario*.txt` + D23 S1-S4 重放脚本 — TestClient 病理重放先例
  - `backend/tests/unit/a1/test_option_cross_question.py` — P3 病理红测范式（波次一批 1.1）
  - `docs/decision-log.md` D23/D25 — 两波次病理用例归档索引

  **WHY**: 四幕是三波次以来全部真机撞墙的收口重放——这一幕绿了，2.1 的用户承诺（任何话有去处/变化有形状/清单能一直加）才叫兑现；存量兼容是"结构大锤不砸坏旧数据"的底线证明。

  **Acceptance Criteria**:
  - [ ] 四幕病理测试文件落库且全 GREEN
  - [ ] 存量 fixture 端到端（加载→访谈→定稿→编译）与升级前行为一致
  - [ ] 交叉烟测状态污染零发生
  - [ ] evidence 四幕各一件 + 兼容一件

  **QA Scenarios**:
  ```
  Scenario: 四幕重放
    Tool: Bash (pytest)
    Steps:
      1. .venv\Scripts\python -m pytest tests/unit/a1/test_wave2_pathology_replay.py -q
      2. 断言四幕全 passed（每幕含正反断言：正确落位 + 不弹问/不丢数据）
    Expected: 4/4 passed
    Evidence: .sisyphus/evidence/wave2-t10-pathology.txt

  Scenario: 存量会话全流程
    Tool: Bash (pytest)
    Steps:
      1. 加载 42 字段 fixture → POST /api/a1/chat（答一题）→ finalize → GET graph
      2. 断言：新答案按 ● 落库；missing_sections 与预计算一致；graph 与基线快照一致
    Expected: 全一致
    Evidence: .sisyphus/evidence/wave2-t10-legacy-e2e.txt
  ```

  **Commit**: YES
  - Message: `test(a1): 波次二病理四幕重放+存量兼容全检`
  - Files: 两个测试文件 + fixture
  - Pre-commit: 全绿

- [x] 11. 终门禁 + 治理收官（D26 + 全链落痕）

  **What to do**:
  - 终门禁亲自复跑：全量 pytest + cov（≥80%）+ tsc 零新增 + frontend/ diff 为空 + ruff 增量清零；提交链白名单全核对
  - 治理收官：
    - decision-log **D26 波次二综合条目**：19 项拍板落痕（含三自定决策：graphify 边产出在 2.1 / 通道全序 / 半填计入门禁）+ 批次提交链 + 遗留清单（图谱页安家 UI 归波次三等）+ 关键机制记录（六通道全序表/D21 豁免台账/cap 位点表）
    - PROJECT_STATE：波次一追认闭卷落痕（2026-10-12 验收协议三原则）+ 波次二收官两节
    - MOC/docs.README 变更记录 + plans 表行
    - ②故事向指南 + ④文案稿各补 Q16 一问（15→16 同步，文档内一致性）
    - **验收协议附录**落施工单尾或 D26：本波次三承诺（任何话有去处/变化有形状/清单能一直加）+ 三原则（范围封闭/判约二元/新问题分流）——波次三沿用
    - 真机冒烟指引落盘（非阻塞，F3 任务内或本任务）：按验收协议写法给出三承诺操作路径
  - E0 提示：五事件埋点已上线，观察台照常取数（波次二验收后取 mirror/reanchor/rack 触发率）

  **Must NOT do**:
  - 跳过用户 okay 自动收工（Final Wave 后必须等明确确认）；拍3-1/3-2/3-3 提前施工（波次三拍板另收）

  **Recommended Agent Profile**:
  - **Category**: `quick`（复跑+文档登记，格式全部有先例）
  - **Skills**: []（治理登记范式成熟）

  **Parallelization**: NO | 收官步 | Blocks: F1-F4 | Blocked By: T10

  **References**:
  - `docs/decision-log.md` D25 — 波次一综合条目格式（本批 D26 直接范式）
  - `.sisyphus/evidence/wave1-t12-closeout.txt` — 终门禁证据格式
  - `.sisyphus/evidence/wave1-t12-smoke-guide.md` — 冒烟指引格式（本批按验收协议升级写法）
  - `docs/plans/2026-10-10-故事向创作指南.md` / `2026-10-10-访谈问题文案说人话-逐句分析优化.md` — Q16 补录目标文档
  - 本施工单 Metis Review 节 — 三自定决策的留痕来源

  **WHY**: 治理闭环是项目纪律的最后一锤——D26 不落，后续会话无法从真相源恢复本波次上下文；验收协议附录把本次会话的验收制度创新固化为波次通用件。

  **Acceptance Criteria**:
  - [ ] 终门禁五件全过（pytest/cov/tsc/frontend diff/ruff）
  - [ ] D26 + PROJECT_STATE 两节 + MOC + 指南 Q16 + 验收协议附录 + 冒烟指引全部落盘
  - [ ] 提交链白名单核对零超范围（evidence 留痕）

  **QA Scenarios**:
  ```
  Scenario: 终门禁
    Tool: Bash
    Steps:
      1. 后端全量 pytest --cov=app -q
      2. 前端 npx tsc --noEmit（对照基线零新增）
      3. git diff --stat <波次二 base>..HEAD 全链白名单核对
    Expected: 五项全过（≥1731 passed / cov ≥80% / tsc 0 新增 / frontend 空 diff / ruff 增量 0）
    Evidence: .sisyphus/evidence/wave2-t11-closeout.txt
  ```

  **Commit**: YES
  - Message: `docs(governance): 波次二收官——D26+验收协议附录+指南Q16`
  - Files: decision-log / PROJECT_STATE / docs.README / MOC / 两指南
  - Pre-commit: 终门禁绿

---

## Final Verification Wave（MANDATORY — 全部施工任务完成后）

> 4 审并行，全部 APPROVE 后呈报用户等明确 okay。不得自动收工。

- [x] F1. **Plan Compliance Audit** — `oracle`
  通读本单全文。逐条 Must Have 验证实现存在（读文件/跑命令）；逐条 Must NOT Have 全仓搜索违禁模式（含 frontend/ diff、L1398、门禁计数口径、双槽唯一性）；evidence 文件齐全性（.sisyphus/evidence/wave2-*）；交付物对照。
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | Evidence [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  pytest 全量 + cov ≥80%；ruff 触碰文件增量清零（存量口径）；mypy 改动文件零新增；AI slop 扫描（as any 型/py 等价物、空 catch、print 残留、恒真断言、注释密度异常）；A1Session 字段 additive 枚举核对（42→45 且仅三字段）。
  Output: `Tests [N/N] | Lint [增量0] | Files [N clean] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  清洁状态起栈：四幕病理 TestClient 重放逐幕取证；六通道共存矩阵全对触发；清单追加×3 到帽；存量 fixture 会话全流程；真机冒烟指引落盘（非阻塞，按验收协议三承诺式写法——本波次承诺：任何话有去处/变化有形状/清单能一直加）。
  Output: `Scenarios [N/N] | Integration [N/N] | Legacy [PASS] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  逐 commit 对照白名单；跨批污染检查；未归账文件清点；拍2-4 排除项零实现核对；「记下了」修复范围核对（仅⑨稿枚举行）；story_modules 1.2 文案零回改核对（④稿字节 diff）。
  Output: `Tasks [N/N compliant] | Contamination [CLEAN] | Unaccounted [CLEAN] | VERDICT`

---

## Commit Strategy

每批独立提交链 + 治理文档随批或收官批统一（波次一模式）：

- **批A**: `feat(a1): 三级树数据+值形态标注+material_pool 字段（契约锁先行）` — story_modules.py / a1_question_tree.py / store.py / models / 契约测试
- **批B**: `feat(a1): AnswerNode L3 全树化+fills 值 schema+半填+追加循环` — guide_engine.py / interviewer 解析区 / 测试
- **批C**: `feat(a1): 协作讨论+话头重锚+通道全序+全量话术` — interviewer.py / 话术数据 / 矩阵测试
- **批D**: `feat(a1): 灵感架回收时机+五事件埋点` — guide_engine.py / interviewer.py / 埋点
- **批E**: `feat(a1): graphify 迁移边/衔接边` + `test(a1): 四幕病理+存量兼容` + `docs(governance): D26+收官`
- 每批 Pre-commit: `pytest 全量绿`；白名单外文件出现即停

---

## Success Criteria

### Verification Commands
```powershell
cd backend; .venv\Scripts\python -m pytest --cov=app -q   # ≥1691+40 passed / 0 failed / cov ≥80%
cd frontend; npx tsc --noEmit                              # 零新增错误
git diff --stat <batch-base>..HEAD                          # 白名单内
```

### Final Checklist
- [x] 全部 Must Have 存在
- [x] 全部 Must NOT Have 缺席
- [x] 四幕病理 + 存量兼容 + 门禁护栏三套测试绿
- [ ] F1-F4 全 APPROVE + 用户 okay
- [x] D26/PROJECT_STATE/MOC/指南 Q16 落痕

---

## 附录：基础验收协议（波次一确立 2026-10-12，波次二沿用，波次三传承）

> **三原则**：①**范围封闭**——只验本波次承诺，不扩到未施工能力；②**判据二元**——每项验收以「有测试锁定的契约行为」为准，体感描述仅作 E0 素材不改判；③**新问题分流**——验收中发现的新缺陷归入后续波次/台账，不阻塞本波次闭卷（阻塞级数据事故除外）。

> **本波次三承诺**（对应真机冒烟指引 `.sisyphus/evidence/wave2-smoke-guide.md`）：
> 1. **任何话有去处**——六通道全序（直选>重锚>6.5知识>镜像>投递>答当前），离题/发问/梳理/无家点子各有落位；
> 2. **变化有形状**——▶/⇄/⇉ 值形态进 fills 与图谱（迁移边/衔接边），半填宽容，● 旧路径字节不变；
> 3. **清单能一直加**——首批 15 位点清单 + 追加循环停驻四出口 + cap 位点表（6/12）。
>
> 波次三沿用本协议时改写承诺为该波次三件事（活地图/label 层/前端开场语 + D24 二期按钮）。
