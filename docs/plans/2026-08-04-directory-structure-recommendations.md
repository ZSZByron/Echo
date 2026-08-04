# 项目目录结构建议

> **日期**: 2026-08-04
> **项目**: H:\UGC — Echo UGC → TRPG 众创孵化平台
> **文档类型**: 结构建议 / 不含实施
> **状态**: 建议稿（用户要求只提建议，不自动修改）
> **关联文档**:
> - `docs/plans/2026-08-04-platform-architecture.md` (平台架构)
> - `docs/plans/2026-08-04-trpg-pipeline-mapping.md` (TRPG 全流程映射)
> **README 引用**: `README.md` 项目结构章节

---

## 〇、当前结构快照

### 后端 `backend/app/`（12 个子目录/文件）

```
app/
├── main.py
├── orchestrator.py
├── api/          # 6 个路由文件（routes, graph_routes, assets_routes, seed_routes, constraints_routes, deps）
├── engine/       # 规则引擎（rules_engine, physics, god_intervention, world_loader）
├── models/       # 17 个数据模型文件
├── services/     # 12 个业务服务文件（扁平）
├── ai/           # AI 服务层（provider, parser, renderer, image_generator...）
├── state/        # 持久化层（database, asset_store, graph_store, migrations）
├── config/
└── utils/
```

### 前端 `frontend/src/`（11 个子目录/文件）

```
src/
├── App.tsx
├── pages/        # 3 个页面（GraphEditor, GraphAssetReview, AssetReview）
├── components/   # 10 个组件（含 graph/ 子目录）
├── api/          # 2 个文件（client.ts, graph.ts）
├── hooks/        # 1 个文件（useGameState.ts）
├── types/        # 1 个文件（graph.ts）
└── ...
```

### 根目录

43 个条目，其中 12+ 个是临时测试脚本。

---

## 一、后端目录结构问题

### 问题 1：`services/` 扁平大杂烩，缺乏领域边界

**现状**: `backend/app/services/` 有 12 个文件平铺，混装了创作工具域（seed_engine, dimension_generator, generation_scheduler...）和基础设施域（graph_extractor）。

**风险**: 随着平台架构文档 Sprint 1-4 新增 `ModuleInheritor`、`ModuleExporter`、`gm_runtime/`（5 个文件）、社区服务（5-8 个文件），这个目录会膨胀到 25+ 个文件平铺，不可维护。

**建议**: 按 pipeline-mapping.md 四层架构（生成侧 → 导出侧 → 运行侧 → 反馈侧）+ platform-architecture.md 八大系统拆分为领域子目录。

```
backend/app/
├── domains/                        # ← 新增：按业务域组织
│   │
│   ├── creation/                   # 创作工具域（平台架构 A 系统）
│   │   │
│   │   ├── seed/                   # 种子引擎（现有文件迁入）
│   │   │   ├── seed_engine.py
│   │   │   ├── backward_generator.py
│   │   │   ├── gap_detector.py
│   │   │   └── cycle_checker.py
│   │   │
│   │   ├── constraint/             # 6 维约束
│   │   │   ├── dimension_generator.py
│   │   │   └── rule_mapper.py
│   │   │
│   │   ├── asset/                  # 资产管线
│   │   │   ├── generation_scheduler.py
│   │   │   ├── generation_planner.py
│   │   │   ├── prompt_builder.py
│   │   │   └── prompt_fusion.py
│   │   │
│   │   ├── graph/                  # 图谱服务
│   │   │   └── graph_extractor.py
│   │   │
│   │   ├── module/                 # ← Sprint 1-2 新增：模组系统（pipeline-mapping A2/A3）
│   │   │   ├── inheritor.py        #   ModuleInheritor（继承-覆写合并）
│   │   │   ├── exporter.py         #   ModuleExporter（装订成册导出）
│   │   │   └── filter.py           #   全局性筛选器（自顶向下筛选世界级设定）
│   │   │
│   │   └── gm_runtime/             # ← Sprint 4 新增：AI GM 运行时（pipeline-mapping A5）
│   │       ├── assistant_mode.py   #   GM 屏（建议 DC + 3 分支）
│   │       ├── auto_mode.py        #   全自动裁决 + 新手保底
│   │       ├── tutorial_mode.py    #   教学弹窗 + 规则提醒
│   │       ├── emotion_fuse.py     #   情感熔断（关键词检测 → 强制降级）
│   │       └── case_cache.py       #   判例缓存（裁决一致性）
│   │
│   ├── community/                  # ← Sprint 1-3 新增：社区互动域（平台架构 B 系统）
│   │   ├── auth/                   #   用户认证（JWT）
│   │   ├── user/                   #   用户主页、作品集
│   │   ├── work/                   #   作品发布、CRUD
│   │   └── interaction/            #   评论、点赞、收藏
│   │
│   └── feedback/                   # ← Sprint 5 新增：反馈收集域（pipeline-mapping 第 4 层）
│       └── collector.py
│
├── api/                            # 路由层（按域分文件，避免膨胀）
│   ├── routes.py                   # 交互终端（现有 /api/action, /api/scene, /api/state）
│   ├── creation_routes.py           # ← 合并 seed + constraints + graph + assets 路由
│   ├── module_routes.py            # ← 新增：/api/module/* （merge, export）
│   ├── gm_routes.py                # ← 新增：/api/gm/* （action, suggest, state, mode）
│   ├── community_routes.py         # ← 新增：/api/auth/* + /api/users/* + /api/works/*
│   └── deps.py                     # 依赖注入（现有）
│
├── models/                         # 数据模型（保持，新增文件）
│   ├── ...                         # 现有 17 个模型文件
│   ├── module.py                   # ← 新增：Module + CampaignPackage（Sprint 1-2）
│   ├── user.py                     # ← 新增：User + UserRole（Sprint 1）
│   ├── work.py                     # ← 新增：Work + WorkType + WorkStatus（Sprint 2）
│   ├── interaction.py              # ← 新增：Comment + Like + Favorite（Sprint 3）
│   └── gm_session.py               # ← 新增：GMSession + GMMode（Sprint 4）
│
├── engine/                         # 规则引擎（保持，gm_runtime 会复用）
├── ai/                             # AI 服务层（保持）
├── state/                          # 持久化层（保持，新增 store）
│   ├── ...                         # 现有（database, asset_store, graph_store, migrations）
│   ├── user_store.py               # ← 新增（Sprint 1）
│   ├── work_store.py               # ← 新增（Sprint 2）
│   └── module_store.py             # ← 新增（Sprint 2）
├── config/
└── utils/
```

**设计依据**:

| 领域子目录 | 对应 platform-architecture 系统 | 对应 pipeline-mapping 层 | TRPG 阶段 |
|---|---|---|---|
| `creation/seed/` | A1. 世界编辑器 | 第 1 层：生成侧 | ①② |
| `creation/constraint/` | A1. 世界编辑器 | 第 1 层：生成侧 | ①② |
| `creation/asset/` | A4. 资产生成 | 第 1 层：生成侧 | ①② |
| `creation/graph/` | A1. 世界编辑器 | 第 1 层：生成侧 | ①② |
| `creation/module/` | A2/A3. 模组编辑器 | 第 1 层：生成侧 | ③④ |
| `creation/gm_runtime/` | A5. AI GM 运行时 | 第 3 层：运行侧 | ⑦ |
| `community/` | B. 社区互动系统 | — | — |
| `feedback/` | E3. 舆论监控 | 第 4 层：反馈侧 | ⑧ |

---

### 问题 2：根目录散落大量临时测试脚本

**现状**: `H:\UGC\` 根目录有 12+ 个临时测试/调试脚本：

```
check_error.py
complete_api_test.py
test_debug_gen.py
test_direct_local.py
test_exact_model.py
test_explicit_local.py
test_free_models.py
test_generate.py
test_image_gen.py
test_local_generation.py
test_models.py
test_wanxiang/
api_test.ps1
reset_failed_assets.py
```

`backend/` 下也有类似情况：`demo_phase1_interactive.py`, `test_e2e_final.py`, `test_e2e_qa.py`, `test_e2e_simple.py`, `test_minimal.py`

**风险**: 根目录 43 个条目中近 1/3 是临时文件，严重干扰项目导航和新人上手。

**建议**:

```
UGC/
├── scripts/                        # ← 新建：运维/一次性脚本
│   ├── api_test.ps1
│   ├── reset_failed_assets.py
│   └── check_error.py
│
├── experiments/                    # ← 新建：临时实验/调试脚本
│   ├── test_debug_gen.py
│   ├── test_direct_local.py
│   ├── test_exact_model.py
│   ├── test_explicit_local.py
│   ├── test_free_models.py
│   ├── test_generate.py
│   ├── test_image_gen.py
│   ├── test_local_generation.py
│   ├── test_models.py
│   └── test_wanxiang/
│
├── tests/                          # 已有：正式测试套件（保持）
└── backend/
    └── tests/                      # 已有：后端正式测试（保持）
```

**影响**: 零风险，纯文件移动。不影响任何 import 路径（这些脚本不参与应用代码）。

---

## 二、前端目录结构问题

### 问题 3：`pages/` 只有 3 个页面，与 MVP 路由设计严重不匹配

**现状**: `frontend/src/pages/` 只有 `GraphEditor.tsx`, `GraphAssetReview.tsx`, `AssetReview.tsx`。

**对照**: platform-architecture.md §4.2 规划了 **14 条 MVP 路由**：

| 路由 | 页面 | 现有？ |
|---|---|---|
| `/` | 首页（推荐作品 + 平台介绍） | ❌ |
| `/auth/login` | 登录页 | ❌ |
| `/auth/register` | 注册页 | ❌ |
| `/editor/world` | 世界编辑器 | ❌ |
| `/editor/module` | 模组编辑器 | ❌ |
| `/editor/asset` | 资产生成器 | ❌ |
| `/editor/export` | 装订成册 | ❌ |
| `/gm` | AI GM 运行时 | ❌ |
| `/graph/editor` | 知识图谱编辑器 | ✅ |
| `/terminal` | 交互终端 Demo | ❌（组件有，页面没有） |
| `/u/:username` | 创作者主页 | ❌ |
| `/works` | 作品浏览 | ❌ |
| `/works/:id` | 作品详情 | ❌ |
| `/settings` | 个人设置 | ❌ |

**建议**:

```
frontend/src/
├── pages/
│   ├── terminal/                   # 交互终端（现有 Terminal 组件迁移为页面）
│   │   └── TerminalPage.tsx        #   /terminal
│   │
│   ├── editor/                     # 创作工具页面组
│   │   ├── WorldEditor.tsx         #   /editor/world（种子 → 6 维 → 知识图谱）
│   │   ├── ModuleEditor.tsx        #   /editor/module（主模组 + 次模组 + 继承覆写）
│   │   ├── AssetGenerator.tsx      #   /editor/asset（概念图 / 地图 / 角色立绘）
│   │   └── ExportPage.tsx          #   /editor/export（Markdown 手册 + AI 配置包）
│   │
│   ├── graph/                      # 图谱相关（现有页面迁入）
│   │   ├── GraphEditor.tsx         #   /graph/editor
│   │   └── GraphAssetReview.tsx    #   /admin/graph-assets
│   │
│   ├── gm/                         # ← Sprint 4 新增：AI GM 运行时
│   │   └── GMRuntime.tsx           #   /gm（助理 / 全自动 / 教学 三种模式切换）
│   │
│   ├── community/                  # ← Sprint 1-3 新增：社区页面
│   │   ├── Login.tsx               #   /auth/login
│   │   ├── Register.tsx            #   /auth/register
│   │   ├── UserProfile.tsx         #   /u/:username
│   │   ├── WorkList.tsx            #   /works
│   │   ├── WorkDetail.tsx          #   /works/:id
│   │   └── Settings.tsx            #   /settings
│   │
│   ├── home/                       # ← 首页
│   │   └── HomePage.tsx            #   /
│   │
│   └── AssetReview.tsx             # 现有 /admin/assets
│
├── components/
│   ├── terminal/                   # 终端相关组件归组
│   │   ├── Terminal.tsx
│   │   ├── TypewriterText.tsx
│   │   ├── StatusPanel.tsx
│   │   ├── SceneView.tsx
│   │   ├── SceneObject.tsx
│   │   ├── ActionHints.tsx
│   │   └── GodWatchIndicator.tsx
│   │
│   ├── editor/                     # ← 新增：创作工具通用组件
│   │   ├── SeedInput.tsx           #   种子输入
│   │   ├── ConstraintPanel.tsx     #   6 维约束面板
│   │   └── ModuleTree.tsx          #   模组继承树
│   │
│   ├── graph/                      # 已有
│   │   ├── NodeBadge.tsx
│   │   ├── PromptPreview.tsx
│   │   └── WaveDivider.tsx
│   │
│   ├── community/                  # ← 新增：社区组件
│   │   ├── WorkCard.tsx
│   │   ├── CommentList.tsx
│   │   ├── TagFilter.tsx
│   │   └── UserAvatar.tsx
│   │
│   └── shared/                     # 通用组件
│       ├── ResetButton.tsx
│       └── AssetPlaceholder.tsx
│
├── api/
│   ├── client.ts                   # 现有：API 客户端基类
│   ├── graph.ts                    # 现有：图谱 API 封装
│   ├── creation.ts                 # ← 新增：seed / constraint / asset API
│   ├── community.ts                # ← 新增：auth / user / work API
│   └── gm.ts                       # ← 新增：GM API（/api/gm/*）
│
├── hooks/
│   ├── useGameState.ts             # 现有
│   ├── useAuth.ts                  # ← 新增：认证状态（Sprint 1）
│   └── useWorks.ts                 # ← 新增：作品列表/详情（Sprint 2）
│
└── types/
    ├── graph.ts                    # 现有
    ├── creation.ts                 # ← 新增：种子/约束/资产 TS 类型
    ├── community.ts                # ← 新增：User/Work/Comment TS 类型
    └── gm.ts                       # ← 新增：GM Session/Mode TS 类型
```

---

## 三、跨项目结构问题

### 问题 4：缺少多端 monorepo 规划

**现状**: 单 Web 项目（`backend/` + `frontend/`）。

**对照**: platform-architecture.md §2 规划了 **Web + 小程序 ×3 + App + 桌面端** 四端。Sprint 5（第 17-20 周）引入小程序，第 7-12 月引入 App / 桌面端。

**风险**: 如果根目录不做规划，多端项目会和现有 `backend/` / `frontend/` 平铺混淆。

**建议**: 在 Sprint 2 结束时评估，多端启动前迁移为 monorepo 结构：

```
UGC/                               # monorepo 根
├── packages/                      # ← 多端包目录
│   ├── web/                       #   ← 现有 frontend/ 迁入
│   ├── miniprogram/               #   ← Sprint 5 新建
│   ├── app/                       #   ← 第 7-12 月新建
│   └── desktop/                   #   ← 第 7-12 月新建
│
├── backend/                       #   保持（多端共享一个 FastAPI 后端）
│
├── shared/                        # ← 新增：多端共享资源
│   └── api-contracts/             #   OpenAPI spec / TypeScript 类型定义
│       ├── openapi.yaml           #   后端生成的 OpenAPI 规范
│       └── types/                 #   前端消费的 TS 类型（自动生成）
│
├── docs/
├── data/
└── ...
```

**MVP 阶段（Sprint 1-4）不需要动**。但建议 Sprint 2 结束时做决策——小程序启动后再迁会很痛。

---

## 四、数据 / 配置文件组织

### 问题 5：`data/` 混装运行时数据和配置数据

**现状**: `data/` 目录混放了：
- 运行时生成的资产图片（`data/assets/`）
- 静态权重矩阵（`data/weight_matrix.yaml`）——这属于源码配置
- SQLite 数据库文件（`backend/ugc.db`）

**风险**:
- `weight_matrix.yaml` 是源码级配置，但放在 `data/` 容易被 `.gitignore` 忽略
- 运行时数据和源码配置混在一起，部署时难以分离

**建议**:

```
UGC/
├── data/                           # 纯运行时数据（.gitignore）
│   ├── assets/                     #   生成的概念图
│   ├── handbooks/                  #   ← Sprint 3：导出手册
│   ├── avatars/                    #   ← Sprint 1：用户头像
│   ├── covers/                     #   ← Sprint 2：作品封面
│   └── ugc.db                      #   SQLite 数据库
│
├── backend/app/config/             # 静态配置文件归属源码（版本控制）
│   ├── __init__.py
│   ├── settings.py                 #   现有
│   └── weight_matrix.yaml          #   ← 从 data/ 迁入
```

**验证**: 迁移后需同步修改 `WeightMatrixLoader` 中的路径引用（README 提到 `data/weight_matrix.yaml`）。

---

## 五、`ConstraintLevel` 枚举放置位置

pipeline-mapping.md 将 `ConstraintLevel`（CORE / MODULE / SCENARIO）定义为**架构基础**——影响数据模型、继承逻辑、导出格式。

**建议放置**: `models/dimension.py`

```
# models/dimension.py （现有文件扩展）

class ConstraintLevel(str, Enum):
    """约束层级标签 — 区分厂家规则 vs 模组规则 vs 场景规则"""
    CORE = "core"          # 厂家硬约束（不可覆写）
    MODULE = "module"      # 模组约束（可被次模组覆写）
    SCENARIO = "scenario"  # 场景约束（临时规则）

# 现有的 ConstraintDimension, CreationLayer, WeightMatrix 不变
```

**理由**:
1. `ConstraintLevel` 是约束的属性，不是 Module 的属性——与 `ConstraintDimension` / `CreationLayer` 语义关联
2. 与现有枚举集中管理模式一致（所有约束相关枚举在同一个文件）
3. `Module` / `CampaignPackage` 数据模型才需要新文件 `models/module.py`

---

## 六、优先级总结

| 优先级 | 建议 | 推荐时机 | 风险 | 理由 |
|:---:|---|---|:---:|---|
| **P0** | `services/` → `domains/` 领域拆分 | Sprint 1 开始前 | 中 | 不拆就无法干净地新增 `module/` 和 `gm_runtime/`；需同步修改 import |
| **P0** | 根目录临时脚本归集到 `scripts/` + `experiments/` | 立即可做 | 低 | 纯文件移动，不影响应用代码 |
| **P1** | `models/` 新增 module.py / user.py / work.py | Sprint 1 | 低 | 数据模型先行，新文件不冲突 |
| **P1** | `api/` 路由按域合并 | Sprint 1 | 中 | 当前 5 个路由文件会膨胀到 10+；需修改 `main.py` 注册 |
| **P1** | 前端 `pages/` 按功能域建子目录 | Sprint 1 | 低 | 14 条路由不能平铺；渐进迁移即可 |
| **P2** | `data/` 分离配置 vs 运行时 | Sprint 1-2 | 低 | `weight_matrix.yaml` 应入版本控制 |
| **P2** | 前端 `components/` 按域归组 | Sprint 1-2 | 低 | 组件少时可渐进 |
| **P3** | monorepo 结构规划 | Sprint 2 后评估 | 高 | 多端启动前需要；迁移成本较大 |

---

## 七、迁移注意事项（如果后续执行）

### 后端 `services/` → `domains/` 迁移

1. **import 路径批量更新**: 所有 `from app.services.seed_engine import ...` → `from app.domains.creation.seed.seed_engine import ...`
2. **`__init__.py` 兼容层**: 可在 `services/__init__.py` 临时 re-export，逐步迁移
3. **测试路径更新**: `tests/unit/` 下的 import 同步修改
4. **建议分批迁移**: 先迁 seed/ → 验证 → 迁 constraint/ → 验证 → ...

### 前端 `pages/` 迁移

1. **路由配置在 `App.tsx`**: 修改 pathname 分发逻辑
2. **渐进迁移**: 新页面直接放新目录，旧页面逐步迁移
3. **组件 import 路径**: 迁移后更新引用

### `data/weight_matrix.yaml` 迁移

1. **修改 `WeightMatrixLoader`**: 路径从 `data/weight_matrix.yaml` → `app/config/weight_matrix.yaml`
2. **修改 README**: 更新文件路径引用
3. **修改测试**: 如果测试硬编码了路径

---

## 八、与架构文档的对照验证

### pipeline-mapping.md 四层架构 → 目录映射

| 架构层 | TRPG 阶段 | 建议目录 | 现有目录 |
|---|---|---|---|
| 第 1 层：生成侧 | ①②③④ | `domains/creation/seed/` + `constraint/` + `module/` | `services/` (扁平) |
| 第 2 层：导出侧 | ⑤ | `domains/creation/module/exporter.py` | ❌ 不存在 |
| 第 3 层：运行侧 | ⑥⑦ | `domains/creation/gm_runtime/` | ❌ 仅 `/api/action` |
| 第 4 层：反馈侧 | ⑧ | `domains/feedback/` | ❌ 不存在 |

### platform-architecture.md 八大系统 → 目录映射

| 系统 | MVP？ | 建议目录 | 现有状态 |
|---|:---:|---|---|
| A. 创作工具 | ✅ | `domains/creation/` | `services/` (部分) |
| B. 社区互动 | ✅ | `domains/community/` | ❌ 不存在 |
| C. 交易市场 | ❌ | `domains/market/` (后置) | ❌ |
| D. 企业服务 | ❌ | `domains/enterprise/` (后置) | ❌ |
| E. 治理系统 | ❌ | `domains/governance/` (后置) | ❌ |
| F. 游戏运行时 | ❌ | `domains/game/` (后置) | ❌ |
| G. 工单分派 | ❌ | `domains/ticket/` (后置) | ❌ |
| H. 推荐匹配 | ❌ | `domains/recommend/` (后置) | ❌ |

> MVP 阶段只需建 `creation/` 和 `community/` 子目录。其余系统后置到对应建设期再建目录。

---

*本文档基于 `2026-08-04-platform-architecture.md` 和 `2026-08-04-trpg-pipeline-mapping.md` 两份规划文档 + 当前代码库实际结构综合编写。仅提供建议，不执行任何修改。*
