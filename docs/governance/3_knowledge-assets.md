---
tags: [governance, knowledge, data-model]
updated: 2026-08-04
---

# 表3 — 知识资产体系 (Knowledge Asset Architecture)

> **管理维度**: 内容 — "世界知识如何组织、连接、复用？"
>
> **更新频率**: 新数据模型确定时
>
> **核心认知**: 项目的护城河不是代码，而是世界知识的数据结构。

---

## 1. 知识结构全景

```
World Model（世界实例）
  │
  ├── KnowledgeGraph（知识图谱 — 交叉关系）
  │     ├── 实体节点：角色/地点/物品/势力/概念
  │     └── 交叉边：belongs_to / contains / uses / related_to
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

---

## 2. 实体类型清单 (Ontology)

> **填写规则**: 每种实体一行。定义"世界上存在哪些东西"。

| 实体类型 | 代码位置 | 描述 | 示例 |
|---------|---------|------|------|
| Character | <!-- models/xxx.py --> | NPC / 玩家角色 | "精灵王艾兰" |
| Location | <!-- 填写 --> | 地点 / 场景 | "黑暗森林" |
| Item | <!-- 填写 --> | 物品 / 装备 | "水晶祭坛" |
| Faction | <!-- 填写 --> | 势力 / 组织 | "银月议会" |
| Concept | <!-- 填写 --> | 抽象概念 | "魔法体系" |
| Event | <!-- 填写 --> | 事件 | "诸神黄昏" |
| Culture | <!-- 填写 --> | 文化体 | "高地人文化" |
| Constraint | <!-- 填写 --> | 规则约束 | "禁用火魔法" |
| Scene | <!-- 填写 --> | 场景空间 | "酒馆大厅" |
| <!-- 补充更多 --> | | | |

---

## 3. ID 规则

> **填写规则**: 定义全项目统一的 ID 命名规范。

### 3.1 ID 格式

| 类型 | 前缀 | 格式 | 示例 |
|------|------|------|------|
| 世界 | `world` | `world_{timestamp}` | `world_20260804` |
| 角色 | `char` | `char_{seq:03d}` | `char_001` |
| 地点 | `loc` | `loc_{seq:03d}` | `loc_003` |
| 物品 | `item` | `item_{seq:03d}` | `item_024` |
| 事件 | `evt` | `evt_{seq:03d}` | `evt_012` |
| 资产 | `asset` | `asset_{uuid8}` | `asset_a1b2c3d4` |
| 场景 | `scene` | `scene_{seq:03d}` | `scene_001` |
| <!-- 补充 --> | | | |

### 3.2 ID 分配规则

<!-- 填写: ID 是自增？UUID？还是语义化（如 world_darkforest_elfking）？ -->

---

## 4. Schema 定义

> **填写规则**: 每种实体的数据模型字段。已有代码的从 Pydantic 模型提取。

### 4.1 角色 (Character)

| 字段 | 类型 | 必填 | 描述 | 代码位置 |
|------|------|------|------|---------|
| id | str | ✅ | 唯一标识 | <!-- 填写 --> |
| name | str | ✅ | 显示名称 | <!-- 填写 --> |
| race | str | <!-- 填写 --> | 种族 | <!-- 填写 --> |
| culture | str | <!-- 填写 --> | 所属文化 | <!-- 填写 --> |
| relations | list | <!-- 填写 --> | 关系列表 | <!-- 填写 --> |
| state | dict | <!-- 填写 --> | 当前状态 | <!-- 填写 --> |
| <!-- 补充更多字段 --> | | | | |

### 4.2 资产 (Asset)

| 字段 | 类型 | 必填 | 描述 | 代码位置 |
|------|------|------|------|---------|
| asset_id | str | ✅ | 唯一标识 | `models/asset.py` |
| type | AssetType | ✅ | 资产类型 | `models/asset.py` |
| status | AssetStatus | ✅ | 生命周期状态 | `models/asset.py` |
| parent_id | str | <!-- 填写 --> | 父节点 | <!-- 填写 --> |
| prompt | str | ✅ | 生成用Prompt | <!-- 填写 --> |
| image_url | str | <!-- 填写 --> | 生成结果URL | <!-- 填写 --> |

### 4.3 约束 (Constraint)

| 字段 | 类型 | 必填 | 描述 | 代码位置 |
|------|------|------|------|---------|
| dimension | ConstraintDimension | ✅ | 6维之一 | `models/dimension.py` |
| level | ConstraintLevel | ✅ | CORE/MODULE/SCENARIO | <!-- 填写: 待创建枚举 --> |
| type | HARD/SOFT | ✅ | 硬约束/软约束 | `models/constraint.py` |
| priority | int | <!-- 填写 --> | 优先级 | <!-- 填写 --> |
| content | str | ✅ | 约束内容 | <!-- 填写 --> |

### 4.4 <!-- 补充更多实体 Schema -->

---

## 5. 关系语义规则

> **填写规则**: 关系不是随便连的——每条边都有语义。定义"什么能连什么"。

### 5.1 允许的关系

| 源类型 | 关系 | 目标类型 | 语义 | 示例 |
|--------|------|---------|------|------|
| Character | belongs_to | Faction | 角色属于势力 | 精灵王 → 银月议会 |
| Character | located_at | Location | 角色在地点 | 精灵王 → 黑暗森林 |
| Location | contains | Item | 地点包含物品 | 森林 → 水晶祭坛 |
| Character | owns | Item | 角色拥有物品 | 精灵王 → 王冠 |
| Event | involves | Character | 事件涉及角色 | 诸神黄昏 → 精灵王 |
| Culture | influences | Character | 文化影响角色 | 高地文化 → 精灵王 |
| <!-- 补充更多关系 --> | | | | |

### 5.2 禁止的关系

| 源类型 | 关系 | 目标类型 | 原因 |
|--------|------|---------|------|
| Item | belongs_to | Character | 应为 Character.owns Item（方向反了） |
| <!-- 补充 --> | | | |

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
