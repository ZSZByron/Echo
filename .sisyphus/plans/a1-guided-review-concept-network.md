# A1 引导审核流与概念网实施计划（含备份前置门禁）

## TL;DR

> **Quick Summary**: 按 `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` 实施 A1 三大改造（G1 写入守卫提案制 / G2 概念网 / G3 发散兜底）。**Task 0 为备份门禁**：清理 gitignore → 全量提交 → 打标签 `backup-8.31-pre-concept-net` → 推送 origin，未完成备份任何实施任务不得启动（用户铁律）。
>
> **Deliverables**:
> - 备份标签 `backup-8.31-pre-concept-net`（本地 + origin 远端）
> - 写入守卫：非空字段修改 → 提案（替换/合并/放弃）→ 确认后落盘
> - 概念网：finalize 时一次 LLM 抽取概念边（◆语义/★规则/◇结构），图谱页网状视图 + 审核台
> - 待问清单（表外关系）访谈闭环 + divergent_question 代码级兜底
> - 692 现有测试全绿 + 新增 TDD 测试
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 6 waves（W0 备份 → W1×3 → W2×2 → W3×1 → W4×2 → W5×2 → FINAL×4）
> **Critical Path**: Task 0 → 1 → 4 → 6 → 7 → 9 → F1-F4

---

## Context

### Original Request
用户要求依据设计文档实施 A1 改造，且设定铁律：**改进前必须确认项目已备份并设定备份标签，不备份不许进行改进**。当前分支 `demo_v0.6-8.04`（注意：分支名为 `demo-v0.6-8.04`）工作区有 26 个已修改 + ~30 个未跟踪文件，`git tag` 只保护已提交状态，故备份 = gitignore 清理 + 全量提交 + annotated tag + 推送 origin。

### Interview Summary
**Key Discussions**:
- 备份方式：清理垃圾（.coverage.* pid 残留/根目录截图/生成产物/会话日志）+ 全量提交 + 标签（用户以"继续"采纳推荐）
- 标签命名：`backup-8.31-pre-concept-net`（沿用项目日期风格）
- 推送 origin（github.com/ZSZByron/Echo）双保险
- 测试策略：后端核心逻辑 TDD（RED→GREEN），前端组件测试随任务补

**Research Findings**:
- `_apply_fills` 在 guide_engine.py:118-142，**有两个调用点**（:230 stall-guard 路径 + :383 主路径）——守卫必须实现在 `_apply_fills` 函数内部以覆盖两者（Metis Q1/E2）
- 现有 `/api/a1/chat/confirm` 的 `ConfirmRequest.proposal` 是 loose dict（a1_routes.py:373-392），服务分类提案；fill 提案形状不同（{module,subfield,old,new,conflict_note,merge_preview}）——用 `kind` 判别字段扩展而非新端点（忠于设计文档"复用+补语义"）
- v0.4 §3 边总表：5 列（级|边|上游|下游|说明），14 条边（7★+4◆+3◇）；§2 8 个 AXIS 槽位——高度可编译
- `EdgeType` 枚举现为 `TREE|CROSS`（knowledge_graph.py:24-28），GraphEdge 在 49-62 仅 4 字段——需扩枚举 + 带默认值新字段
- divergent_question 已建模（InterviewResult）但未展示未存储——G3 兜底落点确认
- 前端 A1KnowledgeGraph.tsx:187-208 已有 TREE 紫实线/CROSS 琥珀虚线双通道
- 测试基建：692 测试（478 单元+214 集成），A1 专属 131 个/12 文件，FakeInterviewer 确定性 mock 范式；pytest 配置 backend/pyproject.toml:75-107
- A1Session 已有 `pending_suggestions: list[str]`（:70，stall-guard 示例答案）——与新 `pending_proposals` 语义不同非冲突，须防混淆

### Metis Review
**Identified Gaps** (addressed):
- 守卫双调用点覆盖 → 守卫实现在 `_apply_fills` 内部（Q1/E2）
- ConfirmRequest 形状不匹配 → `kind` 判别字段方案（Q2）
- immutable_core 数据源未验证 → Task 0 只读验证 + Task 1 回退策略（Q3/A4）
- EdgeType 扩展策略 → 扩枚举 SEMANTIC/RULE/STRUCTURE + lsp 全消费方检查（Q4/G3）
- confirmed_edges 键漂移 → 键使用词表内部名而非 LLM 自由文本（A5/E6）
- 标签推送顺序 → 先推分支再推标签（A7/E10）
- 合并语义未定 → 分隔符锁定 `；`，连续合并上限 3 次后强制替换/放弃（G7/E4）
- 10 条补充验收标准 AC-M1~M10 全部纳入各任务
- P4（待问闭环）标记为放弃区：W1-W3 超时则砍（S3）

---

## Work Objectives

### Core Objective
一切非空字段修改走提案→确认流（用户最终审核权）；finalize 产出概念网（词表约束的三级可信边）；图谱页可审核边；表外关系经访谈转正。全程 692 测试保持绿色。

### Concrete Deliverables
- git 标签 `backup-8.31-pre-concept-net`（本地 + origin）
- `backend/app/domains/creation/a1/`: guide_engine.py（守卫+提案+兜底）、interviewer.py（模型+三规则）、concept_edge_vocab.py（新）、concept_edge_extractor.py（新）
- `backend/app/api/a1_routes.py`: chat/confirm 扩展、finalize 概念边集成、edge confirm/reject API、GET file 扩展
- `backend/app/models/knowledge_graph.py`: EdgeType 扩展 + GraphEdge 新字段
- `frontend/src/`: types/api 扩展、GuidedChat 提案卡片+托盘、A1KnowledgeGraph 概念网视图、A1Workspace 状态徽章+一键重定稿+待问闭环
- 新增 pytest 测试（每任务 TDD）+ vitest 组件测试

### Definition of Done
- [ ] `git tag -l "backup-8.31*"` 与 `git ls-remote --tags origin` 均含备份标签
- [ ] `cd backend && python -m pytest -q` 退出码 0 且总数 ≥ 692
- [ ] `cd frontend && npm run build` 成功
- [ ] 设计文档 §8 的 12 条 Given/When/Then 全部可演示（P4 放弃区除外，见各任务标注）
- [ ] 图谱页组件 `ast-grep` 断言零 `<input>/<textarea>/contentEditable`

### Must Have
- 守卫覆盖 `_apply_fills` 全部调用点（含 stall-guard :230 路径，Metis G1）
- FakeInterviewer/InterviewFill/InterviewResult 新字段全部带默认值，692 存量测试零修改通过（Metis G2）
- 合并分隔符 = `；`（全角分号）；连续合并 ≥3 次后强制替换/放弃二选一（Metis G7/E4）
- confirmed_edges 键 = (from, to, relation)，relation 取词表内部名（表外关系经用户回答后固化为定制边名）（Metis A5/E6）
- finalize 概念边抽取失败 → finalize 仍成功 + warnings 非空 + 纯 TREE 图（设计 §5.3 降级）
- 模糊响应（"嗯"/"好"）绝不默认替换——字符串启发式：<5 字符且无"替换/合并/放弃"关键词 → 原样重述三选项（Metis S5）
- 提案在场时同一屏只有一个问句（next_question 挂起）
- 新字段在 GET file 响应中常驻（draft 态为空列表，不搞条件形状）（Metis E8）

### Must NOT Have (Guardrails)
- 不做 prompt 调优循环：三规则写成字符串常量，FakeInterviewer 测过即走，禁止真实 LLM 迭代调优（Metis S1）
- 不评估边语义正确性（V2 关注点），本计划只证明管线通：调用发生→解析成边→确认态跨重定稿保留（Metis S2）
- 图布局二选一定死：React Flow 现有布局 + 模块分簇，禁止自研 D3-force 物理引擎（Metis S4）
- edge_stats 只是按可信级计数，不做图分析仪表盘（Metis S6）
- .gitignore 补丁仅限枚举的 6 类模式，不顺手加别的（Metis G5）
- W3/W4 两任务对 a1_routes.py 的修改不得互相触碰对方行区（Metis G4）
- 设计文档 §10 四项 YAGNI 排除：不做语义编译器/答案结构化/cst 复活/自由拖拽编辑
- 不创建需要人工浏览器验证或真实 LLM API 的单测验收（Metis QA 指令）

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES（pytest 692 测试 / vitest / Playwright E2E）
- **Automated tests**: TDD（后端核心逻辑：先 RED 失败测试再 GREEN 实现）；前端组件测试随任务补（tests-after within task）
- **Framework**: pytest（backend/pyproject.toml:75-107）+ vitest（frontend）
- **TDD 顺序**: Task 1/2/4/5/6/7 每个先写失败测试（FakeInterviewer / mock LLM 模式），确认 RED 后实现至 GREEN

### QA Policy
每个任务含 agent 执行的 QA 场景，证据存 `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`。
- **后端逻辑**: Bash 跑 `python -m pytest tests/unit/a1/<file> -q`（指定文件）+ 全量回归
- **API**: Bash 启 uvicorn → curl 断言状态码 + JSON 字段
- **前端**: Bash 跑 `npx vitest run <file>` + `npm run build`；ast-grep 断言零文本输入
- **最终 QA**: Playwright（playwright skill）走完整三态流

### 回归门禁（每个实施任务通用）
```
cd H:\UGC\backend && python -m pytest -q --tb=short   # 退出码 0，总数 ≥ 基线（Task 0 记录）
cd H:\UGC\frontend && npm run build                    # 成功
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 0 (备份门禁 - 阻塞一切):
└── Task 0: gitignore 清理 + 全量提交 + 标签 + 推送 + 假设验证 + 基线测试计数 [quick]

Wave 1 (基础 - 3 并行，互不相交文件):
├── Task 1: interviewer.py 模型扩展 + prompt 三规则 [deep]
├── Task 2: concept_edge_vocab.py 边词表编译 [unspecified-high]
└── Task 3: 前端 types + API client 扩展 [quick]

Wave 2 (后端核心 - 2 并行):
├── Task 4: guide_engine.py 写入守卫+提案+发散兜底 (depends: 1) [deep]
└── Task 5: concept_edge_extractor.py LLM 抽取封装 (depends: 2) [unspecified-high]

Wave 3 (路由集成 A - 单任务，a1_routes.py chat 侧行区):
└── Task 6: chat 流提案返回 + confirm kind 判别 + GET file 扩展 (depends: 1,4) [unspecified-high]

Wave 4 (路由集成 B + 访谈 UI - 2 并行):
├── Task 7: finalize 概念边集成 + edge API (depends: 2,5,6; a1_routes.py finalize 侧行区) [deep]
└── Task 8: GuidedChat 提案卡片/托盘/模糊响应 (depends: 3,6) [visual-engineering]

Wave 5 (图谱页 UI - 2 并行):
├── Task 9: A1KnowledgeGraph 概念网视图+审核台 (depends: 3,7) [visual-engineering]
└── Task 10: A1Workspace 状态徽章/一键重定稿/待问闭环 (depends: 3,8) [visual-engineering]

Wave FINAL (4 并行审查 → 用户确认):
├── F1: 计划合规审计 [oracle]
├── F2: 代码质量审查 [unspecified-high]
├── F3: 真实手动 QA（Playwright 三态流全演示）[unspecified-high]
└── F4: 范围忠实检查 [deep]
→ 呈报结果 → 用户明确 okay 后才算完成

Critical Path: 0 → 1 → 4 → 6 → 7 → 9 → F1-F4
Max Concurrent: 3 (Wave 1)
```

**串行化说明**：W3 单任务与 W4 的 Task 7 因 a1_routes.py 同文件冲突约束串行（Metis G4）——Task 6 拥有 chat 区（~328-392 行）与 GET file（~440-452 行），Task 7 拥有 finalize 区（~455-508 行）与 _build_graph（~183-250 行）及文件尾部新端点；两任务行区互斥。

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 0 | - | 1,2,3,4,5,6,7,8,9,10 |
| 1 | 0 | 4, 6 |
| 2 | 0 | 5, 7 |
| 3 | 0 | 8, 9, 10 |
| 4 | 1 | 6, 8 |
| 5 | 2 | 7 |
| 6 | 1, 4 | 7, 8 |
| 7 | 2, 5, 6 | 9 |
| 8 | 3, 6 | 10 |
| 9 | 3, 7 | F3 |
| 10 | 3, 8 | F3 |
| F1-F4 | 全部 | 用户 okay |

### Agent Dispatch Summary

- **W0**: 1 任务 — T0 → `quick`（+ git-master skill）
- **W1**: 3 任务 — T1 → `deep`，T2 → `unspecified-high`，T3 → `quick`
- **W2**: 2 任务 — T4 → `deep`，T5 → `unspecified-high`
- **W3**: 1 任务 — T6 → `unspecified-high`
- **W4**: 2 任务 — T7 → `deep`，T8 → `visual-engineering`
- **W5**: 2 任务 — T9 → `visual-engineering`，T10 → `visual-engineering`
- **FINAL**: 4 任务 — F1 → `oracle`，F2 → `unspecified-high`，F3 → `unspecified-high`（+playwright），F4 → `deep`

---

## TODOs

- [x] 0. 备份门禁：gitignore 清理 + 全量提交 + 标签 + 推送 + 假设验证 + 基线计数

  **What to do**:
  - **第一步（备份优先，用户铁律）**：
    1. `.gitignore` 追加且仅追加以下模式（Metis G5）：
       ```
       .coverage.*
       /*.png
       backend/experiments/results/
       data/assets/visual_bg/
       data/*.jsonl
       backend/data/*.txt
       ```
    2. `git add -A` 后 `git status` 复核：剩余待提交清单应只含源码/测试/文档/实验记录（`experiments/2026-08-28-明华修仙-概念树填空实验/` 是实测证据记录，**应提交**）；截图/coverage残留/生成产物/会话日志应全部消失
    3. 提交：`chore(backup): A1概念网改造前基线备份(gitignore清理+全量提交)`
    4. 打 annotated tag：`git tag -a backup-8.31-pre-concept-net -m "A1引导审核流与概念网改造前完整基线(56文件含26修改+30新增)"`
    5. **先推分支再推标签**（Metis E10）：`git push origin demo-v0.6-8.04` 然后 `git push origin backup-8.31-pre-concept-net`；若分支推送失败（远端不存在/历史分叉）→ 停止并报告，不强推
  - **第二步（只读假设验证，Metis A1-A7）**：
    - [x] 验证 A1：读 `docs/governance/2-A1-v0.4-世界观底层拓扑概念树.md` §3（约 347-370 行）确认边总表结构（5 列 14 条 7★/4◆/3◇）与 §2 的 8 个 AXIS 槽位——若实际条数 ≠14/8，以实际数为准回填 Task 2（记录到证据文件）
    - [x] 验证 A2：读 `backend/app/domains/creation/a1/interviewer.py:247-315` 确认规则编号结构可插入（设计说插在规则 3/4 之间）
    - [x] 验证 A4：grep `a1_question_tree.py` 找 `设定边界`/`immutable_core`/`不可变` 字段——确认红线数据源；不存在则记录，Task 1 用回退策略（红线=空清单，规则仍注入）
    - [x] 验证 A6：读 `frontend/src/components/graph/A1KnowledgeGraph.tsx:187-208` 确认 TREE/CROSS 边样式映射基建存在
    - [x] 验证 A7：`git log --oneline origin/demo-v0.6-8.04..HEAD` 记录未推送提交数（第一步推送已消除）
  - **第三步（基线计数）**：`cd backend && python -m pytest --co -q -p no:cacheprovider 2>&1 | tail -3` 记录精确测试总数到证据文件（后续回归门禁比对基准）

  **Must NOT do**:
  - 不执行 `git reset --hard` 或任何破坏性回退演练（只验证标签指向 `git rev-parse backup-8.31-pre-concept-net` 正确）
  - gitignore 不加枚举外的任何模式
  - 不修改任何源码（本任务只做 git 操作 + 只读验证）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 纯 git 操作 + 只读验证，路径明确无歧义
  - **Skills**: [`git-master`]
    - `git-master`: 原子提交/标签/历史操作规范，MUST USE for ANY git operations
  - **Skills Evaluated but Omitted**:
    - `test-driven-development`: 无代码实现，不适用

  **Parallelization**:
  - **Can Run In Parallel**: NO（一切任务的前置门禁）
  - **Parallel Group**: Wave 0（单独）
  - **Blocks**: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
  - **Blocked By**: None

  **References**:
  - `H:\UGC\.gitignore`（77 行现状）——追加模式的落点，现有规则已覆盖 *.db/*.xmind/会话状态
  - `PROJECT_STATE.md` ——工作区状态描述（"大量未提交改动"）与实验记录价值判断依据
  - `docs/governance/2-A1-v0.4-世界观底层拓扑概念树.md:347-370` ——A1 验证的边总表位置
  - `backend/app/domains/creation/a1/interviewer.py:247-315` ——A2 验证的规则结构
  - `backend/app/domains/creation/seed/a1_question_tree.py` ——A4 验证的红线数据源
  - `frontend/src/components/graph/A1KnowledgeGraph.tsx:187-208` ——A6 验证的边渲染基建

  **Acceptance Criteria**:
  - [ ] `git status --porcelain` 输出为空（全提交或全忽略）
  - [ ] `git tag -l "backup-8.31-pre-concept-net"` 返回该标签
  - [ ] `git ls-remote --tags origin` 含 `backup-8.31-pre-concept-net`
  - [ ] `git rev-parse backup-8.31-pre-concept-net` == 备份提交 SHA
  - [ ] 证据文件记录：v0.4 实际边数/AXIS 数、immutable_core 存在性、pytest 基线总数、未推送提交数

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 备份完整性验证（happy path）
    Tool: Bash (git)
    Preconditions: 工作区有 56 个未提交文件
    Steps:
      1. git status --porcelain | Measure-Object -Line  → 执行前记录 N>0
      2. 执行 gitignore 补丁 + git add -A + git commit
      3. git status --porcelain | Measure-Object -Line  → 断言 == 0
      4. git tag -a backup-8.31-pre-concept-net -m "..." 后 git tag -l "backup-8.31*" → 断言输出含标签名
      5. git push origin demo-v0.6-8.04 && git push origin backup-8.31-pre-concept-net → 两者退出码均 0
      6. git ls-remote --tags origin | Select-String backup-8.31 → 断言非空
    Expected Result: 工作区干净、标签本地+远端双存在
    Failure Indicators: push 失败（远端历史分叉）、status 非空（漏 add 或 ignore 未生效）
    Evidence: .sisyphus/evidence/task-0-backup-verification.txt

  Scenario: 推送失败保护（edge case）
    Tool: Bash (git)
    Preconditions: 假设 origin 与本地历史分叉
    Steps:
      1. git push origin demo-v0.6-8.04 → 若失败：不执行 --force，保留本地标签，报告用户决策
    Expected Result: 任何推送失败都停止并上报，本地标签仍有效（本地备份已成立）
    Failure Indicators: 使用了 force push（禁止）
    Evidence: .sisyphus/evidence/task-0-push-failure-handling.txt（仅失败时）
  ```

  **Commit**: YES（本任务就是提交本身）
  - Message: `chore(backup): A1概念网改造前基线备份(gitignore清理+全量提交+标签backup-8.31-pre-concept-net)`
  - Files: .gitignore + 全部 56 个有效改动文件
  - Pre-commit: `git status` 复核清单符合预期

- [x] 1. interviewer.py 模型扩展 + prompt 三规则（TDD）

  **What to do**:
  - **RED 先行**：在 `backend/tests/unit/a1/` 新建 `test_interviewer_extensions.py`，先写失败测试：
    - InterviewFill 带 `conflict_note: str | None = None` 字段（默认 None）
    - InterviewResult 带 `proposals: list[Proposal] = []`（默认空）
    - Proposal 模型：`{module: str, subfield: str, old: str, new: str, conflict_note: str | None = None, merge_preview: str = ""}`；`merge_preview` 默认 `f"{old}；{new}"`（工厂方法或 __init__ 计算，分隔符 `；` 全角，Metis G7/E9）
    - `_build_prompt` 输出含三段新规则文本标记（断言子串：「冲突预检」「不可动清单」「术语转译」等关键锚点）
    - FakeInterviewer 构造签名向后兼容（不传新字段照常工作，Metis G2）
  - **GREEN 实现**（`backend/app/domains/creation/a1/interviewer.py`）：
    1. InterviewFill（36-42 行）加 `conflict_note: str | None = None`
    2. 新增 Proposal dataclass/pydantic 模型（放 InterviewResult 附近）
    3. InterviewResult（44-52 行）加 `proposals: list[Proposal] = []`
    4. `_build_prompt`（247-315 行）在规则 3 与 4 之间插入三条规则（字符串常量，禁止运行时拼接逻辑）：
       - 冲突预检：生成 fills 前逐条对照【用户已确定的内容】——矛盾/窄化（个例替代通例）/重叠（实例冒充类型）→ 该 fill 标记 conflict_note（世界观语言），value 仍按用户原意提取（由守卫拦截落盘）
       - 红线记忆：【设定边界.不可变集】值以 `【不可动清单】` 标头注入并置顶；冲突内容拒绝提取，reply 说明与哪条冲突。**数据源回退**（Metis A4 验证结果决定）：若 `设定边界.不可变集` 子字段存在于问卷树 → 从 answers 读取；不存在 → 注入空清单占位（规则文本保留，清单为空则规则自然不触发）
       - 术语转译：面向用户输出禁用 拓扑/槽位/派生/枚举/轴向/上游下游 → 转译为设定式表述（内部 JSON 字段名不受限）
    5. `_parse` 解析函数同步支持新字段（LLM 返回 conflict_note 时透传；缺失时 None）
    6. prompt schema 描述同步（若 interviewer 的 JSON schema 有字段说明段）
  - FakeInterviewer 扩展：可选拘认参数（conflict_note/proposals 注入能力），默认值保持现状

  **Must NOT do**:
  - 不改 FakeInterviewer 现有必填参数语义（692 存量测试零修改）
  - 不做真实 LLM 调优迭代（规则字符串写完即走，Metis S1）
  - 不实现守卫本身（守卫在 Task 4 的 guide_engine）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 模型扩展 + prompt 规则注入涉及存量 131 个 A1 测试兼容性，需谨慎的 TDD 节奏
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: RED→GREEN 纪律，本任务核心工作方式
  - **Skills Evaluated but Omitted**:
    - `systematic-debugging`: 无 bug 修复场景

  **Parallelization**:
  - **Can Run In Parallel**: YES（与 Task 2、3 同波，文件不相交：interviewer.py | 新文件 | frontend）
  - **Parallel Group**: Wave 1
  - **Blocks**: 4, 6
  - **Blocked By**: 0

  **References**:
  - `backend/app/domains/creation/a1/interviewer.py:36-52` ——InterviewFill/InterviewResult 现状模型（扩展落点）
  - `backend/app/domains/creation/a1/interviewer.py:247-315` ——_build_prompt 9 条规则结构（插入点在 3/4 之间）
  - `backend/app/domains/creation/a1/interviewer.py:292-305` ——规则 9 发散引导的现有写法（新规则的文风参照）
  - `backend/tests/unit/a1/test_guide_engine.py:1-30` ——FakeInterviewer 使用范式（向后兼容基准）
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §4.2/§4.3 ——三规则原文与模型扩展规格（权威照抄）
  - Task 0 证据文件 immutable_core 验证结果 ——红线数据源决策依据

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/unit/a1/test_interviewer_extensions.py -q` 全绿
  - [ ] 全量回归 `python -m pytest -q` 零失败（存量零修改，Metis AC-M9）
  - [ ] Proposal 默认值完备：`Proposal(module="a",subfield="b",old="x",new="y")` 无报错且 merge_preview=="x；y"

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 模型向后兼容（happy path）
    Tool: Bash (python REPL)
    Preconditions: Task 1 已实现
    Steps:
      1. cd H:\UGC\backend && python -c "from app.domains.creation.a1.interviewer import InterviewFill, InterviewResult, Proposal; f=InterviewFill(module='IP定位',subfield='name',value='星陨大陆'); r=InterviewResult(fills=[f],guidance_reply='ok'); p=Proposal(module='地理空间',subfield='special_geo',old='灵韵海化生万物',new='第三层地壳的阴面'); print(f.conflict_note, r.proposals, p.merge_preview)"
      2. 断言输出: None [] 灵韵海化生万物；第三层地壳的阴面
    Expected Result: 旧构造方式零报错，新字段默认值正确
    Failure Indicators: TypeError（必填参数被新增）或 merge_preview 分隔符错误
    Evidence: .sisyphus/evidence/task-1-model-compat.txt

  Scenario: prompt 规则缺失注入失败（edge case）
    Tool: Bash (pytest)
    Preconditions: RED 阶段（实现前）
    Steps:
      1. 运行 test_interviewer_extensions.py → 断言 FAIL（证明测试有效捕获缺失）
      2. 实现后重跑 → 断言 PASS
    Expected Result: RED→GREEN 完整闭环
    Failure Indicators: RED 阶段测试就通过（测试无效）
    Evidence: .sisyphus/evidence/task-1-tdd-red-green.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): 访谈器模型扩展(conflict_note/proposals)+prompt三规则(冲突预检/红线记忆/术语转译)`
  - Files: interviewer.py + test_interviewer_extensions.py
  - Pre-commit: `python -m pytest tests/unit/a1/ -q && python -m pytest -q`

- [x] 2. concept_edge_vocab.py 边词表编译（TDD）

  **What to do**:
  - **RED 先行**：新建 `backend/tests/unit/a1/test_concept_edge_vocab.py`：
    - 断言 EDGE_VOCAB 条数 == Task 0 验证的实际边数（预期 14，以证据文件为准）
    - 断言三级分布 7★/4◆/3◇（以实际为准）
    - 断言每条 EdgeSpec 字段完备：name/level(rule|semantic|structure)/from_slots/to_slots/hint 或 rule
    - 断言 AXIS_SLOTS == 8 槽位，每槽位二元谱系值列表
    - 断言词表封闭性：所有 relation 名可枚举（`VOCAB_RELATION_NAMES` frozenset）
  - **GREEN 实现**（新文件 `backend/app/domains/creation/a1/concept_edge_vocab.py`）：
    1. `EdgeSpec` dataclass：`{name: str, level: Literal["rule","semantic","structure"], from_slots: list[str], to_slots: list[str], hint: str = "", rule: str = ""}`
    2. `EDGE_VOCAB: list[EdgeSpec]` ——从 v0.4 §3 边总表**逐条忠实编译**（5 列→字段映射：级→level(★=rule/◆=semantic/◇=structure)、边→name、上游→from_slots、下游→to_slots、说明→hint 或 rule）。**词表内部名用 v0.4 原文边名**（如 DERIVES→骰子.概率分布 的中文短语部分），LLM 不得自造（设计 §5.1 封闭词表）
    3. `AXIS_SLOTS: list[tuple[str, list[str]]]` ——从 v0.4 §2 编译 8 槽位二元谱系（如 `("世界本体.现实规则", ["意志主导", "物质主导"])`）
    4. 辅助函数：`get_vocab_by_level(level)`、`is_known_relation(name)`（供 extractor 与 confirmed_edges 键规范化使用，Metis A5/E6）
    5. 槽位名映射注意：v0.4 用概念树命名（如 力量.载体.权限映射），A1 answers 键是问卷树命名（module.subfield）——**编译时须对照 a1_question_tree.py 做槽位名对齐**；无法对齐的条目保留 v0.4 原名并在 EdgeSpec 加 `slot_note` 备注（不静默丢弃）
  - 上游→下游方向语义：from_slots 是"因/源"，to_slots 是"果/目标"（v0.4 拓扑序）

  **Must NOT do**:
  - 不引入 LLM 动态产边（纯静态常量模块）
  - 不做 v0.4 之外的边（不发明、不推测）
  - 不改 a1_question_tree.py（只读对照；发现命名对齐问题记录到 slot_note）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: v0.4 文档忠实转录 + 两套命名体系对齐，需要高细致度但非创造性问题
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: 条数/结构断言先行，防转录失真
  - **Skills Evaluated but Omitted**:
    - `handle-large-files`: v0.4 文档约 370 行相关段，无需切片技能

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 1，与 1/3 文件不相交）
  - **Parallel Group**: Wave 1
  - **Blocks**: 5, 7
  - **Blocked By**: 0（依赖 Task 0 的 A1 验证证据：实际边数/AXIS 数）

  **References**:
  - `docs/governance/2-A1-v0.4-世界观底层拓扑概念树.md:347-370` ——§3 边总表（编译唯一权威源）
  - `docs/governance/2-A1-v0.4-世界观底层拓扑概念树.md:76-343` ——§2 槽位策略与 8 个 AXIS 定义
  - `backend/app/domains/creation/seed/a1_question_tree.py` ——问卷树槽位命名对照（10 模块）
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §5.1 ——EdgeSpec 代码骨架示例（设计意图参照，字段以本计划为准）
  - `.sisyphus/evidence/task-0-*.txt` ——实际边数/AXIS 数验证结果

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/unit/a1/test_concept_edge_vocab.py -q` 全绿
  - [ ] 全量回归零失败
  - [ ] `python -c "from app.domains.creation.a1.concept_edge_vocab import EDGE_VOCAB, AXIS_SLOTS; print(len(EDGE_VOCAB), len(AXIS_SLOTS))"` 输出与 Task 0 证据一致（预期 14 8）

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 词表封闭性与分布（happy path）
    Tool: Bash (python REPL)
    Preconditions: 实现完成
    Steps:
      1. python -c "from app.domains.creation.a1.concept_edge_vocab import *; from collections import Counter; print(Counter(e.level for e in EDGE_VOCAB)); print(all(e.name and e.from_slots and e.to_slots for e in EDGE_VOCAB))"
      2. 断言: Counter 含 rule=7 semantic=4 structure=3（或实际数）且 all() 为 True
    Expected Result: 三级分布与 v0.4 一致，无字段缺失
    Failure Indicators: 分布不符/空字段/条数不符
    Evidence: .sisyphus/evidence/task-2-vocab-distribution.txt

  Scenario: 词表关系名去重（edge case）
    Tool: Bash (python REPL)
    Steps:
      1. python -c "from app.domains.creation.a1.concept_edge_vocab import EDGE_VOCAB; names=[e.name for e in EDGE_VOCAB]; print(len(names), len(set(names)))"
      2. 断言: 两数相等（无重名边）
    Expected Result: 关系名唯一（confirmed_edges 键稳定性前提）
    Failure Indicators: 重名（键冲突隐患）
    Evidence: .sisyphus/evidence/task-2-name-uniqueness.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): 概念边词表编译(v0.4§3全量14边+§2八AXIS槽位)`
  - Files: concept_edge_vocab.py + test_concept_edge_vocab.py
  - Pre-commit: `python -m pytest tests/unit/a1/test_concept_edge_vocab.py -q`

- [x] 3. 前端类型与 API client 扩展

  **What to do**:
  - `frontend/src/types/`（现有 graph.ts 或新建 a1.ts）新增类型：
    ```typescript
    interface A1Proposal { key: string; module: string; subfield: string; old: string; new: string;
      conflict_note: string | null; merge_preview: string }
    interface OpenQuestion { id: string; question: string; status: 'pending'|'answered'|'skipped';
      created_at: string; answer?: string }
    interface EdgeStats { semantic_total: number; semantic_confirmed: number; rule_total: number;
      structure_total: number; pending_review: number }
    // GraphEdge 扩展: relation?: string; confidence?: 'rule'|'semantic'|'structure'|''; confirmed?: boolean
    ```
  - `frontend/src/api/`（现有 client.ts/graph.ts 模式）新增封装：
    - `confirmFillProposal(sessionId, proposalKey, choice: 'replace'|'merge'|'drop')` → POST `/api/a1/chat/confirm`（body 含 `kind: 'fill'`）
    - `confirmEdge(fileId, edgeKey)` → POST `/api/a1/file/{id}/edge/{key}/confirm`
    - `rejectEdge(fileId, edgeKey)` → POST `/api/a1/file/{id}/edge/{key}/reject`
  - 类型与 API 名称与后端 Task 6/7 的契约对齐（本计划即契约源，后端实现须与此一致）

  **Must NOT do**:
  - 不实现 UI 组件（Task 8/9/10 的事）
  - 不改动现有类型定义的形状（只加可选字段/新类型）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 纯类型声明 + API 封装函数，模式明确
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: 无 UI 工作

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 1，纯前端类型层与 1/2 不相交）
  - **Parallel Group**: Wave 1
  - **Blocks**: 8, 9, 10
  - **Blocked By**: 0

  **References**:
  - `frontend/src/types/graph.ts` ——现有类型定义风格（扩展起点）
  - `frontend/src/api/client.ts`、`frontend/src/api/graph.ts` ——API 封装模式（fetch 风格/错误处理照抄）
  - 本计划 Task 6/7 的 API 契约描述 ——路径与 body 形状的唯一权威
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §4.3/§6.3 ——Proposal 字段与三个新 API 规格

  **Acceptance Criteria**:
  - [ ] `npm run build` 成功（tsc 零错误）
  - [ ] 新类型文件被正确导出（`import type { A1Proposal }` 无报错）
  - [ ] 全量回归不破坏现有前端

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 类型编译与导入（happy path）
    Tool: Bash
    Preconditions: 类型与 API 封装已写
    Steps:
      1. cd H:\UGC\frontend && npm run build
      2. 断言: 退出码 0，tsc 零错误
      3. grep -c "A1Proposal\|OpenQuestion\|confirmEdge" src/types/*.ts src/api/*.ts → 断言非零
    Expected Result: 构建通过且新符号存在
    Failure Indicators: TS2304 (cannot find name) / 构建失败
    Evidence: .sisyphus/evidence/task-3-frontend-types.txt

  Scenario: API 路径契约冻结（edge case）
    Tool: Bash (grep)
    Steps:
      1. grep -n "chat/confirm\|/edge/" src/api/*.ts
      2. 断言: 路径字符串与计划 Task 6/7 定义逐字一致
    Expected Result: 前后端契约单源一致
    Failure Indicators: 路径拼写偏差（后端 404 隐患）
    Evidence: .sisyphus/evidence/task-3-api-contract.txt
  ```

  **Commit**: YES
  - Message: `feat(a1-fe): 前端类型与API client扩展(Proposal/ConceptEdge/待问)`
  - Files: frontend/src/types/*, frontend/src/api/*
  - Pre-commit: `npm run build`

- [x] 4. guide_engine.py 写入守卫 + 提案机制 + 发散兜底（TDD）

  **What to do**:
  - **RED 先行**：新建 `backend/tests/unit/a1/test_write_guard.py`（守卫核心）+ 扩展 test_guide_engine.py（兜底）：
    - **守卫主路径**（设计 §8.1）：字段空 → 直写 + file_diff(old='')；非空且新≠旧 → 不落盘、返回 Proposal；新==旧 → 跳过
    - **stall-guard 路径覆盖**（Metis AC-M4）：stall_count=3 触发 forced_allocate 返回的 fills 命中已填字段 → 同样生成提案而非静默覆盖
    - **merge 语义**（Metis AC-M1）：合并 → `answers[key] = old + "；" + new`；连续合并计数，已达 3 次再提案 → 只给 替换/放弃 二选一（Metis E4）
    - **三选一落盘**：replace → answers=新值；drop → 不写入；merge → 追加语义
    - **reply 改写**：拦截时 reply 改写为确认问句（引用旧值关键词 + 三选项，世界观语言，范式见设计 §4.1）
    - **单问句铁律**：pending_proposals 非空 → next_question 挂起
    - **发散兜底**（Metis AC-M8）：divergent_question 为 None 且本轮 fills 非空 → 代码模板生成一条（本次 fills 关键词 × 未填字段），文本含 fill 关键词
  - **GREEN 实现**（`backend/app/domains/creation/a1/guide_engine.py`）：
    1. **守卫实现在 `_apply_fills` 函数内部**（118-142 行），非外层包装——自动覆盖两个调用点（:230 stall 路径 + :383 主路径，Metis Q1/E2 铁律）
    2. `_apply_fills` 返回签名扩展：`(file_diff, proposals)` 或封装结构；两个调用方同步适配
    3. A1Session（50-71 行）加 `pending_proposals: dict[str, dict] = {}`（键=proposal_key）、`merge_counts: dict[str, int] = {}`；与现有 `pending_suggestions`（stall 示例答案）**语义无关不得混用**（Metis Q5）
    4. 提案键：`f"{module}.{subfield}:{hashlib.md5(new.encode()).hexdigest()[:8]}"`（同字段同新值幂等）
    5. 新增 `resolve_proposal(session, key, choice)` 方法：三选一落盘 + 清 pending + 恢复 next_question
    6. 发散兜底 `_fallback_divergent(session, fills)`：fills value 关键词（前 8 字符或首标点段）× 未填字段清单 → 模板问句"你提到【关键词】，这和＿＿（未填字段名）有关系吗？"
    7. handle_message 中：InterviewResult.divergent_question 为 None 且 fills 非空 → 调兜底
    8. "跳过"语义（Metis E1，实现为文档注释+测试固化）：提案在场时"跳过"仍走现有 skip-subfield 逻辑；提案只能经按钮/confirm 解决；自然语言映射（"两个都要"）在 Task 6 的 confirm 端点处理
    9. **幂等与并发序（Metis E3）**：resolve_proposal 按 key 幂等（重复 confirm 同 key → 返回最新状态不重复落盘）

  **Must NOT do**:
  - 不在 handle_message 层单独实现守卫逻辑（必须在 _apply_fills 内部，防 stall 路径绕过）
  - 不修改 finalize 门禁逻辑（>50% 规则不动）
  - 不动 pending_suggestions 现有行为

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 本计划最高风险任务——双调用点覆盖 + 状态机扩展 + 131 存量测试兼容，需要深度推敲
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: 守卫是纯逻辑判定，TDD 最佳适用场景
  - **Skills Evaluated but Omitted**:
    - `systematic-debugging`: 前置性开发非调试

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 2，与 Task 5 文件不相交：guide_engine.py | 新文件）
  - **Parallel Group**: Wave 2
  - **Blocks**: 6, 8
  - **Blocked By**: 1（依赖 Proposal 模型）

  **References**:
  - `backend/app/domains/creation/a1/guide_engine.py:118-142` ——_apply_fills 现状（无条件直写，守卫改造核心落点）
  - `backend/app/domains/creation/a1/guide_engine.py:230` ——stall-guard 调用点（覆盖验证点）
  - `backend/app/domains/creation/a1/guide_engine.py:383` ——handle_message 主调用点
  - `backend/app/domains/creation/a1/guide_engine.py:50-71` ——A1Session 模型（新字段落点）
  - `backend/app/domains/creation/a1/interviewer.py` ——Proposal/InterviewFill.conflict_note（Task 1 产出，本任务消费）
  - `backend/tests/unit/a1/test_guide_engine.py` ——现有 22 测试的会话状态注入范式（新测试照此写）
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §4.1 ——守卫流程图与确认问句范式（照抄）
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §4.4 ——发散兜底规格

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/unit/a1/test_write_guard.py -q` 全绿（含 stall 路径、merge 上限、幂等键）
  - [ ] 全量回归零失败（test_guide_engine.py 22 个存量测试零修改通过）
  - [ ] 守卫单测覆盖六类场景：空写/跳过/拦截/三选一/合并上限/stall 路径

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 非空字段拦截（happy path - G1 核心修复）
    Tool: Bash (pytest)
    Preconditions: session.answers 含 "地理空间.special_geo"="灵韵海位于最中心，化生万物"
    Steps:
      1. FakeInterviewer 返回 fill(module=地理空间, subfield=special_geo, value=第三层地壳的阴面)
      2. handle_message 处理
      3. 断言: answers 仍为旧值；proposals 长度 1；merge_preview=="灵韵海位于最中心，化生万物；第三层地壳的阴面"；reply 含替换/并存/放弃关键词
    Expected Result: 不落盘 + 提案生成 + 问句改写
    Failure Indicators: answers 被改写（守卫失效——G1 未修复）
    Evidence: .sisyphus/evidence/task-4-guard-intercept.txt

  Scenario: 三选一落盘语义（happy path）
    Tool: Bash (pytest)
    Steps:
      1. 拦截后 resolve_proposal(key, 'replace') → answers==新值
      2. 重建提案 resolve_proposal(key, 'merge') → answers==旧；新
      3. resolve_proposal(key, 'drop') → answers 不变
    Expected Result: 三种语义精确符合设计 §4.1
    Evidence: .sisyphus/evidence/task-4-resolve-semantics.txt

  Scenario: stall-guard 路径绕过防护（edge case - Metis AC-M4）
    Tool: Bash (pytest)
    Preconditions: stall_count=3，当前字段已有答案 "X"
    Steps:
      1. 触发 stall guard → forced_allocate 返回同字段 fill value="Y"
      2. 断言: answers 仍为 "X"，proposal 生成
    Expected Result: 强制分配路径同样走提案（无静默覆盖后门）
    Failure Indicators: answers 变 "Y"（Metis G1 红线）
    Evidence: .sisyphus/evidence/task-4-stall-guard.txt

  Scenario: 合并次数上限（edge case - Metis E4）
    Tool: Bash (pytest)
    Steps:
      1. 同字段连续 3 次 merge
      2. 第 4 次拦截时断言: 提案标记 merge 不可用（options 只剩替换/放弃语义）
    Expected Result: 值不无限膨胀
    Evidence: .sisyphus/evidence/task-4-merge-cap.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): 写入守卫(非空字段提案制)+发散问句代码兜底`
  - Files: guide_engine.py + test_write_guard.py + test_guide_engine.py 扩展
  - Pre-commit: `python -m pytest tests/unit/a1/ -q && python -m pytest -q`

- [x] 5. concept_edge_extractor.py LLM 抽取封装（TDD）

  **What to do**:
  - **RED 先行**：新建 `backend/tests/unit/a1/test_concept_edge_extractor.py`（全部 mock LLM，零真实调用，Metis QA 红线）：
    - mock chat_json 返回合法三段输出（概念边/轴向归类/表外关系）→ 正确解析
    - 词表校验：relation ∉ VOCAB_RELATION_NAMES → 该边转入表外通道
    - 空模块跳过：from/to 槽位对应模块无 answers → 不产出（Metis E7）
    - 抽取上限：边数 ≤ 1.5×条目数，超限截断（优先级 rule>semantic>structure）
    - 异常路径：chat_json 抛异常 → ExtractResult(success=False, warning 含 concept_edge)，不抛出
    - ◆ 语义边默认 confirmed=False；★ 规则边由 AXIS 归类点燃（rule 文本为判定依据）
  - **GREEN 实现**（新文件 `backend/app/domains/creation/a1/concept_edge_extractor.py`）：
    1. `extract_concept_edges(session, vocab) -> ExtractResult`：
       - 输入：35 条目全文 + EDGE_VOCAB（name/level/from_slots/to_slots/hint）+ 不可动清单（有则注入）
       - LLM：复用 provider.chat_json 单次调用（interviewer 调用范式照抄）
       - 输出模型：`ExtractResult { edges: list[ExtractedEdge], axis_assignments: list[AxisAssignment], open_questions: list[str], success: bool, warning: str = "" }`；`ExtractedEdge { from_slot, to_slot, relation, confidence(rule|semantic|structure), rationale }`
    2. 词表校验层：relation ∈ VOCAB_RELATION_NAMES 才成边；否则 → open_questions（表外关系→世界观问句模板转译，禁术语）
    3. ★ 规则边点燃：axis_assignments 槽位归类值 → 匹配 EDGE_VOCAB level=rule 且条件满足 → confirmed=True 规则边
    4. prompt 模板：封闭词表约束（"只能使用下列关系名，不得自造"）+ 三段输出 JSON schema
    5. 失败 → success=False + warning（Task 7 消费降级，本函数不抛异常）

  **Must NOT do**:
  - 不在单测调用真实 LLM API
  - 不评估边语义质量（管线通即可，Metis S2）
  - 不集成 finalize（Task 7 的事）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: LLM 输出解析 + 词表校验 + 降级路径，边界情况密集需高投入
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: mock 先行定义解析契约
  - **Skills Evaluated but Omitted**:
    - `kb-retriever`: 无知识库检索需求

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 2，与 Task 4 文件不相交）
  - **Parallel Group**: Wave 2
  - **Blocks**: 7
  - **Blocked By**: 2（依赖词表）

  **References**:
  - `backend/app/domains/creation/a1/concept_edge_vocab.py` ——Task 2 产出（词表+is_known_relation）
  - `backend/app/domains/creation/a1/interviewer.py` ——chat_json 调用范式与 JSON 解析容错（剥围栏/前后缀）
  - `backend/app/ai/provider.py` ——chat_json 接口（response_format 400 降级重试链已内置）
  - `backend/tests/unit/a1/test_semantic_real.py` ——现有语义协议测试的 mock 风格参照
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §5.2 ——抽取流程与明华世界示例产出
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §5.3 ——降级立场

  **Acceptance Criteria**:
  - [ ] `python -m pytest tests/unit/a1/test_concept_edge_extractor.py -q` 全绿（≥8 测试：解析/校验/截断/降级/点燃/空模块）
  - [ ] 全部测试 mock LLM（grep 断言无真实 API 调用路径）
  - [ ] 全量回归零失败

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 合法抽取解析（happy path）
    Tool: Bash (pytest, mock chat_json)
    Steps:
      1. mock 返回 {edges:[{from_slot:"地理空间.terrain",to_slot:"世界本体.origin",relation:"中心位于",rationale:"九层嵌套最中心为明珠"}], axis:[{slot:"世界本体.现实规则",side:"物质主导"}], open_questions:[]}
      2. 断言: edges[0].confidence=="semantic"；axis 匹配点燃对应 ★ 规则边（判定依据非空）
    Expected Result: 三段输出正确解析与点燃
    Evidence: .sisyphus/evidence/task-5-extract-parse.txt

  Scenario: LLM 失败降级（edge case - Metis AC-M7 前半）
    Tool: Bash (pytest, mock 抛异常)
    Steps:
      1. mock chat_json 抛 RuntimeError("provider down")
      2. 断言: success==False，warning 含 "concept_edge"，不抛异常
    Expected Result: 降级信号而非崩溃（finalize 可继续）
    Failure Indicators: 异常上抛（会阻塞 finalize，违反设计 §5.3）
    Evidence: .sisyphus/evidence/task-5-extract-degradation.txt

  Scenario: 表外关系转问句（edge case）
    Tool: Bash (pytest)
    Steps:
      1. mock 返回 relation="灵韵浓度梯度"（不在词表）
      2. 断言: edges 不含它；open_questions 含转译问句且无 拓扑/槽位/派生/枚举/轴向 术语
    Expected Result: 表外→世界观问句（设计 R6）
    Evidence: .sisyphus/evidence/task-5-out-of-vocab.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): 概念边抽取器(LLM单次调用+词表约束+降级)`
  - Files: concept_edge_extractor.py + test_concept_edge_extractor.py
  - Pre-commit: `python -m pytest tests/unit/a1/ -q`

- [x] 6. a1_routes.py chat 侧集成：提案返回 + confirm kind 判别 + GET file 扩展（TDD）

  **What to do**:
  - **行区所有权**（Metis G4）：本任务只改 a1_routes.py 的 chat 区（~328-392 行）、GET file 区（~440-452 行）与 ConfirmRequest 模型定义；**不碰** finalize 区（~455-508 行）、_build_graph（~183-250 行）——那是 Task 7 的领地
  - **RED 先行**：扩展 `backend/tests/unit/a1/test_a1_routes.py`（TestClient 范式）：
    - chat 响应含 `proposals` 数组（守卫拦截时非空，正常时空数组常驻——形状稳定，Metis E8）
    - chat 响应含 `divergent_question`（兜底后非 None）
    - confirm kind='fill' + choice='replace|merge|drop' → 按 Task 4 语义落盘，响应含更新后 answers/进度
    - confirm kind 缺省（='classification'）→ 现有分类提案行为不变（向后兼容）
    - 自然语言 confirm 映射：模糊语（"嗯"/"好"）→ 响应为重述三选项信号（`needs_clarification: true`），answers 不变（设计 §6.5 行 5，Metis 歧义铁律）——实现为字符串启发式：<5 字符且无"替换/合并/放弃/并存/都保留/算了"关键词 → needs_clarification
    - GET file 响应新增 `open_questions: []`、`edge_stats: {...}` 常驻字段（draft 态为空，不搞条件形状）
  - **GREEN 实现**：
    1. ConfirmRequest 加 `kind: str = "classification"` 判别字段（Metis Q2 方案：忠于设计"复用+补语义"，不新建端点）
    2. chat 端点（328-370 行）：透传 guide_engine 的 proposals 与 divergent_question 到响应
    3. chat/confirm 端点（373-392 行）：kind 分支——'fill' → 调 engine.resolve_proposal + 自然语言意图映射（明确词→三选一；模糊→needs_clarification 重述）；'classification' → 现有 innovation_capture 路径不动
    4. 自然语言映射词表（枚举封闭，写常量）：替换/换成→replace；合并/并存/都保留/两个都要→merge；放弃/算了/不要了→drop；其他→needs_clarification
    5. GET file（440-452 行）：open_questions/edge_stats 从 _FILES 记录读取（本任务先返回空态常驻字段，Task 7 填充真实数据）
    6. **共存规则**（Metis Q6）：一条消息同时触发分类提案与 fill 提案时——fill 提案优先出卡，分类提案顺延（单问句铁律）；响应中两者都有字段，前端 Task 8 决定展示序

  **Must NOT do**:
  - 不改 finalize/_build_graph 区任何行（Task 7 领地）
  - 不动 innovation_capture.py 现有逻辑（分类提案行为向后兼容）
  - 模糊语绝不默认任何选项（needs_clarification 是唯一出路）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: API 集成 + 判别逻辑 + 契约形状稳定性，需要细致的向后兼容处理
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: TestClient 契约测试先行
  - **Skills Evaluated but Omitted**:
    - `git-master`: 单文件修改无 git 操作

  **Parallelization**:
  - **Can Run In Parallel**: NO（Wave 3 单任务；与 Task 7 同文件串行）
  - **Parallel Group**: Wave 3
  - **Blocks**: 7, 8
  - **Blocked By**: 1, 4

  **References**:
  - `backend/app/api/a1_routes.py:328-392` ——chat 与 confirm 端点现状（改造落点）
  - `backend/app/api/a1_routes.py:440-452` ——GET file 现状（扩展落点）
  - `backend/app/api/a1_routes.py:66-67` ——_FILES 存储形状（新字段 open_questions/edge_stats 落点）
  - `backend/app/domains/creation/a1/innovation_capture.py` ——分类提案 confirm 现有流（kind 分支的参照与保留对象）
  - `backend/tests/unit/a1/test_a1_routes.py` ——TestClient 测试范式（23 个存量测试零修改基准）
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §6.5 ——输入协议表行 4/5（提案响应协议与自然语言映射）
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §6.3 ——GET file 扩展规格

  **Acceptance Criteria**:
  - [ ] 扩展测试全绿（proposals 透传/confirm 三选一/needs_clarification/kind 向后兼容/常驻字段）
  - [ ] test_a1_routes.py 23 个存量测试零修改通过
  - [ ] 全量回归零失败

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: confirm-fill 三选一 API 契约（happy path）
    Tool: Bash (uvicorn + curl)
    Preconditions: 后端启动，session 已有拦截提案
    Steps:
      1. curl -X POST http://localhost:8000/api/a1/chat/confirm -H "Content-Type: application/json" -d '{"session_id":"S1","kind":"fill","proposal":{"key":"地理空间.special_geo:abcd1234"},"choice":"merge"}'
      2. 断言: HTTP 200；响应含更新后 answers；answers["地理空间.special_geo"]=="旧值；新值"
    Expected Result: kind 判别 + merge 语义端到端
    Evidence: .sisyphus/evidence/task-6-confirm-fill-api.txt

  Scenario: 模糊语绝不默认替换（edge case - 设计 §8.11 + Metis 铁律）
    Tool: Bash (curl)
    Steps:
      1. confirm body choice 传自然语言 "嗯"
      2. 断言: 响应 needs_clarification==true 且含重述的三选项文本；answers 不变（GET file 验证）
    Expected Result: 歧义→重述，零副作用
    Failure Indicators: answers 被替换（最严重的失败模式）
    Evidence: .sisyphus/evidence/task-6-ambiguity-no-replace.txt

  Scenario: 分类提案向后兼容（edge case）
    Tool: Bash (pytest)
    Steps:
      1. POST confirm 不带 kind（老客户端 payload）→ 走分类提案路径
      2. 断言: 行为与改造前一致（现有 4 个 test_innovation_capture 测试零修改通过）
    Expected Result: kind 缺省默认 classification
    Evidence: .sisyphus/evidence/task-6-backward-compat.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): chat提案返回+confirm kind判别+file扩展(open_questions/edge_stats)`
  - Files: a1_routes.py（chat/confirm/GET file 区）+ test_a1_routes.py 扩展
  - Pre-commit: `python -m pytest tests/unit/a1/ -q && python -m pytest -q`

- [x] 7. a1_routes.py finalize 侧集成：概念边 + 确认态持久化 + edge 审核 API（TDD）

  **What to do**:
  - **行区所有权**（Metis G4）：本任务只改 finalize 区（~455-508 行）、_build_graph（~183-250 行）、models/knowledge_graph.py、文件尾部新端点；**不碰** chat/confirm/GET file 区——那是 Task 6 的领地
  - **RED 先行**：扩展 test_a1_routes.py（或新建 test_a1_edges.py）：
    - finalize 后 graph_json 含概念边（mock extractor 返回 3 语义边 + 1 规则边点燃 → 断言 edges 含 confidence=semantic/rule 且 confirmed 语义正确）
    - 确认态持久化（Metis AC-M6）：确认 3 边拒绝 2 边 → 改一条 answer 重新 finalize → confirmed/rejected 保留，新抽取不再提示已决边
    - 降级（Metis AC-M7）：mock extractor 抛异常/success=False → finalize 仍 200，graph 纯 TREE，warnings 含 concept_edge
    - edge confirm/reject API：POST 后 confirmed_edges/rejected_edges 更新；reject 后同会话可查已拒绝清单
    - EdgeType 向后兼容（Metis AC-M5）：旧 graph_json（仅 TREE/CROSS）反序列化零报错
    - open_questions 写入 _FILES 并经 GET file 暴露（对接 Task 6 的空态字段）
  - **GREEN 实现**：
    1. `backend/app/models/knowledge_graph.py`：EdgeType 枚举扩展 `SEMANTIC/RULE/STRUCTURE`（**修改前 lsp_find_references 全消费方检查**，Metis G3——重点 apply_constraints 的 CROSS 生成逻辑与前端类型）；GraphEdge 加 `relation: str = ""`、`confidence: str = ""`、`confirmed: bool = True`（全默认值）
    2. finalize 流程（455-508 行）：门禁通过后调 `extract_concept_edges`（Task 5）→ 成功：语义/结构/规则边合并入 _build_graph 产物（TREE 边不动，概念边追加）+ confirmed_edges 状态恢复匹配（键=(from,to,relation)，relation 用词表内部名，Metis A5/E6）；失败：warnings 追加、纯 TREE 图（不阻塞）
    3. _FILES 记录扩展：`confirmed_edges: dict`、`rejected_edges: dict`、`open_questions: list`、`edge_stats: dict`
    4. 新端点（文件尾部）：
       - `POST /api/a1/file/{id}/edge/{key}/confirm` → confirmed_edges[key]=edge 快照
       - `POST /api/a1/file/{id}/edge/{key}/reject` → 边移除 + rejected_edges[key] 记录（重抽取不再出现）
    5. edge_stats 计算（Metis S6 锁定）：按 confidence 级计数 + pending_review 数，纯 dict 无图分析
    6. 概念边追加时节点引用校验：from/to 节点必须已存在于 TREE 产物（槽位名→节点 id 映射复用 _build_graph 现有约定：条目 id=module.subfield）；引用缺失的边丢弃
    7. 表外 open_questions 用户已答的（answers 相关字段更新）→ re-finalize 时转正：下次抽取的 relation 候选含用户确认的定制边名（经词表校验通道外的用户通道，键固化）

  **Must NOT do**:
  - 不改 chat/confirm/GET file 区（Task 6 领地；GET file 的字段消费在 Task 6 已就位）
  - 不改 apply_constraints 现有 CROSS 行为（只是确认它不被 EdgeType 扩展破坏）
  - 不做图分析/中心性计算（S6）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: finalize 关键路径 + 持久化状态机 + 枚举扩展全消费方兼容——高风险集成
  - **Skills**: [`test-driven-development`]
    - `test-driven-development`: 持久化/降级/兼容三类断言必须先行
  - **Skills Evaluated but Omitted**:
    - `systematic-debugging`: 无既有 bug

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 4，与 Task 8 文件不相交：a1_routes.py+models | 前端组件）
  - **Parallel Group**: Wave 4（依赖链上在 Task 6 之后——同文件串行约束）
  - **Blocks**: 9
  - **Blocked By**: 2, 5, 6

  **References**:
  - `backend/app/api/a1_routes.py:183-250` ——_build_graph 现状（TREE 三层拓扑，概念边追加落点）
  - `backend/app/api/a1_routes.py:455-508` ——finalize 流程（门禁→v2→stale→建图→登记）
  - `backend/app/models/knowledge_graph.py:24-28`（EdgeType）与 `:49-62`（GraphEdge）——现状模型（扩展落点）
  - `backend/app/domains/creation/a1/concept_edge_extractor.py` ——Task 5 产出（ExtractResult 契约）
  - `backend/app/domains/creation/a1/concept_edge_vocab.py` ——词表内部名（confirmed_edges 键源）
  - `backend/tests/unit/a1/test_a1_routes.py:279-377` ——test_finalize_graph_topology 拓扑断言范式（新测试参照）
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §5.3 ——确认态持久化与降级规格
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §6.3 ——两个 edge API 规格
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §7 ——数据模型变更汇总表

  **Acceptance Criteria**:
  - [ ] 概念边集成测试全绿（追加/持久化/降级/edge API/向后兼容）
  - [ ] 全量回归零失败
  - [ ] `python -c "import json; from app.models.knowledge_graph import GraphEdge; e=GraphEdge(from_node_id='a',to_node_id='b',edge_type='TREE',visual_description='x'); print(e.relation, e.confidence, e.confirmed)"` 输出 ` True`（旧构造兼容）

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: finalize 概念边端到端（happy path）
    Tool: Bash (pytest, mock extractor)
    Steps:
      1. 构造含 35 字段 answers 的 session，mock extract 返回 3 语义边+1 轴向归类
      2. POST finalize
      3. 断言: graph_json.edges 含 TREE 边（原有）+ semantic 边（confirmed=false）+ rule 边（confirmed=true, relation=词表名）；open_questions 进 _FILES
    Expected Result: 三级边全部入图（设计 §8.3/8.4）
    Evidence: .sisyphus/evidence/task-7-finalize-edges.txt

  Scenario: 确认态跨 re-finalize（happy path - Metis AC-M6）
    Tool: Bash (pytest)
    Steps:
      1. finalize → confirm 3 边 reject 2 边
      2. 改一条 answer → re-finalize（v2）
      3. 断言: confirmed_edges 仍 3 条、rejected_edges 仍 2 条、新图中已确认边 confirmed=true、已拒绝边不出现
    Expected Result: 用户审核权持久（设计 §8.6）
    Evidence: .sisyphus/evidence/task-7-persist-refinalize.txt

  Scenario: 抽取失败降级（edge case - Metis AC-M7 + 设计 §8.7）
    Tool: Bash (pytest, mock 抛异常)
    Steps:
      1. mock extract_concept_edges 返回 success=False
      2. POST finalize → 断言: HTTP 200；graph 全 TREE；warnings 含 "concept_edge"；status=="finalized"
    Expected Result: finalize 不被抽取失败阻塞
    Failure Indicators: 500 错误或 status=error
    Evidence: .sisyphus/evidence/task-7-degradation.txt

  Scenario: 旧图反序列化兼容（edge case - Metis AC-M5）
    Tool: Bash (python REPL)
    Steps:
      1. 用旧形状 JSON（仅 TREE/CROSS 边、无 relation/confidence/confirmed 字段）调 get_graph
      2. 断言: 零报错，edge_type 保留原值
    Expected Result: 存量定稿文件全部可读
    Evidence: .sisyphus/evidence/task-7-backward-compat.txt
  ```

  **Commit**: YES
  - Message: `feat(a1): finalize概念边集成+确认态持久化+edge审核API`
  - Files: a1_routes.py（finalize/_build_graph/尾部新端点）+ models/knowledge_graph.py + 测试
  - Pre-commit: `python -m pytest tests/unit/a1/ -q && python -m pytest -q`

- [x] 8. GuidedChat 提案卡片 + 托盘 + 模糊响应 + 单问句铁律

  **What to do**:
  - 新建 `frontend/src/components/guided/ProposalCard.tsx`（提案卡片，设计 §6.6 线框照抄）：
    - 展示：⚠重叠提示 / 字段名 / 原设定 vs 新内容对比框 / 冲突说明（conflict_note）/ 三按钮 [替换] [合并保留两者 ✓默认高亮] [放弃]（merge_counts 达上限时合并按钮禁用——对接 Task 4 的 merge 不可用标记）
    - 点击 → 调 `confirmFillProposal`（Task 3 API）→ 成功后卡片消失 + answers 面板刷新
  - 新建 `frontend/src/components/guided/ProposalTray.tsx`（右下角托盘）：
    - 图标 ⚑ + 未处理计数红点；点开展开卡片列表逐条处理
    - 单轮 >3 提案：前 3 成卡，其余直接进托盘（对接后端返回顺序）
  - GuidedChat.tsx / A1Workspace.tsx 的 chat 区改造：
    - chat 响应含 proposals 非空 → 渲染卡片（≤3）；needs_clarification → 渲染重述三选项气泡
    - **单问句铁律**：卡片在场时 next_question 区域挂起（显示"处理完修改提案后继续"占位）；卡片处理完下一轮恢复
    - 用户不理会卡片继续发消息 → 卡片自动收进托盘（红点+1），访谈不中断
    - **输入协议行 7/8**（待问回答）：chat 界面在待问开启轮显示当前待问问句（一次一条，最老优先）；清单 >5 条时提示"有 N 个问题待你拍板"
  - 状态管理：proposals/tray/open_questions 挂 A1Workspace 会话状态（现有状态模式照抄）
  - 组件测试（vitest）：卡片渲染/三按钮回调/托盘计数/挂起恢复/needs_clarification 气泡

  **Must NOT do**:
  - 图谱页方向的任何改动（Task 9/10 领地）
  - 不引入新状态管理库（用现有 useState/模式）
  - 模糊语在前端不做任何自动选择（只展示后端 needs_clarification 结果）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 交互卡片/托盘/状态可视化，UI 密集任务
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: 卡片线框→组件的视觉与交互设计指导
  - **Skills Evaluated but Omitted**:
    - `test-driven-development`: 前端组件测试随任务补（tests-after within task）

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 4，与 Task 7 文件不相交：前端组件 | 后端路由）
  - **Parallel Group**: Wave 4
  - **Blocks**: 10
  - **Blocked By**: 3, 6

  **References**:
  - `frontend/src/components/guided/GuidedChat.tsx:62-68` ——handleSubmit 现状（输入处理接入点）
  - `frontend/src/pages/a1/A1Workspace.tsx` ——会话状态管理模式（sendMessage/状态刷新范式）
  - `frontend/src/components/structured/StructuredFilePanel.tsx` ——answers 面板（卡片确认后刷新联动）
  - `frontend/src/components/__tests__/A1KnowledgeGraph.test.tsx` ——现有组件测试范式（vitest 写法参照）
  - `frontend/src/api/`（Task 3 产出）——confirmFillProposal 封装
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §6.5 ——输入协议表（行 3/4/5/7/8 前端行为）
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §6.6 ——提案卡片与托盘线框+状态图（照抄）
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §6.7 机制 4 ——待问清单防堆积规则

  **Acceptance Criteria**:
  - [ ] `npx vitest run` 新组件测试全绿；`npm run build` 成功
  - [ ] 现有前端测试零破坏（useTypewriter 6 个失败为前序遗留，排除在外）
  - [ ] 提案在场时 next_question 挂起可断言（组件测试验证）

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 提案卡片渲染与确认（happy path - 设计 §8.1/8.9）
    Tool: Bash (vitest 组件测试)
    Steps:
      1. 渲染 GuidedChat 传入 proposals=[{key:'k1',module:'地理空间',subfield:'special_geo',old:'灵韵海化生万物',new:'第三层地壳的阴面',conflict_note:'…',merge_preview:'…'}]
      2. 断言: 卡片可见，含 .proposal-card 选择器；next_question 区域为挂起占位
      3. 模拟点击 [合并保留两者] → 断言 confirmFillProposal 以 ('k1','merge') 调用
      4. 断言: 默认高亮按钮是合并（class 含 high-light 或等效标记）
    Expected Result: 卡片交互完整、单问句铁律生效
    Evidence: .sisyphus/evidence/task-8-proposal-card.txt

  Scenario: 托盘收纳与计数（edge case - 设计 §6.6 + Metis AC-M2）
    Tool: Bash (vitest)
    Steps:
      1. 渲染时传 5 个 proposals → 断言: 直接渲染卡片 ≤3，托盘计数 ⚑2
      2. 模拟用户发送新消息（不理会卡片）→ 断言: 卡片收进托盘，托盘计数 ⚑5，输入框可用不阻塞
    Expected Result: 防提案轰炸机制生效
    Evidence: .sisyphus/evidence/task-8-tray.txt

  Scenario: 模糊语重述展示（edge case - 设计 §8.11）
    Tool: Bash (vitest)
    Steps:
      1. chat 响应 needs_clarification=true → 断言: 渲染重述三选项气泡；无任何自动 confirm 调用
    Expected Result: 歧义只重述不动作
    Evidence: .sisyphus/evidence/task-8-clarification.txt
  ```

  **Commit**: YES
  - Message: `feat(a1-fe): 提案卡片+托盘+模糊响应重述+单问句铁律`
  - Files: ProposalCard.tsx + ProposalTray.tsx + GuidedChat.tsx + A1Workspace.tsx chat 区 + 组件测试
  - Pre-commit: `npx vitest run && npm run build`

- [x] 9. A1KnowledgeGraph 概念网视图 + 审核台

  **What to do**:
  - `frontend/src/components/graph/A1KnowledgeGraph.tsx` 扩展（393 行现状）：
    1. **视图切换**：顶部 [行政树|概念网] Tab；概念网模式 = 按模块分簇 + 语义边织网（**布局定死：React Flow 现有布局 + 模块分簇**，禁自研物理引擎，Metis S4）
    2. **边渲染扩展**（187-208 行现有通道扩展，设计 §6.2 渲染表）：
       - TREE 紫实线（现状不变）
       - ◆ semantic 待确认：琥珀虚线 + 呼吸动画（CSS）+ `?` 角标 → 点击开审核卡
       - ◆ semantic 已确认：琥珀实线 → 点击查看 rationale
       - ★ rule：绿色点线 + 关系名标签 → 点击查看判定依据
       - 疑点：红虚线（conflict 疑点通道）
    3. **审核卡**（点击待确认边弹出）：rationale + [确认] [删除] 按钮 → 调 confirmEdge/rejectEdge（Task 3 API）；删除二次确认弹层；已拒绝进"已拒绝清单"（可展开，同会话可恢复）
    4. **筛选器**：可信级（★/◆/◇）× 状态（待确认/已确认/已拒绝）多选；默认只显示 已确认+待确认；已拒绝默认隐藏
    5. **防毛线球**：悬停高亮邻边其余淡化（React Flow 边交互）
    6. **术语词典**（设计 §6.7 机制 5）：★→"铁律推断"（绿）、◆→"联想"（琥珀）、◇→"结构拆解"（蓝灰）；relation 名显示抽取时中文短语
    7. 顶部统计条：待确认边 N / 疑点 N / 待问 N（edge_stats + open_questions 数据）
  - **零文本输入铁律**：本组件不得含任何 `<input>`/`<textarea>`/`contentEditable`（设计 §6.4 + Metis G6）
  - 组件测试（vitest）：切换/边样式映射/审核卡交互/筛选器/已拒绝清单

  **Must NOT do**:
  - 不加任何文本输入框（改关系名属编辑，留给既有图谱编辑器，设计 §10）
  - 不做自由拖拽编辑（只读+审核，YAGNI）
  - 不改 A1Workspace（Task 10 领地）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: React Flow 图可视化 + 边样式体系 + 审核交互，视觉工程密集
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: 三级可信度的视觉语言（颜色/线型/动画）设计
  - **Skills Evaluated but Omitted**:
    - `playwright`: 组件级 vitest 即可，E2E 在 F3

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 5，与 Task 10 文件不相交：A1KnowledgeGraph.tsx | A1Workspace.tsx）
  - **Parallel Group**: Wave 5
  - **Blocks**: F3
  - **Blocked By**: 3, 7

  **References**:
  - `frontend/src/components/graph/A1KnowledgeGraph.tsx:187-208` ——边渲染现状（TREE/CROSS 双通道，扩展起点）
  - `frontend/src/components/graph/A1KnowledgeGraph.tsx`（整体）——React Flow 用法与 props 模式
  - `frontend/src/components/__tests__/A1KnowledgeGraph.test.tsx` ——现有测试（扩展而非重写）
  - `frontend/src/api/`（Task 3 产出）——confirmEdge/rejectEdge
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §6.1 ——概念网视图线框（照抄）
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §6.2 ——边渲染规则表（样式/交互逐条对照）
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §6.7 机制 3/5/6 ——防毛线球/术语词典/误删防护

  **Acceptance Criteria**:
  - [ ] `npx vitest run` 组件测试全绿；`npm run build` 成功
  - [ ] `ast-grep -p '<input $$$>' -l tsx frontend/src/components/graph/A1KnowledgeGraph.tsx` 零匹配（含 textarea/contentEditable 三查）
  - [ ] 边样式映射测试覆盖五类边（TREE/待确认/已确认/规则/疑点）

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 概念网渲染与审核流（happy path - 设计 §8.6/8.10）
    Tool: Bash (vitest)
    Steps:
      1. 渲染 A1KnowledgeGraph 传入含 TREE+semantic(confirmed=false)+rule 边的 graph
      2. 断言: 概念网 Tab 可切换；semantic 待确认边样式含虚线+动画标记类名；rule 边含关系名标签
      3. 点击待确认边 → 审核卡出现（含 rationale 文本）→ 模拟 [确认] → 断言 confirmEdge 调用
      4. 模拟 [删除] → 二次确认弹层出现 → 确认后 rejectEdge 调用
    Expected Result: 完整审核台交互
    Evidence: .sisyphus/evidence/task-9-concept-view.txt

  Scenario: 筛选器默认态与隐藏（edge case - 设计 §6.7 机制 3）
    Tool: Bash (vitest)
    Steps:
      1. 传入 已确认2+待确认1+已拒绝1 边
      2. 断言: 默认渲染 3 条（已确认+待确认），已拒绝不可见
      3. 切换筛选器显示已拒绝 → 断言 4 条可见且已拒绝样式区分
    Expected Result: 防信息过载默认态
    Evidence: .sisyphus/evidence/task-9-filter.txt

  Scenario: 零文本输入断言（edge case - Metis G6 铁律）
    Tool: Bash (ast-grep + grep)
    Steps:
      1. ast-grep 查 <input/<textarea 标签 + grep contentEditable → 三查均零匹配
    Expected Result: 图谱页纯点选
    Failure Indicators: 任何文本输入元素（验收 #10 失败）
    Evidence: .sisyphus/evidence/task-9-zero-input.txt
  ```

  **Commit**: YES
  - Message: `feat(a1-fe): 概念网视图(三级边渲染+审核卡+筛选器)`
  - Files: A1KnowledgeGraph.tsx + 测试
  - Pre-commit: `npx vitest run && npm run build`

- [x] 10. A1Workspace 状态徽章 + 一键重定稿 + 待问闭环

  **What to do**:
  - `frontend/src/pages/a1/A1Workspace.tsx`（A1GraphSection 区 1134-1217 行附近）：
    1. **状态徽章**（设计 §6.7 机制 1）：图谱页顶部 `已定稿 v2 ✓` / `⚠ 设定已更新——点此重新定稿查看新图`；draft 期间显示旧图+徽章不闪空（对接现有 stale 机制 409 门禁）
    2. **一键重新定稿**：徽章点击 → 调现有 finalize API → 完成后图谱刷新 + 概念边确认态保留（后端 Task 7 已保证）
    3. **已拒绝清单**：图谱页可展开区块（数据来自 GET file 的 rejected 信息或 edge_stats 扩展）+ 同会话恢复按钮（调 confirm 恢复）
    4. **待问闭环 UI**（P4——**放弃区标记**，Metis S3：若前序任务超时此任务的可裁剪部分）：
       - 访谈页开场（session 恢复时）若有 pending open_questions → 由访谈者自然问出一条（最老优先）；对接 Task 8 的待问显示
       - 用户回答 → 前端发送时带 open_question_id 上下文 → 后端关闭该待问（status=answered）；"先不谈" → skipped 永久跳过
       - 图谱页"待问 N"条目点击 → "去回答"跳回访谈页（复用现有 a1_return_intent localStorage 键机制，键值 'chat'）
    5. "跳过"语义文档化：ProposalCard 组件加提示文案"输入'跳过'将跳过当前问题而非处理提案"（Metis E1 前端侧落地）
  - 组件测试：徽章两态/一键重定稿调用/已拒绝展开/跳转跳回

  **Must NOT do**:
  - 不改 GuidedChat/ProposalCard/Tray（Task 8 领地；只做集成消费）
  - 不改后端（纯前端集成；若发现后端缺口报告而非自行改）
  - P4 待问闭环不引入新的页面路由（复用现有视图切换）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 状态徽章/清单/跳转交互集成，UI 工程任务
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: 徽章状态语言与跳转交互设计
  - **Skills Evaluated but Omitted**:
    - `test-driven-development`: 集成测试随任务补

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 5，与 Task 9 文件不相交：A1Workspace.tsx | A1KnowledgeGraph.tsx）
  - **Parallel Group**: Wave 5
  - **Blocks**: F3
  - **Blocked By**: 3, 8

  **References**:
  - `frontend/src/pages/a1/A1Workspace.tsx:1134-1217` ——A1GraphSection 现状（徽章/重定稿按钮落点）
  - `frontend/src/pages/a1/A1Workspace.tsx`（挂载逻辑）——a1_return_intent localStorage 消费范式（待问跳转复用）
  - PROJECT_STATE.md 关键决策 ——`a1_return_intent='chat'` 键一步回访谈页（现有机制）
  - `frontend/src/api/`（Task 3 产出）+ 现有 finalize 调用 ——一键重定稿复用
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §6.7 机制 1/4/6 ——徽章/待问/已拒绝清单规格
  - `docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md` §8.12 ——状态徽章验收标准

  **Acceptance Criteria**:
  - [ ] `npx vitest run` 全绿；`npm run build` 成功
  - [ ] 徽章两态切换可断言（finalized ✓ / ⚠ 设定已更新）
  - [ ] "去回答"跳转经 a1_return_intent 键实现（grep 断言键名）

  **QA Scenarios (MANDATORY)**:

  ```
  Scenario: 状态徽章与一键重定稿（happy path - 设计 §8.12）
    Tool: Bash (vitest)
    Steps:
      1. 渲染 A1GraphSection，file 状态 finalized + stale 标记
      2. 断言: 徽章显示 ⚠ 设定已更新 文案
      3. 模拟点击 → 断言 finalize API 调用 → mock 返回新 v → 徽章变 已定稿 v3 ✓
    Expected Result: 双页状态漂移防护闭环
    Evidence: .sisyphus/evidence/task-10-badge-refinalize.txt

  Scenario: 待问跳转闭环（happy path - 设计 §8.5，P4 放弃区）
    Tool: Bash (vitest)
    Steps:
      1. 渲染含 open_questions=[{id:'q1',question:'…',status:'pending'}] 的图谱页
      2. 断言: 待问 N 计数显示；点击"去回答"→ localStorage a1_return_intent=='chat' + 视图切换到访谈
    Expected Result: 图谱→访谈跳转复用现有机制
    Evidence: .sisyphus/evidence/task-10-openquestion-nav.txt

  Scenario: 已拒绝清单恢复（edge case - 设计 §6.7 机制 6）
    Tool: Bash (vitest)
    Steps:
      1. 含 rejected 边数据渲染 → 断言默认隐藏、可展开
      2. 模拟恢复点击 → 断言 confirmEdge 恢复调用
    Expected Result: 误删可救
    Evidence: .sisyphus/evidence/task-10-rejected-recover.txt
  ```

  **Commit**: YES
  - Message: `feat(a1-fe): 状态徽章+一键重定稿+已拒绝清单+待问闭环`
  - Files: A1Workspace.tsx + 测试
  - Pre-commit: `npx vitest run && npm run build`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval.**
> **Never mark F1-F4 as checked before getting user's okay.**

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan. 特别验证：设计文档 §8 的 12 条验收标准逐条对照（P4 放弃区条目标注状态）。
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `cd backend && python -m pytest -q` + `python -m ruff check app` + `python -m mypy app`（存量遗留问题不新增即可）+ `cd frontend && npm run build` + `npx oxlint src`。Review all changed files for: `as any`/`@ts-ignore`、empty catches、console.log in prod、commented-out code、unused imports。Check AI slop：过度注释、过度抽象、泛型命名（data/result/item/temp）。新字段默认值完备性（旧 JSON 反序列化兼容，Metis AC-M5）。
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`（+ `playwright` skill）
  从干净状态启动（start.ps1 或手动 uvicorn+vite）。执行设计文档 §8 全部可演示场景 + 本计划各任务 QA 场景抽样：上传明华修仙.txt → 访谈补充触发提案卡片 → 三选一 → 定稿 → 概念网可见 ◆/★ 边 → 审核台确认/删除 → 重定稿确认态保留 → 状态徽章。跨任务集成测试 + 边界情况（空状态/无效输入/快速操作）。证据存 `.sisyphus/evidence/final-qa/`。
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (`git log --oneline backup-8.31-pre-concept-net..HEAD` + `git diff`）。Verify 1:1 — 计划内的都建了（无遗漏），计划外的没建（无蔓延）。Check "Must NOT do" compliance（尤其：gitignore 只加 6 类模式、无 prompt 调优残留、无 D3-force、§10 四项 YAGNI）。Detect cross-task contamination：对照行区划分检查 Task 6 vs 7 的 a1_routes.py 修改是否越界。Flag unaccounted changes。
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

> 每任务一提交（回退粒度=任务）。提交前必须过该任务回归门禁。提交信息沿用仓库惯例（type(scope): desc）。

- **Task 0**: `chore(backup): A1概念网改造前基线备份(gitignore清理+全量提交+标签backup-8.31-pre-concept-net)` — .gitignore + 全部有效改动；提交后打 annotated tag 并推送（先推分支后推标签）
- **Task 1**: `feat(a1): 访谈器模型扩展(conflict_note/proposals)+prompt三规则(冲突预检/红线记忆/术语转译)` — interviewer.py + 测试
- **Task 2**: `feat(a1): 概念边词表编译(v0.4§3全量14边+§2八AXIS槽位)` — concept_edge_vocab.py + 测试
- **Task 3**: `feat(a1-fe): 前端类型与API client扩展(Proposal/ConceptEdge/待问)` — types + api
- **Task 4**: `feat(a1): 写入守卫(非空字段提案制)+发散问句代码兜底` — guide_engine.py + 测试
- **Task 5**: `feat(a1): 概念边抽取器(LLM单次调用+词表约束+降级)` — concept_edge_extractor.py + 测试
- **Task 6**: `feat(a1): chat提案返回+confirm kind判别+file扩展(open_questions/edge_stats)` — a1_routes.py chat 区 + 测试
- **Task 7**: `feat(a1): finalize概念边集成+确认态持久化+edge审核API` — a1_routes.py finalize 区 + 测试
- **Task 8**: `feat(a1-fe): 提案卡片+托盘+模糊响应重述+单问句铁律` — GuidedChat + 组件
- **Task 9**: `feat(a1-fe): 概念网视图(三级边渲染+审核卡+筛选器)` — A1KnowledgeGraph
- **Task 10**: `feat(a1-fe): 状态徽章+一键重定稿+已拒绝清单+待问闭环` — A1Workspace

---

## Success Criteria

### Verification Commands
```bash
# 备份有效性
git tag -l "backup-8.31-pre-concept-net"          # Expected: backup-8.31-pre-concept-net
git ls-remote --tags origin | grep backup-8.31    # Expected: 远端存在该标签

# 回归
cd H:\UGC\backend && python -m pytest -q          # Expected: 0 failed, 总数 ≥ Task 0 基线
cd H:\UGC\frontend && npm run build               # Expected: 构建成功

# 守卫核心行为（测试名示意）
python -m pytest tests/unit/a1/test_write_guard.py -q   # Expected: 全绿
```

### Final Checklist
- [ ] 备份标签本地+远端双存在（Task 0 证据）
- [ ] 全部 Must Have 项落地（F1 审计通过）
- [ ] 全部 Must NOT Have 项未出现（F1/F4 审计通过）
- [ ] 692+ 测试全绿（F2 验证）
- [ ] 设计文档 §8 验收标准可演示（F3 Playwright 证据）
- [ ] 用户明确 okay（F1-F4 呈报后）

---

## 附录 A：结合点与原项目改动对照表（用户要求 · 变更影响地图）

> 本附录回答两个问题：**改了原项目的什么**（A.1 存量文件改动）与**在哪里接入现状**（A.3 数据流结合点）。执行代理与审查代理均以此为准。

### A.1 存量文件改动清单（原项目改动 · 11 个文件）

| # | 文件（行数） | 改动位置 | 具体改动 | 保持不变 |
|---|---|---|---|---|
| 1 | `backend/app/domains/creation/a1/guide_engine.py` (394) | `_apply_fills` 118-142 | **核心改造**：无条件直写 → 守卫三分支（空→直写 / 非空且新≠旧→拦截转提案 / 相等→跳过）；返回签名 `(file_diff, proposals)` | finalize 门禁（>50%）、stall 检测机制、进度跟踪 |
| 2 | 同上 | A1Session 50-71 | +`pending_proposals: dict`、+`merge_counts: dict`（默认空，旧会话反序列化兼容） | 现有全部字段含 `pending_suggestions`（语义无关不混用） |
| 3 | 同上 | :230 与 :383 两调用方 | 适配新返回签名（守卫在 _apply_fills 内部故 stall 路径自动受保护） | 调用时序与上下文 |
| 4 | 同上 | 新增方法 | `resolve_proposal(session,key,choice)`、`_fallback_divergent(session,fills)` | — |
| 5 | `backend/app/domains/creation/a1/interviewer.py` (470) | InterviewFill 36-42、InterviewResult 44-52 | +`conflict_note: str\|None=None`、+`proposals: list=[]`、新增 Proposal 模型（merge_preview 默认 `f"{old}；{new}"`） | 9 条现有规则文本、innovative 判定、JSON schema 主体 |
| 6 | 同上 | `_build_prompt` 247-315 | 规则 3/4 之间插入三条：冲突预检 / 红线记忆（【不可动清单】标头置顶）/ 术语转译 | 其余规则原文与顺序 |
| 7 | 同上 | `_parse` | conflict_note 缺失透传 None | 现有字段解析 |
| 8 | `backend/app/api/a1_routes.py` (920) | chat 328-370 | 响应透传 proposals / divergent_question | 现有响应字段全部保留 |
| 9 | 同上 | ConfirmRequest + confirm 373-392 | +`kind: str="classification"` 判别；fill 分支调 resolve_proposal + 自然语言映射（封闭词表常量）；模糊语→needs_clarification | innovation_capture 分类提案路径零改动 |
| 10 | 同上 | GET file 440-452 | +`open_questions`/`edge_stats` 常驻字段（draft 态空） | 现有返回形状不变 |
| 11 | 同上 | finalize 455-508 | 门禁通过后挂 `extract_concept_edges` 调用；成功→概念边合并+确认态恢复；失败→warnings+纯 TREE 降级 | 409 门禁、v2 版本号、stale 标记、视觉背景预生成 |
| 12 | 同上 | `_build_graph` 183-250 | TREE 产物不动，概念边**追加**（节点引用校验：槽位名→条目 id=module.subfield 映射复用现有约定） | 三层行政拓扑结构与 cst_* 逻辑 |
| 13 | 同上 | `_FILES` 66-67 | +`confirmed_edges`/`rejected_edges`/`open_questions`/`edge_stats` 四键 | 现有键与生命周期 |
| 14 | 同上 | 文件尾部 | +2 端点：`POST /api/a1/file/{id}/edge/{key}/confirm`、`/reject` | — |
| 15 | `backend/app/models/knowledge_graph.py` | EdgeType 24-28、GraphEdge 49-62 | 枚举 +`SEMANTIC/RULE/STRUCTURE`（改前 lsp_find_references 全消费方检查） | TREE/CROSS 语义、apply_constraints 的 CROSS 生成行为 |
| 16 | 同上 | GraphEdge | +`relation: str=""`、`confidence: str=""`、`confirmed: bool=True`（全默认值→旧 JSON 兼容） | 现有 4 字段 |
| 17 | `frontend/src/pages/a1/A1Workspace.tsx` (1317) | chat 区 + A1GraphSection 1134-1217 | chat 消费 proposals/needs_clarification；图谱 Tab +状态徽章/一键重定稿/已拒绝清单/待问跳转 | 种子选择、双 Tab 骨架、a1_return_intent 机制、展板 |
| 18 | `frontend/src/components/guided/GuidedChat.tsx` (126) | 渲染层 | 提案卡片挂载位（≤3）、next_question 挂起占位、待问问句显示 | handleSubmit 流程、输入框行为 |
| 19 | `frontend/src/components/graph/A1KnowledgeGraph.tsx` (393) | 边渲染 187-208 起 | +3 类边样式通道（◆琥珀虚线动画/★绿点线标签/疑点红虚线）、[行政树\|概念网]切换、审核卡、筛选器、术语词典 | React Flow 骨架、TREE 紫实线、props 接口 |
| 20 | `.gitignore` (77) | 尾部 | +6 类运行时产物模式（且仅此 6 类） | 现有全部规则 |
| 21 | `backend/tests/unit/a1/test_guide_engine.py` | 追加 | 发散兜底测试 | **22 个存量测试零修改** |
| 22 | `backend/tests/unit/a1/test_a1_routes.py` | 追加 | 提案/confirm/edge 测试 | **23 个存量测试零修改** |
| 23 | `frontend/src/components/__tests__/A1KnowledgeGraph.test.tsx` | 追加 | 概念网/筛选器测试 | 现有断言 |

### A.2 新增文件清单（全新建设，零侵入）

| # | 文件 | 职责 | 所属任务 |
|---|---|---|---|
| 1 | `backend/app/domains/creation/a1/concept_edge_vocab.py` | v0.4 §3 全量边词表（14 边 ★/◆/◇）+ §2 八 AXIS 槽位 + `is_known_relation` | T2 |
| 2 | `backend/app/domains/creation/a1/concept_edge_extractor.py` | LLM 单次抽取 + 词表校验 + 表外转问句 + 降级信号 | T5 |
| 3 | `backend/tests/unit/a1/test_interviewer_extensions.py` | 模型扩展 + prompt 规则断言 | T1 |
| 4 | `backend/tests/unit/a1/test_concept_edge_vocab.py` | 词表结构/分布/唯一性 | T2 |
| 5 | `backend/tests/unit/a1/test_write_guard.py` | 守卫六类场景 | T4 |
| 6 | `backend/tests/unit/a1/test_concept_edge_extractor.py` | 抽取管线（全 mock LLM） | T5 |
| 7 | `frontend/src/types/a1.ts`（或扩展 graph.ts） | A1Proposal/OpenQuestion/EdgeStats | T3 |
| 8 | `frontend/src/api/`（扩展现有文件） | confirmFillProposal/confirmEdge/rejectEdge | T3 |
| 9 | `frontend/src/components/guided/ProposalCard.tsx` | 提案卡片（三按钮，合并默认高亮） | T8 |
| 10 | `frontend/src/components/guided/ProposalTray.tsx` | 右下角托盘（⚑计数红点） | T8 |

### A.3 数据流结合点（现状机制如何被复用/接入）

| # | 新能力 | 接入的现状机制 | 结合方式 |
|---|---|---|---|
| 1 | 写入守卫 | stall-guard 强制分配（guide_engine:230） | 守卫在 `_apply_fills` 内部 → stall 路径**自动**受保护，无需改 stall 代码 |
| 2 | fill 提案确认 | 现有 `/api/a1/chat/confirm` + innovation_capture | 同端点 `kind` 判别共存；分类提案行为零改动 |
| 3 | 概念边生成 | 现有 finalize 流程（455-508） | 门禁通过后**追加** extract 调用；TREE 图谱产物不动 |
| 4 | 概念边入图 | 现有 `_build_graph` 三层拓扑 | 追加边而非改结构；节点 id 复用 `{module_id}.{subfield_id}` 现有约定 |
| 5 | 确认态持久化 | 现有 `_FILES` 内存会话存储 | 新增 4 键同生命周期；re-finalize 键匹配恢复 |
| 6 | 边渲染 | 现有 TREE/CROSS 双样式通道（187-208） | 扩展第三/四/五通道，CROSS 语义留给约束拓扑 |
| 7 | 状态徽章 | 现有 stale 标记 + 409 门禁 + v2 版本号 | 徽章数据全部来自现状字段，一键重定稿复用 finalize API |
| 8 | 待问跳转 | 现有 `a1_return_intent` localStorage 键 | 键值 'chat' 复用，零新路由 |
| 9 | LLM 调用 | 现有 provider.chat_json（含 400 降级重试链/围栏剥离） | 抽取器直接复用，零 provider 改动 |
| 10 | divergent_question | 现有 InterviewResult 字段（已建模未使用） | 代码兜底填值 + 前端展示，字段本身零改动 |

### A.4 明确不改的原项目部分（防误伤清单）

- `semantic_compiler.py`（355 行，保持骨架——设计 §10 YAGNI）
- `worldview_upload.py` / `ip_poster.py` / `interaction_log.py` / `innovation_capture.py` 的现有逻辑
- `a1_question_tree.py`（词表编译只读对照，发现问题记 slot_note 不改文件）
- `provider.py` / `config.py` / 全部 LLM provider 抽象
- finalize 409 门禁、模块 >50% 门禁、stale 机制
- 前端：种子选择页、IP 展板页、资产审核页、终端 Demo
- **现有 692 个测试的断言内容**（只允许追加文件/用例，不允许修改存量断言）
- `pending_suggestions`（stall 示例答案机制，与 pending_proposals 语义无关）
