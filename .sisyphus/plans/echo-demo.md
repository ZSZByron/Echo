# 回声·AI交互式规则终端 Demo

## TL;DR

> **Quick Summary**: 构建一个"AI交互式规则终端"Demo — 玩家输入自然语言 → AI解析为结构化指令 → Python规则引擎冷酷判决 → AI渲染为赛博朋克叙事 → 前端打字机输出。单一场景深Demo（神殿废墟），3-5条神王规则。核心展示"AI创造性 + 代码确定性"的结合。
>
> **Deliverables**:
> - Vite + React + TS 前端终端（打字机效果 + 状态面板 + 神王干涉红光）
> - FastAPI 后端（规则引擎 + AI服务层 + 混合存储）
> - 全量兼容LLM Provider抽象层（2个Adapter覆盖6家API）
> - 单一场景完整内容（神殿废墟 + 神王规则 + 分支）
> - 6层测试体系（分层应用，规则引擎最严格）
> - 4-Agent流水线质量门禁（规格化→编码→重构→架构审查）
> - 一键验证脚本 + 配置化质量门禁
>
> **Estimated Effort**: Large（5个工作日）
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: T1→T4→T7→T9→T10（5个节点）

---

## Context

### Original Request
构建基于"AI交互 + 规则判定"新形态的《回声》Demo。三层架构：表现层（终端UI）/ 认知层（AI解析+渲染）/ 逻辑层（Python规则引擎）。Demo杀手锏："无论玩家怎么胡搅蛮缠，底层代码都能死死按住逻辑不崩坏，然后让AI去解释这个残酷结果"。

### Interview Summary
**Key Discussions**:
- AI Provider：全量兼容（OpenAI/Anthropic/国产全家桶），配置驱动，"给API就能用"
- 数据存储：混合方案（静态世界设定YAML + 运行时状态SQLite）
- 流式通信：前端模拟打字机（后端一次性返回完整文本）
- Demo内容：单一场景深Demo（神殿废墟，3-5条神王规则）
- 测试策略：6层严格关卡（单元/Gherkin/QA/覆盖率/质量/变异）— **用户明确要求，非协商**
- 质量门禁：4-Agent流水线（规格化→编码→重构→架构审查）— **用户明确要求**

### Review Feedback Processing (2份审查报告)
**采纳15项优化**：任务合并（T1+T2+T7, T3+T4, T8+T9, T12+T13）、新增T0预研、配置化门禁、文件≤400行、时间盒、降级方案等
**拒绝3项建议**：砍mutmut/Gherkin/4-Agent — 这些是用户明确需求，不可替用户删减

### Architecture Overview
```
[Frontend: Vite + React + TS + Tailwind]
   │  ▲ (HTTP POST /api/action, GET /api/state)
   ▼  │
[Backend: FastAPI Orchestrator]
   ├── 1. Intent Parser (Provider → Structured JSON)
   ├── 2. Deterministic Rules Engine (Pure Python, Zero-AI)
   │     ├── Physics Check (Strength vs Hardness)
   │     └── God Intervention Table (Forced Fail on Key Anchors)
   ├── 3. Narrative Renderer (Cyberpunk Prompt → Narrative Text)
   └── 4. State Manager (SQLite via aiosqlite + SQLAlchemy)
```

---

## Work Objectives

### Core Objective
构建可运行、可演示的Demo，证明"AI创造性 + 代码确定性"的结合。核心价值不在"聊天机器人"，而在"规则引擎冷酷判决 + AI温暖叙事"的张力。

### Concrete Deliverables
- 前端：Vite+React+TS终端，打字机效果，状态面板，赛博朋克UI，神王干涉红光
- 后端：FastAPI服务，4个核心模块（Provider/解析器+渲染器/规则引擎/API编排）
- 数据：神殿废墟场景YAML + 3-5条神王规则 + SQLite运行时状态
- 测试：6层测试体系，4-Agent流水线，一键验证脚本
- 配置：一键启动 + `.env.example` + `verify.ps1`

### Definition of Done
- [ ] `cd backend && uvicorn app.main:app --reload` 启动无错误
- [ ] `cd frontend && npm run dev` 启动无错误
- [ ] 玩家输入"我强行砸开这个锁" → 终端显示完整判决+叙事
- [ ] `./scripts/verify.ps1` 全部通过（6层检查串联）
- [ ] 规则引擎覆盖率 ≥ 95%，变异分数 ≥ 80%
- [ ] 切换LLM Provider仅需修改`.env`

### Must Have
- 完整的玩家输入→解析→判决→渲染→打字机输出循环
- 规则引擎绝对确定性（相同输入100次结果完全一致）
- LLM Provider配置驱动切换（至少验证2个不同Provider）
- 3-5条神王规则有明确触发条件、判决逻辑、惩罚机制
- 神王干涉可视化（UI边缘红光/噪点效果）
- 6层测试体系（分层应用，见验证策略矩阵）
- 4-Agent流水线质量门禁（每个任务内嵌）

### Must NOT Have (Guardrails)
- ❌ 不引入litellm/langchain等重型AI框架
- ❌ 不实现真流式API（SSE/WebSocket）— 前端模拟打字
- ❌ 不做多用户/账号/存档系统
- ❌ 不做剧本编辑器或可视化规则配置
- ❌ 不做生产级部署（Docker/K8s）
- ❌ AI层不做变异测试（非确定性逻辑，无意义）
- ❌ UI组件不做Gherkin测试（用Playwright QA覆盖）
- ❌ 单文件不超过400行（配置文件/YAML除外）
- ❌ 单函数不超过50行（judge等核心函数允许，但需注释分段）
- ❌ 单函数圈复杂度不超过10
- ❌ 禁止 `as any` / `# type: ignore` / 空except

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed.

### Test Decision
- **Infrastructure**: 新建（在T1中搭建）
- **Framework**: pytest + pytest-cov + pytest-behave + ruff + mypy + mutmut + radon
- **自动化门禁**: 全部配置在 `pyproject.toml`，通过 `verify.ps1` 一键串联

### 6-Layer Test Strategy (分层应用)

| 层级 | 工具 | 规则引擎 | Provider | 解析/渲染 | API层 | 前端 |
|------|------|---------|----------|----------|-------|------|
| 单元测试 | pytest / vitest | ✅ 必须 | ✅ Mock | ✅ Mock LLM | ✅ TestClient | ✅ hooks逻辑 |
| Gherkin/BDD | pytest-behave | ✅ 必须 | ❌ | ❌ | ✅ 关键流程 | ❌ |
| 覆盖率 | pytest-cov | ✅ ≥95% | ✅ ≥70% | ✅ ≥70% | ✅ ≥80% | ❌ |
| 代码质量 | ruff + mypy | ✅ | ✅ | ✅ | ✅ | eslint+tsc |
| 变异测试 | mutmut | ✅ ≥80% | ❌ | ❌ | ❌ | ❌ |
| QA场景 | Playwright/curl | ✅ | ✅ | ✅ | ✅ | ✅ |

### 配置化质量门禁（机械化执行，非人工查验）

`backend/pyproject.toml` 中嵌入：
```toml
[tool.ruff.lint]
select = ["E", "F", "W", "C90", "I", "N", "UP", "B", "SIM"]
[tool.ruff.lint.mccabe]
max-complexity = 10  # CC ≤ 10 强制门禁
[tool.coverage.run]
branch = true
source = ["app"]
[tool.coverage.report]
fail_under = 85  # 总体覆盖率门禁
[tool.mutmut]
paths_to_mutate = "app/engine/"  # 仅规则引擎
tests_dir = "tests/"
```

### 一键验证脚本 `backend/scripts/verify.ps1`
串联6层检查，任一层失败即停止：
1. ruff check + mypy
2. radon cc（圈复杂度，≥B级）
3. pytest + coverage（--cov-fail-under=85）
4. mutmut run（仅 app/engine/）
5. behave（Gherkin场景）
6. 前端：npm run lint + tsc --noEmit + build

### 4-Agent Pipeline (每个实现任务内嵌的纵向流水线)

```
Stage 1: 需求规格化 (category=writing)
  → 输出精确规格（输入/输出/边界/验收标准）
  → 门禁：规格无歧义、可测试

Stage 2: 编码 (category按任务类型)
  → 代码 + 单元测试
  → 门禁：pytest通过 + 类型检查通过

Stage 3: 重构 (category=unspecified-high)
  → 优化结构（DRY/SOLID/可读性）
  → 门禁：CC≤10 + 文件≤400行 + 测试仍通过

Stage 4: 架构审查 (subagent_type=oracle)
  → 量化检查：覆盖率% + 依赖结构 + 圈复杂度 + 模块大小
  → 门禁：全部达标 → 任务可标记完成
```

### Risk Mitigation (风险缓解)

| 风险 | 概率 | 缓解措施 |
|------|------|---------|
| LLM Provider JSON输出不稳定 | 高 | T0预研 + 解析器增加"非JSON fallback" |
| 神王干涉视觉效果性能差 | 中 | 降级方案：静态红色边框替代CSS动画 |
| API契约前后端不匹配 | 中 | T7定义后立即写 `frontend/src/types/api.ts`（手动复制共享类型） |
| 规则引擎逻辑矛盾 | 低 | T4增加"一致性检查"：同输入跑100次哈希对比 |
| Day3规则引擎未跑通 | 低 | **应急降级**：T6渲染器改为模板字符串（"系统判定：{result}"），砍AI渲染保核心 |

---

## Execution Strategy

### Time-boxing (5个工作日)

```
Day 1 (Wave 1 - 5并行):
├── T0: Prompt预研（2h，先执行验证Provider JSON能力）
├── T1: 全栈脚手架 + 测试infra + 质量门禁配置
├── T2: 模型定义 + 世界内容（神殿废墟+神王表）
├── T3: Provider抽象层（2个Adapter）
└── T4: 规则引擎核心（Demo心脏）

Day 2-3 (Wave 2 - 4并行):
├── T5: SQLite状态管理
├── T6: AI服务层（解析器+渲染器，prompt风格统一）
├── T7: FastAPI编排（端点+交互循环）
└── T8: 前端终端完整版（Terminal+Typewriter+StatusPanel+GodWatch）

Day 4 (Wave 3):
└── T9: 前后端联调 + 神王干涉可视化 + E2E QA

Day 5:
├── T10: 内容调优 + 演示脚本 + 性能验证
└── FINAL: F1-F4 最终验证（4并行）
```

### Parallel Execution Waves

```
Wave 1 (Foundation - 5 parallel):
├── T0:  Prompt预研（Provider JSON mode验证）[quick]
├── T1:  全栈脚手架 + 测试infra [quick]
├── T2:  Pydantic模型 + 世界数据YAML [writing]
├── T3:  LLM Provider抽象层 [deep]
└── T4:  规则引擎核心 [deep]

Wave 2 (Core Modules - 4 parallel):
├── T5:  SQLite运行时状态管理 [unspecified-high]
├── T6:  AI服务层（解析器+渲染器）[deep]
├── T7:  FastAPI端点 + 交互循环编排 [deep]
└── T8:  前端终端完整版 [visual-engineering]

Wave 3 (Integration):
└── T9:  前后端联调 + 神王干涉可视化 + E2E [visual-engineering]

Wave 4 (Content & Verification):
├── T10: 内容调优 + 演示脚本 + 性能验证 [deep]
└── FINAL: F1-F4 (4 parallel reviews, then user okay)

Critical Path: T1 → T4 → T7 → T9 → T10 → FINAL
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 5 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave | Agent |
|------|-----------|--------|------|-------|
| T0 | - | T6 | 1 | quick |
| T1 | - | T2-T4,T7-T8 | 1 | quick |
| T2 | T1 | T4,T5,T6,T7 | 1 | writing |
| T3 | T1 | T6,T7 | 1 | deep |
| T4 | T1,T2 | T7,T9 | 1 | deep |
| T5 | T2 | T7 | 2 | unspecified-high |
| T6 | T2,T3,T0 | T7 | 2 | deep |
| T7 | T4,T5,T6 | T9 | 2 | deep |
| T8 | T1,T2 | T9 | 2 | visual-engineering |
| T9 | T7,T8 | T10,F1-F4 | 3 | visual-engineering |
| T10 | T9 | F1-F4 | 4 | deep |

### Agent Dispatch Summary
- **Wave 1**: T0→quick, T1→quick, T2→writing, T3→deep, T4→deep
- **Wave 2**: T5→unspecified-high, T6→deep, T7→deep, T8→visual-engineering
- **Wave 3**: T9→visual-engineering
- **Wave 4**: T10→deep, F1→oracle, F2→unspecified-high, F3→unspecified-high(+playwright), F4→deep

---

## TODOs

### Wave 1: Foundation (5 parallel tasks)

- [x] 0. Prompt 预研 — 验证各 LLM Provider JSON Mode 能力

  **What to do**:
  - 创建 `backend/research/provider_json_test.py`（临时脚本，非生产代码）
  - 对6家Provider（OpenAI/Anthropic/DeepSeek/Qwen/Kimi/GLM）发送测试请求：
    - 测试 `response_format={"type":"json_object"}` 支持情况
    - 测试 Anthropic 的 tool_use / prefill 方案做结构化输出
    - 测试 prompt-only JSON引导（无原生JSON mode时的fallback）
  - 记录结果到 `backend/research/provider_capabilities.md`：
    - 每家Provider：是否支持原生JSON mode？返回格式是否稳定？延迟？
    - 推荐策略：哪些Provider用JSON mode，哪些用prompt引导+Pydantic校验fallback
  - 测试用API key从 `.env` 读取（如果某家没key，标记"未测试"）

  **Must NOT do**:
  - 不写生产代码（仅研究脚本）
  - 不超过2小时
  - 不因某家Provider不可用而阻塞后续任务

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**: Wave 1 | Blocks: T6 | Blocked By: None

  **References**:
  - OpenAI JSON mode: https://platform.openai.com/docs/guides/structured-outputs
  - Anthropic tool_use: https://docs.anthropic.com/claude/docs/tool-use
  - DeepSeek API: https://platform.deepseek.com/api-docs/
  - Qwen DashScope: https://help.aliyun.com/zh/dashscope/
  - Kimi (Moonshot): https://platform.moonshot.cn/docs/api/chat
  - GLM (智谱): https://open.bigmodel.cn/dev/api/normal-model/glm-4

  **Acceptance Criteria**:
  - [ ] `provider_capabilities.md` 存在且包含至少3家Provider的测试结果
  - [ ] 明确推荐策略：哪些用JSON mode，哪些用fallback
  - [ ] T6实现时可直接参考此文档

  **QA Scenarios**:
  ```
  Scenario: Provider能力报告存在且有内容
    Tool: Bash
    Steps:
      1. Test-Path backend/research/provider_capabilities.md
      2. 检查文件包含 "JSON mode" 关键词
      3. 检查包含至少3家Provider名称
    Expected Result: 文件存在，有实质内容
    Evidence: .sisyphus/evidence/task-0-provider-research.md
  ```

  **Commit**: YES - `docs(research): LLM provider JSON mode capability report`

---

- [x] 1. 全栈脚手架 + 测试基础设施 + 质量门禁配置

  **What to do**:
  - **后端脚手架** (`backend/`):
    - `pyproject.toml` (Python ≥3.11): 依赖 fastapi/uvicorn/httpx/openai/anthropic/pydantic/python-dotenv/sqlalchemy/aiosqlite + 测试依赖 pytest/pytest-asyncio/pytest-cov/pytest-behave/ruff/mypy/mutmut/radon
    - `pyproject.toml` 中嵌入质量门禁配置: ruff(mccabe max-complexity=10, select规则集) + coverage(fail_under=85, branch=true) + mypy(strict=true) + mutmut(paths=app/engine/)
    - 创建 `app/` 包: `__init__.py`, `main.py`(占位), `api/`, `engine/`, `ai/`, `models/`, `state/`
    - `.env.example`: 6家Provider配置模板（ACTIVE_PROVIDER + 各家API_KEY/BASE_URL/MODEL）
  - **前端脚手架** (`frontend/`):
    - `npm create vite@latest . -- --template react-ts`
    - 安装+配置 tailwindcss（赛博朋克色调：黑/绿/红）
    - `tailwind.config.js`: 自定义动画（flicker/scanline/glitch）
    - `src/index.css`: Tailwind directives + CRT扫描线 + text-shadow辉光
    - `vite.config.ts`: server.proxy `/api` → `http://localhost:8000`
    - 目录: `src/components/`, `src/hooks/`, `src/api/`, `src/types/`
    - ESLint + Prettier 配置
  - **测试基础设施** (`backend/tests/`):
    - `tests/unit/`, `tests/features/`, `tests/features/steps/`, `tests/conftest.py`
  - **一键验证脚本** (`backend/scripts/verify.ps1`):
    - 串联6层：ruff→mypy→radon→pytest+cov→mutmut→behave→前端(lint+tsc+build)
    - 每层失败即 `exit 1`
  - **根目录**: `README.md`(启动说明) + `start.ps1`(一键启动前后端)
  - **冒烟测试**: `tests/test_smoke.py` 验证工具链工作

  **Must NOT do**:
  - 不安装 litellm/langchain
  - 不创建 Docker 配置
  - 不写业务逻辑代码（仅占位+配置+工具链）
  - 不设过高覆盖率导致无法通过

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**: Wave 1 | Blocks: T2,T3,T4,T7,T8 | Blocked By: None

  **References**:
  - FastAPI项目结构: https://fastapi.tiangolo.com/tutorial/bigger-applications/
  - Vite React TS: https://vitejs.dev/guide/#scaffolding-your-first-vite-project
  - Tailwind+Vite: https://tailwindcss.com/docs/guides/vite
  - ruff mccabe配置: https://docs.astral.sh/ruff/settings/#lint_mccabe_max-complexity
  - pytest-cov配置: https://coverage.readthedocs.io/en/latest/config.html
  - mutmut配置: https://mutmut.readthedocs.io/

  **Acceptance Criteria**:
  - [ ] `cd backend && python -c "import app"` 无错误
  - [ ] `cd frontend && npm run build` 无错误
  - [ ] `cd backend && pytest tests/test_smoke.py` 通过
  - [ ] `cd backend && ruff check .` 零错误
  - [ ] `cd backend && mypy app/` 零错误
  - [ ] `.env.example` 包含6家Provider配置
  - [ ] `verify.ps1` 存在且可执行（dry-run验证结构）
  - [ ] 目录结构: backend/app/{__init__.py,main.py,api/,engine/,ai/,models/,state/}

  **QA Scenarios**:
  ```
  Scenario: 脚手架全栈可运行
    Tool: Bash
    Steps:
      1. cd backend && python -c "import app; print('OK')"
      2. cd frontend && npx tsc --noEmit
      3. cd backend && pytest tests/test_smoke.py -v
    Expected Result: 3命令均退出码0
    Evidence: .sisyphus/evidence/task-1-scaffold-verify.txt

  Scenario: 质量门禁配置正确
    Tool: Bash
    Steps:
      1. cd backend && grep "max-complexity" pyproject.toml (应为10)
      2. grep "fail_under" pyproject.toml (应为85)
      3. grep "paths_to_mutate" pyproject.toml (应为app/engine/)
    Expected Result: 3项配置均存在且值正确
    Evidence: .sisyphus/evidence/task-1-config-verify.txt

  Scenario: verify.ps1脚本结构完整
    Tool: Bash
    Steps:
      1. cat backend/scripts/verify.ps1
      2. 检查包含6个阶段（ruff/mypy/radon/pytest/mutmut/behave + 前端检查）
      3. 每阶段失败时有exit处理
    Expected Result: 脚本包含6层有序检查
    Evidence: .sisyphus/evidence/task-1-verify-script.txt
  ```

  **Commit**: YES - `chore(scaffold): full-stack setup + 6-layer test infra + quality gates`

---

- [x] 2. Pydantic 模型定义 + 世界数据内容（模型+内容同任务，避免割裂）

  **What to do**:
  - **Pydantic 模型** (`backend/app/models/`):
    - `models/world.py`: `GodKing`(id/name/domain/intervention_threshold/penalty), `WorldRule`(区域物理法则), `Scene`(场景定义+可交互对象列表), `GameObject`(id/name/type/hardness/energy_cost/is_future_anchor), `InteractionTarget`
    - `models/player.py`: `PlayerState`(id/energy/health/strength/intelligence/echo_mode_enabled/mental_stability/location), `PlayerStatus`
    - `models/action.py`: `ParsedIntent`(action_type/target/intensity/risk_acceptance/tool_used), `JudgmentResult`(result:success|fail|forced_fail/reason/damage/state_changes/god_intervention), `NarrativeContext`
    - `models/api.py`: `ActionRequest`(player_input:str), `ActionResponse`(judgment/narrative/updated_state)
  - **前端 TS 类型** (`frontend/src/types/`): 镜像后端API模型（ActionRequest/ActionResponse/PlayerState）
  - **世界数据 YAML**:
    - `data/scenes/temple_ruins.yaml`: 神殿废墟场景（赛博朋克+神话氛围），≥3个可交互对象（古锁门/尸体/祭坛）
    - `data/gods/gods_table.yaml`: 3-5位神王（秩序/混沌/记忆+可选2位），每位含完整字段
    - `data/rules/intervention_table.yaml`: 未来干涉表（哪些对象被哪位神王保护）
    - `data/objects/`: 门/锁/尸体/祭坛具体数值（hardness/energy_cost等）
    - `data/default_player.json`: 默认玩家状态

  **Must NOT do**:
  - 不写业务逻辑（纯数据结构+内容）
  - 不超过5位神王
  - 不做多个场景

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 模型定义需要理解游戏概念，世界数据是创作密集型
  - **Skills**: []

  **Parallelization**: Wave 1 | Blocks: T4,T5,T6,T7 | Blocked By: T1

  **References**:
  - 蓝图中的 Gods_Table / World_Rules / Player_State 概念
  - 蓝图中 ParsedIntent / JudgmentResult JSON 示例
  - Pydantic v2: https://docs.pydantic.dev/latest/
  - 蓝图中神王示例（秩序/混沌/记忆）

  **Acceptance Criteria**:
  - [ ] 所有模型字段有类型注解+docstring
  - [ ] `mypy app/models/` + `ruff check app/models/` 零错误
  - [ ] 前端 `tsc --noEmit` 零错误
  - [ ] 所有YAML语法正确（`yaml.safe_load` 无错误）
  - [ ] 神王3-5位，每位字段完整
  - [ ] 场景≥3个可交互对象
  - [ ] 干涉表明确（对象→神王映射）

  **QA Scenarios**:
  ```
  Scenario: 模型实例化+序列化
    Tool: Bash
    Steps:
      1. python -c "from app.models.action import ParsedIntent; p=ParsedIntent(action_type='brute_force',target='mechanical_lock',intensity='maximum',risk_acceptance=True); print(p.model_dump_json())"
      2. python -c "from app.models.player import PlayerState; ..."
    Expected Result: JSON输出包含所有字段
    Evidence: .sisyphus/evidence/task-2-models-verify.txt

  Scenario: 世界数据完整性
    Tool: Bash
    Steps:
      1. python -c "import yaml,glob;[yaml.safe_load(open(f)) for f in glob.glob('data/**/*.yaml',recursive=True)];print('OK')"
      2. python -c "import yaml;gods=yaml.safe_load(open('data/gods/gods_table.yaml'));assert 3<=len(gods)<=5"
      3. python -c "import yaml;s=yaml.safe_load(open('data/scenes/temple_ruins.yaml'));assert len(s['objects'])>=3"
    Expected Result: 所有断言通过
    Evidence: .sisyphus/evidence/task-2-worlddata-verify.txt
  ```

  **Commit**: YES - `feat(data): Pydantic models + temple ruins world content`

---

- [x] 3. LLM Provider 抽象层（2个Adapter覆盖6家API）

  **What to do**:
  - 创建 `backend/app/ai/provider.py`: 统一LLM接口
    - `class LLMProvider(ABC)`: `async def chat(messages, **kwargs) -> str` | `async def chat_json(messages, **kwargs) -> dict`
    - `class OpenAICompatibleProvider(LLMProvider)`: 使用openai SDK，通过`base_url`适配所有OpenAI兼容API（覆盖OpenAI/DeepSeek/Qwen/Kimi/GLM）
    - `class AnthropicProvider(LLMProvider)`: 使用anthropic SDK原生API，转换message格式
    - `def create_provider(config) -> LLMProvider`: 工厂函数，根据config选择adapter
  - 创建 `backend/app/ai/config.py`: Provider配置
    - `@dataclass ProviderConfig`: provider_type/base_url/api_key/model/temperature/max_tokens
    - 从 `.env` 读取: ACTIVE_PROVIDER + 各家key/url/model
    - 支持热切换: 修改.env重启即生效
  - 单元测试 `tests/unit/test_provider.py`: Mock HTTP，验证provider选择+格式转换

  **Must NOT do**:
  - 不使用 litellm/langchain
  - 不实现流式接口
  - 不做运行时动态切换（重启生效即可）
  - 不硬编码API key

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 架构核心，抽象层设计直接影响后续所有AI服务
  - **Skills**: []

  **Parallelization**: Wave 1 | Blocks: T6,T7 | Blocked By: T1

  **References**:
  - OpenAI Python SDK多base_url: https://github.com/openai/openai-python
  - DeepSeek API兼容文档: https://platform.deepseek.com/api-docs/
  - Qwen DashScope兼容模式: https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope
  - Kimi兼容: https://platform.moonshot.cn/docs/api/chat
  - GLM兼容: https://open.bigmodel.cn/dev/api/normal-model/glm-4
  - Anthropic SDK: https://github.com/anthropics/anthropic-sdk-python

  **Acceptance Criteria**:
  - [ ] `LLMProvider` 抽象类2个抽象方法定义清晰
  - [ ] `OpenAICompatibleProvider` 通过base_url适配≥4家（文档验证）
  - [ ] `AnthropicProvider` 正确转换message格式
  - [ ] 工厂函数根据ACTIVE_PROVIDER返回正确实例
  - [ ] 单元测试覆盖率 ≥ 70%
  - [ ] mypy strict 零错误

  **QA Scenarios**:
  ```
  Scenario: Provider工厂正确选择
    Tool: Bash
    Steps:
      1. ACTIVE_PROVIDER=openai → 验证返回OpenAICompatibleProvider
      2. ACTIVE_PROVIDER=anthropic → 验证返回AnthropicProvider
      3. ACTIVE_PROVIDER=deepseek → 验证返回OpenAICompatibleProvider（兼容模式）
    Expected Result: 工厂正确分发
    Evidence: .sisyphus/evidence/task-3-provider-factory.txt

  Scenario: 错误配置优雅处理
    Tool: Bash
    Steps:
      1. ACTIVE_PROVIDER=invalid → 应抛出ValueError "Unknown provider"
    Expected Result: 明确错误消息
    Evidence: .sisyphus/evidence/task-3-provider-error.txt

  Scenario: Mock调用测试通过
    Tool: Bash
    Steps:
      1. pytest tests/unit/test_provider.py -v --cov=app.ai
    Expected Result: 所有测试通过，覆盖率≥70%
    Evidence: .sisyphus/evidence/task-3-provider-tests.txt
  ```

  **Commit**: YES - `feat(ai): universal LLM provider with 2 adapters`

---

- [x] 4. 核心规则引擎（Demo心脏 — 绝对确定性 + 全套测试）

  **What to do**:
  - 创建 `backend/app/engine/rules_engine.py`: 主判决引擎
    - `class RulesEngine`: 加载世界数据，执行判决流水线
    - `async def judge(intent: ParsedIntent, player: PlayerState) -> JudgmentResult`
    - 流水线: ①加载区域规则 → ②物理/数值校验 → ③神王干涉检查 → ④状态变更计算 → ⑤返回
    - **judge()函数允许≤50行**（复杂判决逻辑，但需注释分段）
  - 创建 `backend/app/engine/physics.py`: 纯函数物理计算
    - `def check_strength_vs_hardness(player_str, target_hardness) -> bool`
    - `def calculate_damage(force, resistance) -> int`
  - 创建 `backend/app/engine/god_intervention.py`: 神王干涉
    - `def check_intervention(target_id, intervention_table) -> GodKing | None`
    - `def apply_penalty(god, player) -> StateChanges`
    - 未来支点对象 → forced_fail
  - 创建 `backend/app/engine/world_loader.py`: YAML → 内存对象
  - **6层全套测试**（规则引擎是核心，最严格）:
    - `tests/unit/test_engine.py`: 每个判决分支、边界值、确定性验证（同输入100次完全一致）
    - `tests/features/engine.feature` + `steps/`: Gherkin场景 (Given/When/Then)
    - 变异测试: mutmut ≥ 80%
    - 覆盖率: ≥ 95%

  **Must NOT do**:
  - 规则引擎内绝不调用AI/LLM（纯确定性）
  - 不使用随机数（除非混沌神王明确需要，且固定seed）
  - judge()不超过50行
  - 不在引擎内做I/O（数据通过参数传入）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Demo核心价值 — "冷酷确定性"。需要极严谨逻辑设计+完整测试。
  - **Skills**: []

  **Parallelization**: Wave 1 | Blocks: T7,T9 | Blocked By: T1,T2

  **References**:
  - 蓝图模块C逻辑流程（读取世界→物理校验→神王干涉→输出JSON）
  - 蓝图物理校验: `if player.strength < lock.hardness: result = "fail"`
  - 蓝图神王干涉: "未来支点 → forced_fail + penalty"
  - T2的 `JudgmentResult` 模型 + 世界数据YAML

  **Acceptance Criteria**:
  - [ ] `judge()` 对相同输入100次返回完全相同输出
  - [ ] 物理校验: strength<hardness→fail, strength>hardness→success
  - [ ] 神王干涉: 未来支点对象 → forced_fail + penalty
  - [ ] 覆盖率 ≥ 95%
  - [ ] `mutmut run --paths-to-mutate=app/engine/` 分数 ≥ 80%
  - [ ] `radon cc app/engine/ -n B` 所有函数 ≥ B级
  - [ ] Gherkin ≥ 5个场景
  - [ ] mypy strict 零错误

  **QA Scenarios**:
  ```
  Scenario: 确定性验证（核心特性）
    Tool: Bash
    Steps:
      1. python -c "
         from app.engine.rules_engine import RulesEngine
         engine = RulesEngine()
         intent = ParsedIntent(action_type='brute_force', target='ancient_lock', intensity='maximum', risk_acceptance=True)
         player = PlayerState(energy=100, health=100, strength=10, ...)
         results = [engine.judge(intent, player) for _ in range(100)]
         assert all(r.model_dump_json() == results[0].model_dump_json() for r in results)
         print('100次结果完全一致')
         "
    Expected Result: 100次完全相同
    Evidence: .sisyphus/evidence/task-4-determinism.txt

  Scenario: 物理校验+神王干涉+变异测试+Gherkin
    Tool: Bash
    Steps:
      1. pytest tests/unit/test_engine.py -v --cov=app.engine --cov-fail-under=95
      2. behave tests/features/engine.feature
      3. mutmut run --paths-to-mutate=app/engine/
    Expected Result: 全部通过，mutmut分数≥80%
    Evidence: .sisyphus/evidence/task-4-full-tests.txt
  ```

  **Commit**: YES - `feat(engine): deterministic rules engine + god intervention + 6-layer tests`

---

### Wave 2: Core Modules (4 parallel tasks)

- [x] 5. SQLite 运行时状态管理

  **What to do**:
  - 创建 `backend/app/state/database.py`: SQLite + SQLAlchemy异步
    - `aiosqlite` 异步驱动
    - `PlayerStateModel` ORM模型
    - `class StateRepository`: get_state / update_state / reset_state
  - 创建 `backend/app/state/migrations.py`: 初始化脚本 (CREATE TABLE IF NOT EXISTS + 默认数据)
  - 单元测试 `tests/unit/test_state.py`

  **Must NOT do**:
  - 不做复杂迁移系统
  - 不做多表关联（单表存玩家状态）
  - 不存世界数据到SQLite（世界数据是YAML）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**: Wave 2 | Blocks: T7 | Blocked By: T2

  **References**:
  - T2的 `PlayerState` 模型 + `data/default_player.json`
  - SQLAlchemy异步: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
  - aiosqlite: https://github.com/omnilib/aiosqlite

  **Acceptance Criteria**:
  - [ ] get/update/reset 三方法工作正确
  - [ ] reset恢复到default_player.json值
  - [ ] 单元测试覆盖率 ≥ 70%
  - [ ] mypy strict 零错误

  **QA Scenarios**:
  ```
  Scenario: 状态CRUD
    Tool: Bash
    Steps:
      1. pytest tests/unit/test_state.py -v
    Expected Result: 初始化→更新→读取→重置 全部正确
    Evidence: .sisyphus/evidence/task-5-state-tests.txt
  ```

  **Commit**: YES - `feat(state): SQLite runtime state management`

---

- [x] 6. AI 服务层（意图解析器 + 叙事渲染器 — prompt风格统一）

  **What to do**:
  - **意图解析器** (`backend/app/ai/parser.py`):
    - `class IntentParser`: 接收玩家文本，调用LLM，返回 `ParsedIntent`
    - `async def parse(player_input, context) -> ParsedIntent`
    - JSON mode / structured output（参考T0预研结果选择策略）
    - 非JSON fallback: Pydantic校验失败 → action_type="unknown"
    - action_type白名单: brute_force/stealth/read_memory/negotiate/probe/god_provoke/investigate
  - **叙事渲染器** (`backend/app/ai/renderer.py`):
    - `class NarrativeRenderer`: 接收JudgmentResult，调用LLM，返回叙事文本
    - `async def render(result, intent, context) -> str`
    - 返回完整文本（非流式）
    - 根据result分支(success/fail/forced_fail)不同语气
    - 神王干涉特殊处理："低语"/"超自然"元素
    - 不超过500字/次
  - **Prompt模板** (`backend/app/ai/prompts/`):
    - `parser_prompt.py`: action_type白名单 + 输出格式 + few-shot(≥3个"人话→JSON")
    - `renderer_prompt.py`: "回声系统终端播报员，客观但略带悲悯" + 赛博朋克style + [SYSTEM][WARN][EVENT]格式
  - **应急降级方案** (`backend/app/ai/fallback_renderer.py`):
    - 如果Day3规则引擎跑通但AI渲染不稳定，启用模板字符串渲染
    - `"系统判定：{result}，原因：{reason}"`
    - 这是保底策略，确保Demo可演示
  - 单元测试 `tests/unit/test_parser.py` + `tests/unit/test_renderer.py`: Mock LLM

  **Must NOT do**:
  - 不调用真实LLM API（测试全mock）
  - action_type白名单不可运行时动态添加
  - 渲染器不修改JudgmentResult（只读）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Prompt工程+JSON校验+fallback+渲染prompt调优，需要深度专注
  - **Skills**: []

  **Parallelization**: Wave 2 | Blocks: T7 | Blocked By: T2,T3,T0

  **References**:
  - 蓝图模块B（意图解析器）+ 模块D（叙事渲染器）完整描述
  - 蓝图中prompt秘密（style/tone/格式标签）
  - T0的 `provider_capabilities.md`（JSON mode策略）
  - T2的 `ParsedIntent` / `JudgmentResult` 模型
  - T3的 `LLMProvider` 接口

  **Acceptance Criteria**:
  - [ ] 解析器处理3+种同义表述→同一意图（"砸门"/"暴力破门"/"撞开"→brute_force）
  - [ ] 非法JSON/action_type/target → fallback intent
  - [ ] 渲染器prompt按result类型分支（success/fail/forced_fail）
  - [ ] 神王干涉渲染包含"低语"/"超自然"引导
  - [ ] 输出包含[SYSTEM][WARN][EVENT]标签
  - [ ] fallback_renderer.py存在且可替代
  - [ ] 单元测试覆盖率 ≥ 70%（mock LLM）
  - [ ] mypy strict 零错误

  **QA Scenarios**:
  ```
  Scenario: 解析器正常+fallback+白名单
    Tool: Bash
    Steps:
      1. pytest tests/unit/test_parser.py -v
      2. 验证: 正常解析+非法JSON fallback+非法action_type fallback
    Expected Result: 所有场景正确处理
    Evidence: .sisyphus/evidence/task-6-parser-tests.txt

  Scenario: 渲染器分支渲染
    Tool: Bash
    Steps:
      1. pytest tests/unit/test_renderer.py -v
      2. 验证: success/fail/forced_fail各有对应prompt
    Expected Result: 三种分支prompt正确构建
    Evidence: .sisyphus/evidence/task-6-renderer-tests.txt
  ```

  **Commit**: YES - `feat(ai): intent parser + narrative renderer + fallback`

---

- [x] 7. FastAPI 端点 + 交互循环编排（核心整合）

  **What to do**:
  - 创建 `backend/app/main.py`: FastAPI应用入口
    - CORS + 路由注册 + 启动时加载世界数据+初始化Provider
  - 创建 `backend/app/api/routes.py`: API端点
    - `POST /api/action`: 主交互端点（编排完整循环: parse→judge→render→update_state）
    - `GET /api/state`: 获取玩家状态
    - `POST /api/reset`: 重置状态
    - `GET /api/health`: 健康检查(provider状态)
  - 创建 `backend/app/api/deps.py`: 依赖注入（Provider/Engine/StateRepository单例）
  - 创建 `backend/app/orchestrator.py`: 交互循环编排器
    - `async def process_action(input, state) -> ActionResponse`
    - 串联: parse → judge → render → update_state
    - 错误处理: 任一步骤失败 → 返回"系统不稳定"叙事（不500）
  - **定义后立即写前端共享类型** `frontend/src/types/api.ts`（手动复制，防止契约不匹配）
  - 单元测试 `tests/unit/test_api.py` + `tests/features/api_flow.feature`

  **Must NOT do**:
  - 不在API层写业务逻辑（仅编排）
  - 端点函数≤20行
  - 不暴露内部JudgmentResult原始结构

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 所有模块整合点 — 编排+错误处理+依赖注入
  - **Skills**: []

  **Parallelization**: Wave 2 | Blocks: T9 | Blocked By: T4,T5,T6

  **References**:
  - T2 API模型 + T3 Provider + T4 RulesEngine + T5 StateRepository + T6 Parser/Renderer
  - FastAPI依赖注入: https://fastapi.tiangolo.com/tutorial/dependencies/
  - 蓝图"核心交互循环"（3-5秒内完成）

  **Acceptance Criteria**:
  - [ ] `POST /api/action` 完整跑通解析→判决→渲染循环
  - [ ] `GET /api/health` 返回200 + provider状态
  - [ ] `POST /api/reset` 重置状态
  - [ ] LLM失败时优雅降级（不500）
  - [ ] `frontend/src/types/api.ts` 与后端模型一致
  - [ ] 单元测试覆盖率 ≥ 80%
  - [ ] Gherkin feature覆盖关键流程
  - [ ] mypy strict 零错误

  **QA Scenarios**:
  ```
  Scenario: 完整交互循环
    Tool: Bash (curl + mock LLM)
    Steps:
      1. 启动后端(mock provider)
      2. curl -X POST http://localhost:8000/api/action -d '{"player_input":"我强行砸开这个锁"}'
      3. 验证响应含 judgment + narrative + updated_state
    Expected Result: 200 + 完整ActionResponse
    Evidence: .sisyphus/evidence/task-7-api-action.json

  Scenario: LLM失败优雅降级
    Tool: Bash
    Steps:
      1. 配置无效API key
      2. curl POST /api/action
    Expected Result: 200 + "系统不稳定"叙事，不500
    Evidence: .sisyphus/evidence/task-7-api-fallback.json
  ```

  **Commit**: YES - `feat(api): FastAPI endpoints + interaction loop + shared types`

---

- [x] 8. 前端终端完整版（Terminal + Typewriter + StatusPanel + GodWatch）

  **What to do**:
  - **TypewriterText组件** (`components/TypewriterText.tsx`):
    - 逐字显示，speed可配置，闪烁光标█，支持中断
  - **Terminal组件** (`components/Terminal.tsx`):
    - 输出历史区(滚动) + 输入框 + 状态栏
    - TerminalLine: player/system/narrative/error着色
    - 输入回车提交，提交时禁用
  - **StatusPanel组件** (`components/StatusPanel.tsx`):
    - energy/health/mental_stability (progress bar + 动画过渡)
    - 当前位置 + echo_mode状态
    - 数值减少时红色闪烁
  - **GodWatchIndicator** (`components/GodWatchIndicator.tsx`):
    - 注视等级0-3
    - 等级>0时终端边缘红光 + 噪点增强
    - **降级方案**: CSS动画性能差时用静态红色边框
  - **ResetButton** (`components/ResetButton.tsx`): 重置+清空历史
  - **Hooks**:
    - `useTypewriter.ts`: 打字机逻辑 + skip()
    - `useAction.ts`: API调用 + loading状态 + 错误处理
    - `useGameState.ts`: Context + useReducer 全局状态
  - **API客户端** (`api/client.ts`): fetch封装 + 类型安全 + 30秒超时
  - **CSS效果**: CRT扫描线 + text-shadow辉光 + [SYSTEM]=green/[WARN]=yellow/[EVENT]=cyan
  - Vitest测试: 仅测hooks逻辑（useTypewriter状态机），不测DOM渲染

  **Must NOT do**:
  - 不使用真流式
  - 不安装动画库
  - 不做移动端适配
  - 不安装Redux/Zustand（Context足够）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 终端视觉是Demo第一印象，需要精心打磨
  - **Skills**: []

  **Parallelization**: Wave 2 | Blocks: T9 | Blocked By: T1,T2

  **References**:
  - T1 tailwind主题 + T2 TS类型 + T7 api.ts
  - 蓝图模块A（输入框/状态区/渲染区/视觉细节）
  - 蓝图"神王注视时UI边缘闪烁红光"

  **Acceptance Criteria**:
  - [ ] TypewriterText逐字显示+可跳过
  - [ ] 输入提交后打字机播放narrative
  - [ ] CRT扫描线+文本辉光可见
  - [ ] [SYSTEM]/[WARN]/[EVENT]标签着色正确
  - [ ] 状态面板energy变化有动画
  - [ ] GodWatch红光效果可触发
  - [ ] reset按钮工作
  - [ ] vitest hooks测试通过
  - [ ] `tsc --noEmit` + `eslint` 零错误

  **QA Scenarios**:
  ```
  Scenario: 打字机+视觉风格
    Tool: Playwright
    Steps:
      1. 导航到 http://localhost:5173
      2. 输入test回车，等待响应
      3. 验证文本逐字出现+光标闪烁
      4. 点击跳过→立即完整显示
      5. 截图终端风格
    Expected Result: 打字机+CRT效果正常
    Evidence: .sisyphus/evidence/task-8-typewriter.png

  Scenario: 状态面板+神王注视
    Tool: Playwright
    Steps:
      1. 触发消耗energy的action→验证progress bar动画
      2. 触发god_intervention action→截图红光效果
    Expected Result: 状态更新+红光可见
    Evidence: .sisyphus/evidence/task-8-status-godwatch.png
  ```

  **Commit**: YES - `feat(frontend): terminal + typewriter + status panel + god watch`

---

### Wave 3: Integration (1 task)

- [x] 9. 前后端联调 + 神王干涉可视化 + E2E QA

  **What to do**:
  - **前后端联调**:
    - 确认 vite proxy 正确
    - 完整跑通: 输入→解析→判决→渲染→打字机→状态更新 全链路
    - 跨域/超时/错误边界处理
  - **神王干涉完整可视化**:
    - 后端JudgmentResult返回god_intervention详情
    - 前端: GodWatchIndicator升级 + 边缘强红光 + 噪点 + 打字时故障效果
    - 效果持续N秒后消退
  - **交互打磨**:
    - 输入提交→禁用+loading
    - 响应慢时显示 "> PROCESSING..."
    - 错误时红色 "> [ERROR] ..."
  - **E2E验证**: 5种action类型(brute_force/stealth/read_memory/negotiate/god_provoke)全跑通

  **Must NOT do**:
  - 不改API契约（回头改T7）
  - 不添加新功能（仅整合+打磨）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: []

  **Parallelization**: Wave 3 | Blocks: T10,F1-F4 | Blocked By: T7,T8

  **References**:
  - T7 API端点 + T8 前端完整版
  - 蓝图"AI输出涉及神王注视时UI边缘闪烁红光或出现噪点"

  **Acceptance Criteria**:
  - [ ] 完整交互链路无错误跑通
  - [ ] 5种action类型全部正确响应
  - [ ] 神王干涉: 红光+噪点+故障打字
  - [ ] 错误状态优雅显示
  - [ ] loading状态有视觉反馈

  **QA Scenarios**:
  ```
  Scenario: 完整playthrough（5种action）
    Tool: Playwright
    Steps:
      1. 启动后端+前端
      2. "我强行砸开这个锁" → brute_force判决
      3. "我悄悄绕过这扇门" → stealth
      4. "我用回响模式读取尸体记忆" → read_memory + 可能神王干涉
      5. "我试图和祭坛沟通" → negotiate/probe
      6. "我向神王挑衅" → god_provoke + 红光效果
    Expected Result: 5种action全部正确，可视化完整
    Evidence: .sisyphus/evidence/task-9-playthrough.mp4

  Scenario: 神王干涉效果+错误处理
    Tool: Playwright
    Steps:
      1. 触发god_provoke → 截图红光+噪点
      2. 停止后端 → 输入 → 验证红色[ERROR]文本不崩溃
    Expected Result: 红光效果+优雅错误
    Evidence: .sisyphus/evidence/task-9-intervention-error.png
  ```

  **Commit**: YES - `feat(integration): full stack + god intervention visualization`

---

### Wave 4: Content & Verification (1 task + FINAL)

- [x] 10. 内容调优 + 演示脚本 + 性能验证

  **What to do**:
  - **场景全覆盖**: 验证每个对象×action组合矩阵，确保判决分支正确
  - **神王规则验证**: 3-5条规则全部可触发且效果正确
  - **AI叙事质量调优**:
    - 调整renderer prompt确保风格一致
    - 测试不同Provider叙事质量差异
    - 确保叙事≤500字
  - **解析器鲁棒性**: 10+种暴力变体 + 无意义输入 + 超长输入
  - **性能验证**: 单次交互循环≤5秒
  - **演示脚本** (`data/demo_scripts.md`): 3-5个"最佳演示路径"

  **Must NOT do**:
  - 不添加新功能/新场景
  - 不改API契约

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**: Wave 4 | Blocks: F1-F4 | Blocked By: T9

  **References**:
  - T2世界数据 + T4规则引擎 + T6 AI服务 + 蓝图"Demo杀手锏"

  **Acceptance Criteria**:
  - [ ] 所有关键对象×action组合正确
  - [ ] 3-5条神王规则全部可触发
  - [ ] 10+种暴力变体正确识别
  - [ ] 无意义输入→优雅fallback
  - [ ] 单次交互≤5秒
  - [ ] demo_scripts.md含3-5个路径

  **QA Scenarios**:
  ```
  Scenario: 全场景对象矩阵+神王规则+解析器鲁棒性+性能
    Tool: Bash (curl批量)
    Steps:
      1. 每对象3+种action→记录判决
      2. 每神王触发action→验证
      3. 10+暴力变体→验证brute_force
      4. time curl × 5取平均
    Expected Result: 全矩阵正确，性能达标
    Evidence: .sisyphus/evidence/task-10-matrix-robustness-perf.json
  ```

  **Commit**: YES - `test(qa): E2E scenarios + content tuning + demo scripts`

## Final Verification Wave (MANDATORY)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  逐条验证 "Must Have" 全部实现（读文件/curl/run命令）。搜索 "Must NOT Have" 禁止模式（reject with file:line）。检查evidence文件存在于 `.sisyphus/evidence/`。对比deliverables与plan。
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Full Test Suite + Code Quality** — `unspecified-high`
  运行 `verify.ps1` 完整6层管道。检查所有文件：`as any`/`# type: ignore`/空catch/console.log。报告：Coverage%/Mutation%/Lint/Type errors。
  Output: `Build [PASS/FAIL] | Tests [N/N] | Coverage [%] | Mutation [%] | VERDICT`

- [x] F3. **Real Manual QA — Full Playthrough** — `unspecified-high` (+ `playwright` skill)
  从clean state启动。Playwright完整5+种action测试（brute_force/stealth/read_memory/negotiate/god_provoke）。验证Provider切换（改.env重启）。验证神王干涉红光效果。截图存 `.sisyphus/evidence/final-qa/`。
  Output: `Scenarios [N/N] | Provider Switch [PASS/FAIL] | Edge Cases [N] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  每个任务spec vs实际diff 1:1对比。检查文件≤400行/CC≤10/无循环依赖。运行 `radon cc app/ -n B` + `pydeps --cycle`。检测跨任务文件污染。
  Output: `Tasks [N/N] | CC Violations [N] | Circular Deps [N] | VERDICT`

---

## Commit Strategy
- **Wave 1**: `feat(foundation): scaffold + models + world data + provider + rules engine`
- **Wave 2**: `feat(core): AI services + API + state + frontend terminal`
- **Wave 3**: `feat(integration): full stack integration + god intervention`
- **Wave 4**: `test(verification): E2E QA + content tuning + full test suite`

---

## Success Criteria

### Verification Commands
```bash
# 一键验证（6层串联）
cd backend && ./scripts/verify.ps1

# Backend单独
cd backend && uvicorn app.main:app --reload
cd backend && pytest --cov=app --cov-report=term --cov-fail-under=85
cd backend && mutmut run --paths-to-mutate=app/engine/
cd backend && ruff check . && mypy app/ && radon cc app/ -n B

# Frontend
cd frontend && npm run build && npm run lint

# Integration
curl -X POST http://localhost:8000/api/action \
  -H "Content-Type: application/json" \
  -d '{"player_input":"我强行砸开这个锁"}'
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] `verify.ps1` 全部6层通过
- [ ] 4-Agent pipeline 每个任务都执行
- [ ] 覆盖率：规则引擎≥95%，整体≥85%
- [ ] 变异分数：规则引擎≥80%
- [ ] 圈复杂度：所有函数≤10（radon ≥ B级）
- [ ] 模块大小：所有源文件≤400行
- [ ] 无循环依赖
- [ ] LLM Provider切换仅需改.env
