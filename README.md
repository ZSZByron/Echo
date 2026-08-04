# Echo UGC — AI驱动知识图谱资产管线

## 项目概述

Echo UGC 是一个 **6维约束驱动 → 6维生成 → 知识图谱+树结构 → 多维标签合成Prompt → 资产概念图** 的完整AI世界生成管线。

### 核心管线

```
┌─────────────────────────────────────────────────────────────────┐
│  Step 1: 6维约束生成                                            │
│  RED(内容红线) / LAW(物理法则) / ACT(行为规则)                  │
│  NAR(叙事约束) / WST(世界状态) / SOC(社交生态)                  │
│  ↓ 按权重矩阵分配（6×6，每层占比不同）                           │
├─────────────────────────────────────────────────────────────────┤
│  Step 2: 6个生成维度                                            │
│  世界(World) / 情节(Story) / 场景(Scene) / 人物(NPC)            │
│  / 资产(Asset) / 限制(Constraint)                                │
│  ↓ 根据约束维度内容，生成完整世界                                │
├─────────────────────────────────────────────────────────────────┤
│  Step 3: 拆分为知识图谱 + 树结构                                 │
│  世界观 → KnowledgeGraph（交叉关系）                             │
│  文化/约束 → CultureTree / ConstraintTree（层级树）              │
│  剧情/事件 → StoryGraph / EventGraph（分支图）                   │
│  场景 → SceneGraph（空间依赖图）                                 │
│  ↓ 建立图谱与树之间的联系（WorldKG overlay 交叉边）              │
├─────────────────────────────────────────────────────────────────┤
│  Step 4: 资产编辑器 — 多维标签合成Prompt                        │
│  从图谱节点+约束标签+依赖关系 → 合成8层Prompt                    │
│  Subject + Relation + Background + Material + Lighting + ...    │
│  ↓ 生成资产概念图（ImageGenerator: zhipu/wanxiang/qwen/local）   │
└─────────────────────────────────────────────────────────────────┘
```

### 两个正交的"6"

- **6维约束**（ConstraintDimension — "什么规则"）：RED / LAW / ACT / NAR / WST / SOC
- **6维生成**（CreationLayer — "生成什么"）：World / Scene / Campaign / NPC / Asset / Constraint

通过 **6×6 权重矩阵**（`data/weight_matrix.yaml`）关联：每个生成维度中 6 维约束的占比不同，权重决定 Prompt 占比、继承过滤强度和编辑器 UI 优先级。

> **实现状态**: Step 1（约束）和 Step 4（资产生成）已基本可用。Step 2（种子生成）当前只有五维（缺 Scene 和 NPC），详见断点 B2。Step 3（拆分+联系）数据模型完成但拆分逻辑和 overlay 未实现，详见断点 D/E。

---

## 技术栈

### 后端
- **框架**: FastAPI + Python 3.11+ + Pydantic v2
- **规则引擎**: 纯Python确定性规则（physics.py / rules_engine.py / god_intervention.py）
- **AI服务**: 多LLM Provider抽象（OpenAI / Anthropic / DeepSeek / Qwen / Kimi / GLM）
- **数据库**: SQLite（aiosqlite + SQLAlchemy）
- **6图模型**: 6个创作层级各有独立图模型 — World / Region / Scene / Campaign / NPC / Asset（`models/dimension.py` CreationLayer 枚举）
- **6维约束**: RED / LAW / ACT / NAR / WST / SOC × 6层 × 6×6权重矩阵（`data/weight_matrix.yaml`）
- **图数据结构**: KnowledgeGraph（核心）+ StoryGraph + EventGraph + CultureTree + ConstraintTree + SceneGraph + PuzzleGraph（全部 Pydantic v2 模型 + 测试）
- **资产管线**: GenerationScheduler（Wave调度）+ PromptBuilder + PromptFusion
- **测试**: pytest + pytest-cov + pytest-behave (BDD) + mutmut（变异测试）

### 前端
- **框架**: Vite + React 19 + TypeScript
- **样式**: TailwindCSS v4 + 自定义赛博朋克CRT效果
- **图编辑器**: React Flow（节点/边可视化编辑）
- **测试**: Vitest + Playwright（E2E）
- **特性**: 打字机效果、状态面板、神王干涉红光可视化、场景背景渲染

### 工具链
- **CI/CD**: GitHub Actions
- **Linter**: ruff + mypy（后端）/ oxlint（前端）
- **启动**: PowerShell 一键脚本 `start.ps1`

---

## 快速开始

### 前置要求

- Python 3.11+（项目使用 Anaconda `F:\Anaconda\envs\Deepcode` 环境）
- Node.js 18+
- PowerShell 5.1+ 或 PowerShell 7+

### 1. 环境配置

#### 后端配置

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate
pip install -e .
deactivate
```

复制 `.env.example` 到 `.env`，填入LLM Provider API密钥：

```env
ACTIVE_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-key-here
```

支持的Provider：
| Provider | 配置键 | 默认模型 |
|----------|--------|---------|
| `openai` | `OPENAI_API_KEY` | gpt-4o-mini |
| `anthropic` | `ANTHROPIC_API_KEY` | claude-3-5-sonnet |
| `deepseek` | `DEEPSEEK_API_KEY` | deepseek-chat |
| `qwen` | `QWEN_API_KEY` | qwen-plus |
| `kimi` | `KIMI_API_KEY` | moonshot-v1-8k |
| `glm` | `GLM_API_KEY` | glm-4 |

#### 前端配置

```bash
cd frontend
npm install
```

### 2. 启动服务

#### 方法一：一键启动脚本（推荐）

```powershell
.\start.ps1
```

> **注意**: `start.ps1` 硬编码了 Anaconda 环境路径 `F:\Anaconda\envs\Deepcode\python.exe`。如果 Python 安装位置不同，请修改脚本或使用手动启动。

同时启动后端（:8000）和前端（:5173）。

#### 方法二：手动启动

```bash
# 后端
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端（新终端）
cd frontend
npm run dev
```

### 3. 访问应用

| 路由 | 页面 | 说明 |
|------|------|------|
| `http://localhost:5173/` | 交互终端 | 赛博朋克终端 Demo（主入口） |
| `http://localhost:5173/graph/editor` | 知识图谱编辑器 | React Flow 可视化编辑 |
| `http://localhost:5173/admin/graph-assets` | 图谱资产生成 | Wave 分组展示 + 生成进度（前端部分 Mock） |
| `http://localhost:5173/admin/assets` | 资产审核 | 资产审批/拒绝/重新生成 |

后端API文档：`http://localhost:8000/docs`

---

## 当前可用功能

### ✅ Step 0: 交互终端（Demo）
- 自然语言输入 → AI解析意图 → 规则判决 → 叙事渲染 → 打字机输出
- 状态面板（生命值/力量/物品栏）、神王干涉红光、场景视图
- API: `POST /api/action`、`GET /api/scene`、`GET /api/state`、`POST /api/reset`

### ✅ Step 1a: 6维约束数据模型 + 静态权重矩阵
- **6维约束枚举+输出模型**: RED/LAW/ACT/NAR/WST/SOC，各有类型化 Output（`models/dimension.py`）
- **6层生成维度枚举**: World/Region/Scene/Campaign/NPC/Asset（`CreationLayer`）
- **静态权重矩阵**: `data/weight_matrix.yaml`（6×6，硬编码基线值，每行和=100）
- **WeightMatrixLoader**: YAML 加载 + 8项验证（文件存在/YAML语法/根映射/6层齐全/6维齐全/行和=100/整数/非负）
- **DimensionPromptBuilder**: 按权重降序排列维度 → 组装 system prompt（高权重大篇幅，低权重简略）
- **DimensionGenerator**: 权重 → prompt → LLM → JSON 解析 → `DimensionResultSet`
- API: `POST /api/constraints/generate`

### ✅ Step 2a: 种子生成引擎（反向推理，当前五维，应为六维）
- **SeedEngine**: 任意种子输入 → 概念解析 → 缺失检测 → 反向推理 → 循环校验 → 用户确认 → 规则回馈
- **当前五维**（`concept.py` FIVE_DIMENSIONS）: story / asset / event / culture / constraint
- **反向生成器**: 20个方向专属 prompt 模板（`backward_generator.py`，如 asset→story / culture→constraint）
- **缺失检测器**: 优先级排序 + 依赖关系 + 建议来源（`gap_detector.py`，纯规则零LLM）
- **循环校验**: 生成内容跨维度一致性验证（`cycle_checker.py`）
- **规则回馈**: 用户确认后自动学习新规则到 RuleTable
- API: `POST /api/seed/generate`、`POST /api/seed/confirm`、`GET /api/seed/presets`

> **⚠️ 维度缺口**: 种子引擎当前是五维（story/asset/event/culture/constraint），但系统设计需要 **6个生成维度**：World（世界） / Story（情节） / Scene（场景） / NPC（人物） / Asset（资产） / Constraint（限制）。对比见下表：
>
> | 系统设计的6维 | concept.py 现状 | 差异 |
> |-------------|----------------|------|
> | World（世界） | culture（近似但不等同） | culture 侧重"区域文化"，缺"世界观/物理法则"层 |
> | Story（情节） | story ✅ | — |
> | Scene（场景） | **缺失** | 无场景生成维度 |
> | NPC（人物） | **缺失** | 无 NPC 生成维度（CreationLayer 有 NPC 层级但种子引擎不生成） |
> | Asset（资产） | asset ✅ | — |
> | Constraint（限制） | constraint ✅ | — |
> | — | event（额外） | event 在你的6维里未独立出现，可能归入 Story 或 Scene 的子内容 |
>
> **影响**: `backward_generator.py` 的 20 个方向模板只覆盖五维对（5×4=20），补全 Scene/NPC 后需扩展到 6×5=30 个方向模板。`gap_detector.py` 的优先级表和依赖关系表也需同步扩展。

### ✅ Step 3a: 知识图谱 + 树结构（数据模型层）
- **KnowledgeGraph**: 节点/边/层级解析/依赖查询/环检测（31测试，96%覆盖）
- **StoryGraph**: 跨场景剧情图，节点类型(start/end/choice/event/condition) + 条件分支 + 选择支
- **EventGraph**: 动态事件图，触发条件(time/location/state) + 动作 + 奖励
- **CultureTree**: 递归文化树，价值观 + 美学原则
- **ConstraintTree**: 约束树，硬约束(HARD)/软约束(SOFT) + 优先级
- **SceneGraph**: 场景依赖图，Kahn 拓扑排序生成顺序
- **PuzzleGraph**: 谜题依赖图，拓扑求解顺序

### ✅ Step 3b: 知识图谱编辑器 + API（仅 KnowledgeGraph）
- React Flow 可视化编辑（节点拖拽 / 边连接 / 增删改）
- LLM 文本提取图谱（输入场景描述 → AI提取节点和边）
- 环检测 + 图谱持久化（SQLite）
- Wave 分组串行生成触发
- API: `POST /api/graph/extract`、`/validate`、`/save`、`GET /api/graph/{id}`、`POST /api/graph/generate`

### ✅ Step 4a: Prompt 合成（基础）
- **PromptBuilder**: 8层模板化 prompt（World/Location/Camera/Subject/Gameplay/Interaction/Material/Lighting）
- **PromptFusion**: 图谱驱动3段式 prompt（Subject + Relation + Background），只融合已完成依赖节点
- **GenerationPlanner**: LOD感知 + SceneGraph + PuzzleGraph 合并依赖 → 生成顺序

### ✅ Step 4b: 资产概念图生成
- **ImageGenerator**: 支持 zhipu(CogView-3-Plus) / wanxiang(DashScope) / qwen / local 四种 provider
- 资产状态机: pending → generating → pending_review → approved/rejected
- 场景资产挂载: approved 资产自动渲染到场景
- **GenerationScheduler**: Wave串行调度，环检测 → 拓扑排序 → 并行生成（信号量限流）
- API: `POST /api/assets/{id}/generate`、`PUT /api/assets/{id}/approve`、`PUT /api/assets/{id}/reject`

### ✅ 测试体系
- pytest 单元测试 + pytest-behave BDD + pytest-cov（目标≥85%）+ mutmut 变异测试
- Playwright E2E（图谱编辑器 + 资产生成页面）
- GitHub Actions CI/CD

---

## 开发断点

> **按管线步骤列出断点。两大核心断点用 ⚠️ 标记。**

### ⚠️ 断点 A: 权重规则化生成（当前最大断点）

**问题**: 权重矩阵 `data/weight_matrix.yaml` 是**硬编码静态表**。`WeightMatrixLoader` 只做读取+验证，**没有权重生成能力**。无法根据种子概念动态调整约束维度占比。

**现状**:
- `DimensionGenerator.generate()` → `self._loader.get_weights(layer)` → 直接读静态 YAML → 组装 prompt
- 所有种子在同一层级拿到完全相同的权重分配
- 例如 "战斗型 NPC" 和 "外交型 NPC" 在 NPC 层都拿到 SOC=30%/ACT=25%，无法区分

**需要**:
1. **LLM 规则化权重生成器** — 根据种子概念 + 层级 → LLM 分析种子特征 → 输出调整后的权重（如"外交官"NPC → SOC 提升到 45%，ACT 降到 10%）
2. **权重安全机制** — 偏移警告（偏离基线>15%黄色 / >30%红色）+ 冲突检测（依赖对权重差>25%告警，如 LAW=40% / ACT=5%）
3. **权重缓存** — 相似种子复用权重，避免每次 LLM 调用

**设计文档**: `docs/plans/2026-08-03-layered-constraint-architecture.md` 第六节"权重调整安全机制"

### ⚠️ 断点 B: 递归生成细节（单跳反向推理，无递归深化）

**问题**: `backward_generate()` 是**单跳**推理（seed_dim → target_dim）。`SeedEngine` 对每个缺失维度只调用一次反向生成，**不会用生成结果作为新种子再展开下一层**。

**现状**:
- 种子 "水晶祭坛"(asset) → 单轮生成 story/event/culture/constraint → 结束
- 不会：水晶祭坛 → 生成 story "祭坛的秘密" → 用 story 作为新种子 → 生成更细的 event "发现祭坛暗格" → 再展开 asset "暗格中的水晶碎片"...
- `gap_detector` 只检查初始五维的填充状态，不做迭代轮次

**需要**:
1. **递归深化引擎** — 每轮生成结果作为新种子 → `gap_detector` 再次检测 → `backward_generate` 继续展开，直到达到深度限制或用户中止
2. **深度控制** — 最大递归深度 / 最小细节粒度 / token 预算限制
3. **循环引用检测** — 防止 A→B→A 无限递归
4. **递归结果汇聚** — 多层生成结果合并为一棵展开树（而非扁平五维）

**相关文件**: `app/domains/creation/seed/seed_engine.py`、`app/domains/creation/seed/backward_generator.py`、`app/domains/creation/seed/gap_detector.py`

### ⚠️ 断点 B2: 种子引擎五维 → 六维（Scene + NPC 维度缺失）

**问题**: `concept.py` 定义的是 `FIVE_DIMENSIONS`（story/asset/event/culture/constraint），缺 **Scene（场景）** 和 **NPC（人物）** 两个生成维度。

**现状**:
- `CreationLayer`（`dimension.py`）有全部 6 层：world/region/scene/campaign/npc/asset
- 但种子引擎的 `ConceptNode.dimensions` 只有 5 个 slot
- `backward_generator.py` 只有 5×4=20 个方向模板，补 Scene/NPC 后需 6×5=30 个
- `gap_detector.py` 的优先级表和依赖关系表也只覆盖五维
- Culture 维度近似 World 但不等同（culture 侧重区域文化，不包含物理法则/世界观层）

**需要**:
1. `FIVE_DIMENSIONS` → `SIX_DIMENSIONS`，加入 `SCENE_DIM` 和 `NPC_DIM`
2. `SeedType` 枚举加入 `SCENE` / `NPC`
3. `backward_generator.py` 补充新维度对的方向模板（scene→npc / npc→story / world→scene...）
4. `gap_detector.py` 优先级表和依赖关系表扩展
5. Culture 维度重新定义或拆分为 World + Culture

**相关文件**: `app/models/concept.py`、`app/domains/creation/seed/seed_engine.py`、`app/domains/creation/seed/backward_generator.py`、`app/domains/creation/seed/gap_detector.py`

### 🔧 断点 C: 6维约束 → 资产管线 Prompt 注入（未集成）
- **已完成**: DimensionGenerator 独立可用（权重→prompt→LLM→6维Output）
- **断点**: 约束结果尚未注入到 PromptBuilder / PromptFusion → 资产概念图生成不感知约束
- **需要**: PromptFusion 升级为权重感知组装器（约束维度 → prompt 段落，按权重分配篇幅）
- **设计**: `docs/plans/2026-08-03-layered-constraint-architecture.md` 第八节

### 🔧 断点 D: 生成内容拆分为知识图谱 + 树结构（拆分逻辑未建）
- **已完成**: 7个图模型的数据模型 + KnowledgeGraph 的 API 和编辑器
- **断点**: SeedEngine/DimensionGenerator 的输出（DimensionResultSet / ConceptNode）**不会自动拆分**到对应的图模型中（生成的 Story 内容不会自动写入 StoryGraph，约束不会自动写入 ConstraintTree...）
- **需要**: 生成结果 → 结构化分发器 → 写入各图模型 → 持久化

### 🔧 断点 E: 图谱-树联系建立（WorldKG overlay 未实现）
- **状态**: 设计完成，代码未实现
- **设计**: 五图保持独立，之上增加 WorldKG overlay 交叉边层（`NPC─belongs_to→Culture`, `Scene─contains→Asset`...），边在生成时自动建立
- **需要新建**: `app/domains/creation/graph/world_kg_overlay.py`、`app/domains/creation/constraint/constraint_inheritor.py`
- **设计文档**: `docs/plans/2026-08-03-layered-constraint-architecture.md` 第七节

### 🔧 断点 F: 约束继承传递（沿图谱边按权重过滤）
- **状态**: 设计完成，代码未实现
- **设计**: 约束沿知识图谱边向下游传递，按权重过滤密度（≥10%完整传递 / 5-10%压缩为摘要 / <5%不传），支持 override 但不可删除
- **设计文档**: `docs/plans/2026-08-03-layered-constraint-architecture.md` 第五节

### 🔧 断点 G: RED 硬编码拦截器（前置红线过滤）
- **已完成**: RED 维度有完整数据模型（RedOutput: forbidden 列表）+ LLM 生成
- **断点**: 资产生成前没有实际过滤禁止内容的拦截器
- **需要新建**: `app/domains/creation/constraint/red_filter.py`（系统级红线直接拒绝 / 世界观红线拒绝+提示 / 场景红线标记需确认）

### 🔧 断点 H: 其余图层级 API + 前端编辑器
- **已完成**: KnowledgeGraph 有完整 API + React Flow 编辑器
- **断点**: StoryGraph / EventGraph / CultureTree / ConstraintTree / SceneGraph 的 CRUD API 端点和前端可视化编辑器

### 🔧 断点 I: 前端对接 + 持久化
- GraphAssetReview 前端使用 Mock 数据（`AVAILABLE_GRAPHS` 和 `GeneratedAsset` 硬编码）
- 缺 `GET /api/graph/list` 端点
- GenerationScheduler 生成结果未持久化到 AssetStore

### 🔧 断点 J: start.ps1 路径硬编码
- 脚本硬编码 `F:\Anaconda\envs\Deepcode\python.exe`

---

## 项目结构

```
UGC/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI入口，注册6组路由
│   │   ├── orchestrator.py          # 终端交互编排器
│   │   ├── api/                     # API路由层
│   │   │   ├── routes.py            # /api/action, /api/scene, /api/state
│   │   │   ├── graph_routes.py      # /api/graph/* (知识图谱CRUD+生成)
│   │   │   ├── assets_routes.py     # /api/assets/*, /api/scenes/*
│   │   │   ├── seed_routes.py       # /api/seed/* (五维种子生成)
│   │   │   ├── constraints_routes.py # /api/constraints/* (6维约束)
│   │   │   └── deps.py              # 依赖注入
│   │   ├── engine/                  # 规则引擎
│   │   │   ├── rules_engine.py      # 确定性判决
│   │   │   ├── physics.py           # 物理法则
│   │   │   ├── god_intervention.py  # 神王法则
│   │   │   └── world_loader.py      # 场景YAML加载
│   │   ├── models/                  # Pydantic数据模型
│   │   │   ├── knowledge_graph.py   # 知识图谱(GraphNode/Edge/KnowledgeGraph)
│   │   │   ├── story_graph.py       # 剧情图(StoryNode/Edge/Graph)
│   │   │   ├── event_graph.py       # 事件图(EventNode/Trigger/Action/Reward)
│   │   │   ├── puzzle_graph.py      # 谜题依赖图(拓扑求解)
│   │   │   ├── culture.py           # 文化树(CultureNode/Tree 递归)
│   │   │   ├── constraint.py        # 约束树(HARD/SOFT ConstraintNode)
│   │   │   ├── dimension.py         # 6维约束(ConstraintDimension+CreationLayer+WeightMatrix+6个Output模型)
│   │   │   ├── asset.py             # 资产状态机(AssetStatus)
│   │   │   ├── concept.py           # 种子概念
│   │   │   ├── player.py            # 玩家状态
│   │   │   └── world.py             # 世界定义
│   │   ├── domains/                 # 领域驱动设计层
│   │   │   ├── creation/            # 创作域
│   │   │   │   ├── seed/            # 种子生成
│   │   │   │   │   ├── seed_engine.py       # 五维种子引擎
│   │   │   │   │   ├── backward_generator.py # 反向生成
│   │   │   │   │   ├── cycle_checker.py     # 环检测
│   │   │   │   │   └── gap_detector.py      # 间隙检测
│   │   │   │   ├── constraint/      # 约束生成
│   │   │   │   │   ├── dimension_generator.py  # 6维约束生成
│   │   │   │   │   └── rule_mapper.py       # 规则映射
│   │   │   │   ├── asset/           # 资产生成
│   │   │   │   │   ├── generation_scheduler.py # Wave串行生成调度
│   │   │   │   │   ├── generation_planner.py   # 生成计划(依赖排序)
│   │   │   │   │   ├── prompt_builder.py    # 提示词构建
│   │   │   │   │   └── prompt_fusion.py     # 提示词融合
│   │   │   │   └── graph/           # 图谱提取
│   │   │   │       └── graph_extractor.py   # LLM图谱提取
│   │   ├── ai/                      # AI服务层
│   │   │   ├── provider.py          # LLM Provider抽象
│   │   │   ├── parser.py            # 意图解析器
│   │   │   ├── renderer.py          # 叙事渲染器
│   │   │   ├── image_generator.py   # 图像生成器
│   │   │   ├── bg_remover.py        # 背景移除
│   │   │   ├── style_extractor.py   # 风格提取
│   │   │   ├── local_generator.py   # 本地生成器
│   │   │   ├── fallback_renderer.py # 降级渲染
│   │   │   ├── config.py            # AI配置
│   │   │   └── prompts/             # Prompt模板
│   │   ├── state/                   # 持久化层
│   │   │   ├── database.py          # SQLite连接管理
│   │   │   ├── asset_store.py       # 资产存储
│   │   │   ├── graph_store.py       # 图谱存储
│   │   │   └── migrations.py        # 数据库迁移
│   │   ├── config/                  # 配置
│   │   │   ├── features.py          # 功能开关
│   │   │   ├── paths.py             # 路径配置
│   │   │   └── weight_matrix.yaml   # 6×6权重矩阵
│   │   └── utils/                   # 工具函数
│   ├── tests/                       # 测试套件
│   │   ├── unit/                    # 单元测试
│   │   ├── integration/             # 集成测试
│   │   ├── models/                  # 模型测试
│   │   └── features/                # BDD测试(Gherkin)
│   ├── .env.example
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # 路由入口(pathname分发)
│   │   ├── pages/
│   │   │   ├── GraphEditor.tsx      # 图谱编辑器(/graph/editor)
│   │   │   ├── GraphAssetReview.tsx # 图谱资产生成(/admin/graph-assets)
│   │   │   └── AssetReview.tsx      # 资产审核(/admin/assets)
│   │   ├── components/
│   │   │   ├── Terminal.tsx         # 终端组件
│   │   │   ├── StatusPanel.tsx      # 状态面板
│   │   │   ├── SceneView.tsx        # 场景视图
│   │   │   ├── GodWatchIndicator.tsx # 神王干涉
│   │   │   ├── graph/               # 图谱专用组件
│   │   │   │   ├── NodeBadge.tsx    # 节点徽章
│   │   │   │   ├── PromptPreview.tsx # 提示词预览
│   │   │   │   └── WaveDivider.tsx  # Wave分隔线
│   │   │   └── ...
│   │   ├── api/
│   │   │   ├── client.ts            # API客户端
│   │   │   └── graph.ts             # 图谱API封装
│   │   ├── types/
│   │   │   └── graph.ts             # 图谱TypeScript类型
│   │   └── hooks/
│   │       └── useGameState.ts      # 游戏状态Hook
│   ├── tests/e2e/
│   │   ├── graph.spec.ts            # Playwright E2E测试
│   │   └── README.md
│   ├── playwright.config.ts
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── package.json
├── docs/
│   ├── SYSTEM_DESIGN_SPEC_v4.md     # 系统设计规范v4（最新）
│   ├── SYSTEM_DESIGN_SPEC_v3.md
│   ├── SYSTEM_DESIGN_SPEC_v2.md
│   ├── SYSTEM_DESIGN_SPEC.md
│   ├── handoff-bidirectional-concept-mapping.md
│   ├── handoff-bidirectional-mapping.md
│   └── plans/
│       ├── 2026-08-01-ai-story-scene-editor-design.md  # AI编辑器设计
│       └── 2026-08-03-layered-constraint-architecture.md # 分层约束架构
├── data/                             # 运行时数据（资产图片等）
├── start.ps1                        # 一键启动脚本
└── README.md                        # 本文件
```

---

## API 端点总览

### 交互终端
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/action` | 处理玩家自然语言指令 |
| GET | `/api/scene` | 获取场景数据（含已审批资产） |
| GET | `/api/state` | 获取玩家状态 |
| POST | `/api/reset` | 重置玩家状态 |
| GET | `/api/health` | 健康检查 |

### 知识图谱
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/graph/extract` | LLM从文本提取图谱 |
| POST | `/api/graph/validate` | 环检测验证 |
| POST | `/api/graph/save` | 保存图谱到数据库 |
| GET | `/api/graph/{scene_id}` | 加载图谱 |
| DELETE | `/api/graph/{scene_id}` | 删除图谱 |
| POST | `/api/graph/generate` | 触发Wave串行生成 |

### 资产管理
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/assets/{id}/generate` | 触发资产生成 |
| PUT | `/api/assets/{id}/approve` | 审批资产 |
| PUT | `/api/assets/{id}/reject` | 拒绝资产 |
| PUT | `/api/assets/{id}/prompt` | 更新提示词 |

### 种子系统
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/seed/generate` | 五维种子生成 |
| POST | `/api/seed/confirm` | 确认并回馈规则 |
| GET | `/api/seed/presets` | TRPG预设列表 |
| GET | `/api/seed/rules` | 当前规则表 |

### 约束体系
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/constraints/generate` | 6维约束生成 |

---

## 测试

### 后端测试

```bash
cd backend
pytest                           # 运行所有测试
pytest --cov=app                 # 带覆盖率
pytest tests/unit/               # 仅单元测试
pytest tests/integration/        # 仅集成测试
behave                           # Gherkin BDD测试
mutmut run                       # 变异测试（规则引擎）
.\scripts\verify.ps1             # 一键验证
```

### 前端测试

```bash
cd frontend
npm run build                    # 构建测试
npx playwright test              # E2E测试（Playwright）
npx vitest                       # 单元测试（Vitest）
```

---

## 质量门禁

| 层级 | 工具 | 目标 |
|------|------|------|
| 单元测试 | pytest | 全模块覆盖 |
| Gherkin BDD | pytest-behave | 关键流程 |
| 覆盖率 | pytest-cov | 总体≥85%，规则引擎≥95% |
| 代码质量 | ruff + mypy | 类型检查+风格 |
| 变异测试 | mutmut | 规则引擎≥80% |
| 前端E2E | Playwright | 图谱编辑器 + 资产生成 |
| 前端Lint | oxlint | 代码风格 |

---

## 故障排除

### 后端启动失败
1. 检查Python版本：`python --version`（需要3.11+）
2. 确认虚拟环境：`backend\.venv\Scripts\python -m pip install -e .`
3. 检查.env配置：确保API密钥正确
4. 如果使用 `start.ps1`：确认 Anaconda 环境路径 `F:\Anaconda\envs\Deepcode` 存在

### 前端启动失败
1. 检查Node版本：`node --version`（需要18+）
2. 删除重装：`rm -rf node_modules && npm install`
3. 端口占用：`netstat -ano | findstr :5173`

### API调用失败
1. 后端是否运行：`http://localhost:8000/docs`
2. CORS配置（已在main.py中配置 `allow_origins=["*"]`）
3. `.env` 中的 `ACTIVE_PROVIDER` 和 API密钥

### 图谱功能异常
1. 图谱提取需要LLM Provider可用
2. 图谱保存前会自动做环检测验证
3. SQLite数据库文件在 `backend/data/` 目录下

---

## 开发路线图

### 已完成
- [x] 交互终端 Demo（v0.4）— 自然语言交互 + 规则判决 + 叙事渲染
- [x] 知识图谱（KnowledgeGraph）— 数据模型 + 环检测（31测试/96%覆盖）+ API + SQLite持久化 + React Flow编辑器
- [x] Wave串行生成调度器 — 拓扑排序 + 依赖感知 + PromptFusion + ImageGenerator
- [x] 6个图模型数据层 — StoryGraph / EventGraph / CultureTree / ConstraintTree / SceneGraph / PuzzleGraph
- [x] 种子生成引擎 — 反向推理（20方向模板）+ 缺失检测 + 循环校验 + 规则回馈（**当前五维，缺 Scene/NPC，详见断点 B2**）
- [x] 6维约束体系 — RED/LAW/ACT/NAR/WST/SOC × 6层 × 静态权重矩阵 + DimensionGenerator（LLM驱动）+ API
- [x] Playwright E2E + GitHub Actions CI/CD

### 核心断点（阻塞管线的关键缺口）
- [ ] **⚠️ 权重规则化生成** — LLM 根据种子特征动态调整权重 + 偏移警告 + 冲突检测 + 权重缓存
- [ ] **⚠️ 递归生成细节** — 生成结果作为新种子迭代深化 + 深度控制 + 循环引用检测 + 结果汇聚为展开树
- [ ] **⚠️ 种子五维→六维** — `concept.py` 补 Scene + NPC 维度，`backward_generator` 扩展到30方向模板，`gap_detector` 同步扩展

### 集成断点（各模块间打通）
- [ ] 生成结果拆分 → 写入各图模型（DimensionResultSet → StoryGraph / CultureTree / ConstraintTree...）
- [ ] 6维约束 → PromptFusion 注入（权重感知 prompt 组装）
- [ ] 图谱-树联系（WorldKG overlay 交叉边，自动建边）
- [ ] 约束继承传递（沿边按权重过滤密度）
- [ ] RED 拦截器（前置红线过滤）

### 功能断点
- [ ] 其余图层级 CRUD API + 前端编辑器
- [ ] GraphAssetReview 去Mock + 图谱列表API + 生成结果持久化
- [ ] SOC 运行时引擎（关系图遍历 + 声望变更）
- [ ] start.ps1 路径硬编码修复

### 设计文档
- `docs/SYSTEM_DESIGN_SPEC_v4.md` — 系统设计规范 v4（3419行，含 §18 6维约束体系接口注册区）
- `docs/plans/2026-08-01-ai-story-scene-editor-design.md` — AI剧情场景编辑器设计（五图模型 + Phase 1-4）
- `docs/plans/2026-08-03-layered-constraint-architecture.md` — 分层约束架构（6维×6层×权重矩阵 + 继承模型 + 生成管线 + 实施路线 Phase D/E/F）

---

## 许可

MIT License
