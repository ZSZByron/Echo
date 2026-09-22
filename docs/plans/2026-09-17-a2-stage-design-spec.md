# A2 阶段交接与设计规格书 v0.1

> **日期**: 2026-09-17
> **地位**: A1→A2 阶段交接契约 + A2 前后端设计规格（依据 [[decision-log]] D3/D4/B4/B5/B6 + [[2_product-architecture]] 双路径架构 + [[A1-v0.5-A模块公用模块与A模块设计]] Task 10 + [[2-A2-v0.2-产品策划顾问+模组合成]] 产品理念）
> **阅读提醒**: 本文档同时回答六个问题——A1 总结 / 交接数据结构 / 架构一致性 / A2 前后端设计 / 开发断点 / A2 数据结构。§2 与 §4.3 为契约性内容，实现时逐字对齐。
> **待办**: 治理收编后应升格为 `2-A2-v0.3` 治理文档（见断点 BP-A2-0）。

---

## 目录

1. [A1 阶段总结](#1-a1-阶段总结)
2. [A1→A2 交接数据结构（契约冻结）](#2-a1a2-交接数据结构契约冻结)
3. [治理矛盾收编与架构一致性裁决](#3-治理矛盾收编与架构一致性裁决)
4. [A2 后端详细设计](#4-a2-后端详细设计)
5. [A2 前端详细设计](#5-a2-前端详细设计)
6. [断点提取（A2 开发断点编号清单）](#6-断点提取a2-开发断点编号清单)
7. [分期路线（P0 基线 → P3 完整）](#7-分期路线p0-基线--p3-完整)

---

## 1. A1 阶段总结

### 1.1 A1 是什么、做到了什么

**A1 世界观工坊**（`/a1`）：用户带入世界观（种子预设 / .txt 文档上传 / 一句话）→ LLM 引导访谈补全 10 模块 → 定稿编译为知识图谱 → 产出 IP 展板与视觉背景。

**已交付能力（全部实测可用）**：

| 环节 | 能力 | 实现位置 |
|------|------|---------|
| 入口 | 种子选择（TRPG 预设三件套）/ 文档上传（35 字段预填、逐字保真、无依据诚实留空）/ 一句话开始 | `a1_routes.py`, `worldview_upload.py` |
| 访谈 | 10 模块顺序状态机、LLM fills 自动填空、写保护提案（pending_proposals）、防卡死（stall 机制+示例）、发散引导 | `guide_engine.py`, `interviewer.py` |
| 门禁 | 定稿门禁 409+missing_sections（模块完成度真值化计数，占位答案不计入，J1） | `a1_question_tree.py` |
| 图谱化 | graphify 单次 LLM 调用产出 SIR 五字段 → 确定性编译双树图谱（J2 id 不变量未做，归 v0.6） | `graphify.py`, `a1_routes.py:_build_graph` |
| 版本化 | graph_code `IPxxxx-W{n}-v{n}`、重定稿 v+1 旧版保留、下游 stale 标记（只标记不删除） | `graph_code_issuer.py`, `stale_marker.py` |
| 产出 | 知识图谱页（tier 分组/搜索/节点详情/边审核）、IP 展板、视觉背景预生成 | `A1KnowledgeGraph.tsx`, `ip_poster.py` |
| 可观测 | warning ledger 五源披露（upload/convert/graphify/answers/直注），前端角标 | `warning_ledger.py`（J3） |
| 护栏 | 答案 ≤2000 / prompt 预算 / convert ≤20000 / store 备份轮转 / 专名 cap 披露（J4） | 各域模块 |

**质量基线**：pytest 1020/1020 全绿；vitest 185 passed（6 存量失败=useTypewriter）；tsc 16=存量基线（D9 闸门待清零）；契约测试 C1-C5 + xt 极限病理系列在库。

**治理基线**：v0.5 统一模型（NL/SIR/KG 三轴分离）+ v0.5.1 加固补丁（J1/J3/J4 已落地）为唯一权威概念模型；文档清账战役完成；容器化部署全链路实测通过（2026-09-13 批次四）。

### 1.2 A1 的问卷树（A2 的信号源地图）

现行 10 模块（`a1_question_tree.py`，模块 id 逐字）：

| # | 模块 id | 关键子字段（A2 信号价值） |
|---|--------|--------------------------|
| 1 | `IP定位` | name / concept / world_type / **core_experience** |
| 2 | `世界本体` | origin / existence / **reality_rule**（骰子核心的哲学信号） |
| 3 | `力量体系` | source / acquire / mechanism / **cost**（骰子五链·代价机制） |
| 4 | `地理空间` | terrain / vertical / special_geo（A2 分区的挂载锚点） |
| 5 | `文明与社会` | core_value / **conflict** / faction_type / economy（主势力/主线冲突信号） |
| 6 | `历史时间线` | time_span / key_nodes / **main_plot**（时代选择与平行剧情边界） |
| 7 | `视觉设计` | keywords / architecture / material |
| 8 | `玩法设计DNA` | player_role / main_action / **growth** / growth_end（等级系统信号） |
| 9 | `骰子设定` | **probability / dice_count / check_mode / success_check**（骰子五链·前四链，A1 已立法！） |
| 10 | `设定边界` | **immutable_core / ai_fill**（generation_boundary，约束生成器自身） |

> **关键发现**：骰子五链（概率分布/骰子数量/判定方式/成功判定/代价机制）中前四链已在 A1 问卷 `骰子设定` 模块立法，第五链（代价）在 `力量体系.cost`。A2 骰子投影器**有确定性信号源**，不必凭空生成。

### 1.3 遗留问题（对 A2 的影响）

| 遗留 | 状态 | 对 A2 的影响 |
|------|------|-------------|
| J2 id 不变量（sanitize 规范化/端点 canonical 匹配） | 待 v0.6 设计评审 | A2 消费图谱时**不得假设边端点 id 永远有效**——按 id 查询需容错缺失 |
| parse_modules 边缘文档字段三态漂移（spread=3） | 病灶归 J2/J3 | A2 的上游信号提取需容忍占位值（J1 已在出口拦截，A2 仍应防御） |
| store 单机假设（内存 dict+单 JSON，无用户隔离） | 平台缺口，D8 账号延期 | A2 沿用同一模式（`a2/store.py`），不擅自引入用户体系 |
| GraphSelector/IdentityGate/TopNav 前端组件 | 2026-09-13 批次三删除（零引用验证后） | A2 需**重建 GraphSelector**（断点 BP-A2-1） |
| tsc 16 + vitest 6 存量失败 | D9 前置闸门（时间盒 ≤1 天） | **先于一切 A2 新功能** |

---

## 2. A1→A2 交接数据结构（契约冻结）

### 2.1 交接总览：五类资产

```
A1 产出                                 A2 消费方式
─────────────────────────────────────────────────────────────
① A1 图谱 (graph_json)        ──►  A2 一切生成的唯一上游事实源
② A1Session.answers (NL)     ──►  LLM 上下文（策划分析/模组编成的语义信号）
③ 编码与注册表 (graph_code)   ──►  血缘链（parent_graph_code）+ stale 检查
④ StructuredFileStore         ──►  A2 产出的单向导出承载（同构复用）
⑤ 共享组件与基建              ──►  GraphSelector(重建)/GuidedChat/provider/ledger
```

**铁律：A2 只消费 A1 的"定稿产物"（图谱+会话快照），不可回改 A1 任何字段；A1 重新定稿产生新版本，旧版图谱被标 stale 但保留可查。**

### 2.2 资产①：A1 图谱 schema（逐字段，来源 `models/knowledge_graph.py` + `_build_graph`）

`GET /api/a1/file/{file_id}/graph`（须 status=finalized，否则 409 `pending_finalize`）返回：

```python
class KnowledgeGraph(BaseModel):
    scene_id: str                              # = A1 session_id
    nodes: dict[str, GraphNode]                # key = node id
    edges: list[GraphEdge]
    background_node_id: str | None             # 背景树根

class GraphNode(BaseModel):
    id: str                # 三种 id 形态（A2 必须全部识别）：
                         #   模块节点 = 模块 id（如 "骰子设定"）
                         #   条目节点 = "{module_id}.{subfield_id}"（与 answers key 同构）
                         #   深度树   = "d:{anchor}:{title}"（LLM 生成条目，title 已 sanitize）
                         #   约束节点 = "cst_*"（level 0）
    serial_number: str     # 背景树 "0"/"N"/"N-M"；深度树 "D{锚点}-{k}"
    level: int             # 约束 L0 → 背景 L1 → 模块 L2 → 条目 L3
    description: str       # 节点正文（NL）
    status: str            # pending/generating/completed/failed（资产管线语义，A2 只读）
    tier: int | None       # 0-6（L0 存在基座→L6 治理层；tier≠level，语义分层属性）

class GraphEdge(BaseModel):
    from_node_id: str
    to_node_id: str
    edge_type: str         # 封闭枚举: TREE | CROSS | SEMANTIC | RULE | STRUCTURE
    visual_description: str
    relation: str          # 概念边关系名（TREE/CROSS 为空）；18 码中文展示层见 relationLabel
    confidence: str        # "rule" | "semantic" | "structure" | ""
    confirmed: bool        # TREE/CROSS 恒 True；概念边经用户确认
```

**图谱形态事实**（v0.5 统一模型）：双树异号——背景树=问卷投影（`0/N/N-M` 序号），深度树=LLM 条目（`D{锚点}-{k}`）；tier 以节点属性+派生边呈现，不入图加深。

### 2.3 资产②：A1 会话与 SIR（LLM 上下文用）

- **A1Session.answers**: `dict["{module_id}.{subfield_id}", str]`——35 字段自然语言真值（J1 保证占位词不写入）。A2 的 LLM 调用（策划分析/模组编成）以此为语义输入，**NL 永不携带机器格式**（铁律沿用）。
- **GraphifyResult（SIR 五字段）**：`module_summaries / entries / edges / constraint_fields / open_questions`。A2 可读 `constraint_fields`（约束域映射）与 `open_questions`（世界观留白点→模组设计素材）。
- **warning ledger**：`file_rec["warnings"]`，LedgerEntry{source, detail, count, level}。A2 生成时应透传上游 ledger 并追加自身 source（见 §4.3）。

### 2.4 资产③：编码、版本与血缘底座（已存在，A2 直接复用）

```python
# graph_code_issuer.py — StageCode 封闭枚举（不允许添加或修改）
W  = A1 世界观    M  = A2 主模组      S  = A3 次级模组
TD = 骰子模板     TC = 角色模板       R  = 策划报告      G = 图谱

# 格式: IP{序号}-{阶段路径}-v{版本}
#   A1 重定稿:  IP0142-W1-v1 → IP0142-W1-v2（版本追加，永不覆盖）
#   A2 产出:   IP0142-M1-v1（M 在 IP 内递增）；骰子模板 IP0142-TD1-v1
#   A3 产出:   IP0142-M1-S1-v1（S 在其父 M 内递增）
# 发号规则: Store 层原子递增（单写者事务），(user_id, code) 唯一约束
```

- **上游清单**: `GET /api/graphs?user_id=` → `{ips:[{ip_code, display_name, artifacts:[{graph_id, graph_code, stage, instance_no, version, status(finalized/stale), created_at, parent_graph_code}]}]}`（`graph_registry_routes.py`，A2 的 GraphSelector 数据源）。
- **stale 语义**（横切铁律，逐字）：A1 重新定稿 → `mark_downstream_stale` 自动标记 `parent_graph_code` 指向旧版本的下游图谱；**只标记不删除**，附变更集；A2 消费 stale 上游前提示变更集，**不阻断**；用户坚持继续 → 留痕（`used_stale=true`）。

### 2.5 资产④⑤：共享基建与组件现状

| 基建 | 状态 | A2 用法 |
|------|------|--------|
| `provider.py` 多 LLM 抽象 | ✅ 六厂商加固 | A2 所有 LLM 调用经此（chat_json 健壮解析/降级重试） |
| `structured_file_store.py` | ✅ 单向导出 | A2 产出的文件快照（图谱→文件，反向不回写） |
| `stale_marker.py` + registry | ✅ | A2 finalize 时注册 M 图谱；重定稿时标记 A3 下游 |
| `warning_ledger.py` | ✅ | A2 追加 source 前缀（见 §4.3），不改动既有五源 |
| `GraphSelector.tsx` | ❌ 批次三已删 | **BP-A2-1 重建**（stale 徽章+变更集浮层+二次确认） |
| `GuidedChat.tsx` | ✅ A1 在用 | 路径 A 策划决策对话直接复用 |
| `identity`（register+tier） | ✅ | user_id 传递（D8：不引入登录） |

### 2.6 交接铁律（A2 消费规则，Must）

1. **只读上游**：A2 对 A1 图谱/answers 只读；任何修改诉求 → 引导用户回 A1 重新定稿（版本+1）。
2. **stale 不阻断**：上游 stale → 展示变更集 → 用户确认 → `used_stale` 留痕后继续。
3. **id 容错**：引用 A1 节点 id 前必须验证存在（J2 未落地，canonical 匹配不保证）；端点缺失的边引用进死区披露，不静默丢弃。
4. **图谱=事实源**：A2 的一切交付物（A2'/A2''文件、文字版、展板）均为图谱的单向序列化导出；文件永不反向改写图谱。
5. **编码纪律**：M/TD/TC/R 发号只经 GraphCodeIssuer；`StageCode` 枚举封闭，不添加不修改。

---

## 3. 治理矛盾收编与架构一致性裁决

### 3.1 三代 A2 设计矛盾对照表

| 维度 | 一代：2-A2-v0.2（08-05/08-19） | 二代：8.19 图谱中心制（2_product-architecture + Task 10） | 三代：decision-log B6（09-17） |
|------|------------------------------|--------------------------------------------------------|------------------------------|
| 核心契约 | `world_package.json` / `main_module.json` | **图谱中心**：A1 图谱 → 主模组图谱 `IPxxxx-M1-v1` | v0 只要求**主模组文字版** |
| 输入 | WorldPackage（含 DimensionResultSet——**已删除**） | A1 图谱（GraphSelector 显式选择） | 同二代 |
| API | `/api/planning/*` 8 端点 | `/api/a2/*` 6 端点 | 未指定 |
| 骰子/角色模板 | LLM 三步生成+校准（§6.3） | **确定性投影器**（查图谱→组装，非 LLM） | 未指定（机械码延期 B4） |
| 策划分析 | RAG 案例库（30 条 JSON+亲和度矩阵）+ FeatureExtractor | 路径 A analyze/decide/report（多轮对话） | 商业分析报告**延期** |
| 模组编成 | ModuleComposer（LLM） | 汇合于 finalize（免费线不带决策也可用） | 主模组文字版 |

### 3.2 一致性裁决（D-A2 系列，实现时逐条遵守）

- **D-A2-1 图谱中心制为准**：A2 核心交付物=主模组图谱（M stage）；一代的 `MainModule/DiceTemplate/CharacterTemplate` JSON 模型降格为**图谱的类型化投影**（渲染/导出视图，单向派生）。API 采用 `/api/a2/*`。
- **D-A2-2 免费线优先**：路径 B（TRPG 默认线）是主路径；路径 A（策划线）是可选增强。D2-③（AI 提案永不阻塞主路径）的直接推论。B6 基线（9.26）下 P0 甚至只做"汇合点"（无骰子/角色的主模组文字版）。
- **D-A2-3 投影器确定性**：骰子投影④/角色投影⑤=确定性查询引擎（查 A1 图谱信号节点→规则表映射→装配 TD/TC 图谱）。一代的 LLM 三步生成法仅保留"信号提取"语义——且信号已在 A1 问卷立法（§1.2），LLM 仅在 A1 graphify 阶段参与，A2 投影零 LLM。
- **D-A2-4 LLM 单点原则沿用**：A2 的 LLM 调用点收窄为两处——①路径 A 策划分析（analyze，多轮对话）；②主模组编成（finalize 内 module_compile，单次调用产 A2-SIR）。图谱装配（M/TD/TC）全部确定性，同输入可复现（v0.5 铁律 2 延伸）。
- **D-A2-5 产出三形态延伸**：A2 版 NL/SIR/KG——决策与编成对话（NL）→ A2-SIR 结构化中间表示 → M/TD/TC 图谱（KG）→ 文字版/展板（导出）。每种形态单生产单消费。
- **D-A2-6 范围裁剪遵 B6**：v0 基线=主模组文字版（Markdown/JSON 导出，B5 通用格式）。机械码（B4）、商业分析报告、场景拼装交互一律延期；骰子/角色模板排 P1（B6 未列入延期名单，但非基线验收必需——若产能受限可再裁）。
- **D-A2-7 治理收编**：本规格书 §3 为底稿，新立 `2-A2-v0.3`（治理规则：新版本顺延号新建文件），旧 v0.2 加归档头指向 v0.3。

### 3.3 v0.5 三铁律的 A2 延伸（架构一致性核心）

| v0.5 铁律（A1） | A2 延伸 |
|----------------|--------|
| 数据形态单生产单消费（NL/SIR/KG） | 决策对话（NL）→ A2-SIR → M/TD/TC 图谱 → 文字版导出；对话永不携带机器格式 |
| 图谱装配确定性（LLM 单点） | LLM 仅 analyze/module_compile 两点；投影器与图谱装配纯代码 |
| 诚实与可观测 | ledger 透传上游+追加 A2 源；门禁 409 契约；降级永不阻塞（graphify 失败→确定性骨架兜底，同 A1 模式） |

### 3.4 Must NOT do（红线清单）

1. ❌ A2 不得生成**世界级**细节（地理只到分区，场景细节归 A3——拓扑边界 §2.9.2）。
2. ❌ A2 不得修改 A1 字段/骨架边/结构边（权限链：只有厂家在 A1 重新定稿可改）。
3. ❌ A2 产出文件不得反向改写图谱。
4. ❌ 骰子模板不得违反 A1 `骰子设定`/`世界本体.reality_rule` 的映射（世界观一致性试纸）。
5. ❌ 不得新建 A1 结构边类型；EdgeType 封闭枚举不添加。
6. ❌ `StageCode`/`GameGenre`/`DiceCoreType`/`GrowthSystem`/`DifficultySystem`/`Phase` 等枚举封闭，不允许添加或修改。
7. ❌ scope_boundary（A3 不可超越的边界）生成后随 M 图谱版本化，A3 只能继承不能放宽。

---

## 4. A2 后端详细设计

### 4.1 域模块布局（`backend/app/domains/creation/a2/`）

```
backend/app/domains/creation/a2/
├── __init__.py
├── models.py              # A2 域内模型全集（§4.3；遵循 graphify.py 域内模型模式）
├── store.py               # A2Store（JSON 文件快照，沿用 A1Store 模式；D8 无用户体系）
├── upstream_loader.py     # A1 图谱消费：拉取 graph_json + answers 快照 + stale 检查 + used_stale 留痕
├── dice_projector.py      # ④ 骰子投影器（P1）：确定性查询引擎，零 LLM
├── character_projector.py # ⑤ 角色投影器（P1）：确定性，依赖 TD 图谱
├── module_finalizer.py    # ③ 主模组生成（P0 汇合点）：module_compile LLM 单点 + 确定性装配 M 图谱
├── module_text_exporter.py# 主模组文字版（P0）：M 图谱 → Markdown/JSON 单向序列化（B5/B6）
├── module_poster.py       # 主模组展板（P3）
├── planning_analyzer.py   # 路径A 策划分析（P2）：LLM 多轮对话决策循环
├── report_generator.py    # 策划报告（P2，R 图谱）
└── (api 层) backend/app/api/a2_routes.py
```

**依赖注入范式与 A1 一致**：provider 经 `create_provider(load_provider_config())` 获取，失败降级 None；LLM 失败永不阻塞（降级路径产出确定性骨架+ledger 披露）。

### 4.2 API 契约（`/api/a2/*`）

> Task 10 六端点为基；**加粗**者为本次补充的契约缺口（Task 10 未定义会话入口与产出查询，A1 对称性要求补齐）。分期标注 [P0][P1][P2][P3]。

| 方法 | 路径 | 请求→响应 | 说明 |
|------|------|----------|------|
| POST | `/api/a2/session/start` **[P0]** | `{user_id, upstream_graph_id?}`→`{session_id, file_id, upstream:{graph_id, graph_code, status, stale, change_set}}` | **新增**（Task 10 缺口）：免费线会话入口；upstream 缺省=该用户最新 W-stage 已定稿图谱；stale→附变更集（不阻断） |
| POST | `/api/a2/file/{id}/finalize` **[P0]** | `{decision_session_id?, used_stale?}`→`{module_graph_id, module_graph_code, warnings, ledger}` | **③汇合点**：不带 decision=免费线；产出 `IPxxxx-M1-v1`；注册 registry（parent=上游 W 图谱）；预留下游 stale 标记挂点 |
| GET | `/api/a2/file/{id}` **[P0]** | → A2 文件状态（status/upstream/产物索引/ledger） | **新增**：mirror A1 get_file |
| GET | `/api/a2/file/{id}/graph` **[P0]** | → M 图谱 KnowledgeGraph JSON | **新增**：须 status=finalized 否则 409 `pending_finalize` |
| GET | `/api/a2/file/{id}/module-text` **[P0]** | `?format=markdown\|json`→`{content, format, exported_at, module_graph_code}` | **新增**：主模组文字版（B6 核心交付；B5 通用格式） |
| POST | `/api/a2/file/{id}/dice-template` **[P1]** | `{upstream_graph_id?}`→`{dice_graph_id, dice_graph_code(IPxxxx-TD1-v1), spec}` | ④骰子投影；上游=A1 图谱 |
| POST | `/api/a2/file/{id}/character-template` **[P1]** | `{upstream_graph_id?, dice_template_id?}`→`{char_graph_id, char_graph_code(IPxxxx-TC1-v1), spec}` | ⑤角色投影；**缺骰子模板→409**（Task 10 TDD 要点） |
| POST | `/api/a2/analyze` **[P2]** | `{user_id, upstream_graph_id?}`→`{session_id, analysis, questions}` | 路径A 启动；上游 stale 附变更集提示 |
| POST | `/api/a2/decide` **[P2]** | `{session_id, decisions}`→`{a2_prime_file, free_path:"TRPG"}` | 决策落定（A2' 文件=决策快照） |
| GET | `/api/a2/report` **[P2]** | `?session_id=`→PlanningReport | 策划报告（R 图谱投影） |
| GET | `/api/a2/file/{id}/poster` **[P3]** | → 主模组展板数据 | mirror A1 poster |

**门禁与错误契约**（沿用 A1 409 语义）：上游不存在/未定稿→409 `pending_finalize`；角色投影缺骰子→409 `missing_dice_template`；finalize 无有效上游→404/409。**stale 永不 409**（提示+留痕，§2.4）。

### 4.3 数据模型（Pydantic 全集，`a2/models.py`）

```python
"""A2 domain models. 枚举一律封闭（不允许添加或修改）。"""
from enum import StrEnum
from pydantic import BaseModel, Field

# ── 会话与上游 ──────────────────────────────────────────────
class A2Mode(StrEnum):
    FREE = "free"            # 路径B/免费线（TRPG默认）
    PLANNING = "planning"    # 路径A/策划线

class UpstreamRef(BaseModel):
    """A1 图谱引用快照（upstream_loader 产出，写入 A2Session 时冻结）。"""
    graph_id: str
    graph_code: str                     # 如 "IP0142-W1-v2"
    status: str                         # finalized | stale
    change_set: dict | None = None      # stale 时的变更集
    used_stale: bool = False            # 用户坚持使用 stale 的留痕
    ip_code: str = ""

class A2Session(BaseModel):
    """A2 会话状态（A2Store JSON 快照）。"""
    session_id: str
    user_id: str
    mode: A2Mode = A2Mode.FREE
    upstream: UpstreamRef
    # 产物索引（全部经 GraphCodeIssuer 发号后回填）
    dice_graph_code: str = ""           # IPxxxx-TD1-v1（P1）
    char_graph_code: str = ""           # IPxxxx-TC1-v1（P1）
    module_graph_code: str = ""         # IPxxxx-M1-v1（P0）
    decision_session_id: str = ""       # 路径A 关联（P2）
    warnings: list[dict] = Field(default_factory=list)  # ledger 追加区

# ── ④ 骰子模板（TD 图谱的类型化投影，一代模型收编）──────────────
class DiceCoreType(StrEnum):
    """骰子核心类型。不允许添加或修改。"""
    D20_MODIFIER = "d20_modifier"   # 数值骰：d20+修正 vs DC
    DICE_POOL = "dice_pool"         # 骰池计数：Xd6 计 5-6
    PERCENTAGE = "percentage"       # 百分比对冲：技能% vs 难度%

class GrowthSystem(StrEnum):
    """等级系统。不允许添加或修改。"""
    SLOT = "slot"       # 槽位制（台阶渐进）
    TIER = "tier"       # 位阶制（跳跃质变）
    HYBRID = "hybrid"   # 混合制（槽位累积触发位阶跃迁）

class DifficultySystem(StrEnum):
    """难度系统。不允许添加或修改。"""
    COUNTER_VALUE = "counter_value"   # 对抗数值 DC=均值+系数
    CONTEXTUAL = "contextual"         # 情境阻力 梯度1-5
    HYBRID = "hybrid"                 # 双轨制

class DifficultyTier(BaseModel):
    label: str            # 日常/简单/标准/困难/极限
    modifier: int         # 挑战系数（对抗数值用）
    gradient: int         # 情境梯度 1-5
    description: str      # GM 参考

class DiceTemplateSpec(BaseModel):
    """TD 图谱的单向投影（渲染视图；图谱为事实源）。"""
    world_ref: str                      # 上游 A1 graph_code
    module_ref: str = ""                # 关联 M 图谱（后填）
    dice_core: DiceCoreType
    dice_source: str                    # 骰子来源描述
    success_criteria: str               # 成功判定方式
    growth_system: GrowthSystem
    level_cap: int | None = None
    tier_labels: list[str] = Field(default_factory=list)   # 位阶名（位阶制）
    modifier_range: tuple[int, int] | None = None
    difficulty_system: DifficultySystem
    difficulty_table: list[DifficultyTier] = Field(default_factory=list)  # 5 档
    stat_floor: int = 0
    stat_ceiling: int = 0
    # 信号溯源（诚实披露：每个决策来自哪个 A1 字段）
    signal_sources: dict[str, str] = Field(default_factory=dict)
    #   例 {"dice_core": "世界本体.reality_rule", "growth": "玩法设计DNA.growth"}
    conflict_warning: str | None = None  # 世界观信号与类型信号冲突时
```

```python
# ── ⑤ 角色模板（TC 图谱的类型化投影）─────────────────────────
class Phase(StrEnum):
    """角色模板4大相位。不允许添加或修改。"""
    NARRATIVE = "narrative"    # 叙事相位（锚点拓扑）
    MECHANISM = "mechanism"    # 机制相位（流程拓扑）
    RESOURCE = "resource"      # 资源相位（交换拓扑）
    DIRECTION = "direction"    # 定向相位（层级拓扑）

class PhaseContent(BaseModel):
    phase: Phase
    is_core: bool                       # 核心2相（定调结果）
    constants: list[dict] = Field(default_factory=list)   # 厂家常量（硬规则/经济闭环/终极边界）
    variables: list[dict] = Field(default_factory=list)   # 玩家变量（组合/叙事/路径自由度）
    anchors: list[str] = Field(default_factory=list)      # 留白锚点（"你有一个死敌，请自己填"）

class CharacterTemplateSpec(BaseModel):
    world_ref: str
    dice_template_ref: str
    flavor_concentration: str
    core_phases: list[Phase] = Field(default_factory=list)
    phases: dict[str, PhaseContent] = Field(default_factory=dict)

# ── ③ 主模组（M 图谱 + 文字版导出）────────────────────────────
class ScopeBoundary(BaseModel):
    """模组范围边界——A3 不可超越（认知边界 §1.3 逐字字段）。"""
    allowed_regions: list[str] = Field(default_factory=list)
    allowed_eras: list[str] = Field(default_factory=list)
    max_power_level: str = ""
    core_factions_unmodifiable: list[str] = Field(default_factory=list)
    max_party_size: int = 4
    content_density: str = ""

class ModuleSection(BaseModel):
    """主模组文字版分节（M 图谱的序列化单元）。"""
    kind: str              # overview | inherited | module | constraint
    title: str
    body: str              # Markdown 正文
    origin: str = ""       # inherited 节点回指 A1 node id（溯源）

class ModuleTextExport(BaseModel):
    """B6 核心交付物：主模组文字版。"""
    module_graph_code: str
    title: str
    tagline: str           # 一句话模组核心幻想
    scope_boundary: ScopeBoundary
    sections: list[ModuleSection]
    format: str = "markdown"
    upstream_ledger: list[dict] = Field(default_factory=list)  # 透传的 A1 ledger
```

**M 图谱装配约定**（确定性，P0 实现以 `_build_graph` 为模板）：

- 节点三层：**继承层**（A1 骨架选择性投影，id=`"inh:"+A1_id`，tier 保持，origin 回指）＋**模组层**（A2 新增：主线冲突/幕结构/地点分区/平行剧情/Culture 节点——拓扑边界矩阵授权的 A2 独有产出，id=`"mod:"+slug`）＋**约束层**（`cst_m_scope_boundary` 等 MODULE 级约束，level 0）。
- 边：沿用封闭 EdgeType（TREE 层内层级 / CROSS 跨层引用）；**不新建 A1 结构边**。
- scope_boundary 随 M 图谱版本化；A3 只继承不放宽。

### 4.4 关键流程：免费线 finalize 时序（P0 核心）

```
POST /api/a2/file/{id}/finalize
  1. 校验：A2Session 存在、upstream 有效（finalized 或 stale+used_stale 留痕）
  2. upstream_loader 拉取：A1 graph_json + answers 快照 + 上游 ledger
  3. module_compile（LLM 单点，provider 失败→降级）：
     输入 = A1 图谱骨架 + answers 关键信号（骰子设定/玩法DNA/文明与社会.冲突/历史时间线.main_plot）
          + open_questions（留白→模组设计素材）
     输出 = A2-SIR {module_title, tagline, scope_boundary, module_sections[],
                    prompts?}（结构化，NL 正文）
  4. 确定性装配 M 图谱：继承层投影 + 模组层节点 + cst_m_* 约束节点 + TREE/CROSS 边
  5. GraphCodeIssuer.next(user_id, ip, stage="M") → IPxxxx-M1-v1
  6. registry 注册（parent_graph_code=上游 W 图谱；为 A3 stale 链预留）
  7. ledger：透传上游 + A2 源追加（source="a2_compile"）；降级路径必披露
  8. 持久化：A2Session.module_graph_code 回填；M graph_json 入 A2Store；
     文字版按需从 M 图谱单向导出（module-text 端点，不落盘缓存或落 StructuredFileStore）
```

**TDD 要点**（Task 10 逐字保留+扩充）：finalize 不带 decision_session_id 也成功（免费线）✓；骰子→角色依赖校验（缺骰子→409）✓；模板 v+1 不覆盖 ✓；**新增**：LLM 失败→确定性骨架 M 图谱+ledger 披露（同 A1 graphify 降级）；上游 stale→不阻断+used_stale 留痕；scope_boundary 字段齐全性断言。

---

## 5. A2 前端详细设计

### 5.1 路由与页面结构

| 路由 | 页面 | 分期 |
|------|------|------|
| `/a2` | `pages/a2/A2Workspace.tsx`——三态工作台 | P0（简化态）→ P1/P2（完整态） |
| `/a2/boards` | `pages/a2/A2Boards.tsx`——展板组 | P1 起 |

**A2Workspace 三态**（镜像 A1 三态模式）：

```
态① 上游选择
  GraphSelector（重建）：消费 GET /api/graphs
  ├─ 默认选中该用户最新 W-stage 已定稿图谱
  ├─ stale 徽章 + 变更集浮层
  └─ 二次确认卡：「留痕使用旧版 / 回 A1 重新定稿」
        ↓
态② 路径选择与执行 ⭐（Task 10 Step3）
  ├─ 路径A 卡片（完整策划线）    [P2 前灰置："策划顾问即将上线"]
  ├─ 路径B 卡片（TRPG默认线⚡）
  │    P1：骰子投影 → 角色投影 两步进度卡
  │    P0：直通汇合 CTA「生成主模组」
  └─ 底部常驻：「跳过一切，直接生成主模组」（D2-③ 永不阻塞主路径）
        ↓
态③ 产出预览
  ├─ Tab1 主模组文字版（P0）：Markdown 渲染 + scope_boundary 卡片 + 导出按钮(.md/.json)
  ├─ Tab2 模组图谱（P0）：复用 A1KnowledgeGraph 渲染 M 图谱
  ├─ Tab3 骰子展板（P1）/ Tab4 角色展板（P1）
  └─ 「进入 A3」/「回 A1 修改世界观」（a1_return_intent 同款回退键模式）
```

**A2Boards**（`/a2/boards`）：Tab 切换 主模组文字版 | 骰子 | 角色 | 主模组展板；P3 追加 PromptGroupViewer（提示词组）。

### 5.2 组件复用与新建清单

| 组件 | 动作 | 说明 |
|------|------|------|
| `components/graph/GraphSelector.tsx` | **重建**（BP-A2-1） | 批次三删除；规格=Task 7 原样（stale 徽章/变更集/二次确认）+ Vitest |
| `components/guided/GuidedChat.tsx` | 复用 | 路径 A 策划决策对话 |
| `components/graph/A1KnowledgeGraph.tsx` | 复用 | M 图谱渲染（层级带状布局直接适用） |
| `components/poster/PosterBoard.tsx` | 复用 | 主模组展板骨架（P3） |
| `labels/relationLabel.ts` | 复用 | 边关系中文展示 |
| `components/a2/DiceBoard.tsx` 等 | 新建（P1） | 骰子/角色展板、DifficultyTable 渲染 |
| `api/a2.ts` + `types/a2.ts` | 新建（P0） | §5.3 |

### 5.3 TS 类型（`frontend/src/types/a2.ts`，与后端逐字对齐）

```typescript
// 枚举封闭——与后端逐字对齐，禁自造值
export type A2Mode = "free" | "planning";
export type DiceCoreType = "d20_modifier" | "dice_pool" | "percentage";
export type GrowthSystem = "slot" | "tier" | "hybrid";
export type DifficultySystem = "counter_value" | "contextual" | "hybrid";
export type Phase = "narrative" | "mechanism" | "resource" | "direction";

export interface UpstreamRef {
  graph_id: string; graph_code: string;
  status: "finalized" | "stale";
  change_set?: Record<string, unknown> | null;
  used_stale: boolean; ip_code: string;
}

export interface A2SessionInfo {
  session_id: string; user_id: string; mode: A2Mode;
  upstream: UpstreamRef;
  dice_graph_code?: string; char_graph_code?: string; module_graph_code?: string;
  warnings: WarningLedgerEntry[];   // 复用 types/a1.ts 的 WarningLedgerEntry
}

export interface ScopeBoundary {
  allowed_regions: string[]; allowed_eras: string[]; max_power_level: string;
  core_factions_unmodifiable: string[]; max_party_size: number; content_density: string;
}

export interface ModuleTextExport {
  module_graph_code: string; title: string; tagline: string;
  scope_boundary: ScopeBoundary;
  sections: Array<{ kind: "overview"|"inherited"|"module"|"constraint"; title: string; body: string; origin?: string }>;
  format: "markdown" | "json";
  upstream_ledger: WarningLedgerEntry[];
}

export interface DiceTemplateSpec { /* 与后端 DiceTemplateSpec 逐字对齐 */ }
export interface CharacterTemplateSpec { /* 与后端逐字对齐 */ }
```

### 5.4 视觉一致性（P1-P3 原则约束）

- **P1 秩序感**：A2Workspace 三态即过程可视化——态①选世界→态②选路径→态③出模组，任意时刻 1 秒可说出进展。
- **P2 奇幻感**：沿用 A1 星空主题 tokens（nebula/cosmos/energy 色板，决策台账 D 系治理）；导出物视觉规格高于工具 UI。
- **P3 所有权**：文案全程「你的世界 → 你的模组」；文字版导出带品牌落款位（P3 `flavor_concentration` 同款语气）。

---

## 6. 断点提取（A2 开发断点编号清单）

### 6.0 前置闸门（先于一切 A2 工作）

| 闸门 | 内容 | 状态 |
|------|------|------|
| **D9** | tsc 16 错误 + 存量测试失败清零，时间盒 ≤1 天 | 待启动指令（决策台账） |
| **⛔ 产能** | 谁写代码/几人/全职业余 | 未答，阻塞一切排期 |
| **D7 倒计时** | 外测员锁定日 9.20，基线验收 9.26（B1） | 未答 |

### 6.1 断点编号表

| # | 断点 | 内容 | 依赖 | 分期 | 验收 |
|---|------|------|------|------|------|
| BP-A2-0 | 治理收编 | 新立 `2-A2-v0.3`（本规格 §3 为底稿）；v0.2 加归档头；MOC 注册 | — | P0（文档，可并行） | 新文档入 MOC；三代矛盾表落档 |
| BP-A2-1 | GraphSelector 重建 | 组件+Vitest（stale 徽章/变更集浮层/二次确认）；消费 `/api/graphs` | — | P0 | Task 8 验收口径复跑 |
| BP-A2-2 | A2 会话底座 | `a2/models.py` 会话部分 + `store.py` + `upstream_loader.py` + `session/start` + registry 发号 M/TD/TC/R 实测 | D9 | P0 | 发号 `IPxxxx-M1-v1` 原子递增；stale 留痕 |
| BP-A2-3 | 主模组生成器 | `module_finalizer.py`（LLM 单点+确定性装配+降级骨架）+ finalize 端点 | BP-A2-2 | P0 | TDD：免费线成功/降级披露/scope 完整性 |
| BP-A2-4 | 主模组文字版 | `module_text_exporter.py` + `module-text` 端点（.md/.json） | BP-A2-3 | P0 | 导出物 GM 零加工可读（D2-①） |
| BP-A2-5 | A2Workspace P0 | 三态简化版（态③仅 Tab1/Tab2）+ types/api | BP-A2-1,4 | P0 | Playwright：选谱→生成→导出全链 |
| BP-A2-6 | 骰子投影器④ | `dice_projector.py`（确定性，信号源=骰子设定/reality_rule/growth/cost）+ TD 端点 + signal_sources 溯源 | BP-A2-3 | P1 | 同上游同 TD 图谱（确定性断言）；v+1 不覆盖 |
| BP-A2-7 | 角色投影器⑤ | `character_projector.py`（4 相位映射+常量变量分配）+ TC 端点 | BP-A2-6 | P1 | 缺骰子→409；常量管底线变量给选择 |
| BP-A2-8 | A2Boards + 展板 | 骰子/角色展板 Tab + DifficultyTable 渲染 | BP-A2-6,7 | P1 | 展板组四 Tab 可切换 |
| BP-A2-9 | 策划线三端点 | `planning_analyzer`（多轮对话决策循环）+ `report_generator`（R 图谱）+ analyze/decide/report + 前端报告面板 | BP-A2-3 | P2 | analyze 2 次 LLM 内出报告；免费线不被动依赖 |
| BP-A2-10 | 主模组展板+提示词组 | `module_poster.py` + PromptGroupViewer | BP-A2-8 | P3 | 展板视觉规格 ≥ A1 IP 展板 |
| BP-A2-11 | 全链路验收 | A1→A2→A3 streak（mirror Task 13）：`…finalize(A1)→a2/start→finalize(A2)→module-text→a3/expand…` 全 200；A1 重定稿→M 图谱 stale 徽章不阻断 | BP-A2-4(+A3 P0) | P0 末 | 证据存 `.sisyphus/evidence/` |

### 6.2 依赖图

```
D9 ─┬─► BP-A2-1 ──────────────┐
    ├─► BP-A2-2 ─► BP-A2-3 ─► BP-A2-4 ─► BP-A2-5 ─► BP-A2-11(P0 末)
    └─► BP-A2-0（文档，全程可并行）              │
                                                 └─► P1: BP-A2-6 ─► BP-A2-7 ─► BP-A2-8
                                                     P2: BP-A2-9    P3: BP-A2-10
```

---

## 7. 分期路线（P0 基线 → P3 完整）

| 期 | 目标 | 断点 | B6 对齐 |
|----|------|------|---------|
| **P0**（至 9.26） | 主模组文字版闭环：选 A1 图谱→免费线 finalize→M 图谱+文字版导出 | BP-A2-0~5, 11 | ✅ B6「A2 主模组文字版」；B5 通用格式导出 |
| **P1** | TRPG 默认线完整化：骰子/角色投影+展板 | BP-A2-6~8 | 骰子五链首次落地给 GM/PC |
| **P2** | 策划增强线：analyze/decide/report | BP-A2-9 | 商业分析仍延期（B6） |
| **P3** | 展板视觉+提示词组+机械码规格 | BP-A2-10 | 机械码随导出规格设计（B4 预留） |

**P0 最小验收（D7 对齐）**：外部用户从 A1 定稿图谱出发，在 A2 无协助选谱→生成→导出主模组文字版，GM 拿到 Markdown 零加工可开团。

---

## 附录：本文档引用的权威源

| 文档 | 用法 |
|------|------|
| [[decision-log]] v1.0（09-17） | D2/D3/D4/D7/D8/D9/B1/B4/B5/B6/P1-P3 裁决 |
| [[2_product-architecture]] | §3 A2 双路径职责表（现行） |
| [[A1-v0.5-A模块公用模块与A模块设计]] | Task 10 A2 API 契约 + TDD 要点（本规格 4.2 基座） |
| [[2-A2-v0.2-产品策划顾问+模组合成]] | 产品理念（制片人定位/骰子三步逻辑/4 相位）+ 枚举定义（§2/§6/§7 数据模型收编进 §4.3） |
| [[2-A-认知边界与信息框架总纲]] | §1.3 A2 契约边界（scope_boundary 逐字字段/骰子五链/常量变量原则） |
| a1-topology-boundary-spec（归档） | §2.9.2 阶段产出矩阵（A2 可生成范围：分区/平行剧情/Culture/MODULE 约束） |
| [[2-A1-v0.5-内容图谱化统一模型与契约]] | 三铁律（本文档 §3.3 延伸依据） |
| 代码事实 | `a1_routes.py`/`graphify.py`/`guide_engine.py`/`knowledge_graph.py`/`graph_code_issuer.py`/`structured_file_store.py`（schema 逐字段核对） |
