# 项目目录结构优化 — 实施计划

## TL;DR

> **目标**: 根据 `docs/plans/2026-08-04-directory-structure-recommendations.md` + 治理五表，优化后端 `services/` 扁平结构为领域目录、迁移 `weight_matrix.yaml` 入版本控制、前端页面按功能域归组。
>
> **当前状态**: P0-a（根目录脚本归集）已在上轮操作中完成。本计划覆盖剩余 P0-b / P2-a / P2-b。

---

## Context

### 当前实际代码目录（已含上轮 P0-a 迁移结果）

```
H:\UGC\                              # 31 个条目（已清理临时脚本）
├── scripts/                         # ✅ 已有：api_test.ps1, check_error.py, reset_failed_assets.py
├── experiments/                     # ✅ 已有：14个 test_*.py + test_wanxiang/
├── backend/
│   └── app/
│       ├── services/                # 🔴 12个文件扁平堆放（待迁移）
│       │   ├── seed_engine.py
│       │   ├── backward_generator.py
│       │   ├── gap_detector.py
│       │   ├── cycle_checker.py
│       │   ├── dimension_generator.py
│       │   ├── rule_mapper.py
│       │   ├── generation_scheduler.py
│       │   ├── generation_planner.py
│       │   ├── prompt_builder.py
│       │   ├── prompt_fusion.py
│       │   └── graph_extractor.py
│       ├── api/                     # 6个路由文件（保持）
│       ├── models/                  # 数据模型（保持）
│       ├── engine/                  # 规则引擎（保持）
│       ├── ai/                      # AI服务层（保持）
│       ├── state/                   # 持久化层（保持）
│       ├── config/                  # 配置
│       │   ├── paths.py             # ← WEIGHT_MATRIX_PATH 指向 data/
│       │   └── settings.py
│       └── utils/
├── frontend/
│   └── src/
│       ├── pages/                   # 3个页面扁平（待归组）
│       │   ├── GraphEditor.tsx
│       │   ├── GraphAssetReview.tsx
│       │   └── AssetReview.tsx
│       ├── components/              # 9个组件 + graph/ 子目录（部分待归组）
│       │   ├── Terminal.tsx
│       │   ├── StatusPanel.tsx
│       │   ├── SceneView.tsx
│       │   ├── SceneObject.tsx
│       │   ├── ActionHints.tsx
│       │   ├── GodWatchIndicator.tsx
│       │   ├── TypewriterText.tsx
│       │   ├── ResetButton.tsx
│       │   ├── AssetPlaceholder.tsx
│       │   └── graph/               # 已有子目录
│       ├── api/
│       ├── hooks/
│       └── types/
└── data/
    ├── weight_matrix.yaml           # 🔴 源码级配置放在运行时数据目录
    └── assets/
```

### 已完成的工作

| 项 | 状态 | 说明 |
|---|---|---|
| P0-a 根目录脚本归集 | ✅ 已完成 | `scripts/` 3个文件 + `experiments/` 15个条目 |

### 依据文档

- `docs/plans/2026-08-04-directory-structure-recommendations.md`（475行完整建议）
- `docs/governance/5_engineering-governance.md` §2 目录结构规范
- `docs/governance/2_product-architecture.md` §2 系统全景图（A创作 / B社区 / C商业...）

---

## Work Objectives

### Core Objective
将后端扁平 `services/` 拆分为领域目录 `domains/`，迁移 `weight_matrix.yaml` 到版本控制位置，前端页面/组件按功能域归组。**纯结构迁移，不写新功能代码。**

### Concrete Deliverables
1. `backend/app/domains/creation/{seed,constraint,asset,graph}/` 目录结构 + 12个文件迁入
2. 全部 import 路径更新（约20处）
3. `data/weight_matrix.yaml` → `backend/app/config/weight_matrix.yaml`
4. 前端 `pages/` 建子目录 + 现有3页面迁入
5. 前端 `components/` 归组 terminal/ + shared/

### Must NOT Have（边界）
- ❌ 不创建空目录占位（`community/`, `module/`, `gm_runtime/` 等 Sprint 1+ 才用的目录）
- ❌ 不新增模型文件（`models/module.py`, `models/user.py` 等）
- ❌ 不新增 API 路由
- ❌ 不做 monorepo 改造
- ❌ 不修改任何 .py 文件的内部逻辑，只移动文件 + 改 import
- ❌ 不在 `__init__.py` 中加 re-export（纯包标记）

---

## Verification Strategy

### 验证命令
```bash
# 后端：应用能正常加载
cd backend && python -c "from app.main import app; print('OK')"

# 后端：所有新路径可导入
python -c "from app.domains.creation.seed.seed_engine import SeedEngine; print('OK')"
python -c "from app.domains.creation.constraint.dimension_generator import DimensionGenerator; print('OK')"
python -c "from app.domains.creation.asset.generation_scheduler import GenerationScheduler; print('OK')"
python -c "from app.domains.creation.graph.graph_extractor import GraphExtractor; print('OK')"

# 后端：测试套件
pytest --tb=short

# 后端：weight_matrix 加载
python -c "from app.config.paths import WEIGHT_MATRIX_PATH; print(WEIGHT_MATRIX_PATH)"

# 前端：构建通过
cd frontend && npm run build
```

---

## TODOs

- [x] 1. 后端 services/ → domains/ 目录创建 + 文件迁移

  **What to do**:
  - 创建目录结构：`backend/app/domains/creation/{seed,constraint,asset,graph}/`
  - 每个目录创建 `__init__.py`（仅含 `"""package docstring."""`）
  - 用 `git mv` 迁移12个文件（保留 git 历史）：

  | 源文件 | 目标路径 |
  |---|---|
  | `services/seed_engine.py` | `domains/creation/seed/seed_engine.py` |
  | `services/backward_generator.py` | `domains/creation/seed/backward_generator.py` |
  | `services/gap_detector.py` | `domains/creation/seed/gap_detector.py` |
  | `services/cycle_checker.py` | `domains/creation/seed/cycle_checker.py` |
  | `services/dimension_generator.py` | `domains/creation/constraint/dimension_generator.py` |
  | `services/rule_mapper.py` | `domains/creation/constraint/rule_mapper.py` |
  | `services/generation_scheduler.py` | `domains/creation/asset/generation_scheduler.py` |
  | `services/generation_planner.py` | `domains/creation/asset/generation_planner.py` |
  | `services/prompt_builder.py` | `domains/creation/asset/prompt_builder.py` |
  | `services/prompt_fusion.py` | `domains/creation/asset/prompt_fusion.py` |
  | `services/graph_extractor.py` | `domains/creation/graph/graph_extractor.py` |

  - 旧 `services/__init__.py` 保留，内容替换为弃用说明注释
  - 删除 `services/` 下已迁走的 .py 文件

  **Must NOT do**:
  - 不修改任何 .py 文件的函数/类/逻辑
  - 不在 `__init__.py` 加 re-export

  **Acceptance Criteria**:
  - [ ] `backend/app/domains/creation/seed/` 含4个 .py 文件
  - [ ] `backend/app/domains/creation/constraint/` 含2个 .py 文件
  - [ ] `backend/app/domains/creation/asset/` 含4个 .py 文件
  - [ ] `backend/app/domains/creation/graph/` 含1个 .py 文件
  - [ ] 每个新目录有 `__init__.py`
  - [ ] `services/` 目录下只剩 `__init__.py`（弃用标记）

---

- [x] 2. 后端 import 路径全量更新

  **What to do**:
  - 搜索全代码库 `from app.services.` 的所有引用，逐个替换为新路径
  - 完整清单（基于实际 grep 结果）：

  **api/ 层（7处）：**
  | 文件 | 行号 | 旧 import | 新 import |
  |---|---|---|---|
  | `api/assets_routes.py` | 65,243,293 | `app.services.generation_planner` | `app.domains.creation.asset.generation_planner` |
  | `api/constraints_routes.py` | 12 | `app.services.dimension_generator` | `app.domains.creation.constraint.dimension_generator` |
  | `api/deps.py` | 22,102 | `app.services.dimension_generator` | `app.domains.creation.constraint.dimension_generator` |
  | `api/graph_routes.py` | 75 | `app.services.graph_extractor` | `app.domains.creation.graph.graph_extractor` |
  | `api/graph_routes.py` | 206 | `app.services.generation_scheduler` | `app.domains.creation.asset.generation_scheduler` |
  | `api/seed_routes.py` | 17 | `app.services.seed_engine` | `app.domains.creation.seed.seed_engine` |
  | `api/seed_routes.py` | 161 | `app.services.rule_mapper` | `app.domains.creation.constraint.rule_mapper` |

  **domains/ 内部交叉引用（7处）：**
  | 文件 | 行号 | 旧 import | 新 import |
  |---|---|---|---|
  | `seed_engine.py` | 31 | `app.services.backward_generator` | `app.domains.creation.seed.backward_generator` |
  | `seed_engine.py` | 32 | `app.services.cycle_checker` | `app.domains.creation.seed.cycle_checker` |
  | `seed_engine.py` | 33 | `app.services.gap_detector` | `app.domains.creation.seed.gap_detector` |
  | `seed_engine.py` | 34,367 | `app.services.rule_mapper` | `app.domains.creation.constraint.rule_mapper` |
  | `cycle_checker.py` | 27 | `app.services.backward_generator` | `app.domains.creation.seed.backward_generator` |
  | `generation_scheduler.py` | 20 | `app.services.prompt_fusion` | `app.domains.creation.asset.prompt_fusion` |

  **tests/ 层（6处）：**
  | 文件 | 旧 import | 新 import |
  |---|---|---|
  | `tests/unit/test_graph_extractor.py:20` | `app.services.graph_extractor` | `app.domains.creation.graph.graph_extractor` |
  | `tests/integration/test_constraints_api.py:13` | `app.services.dimension_generator` | `app.domains.creation.constraint.dimension_generator` |
  | `tests/unit/test_dimension_service.py:21` | `app.services.dimension_generator` | `app.domains.creation.constraint.dimension_generator` |
  | `tests/integration/test_generation_chain_integration.py:17,25` | `app.services.generation_planner` / `prompt_builder` | `app.domains.creation.asset.*` |
  | `tests/unit/test_generation_planner.py:6` | `app.services.generation_planner` | `app.domains.creation.asset.generation_planner` |
  | `tests/unit/test_prompt_builder.py:6` | `app.services.prompt_builder` | `app.domains.creation.asset.prompt_builder` |

  **experiments/ 脚本（如存在引用）：**
  - `experiments/demo_pipeline*.py`, `experiments/demo_run.py` 中如有 `app.services.dimension_generator` 引用，更新为新路径

  **Acceptance Criteria**:
  - [ ] `grep -r "from app.services" backend/` 返回0个结果（除 `services/__init__.py` 弃用注释）
  - [ ] `python -c "from app.main import app"` 成功

---

- [x] 3. weight_matrix.yaml 迁移到版本控制

  **What to do**:
  - `git mv data/weight_matrix.yaml backend/app/config/weight_matrix.yaml`
  - 修改 `backend/app/config/paths.py` 第39行：
    ```python
    # 旧: WEIGHT_MATRIX_PATH: Path = DATA_DIR / "weight_matrix.yaml"
    # 新: WEIGHT_MATRIX_PATH: Path = Path(__file__).parent / "weight_matrix.yaml"
    ```
  - 检查 `.gitignore` 确认 `backend/app/config/weight_matrix.yaml` 未被忽略
  - 检查 `data/.gitignore` 不影响新位置

  **Acceptance Criteria**:
  - [ ] `backend/app/config/weight_matrix.yaml` 存在且内容完整
  - [ ] `python -c "from app.config.paths import WEIGHT_MATRIX_PATH; print(WEIGHT_MATRIX_PATH)"` 输出 `backend/app/config/weight_matrix.yaml`
  - [ ] `python -c "from app.domains.creation.constraint.dimension_generator import WeightMatrixLoader; l=WeightMatrixLoader(); print('loaded')"` 成功

---

- [x] 4. 前端 pages/ 按功能域建子目录 + 现有页面迁入

  **What to do**:
  - 创建子目录：
    - `frontend/src/pages/graph/` — 图谱相关页面
  - 迁移现有3个页面（只移动现有文件，不创建新页面）：
    | 源文件 | 目标路径 |
    |---|---|
    | `pages/GraphEditor.tsx` | `pages/graph/GraphEditor.tsx` |
    | `pages/GraphAssetReview.tsx` | `pages/graph/GraphAssetReview.tsx` |
    | `pages/AssetReview.tsx` | `pages/graph/AssetReview.tsx` |

    > AssetReview 是资产审核页面，与图谱资产审核同域，暂归 graph/。后续新增 editor/ 等域时再拆。

  - 更新 `App.tsx` 中的 import 路径（第8-10行）：
    ```typescript
    // 旧
    import { AssetReview } from './pages/AssetReview';
    import { GraphAssetReview } from './pages/GraphAssetReview';
    import GraphEditorWrapper from './pages/GraphEditor';
    // 新
    import { AssetReview } from './pages/graph/AssetReview';
    import { GraphAssetReview } from './pages/graph/GraphAssetReview';
    import GraphEditorWrapper from './pages/graph/GraphEditor';
    ```

  **Must NOT do**:
  - 不创建空页面子目录（editor/, community/ 等没有对应文件就不建）
  - 不新增页面组件
  - 不改路由逻辑（pathname 分发保持不变）

  **Acceptance Criteria**:
  - [ ] `pages/graph/` 含3个 .tsx 文件
  - [ ] `App.tsx` import 路径已更新
  - [ ] `npm run build` 成功

---

- [x] 5. 前端 components/ 终端组件归组

  **What to do**:
  - 创建 `frontend/src/components/terminal/` 子目录
  - 迁移终端相关组件：
    | 源文件 | 目标路径 |
    |---|---|
    | `components/Terminal.tsx` | `components/terminal/Terminal.tsx` |
    | `components/TypewriterText.tsx` | `components/terminal/TypewriterText.tsx` |
    | `components/StatusPanel.tsx` | `components/terminal/StatusPanel.tsx` |
    | `components/SceneView.tsx` | `components/terminal/SceneView.tsx` |
    | `components/SceneObject.tsx` | `components/terminal/SceneObject.tsx` |
    | `components/ActionHints.tsx` | `components/terminal/ActionHints.tsx` |
    | `components/GodWatchIndicator.tsx` | `components/terminal/GodWatchIndicator.tsx` |

  - 创建 `frontend/src/components/shared/` 子目录
  - 迁移通用组件：
    | 源文件 | 目标路径 |
    |---|---|
    | `components/ResetButton.tsx` | `components/shared/ResetButton.tsx` |
    | `components/AssetPlaceholder.tsx` | `components/shared/AssetPlaceholder.tsx` |

  - 更新所有 import 引用（主要是 `App.tsx` 和 `pages/`）
  - `components/graph/` 已有，不动

  **Acceptance Criteria**:
  - [ ] `components/terminal/` 含7个 .tsx 文件
  - [ ] `components/shared/` 含2个 .tsx 文件
  - [ ] `components/graph/` 不变
  - [ ] `npm run build` 成功

---

- [x] 6. 验证 + 文档更新

  **What to do**:
  - 后端验证：
    ```bash
    cd backend
    python -c "from app.main import app; print('FastAPI OK')"
    pytest --tb=short -q
    ```
  - 前端验证：
    ```bash
    cd frontend
    npm run build
    ```
  - 更新 `README.md` 项目结构章节中的路径引用
  - 更新 `docs/governance/5_engineering-governance.md` §2.3 迁移计划状态

  **Acceptance Criteria**:
  - [ ] 后端 `from app.main import app` 成功
  - [ ] 后端 pytest 无新增失败
  - [ ] 前端 `npm run build` 成功
  - [ ] README 项目结构章节路径已更新

---

## Commit Strategy

- 单次 commit：`refactor: migrate services/ to domains/ + weight_matrix to config/ + frontend pages grouping`
- 或分3次：后端 domains 迁移 / weight_matrix 迁移 / 前端归组

---

## Success Criteria

- [ ] `backend/app/services/` 下只剩 `__init__.py`（弃用标记）
- [ ] `backend/app/domains/creation/{seed,constraint,asset,graph}/` 结构完整
- [ ] 全库无 `from app.services.` 引用（弃用注释除外）
- [ ] `weight_matrix.yaml` 在 `backend/app/config/` 下
- [ ] 前端 `pages/graph/` + `components/terminal/` + `components/shared/` 结构就位
- [ ] 后端 pytest 通过
- [ ] 前端 build 通过
