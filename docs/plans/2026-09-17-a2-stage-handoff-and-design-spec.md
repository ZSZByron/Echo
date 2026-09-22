# A1→A2 阶段交接与 A2 前后端设计规格 v0.1

> **日期**: 2026-09-17
> **性质**: 阶段交接规格书（A1 总结 + A1→A2 交接契约 + A2 前后端设计 + 架构一致性检查 + 断点提取）
> **输入权威**: [[PROJECT_STATE]] · [[2-A1-v0.5-内容图谱化统一模型与契约]] · [[2-A1-v0.5.1-管线缺陷级联与修复接头J1-J4]] · [[2_product-architecture]] §3 · [[mvp-requirements-and-flows]] · .sisyphus/plans/A1-v0.5-A模块公用模块与A模块设计.md Task 10 · [[decision-log]]（D1-D11/B1-B6/P1-P3）· [[2-A2-v0.2-产品策划顾问+模组合成]]（愿景参考）· [[2-A-认知边界与信息框架总纲]] §1
> **地位**: plans 层规格书。⚠️ 实施前置闸门：D9（tsc 16 + 存量测试清零，≤1 天）+ ⛔产能未答——**本计划可排期，未获指令不可启动实施**。
> **治理建议**: 本文档定稿后，将三代 A2 文档矛盾收编升版 `docs/governance/2-A2-v0.3-*.md`（治理规则：新版本顺延号新建文件）。

---

## 0. 三代 A2 文档矛盾收编（本规格的仲裁立场）

A2 存在三代设计文档，存在实质冲突，本规格按以下立场收编：

| 代际 | 文档 | 契约形态 | 裁定 |
|------|------|---------|------|
| 第一代（08-05） | 2-A2-v0.2 愿景稿 | `world_package.json` / `main_module.json` 文件契约；`/api/planning/*` 端点；引用 DimensionResultSet（**已删除**） | ❌ 契约作废；**产品理念承袭**（制片人定位/四阶段/RAG 案例推理/骰子五链/4 相位） |
| 第二代（08-19） | 2_product-architecture §3 + mvp-flows + Task 10 | **图谱中心制**：`/api/a2/*` 双路径架构；产出=主模组图谱 IPxxxx-M1-v1；A2'/A2'' 文件为图谱单向导出 | ✅ **架构骨架现行权威** |
| 第三代（09-17） | decision-log B6/D3/D4 | v0 基线范围裁剪：A2=**主模组文字版**（9.26 截止）；机械码延期（B4） | ✅ **范围裁决现行权威** |

**收编结论**：架构按第二代（双路径、图谱中心、Task 10 API 契约），范围按第三代分三段交付（见 §3.1），产品理念按第一代承袭（骰子五链/4 相位/案例推理进入 v0.5/v1）。

---

## 1. A1 阶段总结

### 1.1 功能交付（用户可感知的完整链路）

```
入口三选一（种子预设/文档上传.txt/一句话）
  → 引导访谈（10 模块 35 字段顺序推进，LLM 追问+fills 自动填空+写保护+防卡死+发散引导）
  → 定稿门禁（模块过半真值化计数，未达标 409 + missing_sections）
  → graphify（单次 LLM 调用 → SIR 五字段结构化中间表示）
  → 确定性编译（双树 + 派生边 + 约束节点，纯代码装配零 LLM）
  → 产出三件：知识图谱页（tier 分组/搜索/边审核/重定稿版本化）
              IP 展板（氛围图 + 设定浮层）
              视觉背景（A+B 双触发预生成）
```

- **API**：16 端点（`/api/a1/*`），409 门禁契约贯穿（未定稿访问 graph/poster → 409）
- **前端**：`/a1`（A1Workspace 三态：种子选择/引导访谈/产出）+ `/a1/poster`（IPPoster）+ graph_view 双 Tab（图谱/展板）
- **可观测**：warning ledger 五源披露（upload/convert/graphify/answers/直注），前端角标展示

### 1.2 架构遗产（A2 必须继承的六条模式）

| # | 模式 | A1 落地 | A2 对偶要求 |
|---|------|--------|------------|
| 1 | **三数据形态铁律** | NL（访谈）→ SIR（graphify 五字段）→ KG（确定性编译），单生产单消费 | A2 对偶：NL（路径A决策对话）→ SIR'（A2' 决策文件）→ KG（M/TD/TC 图谱投影） |
| 2 | **图谱装配确定性** | LLM 只在 graphify 单点产出结构，图谱由代码装配，同输入可复现 | 投影器④⑤=确定性查询引擎**零 LLM**；finalize 免费线=确定性组装 |
| 3 | **诚实与可观测** | J1 真值闸 / J3 warning ledger / J4 三级预算护栏+留痕 | A2 全产物挂 ledger（source 扩充）；上游 stale/投影缺料全披露不静默 |
| 4 | **版本化血缘** | graph_code `IPxxxx-W{n}-v{n}` 永不覆盖只追加；重定稿→下游 stale 横切（只标记不删除） | M/TD/TC 同码制（StageCode 已预留）；A1 重定稿→A2 产物 stale |
| 5 | **409 门禁契约** | finalize 未达标 409+missing_sections；graph/poster 未定稿 409 | A2 finalize 缺上游/缺依赖（如缺骰子模板）→ 409+结构化 detail |
| 6 | **测试文化** | pytest 1020/1020；C1-C5 契约测试；xt 极限病理系列 | A2 每阶段配契约测试 + 病理用例（免费线零 LLM 可跑 = 测试天然确定性） |

### 1.3 质量基线与已知债务（交接时的诚实快照）

- **绿**：pytest 1020/1020；vitest 185 passed；后端 1000+ 测试基线为合入门槛
- **存量债**（A2 启动前须知，非 A2 范围）：
  - tsc 16 基线错误（D9 闸门清零目标，≤1 天时间盒）
  - vitest 6 存量失败（useTypewriter）+ 1 收集错误（e2e spec 被 vitest 收集）
  - J2 未做（id 不变量，需 v0.6 设计评审——影响 A2 图谱 id 稳定性预期）
  - parse_modules 值级方差（同文档两次上传 32↔35 字段漂移；占位半边已治，值级方差归 J2/J3）
  - 平台缺口：全 store 无用户隔离（A1 store 自述单机假设）、identity 路由接 MockUserStore

### 1.4 A1 边界止步处 = A2 职责起点

依据认知边界总纲 §1.2 与拓扑边界矩阵：

| A1 止步 | A2 接管 |
|---------|--------|
| 地理只到骨架（"地点以下"） | 区域内**分区**（沿 GEO_CONTAINS 型 TREE 下挂追加） |
| 剧情只锁主线骨架 | **平行剧情**（下挂追加，不可改主线链） |
| 5 类骨架实体创建后不可变 | A2 **只可追加不可回改** A1 字段与结构边 |
| 骰子设定只收 4 字段 NL 答案 | **骰子模板**（结构化投影 + 数值边界） |
| 设定边界（immutable_core/ai_fill）只收声明 | **scope_boundary**（A3 不可超越的模组契约） |
| — | **Culture 节点**（A2 独有产出）+ MODULE 级约束 |

---

## 2. A1→A2 交接数据结构（契约冻结）

> 本章是 A2 的**唯一上游契约**。字段定义以当前代码为准（非任何旧文档）；A2 不得假设旧世界包（WorldPackage/DimensionResultSet，已删除）。

### 2.1 交接物五件套

#### 件一：定稿知识图谱（核心交接物）

`GET /api/a1/file/{file_id}/graph` → `graph_json`（KnowledgeGraph.model_dump(mode="json")，未定稿 409）

```python
# backend/app/models/knowledge_graph.py（现行，字段逐字）
class KnowledgeGraph(BaseModel):
    scene_id: str                              # = A1 session_id
    nodes: dict[str, GraphNode]                # id → node
    edges: list[GraphEdge]
    background_node_id: str | None             # 背景树根

class GraphNode(BaseModel):
    id: str                # 三种形态：
                           #   模块节点   = module_id（如 "力量体系"）
                           #   条目节点   = "{module_id}.{subfield_id}"（与 answers key 同构）
                           #              + 深度树条目 = "d:{anchor}:{title}"（title 经 sanitize，≤32字）
                           #   约束节点   = "cst_*"
    serial_number: str     # 层级序号（背景树 0/N/N-M 制；level = 段数+1）
    level: int             # 层级：约束 L0 → 背景 L1 → 模块 L2 → 条目 L3
    description: str       # 节点正文（条目=content，模块=summary）
    status: str            # pending/generating/completed/failed（资产管线遗留，A2 只读）
    tier: int | None       # 0-6 七层语义（L0 存在基座→L6 治理层；tier≠level）

class GraphEdge(BaseModel):
    from_node_id: str
    to_node_id: str
    edge_type: str         # TREE（层级）/ CROSS（交叉引用）/ SEMANTIC（LLM 概念边，需确认）
                           # / RULE（确认后规则边）/ STRUCTURE（解析扩展边）
    visual_description: str
    relation: str          # 概念边关系名（词表内中文，TREE/CROSS 为空）
    confidence: str        # "rule"/"semantic"/"structure"/""
    confirmed: bool        # TREE/CROSS 恒 True；概念边待审核
```

**A2 消费规则**：
- 确定性投影（④⑤）只读 `tier`/`level`/TREE 边 + 条目正文——**不依赖 SEMANTIC 概念边**（其确认状态不稳定，属增强信号非依赖信号）
- cst_* 约束节点是骰子投影的约束源；**稀疏性风险**见 §8-R2

#### 件二：A1 答案真值（35 字段 NL）

`A1Session.answers: dict[str, str]`，key = `{module_id}.{subfield_id}`，value = 用户确认的 NL 真值（J1 真值闸保证无占位词污染）。

**10 模块清单**（a1_question_tree.py 为权威，A2 信号源映射的基准）：

| 模块 id | 子字段（A2 消费视角标注 ★=投影器直接信号） |
|---------|------------------------------------------|
| IP定位 | name / concept / world_type / core_experience |
| 世界本体 | origin / existence / **reality_rule ★**（骰子核心判定信号） |
| 力量体系 | source / acquire / mechanism / **cost ★**（骰子第 5 链「代价机制」） |
| 地理空间 | terrain / vertical / special_geo（分区选择的母体） |
| 文明与社会 | core_value / **conflict ★**（主冲突候选）/ faction_type ★（主势力候选）/ economy |
| 历史时间线 | time_span / key_nodes / **main_plot ★**（时代选择 + 平行剧情母体） |
| 视觉设计 | keywords / architecture / material（展板信号） |
| 玩法设计DNA | **player_role ★ / main_action ★ / growth ★**（等级系统+角色相位排序信号）/ growth_end |
| 骰子设定 | **probability ★ / dice_count ★ / check_mode ★ / success_check ★**（骰子五链之四） |
| 设定边界 | **immutable_core ★ / ai_fill ★**（scope_boundary 的 A1 声明源） |

#### 件三：图谱血缘记录（版本链）

- `graph_code`：`IP{序号}-W{实例}-v{版本}`（GraphCodeIssuer 发号，永不覆盖只追加）
- 注册表：SQLite（`data/assets/ugc.db`），`GET /api/graphs?user_id=` → 按 IP 分组清单，含 `status(finalized/stale)`/`change_set`/`parent_graph_code`
- **stale 语义**（A2 必须遵守）：A1 重定稿 → 下游 A2 图谱被标记 stale；**不阻断不删除**，消费 stale 须留痕 `used_stale=true`

#### 件四：警告账本 + 开放问题

- `file_rec["warnings"]: list[LedgerEntry]`（source/detail/count/level；五源：upload/convert/graphify/answers/直注）
- `file_rec["open_questions"]: list[OpenQuestionLog]`（C6 结构化，禁裸 list[str]；answered 条目已作证据回流 graphify）
- **A2 消费规则**：上游 ledger 非空 ≠ 阻断，但 A2 产物 ledger 须**透传继承**（上游降级可见性不断链）；open_questions 中未答条目是 A2 决策对话的天然议题池（路径A）

#### 件五：底座服务（A2 直接复用，零新建）

| 服务 | 位置 | A2 用法 |
|------|------|--------|
| GraphCodeIssuer | domains/creation/shared/graph_code_issuer.py | **StageCode 封闭枚举已预留 `M`(主模组)/`TD`(骰子模板)/`TC`(角色模板)/`R`(报告)**——A2 发号零改动 |
| stale_marker | domains/creation/shared/stale_marker.py | A1 重定稿→mark_downstream_stale 自动覆盖 A2 产物；A2 finalize 也须注册图谱进注册表 |
| StructuredFileStore | state/structured_file_store.py | A2'/A2'' 文件 = 图谱**单向导出**快照（禁止反向回写图谱） |
| warning_ledger | domains/creation/a1/warning_ledger.py | source 枚举扩充 `a2_project`/`a2_finalize`（additive） |
| provider 层 | ai/provider.py | 仅路径A analyze 与增强线 compose 使用（免费线零调用） |
| identity | domains/identity/ + api/identity_routes.py | user_id 沿用（平台缺口见 §8-R5，A2 记录 user_id 字段但不接账号） |

### 2.2 信号源映射表（A1 → A2 消费者 → 产物字段）

| A1 信号 | A2 消费者 | 产物字段 | 缺料降级 |
|---------|----------|---------|---------|
| 骰子设定.probability/dice_count/check_mode/success_check | dice_projector④ | DiceTemplate.dice_core/dice_source/success_criteria 首选值 | 全缺 → 按 reality_rule 推导默认骰型 + ledger 披露 `dice_defaults_used` |
| 世界本体.reality_rule（物质/意志主导） | dice_projector④ | dice_core 类型判定（物质→数值骰；意志→骰池/百分比） | 缺 → 默认 d20_modifier + 披露 |
| 力量体系.cost | dice_projector④ | 骰子第 5 链「代价机制」文案 | 缺 → 留空字段 + open_question |
| 玩法设计DNA.growth（quantitative/qualitative 偏好） | dice_projector④ Step2 | growth_system（槽位/位阶/混合）判定信号 1 | 缺 → 走 Step2b 元素比例分析（对 A1 图谱条目做词法统计，仍零 LLM） |
| 玩法设计DNA.player_role/main_action | character_projector⑤ | 相位排序（4 步判别法）+ 情境阻力难度倾向 | 缺 → 默认排序 + 披露 |
| 设定边界.immutable_core/ai_fill | module_finalizer③ | scope_boundary.core_factions_unmodifiable + 生成边界声明 | 缺 → 空 scope + 披露 |
| 地理空间（图谱 L2/L3 地理子树） | module_finalizer③ | selected_regions + 分区母体 | 缺 → 全域 + 披露 |
| 历史时间线.main_plot/key_nodes | module_finalizer③ | selected_eras + 平行剧情挂点 | 缺 → 全时代 + 披露 |
| 文明与社会.conflict/faction_type | module_finalizer③ | main_conflict/main_faction 候选 | 缺 → LLM 增强线提议 / 免费线留空 |
| IP定位.name/core_experience | module_poster + 文字版 | 模组名（`{name}：主模组`）+ 核心幻想句 | — |
| 图谱 cst_* 约束节点 | dice_projector④ | 数值边界钳制（stat_floor/ceiling 校验） | 稀疏 → 边界取保守缺省 + 披露（R2） |

### 2.3 交接不变量（A2 六条铁律，违反=架构违规）

1. **只读消费**：A2 不可修改 A1 图谱任何节点/边/answers（上游仅 GET）
2. **图谱=事实源**：A2'/A2'' 文件是单向序列化导出，反向写文件不回写图谱
3. **只追加**：A2 产物编码 v+1 追加，永不覆盖；下游 stale 只标记不删除
4. **不可越界**：A2 不生成世界级细节（A3 边界：场景/资产具象素材）；不新建 A1 结构边，只沿 TREE 下挂追加
5. **骰不违宪**：骰子模板不可违背 A1 骰子设定与 cst_* 约束（A1 声明优先于一切推导）
6. **stale 不阻断但留痕**：消费 stale 上游必须记录 used_stale，前端展示徽章

---

## 3. A2 总体架构

### 3.1 范围裁决（B6 收敛 → 三段交付）

遵 D4（先完成基线）+ B6（v0=A2 主模组文字版）+ D2-③（AI 提案永不阻塞主路径）：

| 段 | 范围 | LLM 依赖 | 交付物 | 时机 |
|----|------|---------|--------|------|
| **A2-v0（基线）** | 免费线精简：选 A1 图谱 → 主模组 finalize（确定性）→ **主模组文字版**（Markdown/JSON 导出，B5） | **零 LLM** | 主模组图谱 M + 主模组文字版 | 9.26 基线前 |
| **A2-v0.5** | +骰子投影④（TD）+ 角色投影⑤（TC）+ 展板组 | 零 LLM（投影器确定性） | DiceTemplate/CharacterTemplate + 骰子/角色展板 | 基线后 |
| **A2-v1** | +路径A 策划线（analyze/decide/report，R）+ RAG 案例库 | 2 次/分析 | ProductPlan/策划报告（免费完整实现） | v0.5 后 |
| 延期 | 机械码（B4，随导出规格设计）、账号云端（D8）、策划报告存档、多端 | — | — | — |

> v0 的"免费线零 LLM"不是妥协而是架构红利：投影/组装全确定性 → 基线交付无 API key 依赖、测试天然可复现、外测链路最短（D7）。

### 3.2 双路径架构（现行权威，Task 10 契约）

```
厂家进入 /a2
  ↓
① GraphSelector 选 A1 图谱（默认最新已定稿；stale 徽章+变更集+二次确认）
  ↓
② 路径选择 ⭐
  ├─ 路径A 完整策划线（增强）[v1]
  │    POST /api/a2/analyze（特征+类型推荐+风险）→ 多轮决策对话
  │    → POST /api/a2/decide（A2' 文件）→ GET /api/a2/report
  ├─ 路径B TRPG 默认线 ⚡ [v0 核心]
  │    （v0：直接 finalize；v0.5：骰子投影④ → 角色投影⑤ → finalize）
  ↓
③ 汇合 POST /api/a2/file/{id}/finalize
  ↓ 产出：主模组图谱 IPxxxx-M{n}-v1（+ 展板组 + 提示词组 [v0.5]）
  ↓        + 主模组文字版 doc.md / doc.json [v0 新增，B6/B5]
  ↓
④ /a2/boards 展板组（tab：主模组 [v0] + 骰子/角色 [v0.5]）→ 进入 A3 或返回
```

### 3.3 NL/SIR/KG 对偶（架构一致性的核心表述）

| 轴 | A1 | A2 |
|----|----|----|
| NL（人机对话层） | 引导访谈对话 | 路径A 决策对话（v1；v0 无 NL） |
| SIR（结构化中间表示） | graphify 五字段 | A2' 决策文件（decisions 结构体）/ 投影参数 |
| KG（确定性产物） | W 图谱（双树） | TD/TC 图谱（模板投影）+ M 图谱（主模组） |
| LLM 位置 | 仅 graphify 单点 | 仅 analyze + 增强线 compose（投影与免费线 finalize 零 LLM） |
| 文件 | 结构化文件=图谱导出 | A2'/A2''=图谱导出（同构） |

**A1 教训的制度化**：parse_modules 值级方差（32↔35 漂移）证明"LLM 产结构"必带不确定性——A2 因此把一切可推导结构交给确定性投影器，LLM 只产出**建议与文案**（决策对话/推荐理由），永不产出**结构与数值**。

---

## 4. 后端详细设计

### 4.1 领域层布局（仿 A1 域模式）

```
backend/app/domains/creation/a2/
├── __init__.py
├── models.py              # 全部 A2 Pydantic 模型（域内自治，仿 graphify.py 模式）
├── store.py               # A2FileStore（JSON + .bak 轮转，仿 A1 store J4 模式；记录带 user_id）
├── upstream_loader.py     # A1 图谱/答案/血缘只读装载 + stale 检查（铁律 1/6 执行点）
├── dice_projector.py      # ④ 确定性骰子投影 [v0.5]
├── character_projector.py # ⑤ 确定性角色投影 [v0.5]
├── module_finalizer.py    # ③ 汇合：免费线确定性组装 / 增强线合并 decisions [v0]
├── module_doc.py          # 主模组文字版渲染器（Markdown + JSON 双格式）[v0，B6/B5]
├── module_poster.py       # 主模组展板数据 [v0 最简 / v0.5 完整]
├── planning_analyzer.py   # 路径A 策划分析 + 多轮决策循环 [v1]
├── case_retriever.py      # RAG JSON 案例检索（零向量库）[v1]
└── report_generator.py    # 策划报告 [v1]
```

### 4.2 数据模型（Pydantic v2，逐字段冻结）

> 存放域内 `models.py`（A1 先例：GraphifyResult 在 graphify.py 域内），不进 app/models/（该处仅放跨域共享如图谱 schema）。枚举注释铁律："不允许添加或修改"。

```python
# ============ 主模组范围边界（结构化，替代旧版 dict） ============
class ScopeBoundary(BaseModel):
    """A3 不可超越的模组契约。A2 定稿产物，沿血缘向下游传递。"""
    allowed_regions: list[str] = Field(default_factory=list)   # 允许的区域（A1 地理子树 id 集）
    allowed_eras: list[str] = Field(default_factory=list)      # 允许的时代（A1 历史节点 id 集）
    max_power_level: int | None = None                          # 力量层级上限（骰子等级钳制）
    core_factions_unmodifiable: list[str] = Field(default_factory=list)  # 不可改写的核心势力
    max_party_size: int = 6                                     # 队伍上限（TRPG 惯例缺省 6）
    content_density: str = "standard"                           # 内容密度：sparse/standard/dense
    source: str = "default"                                     # default(免费线缺省)/planning(路径A决策)

# ============ 路径A 决策（A2' 文件 payload）[v1，v0 预留字段] ============
class A2Decisions(BaseModel):
    """POST /api/a2/decide 落定；免费线为 None。"""
    selected_eras: list[str] = Field(default_factory=list)
    selected_regions: list[str] = Field(default_factory=list)
    main_faction: str = ""
    main_conflict: str = ""
    gameplay_focus: str = ""            # GameGenre 名单内（八枚举，v1 冻结）
    module_fantasy: str = ""            # 模组核心幻想一句话
    free_path: str = "TRPG"             # 落定后默认走 TRPG 免费标注
    decided_at: str = ""                # ISO 时间戳

# ============ 骰子模板（④ 投影产物，承袭 2-A2-v0.2 §6.4 修订） ============
class DiceCoreType(str, Enum):
    """骰子核心类型。不允许添加或修改。"""
    D20_MODIFIER = "d20_modifier"   # 数值骰（物质主导）
    DICE_POOL = "dice_pool"         # 骰池计数（意志主导）
    PERCENTAGE = "percentage"       # 百分比对冲（意志主导）

class GrowthSystem(str, Enum):
    """等级系统。不允许添加或修改。"""
    SLOT = "slot"; TIER = "tier"; HYBRID = "hybrid"

class DifficultySystem(str, Enum):
    """难度系统。不允许添加或修改。"""
    COUNTER_VALUE = "counter_value"; CONTEXTUAL = "contextual"; HYBRID = "hybrid"

class DifficultyTier(BaseModel):
    label: str            # 日常/简单/标准/困难/极限
    modifier: int         # 挑战系数（对抗数值用）
    gradient: int         # 情境梯度 1-5（情境阻力用）
    description: str      # GM 参考说明

class DiceTemplate(BaseModel):
    """TD 图谱投影产物。全部字段由确定性规则从 A1 图谱+答案推导，零 LLM。"""
    graph_code: str                        # IPxxxx-TD{n}-v{n}（发号器产出）
    upstream_graph_code: str               # 消费的 A1 W 图谱码
    used_stale: bool = False               # 消费 stale 上游留痕（铁律 6）
    # 骰子五链
    dice_core: DiceCoreType
    dice_source: str                       # 骰子来源描述
    check_mode: str                        # 判定方式（直投 A1 骰子设定.check_mode）
    success_check: str                     # 成功判定（直投 A1 success_check）
    cost_mechanism: str = ""               # 代价机制（源：力量体系.cost）
    # 等级系统
    growth_system: GrowthSystem
    level_cap: int | None = None           # 槽位制上限（默认 10）
    tier_labels: list[str] = Field(default_factory=list)   # 位阶名（默认 ["凡人","精英","英雄","传奇","神话"]）
    modifier_range: tuple[int, int] | None = None           # 位阶修正钳制（默认 (-2, 5)）
    # 难度系统
    difficulty_system: DifficultySystem
    difficulty_table: list[DifficultyTier] # 五档对照表（GM 直查）
    # 数值边界（cst_* 约束钳制；稀疏时保守缺省+披露）
    stat_floor: int = 10
    stat_ceiling: int = 20
    # 溯源与披露
    signal_sources: dict[str, str]         # 字段→信号来源（"a1:骰子设定.probability" / "rule:reality_dominant" / "default"）
    warnings: list[str] = Field(default_factory=list)  # 降级/缺料披露（dice_defaults_used 等）

# ============ 角色模板（⑤ 投影产物，承袭 2-A2-v0.2 §7.7 修订） ============
class TemplatePhase(str, Enum):
    """角色模板 4 相位。不允许添加或修改。"""
    NARRATIVE = "narrative"    # 叙事相位（锚点拓扑）
    MECHANISM = "mechanism"    # 机制相位（流程拓扑）
    RESOURCE = "resource"      # 资源相位（交换拓扑）
    DIRECTION = "direction"    # 定向相位（层级拓扑）

class PhaseContent(BaseModel):
    phase: TemplatePhase
    priority: int              # 排序优先级 1-4
    is_core: bool              # 核心 2 相（定调结果）
    constants: list[str]       # 厂家常量（硬规则/经济闭环/终极边界——从 A1 设定边界/约束投影）
    variables: list[str]       # 玩家变量（组合/叙事/路径自由度）
    anchors: list[str]         # 留白锚点（"你有一个死敌，自己填是谁"）

class CharacterTemplate(BaseModel):
    """TC 图谱投影产物。依赖 DiceTemplate（缺 → 409 dice_required）。"""
    graph_code: str                          # IPxxxx-TC{n}-v{n}
    upstream_graph_code: str
    dice_template_code: str                  # 依赖的 TD 码
    used_stale: bool = False
    core_phases: list[TemplatePhase]         # 核心 2 相（reality_dominant + main_action 判定）
    secondary_phases: list[TemplatePhase]
    phases: dict[TemplatePhase, PhaseContent]
    conflict_point: str = ""                 # 玩家动机 × 世界哲学（源：core_experience × conflict）
    flavor_concentration: str = ""           # 风味浓度声明
    signal_sources: dict[str, str]
    warnings: list[str]

# ============ 主模组（③ 汇合产物） ============
class MainModulePayload(BaseModel):
    """M 图谱 payload：节点/边沿用 KnowledgeGraph schema（同构 A1），
    另携带模组元数据。图谱部分= A1 子图筛选 + A2 追加节点。"""
    graph: KnowledgeGraph                    # M 图谱（schema 与 A1 完全同构）
    graph_code: str                          # IPxxxx-M{n}-v{n}
    upstream_graph_code: str
    used_stale: bool = False
    decisions: A2Decisions | None = None     # 路径A 落定（免费线 None）
    scope_boundary: ScopeBoundary
    dice_template_code: str | None = None    # v0.5 起填充
    character_template_code: str | None = None
    prompt_group: list[str] = Field(default_factory=list)  # 提示词组 [v0.5]
    warnings: list[str]

# ============ 主模组文字版（B6 v0 核心交付物） ============
class ModuleDocSection(BaseModel):
    heading: str            # 章节标题
    level: int              # Markdown 标题层级
    body: str = ""          # 正文（NL）
    children: list["ModuleDocSection"] = Field(default_factory=list)

class ModuleDocument(BaseModel):
    """主模组文字版——「产出零加工可用」(D2-①) 的直接载体。
    Markdown 给人（GM/玩家），JSON 给机器（A3/导出）。"""
    title: str                         # "{IP name}：主模组"
    module_fantasy: str                # 一句话核心幻想
    sections: list[ModuleDocSection]   # 结构化章节树
    scope_boundary: ScopeBoundary      # 内嵌契约（机器读）
    graph_code: str                    # 溯源
    generated_at: str
    # 章节树（v0 冻结九节）：
    # ①模组概述 ②世界背景摘要(源:A1 module_summaries) ③舞台：区域与分区
    # ④时代与主线 ⑤平行剧情挂点 ⑥势力与冲突 ⑦骰子规则(源:A1 骰子设定直投/v0.5 TD 投影)
    # ⑧角色创建指南(v0:A1 player_role/growth 摘要；v0.5:TC 投影) ⑨GM 边界须知(scope_boundary 人话版)
```

#### A2 文件记录（store 持久化形态）

```python
class A2FileRecord(TypedDict):
    file_id: str
    user_id: str                 # D8 过渡期仍记录（平台接线预留）
    upstream_graph_code: str     # 绑定的 A1 W 图谱码（进入工作台时选定）
    upstream_graph_id: str
    status: str                  # draft / finalized
    used_stale: bool
    decisions: dict | None       # A2'（路径A 落定后）
    decisions_file_id: str | ""  # A2' StructuredFile 导出 id
    dice_template: dict | None   # TD 投影结果
    character_template: dict | None
    module_payload: dict | None  # M 图谱 payload（finalized 后）
    module_doc_md: str           # 文字版 Markdown 缓存
    module_doc_json: dict
    warnings: list[dict]         # ledger（source 扩充 a2_*）
    created_at: str
```

### 4.3 API 契约（Task 10 契约 + B6 增量）

新增路由文件 `backend/app/api/a2_routes.py`；全部 `/api/a2/*` 前缀。

| # | 端点 | 方法 | 请求→响应 | 段位 | 错误契约 |
|---|------|------|----------|------|---------|
| 1 | `/api/a2/session/start` | POST | `{user_id, upstream_graph_id?}`→`{a2_file_id, upstream:{graph_code,status,stale?,change_set?}, defaults:{scope_boundary}}`（未传 upstream 则默认最新已定稿；stale 附变更集） | **v0** | 404 无可用 A1 图谱 |
| 2 | `/api/a2/file/{id}` | GET | →A2FileRecord 视图（含 TD/TC/M 状态） | **v0** | 404 |
| 3 | `/api/a2/file/{id}/finalize` | POST | `{decisions?: dict}`→`{module_graph_code, module_graph_id, doc_md, doc_json, warnings, ledger}`（免费线零 LLM；带 decisions=增强线） | **v0** | **409** `upstream_missing`/`upstream_not_finalized`；已 finalized→409 `re_finalize_required_new_file`（v0 简化：M 不重定稿，改上游就开新 A2 文件） |
| 4 | `/api/a2/file/{id}/doc` | GET | `?format=md\|json`→文字版（B5 导出） | **v0** | 409 pending_finalize |
| 5 | `/api/a2/file/{id}/dice-template` | POST | `{}`→DiceTemplate（TD 发号+注册表登记+stale 挂钩） | v0.5 | 409 upstream 缺；重复生成→新 v+1 不覆盖 |
| 6 | `/api/a2/file/{id}/character-template` | POST | `{}`→CharacterTemplate | v0.5 | **409 `dice_required`**（Task 10 TDD 要点：缺骰子模板→409） |
| 7 | `/api/a2/analyze` | POST | `{user_id, a2_file_id}`→`{session_id, analysis, questions}` | v1 | 409 upstream 问题 |
| 8 | `/api/a2/decide` | POST | `{session_id, decisions}`→`{a2_prime_file_id}` | v1 | — |
| 9 | `/api/a2/report` | GET | `?session_id=`→PlanningReport（免费完整实现） | v1 | — |

**main.py 注册 + 图谱注册表联动**：finalize/④/⑤ 产物全部 `stale_marker.register_graph(...)` 入册（stage=M/TD/TC），A1 重定稿自动 stale 横切。

### 4.4 确定性投影器设计

**dice_projector④（四步，全规则零 LLM）**：

```
Step1 骰子核心：骰子设定 4 字段已填？
  ├─ 已填 → 直接映射（check_mode/success_check/dice_count 直投；probability→dice_core）
  └─ 缺 → reality_rule 判定（物质主导→d20_modifier；意志→dice_pool/percentage 按 probability 措辞）
          全缺 → d20_modifier 缺省；ledger 披露 dice_defaults_used
Step2 等级系统：growth 字段 quantitative/qualitative 偏好 → slot/tier/hybrid
  缺 → 对图谱条目做累积型/跃迁型词法计数（零 LLM）→ 70% 阈值判定（承袭 2-A2 §6.3.2 比例法）
Step3 难度系统：等级系统联动（slot→counter_value 五档 DC 表；tier→contextual 五梯度；hybrid→双轨）
Step4 边界钳制：cst_* 约束节点存在 → 钳 stat_floor/ceiling/level_cap；稀疏 → 保守缺省+披露
输出：signal_sources 全字段溯源 + warnings 降级披露
```

**character_projector⑤（四步判别排序，承袭 2-A2 §7.4）**：
1. reality_dominant 定调（核心 2 相选择）
2. main_action/player_role 相位命中
3. 常量/变量分配：A1 设定边界.immutable_core → constants；ai_fill 声明域 → variables；open_questions 未答项 → anchors 候选
4. DiceTemplate 数值注入机制相位

**module_finalizer③（免费线确定性）**：
- 图谱装配：A1 图谱按 scope（全缺省=全域）取子图（地理/历史/势力/冲突子树）→ 克隆为 M 图谱基底 → 追加节点：模组根（cst_module_*：MODULE 级约束=scope_boundary 展开为约束节点）+ 分区占位（地理子树下挂，v0 只建骨架占位不填充）+ 平行剧情挂点（main_plot 下挂空锚点）
- 文字版渲染：module_doc.py 将 payload 渲染为九节 Markdown/JSON（章节树见 4.2）

### 4.5 警戒线复用（J3 模式延伸）

`warning_ledger.LedgerEntry.source` 枚举扩充：`a2_project`（投影缺料/降级）+ `a2_finalize`（组装截断/子图空）。上游 ledger 透传规则：A1 图谱的 warn 级条目以 `upstream:` 前缀并入 A2 产物 ledger（可观测性不断链）。

### 4.6 测试策略

- **契约测试**（仿 C1-C5）：TD/TC/M 发号格式断言；免费线 finalize 零 provider 注入可跑（FakeProvider=None）；409 契约（dice_required/upstream_missing）；doc 格式断言（九节结构+scope 内嵌）
- **病理测试**（仿 xt）：上游全空字段/仅 1 模块定稿/stale 消费留痕/ cst 全缺骰子缺省/文档 20000 字答案的 M 图谱子图规模
- 基线：pytest 全量保持 1020+ 全绿零回归

---

## 5. 前端详细设计

### 5.1 路由与页面

| 路由 | 页面 | 段位 |
|------|------|------|
| `/a2` | A2Workspace（工作台） | v0 |
| `/a2/boards` | A2Boards（展板组） | v0（主模组 Tab）/ v0.5（骰子/角色 Tab） |

### 5.2 A2Workspace 状态机（仿 A1 三态流）

```
态① UpstreamSelect：GraphSelector 选 A1 图谱（默认最新已定稿+stale 徽章+变更集浮层
     +「留痕使用/换最新」二次确认）→ POST session/start
态② 路径分岔 ⭐：路径A 卡片（v1 置灰"即将上线"）/ 路径B 卡片（TRPG 默认线 ⚡）
     → v0：直接显示主模组预览摘要（scope 缺省+将产出章节预览）
     → v0.5：骰子投影步骤卡 → 角色投影步骤卡（依赖链 UI：未产骰子则角色卡禁用+提示）
态③ 汇合 finalize CTA：「生成主模组」→ 进度仪式（P1 过程可视化）→ 跳 /a2/boards
```

- 挂载恢复：按 a2_file_id 恢复（localStorage 存活跃 file_id，仿 A1 水合模式）
- 回退意图：仿 `a1_return_intent` 模式，`a2_return_intent='workspace'` 键

### 5.3 组件清单

| 组件 | 动作 | 说明 |
|------|------|------|
| `components/graph/GraphSelector.tsx` | **重建** | 批次三删除（零引用），A2 重新需要；按 Task 7 原规格：默认最新+stale 徽章+变更集浮层+二次确认 |
| `components/guided/GuidedChat.tsx` | 复用 | 仅路径A（v1） |
| `components/structured/DimensionProgress.tsx` | 复用改造 | A2 进度=路径步骤指示（P1 秩序感） |
| `components/a2/DiceBoard.tsx` | 新建 [v0.5] | 骰子五链+难度对照表+溯源徽章（signal_sources 可视化） |
| `components/a2/CharacterBoard.tsx` | 新建 [v0.5] | 4 相位卡（核心 2 相高亮）+常量/变量分栏 |
| `components/a2/ModuleBoard.tsx` | 新建 [v0] | 主模组展板（复用 PosterBoard 骨架） |
| `components/a2/ModuleDocView.tsx` | 新建 [v0] | 文字版渲染+复制/下载（md/json，B5） |
| `components/a2/PromptGroupViewer.tsx` | 新建 [v0.5] | 提示词组查看 |
| `pages/a2/A2Boards.tsx` | 新建 [v0] | Tab：主模组（v0）/骰子/角色（v0.5 置灰） |

### 5.4 TS 类型（与后端逐字对齐，仿 types/a1.ts + WarningLedgerEntry 先例）

```
frontend/src/types/a2.ts     # ScopeBoundary/DiceTemplate/CharacterTemplate/ModuleDocument/
                            # A2FileView 全字段对齐；枚举值逐字（DiceCoreType 等，标注不允许添加或修改）
frontend/src/api/a2.ts       # startA2Session/getA2File/finalizeA2/getModuleDoc/
                            # projectDice/projectCharacter（fetchWithTimeout 复用，409 body 结构化抛出）
```

### 5.5 视觉与 UX 一致性（P1-P3 落实）

- **P1 秩序感**：态②路径分岔卡=阶段地图；finalize 进度仪式； boards Tab 即产物地图——任意时刻 1 秒可说进展
- **P2 奇幻感**：投影步骤卡每步一个魔法时刻（骰子展开动画/相位点亮），令牌走 nebula 系（决策台账 §1 五件套），禁一次性贴图
- **P3 所有权**：文案"你的世界/你的模组"；文字版导出带品牌落款位（导出物规格>工具 UI）
- GSAP 政策：未装（F2 取证），A2 动效用 CSS token 方案，不新增依赖（与台账 §4 一致）

---

## 6. 架构一致性检查单（实施与验收共用）

| # | 检查项 | 判据 |
|---|--------|------|
| 1 | 免费线零 LLM | finalize 全链无 provider 调用（测试：provider=None 通过） |
| 2 | 编码制一致 | TD/TC/M 走 GraphCodeIssuer，格式断言 `IP\d{4}-(TD\|TC\|M)\d+-v\d+`，只追加 |
| 3 | stale 横切 | A1 重定稿→A2 M/TD/TC 自动 stale；消费 stale 记 used_stale；前端徽章 |
| 4 | 图谱事实源 | A2'/A2'' 仅经 StructuredFileStore 单向导出；无任何 file→graph 写路径 |
| 5 | 只读上游 | a2 域无任何对 A1 store/registry 的写调用（代码评审+测试双验） |
| 6 | 409 契约 | 三处 409（upstream_missing/not_finalized/dice_required）detail 结构化 |
| 7 | ledger 贯通 | A2 产物 warnings 含 a2_* 源 + upstream: 透传；前端角标 |
| 8 | 枚举封闭 | DiceCoreType/GrowthSystem/DifficultySystem/TemplatePhase/StageCode 断言封闭 |
| 9 | TS 对齐 | types/a2.ts 与 Pydantic 逐字（仿 WarningLedgerEntry 对齐测试先例） |
| 10 | 视觉令牌 | 零新依赖（无 gsap）；色值全走令牌；P1-P3 验收点过检 |
| 11 | 测试门禁 | pytest 全绿零回归；A2 新增契约+病理测试；vitest 新组件测试过 |
| 12 | 文档同步 | README 路由表/API 表更新；PROJECT_STATE 会话更新；MOC 注册 |

---

## 7. 断点提取

### 7.1 开发断点（BP = Breakpoint，按依赖排序）

| BP | 名称 | 现状→需要 | 依赖 | 段位 |
|----|------|----------|------|------|
| **BP-A2-0** | **D9 前置闸门** | tsc 16 错+vitest 存量失败 → 清零（≤1 天时间盒） | 无（先于一切新功能，台账钦定） | 前置 |
| **BP-A2-1** | 交接契约冻结 | 本规格 §2 评审定稿 → 作为 A2 唯一上游契约（变更须升版本） | 本文档获用户批准 | v0 |
| **BP-A2-2** | GraphSelector 重建 | 批次三已删 → 按 Task 7 原规格重建（含 Vitest 测试） | BP-A2-0 | v0 |
| **BP-A2-3** | A2 会话底座 | 无 → a2 域骨架（models/store/upstream_loader/session/start+file GET） | BP-A2-1 | v0 |
| **BP-A2-4** | 主模组 finalize 汇合 | 无 → module_finalizer 免费线 + M 发号注册 + stale 挂钩 | BP-A2-3 | v0 |
| **BP-A2-5** | 主模组文字版 | 无 → module_doc 渲染器 + /doc 端点 + ModuleDocView 前端（B5 导出） | BP-A2-4 | v0 |
| **BP-A2-6** | 骰子投影④ | 无 → dice_projector 四步 + TD 端点 + DiceBoard | BP-A2-4；**风险 R2（cst 稀疏）** | v0.5 |
| **BP-A2-7** | 角色投影⑤ | 无 → character_projector + TC 端点 + CharacterBoard | BP-A2-6（409 依赖链） | v0.5 |
| **BP-A2-8** | 策划线①② | 无 → planning_analyzer/case_retriever(RAG 30 案例库)/report | BP-A2-4；R3 | v1 |
| **BP-A2-9** | 治理收编 | 三代矛盾 → 2-A2-v0.3 治理文档（本规格升格） | BP-A2-1 定稿后 | 治理 |

### 7.2 验收闸门（G = Gate）

| G | 闸门 | 通过判据 |
|---|------|---------|
| **G-v0** | 基线验收（对齐 D7/B1：9.26，外测员无协助走通） | /a2 全链可走：选图谱→finalize→文字版导出可用（GM 拿 Markdown 能开团）；**零 LLM key 依赖** |
| **G-v0.5** | 投影完备 | 骰子→角色依赖链 409 正确；TD/TC stale 联动；五链溯源徽章可见 |
| **G-v1** | 策划线上线 | analyze 2 次 LLM 调用内出报告；决策落定可增强 finalize |
| **G-回归** | 每段位收尾 | §6 检查单 12 项全过 + pytest 全绿 + 浏览器手动冒烟（仿 A1 start.ps1 冒烟流） |

### 7.3 与全局断点的关系

- 旧六维断点 A-J 已判死（审计一）；I/J（GraphAssetReview Mock、start.ps1 路径）与 A2 无依赖
- A2 不阻塞 A3 数据模型设计（旧路线图 §12.3 原则延续：A3 可并行建模，消费 M 图谱契约=本规格 MainModulePayload）
- J2（id 不变量）归 v0.6 评审，不阻塞 A2-v0（A2 只读消费现有 id，不新造 id 语义）

---

## 8. 风险与开放问题

| # | 风险/问题 | 影响 | 缓解 |
|---|----------|------|------|
| R1 | **⛔产能未答**（台账未决项） | BP-A2-0 之后全部排期悬空 | 本规格先行定契约；实施规模待产能裁决（v0 后端 ≈5 文件+前端 ≈6 文件，1 人周量级） |
| R2 | **cst_* 约束节点稀疏**：graphify 的 constraint_fields 产出依赖 LLM，实测可能空/薄 | 骰子投影 Step4 边界钳制失效 → 数值边界退缺省 | 已设计降级：保守缺省+ledger 披露；v0.5 实施前跑 10 样本实测 cst 密度，低于阈值则 Step4 标记实验性 |
| R3 | RAG 案例库（30 条手工精选）工作量外溢 | v1 排期 | 案例库可并行 bootstrap（旧路线图独立路径原则）；v1 前不阻塞 |
| R4 | A1 parse_modules 值级方差传导 | A2 上游答案字段波动（32↔35） | A2 投影器全字段可缺省设计（§2.2 降级列）——上游薄不崩，披露不静默 |
| R5 | 平台缺口（用户隔离/MockUserStore） | A2 记录 user_id 但无真实账号（D8 过渡） | 遵 D8：localStorage+导出即个人空间；A2 不接账号，只保字段预留 |
| R6 | M 图谱"重定稿"语义未定 | 本规格 v0 简化为开新文件；A1 模式是同文件 v+1 | v0 从简（新文件），v0.5 评审是否对齐 A1 重定稿模式（涉及 BP-A2-4 契约微调） |
| O1 | 开放：机械码（B4）随 A2/A3 导出规格设计 | 文字版 JSON 中预留 `mechanical_codes: {}` 空节 | v1 导出规格设计时定 |
| O2 | 开放：产品总名 48h 未否决生效（台账未决） | 文字版品牌落款位用候选名「ECHO·回声工坊」 | 生效后全局替换 |

---

## 9. 执行顺序建议

```
[前置] BP-A2-0 D9 闸门（≤1天）← 需启动指令
   ↓
[v0 · 9.26 基线] BP-A2-1 契约冻结（本文档批准）→ BP-A2-3 会话底座 ∥ BP-A2-2 GraphSelector
   → BP-A2-4 finalize 汇合 → BP-A2-5 文字版 → G-v0 外测验收
   ↓
[治理] BP-A2-9 2-A2-v0.3 收编（可与 v0 并行）
   ↓
[v0.5] BP-A2-6 骰子投影 → BP-A2-7 角色投影 → G-v0.5
   ↓
[v1] BP-A2-8 策划线（案例库并行 bootstrap）→ G-v1
```

> 每段位启动前按 writing-plans 规范生成正式工作计划（.sisyphus/plans/）→ /start-work 实施。v0 段任务粒度建议：底座/汇合/文字版/前端四任务，各含 TDD 步骤。

---

## 变更记录

- 2026-09-17 v0.1 首版：A1 总结 + 交接契约冻结 + A2 三段设计（v0/v0.5/v1）+ 断点 BP-A2-0..9 + 闸门 G-v0/v0.5/v1
