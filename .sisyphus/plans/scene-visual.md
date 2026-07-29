# 图形化场景系统 — AI 生图审核驱动架构

## TL;DR

> **Quick Summary**: 为赛博朋克终端 Demo 增加全屏图形化场景 + AI 生图审核系统。场景背景全屏，对象贴片叠加，终端浮层在前。AI 生图是核心交付路径（非补充），配套独立审核页面 `/admin/assets`，支持生成/预览/审核/重试。新增视觉设计规范层保证风格一致性。
> 
> **Deliverables**:
> - **视觉规范层**: `data/visual/`（Style Bible + 色彩/镜头/prompt 模板）
> - **素材状态库**: `data/assets/manifest.json`（完整状态机 pending→generating→completed→approved/rejected）
> - **生图运行时模块**: `backend/app/ai/image_generator.py`（异步封装智谱/通义）
> - **素材管理 API**: `/api/assets` 路由组（CRUD + 生成触发 + 审核操作）
> - **场景 API**: `GET /api/scene`（只返回 approved 素材）
> - **生图审核页面**: `/admin/assets`（素材清单 + 预览 + prompt 编辑 + 审核）
> - **场景渲染**: `SceneView`（全屏背景）+ `SceneObject`（贴片 + hover 分层 + 点击交互）
> - **布局改造**: 场景全屏 z-0 + 对象 z-10 + 终端浮层 z-20 + 神王 z-50
> - **补全字段**: available_actions / echo_vision / tension_level 展示
> 
> **Estimated Effort**: Large（4-5 个工作日）
> **Parallel Execution**: YES - 5 waves
> **Critical Path**: T0a→T4→T9 | T0c→T2→T3→T9

---

## Context

### Original Request
当前前端只有终端文本界面 + 状态面板，缺少场景视觉。用户要求"图像场景、可互动的贴片场景"。三份审查报告后升级为：AI 生图是核心交付路径，需配套审核页面 + 视觉质量控制体系。

### Interview Summary
**Key Decisions**:
1. **视觉形态**: 2D 静态贴片场景（背景图 + 对象图标叠加），全屏背景 + 终端半透明浮层
2. **可交互分层**: 主要对象 hover 发光 + 点击填输入栏；次要对象无高亮 + 简短文字
3. **AI 生图 = 核心路径**（非补充）：运行时异步服务 + 审核页面 + manifest 状态库
4. **素材策略**: AI 生图为主 + 降级占位符（CSS 方块），开源仅作参考
5. **视觉一致性**: Style Bible + 五段式 prompt + seed 管理 + 候选池评分
6. **素材审核**: 只有 `approved` 素材才被 `/api/scene` 返回给前端场景
7. **同时补全**: available_actions / echo_vision / NarrativeContext

**Research Findings**:
- 后端 `WorldLoader.load_scene()` 已实现（`backend/app/engine/world_loader.py:22`）
- `data/scenes/temple_ruins.yaml` 有 4 个对象（门/尸体/祭坛/柱子）
- `gods_table.yaml` 有 5 位神王，`intervention_table.yaml` 有 5 条规则
- routes.py 无 `/api/scene`，前端无场景组件
- ActionResponse 的 echo_vision/available_actions 前端完全没消费

### Review Reports Incorporated
**报告1 — 视觉质量控制体系**:
- ✅ 新增 `data/visual/` 规范目录（style_bible.md + palette.yaml + prompts.yaml）
- ✅ 五段式 prompt 结构（世界→空间→镜头→材质→negative）
- ✅ 对象统一摄影棚规则（isolated/centered/transparent bg）
- ✅ 原始 512x512 生成 → 背景去除 → 压缩 128/256
- ✅ Seed 管理 + prompt 元数据保存（`data/assets/meta/`）
- ✅ 候选池生成（4 候选 → 评分 → 选最佳）
- ✅ CLIP 风格一致性评分（阈值 >0.75，可选增强）

**报告2 — Prompt 质量规范**:
- ✅ 背景图视角控制（微俯视 + 构图留白 + negative prompt）
- ✅ 对象生成在单色背景上（自动抠图）
- ✅ `rembg` 自动背景去除流程
- ✅ 风格词绑定（synthwave lighting / cyberpunk concept art 统一前缀）
- ✅ 尺寸规范（背景 1920x1080，对象 512x512 原图）
- ✅ CSS mix-blend-mode: screen 用于全息祭坛（天然去黑背景）

**报告3 — AI 生图审核驱动**:
- ✅ 素材状态机（pending→generating→completed→approved/rejected）
- ✅ manifest.json 状态库
- ✅ 生图审核页面 `/admin/assets`（清单+预览+prompt编辑+审核操作）
- ✅ `/api/assets` 路由组（9 个端点）
- ✅ 运行时异步生图（asyncio + 状态轮询）
- ✅ 审核状态影响场景（只有 approved 才返回）
- ✅ 降级占位符系统（无图也能跑）

---

## Work Objectives

### Core Objective
建立"AI 生图 → 审核筛选 → 场景渲染"的完整可控流水线。用户通过审核页面生成、预览、审核素材，审核通过的素材自动出现在游戏场景中。

### Concrete Deliverables
- `data/visual/style_bible.md` + `palette.yaml` + `prompts.yaml`
- `data/assets/manifest.json` + `data/assets/meta/` (seed/prompt 元数据)
- `backend/app/ai/image_generator.py`（异步生图 + 背景去除 + seed 管理）
- `backend/app/api/assets_routes.py`（`/api/assets` CRUD + 审核）
- `backend/app/models/asset.py`（AssetDTO + 状态枚举）
- `GET /api/scene`（只返回 approved 素材）
- `frontend/src/pages/AssetReview.tsx`（审核页面）
- `frontend/src/components/SceneView.tsx` + `SceneObject.tsx`
- 改造后的 `App.tsx`（路由 + 布局分层）
- 补全的 available_actions / echo_vision / tension_level 展示

### Definition of Done
- [x] `GET /admin/assets` 审核页面可访问
- [x] 审核页面可触发单张/批量生成
- [x] 生成中状态可见，完成后自动刷新预览
- [x] Prompt 可编辑后重新生成
- [x] 审核通过 → 场景自动使用该素材
- [x] 审核拒绝 → 场景使用降级占位符
- [x] 场景背景全屏 + 对象贴片可交互
- [x] 终端浮层不遮挡场景对象
- [x] 无 API key 或生图失败时降级占位符不白屏

### Must Have
- 生图审核页面 `/admin/assets` 完整功能
- 素材 manifest 状态库 + 状态机
- 异步生图 + 状态轮询
- 场景只返回 approved 素材
- 视觉规范层（Style Bible + prompt 模板）
- Prompt 元数据 + seed 保存
- 场景背景全屏渲染
- 主要对象 hover 发光 + 点击填输入栏
- 终端半透明浮层
- 降级占位符（素材缺失时不白屏）

### Must NOT Have (Guardrails)
- ❌ 不在游戏运行时自动触发 AI 生图（只通过审核页面手动/批量触发）
- ❌ 不存储审核历史版本（只保留当前版本 + 最新生成记录）
- ❌ 不做多用户审核冲突（单用户 Demo，无并发锁）
- ❌ 不引入 Redis/Celery（用文件系统 manifest + asyncio 足够）
- ❌ 审核页面不做权限控制（Demo 环境，无登录）
- ❌ 不做 3D 场景 / WebGL / 游戏引擎（Phaser/PixiJS）
- ❌ 不做动画帧序列（静态贴片足够）
- ❌ 不做多场景切换（Demo 只有 temple_ruins）
- ❌ 不做对象被交互后的视觉状态变化（V1 静态）
- ❌ 不做移动端适配
- ❌ 素材文件不提交到 git（data/assets/ 加 .gitignore）
- ❌ 生图 API 不硬编码密钥（从 .env 读取）
- ❌ CLIP 评分是可选增强，不是 V1 阻塞项（标注 `[ENHANCEMENT]`）

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed.

### Test Decision
- **Infrastructure exists**: YES（后端 pytest，前端 vitest）
- **Automated tests**: Tests-after（场景逻辑以 QA 场景为主）
- **Backend**: pytest 测试 `/api/assets` + `/api/scene` 端点
- **Frontend**: vitest 测试 AssetReview + SceneView 渲染逻辑
- **Primary QA**: Playwright E2E（审核页面 + 场景可视化）

### QA Policy
- **Backend API**: Bash (curl) — 发请求，断言 JSON 字段 + 状态流转
- **Frontend UI**: Playwright — 导航，截图，DOM 断言，点击交互
- **素材生成**: Bash — 检查文件存在 + manifest 状态正确

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 0 (Infrastructure - 5 parallel, zero-blocking):
├── T0a: 生图运行时模块（异步封装智谱/通义+背景去除+seed管理）[deep]
├── T0b: 素材状态存储系统（manifest.json + 状态机 + 初始化）[quick]
├── T0c: 降级占位符系统（CSS 方块组件 + SceneView 降级逻辑）[quick]
├── T0d: 审核页面骨架（前端路由 + 布局 + mock 数据）[visual-engineering]
└── T0e: 后端 /api/assets 管理端点（CRUD + 生成触发 + 审核操作）[deep]

Wave 1 (Core - 4 parallel):
├── T1: 视觉规范层（Style Bible + palette + prompt 模板五段式）(depends: -) [writing]
├── T2: 后端 /api/scene 端点（只返回 approved 素材）(depends: T0b) [quick]
├── T3: 前端 SceneView + SceneObject 组件 (depends: T0c) [visual-engineering]
└── T4: 审核页面完整功能（连接 T0a/T0e，生成/审核/轮询）(depends: T0a,T0d,T0e) [visual-engineering]

Wave 2 (Interaction - 3 parallel):
├── T5: 布局改造（场景全屏 z-0 + 终端浮层 z-20）(depends: T3) [visual-engineering]
├── T6: 对象交互（点击→输入栏 + hover 分层）(depends: T3) [visual-engineering]
└── T7: 补全 available_actions/echo_vision/tension (depends: -) [quick]

Wave 3 (Integration - 2 parallel):
├── T8: 端到端生图流程（审核页生成→manifest更新→场景自动刷新）(depends: T2,T4,T5) [deep]
└── T9: prompt 模板集成 + 素材坐标精调 (depends: T1,T3,T8) [visual-engineering]

Wave FINAL (4 parallel reviews):
├── F1: Plan Compliance Audit (oracle)
├── F2: Code Quality Review (unspecified-high)
├── F3: Real Manual QA - 审核页+场景 (unspecified-high + playwright)
└── F4: Scope Fidelity Check (deep)

Critical Path: T0a→T4→T8→T9 | T0b→T2→T8 | T0c→T3→T5→T8
Parallel Speedup: ~65% faster than sequential
Max Concurrent: 5 (Wave 0)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave | Agent |
|------|-----------|--------|------|-------|
| T0a | - | T4 | 0 | deep |
| T0b | - | T2,T4 | 0 | quick |
| T0c | - | T3 | 0 | quick |
| T0d | - | T4 | 0 | visual-engineering |
| T0e | - | T4 | 0 | deep |
| T1 | - | T9 | 1 | writing |
| T2 | T0b | T8 | 1 | quick |
| T3 | T0c | T5,T6 | 1 | visual-engineering |
| T4 | T0a,T0d,T0e | T8 | 1 | visual-engineering |
| T5 | T3 | T8 | 2 | visual-engineering |
| T6 | T3 | T8 | 2 | visual-engineering |
| T7 | - | - | 2 | quick |
| T8 | T2,T4,T5 | T9 | 3 | deep |
| T9 | T1,T3,T8 | F1-F4 | 3 | visual-engineering |

### Agent Dispatch Summary
- **Wave 0**: T0a→deep, T0b→quick, T0c→quick, T0d→visual-engineering, T0e→deep
- **Wave 1**: T1→writing, T2→quick, T3→visual-engineering, T4→visual-engineering
- **Wave 2**: T5→visual-engineering, T6→visual-engineering, T7→quick
- **Wave 3**: T8→deep, T9→visual-engineering
- **FINAL**: F1→oracle, F2→unspecified-high, F3→unspecified-high(+playwright), F4→deep

---

## TODOs

### Wave 0: Infrastructure (5 parallel, zero-blocking)

- [x] 0a. 生图运行时模块（异步封装 + 背景去除 + seed 管理）

  **What to do**:
  - 创建 `backend/app/ai/image_generator.py`:
    - `class ImageGenerator`: 异步封装国产生图 API
    - `async def generate(prompt, negative_prompt, size, seed, num_candidates) -> list[GeneratedImage]`
    - 支持 provider 切换：智谱 CogView-3 / 阿里通义万相（从 `.env` 读取）
    - 每次生成保存 seed 到 `data/assets/meta/{asset_id}.json`
    - 候选池：生成 4 张候选，返回全部供审核页面选择
    - 错误处理：API 超时/限流/key 无效 → 返回明确错误，不 crash
  - 创建 `backend/app/ai/bg_remover.py`:
    - 使用 `rembg` 库自动去除单色背景 → 输出透明 PNG
    - `def remove_background(input_path, output_path) -> bool`
    - 对全息祭坛等特殊对象可选跳过去除（用 mix-blend-mode: screen）
  - 在 `.env.example` 新增:
    ```
    IMAGE_PROVIDER=zhipu
    ZHIPU_API_KEY=
    WANXIANG_API_KEY=
    ```

  **Must NOT do**:
  - 不在应用启动时自动调 API
  - 不硬编码 key
  - 候选生成失败一张不影响其他张返回

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**: Wave 0 | Blocks: T4 | Blocked By: None

  **References**:
  - 现有 Provider 模式: `backend/app/ai/provider.py`（LLM Provider 工厂模式可参考）
  - 智谱 CogView-3: https://open.bigmodel.cn/dev/api/cogview-3
  - 通义万相: https://help.aliyun.com/zh/dashscope/developer-reference/api-details-9
  - rembg: https://github.com/danielgatis/rembg
  - 现有 `.env.example`: `backend/.env.example`

  **Acceptance Criteria**:
  - [ ] `ImageGenerator.generate()` 可异步调用返回图片列表
  - [ ] 生成后 seed + prompt 保存到 `data/assets/meta/`
  - [ ] `bg_remover` 可去除单色背景输出透明 PNG
  - [ ] API key 从 `.env` 读取
  - [ ] 错误时返回明确错误信息（不 crash）
  - [ ] pytest mock 测试通过

  **QA Scenarios**:
  ```
  Scenario: 生图模块 mock 调用
    Tool: Bash
    Steps:
      1. pytest tests/unit/test_image_generator.py -v（mock HTTP）
      2. 验证返回 GeneratedImage 列表
      3. 验证 meta JSON 保存
    Expected Result: mock 生成成功，元数据保存
    Evidence: .sisyphus/evidence/task-0a-generator-test.txt

  Scenario: 背景去除
    Tool: Bash
    Steps:
      1. pytest tests/unit/test_bg_remover.py -v
      2. 验证输出 PNG 有 alpha channel
    Expected Result: 透明 PNG 输出
    Evidence: .sisyphus/evidence/task-0a-bgremover-test.txt
  ```

  **Commit**: YES - `feat(ai): image generator + background remover + seed management`

---

- [x] 0b. 素材状态存储系统（manifest.json + 状态机 + 初始化）

  **What to do**:
  - 创建 `backend/app/models/asset.py`:
    ```python
    class AssetStatus(str, Enum):
        PENDING = "pending"
        GENERATING = "generating"
        COMPLETED = "completed"
        APPROVED = "approved"
        REJECTED = "rejected"
        FAILED = "failed"

    class AssetType(str, Enum):
        BACKGROUND = "background"
        OBJECT = "object"

    class Asset(BaseModel):
        id: str
        type: AssetType
        name: str
        prompt: str
        negative_prompt: str
        status: AssetStatus
        generation_status: str  # pending/generating/completed/failed
        file_path: Optional[str]
        parent_scene: str
        seed: Optional[int]
        created_at: datetime
        approved_at: Optional[datetime]
        reviewer_note: Optional[str]
        error_message: Optional[str]
    ```
  - 创建 `backend/app/state/asset_store.py`:
    - `class AssetStore`: 管理 `data/assets/manifest.json`
    - `def list_assets() -> list[Asset]`
    - `def get_asset(id) -> Asset`
    - `def update_asset(id, **fields) -> Asset`
    - `def init_manifest()`: 从 `data/scenes/*.yaml` 扫描，为每个背景+对象创建 pending 条目
  - 创建 `data/assets/manifest.json`: 初始空或 init 后填充
  - 状态流转函数:
    - `pending → generating`（触发生成时）
    - `generating → completed`（生成成功）/ `generating → failed`（生成失败）
    - `completed → approved` / `completed → rejected`（人工审核）
    - `rejected → pending`（改 prompt 重试）
    - `failed → pending`（重试）

  **Must NOT do**:
  - 不用 SQLite（JSON 文件足够，素材量小）
  - 不做并发锁（单用户 Demo）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**: Wave 0 | Blocks: T2,T4 | Blocked By: None

  **References**:
  - 现有 YAML 数据: `data/scenes/temple_ruins.yaml`（扫描 accessible_objects 初始化）
  - 现有 Pydantic 模式: `backend/app/models/player.py`

  **Acceptance Criteria**:
  - [ ] `Asset` 模型定义完整（所有字段 + 枚举）
  - [ ] `AssetStore` CRUD 方法工作正常
  - [ ] `init_manifest()` 从 YAML 正确初始化所有素材条目
  - [ ] 状态流转逻辑正确
  - [ ] pytest 测试通过

  **QA Scenarios**:
  ```
  Scenario: manifest 初始化
    Tool: Bash
    Steps:
      1. python -c "from app.state.asset_store import AssetStore; s=AssetStore(); s.init_manifest()"
      2. 检查 data/assets/manifest.json 存在
      3. jq '.assets | length' >= 5（1 背景 + 4 对象）
      4. jq '.assets[0].status' == "pending"
    Expected Result: manifest 正确初始化
    Evidence: .sisyphus/evidence/task-0b-manifest-init.json

  Scenario: 状态流转
    Tool: Bash
    Steps:
      1. pytest tests/unit/test_asset_store.py -v
      2. 验证 pending→generating→completed→approved 流转
    Expected Result: 所有状态转换正确
    Evidence: .sisyphus/evidence/task-0b-state-flow.txt
  ```

  **Commit**: YES - `feat(state): asset manifest + status machine + AssetStore`

---

- [x] 0c. 降级占位符系统

  **What to do**:
  - 创建 `frontend/src/components/AssetPlaceholder.tsx`:
    - 背景 placeholder: CSS 渐变 `from-gray-900 to-black` + CRT 扫描线 + 文字 "SCENE ASSET PENDING..."
    - 对象 placeholder: 彩色方块（neon-green 边框）+ 对象名称文字 + type 标签
    - 可选：SVG 线框图占位符（门=矩形、祭坛=圆形等抽象形状）
  - 在 `frontend/src/components/SceneView.tsx`（T3 创建）中:
    - 当素材 `status != approved` 或图片加载失败时 → 渲染 placeholder
    - `<img onError>` 回退到 placeholder
  - 在 `frontend/src/components/SceneObject.tsx` 中:
    - 无 asset 或未 approved → 渲染方块 placeholder

  **Must NOT do**:
  - 不让 placeholder 破坏布局（尺寸/位置一致）

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**: Wave 0 | Blocks: T3 | Blocked By: None

  **References**:
  - CRT 效果: `frontend/src/index.css` — scanline 动画
  - Tailwind 颜色: `frontend/tailwind.config.js`

  **Acceptance Criteria**:
  - [ ] `AssetPlaceholder` 组件渲染两种模式（背景/对象）
  - [ ] 背景 placeholder 有赛博朋克风格
  - [ ] 对象 placeholder 显示对象名称
  - [ ] `tsc --noEmit` 零错误

  **QA Scenarios**:
  ```
  Scenario: 占位符渲染
    Tool: Playwright
    Steps:
      1. mock /api/scene 返回 status=pending 素材
      2. 导航到 localhost:5173
      3. 检查背景是 CSS 渐变非白屏
      4. 检查对象显示方块 + 名称文字
    Expected Result: 占位符可见，不白屏
    Evidence: .sisyphus/evidence/task-0c-placeholder.png
  ```

  **Commit**: YES - `feat(frontend): asset placeholder fallback system`

---

- [x] 0d. 生图审核页面骨架

  **What to do**:
  - 在 `frontend/src/pages/AssetReview.tsx` 创建审核页面:
    - 三栏布局（CSS Grid 或 flex）:
      - 左栏：素材清单列表（缩略图/占位符 + 状态标签 + 类型图标）
      - 中栏：大图预览区（1280x720 或自适应）
      - 右栏：属性面板（状态/prompt 编辑/操作按钮）
    - 顶部栏：标题 + 批量操作按钮（"一键生成所有 pending"）
    - 筛选器：按状态/类型筛选
  - 在 `frontend/src/App.tsx` 新增路由:
    - `/` → 游戏场景（现有）
    - `/admin/assets` → 审核页面
    - 用条件渲染或 hash router（不引入 react-router，保持零新依赖）
    - 简单方案：`window.location.pathname` 判断 + `<a>` 链接切换
  - 此任务仅搭骨架 + mock 数据，T4 连接真实 API
  - 页面赛博朋克风格：黑底 + neon 边框 + font-mono

  **Must NOT do**:
  - 不安装 react-router（用简单条件渲染）
  - 不连接真实 API（T4 做）
  - 不实现生成/审核逻辑（T4 做）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**: Wave 0 | Blocks: T4 | Blocked By: None

  **References**:
  - 现有 App.tsx: `frontend/src/App.tsx`
  - 现有组件风格: `frontend/src/components/GodWatchIndicator.tsx`（全屏 overlay 模式）
  - Tailwind Grid: https://tailwindcss.com/docs/grid

  **Acceptance Criteria**:
  - [ ] `/admin/assets` 路由可访问（或 hash `#admin`）
  - [ ] 三栏布局渲染正确
  - [ ] mock 素材列表显示
  - [ ] 预览区显示 mock 图片或占位符
  - [ ] 属性面板有 prompt 编辑框 + 按钮占位
  - [ ] 有返回游戏场景的链接
  - [ ] `tsc --noEmit` 零错误

  **QA Scenarios**:
  ```
  Scenario: 审核页面路由
    Tool: Playwright
    Steps:
      1. 导航到 http://localhost:5173/admin/assets
      2. 检查页面包含 "素材" 或 "ASSET" 文字
      3. 检查三栏布局存在
      4. 检查有返回游戏链接
    Expected Result: 审核页面骨架可见
    Evidence: .sisyphus/evidence/task-0d-review-scaffold.png
  ```

  **Commit**: YES - `feat(frontend): asset review page scaffold + routing`

---

- [x] 0e. 后端 /api/assets 管理端点

  **What to do**:
  - 创建 `backend/app/api/assets_routes.py`:
    ```python
    router = APIRouter(prefix="/api/assets")

    @router.get("")          # 列出所有素材
    @router.get("/{id}")     # 单个素材详情
    @router.post("/{id}/generate")   # 触发生成（异步）
    @router.get("/{id}/status")      # 查询生成状态
    @router.post("/{id}/approve")    # 审核通过
    @router.post("/{id}/reject")     # 审核拒绝
    @router.put("/{id}/prompt")      # 更新 prompt
    @router.post("/generate-all")    # 批量生成 pending
    @router.post("/bulk-approve")    # 批量通过
    ```
  - `generate` 端点使用 `asyncio.create_task` 异步触发，立即返回 task_id
  - 生成完成后更新 manifest（调用 AssetStore）
  - 在 `backend/app/main.py` 注册路由 + CORS 允许 `/admin` 前端访问
  - 单元测试 `tests/unit/test_assets_api.py`

  **Must NOT do**:
  - 不引入 Celery/Redis
  - generate 不阻塞（异步触发）
  - 端点函数 ≤ 20 行

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**: Wave 0 | Blocks: T4 | Blocked By: None

  **References**:
  - 现有路由模式: `backend/app/api/routes.py`
  - 现有依赖注入: `backend/app/api/deps.py`
  - FastAPI async: https://fastapi.tiangolo.com/async/
  - T0b AssetStore: `backend/app/state/asset_store.py`
  - T0a ImageGenerator: `backend/app/ai/image_generator.py`

  **Acceptance Criteria**:
  - [ ] 9 个端点全部实现
  - [ ] `GET /api/assets` 返回素材列表
  - [ ] `POST /api/assets/{id}/generate` 异步触发不阻塞
  - [ ] `GET /api/assets/{id}/status` 返回生成状态
  - [ ] `POST /api/assets/{id}/approve` 更新状态为 approved
  - [ ] `PUT /api/assets/{id}/prompt` 更新 prompt
  - [ ] `POST /api/assets/generate-all` 批量触发
  - [ ] pytest 测试通过

  **QA Scenarios**:
  ```
  Scenario: 素材列表 API
    Tool: Bash (curl)
    Steps:
      1. curl http://localhost:8000/api/assets
      2. jq '.assets | length' >= 5
      3. jq '.assets[0].id' 非空
      4. jq '.assets[0].status' == "pending"
    Expected Result: 素材列表完整
    Evidence: .sisyphus/evidence/task-0e-assets-list.json

  Scenario: 触发生成（mock）
    Tool: Bash
    Steps:
      1. curl -X POST http://localhost:8000/api/assets/scene_temple_ruins_bg/generate
      2. 检查返回 task_id 或 status=generating
      3. curl http://localhost:8000/api/assets/scene_temple_ruins_bg/status
    Expected Result: 异步触发 + 状态查询
    Evidence: .sisyphus/evidence/task-0e-generate-trigger.json

  Scenario: 审核操作
    Tool: Bash
    Steps:
      1. curl -X POST http://localhost:8000/api/assets/scene_temple_ruins_bg/approve
      2. curl http://localhost:8000/api/assets/scene_temple_ruins_bg
      3. jq '.status' == "approved"
    Expected Result: 状态更新为 approved
    Evidence: .sisyphus/evidence/task-0e-approve.json
  ```

  **Commit**: YES - `feat(api): /api/assets management endpoints + async generation`

---

### Wave 1: Core (4 parallel tasks)

- [x] 1. 视觉规范层（Style Bible + palette + prompt 模板五段式）

  **What to do**:
  - 创建 `data/visual/style_bible.md`:
    ```markdown
    # Echo Scene Visual Style Bible

    ## World
    Cyber Ancient Civilization — Post-human + Greek mythology

    ## Architecture
    - Ancient marble temple, broken columns
    - Holographic technology overlays
    - Brutalist concrete fused with classical Greek

    ## Technology
    - Cyan neon circuits on stone
    - Floating holograms, quantum interfaces
    - Glowing quantum-lock runes

    ## Atmosphere
    - Dark, mysterious, abandoned
    - Melancholy + decaying grandeur

    ## Lighting
    - Primary: blue-cyan ambient
    - Secondary: purple/magenta accent
    - Danger: neon-red (#ff0040)
    - No warm/yellow light

    ## Color Palette (see palette.yaml)
    - Background: #0a0a0a (near-black)
    - Primary neon: #00ff41 (green)
    - Secondary neon: #00ffff (cyan)
    - Danger: #ff0040 (red)
    - Stone: weathered gray marble
    - Metal: oxidized dark bronze
    ```
  - 创建 `data/visual/palette.yaml`:
    - 完整色卡定义（hex 值 + 用途说明）
  - 创建 `data/visual/prompts.yaml`:
    - 五段式 prompt 模板（世界→空间→镜头→材质→negative）
    - 背景图模板: 含 wide cinematic composition + empty foreground + game environment
    - 对象统一前缀: `single object, centered, isolated, transparent background, game asset, front view, high detail`
    - 每个具体对象的完整 prompt（门/尸体/祭坛/柱子）
    - negative prompt 通用模板: `people, characters, text, logo, watermark, modern buildings, cars, low quality, blurry`
  - 这个任务的产出是**数据文件**（非代码），被 T0a 生图模块和审核页面引用

  **Must NOT do**:
  - 不写代码逻辑（纯规范文档）
  - prompt 不含具体 API key

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 创作密集型，需要理解游戏世界观 + prompt 工程
  - **Skills**: []

  **Parallelization**: Wave 1 | Blocks: T9 | Blocked By: None

  **References**:
  - 现有场景描述: `data/scenes/temple_ruins.yaml`（description/atmosphere）
  - 现有视觉风格: `frontend/src/index.css` + `tailwind.config.js`
  - 蓝图中的赛博朋克 + 希腊神话融合设定

  **Acceptance Criteria**:
  - [ ] `style_bible.md` 包含 World/Architecture/Technology/Atmosphere/Lighting 各节
  - [ ] `palette.yaml` 有完整 hex 色卡
  - [ ] `prompts.yaml` 有背景图五段式模板
  - [ ] `prompts.yaml` 有 4 个对象的完整 prompt
  - [ ] `prompts.yaml` 有通用 negative prompt
  - [ ] YAML 语法正确

  **QA Scenarios**:
  ```
  Scenario: 规范文件完整性
    Tool: Bash
    Steps:
      1. Test-Path data/visual/style_bible.md
      2. Test-Path data/visual/palette.yaml
      3. Test-Path data/visual/prompts.yaml
      4. python -c "import yaml; yaml.safe_load(open('data/visual/prompts.yaml')); print('OK')"
      5. grep -c "negative" prompts.yaml >= 1
      6. grep -c "single object" prompts.yaml >= 4（4个对象模板）
    Expected Result: 3 个文件存在且语法正确
    Evidence: .sisyphus/evidence/task-1-visual-specs.txt
  ```

  **Commit**: YES - `feat(visual): style bible + color palette + prompt templates`

---

- [x] 2. 后端 GET /api/scene 端点（只返回 approved 素材）

  **What to do**:
  - 在 `backend/app/api/routes.py` 新增 `GET /api/scene`:
    - 从 WorldLoader 加载场景 YAML
    - 从 AssetStore 查询每个对象的素材状态
    - **只返回 status=approved 的素材的 asset 路径**
    - 未 approved 的对象 asset 返回 null（前端用 placeholder）
    - 新增 `position` 字段（从 YAML 读取，T1/后续任务扩展）
  - 创建 `backend/app/models/scene_response.py`:
    - `SceneResponse`: scene_id/name/description/atmosphere/background_asset/objects[]
    - `SceneObjectDTO`: id/name/type/description/position/asset(is_primary/is_dangerous)
    - `is_primary` 逻辑: `is_future_anchor==true` 或对应 interaction_targets 中 `is_dangerous==true`
  - 在 `backend/app/main.py` 注册静态文件: `app.mount("/assets", StaticFiles(directory="data/assets"), name="assets")`
  - 在 `data/scenes/temple_ruins.yaml` 每个对象新增 `position: {x: N, y: N}` 字段（百分比坐标）
  - 单元测试

  **Must NOT do**:
  - 不依赖 LLM（纯 YAML + manifest 读取）
  - 不暴露内部 Pydantic 模型原始结构

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**: Wave 1 | Blocks: T8 | Blocked By: T0b

  **References**:
  - WorldLoader: `backend/app/engine/world_loader.py:22` — `load_scene()`
  - AssetStore: T0b 产出 `backend/app/state/asset_store.py`
  - Scene 模型: `backend/app/models/world.py:126`
  - FastAPI StaticFiles: https://fastapi.tiangolo.com/tutorial/static-files/

  **Acceptance Criteria**:
  - [ ] `GET /api/scene?scene_id=temple_ruins` 返回 200 + JSON
  - [ ] JSON 包含 background_asset（approved 时有值，否则 null）
  - [ ] objects[] 每个有 position + asset（approved 有值否则 null）+ is_primary
  - [ ] 只有 approved 素材的 asset 非空
  - [ ] `/assets/xxx.png` 静态文件可访问
  - [ ] pytest 测试通过

  **QA Scenarios**:
  ```
  Scenario: 场景 API 无 approved 素材
    Tool: Bash (curl)
    Steps:
      1. curl http://localhost:8000/api/scene?scene_id=temple_ruins
      2. jq '.background_asset' == null（未审核）
      3. jq '.objects[0].asset' == null（未审核）
      4. jq '.objects[0].position' 有 x 和 y
      5. jq '.objects[0].is_primary' 是 boolean
    Expected Result: 结构正确，asset 全 null（未审核）
    Evidence: .sisyphus/evidence/task-2-scene-no-approved.json

  Scenario: 审核后场景更新
    Tool: Bash
    Steps:
      1. POST /api/assets/scene_temple_ruins_bg/approve
      2. GET /api/scene → background_asset 非空
    Expected Result: approved 后 asset 路径返回
    Evidence: .sisyphus/evidence/task-2-scene-approved.json
  ```

  **Commit**: YES - `feat(api): GET /api/scene endpoint + static asset serving`

---

- [x] 3. 前端 SceneView + SceneObject 组件

  **What to do**:
  - 创建 `frontend/src/components/SceneView.tsx`:
    - 全屏容器（`fixed inset-0 z-0`）
    - 从 `/api/scene` 加载场景数据
    - 背景图 `<img>` 填充（`object-cover`）
    - 背景 asset 为 null 时 → 渲染 `AssetPlaceholder`（T0c）
    - 渲染 `SceneObject[]` 子组件
    - loading 状态: CRT 风格 "LOADING SCENE..."
  - 创建 `frontend/src/components/SceneObject.tsx`:
    - 绝对定位（`style={{ left: x%, top: y% }}`）
    - `isPrimary` prop 控制行为:
      - primary: `hover:shadow-[0_0_20px_#00ffff]` + `hover:scale-105` + `cursor-pointer`
      - secondary: `opacity-70` 无 hover 效果
    - asset 为 null → 渲染 placeholder 方块
    - 点击调用 `onClick(objectId, objectName, isPrimary)` 回调
    - 全息祭坛特殊: CSS `mix-blend-mode: screen`（T9 精调）
  - 创建 `frontend/src/hooks/useScene.ts`:
    - `fetch('/api/scene')` → 缓存 state
    - 提供 `scene` / `loading` / `error`
  - 创建 `frontend/src/types/scene.ts`:
    - Position / SceneObjectDTO / SceneResponse 接口

  **Must NOT do**:
  - 不实现点击→填输入栏逻辑（T6）
  - 不改 App.tsx 布局（T5）
  - 不安装动画库

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**: Wave 1 | Blocks: T5,T6 | Blocked By: T0c

  **References**:
  - T0c AssetPlaceholder: `frontend/src/components/AssetPlaceholder.tsx`
  - 现有全屏组件: `frontend/src/components/GodWatchIndicator.tsx`
  - CRT 效果: `frontend/src/index.css`
  - API client: `frontend/src/api/client.ts`

  **Acceptance Criteria**:
  - [ ] SceneView 渲染全屏背景图或 placeholder
  - [ ] 4 个 SceneObject 定位正确
  - [ ] 主要对象 hover 有发光效果
  - [ ] 次要对象 opacity 低无 hover
  - [ ] asset 为 null 时渲染 placeholder
  - [ ] loading 状态有 CRT 提示
  - [ ] `tsc --noEmit` 零错误

  **QA Scenarios**:
  ```
  Scenario: 场景渲染（placeholder 模式）
    Tool: Playwright
    Steps:
      1. 确保 manifest 无 approved 素材
      2. 导航到 localhost:5173
      3. 检查背景是 placeholder 非 img
      4. 检查 4 个对象方块可见
      5. hover 第一个对象 → box-shadow 变化
    Expected Result: placeholder 模式渲染正常
    Evidence: .sisyphus/evidence/task-3-scene-placeholder.png

  Scenario: 场景渲染（有素材模式）
    Tool: Playwright
    Steps:
      1. mock /api/scene 返回有 asset 的数据
      2. 导航到 localhost:5173
      3. 检查背景是 img 标签
      4. 检查对象 img src 非空
    Expected Result: 真实素材渲染正常
    Evidence: .sisyphus/evidence/task-3-scene-assets.png
  ```

  **Commit**: YES - `feat(frontend): SceneView + SceneObject + placeholder integration`

---

- [x] 4. 审核页面完整功能（连接 API + 生成/审核/轮询）

  **What to do**:
  - 在 `frontend/src/pages/AssetReview.tsx`（T0d 骨架基础上）连接真实 API:
    - 左栏: `GET /api/assets` 加载素材列表，显示状态标签（颜色编码）
    - 中栏: 点击素材项 → 大图预览（approved 时显示图片，否则显示 placeholder）
    - 右栏属性面板:
      - 状态显示（pending/generating/completed/approved/rejected/failed）
      - Prompt 编辑框（`PUT /api/assets/{id}/prompt`）
      - 操作按钮:
        - "生成" (`POST /api/assets/{id}/generate`) — pending/completed/rejected 时可用
        - "通过" (`POST /api/assets/{id}/approve`) — completed 时可用
        - "拒绝" (`POST /api/assets/{id}/reject`) — completed 时可用
        - 按钮根据状态禁用/启用
    - 顶部批量操作:
      - "一键生成所有 pending" (`POST /api/assets/generate-all`)
      - "批量通过" (`POST /api/assets/bulk-approve`)
    - 状态轮询:
      - 当有 generating 状态素材时，每 3 秒轮询 `GET /api/assets/{id}/status`
      - 状态变为 completed 后自动刷新预览图 + 列表
    - 错误显示: failed 状态显示 error_message
  - 创建 `frontend/src/api/assets.ts`:
    - 封装所有 `/api/assets` 端点调用
    - 类型安全的请求/响应

  **Must NOT do**:
  - 不做认证/权限
  - 轮询不过于频繁（3 秒间隔）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**: Wave 1 | Blocks: T8 | Blocked By: T0a,T0d,T0e

  **References**:
  - T0d 骨架: `frontend/src/pages/AssetReview.tsx`
  - T0a ImageGenerator: 后端异步生成
  - T0e API 端点: `/api/assets` 全部端点
  - 现有 API client: `frontend/src/api/client.ts`

  **Acceptance Criteria**:
  - [ ] 素材列表从 API 加载正确显示
  - [ ] 点击素材项切换预览
  - [ ] Prompt 编辑后可保存
  - [ ] "生成"按钮触发生成 + 状态变为 generating
  - [ ] 轮询自动更新状态（generating → completed）
  - [ ] completed 后预览图自动刷新
  - [ ] "通过"/"拒绝"按钮工作 + 更新状态
  - [ ] 批量操作可用
  - [ ] failed 状态显示错误信息
  - [ ] 按钮根据状态正确禁用/启用

  **QA Scenarios**:
  ```
  Scenario: 完整审核流程
    Tool: Playwright
    Steps:
      1. 导航到 /admin/assets
      2. 点击第一个 pending 素材
      3. 点击"生成"按钮
      4. 等待状态变为 completed（轮询，最多 60s）
      5. 检查预览图显示
      6. 点击"通过"
      7. 检查状态变为 approved
    Expected Result: 完整审核流程跑通
    Evidence: .sisyphus/evidence/task-4-review-flow.png

  Scenario: Prompt 编辑 + 重新生成
    Tool: Playwright
    Steps:
      1. 选择一个 rejected 素材
      2. 修改 prompt 文本
      3. 保存
      4. 点击"生成"
      5. 检查 prompt 已更新
    Expected Result: prompt 修改后重新生成
    Evidence: .sisyphus/evidence/task-4-prompt-edit.png

  Scenario: 批量生成
    Tool: Playwright
    Steps:
      1. 点击"一键生成所有 pending"
      2. 等待所有素材状态变化
      3. 检查列表更新
    Expected Result: 批量生成触发
    Evidence: .sisyphus/evidence/task-4-bulk-generate.png
  ```

  **Commit**: YES - `feat(review): asset review page full functionality + polling`

---

### Wave 2: Interaction (3 parallel tasks)

- [x] 5. 布局改造（场景全屏 z-0 + 终端浮层 z-20）

  **What to do**:
  - 改造 `frontend/src/App.tsx`:
    - 路由判断: `/admin/assets` → AssetReview 页面；其他 → 游戏场景
    - 游戏场景布局:
      - `<SceneView />` 全屏 z-0
      - `<Terminal />` 浮层 z-20（底部，bg-black/70，高度 ~45%）
      - `<StatusPanel />` 浮层 z-20（右侧，bg-black/70，宽度 ~300px）
      - `<GodWatchIndicator />` z-50（最顶层）
    - 场景对象分布在上半屏（y < 50%），不被终端遮挡
  - 终端浮层样式:
    - `absolute bottom-0 left-0 right-[320px] z-20 bg-black/70 backdrop-blur-sm border-t border-neon-green`
  - StatusPanel 浮层:
    - `absolute top-0 right-0 w-[300px] h-full z-20 bg-black/70 backdrop-blur-sm border-l border-neon-green`

  **Must NOT do**:
  - 不改 Terminal/StatusPanel 内部逻辑
  - 不删除现有功能

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**: Wave 2 | Blocks: T8 | Blocked By: T3

  **References**:
  - 现有 App.tsx: `frontend/src/App.tsx:33-50`
  - T3 SceneView: `frontend/src/components/SceneView.tsx`
  - Tailwind backdrop-blur: https://tailwindcss.com/docs/backdrop-blur

  **Acceptance Criteria**:
  - [ ] 场景背景全屏 z-0
  - [ ] 终端底部浮层 z-20 半透明
  - [ ] StatusPanel 右侧浮层 z-20 半透明
  - [ ] 场景上半屏不被遮挡
  - [ ] GodWatchIndicator z-50 顶层
  - [ ] `/admin/assets` 路由切换正确
  - [ ] `tsc --noEmit` 零错误

  **QA Scenarios**:
  ```
  Scenario: 布局分层
    Tool: Playwright
    Steps:
      1. 导航到 localhost:5173
      2. 截图全屏
      3. 检查 z-index 分层（SceneView < Terminal < GodWatch）
      4. 检查终端有 bg-black/70 透明度
      5. 检查场景上半部分无遮挡
    Expected Result: 分层布局正确
    Evidence: .sisyphus/evidence/task-5-layout.png

  Scenario: 路由切换
    Tool: Playwright
    Steps:
      1. 导航到 localhost:5173/admin/assets
      2. 检查审核页面显示
      3. 点击返回游戏链接
      4. 检查游戏场景显示
    Expected Result: 路由切换正常
    Evidence: .sisyphus/evidence/task-5-routing.png
  ```

  **Commit**: YES - `feat(layout): fullscreen scene + floating panels + routing`

---

- [x] 6. 对象交互逻辑（点击→输入栏 + hover 分层）

  **What to do**:
  - 在 `SceneObject.tsx` 实现点击逻辑:
    - 主要对象点击 → `onObjectClick(objectId, objectName, true)` → 填充: `"检查 ${objectName}（${objectId}）"`
    - 次要对象点击 → `onObjectClick(objectId, objectName, false)` → 填充: `"查看 ${objectName}"`
  - 在 App 或 SceneView 管理 `pendingInput` state:
    - `const [pendingInput, setPendingInput] = useState('')`
    - 传递给 Terminal 组件
    - Terminal 接收 prop，变化时 `setInput(pendingInput)` + `inputRef.current.focus()`
  - 完善 hover 分层（T3 骨架已定义，此处确认效果）:
    - primary: `hover:shadow-[0_0_20px_#00ffff]` + `hover:scale-105`
    - secondary: `opacity-70 hover:opacity-90`（轻微变化但不发光）

  **Must NOT do**:
  - 不自动提交（只填充）
  - 不改 Terminal 提交逻辑

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**: Wave 2 | Blocks: T8 | Blocked By: T3

  **References**:
  - Terminal input: `frontend/src/components/Terminal.tsx:116-124`
  - T3 SceneObject: `frontend/src/components/SceneObject.tsx`

  **Acceptance Criteria**:
  - [ ] 点击主要对象 → 输入栏填充完整描述
  - [ ] 点击次要对象 → 输入栏填充简短描述
  - [ ] 填充后输入框获焦
  - [ ] 不自动提交
  - [ ] 主要对象 hover 发光+缩放
  - [ ] 次要对象 hover 轻微变化

  **QA Scenarios**:
  ```
  Scenario: 点击对象填充
    Tool: Playwright
    Steps:
      1. 找到主要对象贴片
      2. 点击
      3. 检查输入框 value 包含 "检查" 或 objectId
      4. 检查输入框获得焦点
      5. 检查未自动提交（无新终端行）
    Expected Result: 输入栏填充+获焦+未提交
    Evidence: .sisyphus/evidence/task-6-click-fill.png
  ```

  **Commit**: YES - `feat(interaction): object click→input + hover glow`

---

- [x] 7. 补全 available_actions / echo_vision / tension_level 展示

  **What to do**:
  - 新增 `frontend/src/components/ActionHints.tsx`:
    - 渲染 `available_actions[]`（来自 ActionResponse）为可点击标签
    - 点击标签 → 填充输入栏（复用 T6 的 pendingInput 机制）
    - 样式: `text-neon-cyan text-xs` 横排标签
  - 在 Terminal 输出区新增 echo_vision 渲染:
    - `result.echo_vision` 非空 → 新增 `type: 'echo'` 历史行
    - 样式: 紫色 text-glow + `[ECHO VISION]` 前缀
  - 在 StatusPanel 新增:
    - `narrative_context.atmosphere` 文本显示
    - `tension_level` 进度条（0-100，红色渐变）
  - 在 `useGameState.tsx` 的 TerminalLine type 新增 `'echo'` 类型

  **Must NOT do**:
  - 不改后端 API 契约

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**: Wave 2 | Blocks: None | Blocked By: None

  **References**:
  - ActionResponse: `frontend/src/types/api.ts:11`
  - TerminalLine: `frontend/src/hooks/useGameState.tsx:6`
  - StatusPanel: `frontend/src/components/StatusPanel.tsx`

  **Acceptance Criteria**:
  - [ ] available_actions 渲染为可点击标签
  - [ ] 点击标签填充输入栏
  - [ ] echo_vision 非空时渲染特殊行
  - [ ] tension_level 进度条显示
  - [ ] atmosphere 文本显示

  **QA Scenarios**:
  ```
  Scenario: 动作提示标签
    Tool: Playwright
    Steps:
      1. 提交 action（mock 或真实）
      2. 检查 available_actions 标签渲染
      3. 点击标签 → 输入栏填充
    Expected Result: 标签可见+可交互
    Evidence: .sisyphus/evidence/task-7-action-hints.png
  ```

  **Commit**: YES - `feat(frontend): available_actions + echo_vision + tension display`

---

### Wave 3: Integration (2 parallel tasks)

- [x] 8. 端到端生图流程集成

  **What to do**:
  - 验证完整链路: 审核页面生成 → manifest 更新 → 场景自动刷新
  - 在 SceneView 添加素材变化感知:
    - 方案 A: 审核操作后触发 `window.dispatchEvent(new CustomEvent('assets-changed'))`，SceneView 监听后重新加载
    - 方案 B: 定期轮询 `/api/scene`（每 10 秒，仅当审核页面打开时）
    - 推荐方案 A（事件驱动，更高效）
  - 在 AssetReview 页面的审核操作后 dispatch 事件
  - 端到端测试:
    1. 场景显示 placeholder
    2. 打开审核页面
    3. 生成素材 → 等待完成
    4. 审核通过
    5. 切换到游戏场景
    6. 验证场景显示真实素材
  - 处理边界情况:
    - 审核页面和游戏场景同时打开（多 tab）
    - 生图超时（3 分钟）
    - 部分素材 approved 部分未审核

  **Must NOT do**:
  - 不引入 WebSocket（事件驱动足够）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**: Wave 3 | Blocks: T9 | Blocked By: T2,T4,T5

  **References**:
  - T2 /api/scene + T4 审核页面 + T5 布局
  - CustomEvent: https://developer.mozilla.org/en-US/docs/Web/API/CustomEvent

  **Acceptance Criteria**:
  - [ ] 审核通过后场景自动刷新素材
  - [ ] 无需手动刷新页面
  - [ ] placeholder → 真实素材过渡平滑
  - [ ] 部分审核时只显示已审核的
  - [ ] 端到端测试通过

  **QA Scenarios**:
  ```
  Scenario: 端到端生图→审核→场景刷新
    Tool: Playwright
    Steps:
      1. 导航到 localhost:5173（场景 placeholder 模式）
      2. 截图 before
      3. 导航到 /admin/assets
      4. 选择背景素材 → 生成 → 等待 completed → 通过
      5. 导航回 localhost:5173
      6. 截图 after
      7. 检查 after 有真实背景图
    Expected Result: 审核通过后场景显示真实素材
    Evidence: .sisyphus/evidence/task-8-e2e-before.png + task-8-e2e-after.png
  ```

  **Commit**: YES - `feat(integration): end-to-end asset generation flow`

---

- [x] 9. prompt 模板集成 + 素材坐标精调

  **What to do**:
  - 将 T1 的 `prompts.yaml` 模板集成到审核页面:
    - 素材初始 prompt 从 `prompts.yaml` 读取（而非硬编码）
    - 审核页面显示 prompt 时标注"来自模板"
    - 修改 prompt 后标注"自定义"
  - 调试对象坐标:
    - 在浏览器中检查 4 个对象位置合理
    - 调整 `temple_ruins.yaml` 的 position 值
    - 确保不被终端/StatusPanel 浮层遮挡
    - 确保对象之间不重叠
  - 全息祭坛特殊处理:
    - CSS `mix-blend-mode: screen`（黑色背景天然透明）
    - 跳过 rembg 背景去除（标记在 manifest 或 YAML）
  - [ENHANCEMENT] CLIP 风格一致性评分（可选）:
    - 如果时间允许，在生图模块加入 CLIP 评分
    - 比较生成图与 style_bible 的 embedding 相似度
    - 阈值 <0.75 标记为"风格偏差，建议重新生成"
    - 这是增强项，不阻塞 V1 交付

  **Must NOT do**:
  - CLIP 评分是可选的，不做不阻塞交付

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**: Wave 3 | Blocks: F1-F4 | Blocked By: T1,T3,T8

  **References**:
  - T1 prompts.yaml: `data/visual/prompts.yaml`
  - T3 SceneObject: 坐标定位
  - T8 端到端流程
  - mix-blend-mode: https://developer.mozilla.org/en-US/docs/Web/CSS/mix-blend-mode

  **Acceptance Criteria**:
  - [ ] 审核页面 prompt 从模板加载
  - [ ] 4 个对象坐标合理（不重叠/不遮挡）
  - [ ] 全息祭坛 mix-blend-mode 效果正确
  - [ ] [可选] CLIP 评分功能（如实现）

  **QA Scenarios**:
  ```
  Scenario: prompt 模板集成
    Tool: Playwright
    Steps:
      1. 导航到 /admin/assets
      2. 检查素材 prompt 与 prompts.yaml 一致
      3. 检查标注"来自模板"
    Expected Result: prompt 从模板加载
    Evidence: .sisyphus/evidence/task-9-prompt-template.png

  Scenario: 坐标布局
    Tool: Playwright
    Steps:
      1. 导航到 localhost:5173
      2. 截图
      3. 检查 4 个对象不重叠
      4. 检查不被终端浮层遮挡
    Expected Result: 坐标合理
    Evidence: .sisyphus/evidence/task-9-coordinates.png
  ```

  **Commit**: YES - `feat(polish): prompt template integration + coordinate tuning`

---

## Final Verification Wave (MANDATORY)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  逐条验证 "Must Have" 全部实现。搜索 "Must NOT Have" 禁止模式。检查 evidence 文件存在。对比 deliverables 与 plan。
  重点验证：审核页面功能完整、manifest 状态机正确、approved 素材才能进入场景。
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  运行 `tsc --noEmit` + `oxlint` + `pytest`。检查所有改动文件：`as any`/空catch/console.log/未用import。检查 AI slop。
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill)
  从 clean state 启动。Playwright 验证两条路径：
  1. 审核页面：导航到 `/admin/assets` → 触发生成 → 等待完成 → 审核通过 → 截图
  2. 场景页面：导航到 `/` → 场景背景加载 → 对象贴片可见 → hover 发光 → 点击填输入栏 → 截图
  截图存 `.sisyphus/evidence/final-qa/`。
  Output: `Scenarios [N/N pass] | Screenshots [N] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  每个任务 spec vs 实际 diff 1:1 对比。检查无超范围改动。检测跨任务文件污染。
  重点：审核页面是否引入了不必要的依赖、manifest 是否被多处直接修改（应通过 API）。
  Output: `Tasks [N/N compliant] | VERDICT`

---

## Commit Strategy

- **Wave 0**: `feat(infra): image generator + manifest + placeholder + asset API + review scaffold`
- **Wave 1**: `feat(core): visual style system + scene API + SceneView + asset review UI`
- **Wave 2**: `feat(ui): layout overlay + object interaction + action hints`
- **Wave 3**: `feat(integration): end-to-end generation flow + coordinate tuning`
- **FINAL**: `test(scene): E2E QA + full verification`

---

## Success Criteria

### Verification Commands
```bash
# 审核页面可访问
curl -s http://localhost:5173/admin/assets | grep -i "asset\|review\|审核"

# 素材状态 API
curl -s http://localhost:8000/api/assets | jq '.assets[0].status'

# 触发单张生成
curl -s -X POST http://localhost:8000/api/assets/scene_temple_ruins_bg/generate

# 审核通过
curl -s -X POST http://localhost:8000/api/assets/scene_temple_ruins_bg/approve

# 场景只返回 approved 素材
curl -s http://localhost:8000/api/scene | jq '.background_asset'

# 前端构建
cd frontend && npx tsc --noEmit && npm run build
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] 审核页面 `/admin/assets` 完整功能
- [ ] manifest 状态机正确流转
- [ ] approved 素材才能进入场景
- [ ] 场景背景全屏 + 对象可交互
- [ ] 终端浮层半透明叠加
- [ ] 降级占位符在素材缺失时生效
- [ ] 视觉规范层（Style Bible + prompt 模板）存在
- [ ] Prompt 元数据 + seed 保存
