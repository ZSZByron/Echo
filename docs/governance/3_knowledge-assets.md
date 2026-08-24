---
tags: [governance, knowledge, data-model]
updated: 2026-08-05
---

# 表3 — 知识资产体系 (Knowledge Asset Architecture)

> **管理维度**: 内容 — "世界知识如何组织、连接、复用？"
>
> **更新频率**: 新数据模型确定时
>
> **核心认知**: 项目的护城河不是代码，而是世界知识的数据结构。
>
> **⚠️ 定位修正（2026-08-05）**: 知识图谱是系统的**后台支撑层**，不是面向厂家的交付物。厂家看到的是经过产品化处理后的 world_package.json，而非原始知识图谱。

---

## 1. 知识结构全景

```
World Model（世界实例）
  │
  ├── KnowledgeGraph（知识图谱 — 交叉关系）
  │     ├── 实体节点：Geography/Faction/Event/Concept/Constraint(A1) + Culture(A2) + Character/Item/Scene(A3)
  │     └── 交叉边：见 §5 边类型词典 v0.1（封闭枚举）
  │
  ├── StoryGraph（剧情图 — 分支叙事）
  │     ├── 节点：start/end/choice/event/condition
  │     └── 边：条件分支 + 选择支
  │
  ├── EventGraph（事件图 — 动态触发）
  │     ├── 触发器：time/location/state
  │     └── 动作 + 奖励
  │
  ├── CultureTree（文化树 — 递归层级）
  │     ├── 价值观 + 美学原则
  │     └── 父子递归
  │
  ├── ConstraintTree（约束树 — 硬/软约束）
  │     ├── HARD（不可违反） / SOFT（可弯曲）
  │     └── 优先级排序
  │
  ├── SceneGraph（场景图 — 空间依赖）
  │     └── Kahn 拓扑排序
  │
  └── PuzzleGraph（谜题图 — 求解依赖）
        └── 拓扑求解顺序
```

> **填写指引**: 上图预填自 SYSTEM_DESIGN_SPEC_v4.md §2 五图模型 + 代码实际模型。新增图模型时追加。
>
> **⚠️ 重要**: 以上图谱模型均为 **A1 世界观IP设计工作台的后台支撑层**，不直接面向厂家。厂家通过问卷完成世界观IP立项，系统在后台编译为图谱结构。厂家看到的交付物是 World IP Schema（见下方 §1.1）。

### 1.1 A1 世界观IP设计工作台输出包 (World IP Schema)

> **定位**: A1 世界观IP设计工作台的**核心交付物** — 厂家拿到后可以直接开始产品化工作。由问卷回答编译生成。
>
> **详细设计**: [[2-A1-v0.2-6维约束体系×6层生成维度]] §7.2

```json
{
  "identity_card": {
    "世界类型": "多文明科幻幻想",
    "一句话定位": "...",
    "核心体验": ["探索", "发现", "连接历史"],
    "核心冲突": "文明扩张 vs 宇宙记忆",
    "玩家身份": "历史探索者"
  },
  "visual_bible": {
    "建筑": { "关键词": [...], "禁止": [...] },
    "色彩": { "主色": [...], "强调色": [...] },
    "材质": { "金属": "...", "石材": "...", "能源": "..." }
  },
  "gameplay_anchor": {
    "核心行为": ["探索", "连接", "选择", "成长"],
    "重复玩法循环": "...",
    "成长路径": "..."
  },
  "design_note": {
    "世界设计原理": "...",
    "时间线设计": "...",
    "力量体系设计": "...",
    "文明发展设计": "..."
  },
  "generation_boundary": {
    "ai_can_generate": ["NPC", "城市", "任务", "剧情", "资产"],
    "ai_cannot_change": ["世界核心规则", "力量来源", "核心冲突", "玩家身份"]
  },
  "_backend": {
    "world_schema": "WorldSchema 实例（给AI使用）",
    "knowledge_graph": "KnowledgeGraph 实例（后台支撑）— A1 产出骨架节点（Geography/Faction/Event/Concept/Constraint）+ 结构拓扑边（见 §5 边类型词典 v0.1）。Character/Item/Scene 等细节节点由 A2/A3 在拓扑内填充",
    "rule_graph": "RuleGraph 实例（因果/约束/模拟）",
    "constraint": "DimensionResultSet（后台支撑）"
  }
}
```

> **注意**: `_backend` 字段是 AI 内部使用，厂家不需要看到。`generation_boundary` 是 A1 问卷第八部分（AI生成边界）的直接输出。

---

## 2. 实体类型清单 (Ontology)

> **填写规则**: 每种实体一行。定义"世界上存在哪些东西"。

| 实体类型 | 首次出现阶段 | 代码位置 | 描述 | 示例 |
|---------|------------|---------|------|------|
| Character | A3 | <!-- models/entity.py --> | NPC / 玩家角色 | "精灵王艾兰" |
| Geography | A1 | <!-- models/entity.py --> | 地理结构单元（大陆/海洋/山脉/地下/天空层）— 由世界规则和力量体系编译推导，非问卷直采 | "银月大陆"、"虚空裂隙" |
| Item | A3 | <!-- models/entity.py --> | 物品 / 装备 | "水晶祭坛" |
| Faction | A1 | <!-- models/entity.py --> | 势力 / 组织 | "银月议会" |
| Concept | A1 | <!-- models/entity.py --> | 抽象概念（力量体系/世界本体） | "元素魔法体系" |
| Event | A1 | <!-- models/entity.py --> | 事件 | "诸神黄昏" |
| Culture | A2 | <!-- models/culture.py --> | 文化体 | "高地人文化" |
| Constraint | A1 | <!-- models/constraint.py --> | 规则约束 | "禁用火魔法" |
| Scene | A3 | <!-- models/entity.py --> | 场景空间 | "酒馆大厅" |

> **首次出现阶段说明**:
> - **A1 阶段产出**: Geography / Faction / Event / Concept / Constraint — 构成知识图谱骨架节点 + 结构拓扑边（见 §5）
> - **A2 阶段补充**: Culture — 在 A1 已有的 Geography/Faction 拓扑内填充文化体
> - **A3 阶段补充**: Character / Item / Scene — 在 A2 区域拓扑内填充具体实体
> - A2/A3 **不可新建** A1 阶段的边类型（结构常量不可覆写），只能在已有拓扑内追加细节节点
> - **结构层级详细定义**（A1 结构拓扑 / A2 区域填充 / A3 实体填充 + "骨架级"语义澄清）: 见 [[2-A1-v0.1-6维约束体系（6个生成维度）]] §6.4

---

## 3. ID 规则

> **填写规则**: 定义全项目统一的 ID 命名规范。

### 3.1 ID 格式

| 类型 | 前缀 | 格式 | 示例 |
|------|------|------|------|
| 世界 | `world` | `world_{timestamp}` | `world_20260804` |
| 角色 | `char` | `char_{seq:03d}` | `char_001` |
| 地理 | `geo` | `geo_{seq:03d}` | `geo_003` |
| 物品 | `item` | `item_{seq:03d}` | `item_024` |
| 事件 | `evt` | `evt_{seq:03d}` | `evt_012` |
| 势力 | `fac` | `fac_{seq:03d}` | `fac_001` |
| 概念 | `cpt` | `cpt_{seq:03d}` | `cpt_002` |
| 文化 | `cul` | `cul_{seq:03d}` | `cul_001` |
| 约束 | `cst` | `cst_{seq:03d}` | `cst_005` |
| 资产 | `asset` | `asset_{uuid8}` | `asset_a1b2c3d4` |
| 场景 | `scene` | `scene_{seq:03d}` | `scene_001` |

### 3.2 ID 分配规则

<!-- 填写: ID 是自增？UUID？还是语义化（如 world_darkforest_elfking）？ -->

---

## 4. Schema 定义

> **填写规则**: 每种实体的数据模型字段。已有代码的从 Pydantic 模型提取。

### 4.0 通用实体节点 (EntityNode)

> **定位**: 所有知识图谱实体节点的基类。与 `GraphNode`（资产生成依赖树）**职责分离**——EntityNode 是世界知识本体，GraphNode 是 Wave 串行生成的拓扑排序节点。两者不可合并。

| 字段 | 类型 | 必填 | 描述 | 代码位置 |
|------|------|------|------|---------|
| id | str | ✅ | 唯一标识（见 §3 ID 规则） | <!-- models/entity.py --> |
| type | EntityType | ✅ | 实体类型枚举（见 §2） | <!-- models/entity.py --> |
| name | str | ✅ | 显示名称 | <!-- models/entity.py --> |
| detail_level | DetailLevel | ✅ | CONCEPT(A1) / REGIONAL(A2) / SCENE(A3) — 粒度层级 | <!-- models/entity.py --> |
| source_stage | str | ✅ | "A1" / "A2" / "A3" — 谁创建的，不可变 | <!-- models/entity.py --> |
| attributes | dict | ✅ | 类型特定属性（见 §4.1-§4.9） | <!-- models/entity.py --> |
| created_at | datetime | ✅ | 创建时间 | <!-- models/entity.py --> |

> **detail_level 语义**:
> - `CONCEPT` — A1 产出的概念级节点（如"银月大陆"，一个名字+一句话定位）
> - `REGIONAL` — A2 在 A1 拓扑内填充的区域级节点（如"银月广场"）
> - `SCENE` — A3 填充的场景级节点（如"议会大厅密室"）
>
> 同一个 `EntityNode` 实例的 `detail_level` 和 `source_stage` 在创建后不可变。A2/A3 通过**新增子节点**（沿 GEO_CONTAINS 等边）扩展拓扑，不修改 A1 节点。

### 4.1 地理 (Geography) — A1 首次产出

> **数据来源**: 问卷模块 4（地理空间）显式提取 — 主要地形/垂直层级/特殊地理。AI 设计顾问结合模块 2（世界本体）+ 模块 3（力量体系）推导 shaping_rules / power_sources 关联，厂家确认。
> **语义**: 地理结构关系系统——表达"世界规则如何塑造地形"，不是地名标签。

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| geo_type | GeoType | ✅ | CONTINENT / OCEAN / MOUNTAIN / UNDERGROUND / SKY_LAYER / RIVER / FOREST / DESERT / OTHER |
| vertical_layer | VerticalLayer | ✅ | SKY / SURFACE / UNDERGROUND / DEEP — 垂直层级（支持 GEO_ABOVE/BELOW 边） |
| shaping_rules | list[str] | ✅ | 塑造此地理的规则 ID 列表（Constraint 节点 id，对应 RULE_SHAPES_GEO 边） |
| power_sources | list[str] | <!-- --> | 力量来源 ID 列表（Concept 节点 id，对应 POWER_SATURATES_GEO 边） |
| short_description | str | ✅ | 一句话定位（如"高重力塑造的扁平大陆"） |

### 4.2 势力 (Faction) — A1 首次产出

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| ideology | str | ✅ | 核心意识形态 |
| power_tier | PowerTier | ✅ | MAJOR / MINOR / FRINGE — 势力量级 |
| territory_geo_ids | list[str] | <!-- --> | 控制领地的 Geography 节点 ID 列表（对应 GEO_SEPARATES / GEO_NOURISHES 边） |
| allies | list[str] | <!-- --> | 盟友 Faction ID 列表（对应 FACTION_ALLIED 边） |
| enemies | list[str] | <!-- --> | 敌对 Faction ID 列表（对应 FACTION_OPPOSES 边） |

### 4.3 事件 (Event) — A1 首次产出

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| era | str | ✅ | 所属历史时期 |
| severity | EventSeverity | ✅ | COSMIC / MAJOR / REGIONAL / MINOR — 影响范围 |
| location_geo_id | str | <!-- --> | 发生地的 Geography 节点 ID（对应 GEO_HOSTS_EVENT 边） |
| involved_faction_ids | list[str] | <!-- --> | 涉及势力 ID 列表 |
| caused_by_event_id | str | <!-- --> | 因果上游事件 ID（对应 EVENT_CAUSED_BY 边） |

### 4.4 概念 (Concept) — A1 首次产出

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| concept_type | ConceptType | ✅ | POWER_SYSTEM / COSMOLOGY / PHILOSOPHY / OTHER — 概念类别 |
| manifestation_geo_ids | list[str] | <!-- --> | 具现为哪些地理节点（对应 CONCEPT_MANIFESTS_AS 边） |
| description | str | ✅ | 概念描述 |

### 4.5 约束 (Constraint) — A1 首次产出

| 字段 | 类型 | 必填 | 描述 | 代码位置 |
|------|------|------|------|---------|
| dimension | ConstraintDimension | ✅ | 6维之一 | `models/dimension.py` |
| level | ConstraintLevel | ✅ | CORE/MODULE/SCENARIO | <!-- 待创建枚举 --> |
| type | HARD/SOFT | ✅ | 硬约束/软约束 | `models/constraint.py` |
| priority | int | <!-- --> | 优先级 | <!-- --> |
| content | str | ✅ | 约束内容 | <!-- --> |
| limits_entity_ids | list[str] | <!-- --> | 限制哪些实体（对应 CONSTRAINT_LIMITS 边） |

### 4.6 文化 (Culture) — A2 首次产出

> **代码位置**: `models/culture.py`（CultureTree 递归节点，已有实现）

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| values | list[str] | ✅ | 价值观列表 |
| aesthetics | list[str] | ✅ | 美学原则 |
| parent_culture_id | str | <!-- --> | 父文化 ID（CultureTree 递归） |
| region_geo_id | str | <!-- --> | 所属区域的 Geography 节点 ID |

### 4.7 角色 (Character) — A3 首次产出

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| race | str | <!-- --> | 种族 |
| culture_id | str | <!-- --> | 所属文化 ID |
| faction_id | str | <!-- --> | 所属势力 ID（对应 CHAR_BELONGS_TO 边，见 §5） |
| relations | list | <!-- --> | 关系列表 |
| state | dict | <!-- --> | 当前状态 |

### 4.8 物品 (Item) — A3 首次产出

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| item_type | str | ✅ | 物品类型（武器/装备/消耗品/任务物品...） |
| owner_char_id | str | <!-- --> | 持有者 Character ID（对应 owns 边） |
| location_geo_id | str | <!-- --> | 所在 Geography 节点 ID |

### 4.9 场景 (Scene) — A3 首次产出

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| scene_type | str | ✅ | 场景类型（室内/室外/地下/空中...） |
| parent_geo_id | str | ✅ | 所属 Geography 节点 ID（沿 GEO_CONTAINS 边下挂） |
| atmosphere | str | <!-- --> | 氛围描述 |

### 4.10 资产 (Asset) — 独立于知识图谱

> **代码位置**: `models/asset.py`（资产状态机，服务于 Wave 串行生成，非知识图谱实体）

| 字段 | 类型 | 必填 | 描述 | 代码位置 |
|------|------|------|------|---------|
| asset_id | str | ✅ | 唯一标识 | `models/asset.py` |
| type | AssetType | ✅ | 资产类型 | `models/asset.py` |
| status | AssetStatus | ✅ | 生命周期状态 | `models/asset.py` |
| parent_id | str | <!-- --> | 父节点 | <!-- --> |
| prompt | str | ✅ | 生成用Prompt | <!-- --> |
| image_url | str | <!-- --> | 生成结果URL | <!-- --> |

---

## 5. 边类型词典 (Edge Type Dictionary)

> **治理原则**: 封闭枚举 + 版本化。边类型是 `StrEnum`，新增类型必须升级词典版本号并经设计评审。
> **版本**: v0.1（2026-08-05 首次定义）
> **核心规则**: A1 阶段建立的结构拓扑边（第 1-3 类）为**不可覆写常量**；A2/A3 只能在已有拓扑内追加细节节点（第 4-5 类），不可新建结构边。

### 5.1 词典版本规则

| 规则 | 说明 |
|------|------|
| 封闭枚举 | 所有边类型必须是下方表格中已定义的值，代码实现为 `StrEnum` |
| 版本化 | 词典带版本号（当前 v0.1）；新增边类型 → 升级版本号（如 v0.2） |
| 设计评审 | 新增边类型需经设计评审，不可由开发者随意添加 |
| 阶段不可越权 | 标注"仅 A1"的边类型，A2/A3 不可新建；标注"A1+"的边类型，A2/A3 也可新建 |

### 5.2 边类型清单 v0.1

#### 第 1 类：地理层内部关系（Geography ↔ Geography）

| 边类型 | 语义 | 可建阶段 | 示例 |
|--------|------|---------|------|
| `GEO_CONTAINS` | 层级包含 | A1+ | 大陆 → 区域 → 地标 |
| `GEO_BORDERS` | 水平邻接 | A1+ | 海洋 —borders→ 大陆 |
| `GEO_ABOVE` | 垂直上层 | 仅 A1 | 天空层 —above→ 地表 |
| `GEO_BELOW` | 垂直下层 | 仅 A1 | 地下世界 —below→ 地表 |

#### 第 2 类：规则/力量 → 地理（因果链，A1 独有价值）

| 边类型 | 语义 | 可建阶段 | 示例 |
|--------|------|---------|------|
| `RULE_SHAPES_GEO` | 物理法则塑造地形 | 仅 A1 | "高重力"(Constraint) → "扁平大陆"(Geography) |
| `POWER_SATURATES_GEO` | 力量体系渗透地理 | 仅 A1 | "元素魔法"(Concept) → "元素浓度带"(Geography) |
| `POWER_SOURCES_FROM_GEO` | 力量源于地理 | 仅 A1 | "灵脉"(Concept) ← "山脉地脉"(Geography) |

> **为何"仅 A1"**: 这些边表达的是世界规则如何塑造地形——A2/A3 不重新定义世界规则，故不可新建此类边。这是 A1 作为"世界观 IP 立项"阶段的独有价值。

#### 第 3 类：地理 → 势力/事件（跨层投影）

| 边类型 | 语义 | 可建阶段 | 示例 |
|--------|------|---------|------|
| `GEO_SEPARATES` | 地理隔离 | A1+ | 山脉 —separates→ 势力A / 势力B |
| `GEO_NOURISHES` | 地理滋养 | A1+ | 富饶平原 —nourishes→ 强国 |
| `GEO_HOSTS_EVENT` | 地理承载事件 | A1+ | 虚空裂隙 —hosts→ "大分裂事件" |

#### 第 4 类：势力/事件/概念层内部关系

| 边类型 | 语义 | 可建阶段 | 示例 |
|--------|------|---------|------|
| `FACTION_ALLIED` | 势力联盟 | A1+ | 银月议会 ↔ 铁拳佣兵团 |
| `FACTION_OPPOSES` | 势力对立 | A1+ | 银月议会 ↔ 虚空教团 |
| `EVENT_CAUSED_BY` | 事件因果链 | A1+ | "大分裂" ←caused_by→ "神战余波" |
| `CONCEPT_MANIFESTS_AS` | 概念具现 | 仅 A1 | "魔法体系"(Concept) → "灵脉网络"(Geography) |
| `CONSTRAINT_LIMITS` | 约束限制实体 | A1+ | "禁用火魔法"(Constraint) → 某势力 |

#### 第 5 类：跨层社会关系（A2/A3 填充层）

| 边类型 | 语义 | 可建阶段 | 示例 |
|--------|------|---------|------|
| `CHAR_BELONGS_TO` | 角色属于势力 | A3+ | 精灵王 → 银月议会 |
| `CHAR_LOCATED_AT` | 角色位于地理 | A3+ | 精灵王 → 银月城 |
| `ITEM_OWNED_BY` | 物品被持有 | A3+ | 水晶祭坛 ← 精灵王 |
| `ITEM_LOCATED_AT` | 物品位于地理 | A3+ | 水晶祭坛 → 议会大厅 |
| `EVENT_INVOLVES_CHAR` | 事件涉及角色 | A3+ | 诸神黄昏 → 精灵王 |
| `CULTURE_INFLUENCES` | 文化影响角色 | A2+ | 高地文化 → 精灵王 |

### 5.3 禁止的关系

| 源类型 | 关系 | 目标类型 | 原因 |
|--------|------|---------|------|
| Item | CHAR_BELONGS_TO | Character | 方向反了，应为 ITEM_OWNED_BY |
| A2/A3 节点 | RULE_SHAPES_GEO | Geography | 因果链边仅 A1 可建 |
| A2/A3 节点 | CONCEPT_MANIFESTS_AS | Geography | 概念具现边仅 A1 可建 |
| 任意 | 未在 5.2 定义的类型 | 任意 | 封闭枚举，禁止未注册的边类型 |

---

## 6. 约束体系

### 6.1 六维约束

| 维度 | 代码 | 全称 | 含义 |
|------|------|------|------|
| RED | RED | 内容红线 | 禁止生成的内容（暴力/敏感等） |
| LAW | LAW | 物理法则 | 世界物理规律（重力/魔法规则等） |
| ACT | ACT | 行为规则 | 角色行为约束（道德/法律等） |
| NAR | NAR | 叙事约束 | 叙事风格/节奏约束 |
| WST | WST | 世界状态 | 世界当前状态约束 |
| SOC | SOC | 社交生态 | 社会关系/权力结构约束 |

### 6.2 六维生成层级

| 层级 | 代码 | 含义 | 对应图模型 |
|------|------|------|-----------|
| World | WORLD | 世界观 | KnowledgeGraph |
| Region | REGION | 区域 | KnowledgeGraph (sub) |
| Scene | SCENE | 场景 | SceneGraph |
| Campaign | CAMPAIGN | 战役/剧情 | StoryGraph + EventGraph |
| NPC | NPC | 角色 | KnowledgeGraph (node) |
| Asset | ASSET | 资产 | AssetStore |

### 6.3 权重矩阵

> **来源**: `data/weight_matrix.yaml`（6×6，每行和=100）
>
> **状态**: 静态硬编码。规则化动态调整见控制塔断点A。

<!-- 填写: 是否需要在此记录权重矩阵的当前值？还是引用 YAML 文件？ -->

---

## 7. 约束继承规则

> **设计文档**: [[plans/2026-08-03-layered-constraint-architecture]] 第五节
>
> **状态**: 设计完成，代码未实现（控制塔断点F）

| 权重占比 | 继承策略 | 说明 |
|---------|---------|------|
| ≥10% | 完整传递 | 约束原样传递到下游节点 |
| 5-10% | 压缩为摘要 | 约束简化为一句话摘要 |
| <5% | 不传递 | 约束不影响下游 |
| override | 可覆盖不可删除 | 子节点可声明 override，但原约束仍记录 |
