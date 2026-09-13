# UGC 系统设计规范 (System Design Specification)

> **Schema First + Interface Contract + Domain Model Design**
>
> 本文档基于代码实际结构编写，非理论推导。所有接口签名、字段名、枚举值
> 均来自现有源码，可直接作为后续开发的契约基线。

---

## 目录

1. [系统全景架构图](#1-系统全景架构图)
2. [模块拆分总览](#2-模块拆分总览)
3. [各模块详细接口契约](#3-各模块详细接口契约)
4. [数据模型字典 (Domain Model)](#4-数据模型字典-domain-model)
5. [API 接口清单](#5-api-接口清单)
6. [数据流图](#6-数据流图)
7. [五图模型映射](#7-五图模型映射现状--目标)
8. [命名规范](#8-命名规范)

---

## 1. 系统全景架构图

```
                         ┌─────────────────────────────────────┐
                         │           前端 Frontend              │
                         │  Vite + React + TypeScript           │
                         │  ┌──────────┬──────────┬──────────┐ │
                         │  │ Terminal │ SceneView│ Graph UI  │ │
                         │  │ (交互)   │ (场景)   │ (图谱)   │ │
                         │  └────┬─────┴────┬─────┴────┬─────┘ │
                         │       │          │          │       │
                         │  ┌────▼──────────▼──────────▼────┐  │
                         │  │       API Client Layer        │  │
                         │  │  client.ts / graph.ts / assets│  │
                         │  └───────────────┬───────────────┘  │
                         └──────────────────┼──────────────────┘
                                            │ HTTP /api/*
                         ┌──────────────────▼──────────────────┐
                         │        后端 Backend (FastAPI)        │
                         │                                      │
                         │  ┌─────────────────────────────────┐ │
                         │  │         API Layer (api/)        │ │
                         │  │  routes.py   — 交互主回路       │ │
                         │  │  assets_routes.py — 资产管理    │ │
                         │  │  graph_routes.py — 知识图谱     │ │
                         │  └──────────┬──────────────────────┘ │
                         │             │                         │
                         │  ┌──────────▼──────────────────────┐ │
                         │  │     Orchestrator (编排层)        │ │
                         │  │  parse → judge → render → update │ │
                         │  ┠──┬───────┬────────┬─────────┬───┨ │
                         │  ┌──▼──┐ ┌───▼────┐ ┌─▼──────┐ ┌─▼─┐ │
                         │  │ AI  │ │ Engine │ │Services│ │St.│ │
                         │  │Layer│ │(规则)  │ │(生成)  │ │ate│ │
                         │  └──┬──┘ └───┬────┘ └───┬────┘ └─┬─┘ │
                         │     │        │          │        │    │
                         │  ┌──▼────────▼──────────▼────────▼──┐│
                         │  │         Models (数据模型)         ││
                         │  │  Pydantic — 唯一数据契约源        ││
                         │  └──────────────────────────────────┘│
                         │                                      │
                         │  ┌──────────────────────────────────┐│
                         │  │      Data Layer (data/)          ││
                         │  │  scenes/ gods/ objects/ rules/    ││
                         │  │  assets/ visual/                  ││
                         │  └──────────────────────────────────┘│
                         └──────────────────────────────────────┘
```

---

## 2. 模块拆分总览

### 2.1 模块清单

| # | 模块 | 路径 | 层级 | 职责 |
|---|------|------|------|------|
| M1 | **API Gateway** | `app/api/routes.py` | 接入层 | 玩家交互主回路：`POST /api/action` |
| M2 | **Asset API** | `app/api/assets_routes.py` | 接入层 | 资产 CRUD + 场景编排生成 |
| M3 | **Graph API** | `app/api/graph_routes.py` | 接入层 | 知识图谱提取/验证/保存/生成 |
| M4 | **Orchestrator** | `app/orchestrator.py` | 编排层 | 串联 parse→judge→render→update 全流程 |
| M5 | **Rules Engine** | `app/engine/rules_engine.py` | 业务逻辑 | 确定性判决（零AI调用） |
| M6 | **Physics Engine** | `app/engine/physics.py` | 业务逻辑 | 力量校验、伤害计算、能量消耗 |
| M7 | **God Intervention** | `app/engine/god_intervention.py` | 业务逻辑 | 神王干涉检查与惩罚 |
| M8 | **World Loader** | `app/engine/world_loader.py` | 业务逻辑 | YAML 场景/神王/规则数据加载 |
| M9 | **Intent Parser** | `app/ai/parser.py` | AI层 | 自然语言→结构化意图 |
| M10 | **Narrative Renderer** | `app/ai/renderer.py` | AI层 | 判决结果→叙事文本 |
| M11 | **Image Generator** | `app/ai/image_generator.py` | AI层 | 资产图像生成（多Provider） |
| M12 | **Style Extractor** | `app/ai/style_extractor.py` | AI层 | 场景风格提取 |
| M13 | **Graph Extractor** | `app/services/graph_extractor.py` | 服务层 | 文本→知识图谱（LLM提取） |
| M14 | **Generation Planner** | `app/services/generation_planner.py` | 服务层 | LOD感知的资产生成排序 |
| M15 | **Generation Scheduler** | `app/services/generation_scheduler.py` | 服务层 | 波次并行图像生成调度 |
| M16 | **Prompt Builder** | `app/services/prompt_builder.py` | 服务层 | 8层提示词模板组装 |
| M17 | **Prompt Fusion** | `app/services/prompt_fusion.py` | 服务层 | 图谱节点提示词融合 |
| M18 | **LLM Provider** | `app/ai/provider.py` | 基础设施 | 多LLM统一抽象（6家） |
| M19 | **State Repository** | `app/state/database.py` | 持久层 | 玩家状态 SQLite 持久化 |
| M20 | **Asset Store** | `app/state/asset_store.py` | 持久层 | 资产清单 JSON 存储 |
| M21 | **Graph Store** | `app/state/graph_store.py` | 持久层 | 知识图谱 SQLite 存储 |
| M22 | **Config / Paths** | `app/config/` | 基础设施 | 路径常量、特性开关 |
| M23 | **Models** | `app/models/` | 数据契约 | Pydantic 数据模型（唯一真相源） |
| M24 | **Frontend Components** | `frontend/src/` | 前端 | React UI 组件 |

### 2.2 层级依赖规则

```
接入层 (API)
    ↓ 依赖
编排层 (Orchestrator)
    ↓ 依赖
业务逻辑层 (Engine)     AI层 (ai/)        服务层 (services/)
    ↓                    ↓                  ↓
    └─────────────  数据模型层 (models/)  ──────────┘
                         ↓
持久层 (state/)      数据文件层 (data/)
```

**铁律：所有层依赖 models/，models/ 不依赖任何层。**

---

## 3. 各模块详细接口契约

### M1: API Gateway (`routes.py`)

```
路由前缀: /api
依赖: Orchestrator, StateRepository, WorldLoader, AssetStore
```

| 方法 | 路径 | 请求体 | 响应体 | 说明 |
|------|------|--------|--------|------|
| POST | `/api/action` | `ActionRequest` | `ActionResponse` | 玩家交互主入口 |
| GET | `/api/state` | `?player_id` | `PlayerState` | 查询玩家状态 |
| POST | `/api/reset` | `?player_id` | `PlayerState` | 重置玩家状态 |
| GET | `/api/scene` | `?scene_id` | `SceneResponse` | 获取场景+已审批资产 |
| GET | `/api/health` | — | `{status, service}` | 健康检查 |

---

### M2: Asset API (`assets_routes.py`)

```
路由前缀: /api/assets, /api/scenes
依赖: AssetStore, GenerationPlanner, ImageGenerator, StyleExtractor
```

| 方法 | 路径 | 请求体 | 响应体 | 说明 |
|------|------|--------|--------|------|
| GET | `/api/assets` | — | `{assets: Asset[]}` | 列出全部资产 |
| GET | `/api/assets/{id}` | — | `Asset` | 查单个资产 |
| POST | `/api/assets/{id}/generate` | — | `{task_id, status}` | 触发异步生成 |
| GET | `/api/assets/{id}/status` | — | `{status, generation_status}` | 查生成状态 |
| POST | `/api/assets/{id}/approve` | — | `Asset` | 审批通过 |
| POST | `/api/assets/{id}/reject` | `RejectBody` | `Asset` | 审批驳回 |
| PUT | `/api/assets/{id}/prompt` | `PromptBody` | `Asset` | 修改提示词 |
| POST | `/api/assets/generate-all` | — | `{triggered, task_ids}` | 批量生成 |
| POST | `/api/assets/bulk-approve` | — | `{approved: int}` | 批量审批 |
| POST | `/api/scenes/{id}/orchestrate` | — | `{order, triggered}` | 场景级编排生成 |
| GET | `/api/scenes/{id}/graph` | — | `{nodes, generation_order, style_sources}` | 场景图结构 |
| GET | `/api/scenes/{id}/orchestrate/status` | — | `{asset_id: status}` | 场景编排状态 |

---

### M3: Graph API (`graph_routes.py`)

```
路由前缀: /api/graph
依赖: GraphStore, GraphExtractor, GenerationScheduler, CycleDetector
```

| 方法 | 路径 | 请求体 | 响应体 | 说明 |
|------|------|--------|--------|------|
| POST | `/api/graph/extract` | `ExtractRequest` | `KnowledgeGraph.to_dict()` | LLM提取图谱 |
| POST | `/api/graph/validate` | `KnowledgeGraph` JSON | `ValidateResponse` | 环检测 |
| POST | `/api/graph/save` | `KnowledgeGraph` JSON | `SaveResponse` | 保存图谱 |
| GET | `/api/graph/{scene_id}` | — | `KnowledgeGraph.to_dict()` | 加载图谱 |
| DELETE | `/api/graph/{scene_id}` | — | `DeleteResponse` | 删除图谱 |
| POST | `/api/graph/generate` | `KnowledgeGraph` JSON | `GenerateResponse` | 触发波次生成 |

---

### M4: Orchestrator

```python
class Orchestrator:
    def __init__(
        self,
        parser: IntentParser,       # Protocol
        engine: RulesEngine,         # 具体类
        renderer: NarrativeRenderer, # Protocol
        state_repo: StateRepository, # Protocol
    ) -> None

    async def process_action(self, request: ActionRequest) -> ActionResponse
```

**内部流程:**
```
ActionRequest
    │
    ├─ 1. state_repo.get_state(player_id) → PlayerState
    ├─ 2. parser.parse(player_input) → ParsedIntent
    ├─ 3. engine.judge(intent, player) → JudgmentResult
    ├─ 4. _apply_state_changes(player, judgment) → PlayerState (copy)
    ├─ 5. state_repo.update_state(player_id, updated_player)
    ├─ 6. renderer.render(judgment, intent, context) → str
    │
    └→ ActionResponse
```

---

### M5: Rules Engine

```python
class RulesEngine:
    def __init__(self, loader: WorldLoader) -> None

    async def judge(
        self,
        intent: ParsedIntent,    # IN: 解析后的玩家意图
        player: PlayerState      # IN: 当前玩家状态
    ) -> JudgmentResult          # OUT: 判决结果
```

**判决流程:**
```
1. 加载场景 → Scene (含 accessible_objects)
2. 查找目标 → GameObject | None
3. 神王干涉检查 (is_future_anchor?) → FORCED_FAIL + penalty
4. 物理校验 (strength vs hardness) → SUCCESS | FAIL
5. 无目标 → SUCCESS (默认)
```

**确定性保证:** 零AI调用，相同输入100%相同输出。

---

### M6: Physics Engine

```python
# 纯函数，无状态
def check_strength_vs_hardness(player_strength: int, target_hardness: int) -> bool
def calculate_damage(force: int, resistance: int) -> int
def calculate_energy_cost(base_cost: int, intensity: str) -> int
```

**枚举值 (不允许添加或修改):**
```python
INTENSITY_MULTIPLIERS = {
    "low": 0.5,
    "medium": 1.0,
    "maximum": 1.5,
}
```

---

### M7: God Intervention

```python
def check_intervention(
    target_id: str,
    intervention_table: dict[str, str],
    gods: list[GodKing],
) -> GodKing | None

def apply_penalty(god: GodKing, player_id: str = "player") -> list[StateChange]
```

**惩罚规则:** `health_damage = god.penalty`, `stability_damage = god.penalty // 2`

---

### M8: World Loader

```python
class WorldLoader:
    def load_scene(self, scene_id: str) -> Scene
    def load_gods(self) -> list[GodKing]
    def load_intervention_table(self) -> dict[str, str]
```

**数据源:**
- 场景: `data/scenes/{scene_id}.yaml`
- 神王: `data/gods/gods_table.yaml`
- 干涉表: `data/rules/intervention_table.yaml`

---

### M9: Intent Parser

```python
class IntentParser:
    def __init__(self, provider: LLMProvider) -> None

    async def parse(self, player_input: str) -> ParsedIntent
```

**降级策略:** LLM 解析失败 → `ActionType.PROBE, intensity="low", confidence=0.0`

---

### M10: Narrative Renderer

```python
class NarrativeRenderer:
    def __init__(self, provider: LLMProvider) -> None

    async def render(
        self,
        judgment: JudgmentResult,
        intent: ParsedIntent,
        context: dict[str, object],
    ) -> str
```

**降级策略:** LLM 渲染失败 → `"[SYSTEM] 判决完成。结果：{outcome}。原因：{reason}"`

---

### M11: Image Generator

```python
class ImageGenerator:
    _VALID_PROVIDERS = frozenset({"zhipu", "wanxiang", "qwen", "local"})

    async def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        asset_id: str = "",
        reference_asset_ids: list[str] | None = None,
    ) -> list[GeneratedImage]

    async def close(self) -> None
```

```
GeneratedImage:
    seed: int
    image_data: bytes = b""
    url: str | None = None
    file_path: str | None = None
```

---

### M13: Graph Extractor

```python
class GraphExtractor:
    def __init__(self) -> None  # 内部创建 LLMProvider

    async def extract_from_text(self, scene_description: str) -> dict[str, Any]
    def to_knowledge_graph(self, raw_data: dict) -> KnowledgeGraph
```

**LLM 输出格式:**
```json
{
  "background": {"description": "..."},
  "nodes": [
    {"serial": "1", "description": "...", "parent_serial": null},
    {"serial": "1-1", "description": "...", "parent_serial": "1"}
  ],
  "edges": [
    {"from": "1-1", "to": "2-1", "edge_type": "cross", "visual_description": ""}
  ]
}
```

---

### M14: Generation Planner

```python
class GenerationPlanner:
    def create_plan(self, scene_id: str) -> GenerationPlan
```

```
AssetGenerationSpec:
    asset_id: str
    lod_level: str | None        # "near" | "mid" | "far" | None(bg)
    prompt: str
    reference_asset_ids: list[str]

GenerationPlan:
    scene_id: str
    order: list[str]             # 拓扑排序后的资产ID序列
    specs: dict[str, AssetGenerationSpec]
```

**排序优先级:**
```
_DEPTH_TO_LOD = {"near": "near", "mid": "mid", "mid_far": "far", "far": "far"}
_LOD_PRIORITY = {"near": 0, "mid": 1, "far": 2, "bg": 3}
```

**规则:** BG 永远在最后生成。物体间按 LOD 优先级 + 拓扑序排列。

---

### M15: Generation Scheduler

```python
class GenerationScheduler:
    def __init__(self, max_concurrency: int = 3) -> None

    async def run_generation(self, graph: KnowledgeGraph) -> dict
```

**返回值:**
```python
{
    "total": int,
    "succeeded": int,
    "failed": int,
    "order": list[str],    # 实际执行顺序
    "error": str | None,   # 环检测错误时存在
}
```

**流程:** 环检测 → 拓扑分波 → 波内并行(asyncio.gather + Semaphore) → 波间串行

---

### M16: Prompt Builder

```python
class PromptBuilder:
    def build(
        self,
        asset_id: str,        # "{scene_id}_{object_id}"
        lod_level: str,       # "far" | "mid" | "near"
        context: dict | None = None,
    ) -> str
```

**8层提示词结构:**
```
World → Location → Camera → Subject → GameplayFunction → InteractionDetails → Material → Lighting
```

**数据源:**
- 模板: `data/visual/prompts.yaml`
- 色板: `data/visual/palette.yaml`
- 风格圣经: `data/visual/style_bible.md`
- 场景: `data/scenes/{scene_id}.yaml`

---

### M17: Prompt Fusion

```python
class PromptFusion:
    def build_prompt(
        self,
        node: GraphNode,
        graph: KnowledgeGraph,
        completed_nodes: dict[str, GraphNode],
    ) -> str
```

**3段融合:**
```
Section 1: Subject     — 目标节点自身 description
Section 2: Relation    — 已完成父节点的 edge.visual_description
Section 3: Background  — 背景节点的 description（色调/光照上下文）
```

---

### M18: LLM Provider

```python
class LLMProvider(ABC):
    async def chat(self, messages: list[dict[str, str]], **kwargs) -> str
    async def chat_json(self, messages: list[dict[str, str]], **kwargs) -> dict[str, Any]
```

**实现类:**

| 类名 | 支持的 Provider | SDK |
|------|----------------|-----|
| `OpenAICompatibleProvider` | openai, deepseek, qwen, kimi, glm | `openai` |
| `AnthropicProvider` | anthropic | `anthropic` |

**工厂函数:**
```python
def create_provider(config: ProviderConfig) -> LLMProvider
```

---

### M19: State Repository (Protocol)

```python
@runtime_checkable
class StateRepository(Protocol):
    async def init_db(self) -> None
    async def get_state(self, player_id: str = "player_001") -> PlayerState | None
    async def update_state(self, player_id: str, state: PlayerState) -> None
    async def reset_state(self, player_id: str = "player_001") -> PlayerState
    async def close(self) -> None
```

**实现:** `app/state/database.py → StateRepository` (SQLite via aiosqlite)

---

### M20: Asset Store

```python
class AssetStore:
    def __init__(self, path: Path | None = None) -> None  # 默认 data/assets/manifest.json

    def list_assets(self) -> list[Asset]
    def get_asset(self, asset_id: str) -> Asset | None
    def update_asset(self, asset_id: str, **fields) -> Asset    # 抛 InvalidTransitionError
    def init_from_scene(self, scene_id: str) -> None            # 从场景YAML初始化清单
```

**状态机 (不允许添加或修改):**
```
PENDING ──────→ GENERATING ──────→ COMPLETED ──────→ APPROVED
   ↑                 │                  │                 
   │                 ├──→ FAILED ───────┘ (→ PENDING)
   │                 ├──→ CANDIDATES_READY ──→ SELECTED ──→ APPROVED
   │                 └──→ FAILED
   │
   REJECTED ─────────→ PENDING
```

合法转移集合 (`_ALLOWED_TRANSITIONS`):
```
(PENDING, GENERATING)
(GENERATING, COMPLETED)
(GENERATING, FAILED)
(GENERATING, CANDIDATES_READY)
(COMPLETED, APPROVED)
(COMPLETED, REJECTED)
(COMPLETED, GENERATING)      # 重新生成
(CANDIDATES_READY, SELECTED)
(CANDIDATES_READY, GENERATING)
(SELECTED, APPROVED)
(SELECTED, REJECTED)
(REJECTED, PENDING)
(REJECTED, GENERATING)
(FAILED, PENDING)
(FAILED, GENERATING)
(APPROVED, PENDING)          # 审批撤销
```

---

### M21: Graph Store

```python
class GraphStore:
    def __init__(self, db_path: Path | str | None = None) -> None  # 默认 data/assets/graph.db

    async def init_db(self) -> None
    async def save_graph(self, graph: KnowledgeGraph) -> None      # Upsert (先删后插)
    async def load_graph(self, scene_id: str) -> KnowledgeGraph
    async def delete_graph(self, scene_id: str) -> None
    async def update_node_status(self, scene_id, node_id, status) -> None
```

**数据库表:**
```sql
graph_nodes (id, scene_id, serial_number, level, description, status, is_background, created_at)
graph_edges (id, scene_id, from_node_id, to_node_id, edge_type, visual_description, created_at)
```

---

## 4. 数据模型字典 (Domain Model)

> **唯一真相源: `app/models/*.py` (Pydantic v2)**
> 前端镜像: `frontend/src/types/*.ts`

### 4.1 核心模型关系图

```
 ┌──────────────┐         ┌──────────────────┐
 │ ActionRequest│────────▶│   ParsedIntent    │
 │ (api.py)     │         │   (action.py)     │
 └──────────────┘         └────────┬──────────┘
                                   │
                          ┌────────▼──────────┐
                          │  JudgmentResult   │
                          │   (action.py)     │
                          └────────┬──────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
           ┌────────▼──────┐ ┌─────▼──────┐ ┌────▼──────────┐
           │ NarrativeCtx  │ │StateChange │ │ PlayerState   │
           │ (action.py)   │ │(action.py) │ │ (player.py)   │
           └───────────────┘ └────────────┘ └───────────────┘

 ┌──────────────┐    contains    ┌──────────────────┐
 │    Scene     │───────────────▶│   GameObject     │
 │  (world.py)  │                │   (world.py)     │
 └──────┬───────┘                └──────────────────┘
        │ has
        ├──────────────┐
        │              │
 ┌──────▼──────┐ ┌─────▼──────────────┐
 │ WorldRule   │ │ InteractionTarget  │
 │ (world.py)  │ │ (world.py)         │
 └─────────────┘ └────────────────────┘

 ┌──────────────┐
 │   GodKing    │
 │  (world.py)  │
 └──────────────┘

 ┌──────────────┐  belongs to   ┌──────────────────┐
 │    Asset     │──────────────▶│  Candidate       │
 │ (asset.py)   │  has many     │  (asset.py)      │
 └──────┬───────┘               └──────────────────┘
        │ has
 ┌──────▼──────────────┐
 │ SceneStyleProfile   │
 │ (asset.py)          │
 └─────────────────────┘

 ┌──────────────────────┐
 │ KnowledgeGraph       │  contains  ┌──────────────┐
 │ (knowledge_graph.py) │───────────▶│ GraphNode    │
 └──────────┬───────────┘            │ (knowledge_  │
            │ has many               │  graph.py)   │
            │                        └──────────────┘
 ┌──────────▼───────────┐
 │ GraphEdge            │
 │ (knowledge_graph.py) │
 └──────────────────────┘

 ┌──────────────────────┐  contains  ┌──────────────┐
 │ PuzzleGraph          │───────────▶│ PuzzleNode   │
 │ (puzzle_graph.py)    │            │(puzzle_graph │
 └──────────────────────┘            │   .py)       │
                                      └──────────────┘

 ┌──────────────────────┐  contains  ┌──────────────┐
 │ SceneGraph           │───────────▶│ AssetInfo    │
 │ (scene_graph.py)     │            │(scene_graph  │
 └──────────────────────┘            │   .py)       │
                                      └──────────────┘
```

### 4.2 枚举字典 (Schema 合约 — 不允许随意修改)

| 枚举 | 文件 | 值 |
|------|------|-----|
| `ActionType` | action.py | `brute_force`, `stealth`, `read_memory`, `negotiate`, `probe`, `god_provoke`, `investigate` |
| `JudgmentOutcome` | action.py | `success`, `fail`, `forced_fail`, `partial`, `god_intervention` |
| `PlayerStatus` | player.py | `normal`, `injured`, `exhausted`, `dying`, `dead`, `echo_active`, `echo_overload` |
| `AssetStatus` | asset.py | `pending`, `generating`, `completed`, `approved`, `rejected`, `failed`, `candidates_ready`, `selected` |
| `AssetType` | asset.py | `background`, `object` |
| `NodeStatus` | knowledge_graph.py | `pending`, `generating`, `completed`, `failed` |
| `EdgeType` | knowledge_graph.py | `tree`, `cross` |
| `PuzzleNodeType` | puzzle_graph.py | `clue`, `consumable`, `reward`, `obstacle` |

### 4.3 核心模型字段速查

#### ParsedIntent
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action_type | ActionType | ✓ | 动作类别 |
| target | str \| None | | 目标对象ID |
| intensity | "low"\|"medium"\|"maximum" | ✓ | 强度 |
| risk_acceptance | bool | ✓ | 风险接受 |
| tool_used | str \| None | | 使用工具 |
| raw_input | str | ✓ | 原始输入 |
| confidence | float [0,1] | ✓ | 解析置信度 |

#### JudgmentResult
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| result | JudgmentOutcome | ✓ | 判决结果 |
| reason | str | ✓ | 人类可读原因 |
| damage | int ≥0 | | 伤害值 |
| state_changes | list[StateChange] | | 状态变更列表 |
| god_intervention | str \| None | | 干涉神王名 |
| narrative_context | NarrativeContext | ✓ | 叙事上下文 |
| echo_triggered | bool | | 是否触发回声 |

#### PlayerState
| 字段 | 类型 | 范围 | 说明 |
|------|------|------|------|
| id | str | — | 玩家ID |
| energy | int | 0-100 | 体力 |
| health | int | 0-100 | 生命 |
| strength | int | 0-100 | 力量 |
| intelligence | int | 0-100 | 智力 |
| echo_mode_enabled | bool | — | 回声视觉 |
| mental_stability | int | 0-100 | 精神稳定 |
| location | str | — | 当前场景ID |
| inventory | list[str] | — | 物品ID列表 |
| status | PlayerStatus | — | 状态 |
| max_energy | int | ≥0 | 最大体力 (默认100) |
| max_health | int | ≥0 | 最大生命 (默认100) |

#### Scene
| 字段 | 类型 | 说明 |
|------|------|------|
| scene_id | str | 唯一标识 |
| name | str | 显示名称 |
| description | str | 描述文本 |
| atmosphere | str | 氛围 |
| accessible_objects | list[GameObject] | 场景内对象 |
| interaction_targets | list[InteractionTarget] | 可交互点 |
| region | str \| None | 所属世界规则区域 |

#### GameObject
| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | 唯一标识 |
| name | str | 显示名称 |
| type | str | 类别 (door/container/item...) |
| hardness | int 0-100 | 抗交互强度 |
| energy_cost | int ≥0 | 交互消耗 |
| is_future_anchor | bool | 是否时间固定点 |
| description | str | 描述 |
| position | {x:float, y:float} \| None | 百分比坐标 |

#### Asset
| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | 资产ID (`{scene_id}_{obj_id}`) |
| type | AssetType | background \| object |
| name | str | 名称 |
| prompt | str | 生成提示词 |
| negative_prompt | str | 负面提示词 |
| status | AssetStatus | 生命周期状态 |
| generation_status | str | 管道状态 |
| file_path | str \| None | 文件路径 |
| parent_scene | str | 所属场景ID |
| seed | int \| None | 生成种子 |
| candidates | list[Candidate] | 候选图列表 |
| selected_candidate_index | int \| None | 选中候选 |
| reference_asset_ids | list[str] | 参考资产 |
| style_profile | SceneStyleProfile \| None | 风格档案 |
| views | dict \| None | LOD视图 `{far:{}, mid:{}, near:{}}` |
| lod_level | str \| None | 当前LOD |
| puzzle_role | str \| None | 谜题角色 |
| parent_object | str \| None | 父对象ID |
| depth | str \| None | 深度层级 |

#### KnowledgeGraph
| 字段 | 类型 | 说明 |
|------|------|------|
| scene_id | str | 场景ID |
| nodes | dict[str, GraphNode] | 节点字典 |
| edges | list[GraphEdge] | 边列表 |
| background_node_id | str \| None | 背景根节点 |

#### GraphNode
| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | 节点ID (= serial_number) |
| serial_number | str | 层级序号 (如 "1-1-1") |
| level | int | 深度 (段数+1) |
| description | str | 视觉描述 |
| status | NodeStatus | 生命周期 |

#### PuzzleNode
| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | 节点ID |
| type | PuzzleNodeType | clue/consumable/reward/obstacle |
| requires | list[str] | 前置条件 |
| produces | str | 产出物品名 |
| interaction | str | 玩家交互类型 |

---

## 5. API 接口清单

### 5.1 完整端点列表

```
# 交互主回路
POST   /api/action                    玩家输入 → AI解析 → 规则判决 → 叙事渲染

# 玩家状态
GET    /api/state                     查询玩家状态
POST   /api/reset                     重置玩家状态

# 场景
GET    /api/scene                     获取场景 + 已审批资产

# 资产管理
GET    /api/assets                    列出全部资产
GET    /api/assets/{id}               查单个资产
POST   /api/assets/{id}/generate      触发单个资产生成
GET    /api/assets/{id}/status        查生成状态
POST   /api/assets/{id}/approve       审批通过
POST   /api/assets/{id}/reject        审批驳回
PUT    /api/assets/{id}/prompt        修改提示词
POST   /api/assets/generate-all       批量生成
POST   /api/assets/bulk-approve       批量审批

# 场景编排
POST   /api/scenes/{id}/orchestrate             场景级编排生成
GET    /api/scenes/{id}/graph                   场景图结构
GET    /api/scenes/{id}/orchestrate/status      场景编排状态

# 知识图谱
POST   /api/graph/extract             LLM提取图谱
POST   /api/graph/validate            环检测
POST   /api/graph/save                保存图谱
GET    /api/graph/{scene_id}          加载图谱
DELETE /api/graph/{scene_id}          删除图谱
POST   /api/graph/generate            触发波次生成

# 静态资源
GET    /assets/{filename}             生成图像文件

# 系统
GET    /api/health                    健康检查
GET    /docs                          Swagger UI
```

### 5.2 请求/响应体 Schema

#### ActionRequest → ActionResponse
```json
// Request
{
  "player_input": "我强行砸开这个锁",
  "player_id": "player_001",
  "current_scene": "temple_ruins"
}

// Response
{
  "judgment": {
    "result": "forced_fail",
    "reason": "神王Chronos the Order干涉...",
    "damage": 40,
    "state_changes": [...],
    "god_intervention": "Chronos the Order",
    "narrative_context": {
      "scene_id": "temple_ruins",
      "previous_action": "我强行砸开这个锁",
      "active_gods": ["Chronos the Order"],
      "atmosphere": "Melancholy, ancient...",
      "tension_level": 80
    },
    "echo_triggered": false
  },
  "narrative": "[赛博朋克风格叙事文本...]",
  "updated_state": { "id": "player_001", "health": 60, ... },
  "parsed_intent": {
    "action_type": "brute_force",
    "target": "ancient_locked_door",
    "intensity": "maximum",
    "risk_acceptance": true,
    ...
  },
  "echo_vision": null,
  "available_actions": []
}
```

---

## 6. 数据流图

### 6.1 玩家交互主回路

```
玩家输入 "我强行砸开这个锁"
    │
    ▼
┌─────────┐     ┌──────────┐     ┌───────────┐     ┌──────────┐
│ Frontend │────▶│ POST     │────▶│Orchestrator│────▶│ Intent   │
│ Terminal │     │ /api/    │     │           │     │ Parser   │
└─────────┘     │ action   │     └─────┬─────┘     │ (LLM)    │
                └──────────┘           │           └──────────┘
                                       │ ParsedIntent
                                       ▼
                                ┌───────────┐
                                │  Rules    │  确定性判决
                                │  Engine   │  (零AI)
                                └─────┬─────┘
                                      │ JudgmentResult
                    ┌─────────────────┼──────────────────┐
                    │                 │                  │
                    ▼                 ▼                  ▼
              ┌──────────┐    ┌────────────┐    ┌──────────────┐
              │ State    │    │ Narrative   │    │ God          │
              │ Update   │    │ Renderer    │    │ Intervention │
              │ (SQLite) │    │ (LLM)       │    │ (表查询)     │
              └──────────┘    └────────────┘    └──────────────┘
                                      │
                                      ▼ narrative text
                              ┌──────────────┐
                              │ ActionResponse│
                              └──────┬───────┘
                                     │
                                     ▼
                              ┌─────────────┐
                              │  Frontend   │  打字机效果输出
                              │  Terminal   │
                              └─────────────┘
```

### 6.2 资产生成管道

```
                        ┌───────────────────┐
                        │ 场景 YAML 定义     │
                        │ data/scenes/*.yaml│
                        └────────┬──────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
             ┌──────────┐ ┌──────────┐ ┌──────────────┐
             │SceneGraph│ │PuzzleGraph│ │ KnowledgeGraph│
             │(空间依赖) │ │(谜题依赖) │ │ (LLM提取)    │
             └─────┬────┘ └─────┬────┘ └──────┬───────┘
                   │            │             │
                   └────────────┼─────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ GenerationPlanner    │  合并依赖 + LOD排序
                     │ create_plan(scene_id)│
                     └──────────┬──────────┘
                                │ GenerationPlan
                                │ {order, specs}
                                ▼
                     ┌─────────────────────┐
                     │ AssetStore           │  初始化清单
                     │ manifest.json        │
                     └──────────┬──────────┘
                                │
                    ┌───────────┼───────────┐
                    │ (逐资产)  │           │
                    ▼           ▼           ▼
              ┌──────────────────────────────┐
              │  对每个 asset:                │
              │  1. PromptBuilder.build()     │  8层提示词
              │  2. StyleExtractor (bg→obj)   │  风格传递
              │  3. ImageGenerator.generate() │  调用API
              │  4. AssetStore.update()       │  状态流转
              └──────────────────────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ 审批流程              │
                     │ approve / reject     │
                     └─────────────────────┘
```

### 6.3 知识图谱生成管道

```
自由文本场景描述
    │
    ▼
┌──────────────┐     ┌───────────────┐
│ POST         │────▶│GraphExtractor │  LLM提取
│ /api/graph/  │     │ (JSON输出)    │
│ extract      │     └──────┬────────┘
└──────────────┘            │ raw dict
                            ▼
                    ┌───────────────┐
                    │to_knowledge_  │  转换
                    │graph()        │
                    └──────┬────────┘
                           │ KnowledgeGraph
                           ▼
                    ┌───────────────┐
                    │ CycleDetector │  环检测
                    │ validate()    │
                    └──────┬────────┘
                           │ valid?
                     ┌─────┴─────┐
                     │ YES       │ NO → 422 Error
                     ▼           │
              ┌─────────────┐    │
              │ GraphStore  │    │
              │ save_graph()│    │
              └──────┬──────┘    │
                     │           │
                     ▼           │
              ┌──────────────────┐
              │ GenerationScheduler│
              │ (波次并行生成)     │
              │                   │
              │ For each wave:    │
              │   asyncio.gather( │
              │     node1, node2, │
              │     node3...      │
              │   )               │
              └─────────┬────────┘
                        │
                        ▼
              ┌──────────────────┐
              │ GenerateResponse │
              │ {total, succeeded,│
              │  failed, order}   │
              └──────────────────┘
```

---

## 7. 五图模型映射 (现状 → 目标)

### 7.1 现有图谱资产盘点

| 图谱 | 模型 | 文件 | 数据源 | 拓扑算法 |
|------|------|------|--------|----------|
| **SceneGraph** | `scene_graph.py` | YAML | `data/scenes/*.yaml` | Kahn (空间依赖 + anchor优先) |
| **PuzzleGraph** | `puzzle_graph.py` | YAML | `data/scenes/*.yaml` | Kahn (谜题类型优先) |
| **KnowledgeGraph** | `knowledge_graph.py` | SQLite | LLM提取 + 手动 | 波次拓扑 |
| **Scene YAML** | 隐式 | YAML | `data/scenes/*.yaml` | — |

### 7.2 五图模型对应关系

```
用户目标架构                          当前项目对应
══════════════                       ══════════════

Culture Tree (文化树)          ←──    【不存在】❌ 
  "古代魔法文明→图腾→水晶祭坛"        当前无文化约束系统
  影响资产生成候选                     需新增: data/cultures/*.yaml

Constraint Tree (约束树)       ←──    【部分存在】⚠️
  "禁止钢铁/电力"                     WorldRule.physical_constraints
  硬性过滤候选                         存在但未接入生成管道

Story Graph (剧情图)           ←──    【部分存在】⚠️
  固定主线/支线                        PuzzleGraph (puzzle_chain)
  有叙事目的                           但只有谜题链，无完整故事节点

Event Graph (事件图)            ←──    【不存在】❌
  条件触发的动态事件                   当前无动态事件系统
  时间/天气/区域 → 触发                需新增: data/events/*.yaml

Asset Tree (资产树)            ←──    【存在】✅
  空间存在 + LOD层级                   SceneGraph + Asset.views
  背景/物体/LOD视图                    AssetStore (manifest.json)
```

### 7.3 差距分析

```
当前状态:                                目标状态 (五图模型):

  WorldRule (约束碎片)                    Culture Tree (完整文化约束体系)
       │                                      │
       ▼                                      ▼
  Scene YAML                              Constraint Tree (硬性过滤)
       │                                      │
       ├─→ SceneGraph (空间)                     ├─→ Story Graph (固定剧情)
       │                                      │
       ├─→ PuzzleGraph (谜题链) ────────────────┤─→ Event Graph (动态事件)
       │                                      │
       └─→ KnowledgeGraph (LLM提取) ────────────┤─→ Asset Tree (空间资产)
                                                 │
                                                 ▼
                                          Asset Classification
                                          ┌─────┬───────┐
                                          │     │       │
                                       剧情资产 事件资产  环境资产
```

### 7.4 需要新增的模块

| 新模块 | 路径建议 | 依赖 | 优先级 |
|--------|---------|------|--------|
| `CultureTree` | `app/models/culture.py` + `data/cultures/` | — | P1 |
| `ConstraintTree` | `app/models/constraint.py` + `data/constraints/` | CultureTree | P1 |
| `StoryGraph` | `app/models/story_graph.py` + `data/stories/` | Scene, GameObject | P2 |
| `EventGraph` | `app/models/event_graph.py` + `data/events/` | PlayerState, Scene | P3 |
| `AssetClassifier` | `app/services/asset_classifier.py` | StoryGraph, EventGraph, AssetTree | P3 |

### 7.5 现有模块升级清单

| 模块 | 当前 | 升级目标 |
|------|------|---------|
| `WorldRule` | 散落的 physical_constraints 列表 | 接入 ConstraintTree，作为硬过滤层 |
| `PuzzleGraph` | 仅 puzzle_chain 谜题依赖 | 升级为 StoryGraph 的子图，补充叙事节点 |
| `GenerationPlanner` | SceneGraph + PuzzleGraph 合并 | 加入 CultureTree 约束 + ConstraintTree 过滤 |
| `PromptBuilder` | 8层模板 (World→Lighting) | 增加 Culture 层和 Constraint 层 |
| `Asset` | puzzle_role 字段已有雏形 | 增加 asset_class: story/event/environment |

---

## 8. 命名规范

### 8.1 ID 命名规则 (Schema 合约)

| 实体 | ID 格式 | 示例 |
|------|---------|------|
| 场景 | `{snake_case_name}` | `temple_ruins` |
| 背景资产 | `{scene_id}_bg` | `temple_ruins_bg` |
| 物体资产 | `{scene_id}_{object_id}` | `temple_ruins_priest_corpse_01` |
| 图谱节点 | `{serial_number}` | `1`, `1-1`, `1-1-1` |
| 谜题节点 | `{node_id}` (来自YAML) | `priest_corpse_01` |
| 神王 | `{snake_case_id}` | `chronos_order` |
| 玩家 | `player_{number}` | `player_001` |

### 8.2 文件命名规则

```
data/
├── scenes/{scene_id}.yaml              # 场景定义
├── gods/gods_table.yaml                # 神王表
├── objects/{object_id}.yaml            # 物体详情
├── rules/intervention_table.yaml       # 干涉表
├── assets/
│   ├── manifest.json                   # 资产清单
│   ├── {asset_id}.png                  # 生成图像
│   ├── meta/{asset_id}.json            # 生成元数据
│   ├── candidates/{asset_id}_c{N}.png  # 候选图像
│   └── graph.db                        # 图谱数据库
├── visual/
│   ├── prompts.yaml                    # 提示词模板
│   ├── palette.yaml                    # 色板
│   └── style_bible.md                  # 风格圣经
├── default_player.json                 # 默认玩家状态
└── demo_scripts.md                     # 演示脚本
```

### 8.3 代码命名规则

| 类型 | 规则 | 示例 |
|------|------|------|
| Python 类 | PascalCase | `RulesEngine`, `ParsedIntent` |
| Python 函数 | snake_case | `check_intervention`, `load_scene` |
| Python 常量 | UPPER_SNAKE | `INTENSITY_MULTIPLIERS` |
| Python 私有 | 前缀 `_` | `_build_result`, `_load_prompts` |
| TypeScript 类型 | PascalCase | `PlayerState`, `GraphNode` |
| TypeScript 接口 | PascalCase | `ActionRequest`, `SceneResponse` |
| TS 联合类型 | snake_case 值 | `"brute_force" \| "stealth"` |
| YAML 字段 | snake_case | `scene_id`, `is_future_anchor` |
| API 路径 | kebab-case 或 snake | `/api/assets/{id}/generate` |
| 文件名 | snake_case.py / PascalCase.tsx | `rules_engine.py`, `Terminal.tsx` |

---

## 附录 A: 依赖注入架构

```
                    ┌──────────────────────────┐
                    │      app/main.py         │
                    │   FastAPI lifespan       │
                    └────────────┬─────────────┘
                                 │ 注册路由
                    ┌────────────▼─────────────┐
                    │     api/deps.py          │
                    │  (Protocol + @lru_cache) │
                    └────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
  ┌───────────────┐    ┌─────────────────┐   ┌──────────────────┐
  │ get_world_    │    │ get_llm_        │   │ get_state_       │
  │ loader()      │    │ provider()      │   │ repository()     │
  │ → WorldLoader │    │ → LLMProvider   │   │ → StateRepository│
  └───────┬───────┘    └───────┬─────────┘   └──────────────────┘
          │                    │
          ▼            ┌───────┼───────┐
  ┌───────────────┐    │       │       │
  │ get_rules_    │    ▼       ▼       ▼
  │ engine()      │  Parser  Renderer  ImageGen
  │ → RulesEngine │
  └───────────────┘
```

**Protocol 接口 (Duck Typing):**
- `StateRepository` — 状态持久化协议
- `IntentParser` — 意图解析协议
- `NarrativeRenderer` — 叙事渲染协议

**单例缓存:**
- `@lru_cache(maxsize=1)` → `get_world_loader`, `get_rules_engine`, `get_llm_provider`
- 懒加载 → `get_state_repository`, `get_intent_parser`, `get_narrative_renderer`

---

## 附录 B: 场景 YAML Schema (完整字段)

```yaml
# data/scenes/{scene_id}.yaml
scene_id: string                    # 必填，唯一标识
name: string                        # 必填，显示名
description: string                 # 必填，场景描述
atmosphere: string                  # 必填，氛围
region: string                      # 可选，世界规则区域
viewpoint: string                   # 可选，视角描述

depth_layers:                       # 可选，LOD分层定义
  - name: string                    # "near" | "mid" | "far"
    description: string

puzzle_chain:                       # 可选，谜题依赖链
  - node_id: string                 # 必填
    type: string                    # "clue" | "consumable" | "reward" | "obstacle"
    requires: [string]              # 前置节点ID或产出物名
    produces: string                # 产出物品名
    interaction: string             # 玩家交互类型

accessible_objects:                 # 必填，场景内物体
  - id: string                      # 必填
    name: string                    # 必填
    type: string                    # 必填 (door/container/item/interactive/decoration...)
    hardness: int                   # 必填 (0-100)
    energy_cost: int                # 必填 (≥0)
    is_future_anchor: bool          # 必填，是否时间固定点
    description: string             # 必填
    position:                       # 可选
      x: float                      # 0-100 百分比
      y: float                      # 0-100 百分比
    depth: string                   # 可选 "near"|"mid"|"mid_far"|"far"
    lod:                            # 可选，LOD描述
      far: string
      mid: string
      near: string
    puzzle_role: string             # 可选
    parent_object: string           # 可选，父物体ID
    new_assets_hint: string         # 可选，生成提示

interaction_targets:                # 可选，可交互点
  - object_id: string               # 必填，引用 GameObject.id
    is_dangerous: bool              # 必填
    required_tools: [string] | null # 可选
```

---

*文档版本: 1.0 | 基于 commit 时点的实际源码结构*
