# A模块层级图（含断点）

> **格式说明**: 缩进树格式，可直接导入 Xmind（每级缩进 = 子节点）
> - ✅ = 已实现/已设计连接
> - ❌ = 断点（独立节点）
> - 📦 = 数据容器/产物
> - ⚙️ = 处理引擎/模块

---

## A模块完整层级树

```
A模块：世界观IP设计 → 约束 → 生成 完整管线
│
├── 第4套：世界观拓扑维度（设计师输入层）
│   ├── IP定位
│   │   ├── 名称
│   │   ├── 概念（哲学+剧情+冲突）
│   │   ├── 类型（力量+物质+哲学）
│   │   └── 核心体验（主要行为+目标）
│   ├── 世界本体
│   │   ├── 来源（起源力量/起源时间线）
│   │   ├── 存在物
│   │   │   ├── 力量体系
│   │   │   ├── 宇宙学
│   │   │   ├── 哲学思想
│   │   │   └── 其他
│   │   └── 现实规则（意志主导/物质主导）
│   ├── 力量体系·4维拓扑
│   │   ├── 溯源维度（能量来源：有限↔无限）
│   │   │   ├── 力量本体定义（意识体/物理/特殊环境/科技）
│   │   │   ├── 力量来源底层（意志/物质）
│   │   │   └── 能量流动拓扑（自上而下/内聚）
│   │   ├── 载体维度（阶层分化：封闭↔开放）
│   │   │   ├── 力量获取方式（学习/觉醒/仪式/科研）
│   │   │   ├── 获取拓扑（封闭精英/开放众生）
│   │   │   └── 存在物差异→力量分布
│   │   ├── 机制维度（交互法则：守恒↔非守恒）
│   │   │   ├── 交互拓扑（等价交换/唯心投射）
│   │   │   └── 排他性（科技vs魔法互斥）
│   │   └── 代价维度（平衡约束：肉体↔精神）
│   │       ├── 承载vs操作关系
│   │       ├── 反馈回路（变异/非人化）
│   │       └── 代价类型（物理损耗/精神腐蚀）
│   ├── 地理空间
│   │   ├── 主要地形（主世界→地区→区域）
│   │   ├── 垂直层级（深空/天空/高山/地面/地下/地心）
│   │   ├── 特殊地理（shaping_rules + power_sources）
│   │   ├── 主世界设计·4维度
│   │   │   ├── 架构维度（结构形态/边界）
│   │   │   ├── 法则维度（能量来源/神权架构/生死规则）
│   │   │   ├── 位面维度（位面拓扑/传送门/位面共振）
│   │   │   └── 纪元维度（创世阶段/循环机制）
│   │   ├── 地区设计·4维度
│   │   │   ├── 行星地理格局（纬度地带性/海陆分布）
│   │   │   ├── 文明演化位阶（原生/次生/支配/挑战者）
│   │   │   ├── 叙事承载权重（主线舞台/后勤/探索/禁区）
│   │   │   └── 法则同调程度（高魔/低魔/法则破碎区）
│   │   ├── 区域设计·4维度
│   │   │   ├── 核心-边缘拓扑
│   │   │   ├── 系统分工角色
│   │   │   ├── 网络连接密度
│   │   │   └── 发展梯度位势
│   │   └── ❌ A1边界切割：地点分区/场景细节/地点设计 → 归A2/A3
│   ├── 文明与社会
│   │   ├── 核心价值（意识形态）
│   │   ├── 冲突（资源/信仰/种族/文化/权利/特殊）
│   │   ├── 势力类型（政治类型）
│   │   └── 经济（力量物质化/自然资源）
│   ├── 历史时间线
│   │   ├── 长度（时间跨度/era）
│   │   ├── 关键节点（severity/发生地/涉及势力/因果上游）
│   │   ├── 事件图（因果链）
│   │   └── 主剧情·4维拓扑
│   │       ├── 驱动维度（起源回响：开端=对起源的触发）
│   │       │   ├── 意志主导→转折靠信念/牺牲
│   │       │   └── 物质主导→转折靠资源/科技
│   │       ├── 代理维度（意志载体：主角=存在物极端样本）
│   │       │   └── 势力强弱=力量体系分布
│   │       ├── 舞台维度（空间映射：决战=拓扑敏感点）
│   │       │   └── 地图现状=剧情投影
│   │       └── 归宿维度（哲学闭环：结局验证/挑战哲学）
│   │           ├── 循环论→新轮回（Event环形拓扑）
│   │           └── 虚无主义→衰败（Event熵增链）
│   ├── 视觉设计
│   │   ├── 关键词
│   │   ├── 建筑风格（资源+文化风格+社会身份）
│   │   └── 材质偏好（资源+特殊动植物+文化）
│   ├── 玩法设计DNA
│   │   ├── 玩家身份（社会→维度→超越 三阶段）
│   │   ├── 主要行为（探索/战斗/研究/提升）
│   │   ├── 成长方式（量变/质变/哲学/因果/探索）
│   │   └── 成长尽头（社会性/法则性/哲学性终点）
│   ├── 骰子设定·5维映射
│   │   ├── 现实规则→概率分布（意志→线性d20 / 物质→钟形3d6）
│   │   ├── 力量来源→骰子数量（本体→固定骰 / 客体→骰池）
│   │   ├── 获取方式→判定方式（封闭→Roll-under / 开放→Roll-over）
│   │   ├── 玩法行为→成功判定（战斗→二元 / 研究→多层次）
│   │   └── 哲学平衡→代价机制（残酷→临界陷阱）
│   └── AI生成边界
│       ├── 可生成范围（A2分区/A3场景/NPC/支线/视觉变体）
│       └── 不可改变范围（IP/世界本体/力量/地理骨架/主线/视觉/玩法）
│
├── ❌ 断点A：语义→标签→枚举值 编译器
│   ├── 输入：第4套的自然语言语义描述
│   ├── 缺失内容
│   │   ├── ❌ 标签词典（LAW下有哪些合法标签：world_structure/gravity/conservation/...）
│   │   ├── ❌ 枚举词典（每个标签有哪些合法值：FLOATING_ISLANDS/SPHERE/TREE/...）
│   │   └── ❌ 语义→标签→枚举映射规则（LLM+规则引擎混合）
│   ├── 输出应该是：结构化标签=枚举值
│   │   └── 示例：world_structure=FLOATING_ISLANDS, gravity=HIGH, conservation=TRUE
│   └── 阻塞：断点B/C/D/E/F全部
│
├── ❌ 断点B：约束输出模型结构化
│   ├── 现状
│   │   ├── LawOutput.rules: list[str] ← 自由文本
│   │   ├── ActOutput.actions: list[dict] ← 自由结构
│   │   ├── NarOutput.style/tone: str ← 自由文本
│   │   ├── WstOutput.effects: list[dict] ← 自由结构
│   │   └── SocOutput.relations: list[dict] ← 自由结构
│   ├── 需要变成
│   │   ├── LawOutput 增加结构化字段：world_structure / gravity / conservation / divine_intervention / afterlife
│   │   ├── ActOutput 增加结构化字段：dice_mode / check_direction / cost_function / core_action
│   │   ├── NarOutput 增加结构化字段：era_stage / time_mode / trajectory / success_granularity
│   │   ├── WstOutput 增加结构化字段：cost_type / feedback_loop / climate_zone / power_saturation
│   │   ├── SocOutput 增加结构化字段：political_type / access_topology / threshold / economy_type
│   │   └── 保留自由文本字段作为自然语言补充
│   ├── 依赖：断点A（标签+枚举词典）
│   └── 阻塞：断点C/D/E/F
│
├── 第1套：6维约束（ConstraintDimension）
│   ├── Constraint(LAW) 物理法则
│   │   ├── ✅ 现有：DimensionGenerator能生成LawOutput（自由文本）
│   │   ├── ❌ 断点B：需要结构化字段（world_structure/gravity/conservation/...）
│   │   └── 内容来源
│   │       ├── 世界本体.现实规则（意志/物质主导）
│   │       ├── 力量体系.溯源维度（能量来源类型）
│   │       ├── 力量体系.机制维度（守恒/非守恒/排他性）
│   │       ├── 地理空间.主世界设计.架构维度（结构/边界）
│   │       ├── 地理空间.主世界设计.法则维度（神权/生死）
│   │       ├── 地理空间.主世界设计.位面维度（连通性）
│   │       ├── 地理空间.主世界设计.纪元维度（时间模式）
│   │       ├── 骰子设定.现实规则→概率分布
│   │       └── 力量体系.代价维度（物理代价类型）
│   ├── Constraint(ACT) 行为规则
│   │   ├── ✅ 现有：DimensionGenerator能生成ActOutput
│   │   ├── ❌ 断点B：需要结构化字段（dice_mode/check_direction/cost_function/...）
│   │   └── 内容来源
│   │       ├── 力量体系.载体维度（获取方式/门槛）
│   │       ├── 力量体系.代价维度（承载vs操作）
│   │       ├── 骰子设定.力量来源→骰子数量
│   │       ├── 骰子设定.获取方式→判定方式
│   │       └── 玩法DNA.主要行为（探索/战斗/研究/提升）
│   ├── Constraint(NAR) 叙事约束
│   │   ├── ✅ 现有：DimensionGenerator能生成NarOutput
│   │   ├── ❌ 断点B：需要结构化字段（era_stage/time_mode/trajectory/...）
│   │   └── 内容来源
│   │       ├── 历史时间线.主剧情.驱动维度（转折机制）
│   │       ├── 历史时间线.主剧情.归宿维度（哲学闭环）
│   │       ├── 骰子设定.玩法行为→成功判定（二元/多层次）
│   │       ├── 视觉设计.关键词（叙事基调根）
│   │       └── 哲学思想（编译为Constraint(NAR,CORE)）
│   ├── Constraint(WST) 世界状态
│   │   ├── ✅ 现有：DimensionGenerator能生成WstOutput
│   │   ├── ❌ 断点B：需要结构化字段（cost_type/feedback_loop/climate_zone/...）
│   │   └── 内容来源
│   │       ├── 力量体系.代价维度（肉体损耗/变异）
│   │       ├── 地理空间.法则同调程度（力量浓度）
│   │       ├── 骰子设定.哲学平衡→代价机制
│   │       └── 地理空间.气候（纬度地带性）
│   ├── Constraint(SOC) 社交生态
│   │   ├── ✅ 现有：DimensionGenerator能生成SocOutput
│   │   ├── ❌ 断点B：需要结构化字段（political_type/access_topology/threshold/...）
│   │   └── 内容来源
│   │       ├── 文明与社会.核心价值（意识形态）
│   │       ├── 文明与社会.势力类型（政治类型）
│   │       ├── 文明与社会.经济（力量物质化）
│   │       ├── 力量体系.载体维度（封闭/开放拓扑→阶层分化）
│   │       ├── 文明与社会.冲突（对立类型）
│   │       └── 力量体系.代价维度（精神代价类型）
│   └── Constraint(RED) 内容红线
│       ├── ✅ 现有：DimensionGenerator能生成RedOutput
│       └── 内容来源
│           └── AI生成边界.不可改变范围
│
├── 第1套 × 第2套 = 6×6 权重矩阵
│   ├── ✅ 现有：WeightMatrixLoader 已实现（YAML静态表，8项验证）
│   ├── ✅ 现有：DimensionPromptBuilder 已实现（按权重降序排列维度）
│   ├── ⚠️ 断点：权重矩阵是硬编码静态表，无法根据种子动态调整（README断点A）
│   └── 权重表内容
│       ├── WORLD层:  LAW(40%) + SOC(25%) + NAR(15%) + ACT(10%) + RED(5%) + WST(5%)
│       ├── REGION层: SOC(35%) + LAW(20%) + NAR(15%) + WST(15%) + ACT(10%) + RED(5%)
│       ├── SCENE层:  NAR(30%) + WST(20%) + LAW(15%) + ACT(15%) + SOC(15%) + RED(5%)
│       ├── CAMPAIGN层: NAR(35%) + ACT(20%) + SOC(15%) + LAW(10%) + WST(10%) + RED(5%)
│       ├── NPC层:    SOC(30%) + ACT(25%) + NAR(20%) + LAW(10%) + WST(10%) + RED(5%)
│       └── ASSET层:  ACT(25%) + LAW(20%) + NAR(15%) + WST(15%) + SOC(20%) + RED(5%)
│
├── ❌ 断点H：层间语义焦点差异
│   ├── 现状：所有6层使用同一个system prompt模板，只改变权重数字
│   ├── 问题
│   │   ├── LAW在WORLD层：LLM应关注"世界的物理法则是什么"（宏观）
│   │   ├── LAW在NPC层：LLM应关注"这个NPC遵守什么物理法则"（角色级）
│   │   └── LAW在ASSET层：LLM应关注"这个物品的物理属性"（物品级）
│   ├── 当前：prompt只说"LAW在NPC层占10%"，没说"LAW在NPC层应关注角色法则约束"
│   ├── 实现难度：低（改prompt模板）
│   └── 阻塞：无（独立改善项）
│
├── 📦 DimensionResultSet（约束产出物）
│   ├── ✅ 现有：DimensionGenerator.generate() → DimensionResultSet
│   ├── ✅ 现有：6个Output模型（RedOutput/LawOutput/ActOutput/NarOutput/WstOutput/SocOutput）
│   ├── ❌ 断点B：Output模型是自由文本，不是结构化标签=枚举值
│   └── ❌ 核心问题：DimensionResultSet产出后，无人消费它
│
├── ❌ 断点C：约束应用逻辑树（核心缺失）
│   ├── 定位：连接约束体系与生成管线的桥梁
│   ├── 缺失内容
│   │   ├── ❌ 约束维度×生成层→字段调用映射表（6维×6层=36个映射）
│   │   ├── ❌ 同一约束字段在不同层的不同调用目标
│   │   └── ❌ 注入目标的优先级排序
│   ├── 逻辑树数据结构
│   │   ├── source_field: "LAW.world_structure"（从约束哪个字段读）
│   │   ├── target_prompt_layer: "World"（注入PromptBuilder哪一层）
│   │   ├── target_node_field: "Geography.vertical_layer"（影响什么节点字段）
│   │   ├── target_edge_type: "GEO_ABOVE"（触发什么拓扑边）
│   │   ├── transform: "map_to_vertical_layer_enum"（用什么转换函数）
│   │   └── priority: 1（在该层内的注入优先级）
│   ├── 示例：同一个LAW在不同层的不同调用
│   │   ├── LAW.world_structure
│   │   │   ├── WORLD层 → Geography.vertical_layer + RULE_SHAPES_GEO边
│   │   │   ├── NPC层 → 影响移动方式描述
│   │   │   ├── SCENE层 → 影响空间布局描述
│   │   │   └── ASSET层 → 影响物理属性描述
│   │   ├── LAW.gravity
│   │   │   ├── WORLD层 → RULE_SHAPES_GEO边（重力塑造地形）
│   │   │   ├── NPC层 → 影响移动判定（ACT技能检定修正）
│   │   │   ├── SCENE层 → 影响重力环境描述
│   │   │   └── ASSET层 → 影响重量描述
│   │   └── LAW.conservation
│   │       ├── WORLD层 → 力量体系交互法则
│   │       ├── NPC层 → 影响技能消耗
│   │       ├── SCENE层 → 影响能量状态
│   │       └── ASSET层 → 影响耐久消耗
│   ├── 依赖：断点A+B（需要结构化约束才能查表）
│   └── 阻塞：断点D/E/F（需要逻辑树才能注入）
│
├── 第2套：6层生成（CreationLayer）
│   ├── WORLD（世界观）
│   │   ├── 典型约束：LAW(40%)+SOC(25%)+NAR(15%)
│   │   ├── 产出：Geography骨架 + Concept节点 + 结构拓扑边
│   │   └── ❌ 断点F：约束不参与图谱构建（Constraint节点和边不自动创建）
│   ├── REGION（区域文化）
│   │   ├── 典型约束：SOC(35%)+LAW(20%)+NAR(15%)
│   │   └── 产出：区域内分区（A2）+ Culture节点
│   ├── SCENE（场景/地点）
│   │   ├── 典型约束：NAR(30%)+WST(20%)+LAW(15%)
│   │   └── 产出：Scene节点 + 场景细节（A3）
│   ├── CAMPAIGN（战役/剧情）
│   │   ├── 典型约束：NAR(35%)+ACT(20%)+SOC(15%)
│   │   └── 产出：Event骨架 + EVENT_CAUSED_BY因果链
│   ├── NPC（角色）
│   │   ├── 典型约束：SOC(30%)+ACT(25%)+NAR(20%)
│   │   └── 产出：Character节点
│   └── ASSET（资产/物品）
│       ├── 典型约束：ACT(25%)+LAW(20%)+SOC(20%)
│       └── 产出：Item节点 + 资产概念图
│
├── ❌ 断点D：约束→PromptBuilder注入
│   ├── 现状：PromptBuilder 8层模板完全不引用DimensionResultSet
│   │   ├── Layer1 World ← 从YAML模板读取
│   │   ├── Layer2 Location ← 从YAML模板读取
│   │   ├── Layer3 Camera ← 从YAML模板读取
│   │   ├── Layer4 Subject ← 从场景数据读取
│   │   ├── Layer5 Gameplay ← 从场景数据读取
│   │   ├── Layer6 Interaction ← 从场景数据读取
│   │   ├── Layer7 Material ← 从YAML模板读取
│   │   └── Layer8 Lighting ← 从YAML模板读取
│   ├── 需要：每一层都应通过约束应用逻辑树注入约束
│   │   ├── Layer1 World ← Constraint(LAW) world_structure/energy_flow
│   │   ├── Layer4 Subject ← Constraint(SOC) relations + Constraint(ACT) abilities
│   │   ├── Layer5 Gameplay ← Constraint(ACT) dice_mode/check_direction
│   │   ├── Layer7 Material ← Constraint(WST) cost_type + Constraint(LAW) conservation
│   │   └── Layer8 Lighting ← Constraint(NAR) tone/era_stage
│   ├── 依赖：断点C（约束应用逻辑树）
│   └── 阻塞：无（终端断点）
│
├── ❌ 断点E：约束→PromptFusion注入
│   ├── 现状：PromptFusion 3段式只依赖GraphNode.description
│   │   ├── Section1 Subject ← node.description（纯文本）
│   │   ├── Section2 Relation ← edge.visual_description（纯文本）
│   │   └── Section3 Background ← background_node.description（纯文本）
│   ├── 需要：3段式应增强为约束感知
│   │   ├── Subject ← 增加约束描述（LAW环境效果+SOC关系）
│   │   ├── Relation ← 增加约束继承（沿边的约束传递）
│   │   └── Background ← 增加WST状态效果
│   ├── 依赖：断点C（约束应用逻辑树）+ 断点G（约束继承传递）
│   └── 阻塞：无（终端断点）
│
├── ❌ 断点F：约束→拓扑节点/边创建
│   ├── 现状：约束生成后不自动创建Constraint节点和拓扑边
│   ├── 需要
│   │   ├── Constraint(LAW) world_structure=FLOATING_ISLANDS
│   │   │   ↓ 自动创建
│   │   │   ├── Constraint节点(id=cst_001, dimension=LAW)
│   │   │   └── RULE_SHAPES_GEO边: cst_001 → Geography(主世界)
│   │   ├── Concept(POWER_SYSTEM) ← Constraint(LAW/ACT/WST)支配
│   │   │   ↓ 自动创建
│   │   │   ├── POWER_SATURATES_GEO边: Concept → Geography(高魔区)
│   │   │   └── POWER_SOURCES_FROM_GEO边: Geography → Concept
│   │   └── Concept(PHILOSOPHY) → Constraint(NAR,CORE)
│   │       ↓ 自动创建
│   │       └── Concept节点 + 编译为结局约束
│   ├── 依赖：断点A+B（需要结构化约束才能建正确的节点和边）
│   └── 阻塞：断点G（没有节点和边，继承传递无从谈起）
│
├── ❌ 断点G：约束继承传递
│   ├── 现状：设计完成（3_knowledge-assets.md §7），代码未实现
│   ├── 继承规则
│   │   ├── 权重≥10% → 完整传递（约束原样传递到下游节点）
│   │   ├── 权重5-10% → 压缩为摘要（约束简化为一句话）
│   │   ├── 权重<5% → 不传递（约束不影响下游）
│   │   └── override → 可覆盖不可删除（子节点可声明override但原约束仍记录）
│   ├── 传递路径
│   │   ├── GEO_CONTAINS: 父地理→子地理
│   │   ├── GEO_BORDERS: 邻接地理间
│   │   ├── FACTION_OPPOSES/ALLIED: 势力间
│   │   └── EVENT_CAUSED_BY: 事件因果链
│   ├── 依赖：断点F（需要拓扑节点和边存在才能沿边传递）
│   └── 阻塞：断点E（PromptFusion需要继承后的约束）
│
├── 第3套：A1/A2/A3权限控制（贯穿全生命周期）
│   ├── A1（世界观IP设计）— 结构常量
│   │   ├── 可建：5种骨架节点 + 15种结构拓扑边（6种仅A1）
│   │   ├── 不可变：source_stage="A1" 的节点和边
│   │   └── ❌ 断点F影响：约束→拓扑创建未实现，A1的骨架节点不会自动生成
│   ├── A2（产品策划）— 区域填充
│   │   ├── 可建：Culture节点 + CULTURE_INFLUENCES边
│   │   ├── 约束：沿GEO_CONTAINS下挂，不可新建A1结构边
│   │   └── ❌ 依赖：断点G（约束继承传递未实现，A2无法从A1继承约束）
│   └── A3（内容生产）— 实体填充
│       ├── 可建：Character/Item/Scene节点 + CHAR_BELONGS_TO等边
│       ├── 约束：沿A2拓扑下挂，不可新建A1/A2结构边
│       └── ❌ 依赖：断点D/E（约束注入未实现，A3生成的Prompt不含约束）
│
├── 📦 最终Prompt（当前产出物）
│   ├── ✅ PromptBuilder.build() → 8层模板拼接的逗号分隔字符串
│   ├── ✅ PromptFusion.build_prompt() → 3段式中文标记的Prompt
│   └── ❌ 核心问题：两个Prompt组装器都不包含约束信息
│
├── 📦 最终生成节点（当前产出物）
│   ├── ✅ ImageGenerator → 资产概念图（zhipu/wanxiang/qwen/local）
│   ├── ✅ GraphNode → 知识图谱节点
│   └── ❌ 核心问题：生成节点不携带约束属性，约束不参与生成
│
└── 断点依赖链总览
    ├── 断点A（语义→标签编译器）
    │   └── 阻塞 → 断点B
    ├── 断点B（输出模型结构化）
    │   ├── 依赖 ← 断点A
    │   └── 阻塞 → 断点C
    ├── 断点C（约束应用逻辑树）← 核心中的核心
    │   ├── 依赖 ← 断点A+B
    │   └── 阻塞 → 断点D/E/F
    ├── 断点D（PromptBuilder注入）
    │   └── 依赖 ← 断点C
    ├── 断点E（PromptFusion注入）
    │   ├── 依赖 ← 断点C
    │   └── 依赖 ← 断点G
    ├── 断点F（约束→拓扑创建）
    │   ├── 依赖 ← 断点A+B+C
    │   └── 阻塞 → 断点G
    ├── 断点G（约束继承传递）
    │   └── 依赖 ← 断点F
    └── 断点H（层间语义差异）
        └── 独立改善项，不阻塞也不被阻塞
```

---

## 已知连接 vs 断点 速查表

| 管线环节 | 状态 | 连接对象 |
|---------|------|---------|
| 第4套 → 第1套 | ❌ 断点A | 语义→标签→枚举编译器缺失 |
| 第1套（生成约束） | ✅ 已实现 | DimensionGenerator + LLM |
| 第1套结构化 | ❌ 断点B | Output模型是自由文本 |
| 第1套×第2套（权重） | ✅ 已实现 | WeightMatrixLoader + DimensionPromptBuilder |
| 层间语义差异 | ❌ 断点H | 所有层同一个prompt模板 |
| DimensionResultSet → 逻辑树 | ❌ 断点C | 约束应用逻辑树完全不存在 |
| 逻辑树 → PromptBuilder | ❌ 断点D | PromptBuilder不引用约束 |
| 逻辑树 → PromptFusion | ❌ 断点E | PromptFusion不引用约束 |
| 约束 → 拓扑节点/边 | ❌ 断点F | 约束不参与图谱构建 |
| 约束继承传递 | ❌ 断点G | 设计完成代码未实现 |
| PromptBuilder组装 | ✅ 已实现 | 8层模板拼接 |
| PromptFusion组装 | ✅ 已实现 | 3段式拼接 |
| ImageGenerator生成 | ✅ 已实现 | 多Provider资产概念图 |
| 第3套权限控制 | ✅ 已设计 | source_stage标记 + 边类型词典封闭枚举 |
```
