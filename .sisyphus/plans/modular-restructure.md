# 甲（Jia）：模块化产品架构重组实施计划

## TL;DR

> **Quick Summary**: 产品方三裁决（2026-09-22）：①**甲**=放弃 A1/A2/A3 固定阶段架构，重组为**冲动类型→模块配方**的模块化架构——故事型用户拿到剧情/角色/情感线模块组合，设定型拿原 10 世界建构模块，A2 产出模块（主模组文字版/骰子/角色模板）入池；②所有可用材料并入甲计划；③所有后续计划（A2 P0/B1/E2/E3）合并重梳。触发证据 = E1-Lite 上线后真实故事用户访谈翻车（`.sisyphus/evidence/jia-requirement-evidence-interview-failure.md`：偏转被无视重问/剧情细节被误判为主剧情修改/降级建议聋——模块级路由天花板实证）。技术路线 = 三路挖掘已证实（70KB 证据）：**E1-Lite 三数据字典已是配方雏形，问卷树是纯数据+函数门面，最小阻力 = 配方表并行、默认值兜底、四处全集引用换参数**。工作分支 `v2-modular`（基线 f24c5f4，A1+E1-Lite 完整态：后端 837 测试/前端 231）。
>
> **Deliverables**:
> - M0 止血：访谈偏转死循环 hotfix（偏转→占位跳过推进指针 + 剧情细节→素材槽归档 + 故事侧降级建议换料）
> - M1 模块注册表底座：`module_registry.py`（模块池+配方表）+ 问卷树参数化 + A1Session 配方字段 + 四处全集引用改造 + 契约测试重锚
> - M2 故事模块族：剧情主线/角色速写（character_sketch 文本槽）/情感线新模块 + 4 故事型配方 + 前端配方感知
> - M3 产出模块入池：主模组文字版（A2 回收：finalize 八步+九节树+LLM 确定性降级）/骰子投影/角色投影，模块依赖 409 链
> - M4 E2/E3 并入：field_sources 四出口/推断包/冲动坐标观测层/ai_fill 字段级/看门狗/人格卡/埋点
> - 治理：decision-log D14 + impulse spec v1.3（契约翻案）+ A2 规格归档头 + B1 重定义提案
>
> **Estimated Effort**: Large（M0 小；M1 中；M2-M4 各中大；总计数周）
> **Parallel Execution**: YES - M0 立即 → M1 串行 → M2/M3 并行 → M4 → FINAL 四审
> **Critical Path**: M0 → M1 → M2 → M4 → FINAL（M3 与 M2 并行）

---

## Context

### Original Request
产品方指令（2026-09-22，三连裁决）：
1. **甲**：整体模块化，不能用原 A1/A2/A3 了（产品骨架重组，取消固定阶段）
2. **先计划甲，把可用材料放入甲计划**
3. **所有后续计划，重新合并入甲计划，重新梳理**

裁决背景：E1-Lite 完成当日，真实故事向用户（plot 主+romance 次）访谈全程翻车——首问正确（main_plot）、语气正确（锚点生效），但世界建构问卷轰炸导致用户怒斥"垃圾引导！现在的引导完全无法适配故事向的用户"。

### Interview Summary
- 用户已裁决搁置 A1→A2 阶段流水线叙事；A2 规格中"与阶段无关的资产"（骰子/角色投影器、主模组文字版管线、确定性降级范式）全部入池
- B1 基线重定义（验收对象从"A2 P0 产出"改为"甲的模块化产物"）——本计划呈交时一并提案
- E2/E3 从"待排期"升为"并入甲计划主体"
- 分支策略已执行：`backup/a1-e1lite-baseline-2026-09-22`（基线快照）+ `v2-modular`（一切后续代码起点）

### Research Findings（三路挖掘，70KB 证据已落盘）
**证据文件**：
- `.sisyphus/evidence/a2-plan-mining-a2-specs.md`（A2 两规格回收清单）
- `.sisyphus/evidence/a2-plan-mining-impulse-spec.md`（E1余量/E2/E3 逐字提取）
- `.sisyphus/evidence/a2-plan-mining-codebase.md`（A1 代码耦合盘点）
- `.sisyphus/evidence/jia-requirement-evidence-interview-failure.md`（翻车记录）

**关键事实（file:line 已核对）**：
- `TYPE_MODULE_PRIORITY`（guide_engine.py:55-64）/`TYPE_ENTRY_SUBFIELD`（:66-70）/`ANCHOR_BY_TYPE`（interviewer.py:39-49）——E1-Lite 三数据字典**已是配方数据形态**，直接升格为注册表数据源
- 问卷树 `MODULES: list[Module]`（a1_question_tree.py:32）纯 TypedDict 数据；全部访问经函数门面（:347-414）——**无裸列表旁路**
- **四处全集硬引用**（手术点）：finalize 门禁 a1_routes.py:1137（`module_ids()` 全集遍历）、graphify 锚点校验 graphify.py:239/:474、TIER_MAP 封闭 10 键 tier_map.py:12-34（"Do not add an 11th module tier"成文契约）、`first_module()` 默认 guide_engine.py:101-102
- `_type_ordered_modules`（guide_engine.py:72-86）现为**纯置换**（head+rest 保全集）——子集化是唯一产品语义级变更
- 上传链 schema 程序化派生自 MODULES（worldview_upload.py:193-205）——零阻力区
- 护栏全内禀：warning_ledger 五源/真值闸占位词典/预算三级/stale 横切
- A1Store 迁移先例：`model_validate`+全字段默认值（creator_*/prefill_fields/answer_clips 先例）——新增 recipe 字段零迁移
- A2 可回收资产（🟢内禀直搬）：骰子五链+三封闭枚举+四步投影+signal_sources 溯源；角色 4 相位+常量/变量/锚点；主模组 finalize 八步+九节树+LLM 失败确定性降级；409 依赖契约族（missing_dice_template 等）；StageCode 发号/血缘/stale 机制层
- A2 阶段绑定（🔴需重定义）：W/S 编码语义、"A3 边界"表述、路径 A/B 叙事、P0-P3 分期坐标（改为"模块上线序"）
- E1 余量/E2/E3 权威定义在 impulse spec §8（L293-296）：推断包/Q2/公理卡/骰子三方案/character_sketch 文本槽/field_sources 四出口/看门狗（E2）/开场叙事（E1末-E2初，新 LLM 生产方须契约评审立项）/冲动坐标三件套+四护栏（§10.1）/live_projection/人格卡/埋点三项/入口单选 sunset
- 版本规则：甲触及 §5.2 路由契约 → spec 须升 **v1.3+** 并按台账元规则处理（decision-log 立 D14）

### Metis Review（主会话内化自审，缺口已处置）
- **G1 置换→子集语义**：配方外模块对门禁的语义（不适用 vs 未答）直接改变 missing_sections 契约——**DECISION NEEDED 1**（默认：不适用，配方内全达标即可 finalize）
- **G2 tier 闭集契约**："Do not add an 11th module tier"是成文契约（tier_map.py 头注+C5 测试）——**DECISION NEEDED 2**（默认：故事模块复用既有 tier 值映射，不新增层）
- **G3 存量会话兼容**：无配方字段的老会话 → 默认配方=原 10 模块全集（零迁移，先例 creator_*）——行为逐字节兼容
- **G4 R6 可达性重述**：子集配方下"只前移不跳过"自动满足（配方即全集，配方内仍纯置换）；门禁可达性 = 配方内数学可达——契约测试重锚而非废弃
- **G5 prompt 全集泄露**：interviewer `_progress_summary`/`_field_catalog`（interviewer.py:183/:202，Momus 勘误）按 MODULES 全集渲染——配方化必须同步，否则 LLM 被诱导提问配方外字段
- **G6 M0 与 M1 文件交叠**（Momus 措辞修订）：M0 与 M1 同改 guide_engine.py/interviewer.py 但**不同区域**（M0=偏转分支/素材槽/prompt 规则；M1=门面参数化/注册表/全集引用）——依赖矩阵已排 M0→M1 串行合入规避冲突
- **G6b M0 JSON 契约豁免**（Momus G10 修订）：M0 的 `{"deflect": true}` 为访谈 JSON 契约**新增可选字段 = 向前兼容豁免**（旧解析器忽略未知键），与 Must NOT Have 第 4 条"契约面无版本扩张"（指修改/删除既有字段）不冲突——豁免理由入 D14 附录
- **G7 A2 内部冲突回收须裁决**：ScopeBoundary max_party_size 4(S1) vs 6(S2)、端点 module-text(S1) vs doc(S2)、M 重定稿 v+1(S1) vs 开新文件(S2)——**DECISION NEEDED 4**
- **G8 新 LLM 生产方**：开场叙事端点 + M3 module_compile = 新 LLM 生产方清单——三铁律"单生产单消费"扩展评审须立项留痕——**DECISION NEEDED 5**（统一清单，归 M4/M3）

---

## Work Objectives

### Core Objective
按产品方甲裁决交付模块化架构：**模块池 + 冲动类型配方**取代固定阶段流水线；故事向用户在 90 秒内进入故事模块组合（剧情主线/角色/情感线），设定向用户保持原 10 模块体验**逐字节不变**；A2 产出能力以模块身份入池；E2/E3 全量并入；治理动作同步（D14/spec v1.3/归档/B1 提案）。

### Concrete Deliverables
- 新增：`backend/app/domains/creation/shared/module_registry.py`（模块池+配方表+查询门面）
- 修改：`backend/app/domains/creation/seed/a1_question_tree.py`（查询函数配方参数化——MODULES 数据不动）
- 修改：`backend/app/domains/creation/a1/guide_engine.py`（A1Session 配方字段+sync_position 子集遍历）
- 修改：`backend/app/domains/creation/a1/interviewer.py`（prompt 配方感知+偏转/跳过/素材归档规则）
- 修改：`backend/app/api/a1_routes.py`（start_session 配方落定+finalize 门禁配方化）
- 修改：`backend/app/domains/creation/a1/graphify.py` + `a1/tier_map.py`（锚点/tier 配方并集——Momus 勘误路径）
- 新增：故事模块内容（剧情主线/角色速写/情感线——字段集初稿+产品终审）
- 新增：产出模块（A2 回收三件：主模组文字版/骰子投影/角色投影——`backend/app/domains/creation/modules/`）
- 修改/新增：前端配方感知（A1Workspace/impulse 消费配方元数据）
- 新增：M4 各件（field_sources/推断包/坐标观测/ai_fill 字段级/看门狗/人格卡/埋点）
- 治理：decision-log D14、impulse spec v1.3、A2 规格归档头、PROJECT_STATE、B1 重定义提案文档

### Definition of Done
- [ ] `cd backend && python -m pytest tests/unit -q --no-cov --ignore=tests/unit/a1/test_a1_warning_ledger.py` 全绿（基线 837 + 新增，4 preexisting 除外）
- [ ] `cd frontend && npx tsc --noEmit` 0 errors；`npx vitest run` 231+ 全绿
- [ ] 设定型（无 profile/healing/nostalgia）行为与 v2-modular 基线**逐字节一致**（**Momus F5 修订——比较面 = 确定性输出面**：门禁计算结果/模块遍历序/上传 schema 文本/`_build_sections` 结构/graphify 输入 prompt（排除 LLM 生成体与时间戳）；回归用例 = 确定性面快照比对）
- [ ] plot 型新会话：模块组合只含故事配方，首问=剧情主线模块首字段，全程不出现"势力类型"类世界建构轰炸
- [ ] A2 产出模块：主模组文字版 finalize→Markdown 零加工可开团（骰子/角色投影确定性，signal_sources 溯源）
- [ ] 治理四件落地（D14/v1.3/归档头/B1 提案）

### Must Have
- **模块注册表**（命名逐字锁定）：`MODULE_POOL`（初始 = 原 10 世界建构模块引用 + **M11 角色/M12 剧情**故事模块【8+2 重锚定定版，情感线并入 M12+M10 preset】 + **L2 产出×5**（主模组文字版/骰子投影/角色投影/玩法设计完整形态/商业分析报告）+ **L3 产出×3**（场景扩写/资产管线/叙事渲染））/ `Recipe`（id、impulse_type、module_ids 有序子集、entry_subfield、anchor、ai_fill_policy）/ `RECIPES: dict[str, Recipe]`（**8 型 + default**）/ `CHANNELS`（探索态+玩法设计链——2026-09-22 重锚定撤销 exploration 冲动行）（D18 缓期）
- **默认配方 = 原 10 模块全集**：无 creator_primary / 未知值 / 存量会话 → default 配方（行为零变化）
- **E1-Lite 三数据字典并入**：TYPE_MODULE_PRIORITY/TYPE_ENTRY_SUBFIELD/ANCHOR_BY_TYPE 数据迁入 Recipe，消费侧改查表
- **门禁语义**：finalize 门禁 = 配方内模块全达标；missing_sections = 配方内未达标模块（DECISION NEEDED 1 默认值）
- **R6 重述**：配方内纯置换可达性进契约测试
- **故事模块初稿**（字段集待产品终审，DECISION NEEDED 3）：剧情主线（主线陈述/核心抉择/张力源/赌注）、角色速写（character_sketch 文本槽：主角轮廓/关系/执念）、情感线（相遇情境/情感张力/发酵节奏/边界声明[romance 合规]）
- **4 故事型配方**：plot/romance/unsure/character_driven = 剧情主线+角色速写+（romance 加情感线）+ 有限世界建构子集（spec §5.2 各型前移序为子集序）
- **A2 回收三件**（A2 规格行号见证据文件）：主模组文字版（finalize 八步 S1:397-410/九节树 S2:385-403/LLM 失败确定性降级）、骰子投影（五链+四步法 S2:449-466+signal_sources）、角色投影（4 相位+常量/变量/锚点）——`signal_requirements` 声明输入依赖，缺料→409（契约族照搬）
- **M0 三件**：①偏转检测→占位跳过（写占位答案推进指针，J1 真值闸保门禁语义不破坏）②剧情/角色细节→character_sketch 文本槽或 open_questions 归档（不再误判为主剧情修改提案）③故事侧会话 suggest_examples 换料（故事语料非势力模板）
- **M4（E2/E3 并入，权威定义 impulse spec §8/§10.1）**：field_sources 四出口接线（D12 已冻结设计）/推断包（复用 pending_proposals+confirm，不直写 answers）/冲动坐标观测层（三件套落库+看板，只看不判）/ai_fill 字段级粒度（未决①一并设计）/看门狗/live_projection/人格卡（命名未决③）/埋点三项升级/入口单选 sunset
- **治理**：decision-log D14（甲三裁决+E1-Lite 翻车证据引用）；impulse spec v1.3（§0 变更记录+§5.2 路由表配方化重述+§8 分期改模块上线序）；A2 两规格加归档头（"已被甲计划收编，资产映射见 jia 计划"）；B1 重定义提案

### Must NOT Have (Guardrails)
- ❌ 设定型用户体验任何变化（默认配方=全集，行为逐字节兼容）
- ❌ 破坏三铁律：NL/SIR/KG 单生产单消费、图谱确定性装配、诚实可观测
- ❌ LLM 进控制流（路由/配方选择/门禁全部确定性代码；LLM 只产内容与建议——D-A2-4 普适化）
- ❌ 删除存量数据/契约面无版本扩张（store 默认值先例；API 新增可选字段而非改既有）
- ❌ prompt 变体爆炸（R2：配方差异是数据不是代码，prompt 骨架恒 1）
- ❌ 未经 DECISION NEEDED 裁决擅自定：门禁子集语义/tier 扩展方式/故事模块字段文案/ScopeBoundary 冲突/新 LLM 生产方
- ❌ M0 hotfix 顺手重构（Bugfix Rule：最小修复）

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed.
> 计划外人工步骤：仅 DECISION NEEDED 1-5 的产品方确认（均有安全默认值内置，不阻塞）。

### Test Decision
- **Infrastructure exists**: YES（pytest 1009/vitest 231/tsc 0——2026-09-24 全绿实测）
- **Automated tests**: TDD（注册表与门禁语义先契约测试后实现；故事模块内容测试先行）
- **Framework**: pytest / vitest + tsc
- **新代码覆盖率单独 ≥85（2026-09-24 测试方式改进条款，产品方指令）**：甲计划 M1-M4 新增/重写文件的行覆盖率单独核算 ≥85%——全局门禁 80 为现实线（遗留线不拖新代码标准），M1-M3 TDD 回升后全局线回调 85+；实现方式 = 根目录 verify.ps1 一键体检（三命令+覆盖率+死码嫌疑人清单+快照落 .sisyphus/evidence/baseline-latest.txt）每波次末必跑 + C8 快照契约兜底

### QA Policy
- 每任务 agent 执行 QA（happy+failure 双路径），证据存 `.sisyphus/evidence/jia-task-{N}-*.txt`
- 每 Wave 末跑全量三命令
- 回归铁律：设定型逐字节等价用例（默认配方）每 Wave 必跑

---

## Execution Strategy

### Parallel Execution Waves

```
Wave M0（止血，立即独立）:
└── M0: 访谈偏转死循环 hotfix 三件 [quick×3 或 deep]

Wave M1（注册表底座，串行）:
└── M1: module_registry + 问卷树参数化 + A1Session 配方字段 + 四处全集引用 + 契约测试重锚 [deep]

Wave M2/M3（并行，文件所有权互斥）:
├── M2: 故事模块族内容 + 4 故事型配方 + interviewer/前端配方感知 [deep]
└── M3: A2 回收三件入池（modules/ 域）+ 依赖 409 链 + 文字版导出 [deep]

Wave M4（E2/E3 并入，依赖 M2）:
└── M4a: field_sources + 推断包 [deep]
└── M4b: 冲动坐标观测 + ai_fill 字段级 + 看门狗 + live_projection [deep]
└── M4c: 人格卡 + 埋点三项 + sunset（可后置） [quick/deep]

Wave 治理（与 M4 并行）:
└── G: D14 + spec v1.3 + A2 归档头 + B1 提案 [writing]

Wave FINAL（四审并行 → 用户终审）:
├── F1 计划合规审计 [ultrabrain]
├── F2 代码质量审查 [unspecified-high]
├── F3 真实手动 QA（含故事型全流程重放——翻车场景必须翻绿） [unspecified-high]
└── F4 范围忠实检查 [deep]
→ 呈交用户终审
```

### Dependency Matrix

| 任务 | 依赖 | 被依赖 |
|---|---|---|
| M0 | — | 无（独立止血） |
| M1 | M0（建议先合，避免同文件冲突） | M2, M3, M4 |
| M2 | M1 | M4, F1-F4 |
| M3 | M1（注册表先行；A2 资产独立文件） | F1-F4 |
| M4a/b | M1+M2 | F1-F4 |
| M4c | M4a（埋点依赖坐标落库） | F1-F4 |
| G | 甲裁决已下 | 用户终审 |
| F1-F4 | 全部 | 用户 okay |

---

## TODOs

- [x] 0. M0 止血：访谈偏转死循环 hotfix 三件

  **What to do**:
  - `backend/app/domains/creation/a1/interviewer.py`：
    - interview prompt 规则增补：用户明确表示"不想答/先聊别的/专注故事"→ 输出 deflection 标记（JSON 契约内新增可选字段，如 `{"deflect": true}`——**Momus G10 豁免标注**：新增可选键=向前兼容豁免，旧解析器忽略未知键，不违反 Must NOT Have 第 4 条），**不生成 fills**
    - 偏转时 interviewer 产出建议回复引导下一话题（可复用锚点语气）
  - `backend/app/domains/creation/a1/guide_engine.py`：`handle_message` 消费 deflection → 对 current_subfield 写**占位答案**（"（用户跳过）"——已在 `_PLACEHOLDER_ANSWERS` 语义内，J1 真值闸保门禁不计数）→ `sync_position` 指针前进；连续偏转≥2 → 该字段进 open_questions 归档
  - 剧情细节归档：fills 判定新增规则——主冲动为故事型（plot/romance/unsure/character_driven）且输入为叙事细节（无世界建构字段语义）→ 写入 `A1Session.character_sketch`（新文本字段，默认 ""，E1 spec L251 文本槽设计）或 open_questions，**绝不**触发 main_plot 等已答字段的替换/合并提案
  - 故事侧降级建议：suggest_examples 的 prompt 增补故事型上下文规则（示例取种子叙事语料而非势力/政治模板）
  - 新增 pytest：偏转→占位推进+门禁不计数；剧情细节→素材槽归档不触发提案；故事型建议不含势力模板
  **Must NOT do**: 不动 sync_position 遍历结构/MODULES/TYPE_MODULE_PRIORITY（M1 领地）；不改 prompt 骨架份数
  **Agent**: quick×2 或 deep | **Skills**: [test-driven-development]
  **Commit**: `fix(a1): deflect-to-skip placeholder advance + story-detail-to-sketch archive + story-aware suggestions (M0 stopgap)`
  **Acceptance**: 翻车记录四场景（重问死循环/误判提案/聋建议/纪元题——纪元题的根治在 M2 配方，M0 验收前三件）在 pytest 重放中全部翻绿；全量回归无新增失败

- [ ] 1. M1 模块注册表底座（前置 1a：测试环境清债）

  **What to do**:
  - **M1a 前置清债（净基线）**（= D9 v2 闸门，2026-09-24 台账 D16 重定义——另含前后端交互层三项：vitest config 排除 Playwright spec / 前后端类型对齐基线盘点 / 全链路冒烟）：test_c7_loop_e2e 4 失败 + tests/xt/test_a1_warning_ledger 收集错误转正（根因 `ModuleNotFoundError: tests.unit/tests.xt`——修 conftest.py 或 pytest.ini importmode）；前端 tsc 已达标（2026-09-22 实测 exit 0）零工作量；graph.spec Playwright 存量失败只留档另立项。目标：三命令零 preexisting 失败——**这是甲计划的新基线**
  - **【执行注记 2026-09-24】M1a 实况**：①c7/xt 两项实由 eb22a6f（HALT 前提交）修复，全量复测 **1009/1009 全绿**——上行记载已过时（勘误归档，不改原文）；②vitest e2e 排除：配置早已就位（vitest.config `exclude: tests/e2e/**`）；③C2 对齐盘点完成（三先例全绿：relationLabel 7 测试逐字对齐 / WarningLedgerEntry types/a1.ts↔warning_ledger.py / test_module_ids_match_spec 问卷树锁定）；④C3 冒烟完成（/api/health、/api/a1/seeds、前端 /a1 三测全 200，进程已清）；⑤附做死码清理（产品方裁决 A）：删 9 文件（四死模型+四死测试+demo 脚本）+ dimension.py 死类区切除 469→311 行（RedOutput 因 DimensionResultSet.RED 引用保留）；⑥**唯一未决：覆盖率门禁 85% vs 实测 80.16%**（C 降 80 / B 豁免遗留线，待产品方一字裁决）——裁决后 M1a 关闭、M1 开工
  - **【执行注记 2026-09-24】M1a 实况**：c7/xt 两项实由 eb22a6f（HALT 前提交）修复，全量复测 1009/1009 全绿（本行上文记载已过时）；vitest e2e 排除配置早已就位；C2 完成（relationLabel/WarningLedgerEntry/test_module_ids_match_spec 三先例全绿）；C3 冒烟完成（/api/health + /api/a1/seeds + 前端 /a1 全 200）；附做死码清理（产品方裁决 A）：删 9 文件 + dimension.py 死类区 469→311 行（RedOutput 因 DimensionResultSet.RED 引用保留）；**唯一未决：覆盖率门禁 85% vs 实测 80.16%（C 降 80 / B 豁免，待产品方）——裁决后 M1a 关闭、M1 开工**
  - 新建 `backend/app/domains/creation/shared/module_registry.py`：
    ```python
    # 甲：模块池 + 冲动配方（产品方 2026-09-22 裁决）
    # 默认配方 = 原 10 模块全集 → 无 profile/存量会话行为零变化（G3 兼容）
    ModuleDef = ...  # id/family/fields 引用/tier
    Recipe = ...     # id/impulse_type/module_ids/entry_subfield/anchor/ai_fill_policy
    RECIPES: dict[str, Recipe] = { "default": ..., "plot": ..., ... }  # 9型+default
    ```
    E1-Lite 三字典数据迁入（TYPE_MODULE_PRIORITY→配方 module_ids 序；TYPE_ENTRY_SUBFIELD→entry_subfield；ANCHOR_BY_TYPE→anchor）——原字典位置留 re-export 兼容 import（或一次性改全部消费点）
  - `a1_question_tree.py` 门面函数加配方参数（`recipe: Sequence[str] | None = None` 默认 default=全集）：module_ids/get_module/all_subfield_keys/is_finalizable/next_subfield/next_module——**MODULES 数据零改动**
  - `A1Session` 新增 `recipe_id: str = "default"` / `recipe_modules: list[str] = []`（空=default 全集，store 零迁移）；start_session 按 creator_primary 落定配方
  - **全集硬引用改造（Momus 复核后完整清单，六处）**：①finalize 门禁 a1_routes.py:1137（遍历配方集）②graphify 锚点校验 graphify.py:239/:474（配方并集——**注意调用链签名变更**：当前 `legal = set(all_subfield_keys())` 是模块级全局集合，改造需把 recipe 并集经参数传入 graphify 调用链，涉及 `parse_graphify_raw`/`_validate` 等函数签名，M1 内一并完成）③`first_module()` 默认 guide_engine.py:101-102（配方首模块）④`_build_sections` a1_routes.py:958 ⑤**ip_poster.py:8,39-40**（直接 import MODULES 全集遍历建展板 panels——改为配方感知：故事会话的展板含故事模块 panels，行为归 M1 定义+M2 内容）⑥**worldview_upload.py:24-29,193-200**（`_schema_catalog()` 全集渲染进上传 LLM prompt——作用域策略见 M2 落位裁决：default 配方渲染不变，故事型×上传链语义归 DN6）
  - tier_map：故事模块复用既有 tier 映射（DECISION NEEDED 2 默认）——`module_tier_coverage` 断言改"池内模块必有 tier"
  - 契约测试重锚：C4/C5 闭集改池语义；test_type_driven_queue 置换断言改"default 配方内置换等价 + 故事配方子集断言"；新增"设定型逐字节回归"用例（default 配方全链路 vs v2-modular 基线快照）
  **Must NOT do**: MODULES 列表/世界建构 35 字段/question 文案零改动；默认配方行为零变化（回归铁律）
  **Agent**: deep | **Skills**: [test-driven-development, systematic-debugging]
  **Commit**: `feat(modular): module registry + recipe-parameterized question tree + subset gate semantics (M1 core)`
  **Acceptance**: default 配方逐字节回归绿；plot 配方（临时测试用）子集生效；四处全集引用清零；全量三命令绿

- [ ] 2. M2 故事模块族 + 故事型配方

  **What to do**:
  - **数据落位定死（Momus F2 修订）**：故事模块放**独立 `story_modules.py` 经 MODULE_POOL 入池，不并入 a1_question_tree.MODULES**——理由：MODULES 全集消费面（worldview_upload 上传 prompt schema/interviewer prompt 目录/ip_poster 展板/tier 闭集断言）对设定型路径零扰动，"设定型逐字节不变"由此在架构上成立；上传链作用域：default 配方=今日行为不变，故事型×上传链组合语义归 **DN6**（默认：上传链仅 default/怀旧路径暴露）
  - 两个新故事模块（**2026-09-22 重锚定定版**，字段文案**DECISION NEEDED 3 终审**，权威定义见模块清单拓展文档）：
    - M11 角色模块（id: 角色）：身份/欲望/缺陷/关键关系/弧光方向/角色视觉 6 字段——原"第 0 模块"落座；M0 的 character_sketch 素材槽内容迁移入此（归 M2 实施）
    - M12 剧情模块（id: 剧情）：开场事件/核心抉择/张力源/线索链/秘密维度/分支预案/人物绑定/走向基调/场景挂载 9 字段——具体细节剧情的直接落点（A2-v0.2 叙事相位素材转化，设计依据见拓展文档 §1.1）；情感线并入其场景化字段 + M10 爱情 preset
  - RECIPES 按架构 v2 §3.1 的 8+2 矩阵（产品方定版优先序 + ⭐M12 插位提案待终审）——**世界建构子集的裁剪与序 = DECISION NEEDED 6**
  - interviewer 配方感知：`_progress_summary`/`_field_catalog`（interviewer.py:183/:202，Momus 勘误行号）按配方渲染（G5 泄露修复）；锚点查 Recipe.anchor
  - 前端：seeds/进度条/模块维度消费配方元数据（`_build_sections` a1_routes.py:958 配方化顺带完成）；impulse 确认后显示配方预览（可选，轻量）
  **Must NOT do**: 设定型配方零触碰；故事模块字段文案未经终审不得定稿（初稿+DECISION 标注）
  **Agent**: deep | **Skills**: [test-driven-development]
  **Commit**: `feat(modular): story module family + 4 story-type recipes (M2)`
  **Acceptance**: plot 新会话全程无"势力类型"类轰炸；首问=剧情主线.核心抉择（或终审文案）；romance 配方含情感线+边界声明；设定型回归绿

- [ ] 3. M3 A2 产出模块入池

  **What to do**:
  - 新建 `backend/app/domains/creation/modules/`：A2 资产平移 + A3 遗迹复活，**L2 五件 + L3 三件**（蓝图=代码模块设计 §2.4；规格行号见 `.sisyphus/evidence/a2-plan-mining-a2-specs.md` 与 `jia-mining-a2v02-and-a3.md`）：
    - `main_module.py`：主模组文字版——finalize 八步（S1:397-410 逐字可搬）+ 九节树（S2:385-403）+ LLM module_compile 单点+失败确定性降级（骨架+ledger 披露）
    - `dice_projector.py`：骰子投影——封闭三枚举（DiceCoreType/GrowthSystem/DifficultySystem，逐字）+ 四步法（S2:449-466）+ signal_sources 溯源（信号=骰子设定/reality_rule/growth/cost 五链）
    - `character_projector.py`：角色投影——4 相位（叙事/机制/资源/定向）+ 常量/变量/锚点分配 + 依赖骰子（缺→409 missing_dice_template 契约照搬）
  - 模块注册：三件入 MODULE_POOL（family=output），`signal_requirements` 声明输入依赖（H §2.2 L167-181 信号映射表转译）
  - 端点（a1_routes 域内新增，文档导出资源名已裁决 = doc、界面「文档输出」（D15）；路径域 a1 vs modules 于本波次施工前定夺统一：409 依赖链 + stale 永不 409 + ledger 透传
  - StageCode：复用发号/血缘/registry（🟢机制层）；W/S 语义已裁决（D15）：W=世界图/M=模组图族（含 TD/TC/R）/S=场景图（不停发）
  **Must NOT do**: 不复活"A2 阶段"叙事/路径AB/S 编码；LLM 产结构数值（D-A2-4：只产文案与建议）
  **Agent**: deep | **Skills**: [test-driven-development]
  **Commit**: `feat(modular): A2 asset salvage as output modules - main-module doc/dice/character projectors (M3)`
  **Acceptance**: 主模组文字版 finalize→Markdown 零加工可开团；骰子/角色投影确定性（同输入同输出断言）+溯源徽章；409 依赖链正确；零 LLM key 可跑通免费线

- [ ] 4. M4a field_sources + 推断包

  **What to do**（权威定义 impulse spec §3.1/§6，D12 已冻结）:
  - field_sources：平行元数据同键空间，四来源枚举（human/llm_fill/dice_rec/upload_prefill），四写入出口各接线一处（直答/_apply_fills/parse_modules/骰子推荐），都标自动标只看不判，契约测试"有值字段必有来源+键空间⊆配方并集"，存量 unknown 兜底
  - 推断包：`a1/inference_pack.py`（LLM 单次，同 interviewer 模式），输入=冲动类型+上下文，输出 3-5 条；复用 pending_proposals+confirm 交互；判定双写（creator_profile 置信修正 + 对/接近→fills 通道热启动，J1 拦截占位）；**不直写 answers**
  **Agent**: deep | **Skills**: [test-driven-development]
  **Commit**: `feat(modular): field_sources four-outlet wiring + inference pack with confirm flow (M4a)`
  **Acceptance**: 四出口标记矩阵全绿（每写入出口各一用例+键空间⊆配方并集契约测试）；推断包 3-5 条生成/confirm 双写一致（坐标置信修正+fills 热启动经 J1）；存量为值字段 unknown 兜底不抛错；不直写 answers 断言绿

- [ ] 5. M4b 冲动坐标观测 + ai_fill 字段级 + 看门狗 + live_projection

  **What to do**（§10.1 逐字 + 未决①收口）:
  - 冲动坐标观测层：三件套（叙事-建构轴[0,100] 锚点初值逐字 L309/置信度/安全旗单向棘轮）存 creator_profile 扩展；确定性更新函数（只吃显式信号+全留痕）；四护栏（阻尼/可达性不变式进契约测试/安全旗棘轮）；**E2 只看不判**——落库+看板数据接口，不驱动路由
  - ai_fill 字段级粒度：配方 ai_fill_policy 字段级声明（未决①收口：如 romance 型 faction_type 留给用户）——fills 范围按策略过滤
  - 看门狗：每 N 轮门禁检查，配方内未访模块后半程确定性回归提示
  - live_projection：`a1/live_projection.py` 零新 LLM，半成品 answers→背景树 L0-L2 投影（从 _build_graph 抽装配函数复用）
  **Agent**: deep | **Skills**: [test-driven-development]
  **Commit**: `feat(modular): impulse coordinate observation + field-level ai_fill + watchdog + live projection (M4b)`
  **Acceptance**: 坐标确定性更新断言（显式信号→可复现坐标变化+全留痕）；四护栏各一契约测试（防振荡：每会话≤1 次重排/可达性不变式/安全旗棘轮：升旗不降/确定性更新）；路由行为零变化（只看不判回归）；ai_fill 字段级过滤按配方策略生效；看门狗后半程回归提示触发；live_projection 零 LLM 快照测试绿

- [ ] 6. M4c 人格卡 + 埋点三项 + sunset（可后置）

  **What to do**:
  - 人格卡：命名+视觉+一句话解读（命名 DECISION NEEDED——未决③，默认"ECHO 创作人格"占位）；数据源=creator_profile+坐标
  - 埋点三项升级：跳过率/完成度/自报-行为错位地图（前端 telemetry 扩展，schema_version 升 2——E0 v1 兼容读取）
  - 入口单选 sunset：行为信号成熟后选卡权重递减（坐标置信度阈值驱动，本期只留接口不启用）
  **Agent**: quick/deep | **Skills**: [test-driven-development]
  **Commit**: `feat(modular): persona card + telemetry v2 + sunset interface (M4c)`
  **Acceptance**: 人格卡渲染（creator_profile+坐标数据源断言）；telemetry v2 写入+E0 v1 兼容读取回归；sunset 接口存在且默认关闭

- [ ] 7. G 治理四件

  **What to do**:
  - `docs/decision-log.md` 新增 **D14**：甲三裁决逐字 + E1-Lite 翻车证据引用 + 推翻/收编清单（09-20 顺序裁决 A2 P0 让位；D-A2-7 推翻；A2 规格收编）
  - impulse spec 升 **v1.3**：§0 变更记录；§5.2 路由表配方化重述（模块配方列取代前移序列）；§8 分期改"模块上线序"；标注 D14
  - A2 两规格加归档头（"已被甲计划收编——资产映射见 .sisyphus/plans/modular-restructure.md 与 a2-plan-mining-a2-specs.md"——**证据文件权威版 = a2-plan-mining-\*（25/23/21KB 完整版）；jia-mining-\*（13/10KB）为中断残版仅留档**）
  - B1 重定义提案（docs/plans/ 短文档）：验收对象改甲的模块化产物（故事型全流程+主模组文字版闭环）
  - PROJECT_STATE 更新
  **Agent**: writing | **Skills**: []
  **Commit**: `docs(governance): D14 modular restructure ruling + spec v1.3 + A2 archival headers + B1 redefinition proposal`
  **Acceptance**: D14 含三裁决逐字+翻车证据引用+三红线显式翻案记录（门禁子集/tier 扩展/契约升版）；spec v1.3 含 §0 变更记录+§5.2 配方化重述+§8 重锚；A2 两规格归档头存在且指向甲计划；B1 提案留档
  **Acceptance**: D14 含甲三裁决逐字+三红线翻案记录（门禁语义[DN1 结果]/tier 契约[DN2 结果]/枚举扩展）+D12/D13 处置；spec v1.3 §0 有变更记录且 §5.2 配方化重述；两 A2 规格头部有归档注记；B1 提案落盘 docs/plans/

- [ ] 8. FINAL 四审（同 E1-Lite 惯例）

  - [ ] F1 计划合规审计 [ultrabrain]：Must Have/Nought 全核对+证据齐全
  - [ ] F2 代码质量审查 [unspecified-high]：三命令+反模式+slop+回归铁律复核
  - [ ] F3 真实手动 QA [unspecified-high]：**翻车场景全流程重放必须翻绿**（plot 用户：首问故事/偏转被尊重/细节入素材槽/建议贴故事）+ 设定型回归 + 主模组开团文档人审
  - [ ] F4 范围忠实检查 [deep]：甲裁决 1:1、A2 材料只进不出阶段叙事、E2/E3 无遗漏、无蔓延

---

## Commit Strategy
- M0: `fix(a1): deflect-to-skip placeholder advance + story-detail-to-sketch archive + story-aware suggestions (M0 stopgap)`
- M1: `feat(modular): module registry + recipe-parameterized question tree + subset gate semantics (M1 core)`
- M2: `feat(modular): story module family + 4 story-type recipes (M2)`
- M3: `feat(modular): A2 asset salvage as output modules - main-module doc/dice/character projectors (M3)`
- M4a/b/c、G：见各任务
- 提交纪律：原子提交、每任务独立、不混无关文件、分支 v2-modular

---

## Success Criteria

### Verification Commands
```bash
cd backend && python -m pytest tests/unit -q -p no:cacheprovider --no-cov --ignore=tests/unit/a1/test_a1_warning_ledger.py   # 837+ 全绿（4 preexisting 除外）
cd frontend && npx tsc --noEmit && npx vitest run   # 0 errors / 231+ 全绿
```

### Final Checklist
- [ ] 甲三裁决 1:1 兑现（模块化/材料并入/计划合并重梳）
- [ ] 翻车记录四场景重放全绿（F3 灵魂项）
- [ ] 设定型行为逐字节回归
- [ ] 三铁律/护栏/R2/R6 重述后全部存活
- [ ] 治理四件落地
- [ ] DECISION NEEDED 1-6 呈交产品方（默认值生效不阻塞）
- [ ] 全部证据归档 `.sisyphus/evidence/`

### DECISION NEEDED（呈交产品方，均有安全默认值）
1. **门禁子集语义**：配方外模块 = 不适用（默认，missing_sections 只列配方内）vs 未答（保守）——影响 finalize 契约
2. **tier 闭集扩展**：故事模块复用既有 tier 映射（默认——初稿：剧情主线→历史时间线同层、角色速写→文明与社会同层、情感线→IP定位同层，影响图谱层级展示，终审确认）vs 新增 tier 值（C5 契约修订）；注意"复用映射"仍需 TIER_MAP 加键（10→16），tier_map 头注"Do not add an 11th module tier"的翻案记录入 D14
3. **故事模块字段集**：剧情主线/角色速写/情感线的字段清单与问题文案终审（计划内为初稿）
4. **A2 冲突回收裁决**：ScopeBoundary max_party_size 4 vs 6 / 端点 module-text vs doc / M 重定稿 v+1 vs 开新文件 / W-S 编码语义重定义——**已裁决（2026-09-24，D15）**：max_party_size=6；doc（界面「文档输出」）；同 file α-β 版本递进（α0.1→0.11/0.12→定稿转β→0.21…→1.0，全产物统一）；W=世界图/M=模组图族（含 TD/TC/R）/S=场景图（联邦三图谱，不停发）
5. **新 LLM 生产方总清单**（Momus 修订：DN5 扩展）：开场叙事端点 + M3 module_compile 增强线——统一走三铁律"单生产单消费"契约评审立项，逐个留痕
6. **故事配方的世界建构子集与序**（Momus F4a 修订，新增）：plot/romance/unsure/character_driven 各配方保留哪些世界建构模块、序如何（初稿按 §5.2 前移序推导，产品终审定死）+ 故事型×上传链组合语义（默认：上传链仅 default/怀旧路径暴露，故事型走访谈）
