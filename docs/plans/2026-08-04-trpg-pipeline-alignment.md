# Echo UGC × TRPG 全流程对齐文档

> **日期**: 2026-08-04
> **项目**: H:\UGC — Echo UGC 游戏世界生成系统
> **文档类型**: 架构对齐 / 缺口分析 / 改造路线图
> **状态**: 待确认

---

## 〇、一句话诊断

> Echo UGC 目前是一个**"万能工厂"**——能生产发动机（厂家规则）、车身（主模组）、内饰（次模组），但没给产品贴型号标签（CORE / MODULE / SCENARIO），也没有总装车间（继承器 + 导出器），更没交给试车手（AI GM 运行时）。

核心改造方向：**不推翻 6 维模型，只加层级标签 + 继承覆写 + 装订成册 + AI GM 运行时。**

---

## 一、TRPG 全流程 × Echo UGC 现状对照

### 流程全景

```
┌─────────────────────────────────────────────────────────────────────┐
│  TRPG 完整生命周期                                                   │
│                                                                     │
│  ① 厂家设计 TRPG                                                    │
│     世界观 + 基础规则（判定/构建/组织结构）                           │
│     ↓                                                               │
│  ② 设计核心玩法                                                     │
│     玩法动力环（构建→交互→升华）                                     │
│     ↓                                                               │
│  ③ 设计主模组                                                       │
│     大地图 / 主线 / 区域 / 文化 / 权力者 / 全局物品 / 力量 / 经济    │
│     ↓                                                               │
│  ④ 设计次模组（战役/单元剧）                                        │
│     局部地图 / 区域剧情 / 增补物品 / 增补力量                        │
│     ↓                                                               │
│  ⑤ 装订成册 → 交给 GM                                               │
│     GM 自行增补细节、创建角色组织                                    │
│     ↓                                                               │
│  ⑥ 找人成团 → 创建角色                                              │
│     玩家车卡                                                         │
│     ↓                                                               │
│  ⑦ 开始跑团（AI 核心价值区）                                         │
│     三种 AI 辅助模式（助理 / 全自动 / 教学）                         │
│     ↓                                                               │
│  ⑧ 跑团反馈 → 进化                                                  │
│     反馈给厂家 / GM / AI 制作方                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 逐阶段对照表

| # | TRPG 流程阶段 | 具体内容 | Echo UGC 现状 | 状态 | 核心缺口 |
|---|---|---|---|---|---|
| ① | **厂家设计 TRPG** | 世界观 + 基础规则（判定/构建/组织结构） | 6 维约束（RED/LAW/ACT/NAR/WST/SOC）+ 6 维生成（World/Region/Scene/Campaign/NPC/Asset）+ 静态权重矩阵 | ✅ 已有，超配 | 约束模型完善，但缺 CORE 级标签区分 |
| ② | **设计核心玩法** | 玩法动力环（构建→交互→升华） | SeedEngine（种子反向推理）+ DimensionGenerator（权重驱动）试图覆盖 | 🔴 断层 | **厂家规则（硬）vs 模组规则（软）混在一起**，权重矩阵过度复杂，没有层级区分 |
| ③ | **设计主模组** | 大地图/主线/区域/文化/权力者/全局物品/力量/经济/声望 | KnowledgeGraph + CultureTree + ConstraintTree + WorldKG overlay（设计态） | 🟡 半有 | 有数据模型，**但未分层**。主模组应为"全局常量"，次模组为"局部变量"，代码没区分 |
| ④ | **设计次模组** | 局部地图/区域/剧情/权力者/人物/增补物品/增补力量/资产 | 和主模组共用同一套 CreationLayer（World/Scene/Campaign/NPC/Asset），**没有"继承/覆写"机制** | 🔴 **核心断层** | 次模组应"继承"主模组并"覆写"局部，代码全是平铺 6 维 |
| ⑤ | **装订成册 → 给 GM** | GM 拿到手册自行增补 | **完全没有"导出为册"功能**，只有散落的图谱节点和 API 端点 | 🔴 缺失 | GM 拿不到"一本册子"，只能看数据库 |
| ⑥ | **找人成团 → 创建角色** | 玩家车卡 | 终端 Demo 有玩家状态（HP/物品），但没有"角色卡创建向导" | 🟡 缺失 | MVP 可暂缓 |
| ⑦ | **开始跑团（AI 核心）** | 三种 AI 辅助模式（助理/全自动/教学） | 只有 `/api/action` 的极简判决 | 🔴 **蓝海空白** | 没有"GM 屏"、"模式旋钮"、"新手保底"、"情感熔断" |
| ⑧ | **跑团反馈 → 进化** | 反馈给厂家/GM/AI 制作方 | 没有"跑团日志"或"反馈收集器" | 🟢 锦上添花 | 可后置 |

---

## 二、四大架构断层（代码级验证）

### 断层 1: 厂家规则（CORE）vs 模组规则（MODULE/SCENARIO）未区分

**现状验证**:

- `backend/app/models/dimension.py` 只有 `ConstraintDimension`（6 维）和 `CreationLayer`（6 层）两个枚举
- **没有 `ConstraintLevel` 枚举**——所有约束都是"平铺"的，无法区分"厂家硬规则"和"模组软规则"
- `data/weight_matrix.yaml` 是全局静态表，所有种子在同一层拿到相同权重

**影响**: 权重矩阵 6×6 试图同时表达"厂家规则占比"和"模组规则占比"，导致矩阵过度复杂且语义混乱。

### 断层 2: 主模组 → 次模组的"继承-覆写"机制不存在

**现状验证**:

- `backend/app/services/` 下共 12 个文件（`__init__.py` 到 `seed_engine.py`）
- **没有 `module_inheritor.py`**——不存在任何模块继承逻辑
- `SeedEngine` 和 `DimensionGenerator` 的输出（`DimensionResultSet` / `ConceptNode`）是扁平结构
- 次模组和主模组共用完全相同的 `CreationLayer` 枚举，没有父子继承关系

**影响**: GM 想在已有世界观上加一个"城堡探险"次模组时，系统没有"以主模组为底 + 覆写局部"的能力，只能重新生成全部内容。

### 断层 3: "装订成册"导出器缺失

**现状验证**:

- `backend/app/services/` 下**没有 `module_exporter.py`**
- 没有任何代码将图谱 + 树 + 约束翻译成人类可读的 Markdown 手册
- GM 只能通过 API 端点或数据库查看散装数据

**影响**: GM 拿不到可用的"模组手册"，这是从"工具"到"产品"的关键断点。

### 断层 4: AI GM 运行时完全空白

**现状验证**:

- `backend/app/services/` 下**没有 `gm_runtime/` 目录**
- 现有 `orchestrator.py` 只做简单的 `parse → judge → render → update` 线性流程
- `/api/action` 端点只返回极简判决结果（成功/失败 + 叙事文本）
- **不存在**: GM 屏建议、模式旋钮（助理/全自动/教学）、新手保底、情感熔断、判例缓存

**影响**: 这是项目最大的蓝海——AI 辅助跑团——目前完全空白。

---

## 三、改造方案（不推翻 6 维模型，只加层级标签）

### 改造点 1: 约束层级标签（CORE / MODULE / SCENARIO）

**目标**: 在 `dimension.py` 的 `ConstraintDimension` 体系上新增层级字段，区分约束来源。

**新增枚举**:

```python
class ConstraintLevel(StrEnum):
    """约束层级 — 标识约束来源的不可变等级。不允许添加或修改。"""
    CORE = "core"         # 厂家设计，不可覆写（如"没有复活魔法"）
    MODULE = "module"     # 主模组级，可被次模组覆写（如"北方有龙族"）
    SCENARIO = "scenario" # 次模组级，仅本次战役生效（如"城堡里有毒气"）
```

**权重叠加规则**:

| 层级 | 权重优先级 | 可覆写性 | 示例 |
|---|---|---|---|
| CORE | 固定 100%，不可偏移 | 不可覆写 | "没有复活魔法"、"重力常数" |
| MODULE | 基线 ~70%，可偏移 | 可被 SCENARIO 覆写 | "北方有龙族"、"魔法消耗理智值" |
| SCENARIO | 基线 ~30%，可偏移 | 仅本次战役生效 | "城堡里有毒气"、"今夜暴风雪" |

**生成时自动叠加**: CORE 约束始终注入 → MODULE 约束按权重注入 → SCENARIO 约束按权重注入 → 最终 Prompt = 三层合并。

**涉及文件**:
- `backend/app/models/dimension.py` — 新增 `ConstraintLevel` 枚举
- `backend/app/services/dimension_generator.py` — `generate()` 方法感知层级
- `backend/app/services/seed_engine.py` — 种子生成标注层级
- `data/weight_matrix.yaml` — 可选：按层级拆分为 3 个矩阵

### 改造点 2: 主模组 → 次模组继承-覆写机制

**目标**: 新建 `services/module_inheritor.py`，实现"以主模组为底 + 次模组覆写局部"的合并逻辑。

**数据流**:

```
输入：main_module.json（大地图 / 全局力量 / 声望体系 / CORE + MODULE 约束）
输入：scenario_module.json（局部地图 / 增补物品 / SCENARIO 约束）
                    ↓
         ModuleInheritor.merge()
                    ↓
输出：campaign_package.json（完整配置，可直接导入 AI GM 系统）
```

**合并规则**:

| 类型 | 合并策略 |
|---|---|
| CORE 约束 | 直接复制，不可覆写 |
| MODULE 约束 | 默认继承，SCENARIO 有同名 key 则覆写 |
| 图谱节点 | 主模组节点全部保留 + 次模组节点追加 + 冲突边标记 |
| 文化树 | 主模组树为根 + 次模组分支挂载 |
| 约束树 | CORE 为顶层硬约束 + MODULE 为中层软约束 + SCENARIO 为底层临时约束 |
| NPC / 物品 | 主模组为基 + 次模组增补 / 覆写属性 |

**涉及文件**:
- `backend/app/services/module_inheritor.py` — **新建**
- `backend/app/models/module.py` — **新建**（`Module` / `CampaignPackage` 数据模型）

### 改造点 3: "装订成册"导出器

**目标**: 新建 `services/module_exporter.py`，把图谱 + 树 + 约束翻译成人类可读手册 + AI 配置包。

**双输出**:

| 输出 | 格式 | 消费者 | 内容 |
|---|---|---|---|
| **模组手册** | Markdown | GM（人类） | 自动分章：世界概览 → 区域详情 → NPC 名录 → 物品表 → 时间线 |
| **AI 配置包** | JSON | AI GM 系统 | 结构化数据：场景卡 + 判例基线 + NPC 行为树 + 约束层级 |

**涉及文件**:
- `backend/app/services/module_exporter.py` — **新建**
- `backend/app/api/module_routes.py` — **新建**（`GET /api/module/{id}/export`）

### 改造点 4: AI GM 运行时（新主线）

**目标**: 完全独立于生成器，新建 `services/gm_runtime/` 目录，构建 AI 辅助跑团系统。

**模块清单**:

| 文件 | 模式 | 职责 |
|---|---|---|
| `assistant_mode.py` | 助理模式 | GM 屏：建议 DC + 3 分支发展 + NPC 状态提示 |
| `auto_mode.py` | 全自动模式 | 全自动裁决 + 新手保底（连续失败保护）+ 自动叙事 |
| `tutorial_mode.py` | 教学模式 | 教学弹窗 + 规则提醒 + 新手指引 |
| `emotion_fuse.py` | 情感熔断 | 关键词检测 → 强制降级（保护三观升华，防止虐杀/崩坏） |
| `case_cache.py` | 判例缓存 | 跑团日志 → 相似情境裁决一致性保证 |

**涉及文件**:
- `backend/app/services/gm_runtime/` — **新建目录 + 5 个模块**
- `backend/app/api/gm_routes.py` — **新建**（`/api/gm/*` 端点族）
- `backend/app/models/gm.py` — **新建**（GM 状态 / 裁决记录 / 模式配置）

---

## 四、与现有断点的映射关系

用户的 TRPG 流程分析与项目 README 中记录的 10 个断点（A–J）存在以下对应关系：

| TRPG 流程断层 | 对应现有断点 | 关系 |
|---|---|---|
| 断层 1（CORE/MODULE/SCENARIO 未区分） | 断点 A（权重规则化生成）+ 断点 B2（五维→六维） | **部分重叠**：权重规则化的前提是先有层级标签；六维补全后才能正确分层 |
| 断层 2（继承-覆写机制不存在） | 断点 D（生成内容拆分到图模型）+ 断点 E（WorldKG overlay）+ 断点 F（约束继承传递） | **上游依赖**：继承-覆写需要先完成拆分（D）和 overlay（E），现有断点 D/E/F 是继承器的技术基础 |
| 断层 3（装订成册导出器缺失） | 无直接对应 | **全新需求**：现有断点未覆盖"输出为人类可读手册"的场景 |
| 断层 4（AI GM 运行时空白） | 无直接对应 | **全新需求**：现有断点全部聚焦"生成侧"，AI GM 是"运行侧"，完全不同的代码域 |

**结论**: 断层 1 和 2 是现有断点体系的延伸（需要先解决 A/B2/D/E 才能做），断层 3 和 4 是全新的架构需求。

---

## 五、精简版开发路线图（5 个 Sprint）

### Sprint 总览

```
Sprint 1                Sprint 2                Sprint 3
厂家规则 + 主模组  →   次模组 + 继承覆写  →   装订成册 + AI 配置导出
     ↓                        ↓                        ↓
断点 B2 补全            新建 module_inheritor     新建 module_exporter
ConstraintLevel 枚举    CampaignPackage 模型      Markdown 手册生成
                        ↑ 依赖断点 D/E
                                                  
          Sprint 4                        Sprint 5
          AI GM 运行时          →         反馈收集 + 迭代
          （最大蓝海）                       （锦上添花）
               ↓                                ↓
          gm_runtime/ 全部               feedback_collector.py
          assistant / auto / tutorial    跑团日志 + 反馈看板
          emotion_fuse / case_cache
```

### Sprint 1: 厂家规则 + 主模组生成

| 项 | 详情 |
|---|---|
| **目标** | 产出 `core_rules.json` + `main_module.json` |
| **前置** | 无（基于现有 6 维生成能力） |
| **工作项** | 1. 新增 `ConstraintLevel` 枚举（CORE / MODULE / SCENARIO）<br>2. 现有约束数据标注层级<br>3. **冻结断点 D/E/F**（图谱覆盖 / 继承，推迟到 Sprint 2 再按需补）<br>4. 解决断点 B2（种子五维→六维，补 Scene + NPC） |
| **产出** | `core_rules.json`（CORE 层约束）+ `main_module.json`（MODULE 层约束 + 世界设定） |
| **涉及断点** | B2（种子六维补全）、A（权重层级化前提） |

### Sprint 2: 次模组（战役）生成 + 继承覆写

| 项 | 详情 |
|---|---|
| **目标** | 产出 `scenario_module.json` + `campaign_package.json` |
| **前置** | Sprint 1 完成 |
| **工作项** | 1. 新建 `services/module_inheritor.py`<br>2. 新建 `models/module.py`（Module / CampaignPackage）<br>3. **轻量补完断点 D**（只补 Scene/NPC 拆分到图模型，够用即止）<br>4. 继承合并逻辑：CORE 复制 → MODULE 继承 → SCENARIO 覆写 |
| **产出** | `scenario_module.json` + `campaign_package.json`（可导入 AI GM 的完整配置包） |
| **涉及断点** | D（拆分到图模型——轻量版）、B2（Scene/NPC 维度落地） |

### Sprint 3: 装订成册 + AI 配置导出

| 项 | 详情 |
|---|---|
| **目标** | 产出模组手册 Markdown + `gm_ai_config.json` |
| **前置** | Sprint 2 完成 |
| **工作项** | 1. 新建 `services/module_exporter.py`<br>2. 新建 `api/module_routes.py`<br>3. 自动分章逻辑：世界概览 → 区域 → NPC → 物品 → 时间线<br>4. 结构化导出：场景卡 + 判例基线 + NPC 行为树 |
| **产出** | `module_handbook.md`（人类可读）+ `gm_ai_config.json`（机器可读） |
| **涉及断点** | 无（全新模块） |

### Sprint 4: AI GM 运行时

| 项 | 详情 |
|---|---|
| **目标** | 可用的 AI 辅助跑团系统 |
| **前置** | Sprint 3 完成（需要 `gm_ai_config.json` 作为输入） |
| **工作项** | 1. 新建 `services/gm_runtime/` 目录<br>2. `assistant_mode.py` — GM 屏（建议 DC + 3 分支 + NPC 状态）<br>3. `auto_mode.py` — 全自动裁决 + 新手保底 + 连续失败保护<br>4. `tutorial_mode.py` — 教学弹窗 + 规则提醒<br>5. `emotion_fuse.py` — 关键词检测 → 强制降级<br>6. `case_cache.py` — 判例缓存（裁决一致性）<br>7. 新建 `api/gm_routes.py`（`/api/gm/*` 端点族） |
| **产出** | 可运行的 AI GM 系统（三种模式可切换） |
| **涉及断点** | 无（全新模块——项目最大蓝海） |

### Sprint 5: 反馈收集 + 迭代

| 项 | 详情 |
|---|---|
| **目标** | 跑团日志 + 反馈看板 |
| **前置** | Sprint 4 完成 |
| **工作项** | 1. 新建 `services/feedback_collector.py`<br>2. 跑团日志持久化（每轮裁决 + 玩家反馈）<br>3. 反馈聚合看板（高频问题 / 规则争议 / 体验评分） |
| **产出** | `feedback_dashboard.json` + 改进建议报告 |
| **涉及断点** | 无（锦上添花） |

---

## 六、架构分层全景（改造后）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TRPG 全流程分层架构                               │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  生成侧（现有 + 改造 1/2）                                       │   │
│  │                                                                 │   │
│  │  CORE 层（厂家规则）                                             │   │
│  │    ConstraintLevel.CORE → 不可覆写的全局规则                     │   │
│  │       ↓                                                         │   │
│  │  MODULE 层（主模组）                                             │   │
│  │    ConstraintLevel.MODULE → 世界观/区域/全局力量/声望            │   │
│  │       ↓                                                         │   │
│  │  SCENARIO 层（次模组/战役）                                      │   │
│  │    ConstraintLevel.SCENARIO → 局部地图/剧情/增补物品             │   │
│  │       ↓                                                         │   │
│  │  ModuleInheritor.merge()                                        │   │
│  │    主模组为底 + 次模组覆写 → campaign_package.json               │   │
│  └────────────────────────┬────────────────────────────────────────┘   │
│                           ↓                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  导出侧（改造 3）                                                │   │
│  │                                                                 │   │
│  │  ModuleExporter.export()                                        │   │
│  │    → module_handbook.md（人类可读手册）                          │   │
│  │    → gm_ai_config.json（AI GM 结构化配置包）                     │   │
│  └────────────────────────┬────────────────────────────────────────┘   │
│                           ↓                                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  运行侧（改造 4 — 全新）                                         │   │
│  │                                                                 │   │
│  │  GM Runtime                                                     │   │
│  │    ├─ assistant_mode.py  （GM 屏：建议/分支/NPC状态）            │   │
│  │    ├─ auto_mode.py       （全自动裁决 + 新手保底）               │   │
│  │    ├─ tutorial_mode.py   （教学弹窗 + 规则提醒）                 │   │
│  │    ├─ emotion_fuse.py    （情感熔断：关键词→强制降级）           │   │
│  │    └─ case_cache.py      （判例缓存：裁决一致性）                │   │
│  │                                                                 │   │
│  │  FeedbackCollector（改造 5）                                     │   │
│  │    → 跑团日志 → 反馈看板 → 改进建议                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 七、改造优先级矩阵

| 改造点 | 价值 | 复杂度 | 依赖 | 建议 |
|---|---|---|---|---|
| 1. 约束层级标签 | ⭐⭐⭐ | ⭐⭐ | 无 | **立即做**——其他改造的基础 |
| 2. 继承-覆写机制 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 断点 D/E 轻量补完 | Sprint 2 做，先轻量再迭代 |
| 3. 装订成册导出器 | ⭐⭐⭐⭐⭐ | ⭐⭐ | Sprint 2 | **GM 最需要**——简单但高价值 |
| 4. AI GM 运行时 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Sprint 3 | **最大蓝海**——Sprint 4 重点投入 |
| 5. 反感收集 | ⭐⭐ | ⭐⭐ | Sprint 4 | 最后做 |

---

## 八、现有断点处置决策

| 断点 | 状态 | 处置 |
|---|---|---|
| **A** 权重规则化生成 | ⚠️ 核心 | **改造点 1 前置**：先加层级标签（CORE/MODULE/SCENARIO），再处理权重动态化 |
| **B** 递归生成深化 | ⚠️ 核心 | **推迟到 Sprint 2 后**：继承-覆写机制建立后，递归深化才有载体 |
| **B2** 种子五维→六维 | ⚠️ 核心 | **Sprint 1 立即解决**：Scene + NPC 维度补全是所有改造的基础 |
| **C** 约束→Prompt 注入 | 🔧 集成 | **Sprint 1 附带**：层级标签注入 Prompt 时一并完成 |
| **D** 生成内容拆分到图模型 | 🔧 集成 | **Sprint 2 轻量补完**：只补 Scene/NPC 到够用，不全量实现 |
| **E** WorldKG overlay | 🔧 集成 | **冻结**：继承-覆写机制用更简单的方式替代 overlay 需求 |
| **F** 约束继承传递 | 🔧 集成 | **冻结**：被改造点 2 的 ModuleInheritor 替代 |
| **G** RED 拦截器 | 🔧 集成 | **Sprint 4 附带**：放入 `gm_runtime/emotion_fuse.py` 的前置链 |
| **H** 其余图层级 API | 🔧 功能 | **推迟**：等主线（继承器 + GM 运行时）完成后补 |
| **I** 前端对接 + 持久化 | 🔧 功能 | **推迟**：等 Sprint 3 导出器完成后统一前端对接 |
| **J** start.ps1 路径硬编码 | 🔧 功能 | **随手修** |

---

## 九、关键设计决策记录

| 决策 | 选择 | 理由 | 日期 |
|---|---|---|---|
| 是否推翻 6 维模型 | **不推翻** | 6 维模型本身完善，只需加层级标签 | 2026-08-04 |
| 断点 E（WorldKG overlay）是否实现 | **冻结** | ModuleInheritor 用更简单的合并逻辑替代 | 2026-08-04 |
| 断点 F（约束继承传递）是否实现 | **冻结** | 同上，ModuleInheritor 覆盖了该需求 | 2026-08-04 |
| 断点 D（全量拆分）是否实现 | **轻量版** | 只补 Scene/NPC 到够用，不全量拆分到 7 个图模型 | 2026-08-04 |
| AI GM 是否独立于生成器 | **完全独立** | `gm_runtime/` 与生成器零耦合，只通过 `campaign_package.json` 衔接 | 2026-08-04 |
| 导出格式 | **双输出** | Markdown（人类）+ JSON（AI），两者并行 | 2026-08-04 |

---

## 十、后续行动项

- [ ] **确认本文档** — 用户确认改造方向和优先级
- [ ] **Sprint 1 启动** — 新增 `ConstraintLevel` 枚举 + 解决断点 B2（种子六维补全）
- [ ] **更新 README.md** — 将本文档添加到设计文档列表
- [ ] **创建 PROJECT_STATE.md** — 按 AGENTS.md 要求建立跨会话状态文件

---

*本文档基于代码实际结构编写（`dimension.py` / `concept.py` / `services/` 目录验证），非理论推导。*
