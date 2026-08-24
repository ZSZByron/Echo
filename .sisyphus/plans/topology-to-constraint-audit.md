# 拓扑 → 约束 完整链条审计

> **版本**: v0.2（基于正确文件路径重新审计）
> **日期**: 2026-08-14
> **审计对象**: `docs/plans/a1-topology-boundary-spec.md`（633行）
> **审计标准**: 每个节点名词、每条拓扑边，必须能追溯到具体的 Constraint，否则标记为悬空
> **结构**: 总（全景图）→ 分（逐条追踪）→ 总（汇总矩阵+问题清单）

---

## 0. 核心审计标准

每一条拓扑关系必须能回答：

```
源节点 —[边类型]→ 目标节点
  ↑                    ↑
  这个节点的什么属性     这条边表达的关系
  最终编译为哪条约束？   最终编译为哪条约束？
```

**如果一个节点或边无法追溯到任何 Constraint，它就是悬空的——要么补上约束链，要么标记为"纯结构节点无约束"。**

### 节点类型与约束的关系

| 节点类型 | 与约束的关系 | 说明 |
|---------|------------|------|
| **Concept** | 自身被 Constraint 限制 + 自身作为边的源/目标连接 Constraint | 概念节点是"被描述对象"，约束描述它的规则 |
| **Geography** | 被 Constraint 通过因果链边塑造 + 自身携带继承约束 | 地理是"被规则塑造的结果" |
| **Faction** | 被 Constraint(SOC) 约束行为 + 被 Constraint 限制能力 | 势力是"被社会规则约束的实体" |
| **Event** | 被 Constraint(NAR) 约束叙事走向 + 被 Constraint 限制因果 | 事件是"被叙事规则约束的节点" |
| **Constraint** | 自身就是约束 | 约束节点是"规则的具象化" |

**关键区分**：Concept 和 Constraint 不是同一层的东西。
- **Concept** = 世界上存在的抽象概念（力量体系、宇宙学、哲学——"是什么"）
- **Constraint** = 支配 Concept 运行的规则（"怎么运作"）

一个 Concept(POWER_SYSTEM) "元素魔法" 搭配多条 Constraint：
- `Constraint(LAW)`: 元素魔法遵循守恒律
- `Constraint(ACT)`: 使用需要 3d6 Roll-under 检定
- `Constraint(WST)`: 滥用导致肉体结晶化

---

## 1. 总图：全景拓扑 → 约束链

```
┌─────────────────────────────────────────────────────────────────┐
│                        第4套：世界观拓扑选择                      │
│  （设计师在溯源/载体/机制/代价/架构/法则/位面/纪元上的选择）       │
└──────────────────────────────┬──────────────────────────────────┘
                               │ 编译
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Concept 节点层（"是什么"）                   │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │Concept(       │  │Concept(       │  │Concept(              │   │
│  │ ORIGIN)       │  │ POWER_SYSTEM) │  │ COSMOLOGY)           │   │
│  │ 起源          │  │ 力量体系       │  │ 宇宙学                │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                 │                      │               │
│         │          ┌──────────────┐               │               │
│         │          │Concept(       │               │               │
│         └─────────→│ PHILOSOPHY)  │←──────────────┘               │
│                    │ 哲学思想       │                               │
│                    └──────┬───────┘                               │
│                           │                                       │
└───────────────────────────┼───────────────────────────────────────┘
                            │
                     ═══════╪═══════════
                     Concept 被这些约束支配：
                     ═══════╪═══════════
                            │
┌───────────────────────────┼───────────────────────────────────────┐
│                    Constraint 节点层（"怎么运作"）                 │
│                           │                                       │
│  ┌─────────────┐  ┌───────┴───────┐  ┌─────────────┐             │
│  │Constraint(   │  │Constraint(     │  │Constraint(   │             │
│  │ LAW)         │  │ ACT)           │  │ WST)         │             │
│  │ 物理法则      │  │ 行为规则        │  │ 世界状态      │             │
│  │              │  │                │  │              │             │
│  │·力量来源类型  │  │·骰子模式       │  │·代价类型      │             │
│  │·守恒/非守恒   │  │·判定方向       │  │·反馈回路      │             │
│  │·神权架构      │  │·核心行为       │  │·状态变更      │             │
│  │·生死规则      │  │                │  │              │             │
│  └──────┬──────┘  └───────┬───────┘  └──────┬──────┘             │
│         │                 │                  │                     │
│  ┌──────┴──────┐  ┌───────┴───────┐  ┌──────┴──────┐             │
│  │Constraint(   │  │Constraint(     │  │Constraint(   │             │
│  │ NAR)         │  │ SOC)           │  │ RED)         │             │
│  │ 叙事约束      │  │ 社交生态        │  │ 内容红线      │             │
│  │              │  │                │  │              │             │
│  │·基调/风格     │  │·政治类型       │  │·禁止清单      │             │
│  │·判定层次      │  │·阶层分化       │  │              │             │
│  │·转折机制      │  │·经济结构       │  │              │             │
│  │·哲学闭环      │  │·获取门槛       │  │              │             │
│  └──────┬──────┘  └───────┬───────┘  └──────┬──────┘             │
│         │                 │                  │                     │
└─────────┼─────────────────┼──────────────────┼─────────────────────┘
          │                 │                  │
          ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              拓扑边（约束如何连接到其他节点）                       │
│                                                                 │
│  Constraint ──RULE_SHAPES_GEO──→ Geography                      │
│  Concept    ──POWER_SATURATES_GEO──→ Geography                  │
│  Concept    ←─POWER_SOURCES_FROM_GEO── Geography                 │
│  Geography  ──GEO_CONTAINS──→ Geography                          │
│  Geography  ──GEO_BORDERS──→ Geography                           │
│  Geography  ──GEO_ABOVE──→ Geography                             │
│  Geography  ──GEO_BELOW──→ Geography                             │
│  Geography  ──GEO_SEPARATES──→ Faction                           │
│  Geography  ──GEO_NOURISHES──→ Faction                           │
│  Geography  ──GEO_HOSTS_EVENT──→ Event                           │
│  Faction    ──FACTION_OPPOSES──→ Faction                         │
│  Faction    ──FACTION_ALLIED──→ Faction                          │
│  Event      ──EVENT_CAUSED_BY──→ Event                           │
│  Concept    ──CONCEPT_MANIFESTS_AS──→ Geography                  │
│  Constraint ──CONSTRAINT_LIMITS──→ Faction/Concept/Geography     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 分：逐条追踪——节点 → 约束链

### 2.1 Concept(ORIGIN) 起源节点

**节点定义**：世界存在的根本起源，因果链的根（无 caused_by 上游）

| 属性 | 编译为 | 约束维度 | 约束内容 |
|------|--------|---------|---------|
| 起源类型（创世神话/虚空诞生/科学起源） | `Constraint(LAW, CORE)` | LAW | "世界的根本起源法则"——决定能量流动方向 |
| 起源时间线原点 | 编译为 Event 图时间轴起点 | — | 非 Constraint，是 Event 拓扑结构 |

**约束链**：

```
设计师选择"起源=虚空诞生"
  ↓ 编译
Constraint(LAW, CORE):
  content: "世界从虚空中诞生"
  energy_flow: BOTTOM_UP    ← 能量从环境到个体（内聚流）
  resource_type: FINITE      ← 虚空能量是有限资源
  ↓ 影响
  ├→ Constraint(ACT): 力量获取=环境汲取模式（非天赋）
  ├→ Constraint(NAR): 剧情开端=虚空异变/入侵（非神谕）
  └→ POWER_SOURCES_FROM_GEO 边: Geography(虚空裂隙) → Concept(POWER_SYSTEM)
```

**与其他节点的关系**：

| 边类型 | 方向 | 目标节点 | 约束归途 |
|--------|------|---------|---------|
| 因果链（隐式） | ORIGIN → POWER_SYSTEM | Concept | Constraint(LAW): 起源决定力量来源类型 |
| 因果链（隐式） | ORIGIN → PHILOSOPHY | Concept | Constraint(NAR): 起源预示世界走向 |
| `POWER_SOURCES_FROM_GEO` | Geography → POWER_SYSTEM | Concept+Geography | Constraint(LAW): 能量流动方向 |

---

### 2.2 Concept(POWER_SYSTEM) 力量体系节点

**节点定义**：力量的根本来源和运作方式

| 属性 | 编译为 | 约束维度 | 约束内容 |
|------|--------|---------|---------|
| source_type（意识体/物理/特殊环境/科技） | `Constraint(LAW)` | LAW | 力量本体定义——力量是什么 |
| 能量流动方向（自上而下/内聚） | `Constraint(LAW)` | LAW | 力量是有限资源还是无限资源 |
| 获取拓扑（封闭/开放） | `Constraint(SOC)` | SOC | 谁能使用力量——阶层分化 |
| 交互拓扑（守恒/非守恒） | `Constraint(LAW)` | LAW | 力量如何改变现实 |
| 排他性（互斥规则对） | `Constraint(LAW)` | LAW | 科技vs魔法是否互斥 |
| 代价类型（物理/精神） | `Constraint(WST)` | WST | 滥用力量的反噬 |
| 骰子模式（固定骰/骰池） | `Constraint(ACT)` | ACT | 力量使用的检定方式 |
| 判定方向（Roll-under/over） | `Constraint(ACT)` | ACT | 力量检定的判定方向 |

**约束链（4维拓扑全部编译为约束）**：

```
力量体系4维拓扑选择                    编译为约束
─────────────────                    ─────────

【溯源维度】
  能量来源=环境汲取            →  Constraint(LAW): power_source=ENVIRONMENTAL
  资源类型=有限                 →  Constraint(LAW): resource_type=FINITE
  流动方向=环境→个体             →  Constraint(LAW): energy_flow=BOTTOM_UP

【载体维度】
  获取方式=精英学习/觉醒         →  Constraint(SOC): access_topology=CLOSED
  门槛=高                       →  Constraint(SOC): threshold=HIGH
  物种分布差异                   →  Constraint(SOC): species_distribution=UNEQUAL

【机制维度】
  交互法则=等价交换              →  Constraint(LAW): interaction=CONSERVATION
  守恒律                        →  Constraint(LAW): conservation=TRUE
  排他性=科技vs魔法互斥          →  Constraint(LAW): exclusivity_pair=[TECH, MAGIC]

【代价维度】
  代价类型=肉体损耗              →  Constraint(WST): cost_type=PHYSICAL
  反馈回路=变异/非人化            →  Constraint(WST): feedback=MUTATION
  承载vs操作关系                 →  Constraint(ACT): cost_function=CAPACITY_DIFF
```

**拓扑边归途**：

| 边类型 | 角色 | 连接到 | 约束归途 |
|--------|------|--------|---------|
| `POWER_SATURATES_GEO` | 源 | → Geography | Constraint(LAW): 力量在空间上的分布不均→高魔区vs低魔区 |
| `POWER_SOURCES_FROM_GEO` | 目标 | ← Geography | Constraint(LAW): 力量源于地理→地脉/裂隙是高势能节点 |
| `CONCEPT_MANIFESTS_AS` | 源 | → Geography | Constraint(LAW): 抽象力量具现为地理实体→灵脉网络 |
| `CONSTRAINT_LIMITS` | 目标 | ← Constraint | Constraint(SOC): 力量获取门槛限制谁能使用 |

---

### 2.3 Concept(COSMOLOGY) 宇宙学节点

**节点定义**：世界的多世界结构、位面拓扑、连通性

| 属性 | 编译为 | 约束维度 | 约束内容 |
|------|--------|---------|---------|
| 结构形态（浮岛/同心球/世界树/星球） | `Constraint(LAW)` | LAW | 世界物理形态——决定 Geography 的 vertical_layer 枚举 |
| 边界（有限/无限，内/外） | `Constraint(LAW, CORE)` | LAW | 世界边界的不可逾越性 |
| 位面拓扑（连通性/渗透性） | `Constraint(LAW)` | LAW | 跨界旅行路径的可行性和方式 |
| 传送门机制 | `Constraint(ACT)` | ACT | 跨界行为如何判定 |
| 位面共振（区域锚定） | `Constraint(WST)` | WST | 共振区的状态效果（高魔浓度/元素侵蚀） |

**约束链**：

```
宇宙学选择                              编译为约束
────────                              ─────────

结构形态=浮岛群                →  Constraint(LAW): world_structure=FLOATING_ISLANDS
                                    → Geography.vertical_layer 枚举范围被锁定
边界=不可逾越虚空               →  Constraint(LAW, CORE): boundary=VOID_IMPASSABLE
位面连接=与元素位面有裂缝         →  Constraint(LAW): planar_connectivity=FRACTURE
传送门=天然裂缝                 →  Constraint(ACT): cross_planar_check=RESISTANCE_ROLL
共振=火山岛锚定火元素位面        →  Constraint(WST): resonance_effect=FIRE_SATURATION
```

**拓扑边归途**：

| 边类型 | 角色 | 连接到 | 约束归途 |
|--------|------|--------|---------|
| `CONCEPT_MANIFESTS_AS` | 源 | → Geography | Constraint(LAW): 宇宙学结构具现为地理（位面裂缝→裂隙节点） |
| `GEO_BORDERS`（跨位面） | 隐式 | Geography ↔ Geography | Constraint(LAW): 位面连通性决定跨界路径 |

---

### 2.4 Concept(PHILOSOPHY) 哲学思想节点

**节点定义**：世界存在的目的与归宿，预示世界走向

| 属性 | 编译为 | 约束维度 | 约束内容 |
|------|--------|---------|---------|
| era_stage（初生/暮年） | Concept 属性 + `Constraint(NAR)` | NAR | 时代基调——影响所有叙事描述的风格 |
| time_mode（线性/循环/断裂） | Concept 属性 + `Constraint(NAR)` | NAR | Event 因果链的拓扑形态（链/环/断裂） |
| trajectory（进步/衰退/循环） | Concept 属性 + `Constraint(NAR)` | NAR | 剧情结局的约束——必须验证或挑战哲学 |
| 哲学思想（善恶二元/虚无主义/精英统治...） | `Constraint(NAR, CORE)` | NAR | 叙事走向的终极约束 |

**约束链**：

```
哲学选择                              编译为约束
────────                              ─────────

创世阶段=暮年                   →  Constraint(NAR): era_stage=TWILIGHT
                                    → 所有叙事描述基调=压抑/衰败
时间模式=线性                    →  Constraint(NAR): time_mode=LINEAR
                                    → Event 因果链=有向无环图（非环形）
走向=衰退                       →  Constraint(NAR): trajectory=COLLAPSE
                                    → Event 链呈现熵增（逐步衰败）
哲学=善恶二元                    →  Constraint(NAR, CORE): philosophy=DUALISM
                                    → 剧情时间线=善与恶的拉锯战
                                    → 结局必须验证善恶二元论
哲学=虚无主义                    →  Constraint(NAR, CORE): philosophy=NIHILISM
                                    → 剧情结局=不可避免的衰败
哲学=循环论                     →  Constraint(NAR, CORE): philosophy=CYCLE
                                    → 剧情结局=新的轮回开始
                                    → Event 因果链=环形拓扑
```

**拓扑边归途**：

| 边类型 | 角色 | 连接到 | 约束归途 |
|--------|------|--------|---------|
| 因果链（隐式） | PHILOSOPHY → Event 终点 | Event | Constraint(NAR, CORE): 哲学=结局约束 |
| 因果链（隐式） | PHILOSOPHY → PHILOSOPHY（闭环） | 自身 | Constraint(NAR): 循环哲学→Event 环形拓扑 |

---

### 2.5 Concept(OTHER) 其他存在节点

**节点定义**：不属3类但有影响的生灵、规则、物质、存在

| 属性 | 编译为 | 约束维度 | 约束内容 |
|------|--------|---------|---------|
| 存在物类型（特殊生物/规则实体/物质） | `Constraint(LAW)` 或 `Constraint(WST)` | 视类型 | 定制约束 |
| 影响范围 | `Constraint(LAW)` | LAW | 这些存在如何影响世界规则 |

**约束链**：

```
其他存在选择                           编译为约束
───────────                           ─────────

特殊生物（如龙/古神）            →  Constraint(LAW): entity_type=ANCIENT_BEING
                                    → Constraint(SOC): 存在物差异导致力量分布不均
                                    → CONCEPT_MANIFESTS_AS: 龙脉→龙骨山脉

特殊规则（如诅咒/宿命）          →  Constraint(LAW): rule_type=CURSE
                                    → CONSTRAINT_LIMITS: 诅咒限制特定实体

特殊物质（如魔晶/虚空石）        →  Constraint(WST): material_type=MAGIC_CRYSTAL
                                    → POWER_SOURCES_FROM_GEO: 魔晶矿→力量体系
```

---

### 2.6 Geography 地理节点

**节点定义**：世界的地理结构单元，由世界规则和力量体系编译推导

| 属性 | 编译为 | 约束维度 | 约束内容 |
|------|--------|---------|---------|
| geo_type（大陆/海洋/山脉/地下/天空层...） | 节点属性 | — | 纯结构标签，无直接约束 |
| vertical_layer（SKY/SURFACE/UNDERGROUND/DEEP） | 节点属性 | — | 纯结构标签，用于 GEO_ABOVE/BELOW 边 |
| shaping_rules | 引用 Constraint ID | — | 指向塑造此地理的 Constraint 节点 |
| power_sources | 引用 Concept ID | — | 指向渗透此地理的力量源 Concept 节点 |
| climate_zone | 节点属性 → `Constraint(WST)` | WST | 气候=世界状态效果（影响环境修正） |
| narrative_role（主线舞台/后勤区/探索区/禁区） | 节点属性 → `Constraint(NAR)` | NAR | 叙事权重——影响剧情分配 |
| 法则同调程度（高魔/低魔/破碎区） | 节点属性 → `Constraint(WST)` | WST | 力量浓度=状态效果区域 |

**约束链——Geography 是"被约束塑造的结果"**：

```
Geography 本身不产生约束，它被以下约束塑造：

Constraint(LAW) ──RULE_SHAPES_GEO──→ Geography
  "高重力"塑造了"扁平大陆"

Concept(POWER_SYSTEM) ──POWER_SATURATES_GEO──→ Geography
  "元素魔法"渗透了"元素浓度带"

Concept(COSMOLOGY) ──CONCEPT_MANIFESTS_AS──→ Geography
  "位面裂缝"具现为"虚空裂隙"

Geography ←──POWER_SOURCES_FROM_GEO── Concept(POWER_SYSTEM)
  "地脉山脉"是"灵脉力量"的来源
```

**拓扑边归途**：

| 边类型 | 角色 | 连接到 | 约束归途 |
|--------|------|--------|---------|
| `GEO_CONTAINS` | 源/目标 | → Geography | 纯结构拓扑——无直接约束，但约束沿此边**继承传递** |
| `GEO_BORDERS` | 源/目标 | → Geography | 纯结构拓扑——无直接约束，但 Constraint(LAW) 位面连通性影响此边语义 |
| `GEO_ABOVE` | 源 | → Geography | 纯结构拓扑——由 Constraint(LAW) world_structure 决定哪些垂直层级存在 |
| `GEO_BELOW` | 源 | → Geography | 同上 |
| `GEO_SEPARATES` | 源 | → Faction | Constraint(LAW): 地理隔离影响势力关系（物理屏障） |
| `GEO_NOURISHES` | 源 | → Faction | Constraint(WST): 地理滋养影响势力资源（经济状态） |
| `GEO_HOSTS_EVENT` | 源 | → Event | Constraint(NAR): 地理承载事件→事件锚定到拓扑敏感点 |

---

### 2.7 Faction 势力节点

**节点定义**：势力/组织，由力量来源差异导致政治文化不同

| 属性 | 编译为 | 约束维度 | 约束内容 |
|------|--------|---------|---------|
| ideology（核心意识形态） | 节点属性 → `Constraint(SOC)` | SOC | 势力行为逻辑根 |
| power_tier（MAJOR/MINOR/FRINGE） | 节点属性 | — | 纯结构标签 |
| origin_type（原生/次生/边缘文明） | 节点属性 → `Constraint(SOC)` | SOC | 文明等级关系 |
| territory_geo_ids | 引用 Geography ID | — | 通过 GEO_NOURISHES 边关联 |
| 政治类型 | `Constraint(SOC, CORE)` | SOC | 与力量获取拓扑一致 |
| 经济结构 | `Constraint(SOC)` | SOC | 经济=力量体系的物质化映射 |

**约束链**：

```
势力被以下约束支配：

Constraint(SOC, CORE): 政治类型=寡头制（与封闭获取拓扑一致）
Constraint(SOC): 经济结构=魔化矿产主导（力量体系的物质化）
Constraint(SOC): 力量获取门槛=高（封闭拓扑→精英掌握力量）

势力通过拓扑边连接到其他节点：

Geography ──GEO_NOURISHES──→ Faction
  富饶平原滋养了强国 → Constraint(WST): 资源状态

Geography ──GEO_SEPARATES──→ Faction
  山脉隔离了两个势力 → Constraint(LAW): 物理屏障影响势力扩张

Constraint ──CONSTRAINT_LIMITS──→ Faction
  "禁用火魔法"限制了某势力 → Constraint(RED/LAW): 能力限制
```

**拓扑边归途**：

| 边类型 | 角色 | 连接到 | 约束归途 |
|--------|------|--------|---------|
| `FACTION_OPPOSES` | 源 | → Faction | Constraint(SOC): 势力对立——冲突类型决定约束 |
| `FACTION_ALLIED` | 源 | → Faction | Constraint(SOC): 势力联盟——影响声望/关系网络 |
| `GEO_NOURISHES` | 目标 | ← Geography | Constraint(WST): 资源滋养→势力经济状态 |
| `GEO_SEPARATES` | 目标 | ← Geography | Constraint(LAW): 地理屏障→势力扩张限制 |
| `CONSTRAINT_LIMITS` | 目标 | ← Constraint | Constraint(RED/LAW): 能力/行为限制 |

**FACTION_OPPOSES 的冲突类型→约束映射**：

| 冲突类型 | 编译为约束 | 约束维度 |
|---------|-----------|---------|
| 资源争端 | Constraint(WST): 争夺同一资源源 | WST |
| 信仰争端 | Constraint(SOC): 信仰体系互斥 | SOC |
| 种族争端 | Constraint(SOC): 存在物差异→物种对立 | SOC |
| 文化争端 | → A2 CULTURE_INFLUENCES（A1 只锁阵营对立） | SOC |
| 权利争端 | Constraint(SOC): 直接权力对立 | SOC |
| 特殊争端 | Constraint(LAW): 世界观特殊规则导致 | LAW |

---

### 2.8 Event 事件节点

**节点定义**：历史关键节点，因果链的组成单元

| 属性 | 编译为 | 约束维度 | 约束内容 |
|------|--------|---------|---------|
| era（所属历史时期） | 节点属性 | — | 纯结构标签——时间轴定位 |
| severity（COSMIC/MAJOR/REGIONAL/MINOR） | 节点属性 → `Constraint(NAR)` | NAR | 叙事权重——影响剧情分配 |
| location_geo_id | 引用 Geography ID | — | 通过 GEO_HOSTS_EVENT 边关联 |
| involved_faction_ids | 引用 Faction ID | — | 通过 FACTION_OPPOSES/ALLIED 间接关联 |
| caused_by_event_id | 引用 Event ID | — | 通过 EVENT_CAUSED_BY 边关联 |

**约束链——Event 是"被叙事约束驱动的因果节点"**：

```
Event 被 Constraint(NAR) 支配：

主剧情4维映射编译为约束：

【驱动维度·起源回响】
  起源=虚空诞生 → 剧情开端=虚空异变
    → Constraint(NAR): plot_trigger=VOID_INCURSION

  意志主导 → 转折靠信念/牺牲
    → Constraint(NAR): turning_point=WILLPOWER_BASED

  物质主导 → 转折靠资源/科技
    → Constraint(NAR): turning_point=RESOURCE_BASED

【代理维度·意志载体】
  主角=存在物极端样本
    → Constraint(SOC): protagonist_type=ENTITY_EXTREME

  势力强弱=力量体系分布
    → Constraint(SOC): power_distribution=MAPPED_TO_TOPOLOGY

【舞台维度·空间映射】
  决战=拓扑敏感点
    → Constraint(NAR): climax_location=TOPOLOGY_NODE

  地图现状=剧情投影
    → Constraint(LAW): geography_anomaly=HISTORICAL_TRAUMA

【归宿维度·哲学闭环】
  结局验证/挑战哲学
    → Constraint(NAR, CORE): ending_constraint=MUST_VALIDATE_PHILOSOPHY

  循环论 → 新轮回开始
    → Event 因果链=环形拓扑

  虚无主义 → 不可避免衰败
    → Event 因果链=熵增链
```

**拓扑边归途**：

| 边类型 | 角色 | 连接到 | 约束归途 |
|--------|------|--------|---------|
| `EVENT_CAUSED_BY` | 源 | → Event | Constraint(NAR): 因果链拓扑形态由哲学决定（链/环/断裂） |
| `GEO_HOSTS_EVENT` | 目标 | ← Geography | Constraint(NAR): 事件锚定到拓扑敏感点 |

---

### 2.9 Constraint 约束节点（自身就是约束）

**节点定义**：规则的具象化，不需要追溯——自身就是终点

| Constraint 类型 | 来源 | 覆盖内容 |
|----------------|------|---------|
| Constraint(LAW) | 模块②世界本体 + 模块③力量体系 + 模块⑩骰子 | 物理法则/力量来源/守恒律/神权/生死/骰子分布 |
| Constraint(ACT) | 模块③力量体系 + 模块⑧玩法DNA + 模块⑩骰子 | 获取方式/骰子模式/判定方向/核心行为 |
| Constraint(NAR) | 模块⑥历史时间线 + 模块⑩骰子 | 叙事走向/基调/判定层次/转折机制/哲学闭环 |
| Constraint(WST) | 模块③力量体系 + 模块④地理空间 + 模块⑩骰子 | 代价机制/气候状态/力量浓度/资源状态 |
| Constraint(SOC) | 模块⑤文明社会 + 模块③力量体系 | 政治类型/阶层分化/经济结构/获取门槛/势力关系 |
| Constraint(RED) | 模块⑨AI生成边界 | 内容红线/禁止清单 |

---

## 3. 分：逐条追踪——15种边 → 约束链

### 第1类：地理层内部关系（Geography ↔ Geography）

#### 3.1 `GEO_CONTAINS` — 层级包含

```
Geography(大陆) ──GEO_CONTAINS──→ Geography(区域)
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | A1+ |
| 约束归途 | **纯结构边——无直接约束，但约束沿此边继承传递** |
| 继承机制 | ≥10%权重→完整传递 / 5-10%→压缩摘要 / <5%→不传递 |
| 间接约束 | Constraint 沿 GEO_CONTAINS 从父地理→子地理传递 |

**链条**：

```
Constraint(LAW): "高重力" ──RULE_SHAPES_GEO──→ Geography(大陆)
  ↓ GEO_CONTAINS 继承
Geography(大陆) ──GEO_CONTAINS──→ Geography(区域)
  ↓ Constraint 继承传递（按权重）
Geography(区域) 继承 Constraint(LAW) 的摘要或完整版本
```

#### 3.2 `GEO_BORDERS` — 水平邻接

```
Geography(海洋) ──GEO_BORDERS──→ Geography(大陆)
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | A1+ |
| 约束归途 | Constraint(LAW): 位面连通性/海陆分布影响此边的语义密度 |
| 间接约束 | Constraint(LAW): 孤岛=低连通性→文化独特但经济落后 |

#### 3.3 `GEO_ABOVE` — 垂直上层（仅A1）

```
Geography(SKY_LAYER) ──GEO_ABOVE──→ Geography(SURFACE)
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | 仅A1 |
| 约束归途 | Constraint(LAW, CORE): world_structure 决定哪些垂直层级存在 |
| 间接约束 | Constraint(LAW): 天空层=高位面→力量势能高节点 |

**链条**：

```
设计师选择"架构维度: 浮岛群+天空层"
  ↓ 编译
Constraint(LAW, CORE): world_structure=FLOATING_ISLANDS
  ↓ 决定
Geography.vertical_layer 枚举范围 = [SKY, SURFACE, UNDERGROUND]
  ↓ 建边
Geography(SKY) ──GEO_ABOVE──→ Geography(SURFACE)
  ↑ 这条边是 Constraint(LAW) world_structure 的空间投影
```

#### 3.4 `GEO_BELOW` — 垂直下层（仅A1）

```
Geography(UNDERGROUND) ──GEO_BELOW──→ Geography(SURFACE)
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | 仅A1 |
| 约束归途 | Constraint(LAW, CORE): world_structure 决定地下层存在 |
| 间接约束 | Constraint(LAW): 地下世界=低位面→可能连接不同位面 |

---

### 第2类：规则/力量 → 地理（因果链，A1独有）

#### 3.5 `RULE_SHAPES_GEO` — 物理法则塑造地形（仅A1）

```
Constraint(LAW): "高重力" ──RULE_SHAPES_GEO──→ Geography: "扁平大陆"
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | 仅A1 |
| 约束归途 | **源节点自身就是 Constraint** |
| 链条完整性 | ✅ 源=Constraint，目标=Geography，因果关系完整 |

#### 3.6 `POWER_SATURATES_GEO` — 力量体系渗透地理（仅A1）

```
Concept(POWER_SYSTEM): "元素魔法" ──POWER_SATURATES_GEO──→ Geography: "元素浓度带"
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | 仅A1 |
| 约束归途 | **源=Concept，但 Concept 被 Constraint(LAW) 支配** |
| 链条 | Concept(POWER_SYSTEM) ←支配— Constraint(LAW): 力量分布=空间不均 |

**链条**：

```
Constraint(LAW): interaction=CONSERVATION （机制维度：守恒律）
  ↓ 支配
Concept(POWER_SYSTEM): "元素魔法"
  ↓ POWER_SATURATES_GEO 边
Geography: "元素浓度带"（高魔区=高势能节点）
  ↓ 影响
Constraint(WST): 该区域 fire_saturation=HIGH（世界状态效果）
```

#### 3.7 `POWER_SOURCES_FROM_GEO` — 力量源于地理（仅A1）

```
Concept(POWER_SYSTEM): "灵脉" ←──POWER_SOURCES_FROM_GEO── Geography: "山脉地脉"
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | 仅A1 |
| 约束归途 | **源=Geography，目标=Concept，Concept 被 Constraint(LAW) 支配** |
| 链条 | Constraint(LAW): power_source_type=ENVIRONMENTAL |

**链条**：

```
Constraint(LAW): power_source_type=ENVIRONMENTAL （溯源维度：环境汲取）
  ↓ 支配
Concept(POWER_SYSTEM): "灵脉"
  ↑ POWER_SOURCES_FROM_GEO 边
Geography: "山脉地脉"（力量源=高势能节点）
  ↓ 影响
所有在此 Geography 范围内的实体 → Constraint(ACT): 力量获取模式=环境汲取
```

---

### 第3类：地理 → 势力/事件（跨层投影）

#### 3.8 `GEO_SEPARATES` — 地理隔离

```
Geography: "山脉" ──GEO_SEPARATES──→ Faction A / Faction B
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | A1+ |
| 约束归途 | Constraint(LAW): 地理屏障限制势力扩张 |
| 链条 | 地理拓扑 → Constraint(LAW) 物理屏障 → Constraint(SOC) 势力关系受限 |

#### 3.9 `GEO_NOURISHES` — 地理滋养

```
Geography: "富饶平原" ──GEO_NOURISHES──→ Faction: "强国"
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | A1+ |
| 约束归途 | Constraint(WST): 资源状态→势力经济基础 |
| 链条 | 地理资源 → Constraint(WST) 资源修正值 → Constraint(SOC) 经济结构 |

#### 3.10 `GEO_HOSTS_EVENT` — 地理承载事件

```
Geography: "虚空裂隙" ──GEO_HOSTS_EVENT──→ Event: "大分裂"
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | A1+ |
| 约束归途 | Constraint(NAR): 事件锚定到拓扑敏感点 |
| 链条 | Constraint(NAR): climax_location=TOPOLOGY_NODE → 事件必须发生在拓扑敏感点 |

---

### 第4类：势力/事件/概念层内部关系

#### 3.11 `FACTION_OPPOSES` — 势力对立

```
Faction A ──FACTION_OPPOSES──→ Faction B
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | A1+ |
| 约束归途 | Constraint(SOC): 势力对立关系 |
| 链条 | 对立类型 → Constraint(SOC) 内容（资源/信仰/种族/权力/特殊） |

#### 3.12 `FACTION_ALLIED` — 势力联盟

```
Faction A ──FACTION_ALLIED──→ Faction B
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | A1+ |
| 约束归途 | Constraint(SOC): 势力联盟关系 |
| 链条 | 联盟 → Constraint(SOC) 声望/关系网络修正 |

#### 3.13 `EVENT_CAUSED_BY` — 事件因果链

```
Event: "大分裂" ──EVENT_CAUSED_BY──→ Event: "神战余波"
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | A1+ |
| 约束归途 | Constraint(NAR): 因果链拓扑形态 |
| 链条 | Constraint(NAR): time_mode 决定链形态（LINEAR→有向无环 / CYCLE→环形 / FRACTURE→断裂） |

#### 3.14 `CONCEPT_MANIFESTS_AS` — 概念具现（仅A1）

```
Concept(COSMOLOGY): "位面裂缝" ──CONCEPT_MANIFESTS_AS──→ Geography: "虚空裂隙"
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | 仅A1 |
| 约束归途 | Constraint(LAW): 抽象概念→物理实体映射 |
| 链条 | Constraint(LAW): planar_connectivity → Concept(COSMOLOGY) → CONCEPT_MANIFESTS_AS → Geography |

#### 3.15 `CONSTRAINT_LIMITS` — 约束限制实体

```
Constraint(RED): "禁用火魔法" ──CONSTRAINT_LIMITS──→ Faction: "水之国"
```

| 维度 | 内容 |
|------|------|
| 可建阶段 | A1+ |
| 约束归途 | **源节点自身就是 Constraint** |
| 链条完整性 | ✅ 源=Constraint，直接限制目标实体的能力/行为 |

---

## 4. 总：汇总矩阵——所有边 → 约束归途

| # | 边类型 | 源节点 | 目标节点 | 可建阶段 | 约束归途 | 链条完整性 |
|---|--------|--------|---------|---------|---------|-----------|
| 1 | `GEO_CONTAINS` | Geography | Geography | A1+ | 纯结构——约束沿此边继承传递 | ✅ 间接约束（继承） |
| 2 | `GEO_BORDERS` | Geography | Geography | A1+ | Constraint(LAW): 位面连通性密度 | ✅ 间接约束 |
| 3 | `GEO_ABOVE` | Geography | Geography | 仅A1 | Constraint(LAW): world_structure 空间投影 | ✅ 间接约束 |
| 4 | `GEO_BELOW` | Geography | Geography | 仅A1 | Constraint(LAW): world_structure 空间投影 | ✅ 间接约束 |
| 5 | `RULE_SHAPES_GEO` | **Constraint** | Geography | 仅A1 | **源=Constraint 自身** | ✅ 直接约束 |
| 6 | `POWER_SATURATES_GEO` | Concept | Geography | 仅A1 | Constraint(LAW): 力量空间分布不均 | ✅ 间接约束（经Concept） |
| 7 | `POWER_SOURCES_FROM_GEO` | Geography | Concept | 仅A1 | Constraint(LAW): power_source_type=ENVIRONMENTAL | ✅ 间接约束（经Concept） |
| 8 | `GEO_SEPARATES` | Geography | Faction | A1+ | Constraint(LAW): 物理屏障 + Constraint(SOC): 势力扩张受限 | ✅ 跨层约束 |
| 9 | `GEO_NOURISHES` | Geography | Faction | A1+ | Constraint(WST): 资源状态 + Constraint(SOC): 经济结构 | ✅ 跨层约束 |
| 10 | `GEO_HOSTS_EVENT` | Geography | Event | A1+ | Constraint(NAR): 事件锚定拓扑敏感点 | ✅ 跨层约束 |
| 11 | `FACTION_OPPOSES` | Faction | Faction | A1+ | Constraint(SOC): 对立关系（冲突类型决定） | ✅ 直接约束 |
| 12 | `FACTION_ALLIED` | Faction | Faction | A1+ | Constraint(SOC): 联盟关系 | ✅ 直接约束 |
| 13 | `EVENT_CAUSED_BY` | Event | Event | A1+ | Constraint(NAR): 因果链拓扑形态 | ✅ 直接约束 |
| 14 | `CONCEPT_MANIFESTS_AS` | Concept | Geography | 仅A1 | Constraint(LAW): 概念→实体映射 | ✅ 间接约束（经Concept） |
| 15 | `CONSTRAINT_LIMITS` | **Constraint** | Faction/Concept/Geo | A1+ | **源=Constraint 自身** | ✅ 直接约束 |

---

## 5. 审计结论

### 5.1 所有边的约束归途状态

```
15种边类型的约束归途：
  ├─ 直接约束（源=Constraint自身）          : 2种 ✅  (RULE_SHAPES_GEO, CONSTRAINT_LIMITS)
  ├─ 间接约束（经Concept→Constraint）        : 3种 ✅  (POWER_SATURATES, POWER_SOURCES, CONCEPT_MANIFESTS)
  ├─ 直接约束（边语义=Constraint内容）       : 3种 ✅  (FACTION_OPPOSES, ALLIED, EVENT_CAUSED_BY)
  ├─ 跨层约束（地理→势力/事件）              : 3种 ✅  (GEO_SEPARATES, NOURISHES, HOSTS_EVENT)
  └─ 纯结构边（约束沿边继承传递）            : 4种 ✅  (GEO_CONTAINS, BORDERS, ABOVE, BELOW)

总计：15/15 全部可追溯到约束 ✅
```

### 5.2 发现的问题

| 问题 | 严重度 | 说明 |
|------|--------|------|
| Concept 与 Constraint 的区分 | ⚠️ 设计注意 | Concept=存在物（"是什么"），Constraint=规则（"怎么运作"）。同一个力量体系，Concept 节点描述它是什么，多条 Constraint 节点描述它怎么运作。**不可混为一谈。** |
| 纯结构边的约束传递依赖权重 | ⚠️ 设计注意 | GEO_CONTAINS / GEO_BORDERS / GEO_ABOVE / GEO_BELOW 自身不携带约束，约束沿这些边继承传递。**如果继承机制未实现（断点F），这些边就是悬空的。** |
| Concept(OTHER) 的约束编译 | ⚠️ 设计注意 | "其他存在"类型高度定制化，约束编译路径不固定。**需要在问卷时逐项确认编译目标。** |

### 5.3 核心发现

> **所有 15 种边最终都能追溯到 Constraint 约束。追溯路径有三种：**
>
> 1. **直接追溯**（5种）：边的源节点就是 Constraint，或边语义直接等于 Constraint 内容
> 2. **间接追溯**（3种）：边经 Concept 节点中转，Concept 被 Constraint 支配
> 3. **继承追溯**（4种）：纯结构边自身无约束，但约束沿边继承传递
> 4. **跨层追溯**（3种）：地理→势力/事件的边，约束通过跨层映射编译

---

---

## 6. v0.2 补充审计（基于正确文件路径 `docs/plans/a1-topology-boundary-spec.md` 633行）

### 6.1 新增问题（v0.2发现）

| # | 问题 | 规格书行号 | 严重度 | 说明 |
|---|------|-----------|--------|------|
| **1** | **Concept(PHILOSOPHY) 缺约束维度标注** | §2.2.1 第107行 | ❌ 高 | 原文"编译为 Constraint(CORE) 约束所有下游"——缺约束维度。应补为 `Constraint(NAR, CORE)`（从第247-248行和术语表第595行可推断） |
| **2** | **视觉设计→地理/势力拓扑悬空** | §2.7.2 第377-379行 | ⚠️ 中 | 连接列="—"（空），只在 NAR Prompt 文本层面影响，没有标准边类型连接 |
| **3** | **GameplayAnchor 不是 Constraint 节点** | §2.8.1 第398-400行 | ⚠️ 中 | 玩家身份/成长方式存储在 GameplayAnchor 中，不直接参与拓扑约束，通过权重矩阵间接影响 |
| **4** | **POWER_SOURCES_FROM_GEO 方向反常** | §2.4.2 第233行 | ⚠️ 低 | 其他因果链边是 源→目标，此边是 Geography→Concept（力量源于地理），方向是设计意图但需代码标注 |
| **5** | **Concept(COSMOLOGY).attributes.structure 不是 Constraint** | §2.4.3 第239行 | ℹ️ 低 | 是 Concept 自身属性，间接决定 Geography 枚举范围，不是直接 Constraint |
| **6** | **WorldSchema.concept/world_type 不是 Constraint** | §2.1.1 第76-77行 | ℹ️ 低 | 是元数据根，影响权重矩阵初始偏移，不是 Constraint 节点 |

### 6.2 精确行号索引（v0.2新增）

**15种边在规格书中的全部出现位置**：

| 边类型 | 出现行号 |
|--------|---------|
| `GEO_CONTAINS` | 227, 244, 245, 461 |
| `GEO_BORDERS` | 228, 244, 261, 271 |
| `GEO_ABOVE` | 229, 449 |
| `GEO_BELOW` | 230, 449 |
| `RULE_SHAPES_GEO` | 116, 231, 280, 346, 604 |
| `POWER_SATURATES_GEO` | 117, 161, 232, 246, 265, 281, 604 |
| `POWER_SOURCES_FROM_GEO` | 118, 158, 160, 233, 241, 281, 599 |
| `GEO_SEPARATES` | （来自边类型词典§5.2） |
| `GEO_NOURISHES` | 294, 303 |
| `GEO_HOSTS_EVENT` | 331, 345 |
| `FACTION_OPPOSES` | 93, 263, 297, 302-308, 606 |
| `FACTION_ALLIED` | 263, 297, 606 |
| `EVENT_CAUSED_BY` | 333, 334, 356, 453, 608 |
| `CONCEPT_MANIFESTS_AS` | 118, 170, 305, 333, 604 |
| `CONSTRAINT_LIMITS` | 293, 304, 308 |

---

**文档版本**: v0.2
**最后更新**: 2026-08-14
**审计状态**: 15/15 边全部可追溯 ✅ | 1个必须修复 + 5个需确认 + 3个设计提醒
