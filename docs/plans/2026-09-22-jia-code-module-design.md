# 甲：代码模块设计 v1（新架构实施蓝图）

> **定位**：`2026-09-22-jia-modular-architecture-design.md`（v2）的**代码层映射**——每个架构概念落到哪个文件、什么类、什么签名。M1b-M4 施工的直接依据。
> **约束**：HALT 已解除（2026-09-24，D17）——本文档为现行施工设计，代码可动工（自 M1a 起）；⭐=待产品方终审项——**终审前按各默认值施工，冻结对应数据前须终审**。
> **日期**：2026-09-22 ｜ 分支 v2-modular（基线 eb22a6f）

---

## 1. 目标代码结构总览

```
backend/app/domains/creation/
├── shared/
│   ├── module_registry.py      ★新 [M1b] 路由真相源（池+配方+通道）
│   ├── graph_federation.py     ★新 [M3]  联邦知识库层（锚点索引+跨图边）
│   └── tier_map.py             改 [M1b] 池扩展（断言改"池内必有"）
├── a1/
│   ├── guide_engine.py         改 [M1b/M2] 配方遍历+M11/M12 键+素材槽迁移
│   ├── interviewer.py          改 [M1b/M2] prompt 目录配方感知（:183/:202）
│   ├── graphify.py             改 [M1b] 锚点校验=配方并集（:239/:474）
│   ├── story_modules.py        ★新 [M2] M11 角色 + M12 剧情数据定义
│   ├── inference_pack.py       ★新 [M4b] 推断包（DN5 后）
│   ├── opening_narrative.py    ★新 [M2] 开场叙事（DN5 后）
│   ├── content_guard.py        ★新 [M2] 爱情型合规护栏（同批强制）
│   └── live_projection.py      ★新 [M4c] 半成品投影（零新 LLM）
├── modules/                    ★新域 [M3]
│   ├── upstream_loader.py      上游只读装载（A2 回收）
│   ├── dice_projector.py       L2·骰子（零 LLM 四步法）
│   ├── character_projector.py  L2·角色（4 相位）
│   ├── module_finalizer.py     L2·主模组（八步+确定性降级）
│   ├── module_text_exporter.py L2·九节树导出
│   ├── gameplay_designer.py    L2·玩法完整形态（载体分支 schema）
│   ├── analysis_report.py      L2·商业分析（R 码，RAG 三库喂料）
│   ├── scene_expander.py       L3·场景扩写（S 码）
│   ├── asset_pipeline.py       L3·资产管线（状态机）
│   └── narrative_renderer.py   L3·叙事渲染（renderer.py 遗迹复活）
└── seed/
    └── a1_question_tree.py     改 [M1b] 门面函数配方参数化（MODULES 数据零改动）

backend/app/api/
├── a1_routes.py                改 [M1b] 六处全集引用+门禁+M11/M12 键
└── modules_routes.py           ★新 [M3] 产出端点族

backend/tests/unit/
├── a1/test_module_registry.py  ★新 [M1b] 8+1 配方矩阵
├── a1/test_story_modules.py    ★新 [M2]
├── modules/test_*.py           ★新 [M3] 每产出模块一件
└── ...（契约测试重梳见 §7）

frontend/src/pages/a1/
├── A1Workspace.tsx             改 [M2/M3] 配方感知+产出工作台入口
├── graph/ZoomBar.tsx           ★新 [M3] 变焦滑杆（一条故事线三层看）
├── graph/ProvenanceBadge.tsx   ★新 [M3] 源徽章+被引用清单
└── modules/                    ★新 [M3] 产出工作台（GraphSelector 重建+骰子/角色/文字版/场景视图）
```

---

## 2. 核心新模块设计（签名级）

### 2.1 `shared/module_registry.py` [M1b——一切的数据源]

```python
# 唯一路由真相源（R2：差异是数据不是代码）
module_ids: Final[list[str]]           # M1-M12 编号序（问卷树 10 + story_modules 2）

class ModuleDef(TypedDict):
    id: str                            # 中文 id 逐字（问卷树/story_modules 权威）
    level: Literal["L1", "L2", "L3"]
    family: Literal["worldbuilding", "story", "output"]
    fields: NotRequired[list[SubField]]       # L1 采集模块必填（引用不复制）
    tier: NotRequired[int]                     # L1 入 W 图层映射（DN2）
    signal_requirements: NotRequired[dict[str, Literal["required","optional","hard"]]]  # L2/L3 产出模块

class Recipe(TypedDict):
    impulse_type: str                  # 8 型 id | "default"
    module_ids: list[str]              # 有序子集（DN1/DN6）
    entry_subfield: tuple[str, str] | None
    anchor: str
    ai_fill_policy: list[str]
    deliverables: list[str]
    guard_flags: list[str]             # 如 "content_guard"(爱情), "low_pressure"(疗愈)

class Channel(TypedDict):
    channel_id: Literal["explore", "gameplay_line"]
    entry_flow: list[str]
    exit_to: str                       # 归宿配方 id

RECIPES: dict[str, Recipe]             # 8 + default（数据源=架构 v2 §3.1，⭐插位定稿后冻结）
CHANNELS: dict[str, Channel]
DEFAULT_RECIPE: Recipe                 # 原 10 模块全集原序

def get_recipe(impulse_type: str) -> Recipe: ...        # 未知/空 → DEFAULT，永不抛
def get_channel(channel_id: str) -> Channel: ...
def recipe_module_ids(session) -> list[str]: ...        # 消费方统一入口
def recipe_anchor_keys(session) -> set[str]: ...        # 配方并集（graphify 校验/fills 白名单用）
def entry_subfield_for(session) -> tuple[str, str] | None: ...
```

### 2.2 `a1/story_modules.py` [M2]

```python
# M11/M12 数据定义（字段集=产品方定版/拓展文档 ⭐ 终审后逐字冻结）
STORY_MODULES: list[Module] = [
    {"id": "角色", "fields": [
        {"id": "身份", ...}, {"id": "欲望"}, {"id": "缺陷"},
        {"id": "关键关系"}, {"id": "弧光方向"}, {"id": "角色视觉"},
    ]},
    {"id": "剧情", "fields": [
        {"id": "开场事件"}, {"id": "核心抉择"}, {"id": "张力源"},
        {"id": "线索链"}, {"id": "秘密维度"}, {"id": "分支预案"},
        {"id": "人物绑定"}, {"id": "走向基调"}, {"id": "场景挂载"},
    ]},
]
# 注入问卷树门面：注册进 module_registry.MODULE_POOL；a1_question_tree.MODULES 零改动
```

### 2.3 `shared/graph_federation.py` [M3——联邦知识库层]

```python
# 一个知识库 = 三层图联邦；本模块是粘合剂（查询时组装，不落大 blob）
CROSS_EDGE_TYPES = ("DERIVES_FROM", "REALIZES")   # 封闭枚举扩展（D14 台账）

def build_anchor_refs(file_rec: dict) -> dict[str, dict]: ...
    # finalize 时确定性构建反查索引：anchor → {"W":[节点id...], "M":[...], "S":[...]}
    # 数据源：W 图 d:{anchor} 节点 + 产物 source_anchors[] + S 场景挂载——纯遍历，零 LLM

def cross_edges(file_id: str) -> list[CrossEdge]: ...
    # DERIVES_FROM: 产物节点 → W 锚点（source_anchors 平铺）
    # REALIZES:     S 场景节点 → M 章节节点（parent 链）

def trace_up(node_ref: NodeRef) -> list[NodeRef]: ...   # 任意节点上溯到采集现场（含用户原话）
def trace_down(anchor: str) -> list[NodeRef]: ...        # 采集字段下钻到最终产物
def impact_preview(changed_anchors: list[str]) -> ImpactReport: ...
    # 改答案的影响预览：沿血缘枚举将 stale 的 M/S/R 产物（UX 触点 5 数据源）

def validate_cross_edges(file_id: str) -> list[str]: ...  # C10：DERIVES_FROM 的 anchor 必在源图答案集
```

### 2.4 `modules/` 域 [M3——L2/L3 产出]

```python
# upstream_loader.py（全域共用，A2 回收）
def load_upstream(file_id: str) -> UpstreamFacts: ...
    # 已定稿 W 图 + answers 快照 + stale 检查（不阻断）+ used_stale 留痕

# dice_projector.py（零 LLM）
class DiceProjector:
    SIGNALS = {"骰子设定.probability": "required", ..., "力量体系.cost": "optional"}
    def project(self, facts: UpstreamFacts) -> DiceTemplate: ...   # 四步法，signal_sources 逐字段溯源
    def missing(self, facts) -> list[str]: ...                      # → 409 upstream_missing

# character_projector.py（零 LLM；hard 依赖 dice 产物 → 409 missing_dice_template）
# module_finalizer.py（八步：校验→装载→[增强线 module_compile 或跳过]→装配→发号→注册→ledger→持久化）
#   免费线零 LLM=确定性骨架；LLM 失败→骨架+ledger 披露（DN4a 默认 H 稿）
# module_text_exporter.py（九节树 → Markdown/JSON）
# gameplay_designer.py（玩法完整形态）
class GameplayDesigner:
    CARRIER_SCHEMAS = {"trpg": ..., "video_game": ..., "interactive_fiction": ..., "tactics": ...}
    def decide_carrier(self, file_id, choice: str) -> ...          # 显式选择，AI 只供成本对照
    def build_full_form(self, facts, carrier: str) -> GameplayPackage: ...  # M8+/M9+ 按载体分支
    def consistency_check(self, package) -> Report: ...            # 机制→公理 反向回查
# analysis_report.py（商业分析 R 码；RAG 三库喂料：案例库 lesson/题材反模式/亲和矩阵）
# scene_expander.py（L3：M 图+scope+counts → S 码场景族；GEO_CONTAINS 铁律）
# asset_pipeline.py（状态机 pending→generating→pending_review→approved/rejected；Wave 轮询）
# narrative_renderer.py（朗读框文本；renderer.py 遗迹模式复活；未生产场景=迷雾）
```

---

## 3. 存量改造点（六处全集引用 + 三个扩展点）

| # | 位置 | 现状 | 改造 |
|---|---|---|---|
| 1 | a1_routes.py:1137 finalize 门禁 | `for mid in module_ids()` 全集 | `for mid in recipe_module_ids(session)`；missing_sections 只列配方内 |
| 2 | graphify.py:239/:474 锚点校验 | `set(all_subfield_keys())` | `recipe_anchor_keys(session)`（签名需传入 session/recipe 上下文——调用链级改造） |
| 3 | guide_engine.py:101 `first_module()` 默认 | 全集首模块 | `get_recipe(session).module_ids[0]` + entry_subfield 前置 |
| 4 | a1_routes.py:958 `_build_sections` | 遍历 MODULES | 配方序 |
| 5 | ip_poster.py:8,39-40 展板 panels | import MODULES 全集 | 配方感知（故事会话含 M11/M12 panels） |
| 6 | worldview_upload.py:193-200 上传 schema | 全集渲染进 prompt | default 配方不变；故事型×上传=DN6 默认不暴露 |
| 7 | tier_map.py:12-34 | 闭集断言==module_ids() | "池内必有 tier"；M11→文明层/M12→历史线层（DN2⭐） |
| 8 | interviewer.py:183/:202 prompt 目录 | 全集渲染 | 配方渲染（防泄露，M0 偏转规则已有条件注入先例） |
| 9 | store.py | sessions/files 两字典 | 零改动（默认值先例）；files.rec 增 `artifacts` 五键 + `scenes` 实例键控（.get 防御读取） |

---

## 4. API 端点设计

| 端点 | 层 | 波次 | 说明 |
|---|---|---|---|
| POST `/api/a1/session/start` | 存量改 | M1b | 增 `recipe_id` 解析落定（impulse→recipe 查表） |
| GET `/api/a1/file/{id}` | 存量改 | M3 | 增 `anchor_refs`（触点 3 数据）+ `impact_hint` |
| POST `/api/modules/session/start` | L2 | M3 | 声明上游事实源开产出会话 |
| POST `/api/modules/file/{id}/finalize` | L2 | M3 | 主模组八步（409 族照搬：pending_finalize/upstream_missing） |
| GET `/api/modules/file/{id}/doc` | L2 | M3 | 九节树 markdown/json（DN4c 已裁决 = doc，D15；界面显示名「文档输出」） |
| POST `/api/modules/file/{id}/dice-template` | L2 | M3 | 骰子投影（缺料 409） |
| POST `/api/modules/file/{id}/character-template` | L2 | M3 | 角色（缺骰子 409 missing_dice_template） |
| POST `/api/modules/file/{id}/gameplay/decide` + `/build` | L2 | M3 | 玩法链载体决策+完整形态 |
| GET `/api/modules/file/{id}/analysis` | L2 | M3 | 商业分析报告 R |
| POST `/api/modules/file/{id}/scenes` | L3 | M3 | 场景扩写（counts+scope） |
| GET `/api/modules/file/{id}/scenes/{s_code}` | L3 | M3 | 单场景（含朗读框候选） |
| GET `/api/a1/file/{id}/graph/preview` | L1 | M4c | live_projection |

---

## 5. 前端模块设计

| 组件 | 职责 | 依托 |
|---|---|---|
| `ZoomBar.tsx` | 一条故事线三层变焦（W 素材/M 骨架/S 演出），层级徽章+血缘跳转 | anchor_refs + cross_edges |
| `ProvenanceBadge.tsx` | 源徽章（hover 出处）+ 被引用 N 处清单 | NodeDetailPanel 扩展"来源"段 |
| `modules/` 工作台 | GraphSelector 重建（选上游事实源）→ 产出配置 → 产物视图（骰子卡/角色卡/文字版/场景卡） | modules_routes |
| A1Workspace 扩展 | 影响预览弹窗（改答案→stale 波及清单）；配方进度条 | impact_hint |
| 访谈微反馈 | 触点 1"已入图谱"行 | answers 写入回调 |

---

## 6. 实施波次映射（代码模块 → 甲计划任务）

| 波次 | 拿到的代码模块 |
|---|---|
| M1b | module_registry.py / tier_map 改 / 六处引用改造（§3 全部）/ test_module_registry |
| M2 | story_modules.py / guide_engine+interviewer M11/M12 消费 / content_guard / opening_narrative（DN5 后）/ 前端配方进度 |
| M3 | modules/ 域十件 / graph_federation.py / modules_routes.py / store artifacts+scenes / 前端 ZoomBar+Provenance+工作台 |
| M4a | field_sources 四出口 / coordinates / telemetry v2 |
| M4b | inference_pack.py / Q2 / 看门狗 / ai_fill 字段级 |
| M4c | live_projection.py / 人格卡 / sunset 接口 |

## 7. 测试映射（每模块一测 + 契约扩展）

- test_module_registry：8+1 矩阵逐型（首模块/entry/anchor/ai_fill/deliverable）；default 逐字节等价回归
- test_story_modules：M11/M12 字段契约 + 配方插入断言（⭐ 终审文案后冻结）
- modules/test_*：投影确定性（同输入同输出）/ 409 依赖链 / 降级骨架+ledger / 九节树 GM 可读 / S 码 GEO_CONTAINS 铁律 / 资产状态机全路径
- test_graph_federation：anchor_refs 构建 / trace_up/down 贯通 / C10 跨图边合法性
- 契约重梳：C3 配方子集 / C8 确定性快照 / C9 产物隔离 / **C10 跨图边**（新增）

---

## 8. 待终审依赖（⭐ 阻塞点汇总）

| 项 | 阻塞谁 | 默认案 |
|---|---|---|
| M12/M11 字段文案终审 | M2 story_modules 冻结 | 拓展文档初稿 |
| 8+2 配方插位（§3.1 ⭐ 处） | M1b RECIPES 数据冻结 | 插位提案 |
| DN1 门禁子集语义 | M1b 门禁改造 | 不适用 |
| DN2 tier 映射 | M1b tier_map | M11→文明层/M12→历史线层 |
| DN5 LLM 清单（5 生产方） | opening_narrative/scene_render/module_compile/inference_pack | 立项后开写 |
| ScopeBoundary 归并 | M3 scene_expander | 双层边界并存⭐ |
