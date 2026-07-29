# 场景一致性资产生成系统 (v2)

## TL;DR

> **Quick Summary**: 6 个 Task / 3 波并行，将孤立生成改造为"多候选选择 + Prompt 语义风格链 + 极简依赖排序"。Feature Flag 保护，可一键回退。砍掉 base64 参考图和图论模型，接受"结构自动化 + 语义人工抽检"。
> 
> **Deliverables**:
> - 后端：Asset+Candidate 模型扩展 / SceneGraph 极简依赖列表 / StyleProfile 提取+Prompt 注入 / 候选存储+选择 API / 场景编排 API / Feature Flag
> - 前端：CandidateGrid 独立组件 / SceneGraphPage 独立路由 / AssetReview 集成
> 
> **Estimated Effort**: Medium-Large (~30h)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Task 1 → Task 3 → Task 6 (~18h)

---

## Context

### v1 → v2 关键变更

| 维度 | v1 | v2 | 理由 |
|------|----|----|------|
| Task 数 | 11 个串行 | **6 个 / 3 波** | 压缩依赖链 |
| 参考图 | base64 优先 | **删除，纯 Prompt 注入** | API 需公网 URL；base64 未验证 |
| SceneGraph | nodes+edges 图论 | **极简依赖列表** | 节点 <20，YAGNI |
| 风格传递 | `list[str]` tokens | **结构化 StyleProfile** | 分维度约束，非关键词堆砌 |
| 状态机 | 不变 | **+CANDIDATES_READY +SELECTED** | COMPLETED 语义不再模糊 |
| 前端 | 全塞 AssetReview | **拆 CandidateGrid + SceneGraphPage** | 关注点分离 |
| 降级 | 无 | **Feature Flag** | 风格注入可一键关闭 |
| 验证 | "ZERO HUMAN" | **结构自动 + 语义人工抽检** | Playwright 测不了 AI 图片随机性 |

---

## Work Objectives

### Core Objective
背景优先 → 提取 StyleProfile → 物体继承风格 → 用户从多候选挑选 → 全场景视觉统一。

### Must Have
- 多候选生成（n=4）+ 全部存储 + 用户选择
- SceneStyleProfile 五维度提取 + Prompt 前缀注入
- SceneGraph 拓扑排序保证背景先生成
- Feature Flag 降级机制
- 新状态 CANDIDATES_READY / SELECTED

### Must NOT Have (Guardrails)
- 不上传图片到公网图床
- 不使用 base64 参考图
- 不引入 ControlNet / CLIP / networkx / D3.js
- 不引入数据库迁移
- 不自动选候选（用户必须手动）
- 不在 AssetReview.tsx 堆叠所有功能

---

## Verification Strategy

| 层级 | 方法 | 目标 |
|------|------|------|
| 模型序列化 | pytest | 新字段默认值 + 旧 manifest 兼容 |
| API 结构 | curl bash | JSON 字段存在 + 类型正确 |
| UI 结构 | Playwright DOM 断言 | 网格数量、按钮状态、路由可达 |
| 语义质量 | **人工抽检** | 随机抽 2 场景目视风格一致性 |
| Feature Flag | pytest | 关闭时行为 100% 不变 |
| 回滚 | bash | 删 candidates/ 后已 approve 资产正常 |

---

## Execution Strategy

```
Wave 1 (Foundation, 全并行):
├── Task 1: Asset 模型扩展 + 候选存储 [deep]
└── Task 2: SceneGraph 极简模型 + Kahn 拓扑排序 [deep]

Wave 2 (Core Backend, Wave1 完成后内部并行):
├── Task 3: 多候选 API + 选择端点 + 状态流转 (depends: 1) [deep]
├── Task 4: StyleProfile 提取 + Prompt 注入 + Feature Flag (depends: 1) [deep]
└── Task 5: 场景编排 API (depends: 2) [deep]

Wave 3 (Frontend + Integration):
└── Task 6: 前端全部实现 + 集成验证 (depends: 3, 4, 5) [deep]
```

| Task | Depends | Blocks | 估算 |
|------|---------|--------|------|
| 1 | — | 3, 4 | 4h |
| 2 | — | 5 | 3h |
| 3 | 1 | 6 | 6h |
| 4 | 1 | 6 | 5h |
| 5 | 2 | 6 | 4h |
| 6 | 3,4,5 | FINAL | 8h |

---

## TODOs

- [x] 1. Asset 模型扩展 + 候选存储 + Feature Flag 配置

  **What to do**:
  - 在 `backend/app/models/asset.py` 新增 `Candidate` 子模型（`index: int`、`seed: int`、`file_path: Optional[str]`、`url: Optional[str]`、`score: Optional[float] = None`）
  - 新增 `SceneStyleProfile` 模型（`palette: list[str]`、`lighting: dict`、`material: list[str]`、`rendering: dict`、`atmosphere: dict`）— 五维度结构化风格
  - `Asset` 模型新增字段：`candidates: list[Candidate] = Field(default_factory=list)`、`selected_candidate_index: Optional[int] = None`、`reference_asset_ids: list[str] = Field(default_factory=list)`、`style_profile: Optional[SceneStyleProfile] = None`
  - `AssetStatus` 枚举新增：`CANDIDATES_READY = "candidates_ready"`、`SELECTED = "selected"`
  - `Asset.url` computed_field 更新：若 `selected_candidate_index` 非空且索引有效 → 返回选中候选 URL；否则回退到 `file_path` 推导
  - `_ALLOWED_TRANSITIONS` 新增：`(GENERATING, CANDIDATES_READY)`、`(CANDIDATES_READY, SELECTED)`、`(SELECTED, APPROVED)`、`(SELECTED, REJECTED)`、`(CANDIDATES_READY, GENERATING)`（重新生成）
  - Pydantic `@field_validator` 确保旧 manifest 缺新字段时自动补默认值
  - 新建 `backend/app/config/features.py`：`SCENE_CONSISTENCY = os.getenv("FEATURE_SCENE_CONSISTENCY", "true").lower() == "true"`
  - 创建 `data/assets/candidates/` 目录结构
  - 修改 `ImageGenerator._download_image()`：多候选存到 `data/assets/candidates/{asset_id}/{asset_id}_{model}_{timestamp}_{index}.png`

  **Must NOT do**:
  - 不引入 SQLAlchemy/数据库迁移
  - 不删除或破坏任何现有字段
  - 不改变已有 approved 资产的存储位置

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1, with Task 2)
  - **Blocks**: Tasks 3, 4
  - **Blocked By**: None

  **References**:
  - `backend/app/models/asset.py:1-100` — 现有 Asset 模型 + url computed_field，核心扩展点
  - `backend/app/state/asset_store.py:37-50` — `_ALLOWED_TRANSITIONS` 状态转换表，需新增转换
  - `backend/app/state/asset_store.py:77-110` — `update_asset()` 方法，需确认新字段写入
  - `data/assets/manifest.json` — 现有数据格式，新字段需向后兼容（旧条目无 candidates/style_profile）
  - `backend/app/ai/image_generator.py:427-476` — 现有 `_download_image()`，需适配 candidates 目录
  - `backend/app/main.py:50-53` — StaticFiles 挂载，验证覆盖 candidates/ 子目录

  **Acceptance Criteria**:
  - [ ] `python -c "from app.models.asset import Asset; a = Asset(id='t', type='background', name='t', parent_scene='s'); print(a.candidates, a.selected_candidate_index, a.reference_asset_ids, a.style_profile)"` 输出 `[] None [] None`
  - [ ] 现有 `manifest.json` 被新模型加载不报 ValidationError（旧条目自动 candidates=[] style_profile=None）
  - [ ] `AssetStatus.CANDIDATES_READY` 和 `AssetStatus.SELECTED` 可用
  - [ ] `from app.config.features import SCENE_CONSISTENCY` 不报错
  - [ ] `data/assets/candidates/` 目录存在

  **QA Scenarios**:
  ```
  Scenario: 旧 manifest 向后兼容
    Tool: Bash (python)
    Steps:
      1. cd backend && .venv\Scripts\python -c "from app.state.asset_store import AssetStore; s=AssetStore(); assets=s.list_assets(); print(len(assets),'loaded'); [print(a.id, a.status, len(a.candidates)) for a in assets[:3]]"
    Expected Result: 输出资产数量 > 0，每条 candidates=[] 不报错
    Failure Indicators: ValidationError 或 AttributeError
    Evidence: .sisyphus/evidence/task-1-backward-compat.txt

  Scenario: 新状态枚举可用
    Tool: Bash (python)
    Steps:
      1. .venv\Scripts\python -c "from app.models.asset import AssetStatus; print(AssetStatus.CANDIDATES_READY.value, AssetStatus.SELECTED.value)"
    Expected Result: 输出 candidates_ready selected
    Evidence: .sisyphus/evidence/task-1-new-status.txt

  Scenario: Feature Flag 可读取
    Tool: Bash (python)
    Steps:
      1. .venv\Scripts\python -c "from app.config.features import SCENE_CONSISTENCY; print('FLAG:', SCENE_CONSISTENCY)"
    Expected Result: 输出 FLAG: True（或 False 取决于 .env）
    Evidence: .sisyphus/evidence/task-1-feature-flag.txt

  Scenario: 候选目录静态服务可达
    Tool: Bash (curl)
    Preconditions: 后端运行
    Steps:
      1. curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/assets/candidates/nonexist.png
    Expected Result: 404（目录存在但文件不存在），不是 500
    Evidence: .sisyphus/evidence/task-3-static-serve.txt
  ```

  **Commit**: YES (groups with Task 2)
  - Message: `feat(models): Asset candidates + SceneStyleProfile + SceneGraph + AssetStatus`
  - Files: `backend/app/models/asset.py`, `backend/app/state/asset_store.py`, `backend/app/config/features.py`, `backend/app/ai/image_generator.py`
  - Pre-commit: `cd backend && .venv\Scripts\python -c "from app.models.asset import Asset"`

---

- [x] 2. SceneGraph 极简模型 + YAML 解析 + Kahn 拓扑排序

  **What to do**:
  - 新建 `backend/app/models/scene_graph.py`
  - 极简数据结构（不用图论库）：
    ```python
    class AssetInfo(BaseModel):
        id: str
        name: str
        type: str  # background | object
        status: str
        is_future_anchor: bool = False

    class SceneGraph(BaseModel):
        scene_id: str
        nodes: dict[str, AssetInfo]
        generation_order: list[str]       # 拓扑排序结果
        style_sources: dict[str, list[str]]  # asset_id -> [参考资产ID]
    ```
  - 从 `data/scenes/*.yaml` 解析：背景 `{scene_id}_bg` 为核心节点；物体从 `accessible_objects` 解析
  - `style_sources` 规则：每个物体的 style_source = `[scene_id + "_bg"]`（背景是唯一风格来源）
  - Kahn 算法拓扑排序（~20行）：背景入度为0 → 先输出；物体依赖背景 → 背景之后输出
  - `is_future_anchor: true` 的物体排在非 anchor 物体之前（优先级）
  - 环检测：发现环时抛出 `ValueError` 并回退到列表原始顺序

  **Must NOT do**:
  - 不引入 networkx 等图论库
  - 不解析 scene YAML 中不相关字段（hardness, energy_cost 等）
  - 不加 narrative_link / spatial_link 等额外边类型（YAGNI）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1, with Task 1)
  - **Blocks**: Task 5
  - **Blocked By**: None

  **References**:
  - `data/scenes/temple_ruins.yaml:1-60` — 场景定义，含 accessible_objects + position + is_future_anchor
  - `backend/app/state/asset_store.py:14-17` — `_PROJECT_ROOT` 和 `_SCENES_DIR` 路径定义
  - `backend/app/state/asset_store.py:24-34` — `_load_prompts()` YAML 加载模式参考
  - `data/assets/manifest.json` — 资产 ID 命名规则：`{scene_id}_bg`、`{scene_id}_{object_id}`

  **Acceptance Criteria**:
  - [ ] `SceneGraph.from_yaml("temple_ruins").generation_order[0] == "temple_ruins_bg"`
  - [ ] `SceneGraph.from_yaml("temple_ruins").style_sources["temple_ruins_priest_corpse_01"]` 包含 `"temple_ruins_bg"`
  - [ ] `is_future_anchor=True` 的物体（ancient_locked_door, holographic_altar）排在普通物体之前
  - [ ] 环检测：构造循环依赖数据时抛出 ValueError

  **QA Scenarios**:
  ```
  Scenario: 拓扑排序正确性
    Tool: Bash (python)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         from app.models.scene_graph import SceneGraph
         g = SceneGraph.from_yaml('temple_ruins')
         print('order:', g.generation_order)
         assert g.generation_order[0] == 'temple_ruins_bg', 'Background must be first'
         print('OK')
         "
    Expected Result: 背景在 generation_order[0]，物体在其后
    Failure Indicators: 背景不在首位，或列表为空
    Evidence: .sisyphus/evidence/task-2-topo-sort.txt

  Scenario: 风格参考关系正确
    Tool: Bash (python)
    Steps:
      1. .venv\Scripts\python -c "
         from app.models.scene_graph import SceneGraph
         g = SceneGraph.from_yaml('temple_ruins')
         refs = g.style_sources.get('temple_ruins_priest_corpse_01', [])
         print('refs:', refs)
         assert 'temple_ruins_bg' in refs
         print('OK')
         "
    Expected Result: 物体的 style_sources 包含背景 ID
    Evidence: .sisyphus/evidence/task-2-style-sources.txt

  Scenario: anchor 优先级
    Tool: Bash (python)
    Steps:
      1. .venv\Scripts\python -c "
         from app.models.scene_graph import SceneGraph
         g = SceneGraph.from_yaml('temple_ruins')
         order = g.generation_order
         # anchor 物体应在非 anchor 物体之前
         door_idx = order.index('temple_ruins_ancient_locked_door')
         corpse_idx = order.index('temple_ruins_priest_corpse_01')
         assert door_idx < corpse_idx, f'anchor should come first: {door_idx} vs {corpse_idx}'
         print('OK')
         "
    Expected Result: is_future_anchor=True 的物体排在前面
    Evidence: .sisyphus/evidence/task-2-anchor-priority.txt
  ```

  **Commit**: YES (groups with Task 1)
  - Message: `feat(models): add SceneGraph with topological generation order`
  - Files: `backend/app/models/scene_graph.py`

---

- [x] 3. 多候选 API + 选择端点 + 状态流转

  **What to do**:
  - 改造 `assets_routes.py` 的 `_run_generation()`：不再 `first = results[0]`，把全部 results 转为 `Candidate[]` 存入 `asset.candidates`
  - 生成完成后的状态流转改为：`GENERATING → CANDIDATES_READY`（不再是 COMPLETED）
  - 新增 `POST /api/assets/{id}/select-candidate`：body `{"index": N}`
    - 设置 `selected_candidate_index = N`
    - 联动更新 `file_path` 和 `seed` 为候选 N 的值
    - 状态流转：`CANDIDATES_READY → SELECTED`
  - `Asset.url` computed_field 自动返回选中候选的 URL（Task 1 已实现）
  - 批量生成 `generate-all`：感知 Feature Flag，若 `SCENE_CONSISTENCY=true` 则提示用编排 API 代替
  - 状态为 `CANDIDATES_READY` 时 approve/reject 按钮不可用（前端逻辑在 Task 6）
  - `generate()` 的 `num_candidates` 从环境变量 `IMAGE_NUM_CANDIDATES`（默认 4）读取

  **Must NOT do**:
  - 不自动选第一张候选 — 等用户手动选择
  - 不删除旧的单图逻辑路径（向后兼容已有 approved 资产走 file_path）
  - 不修改 generate-all 为强制编排

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 2, with Task 4, 5)
  - **Blocks**: Task 6
  - **Blocked By**: Task 1

  **References**:
  - `backend/app/api/assets_routes.py:35-94` — `_run_generation()` 函数，核心改造点（第 70 行 `first = results[0]`）
  - `backend/app/api/assets_routes.py:37-50` — `_ALLOWED_TRANSITIONS` 需新增 CANDIDATES_READY/SELECTED 相关转换
  - `backend/app/state/asset_store.py:77-110` — `update_asset()` 方法，需支持写 candidates 数组
  - `backend/app/models/asset.py` — Task 1 扩展后的模型（Candidate + AssetStatus）

  **Acceptance Criteria**:
  - [ ] `POST /api/assets/{id}/generate` 后轮询 `GET /api/assets/{id}` → `status == "candidates_ready"` 且 `candidates` 数组长度 == 4
  - [ ] `POST /api/assets/{id}/select-candidate` body `{"index": 1}` → `selected_candidate_index == 1`，`file_path` 指向候选 1
  - [ ] 候选选择后状态为 `SELECTED`
  - [ ] 选择后 `asset.url` 返回候选 1 的 URL

  **QA Scenarios**:
  ```
  Scenario: 多候选存储 + 状态正确
    Tool: Bash (curl)
    Preconditions: 后端运行，至少一个 pending 资产
    Steps:
      1. ASSET_ID=temple_ruins_priest_corpse_01
      2. curl -s -X POST http://localhost:8000/api/assets/$ASSET_ID/generate
      3. 循环: curl -s http://localhost:8000/api/assets/$ASSET_ID/status 直到 status != "generating"（超时 120s）
      4. curl -s http://localhost:8000/api/assets/$ASSET_ID | python -c "
         import sys,json; d=json.load(sys.stdin)
         assert d['status']=='candidates_ready', f'Expected candidates_ready, got {d[\"status\"]}'
         assert len(d.get('candidates',[]))>=1, 'candidates empty'
         print('candidates:', len(d['candidates']), 'status:', d['status'])
         "
    Expected Result: status=candidates_ready, candidates 非空
    Failure Indicators: status=completed（旧逻辑未改）, candidates 为空或只有 1 个
    Evidence: .sisyphus/evidence/task-3-candidate-storage.json

  Scenario: 候选选择 API 联动
    Tool: Bash (curl)
    Preconditions: 上一个 Scenario 完成（资产已有 candidates）
    Steps:
      1. curl -s -X POST http://localhost:8000/api/assets/$ASSET_ID/select-candidate -H "Content-Type: application/json" -d '{"index": 1}'
      2. curl -s http://localhost:8000/api/assets/$ASSET_ID | python -c "
         import sys,json; d=json.load(sys.stdin)
         assert d.get('selected_candidate_index')==1, f'Expected 1, got {d.get(\"selected_candidate_index\")}'
         assert d['status']=='selected', f'Expected selected, got {d[\"status\"]}'
         print('file_path:', d['file_path'])
         "
    Expected Result: selected_candidate_index=1, status=selected, file_path 同步更新
    Evidence: .sisyphus/evidence/task-3-select-candidate.json

  Scenario: 选择越界索引返回 400
    Tool: Bash (curl)
    Steps:
      1. curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/assets/$ASSET_ID/select-candidate -H "Content-Type: application/json" -d '{"index": 99}'
    Expected Result: 400（不是 500）
    Evidence: .sisyphus/evidence/task-3-out-of-range.txt

  Scenario: 全部候选生成失败 → status=failed
    Tool: Bash (curl)
    Preconditions: 构造一个 prompt 为空的资产或断网
    Steps:
      1. 触发生成
      2. 轮询 status
    Expected Result: status=failed 且 error_message 非空，不卡在 generating
    Evidence: .sisyphus/evidence/task-3-all-failed.txt
  ```

  **Commit**: YES
  - Message: `feat(api): multi-candidate storage, selection, and CANDIDATES_READY status`
  - Files: `backend/app/api/assets_routes.py`, `backend/app/state/asset_store.py`
  - Pre-commit: `cd backend && .venv\Scripts\python -m pytest tests/ -x -q`

---

- [x] 4. StyleProfile 提取 + Prompt 注入 + Feature Flag + base64 降级

  **What to do**:
  - 新建 `backend/app/ai/style_extractor.py`：
    - `extract_style_profile(asset: Asset) -> SceneStyleProfile`：从已完成资产的 prompt 中提取五维度风格
    - 五维度关键词库（预定义，纯文本匹配，确定性）：
      - `palette`: cyan, neon-green, deep-black, bronze, amber, red, blue, white...
      - `lighting`: {type: volumetric/directional/ambient, direction: side/top/bottom}
      - `material`: marble, metal, stone, bronze, concrete, glass...
      - `rendering`: {style: cyberpunk/realistic/concept-art, camera: low-angle/wide-shot}
      - `atmosphere`: {mood: dark/melancholic/mystical, weather: mist/fog/clear}
    - `inject_style_prompt(base_prompt: str, profile: SceneStyleProfile) -> str`：把 profile 转为风格前缀注入 prompt
    - 注入格式：`"Scene style: {palette}, {lighting}, {material}. {base_prompt}"`
    - 限制注入 token 数 ≤ 50 词，避免污染物体描述
  - `ImageGenerator.generate()` 新增参数 `reference_asset_ids: list[str] = []`
  - `_call_qwen()` 参考图策略（三级降级）：
    1. **Level 1 — base64 参考图**：读取参考资产 `file_path` → base64 编码 → `messages[0].content` 加 `{"image": "data:image/png;base64,..."}` 条目
    2. **Level 2 — StyleProfile Prompt 注入**：若 base64 被 API 拒绝（HTTP 4xx）→ 捕获异常 → 回退到 `inject_style_prompt()` 模式
    3. **Level 3 — 无参考**：若 Feature Flag 关闭或无参考资产 → 原始行为不变
  - 每次降级记录 `logger.warning()` 并在 metadata JSON 中标注 `reference_mode: "base64" | "prompt" | "none"`
  - Feature Flag：`SCENE_CONSISTENCY=false` 时强制走 Level 3（原始行为）

  **Must NOT do**:
  - 不调用 LLM 做风格提取（纯关键词匹配）
  - 不上传图片到公网
  - 不修改非 qwen provider 的行为
  - 不改变背景自身的 prompt（只注入物体）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 2, with Task 3, 5)
  - **Blocks**: Task 6
  - **Blocked By**: Task 1

  **References**:
  - `backend/app/ai/image_generator.py:113-140` — `generate()` 签名，需加 `reference_asset_ids` 参数
  - `backend/app/ai/image_generator.py:344-413` — `_call_qwen()` 方法，需添加三级降级逻辑
  - `backend/app/models/asset.py` — Task 1 的 `SceneStyleProfile` 模型
  - `backend/app/config/features.py` — Task 1 的 Feature Flag
  - `data/assets/manifest.json:7-8` — 背景资产 prompt 示例（"cyberpunk... marble... neon..."）

  **Acceptance Criteria**:
  - [ ] `extract_style_profile()` 从 temple_ruins_bg prompt 提取出 palette >= 2 色、material >= 1、lighting.type 非空
  - [ ] `inject_style_prompt("a bronze door", profile)` 返回的字符串包含 palette 颜色词
  - [ ] 同一资产多次提取结果完全一致（确定性）
  - [ ] 无参考图时 `_call_qwen()` 行为与之前完全一致
  - [ ] Feature Flag = false 时不触发任何风格逻辑

  **QA Scenarios**:
  ```
  Scenario: 风格提取确定性 + 五维度
    Tool: Bash (python)
    Steps:
      1. cd backend && .venv\Scripts\python -c "
         from app.ai.style_extractor import extract_style_profile_from_prompt
         from app.models.asset import SceneStyleProfile
         prompt = 'cyberpunk ancient marble temple, cyan neon circuits, volumetric fog, synthwave lighting, dark atmosphere'
         p = extract_style_profile_from_prompt(prompt)
         print('palette:', p.palette)
         print('material:', p.material)
         print('lighting:', p.lighting)
         print('atmosphere:', p.atmosphere)
         assert len(p.palette) >= 2
         assert len(p.material) >= 1
         # 确定性测试
         p2 = extract_style_profile_from_prompt(prompt)
         assert p == p2, 'Non-deterministic!'
         print('OK')
         "
    Expected Result: 五维度非空，两次提取结果一致
    Evidence: .sisyphus/evidence/task-4-style-extraction.txt

  Scenario: Prompt 注入正确
    Tool: Bash (python)
    Steps:
      1. .venv\Scripts\python -c "
         from app.ai.style_extractor import inject_style_prompt, extract_style_profile_from_prompt
         p = extract_style_profile_from_prompt('cyan neon marble cyberpunk dark')
         result = inject_style_prompt('a bronze door', p)
         print('injected:', result[:100])
         assert 'cyan' in result or 'neon' in result
         print('OK')
         "
    Expected Result: 注入后的 prompt 包含风格关键词
    Evidence: .sisyphus/evidence/task-4-prompt-injection.txt

  Scenario: Feature Flag 关闭 = 原始行为
    Tool: Bash (python)
    Steps:
      1. 设置 FEATURE_SCENE_CONSISTENCY=false
      2. .venv\Scripts\python -c "
         import os; os.environ['FEATURE_SCENE_CONSISTENCY']='false'
         from app.config.features import SCENE_CONSISTENCY
         assert not SCENE_CONSISTENCY
         print('Flag off — original behavior preserved')
         "
    Expected Result: Flag 为 False
    Evidence: .sisyphus/evidence/task-4-feature-flag-off.txt

  Scenario: base64 降级到 prompt
    Tool: Bash (python)
    Preconditions: 有一个已完成资产
    Steps:
      1. 调用 generate(reference_asset_ids=["temple_ruins_bg"], num_candidates=1)
      2. 检查 metadata JSON 中的 reference_mode 字段
    Expected Result: reference_mode 为 "base64" 或 "prompt"（取决于 API 是否接受），不是报错
    Failure Indicators: 未捕获异常导致生成失败
    Evidence: .sisyphus/evidence/task-4-base64-fallback.txt
  ```

  **Commit**: YES
  - Message: `feat(ai): style profile extraction and prompt injection with feature flag`
  - Files: `backend/app/ai/style_extractor.py`, `backend/app/ai/image_generator.py`

---

- [x] 5. 场景编排 API — 拓扑排序串行触发 + 风格链 + 进度追踪

  **What to do**:
  - 新增 `POST /api/scenes/{scene_id}/orchestrate`：
    1. `SceneGraph.from_yaml(scene_id).generation_order` 获取拓扑顺序
    2. 串行触发：背景先生成 → 等待完成 → 提取 StyleProfile → 填充同场景 pending 资产的 `style_profile`
    3. 后续物体生成时自动注入参考：`reference_asset_ids = [scene_id + "_bg"]`
    4. 返回 `{order: [...], triggered: N}`
  - 新增 `GET /api/scenes/{scene_id}/graph`：返回 `{nodes: {...}, generation_order: [...], style_sources: {...}}`
  - 编排进度追踪：新增 `GET /api/scenes/{scene_id}/orchestrate/status`：返回每个资产的当前状态
  - 背景完成后自动调用 `extract_style_profile()` 并更新同场景 pending 资产的 `style_profile` 字段
  - 编排过程中任一资产失败 → 记录错误但继续后续资产（不阻塞整条链）

  **Must NOT do**:
  - 不并行生成同场景资产（参考链需要串行：背景→物体）
  - 不自动 approve — 生成完仍需用户选择候选 + 审批
  - 不阻塞其他场景的生成请求

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 2, with Task 3, 4)
  - **Blocks**: Task 6
  - **Blocked By**: Task 2

  **References**:
  - `backend/app/models/scene_graph.py` — Task 2 的 SceneGraph 模型
  - `backend/app/api/assets_routes.py:185-198` — `generate_all()` 现有批量逻辑参考
  - `backend/app/ai/style_extractor.py` — Task 4 的风格提取器
  - `backend/app/config/features.py` — Feature Flag 检查

  **Acceptance Criteria**:
  - [ ] `POST /api/scenes/temple_ruins/orchestrate` 返回 order 列表，`temple_ruins_bg` 在第一位
  - [ ] `GET /api/scenes/temple_ruins/graph` 返回 `{nodes, generation_order, style_sources}` 结构
  - [ ] 背景生成完成后，同场景 pending 资产的 `style_profile` 被填充（非 None）
  - [ ] 编排中某资产失败不阻塞后续

  **QA Scenarios**:
  ```
  Scenario: 场景图数据返回
    Tool: Bash (curl)
    Steps:
      1. curl -s http://localhost:8000/api/scenes/temple_ruins/graph | python -c "
         import sys,json; d=json.load(sys.stdin)
         assert 'nodes' in d and 'generation_order' in d and 'style_sources' in d
         assert 'temple_ruins_bg' in d['nodes']
         assert d['generation_order'][0] == 'temple_ruins_bg'
         print('nodes:', len(d['nodes']), 'order:', d['generation_order'][:3])
         "
    Expected Result: 结构化图数据，背景在首位
    Evidence: .sisyphus/evidence/task-5-scene-graph.json

  Scenario: 编排触发 + 顺序正确
    Tool: Bash (curl)
    Preconditions: temple_ruins 有 pending 资产
    Steps:
      1. curl -s -X POST http://localhost:8000/api/scenes/temple_ruins/orchestrate | python -c "
         import sys,json; d=json.load(sys.stdin)
         print('order:', d.get('order', []))
         assert d['order'][0] == 'temple_ruins_bg'
         print('triggered:', d.get('triggered', 0))
         "
    Expected Result: 返回拓扑顺序，背景首位
    Evidence: .sisyphus/evidence/task-5-orchestrate.json

  Scenario: 编排进度追踪
    Tool: Bash (curl)
    Preconditions: 编排已触发
    Steps:
      1. curl -s http://localhost:8000/api/scenes/temple_ruins/orchestrate/status | python -c "
         import sys,json; d=json.load(sys.stdin)
         print('assets:', {k:v for k,v in list(d.items())[:3]})
         "
    Expected Result: 每个资产有状态字段
    Evidence: .sisyphus/evidence/task-5-orchestrate-status.json

  Scenario: 风格 Profile 自动填充
    Tool: Bash (python)
    Preconditions: 编排中背景已完成
    Steps:
      1. .venv\Scripts\python -c "
         from app.state.asset_store import AssetStore
         s = AssetStore()
         for a in s.list_assets():
             if a.parent_scene == 'temple_ruins' and a.type == 'object':
                 print(a.id, 'style_profile:', a.style_profile is not None)
         "
    Expected Result: 背景完成后的物体 style_profile 非 None
    Evidence: .sisyphus/evidence/task-5-style-propagation.txt
  ```

  **Commit**: YES
  - Message: `feat(api): scene orchestration with topological generation order`
  - Files: `backend/app/api/assets_routes.py` (or new `backend/app/api/scene_routes.py`)

---

- [x] 6. 前端全部实现 + 集成验证

  **What to do**:

  **6a. 前端 API Client 扩展**:
  - `frontend/src/api/assets.ts`：
    - 新增 `Candidate` interface（index, seed, file_path, url, score）
    - `Asset` interface 增加 `candidates`、`selected_candidate_index`、`reference_asset_ids`、`style_profile`
    - `AssetStatus` 类型增加 `'candidates_ready' | 'selected'`
    - 新增 `selectCandidate(id: string, index: number): Promise<Asset>` 函数
  - 新建 `frontend/src/api/scenes.ts`：
    - `SceneGraphNode` interface（id, name, type, status, is_future_anchor）
    - `getSceneGraph(sceneId): Promise<{nodes, generation_order, style_sources}>` 函数
    - `orchestrateScene(sceneId): Promise<{order, triggered}>` 函数
    - `getOrchestrateStatus(sceneId): Promise<Record<string, string>>` 函数

  **6b. CandidateGrid 组件**:
  - 新建 `frontend/src/components/CandidateGrid.tsx`
  - Props: `candidates: Candidate[]`、`selectedIndex: number | null`、`onSelect: (index: number) => void`
  - 2x2 网格布局，每个候选显示缩略图 + seed
  - 选中候选加 neon-cyan 边框高亮
  - 未选中的候选 hover 时显示 neon-green 边框
  - `data-testid="candidate-thumb"` 属性供测试定位

  **6c. SceneGraphPage 独立页面**:
  - 新建 `frontend/src/pages/SceneGraphPage.tsx`，路由 `/scenes/:sceneId`
  - 新建 `frontend/src/components/SceneGraphSVG.tsx`：纯 SVG 放射状布局
    - 背景节点在中心，物体节点环绕
    - 节点用 STATUS_COLORS 标记状态色
    - 边用 SVG `<line>` 连接，标注 "style_ref"
    - 点击节点跳转到 `/assets` 并选中该资产
  - "编排生成"按钮 → 调用 `orchestrateScene()` → 轮询 `getOrchestrateStatus()` → 实时更新节点状态色
  - 编排进度条：`已生成 N / 总数 M`

  **6d. AssetReview 集成**:
  - 在 `AssetReview.tsx` 预览区域：当 `asset.status === 'candidates_ready'` 时嵌入 `<CandidateGrid />`
  - 状态联动：
    - `candidates_ready`：显示候选网格，approve/reject 禁用
    - `selected`：主预览显示选中图片，approve/reject 解禁
  - 顶部 header 新增"场景图谱"链接 → 跳转 `/scenes/:sceneId`

  **6e. 集成验证**:
  - 端到端跑 temple_ruins 场景：编排 → 背景生成 → 风格提取 → 物体带风格生成 → 候选展示 → 选择 → approve
  - 修复联调中发现的问题
  - Feature Flag 开/关对比测试

  **Must NOT do**:
  - 不引入 D3.js / cytoscape 等图可视化库
  - 不改变现有资产列表、属性面板布局结构
  - 不在此 Task 新增功能 — 纯集成 + 修复

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`frontend-ui-ux`]

  **Parallelization**:
  - **Can Run In Parallel**: NO (Wave 3 最后一个，依赖全部)
  - **Blocks**: FINAL
  - **Blocked By**: Tasks 3, 4, 5

  **References**:
  - `frontend/src/api/assets.ts:1-152` — 现有 API client，需扩展
  - `frontend/src/api/client.ts` — `fetchWithTimeout` 工具
  - `frontend/src/pages/AssetReview.tsx:1-677` — 现有资产审核页面，需集成 CandidateGrid
  - `frontend/src/pages/AssetReview.tsx:457-503` — 预览区域，候选网格插入点
  - `frontend/src/pages/AssetReview.tsx:605-662` — approve/reject 按钮区域，需联动选中状态
  - `frontend/src/pages/AssetReview.tsx:19-44` — STATUS_COLORS / STATUS_TEXT_COLORS 映射，需加新状态
  - `frontend/src/App.tsx` — 需新增 `/scenes/:sceneId` 路由

  **Acceptance Criteria**:
  - [ ] `npm run build` 无 TypeScript 错误
  - [ ] `candidates_ready` 状态的资产显示 2x2 候选网格
  - [ ] 点击候选后高亮 + approve 按钮解禁
  - [ ] `/scenes/temple_ruins` 路由可访问，显示 SVG 场景图
  - [ ] 场景图节点点击跳转到资产
  - [ ] "编排生成"按钮触发 API 并显示进度
  - [ ] Feature Flag = false 时候选网格仍可用（只是无风格注入）

  **QA Scenarios**:
  ```
  Scenario: TypeScript 编译通过
    Tool: Bash
    Steps:
      1. cd frontend && npm run build
    Expected Result: build 成功无错误
    Evidence: .sisyphus/evidence/task-6-build.txt

  Scenario: 候选网格展示
    Tool: Playwright
    Preconditions: 后端运行，有一个 status=candidates_ready 的资产
    Steps:
      1. 导航到 http://localhost:5173/assets
      2. 点击该资产
      3. 断言 [data-testid="candidate-thumb"] 元素数量 > 1
      4. 截图
    Expected Result: 2x2 网格显示候选缩略图
    Evidence: .sisyphus/evidence/task-6-candidate-grid.png

  Scenario: 候选选择交互
    Tool: Playwright
    Steps:
      1. 在候选网格中点击第二个 [data-testid="candidate-thumb"]
      2. 断言该元素有 class 包含 "border-neon-cyan"
      3. 断言 approve 按钮不再有 "cursor-not-allowed" class
      4. 截图
    Expected Result: 选中高亮 + approve 解禁
    Evidence: .sisyphus/evidence/task-6-select-interaction.png

  Scenario: 场景图页面可达
    Tool: Playwright
    Steps:
      1. 导航到 http://localhost:5173/scenes/temple_ruins
      2. 断言 [data-testid="scene-graph-svg"] 存在
      3. 断言 SVG 内有 > 2 个节点元素
      4. 截图
    Expected Result: 放射状场景图渲染
    Evidence: .sisyphus/evidence/task-6-scene-graph-page.png

  Scenario: 编排生成端到端
    Tool: Playwright + Bash
    Preconditions: temple_ruins 有 pending 资产
    Steps:
      1. 导航到 /scenes/temple_ruins
      2. 点击"编排生成"按钮
      3. 等待确认框 → 确认
      4. 断言进度条出现
      5. 轮询等待直到所有节点状态 != generating（最多 5 分钟）
      6. 导航到 /assets
      7. 检查每个资产 candidates 非空
      8. 截图
    Expected Result: 全场景资产生成完成
    Failure Indicators: 超时、candidates 为空、节点状态不更新
    Evidence: .sisyphus/evidence/task-6-e2e-orchestrate.png

  Scenario: Feature Flag 关闭对比
    Tool: Bash
    Steps:
      1. 设置 FEATURE_SCENE_CONSISTENCY=false 重启后端
      2. curl -X POST /api/scenes/temple_ruins/orchestrate
      3. 检查物体生成时 style_profile 是否为 None
    Expected Result: Flag 关闭时 style_profile 不被填充
    Evidence: .sisyphus/evidence/task-6-feature-flag-off.txt

  Scenario: 回滚安全 — 删除 candidates 后已 approve 资产正常
    Tool: Bash
    Steps:
      1. 找到一个已 approved 资产
      2. 记录其 file_path
      3. curl http://localhost:8000/api/assets/{id} 确认 url 字段非 null
    Expected Result: 已 approve 资产走 file_path 回退，url 正常
    Evidence: .sisyphus/evidence/task-6-rollback-safety.txt
  ```

  **Commit**: YES
  - Message: `feat(ui): CandidateGrid component and SceneGraphPage + integration`
  - Files: `frontend/src/api/assets.ts`, `frontend/src/api/scenes.ts`, `frontend/src/components/CandidateGrid.tsx`, `frontend/src/components/SceneGraphSVG.tsx`, `frontend/src/pages/SceneGraphPage.tsx`, `frontend/src/pages/AssetReview.tsx`, `frontend/src/App.tsx`

---

## Final Verification Wave
- [x] F1. **Plan Compliance Audit** — `oracle`

- [x] F2. **Code Quality Review** — `unspecified-high`
- [x] F3. **Real Manual QA** — `unspecified-high` (+ playwright)
- [x] F4. **Scope Fidelity Check** — `deep`

---

## Commit Strategy

```
feat(models): Asset candidates + SceneStyleProfile + SceneGraph + AssetStatus
feat(api): multi-candidate storage, selection, and scene orchestration
feat(ai): style profile extraction and prompt injection with feature flag
feat(ui): CandidateGrid component and SceneGraphPage
feat(integration): end-to-end orchestration with feature flags
```

---

## Success Criteria

- [ ] 同场景资产视觉风格一致（StyleProfile 五维度注入）
- [ ] 多候选生成 + 用户可选最佳
- [ ] Feature Flag 关闭时行为不变
- [ ] 候选网格 UI + 场景图页面独立路由
- [ ] 所有现有测试不回归
