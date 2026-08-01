# Echo UGC AI剧情场景编辑器设计方案

> **版本**: v1.0  
> **日期**: 2026-08-01  
> **作者**: AI Assistant  
> **状态**: 设计阶段  

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [核心功能模块](#3-核心功能模块)
4. [界面设计](#4-界面设计)
5. [技术实现方案](#5-技术实现方案)
6. [AI辅助系统](#6-ai辅助系统)
7. [数据模型设计](#7-数据模型设计)
8. [API接口设计](#8-api接口设计)
9. [实现路线图](#9-实现路线图)
10. [风险评估与应对](#10-风险评估与应对)

---

## 1. 项目概述

### 1.1 设计目标

将现有的简单场景编辑器升级为基于**五图模型**的完整AI剧情场景编辑器，支持复杂的动态开放世界内容创作。

### 1.2 核心价值

- **可视化叙事设计** - 直观的剧情和事件图编辑
- **智能辅助创作** - AI驱动的创作建议和验证
- **多层叙事架构** - 支持固定剧情+动态事件的混合叙事
- **文化一致性保证** - 通过文化树和约束树确保内容质量
- **高效资产管理** - 分类清晰的资产树管理系统

### 1.3 目标用户

- 游戏设计师 - 剧情和关卡设计
- 内容创作者 - UGC内容生产
- 世界观构建师 - 文化体系设计
- 关卡美术 - 资产生成和管理

---

## 2. 系统架构

### 2.1 五图模型架构

```
                 文化树 Culture Tree
                         |
                 约束树 Constraint Tree
                         |
                         ↓

                 世界知识图谱 World Knowledge Graph
                         |
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓

   剧情图 Story Graph   事件图 Event Graph   资产树 Asset Tree

        |                |                |

   剧情资产 Story Asset 事件资产 Event Asset 环境资产 Environment Asset

        └──────────────┬───────────────┘

                       ↓

                世界运行系统
```

### 2.2 编辑器系统架构

```
┌─────────────────────────────────────────────────────────────┐
│              Echo UGC Studio - AI剧情场景编辑器              │
├─────────────────────────────────────────────────────────────┤
│  前端界面层                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Story Graph │  │ Event Graph │  │   Asset Tree        │ │
│  │   Editor    │  │   Editor    │  │     Editor          │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│  ┌──────▼────────────────▼─────────────────────▼──────────┐  │
│  │         Culture & Constraint Configuration             │  │
│  └──────────────────────┬────────────────────────────────┘  │
│  ┌──────────────────────▼────────────────────────────────┐  │
│  │            World Knowledge Graph Visualization        │  │
│  └───────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  API接口层                                                   │
│  /api/story/*   /api/events/*   /api/assets/*   /api/ai/*   │
├─────────────────────────────────────────────────────────────┤
│  后端服务层                                                   │
│  StoryService  EventService  AssetService  AIService        │
├─────────────────────────────────────────────────────────────┤
│  数据存储层                                                   │
│  YAML Files   SQLite Database   JSON Manifest               │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 核心功能模块

### 3.1 Story Graph Editor (剧情图编辑器)

#### 核心功能
- **节点编辑器** - 创建、连接、编辑剧情节点
- **剧情分支设计** - 条件分支和选择节点
- **跨场景链接** - 主线/支线的跨场景节点连接
- **章节管理** - 章节划分和剧情流控制
- **叙事模板** - 预设剧情模板和快速启动

#### AI辅助功能
- 自动剧情节点生成
- 叙事连贯性检查
- 剧情冲突检测
- 智能剧情建议和补全

#### 数据结构
```typescript
interface StoryNode {
  id: string;
  type: 'start' | 'end' | 'choice' | 'event' | 'condition';
  name: string;
  description: string;
  requiredAssets: string[];
  conditions?: StoryCondition[];
  choices?: StoryChoice[];
  metadata: {
    chapter: string;
    tags: string[];
    author: string;
    created: Date;
  };
}

interface StoryGraph {
  nodes: Map<string, StoryNode>;
  edges: StoryEdge[];
  metadata: {
    name: string;
    description: string;
    version: string;
  };
}
```

### 3.2 Event Graph Editor (事件图编辑器)

#### 核心功能
- **条件触发编辑** - 可视化条件触发器设置
- **事件节点设计** - 动态事件的任务和奖励配置
- **事件链构建** - 串联相关事件形成事件链
- **实时预览** - 事件触发条件的实时测试
- **事件模板库** - 常见事件类型模板

#### AI辅助功能
- 自动事件生成建议
- 条件冲突检测和平滑化
- 事件平衡性分析
- 智能事件关联推荐

#### 数据结构
```typescript
interface EventNode {
  id: string;
  type: 'combat' | 'quest' | 'exploration' | 'social';
  name: string;
  triggerConditions: EventTrigger[];
  actions: EventAction[];
  rewards: EventReward[];
  assets: string[];
  metadata: {
    difficulty: number;
    priority: number;
    cooldown: number;
  };
}

interface EventTrigger {
  type: 'time' | 'location' | 'state' | 'custom';
  condition: any;
  priority: number;
}
```

### 3.3 Asset Tree Editor (资产树编辑器)

#### 核心功能
- **层级资产管理** - 树状结构的资产组织
- **资产生成配置** - Prompt、风格、参数配置
- **资产关联编辑** - 与剧情/事件的资产关联
- **可视化预览** - 资产的实时预览和管理
- **批量操作** - 资产的批量创建和编辑

#### 分类管理系统
- **剧情资产** (Story Assets) - 服务于固定剧情
- **事件资产** (Event Assets) - 服务于动态事件
- **环境资产** (Environment Assets) - 提供世界氛围

#### 数据结构
```typescript
interface AssetNode {
  id: string;
  name: string;
  type: 'story' | 'event' | 'environment';
  assetType: 'background' | 'object' | 'character';
  prompt: string;
  styleProfile: string;
  status: 'pending' | 'generating' | 'completed';
  metadata: {
    parentScene?: string;
    relatedStory?: string;
    relatedEvent?: string;
    tags: string[];
  };
}

interface AssetTree {
  root: AssetNode;
  classification: AssetClassification;
  metadata: {
    version: string;
    lastModified: Date;
  };
}
```

### 3.4 Culture & Constraint Editor

#### 核心功能
- **文化树构建** - 文明体系和价值层级设计
- **约束规则编辑** - 硬约束和软约束配置
- **候选系统管理** - 资产生成的候选池配置
- **风格一致性检查** - 文化约束的验证
- **约束测试** - 约束规则的实时测试

#### 数据结构
```typescript
interface CultureNode {
  id: string;
  name: string;
  description: string;
  values: string[];
  aestheticPrinciples: string[];
  childNodes: CultureNode[];
}

interface ConstraintNode {
  id: string;
  type: 'hard' | 'soft';
  rule: any;
  priority: number;
  applicableTypes: string[];
}
```

### 3.5 World Knowledge Graph Editor

#### 核心功能
- **图谱可视化** - 世界知识的图形化展示
- **关系编辑** - 节点间关系的创建和编辑
- **图谱查询** - 基于条件的图谱搜索
- **导入导出** - 知识图谱的导入导出功能

---

## 4. 界面设计

### 4.1 主界面布局

```
┌─────────────────────────────────────────────────────────────┐
│ File | Edit | View | AI Tools | Preview | Help               │
├───────────┬─────────────────────────────────────────────────┤
│           │                                                 │
│ Navigator │            Canvas Area                         │
│           │         (可视化编辑画布)                        │
│ 📁 Story  │                                                 │
│   ├─ Main │    ┌─────┐        ┌─────┐                     │
│   ├─ Branch│  ┌──┤NodeA ├──────┤NodeB├──┐                 │
│   └─ Side │  │  └─────┘        └─────┘  │                 │
│           │  │                            │                 │
│ 📁 Events │  └─────┐              ┌───────┘                 │
│   ├─ Combat│    ┌──┴──┐          │                         │
│   ├─ Quest│    │Event├──────────┘                         │
│   └─ Random│    └─────┘                                    │
│           │                                                 │
│ 📁 Assets │    ┌─────┐         ┌─────┐                    │
│   ├─ Story│  ┌─┤Asset├───────┬─┤Asset├─┐                 │
│   ├─ Event│  │ └─────┘       │ └─────┘ │                 │
│   └─ Environ│              │          │                  │
│           │                 │          │                  │
├───────────┼─────────────────────────────────────────────────┤
│           │                                                 │
│ Properties│          AI Assistant Panel                     │
│           │         (AI智能辅助面板)                        │
│ 📝 Node   │    💡 AI Suggestions:                          │
│ ├─ Name   │    → Consider adding a choice node here        │
│ ├─ Type   │    → Event trigger condition seems too strict  │
│ └─ Config │    → Asset could be reused in Scene B         │
│           │                                                 │
└───────────┴─────────────────────────────────────────────────┘
```

### 4.2 界面组件层次

```
App
├── Layout
│   ├── Sidebar (Navigator)
│   ├── Canvas (Main Editor)
│   ├── PropertiesPanel
│   └── AIAssistantPanel
├── Editors
│   ├── StoryGraphEditor
│   ├── EventGraphEditor
│   ├── AssetTreeEditor
│   ├── CultureTreeEditor
│   └── WorldKGEditor
└── Shared
    ├── Toolbar
    ├── StatusBar
    └── DialogManager
```

---

## 5. 技术实现方案

### 5.1 前端技术栈

```typescript
{
  "框架": "React 18 + TypeScript",
  "构建工具": "Vite",
  "图编辑器": "React Flow",
  "数据可视化": "D3.js",
  "代码编辑": "Monaco Editor",
  "状态管理": "Zustand",
  "UI组件": "Radix UI",
  "样式": "TailwindCSS",
  "实时协作": "Y.js",
  "路由": "React Router"
}
```

### 5.2 后端技术栈

```python
{
  "框架": "FastAPI",
  "数据验证": "Pydantic",
  "数据库": "SQLite + aiosqlite",
  "AI服务": "多LLM Provider",
  "文件存储": "YAML + JSON",
  "测试": "pytest + pytest-cov"
}
```

### 5.3 核心库选择理由

#### React Flow (图编辑器)
- 专为节点图编辑设计
- TypeScript原生支持
- 自定义节点能力强大
- 性能优秀，支持大型图

#### Zustand (状态管理)
- 轻量简洁
- TypeScript友好
- 无需Provider包装
- 易于学习和使用

#### Radix UI (组件库)
- 无障碍支持
- 高度可定制
- TypeScript原生
- 现代设计理念

---

## 6. AI辅助系统

### 6.1 AI助手功能架构

```typescript
interface AIAssistant {
  // 剧情辅助
  suggestPlotNodes(context: StoryContext): NodeSuggestion[];
  checkNarrativeConsistency(story: StoryGraph): ConsistencyReport;
  detectPlotHoles(story: StoryGraph): PlotHoleReport;
  
  // 事件辅助
  generateEventTriggers(context: WorldContext): TriggerSuggestion[];
  balanceEventDifficulty(events: EventGraph): BalanceReport;
  suggestEventConnections(events: EventGraph[]): ConnectionSuggestion[];
  
  // 资产生成
  suggestAssets(requirement: AssetRequirement): AssetCandidate[];
  optimizeAssetPrompt(prompt: string, culture: Culture): OptimizedPrompt;
  validateAssetConsistency(asset: Asset, culture: Culture): ValidationResult;
  
  // 约束检查
  validateConstraints(assets: Asset[], constraints: ConstraintTree): ValidationResult;
  detectCulturalConflicts(culture: Culture, assets: Asset[]): ConflictReport[];
  suggestConstraintOptimizations(constraints: ConstraintTree): Suggestion[];
}
```

### 6.2 AI服务API设计

```python
# AI辅助接口
@app.post("/api/ai/suggest-nodes")
async def suggest_story_nodes(request: NodeSuggestionRequest) -> NodeSuggestionResponse:
    """AI建议剧情节点"""
    
@app.post("/api/ai/check-consistency")
async def check_narrative_consistency(request: ConsistencyCheckRequest) -> ConsistencyReport:
    """检查叙事一致性"""
    
@app.post("/api/ai/suggest-assets")
async def suggest_assets(request: AssetSuggestionRequest) -> AssetSuggestionResponse:
    """AI建议资产生成"""
    
@app.post("/api/ai/optimize-prompt")
async def optimize_prompt(request: PromptOptimizationRequest) -> OptimizedPromptResponse:
    """AI优化资产生成提示词"""
```

---

## 7. 数据模型设计

### 7.1 后端数据模型

#### Story Graph Model
```python
# app/models/story_graph.py
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class StoryCondition(BaseModel):
    type: str
    requirement: any
    
class StoryChoice(BaseModel):
    text: str
    target_node: str
    conditions: List[StoryCondition] = []

class StoryNode(BaseModel):
    id: str
    type: str  # start, end, choice, event, condition
    name: str
    description: str
    required_assets: List[str] = []
    conditions: List[StoryCondition] = []
    choices: List[StoryChoice] = []
    metadata: Dict = {}

class StoryGraph(BaseModel):
    id: str
    name: str
    description: str
    nodes: Dict[str, StoryNode] = {}
    edges: List[Dict] = []
    metadata: Dict = {}
    version: str = "1.0"
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
```

#### Event Graph Model
```python
# app/models/event_graph.py
class EventTrigger(BaseModel):
    type: str  # time, location, state, custom
    condition: any
    priority: int = 1

class EventAction(BaseModel):
    type: str
    parameters: Dict = {}

class EventReward(BaseModel):
    type: str  # item, experience, story_unlock
    value: any
    probability: float = 1.0

class EventNode(BaseModel):
    id: str
    type: str  # combat, quest, exploration, social
    name: str
    trigger_conditions: List[EventTrigger] = []
    actions: List[EventAction] = []
    rewards: List[EventReward] = []
    assets: List[str] = []
    metadata: Dict = {}

class EventGraph(BaseModel):
    id: str
    name: str
    description: str
    nodes: Dict[str, EventNode] = {}
    global_triggers: List[EventTrigger] = []
    metadata: Dict = {}
```

### 7.2 前端数据模型

#### TypeScript类型定义
```typescript
// types/story.ts
export interface StoryNode {
  id: string;
  type: 'start' | 'end' | 'choice' | 'event' | 'condition';
  name: string;
  description: string;
  requiredAssets: string[];
  conditions?: StoryCondition[];
  choices?: StoryChoice[];
  metadata: StoryMetadata;
}

export interface StoryGraph {
  id: string;
  name: string;
  description: string;
  nodes: Record<string, StoryNode>;
  edges: StoryEdge[];
  metadata: GraphMetadata;
}

// types/event.ts
export interface EventNode {
  id: string;
  type: 'combat' | 'quest' | 'exploration' | 'social';
  name: string;
  triggerConditions: EventTrigger[];
  actions: EventAction[];
  rewards: EventReward[];
  assets: string[];
  metadata: EventMetadata;
}

// types/asset.ts
export interface AssetNode {
  id: string;
  name: string;
  type: 'story' | 'event' | 'environment';
  assetType: 'background' | 'object' | 'character';
  prompt: string;
  styleProfile: string;
  status: AssetStatus;
  metadata: AssetMetadata;
}
```

---

## 8. API接口设计

### 8.1 Story Graph API

```python
# 获取所有剧情图
@app.get("/api/story/graphs")
async def get_story_graphs() -> List[StoryGraph]:

# 获取单个剧情图
@app.get("/api/story/graphs/{graph_id}")
async def get_story_graph(graph_id: str) -> StoryGraph:

# 创建剧情图
@app.post("/api/story/graphs")
async def create_story_graph(graph: StoryGraphCreate) -> StoryGraph:

# 更新剧情图
@app.put("/api/story/graphs/{graph_id}")
async def update_story_graph(graph_id: str, graph: StoryGraphUpdate) -> StoryGraph:

# 删除剧情图
@app.delete("/api/story/graphs/{graph_id}")
async def delete_story_graph(graph_id: str) -> DeleteResponse:

# 导出剧情图
@app.get("/api/story/graphs/{graph_id}/export")
async def export_story_graph(graph_id: str, format: str = 'yaml') -> FileResponse:
```

### 8.2 Event Graph API

```python
# 事件图管理接口
@app.get("/api/events/graphs")
@app.get("/api/events/graphs/{graph_id}")
@app.post("/api/events/graphs")
@app.put("/api/events/graphs/{graph_id}")
@app.delete("/api/events/graphs/{graph_id}")

# 事件测试接口
@app.post("/api/events/test-trigger")
async def test_event_trigger(request: EventTestRequest) -> EventTestResponse:
    """测试事件触发条件"""
```

### 8.3 Asset Tree API

```python
# 资产树管理接口
@app.get("/api/assets/tree")
@app.get("/api/assets/{asset_id}")
@app.post("/api/assets")
@app.put("/api/assets/{asset_id}")
@app.delete("/api/assets/{asset_id}")

# 资产分类接口
@app.get("/api/assets/classified/{classification}")
async def get_assets_by_classification(classification: str) -> List[Asset]:
    """按分类获取资产：story/event/environment"""
```

### 8.4 AI辅助API

```python
# AI建议接口
@app.post("/api/ai/suggest-nodes")
@app.post("/api/ai/check-consistency")
@app.post("/api/ai/suggest-assets")
@app.post("/api/ai/optimize-prompt")
@app.post("/api/ai/validate-constraints")
```

---

## 9. 实现路线图

### Phase 1: 基础框架 (4-6周)

**目标**: 搭建编辑器基础架构

**任务清单**:
- [x] React项目架构搭建
- [x] React Flow图编辑器集成
- [x] 基础UI组件库搭建
- [x] Zustand状态管理系统
- [x] 后端API基础框架
- [x] YAML数据持久化系统
- [x] 基础路由和导航

**交付物**:
- 可运行的基础编辑器界面
- 基础CRUD API接口
- 前后端类型同步机制

### Phase 2: Story + Asset (6-8周)

**目标**: 实现核心编辑功能

**任务清单**:
- [x] Story Graph编辑器完整实现
- [x] 升级现有Asset Tree为分类管理
- [x] 节点编辑和连接功能
- [x] 属性面板和配置界面
- [x] 基础AI辅助功能
- [x] 数据导入导出功能

**交付物**:
- 完整的剧情图编辑器
- 升级的资产树编辑器
- 基础AI建议系统

### Phase 3: Event + Culture (8-10周)

**目标**: 完善五图模型

**任务清单**:
- [x] Event Graph编辑器实现
- [x] Culture Tree编辑器实现
- [x] Constraint Tree编辑器实现
- [x] 条件触发系统
- [x] 文化约束验证系统
- [x] 完整AI辅助系统

**交付物**:
- 完整的五图模型编辑器
- 智能约束验证系统
- AI驱动的创作助手

### Phase 4: 高级功能 (4-6周)

**目标**: 高级功能和优化

**任务清单**:
- [x] World Knowledge Graph集成
- [x] 实时协作功能
- [x] 高级AI功能
- [x] 性能优化和测试
- [x] 用户文档和教程

**交付物**:
- 完整功能的AI剧情编辑器
- 用户手册和开发文档
- 测试套件和质量保证

---

## 10. 风险评估与应对

### 10.1 技术风险

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| React Flow性能问题 | 高 | 中 | 提前进行性能测试，准备虚拟化方案 |
| AI API成本过高 | 中 | 高 | 实施本地缓存，优化API调用频率 |
| 数据同步冲突 | 高 | 中 | 实施乐观锁和冲突解决策略 |
| 复杂图编辑交互 | 中 | 高 | 提前进行用户测试，简化交互设计 |

### 10.2 项目风险

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| 开发周期延长 | 高 | 中 | 分阶段交付，MVP优先 |
| 用户需求变更 | 中 | 高 | 灵活的架构设计，模块化开发 |
| 团队技能不足 | 中 | 低 | 提供培训，引入外部专家 |

### 10.3 质量保证

**测试策略**:
- 单元测试覆盖率 ≥ 85%
- 集成测试覆盖关键用户流程
- E2E测试覆盖核心功能
- 性能测试确保大图编辑流畅
- 用户测试验证交互设计

**代码质量**:
- ESLint + TypeScript严格模式
- 代码审查制度
- 持续集成/持续部署
- 自动化测试运行

---

## 附录

### A. 术语表

| 术语 | 定义 |
|------|------|
| 五图模型 | Story Graph, Event Graph, Asset Tree, Culture Tree, Constraint Tree |
| 剧情资产 | 服务于固定剧情的资产 |
| 事件资产 | 服务于动态事件的临时资产 |
| 环境资产 | 提供世界氛围的背景资产 |
| 文化树 | 定义文明体系和价值层级的树状结构 |
| 约束树 | 定义资产生成限制条件的规则树 |

### B. 参考资料

- React Flow官方文档
- Zustand状态管理最佳实践
- AI辅助内容设计研究论文
- 游戏叙事设计理论

### C. 更新日志

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1.0 | 2026-08-01 | 初始设计文档 |

---

**文档状态**: ✅ 已完成初步设计  
**下一步**: 开始Phase 1基础框架开发  
**负责人**: 开发团队