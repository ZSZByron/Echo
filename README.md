# Echo UGC — AI 世界观工坊（A1）

> **一句话**：用户带入自己的世界观（上传文档 / 一句话灵感）→ AI 引导访谈补全 → 定稿编译为知识图谱 → 产出 IP 展板与视觉背景。
>
> **进度真相源**：[PROJECT_STATE.md](PROJECT_STATE.md)（每次会话更新）。本 README 只描述稳定事实，不追踪进度——想知道"今天做到哪了"看 PROJECT_STATE，想知道"项目是什么、怎么跑"看本页。

---

## 项目概述

Echo UGC 的当前主线是 **A1 世界观工坊**（前端路由 `/a1`）：帮助创作者把手里的世界观设定变成**结构化、可视化、可检索**的知识图谱，并一键产出 IP 展板与场景视觉背景。

### A1 主线流程

```
入口（三选一）
├─ 种子选择（内置 TRPG 预设）
├─ 文档上传（.txt → 自动解析 35 字段预填，逐字保真，无依据字段诚实留空）
└─ 一句话开始
        ↓
引导式访谈 —— LLM 10 模块追问 + 自动填空（fills），锚定用户关键词跨字段深化
        ↓
定稿 finalize —— 门禁契约：模块未完成 409 拒绝（missing_sections）
        ↓
graphify —— 一次 LLM 调用，把全部自然语言答案编译为 SIR 五字段结构化中间表示
        ↓
确定性编译 —— 双树（背景树+深度树）+ 派生边 + 约束节点（纯代码装配，不经过 LLM）
        ↓
产出 —— 知识图谱页（tier 分组/搜索/节点详情）· IP 展板 · 视觉背景预生成
```

### 三条设计铁律（v0.5 统一模型）

1. **数据形态单生产单消费**：自然语言（NL，访谈产出）→ 结构化中间表示（SIR，graphify 产出）→ 知识图谱（KG，确定性编译产出）。每种形态只有一个生产方、一个消费方，访谈对话永不携带机器格式。
2. **图谱装配确定性**：LLM 只在 graphify 单点产出结构（SIR），图谱（KG）由确定性代码装配——同输入可复现，杜绝幻觉直写图谱。
3. **诚实与可观测**：答案真值闸（占位词不污染数据）、warning ledger（截断/丢失全披露落库）、预算护栏（答案/prompt/convert 三级限额+留痕）。

**权威文档**：[docs/SYSTEM_DESIGN_SPEC_v6.md](docs/SYSTEM_DESIGN_SPEC_v6.md)（模块化架构规范正文，D14）+ [docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md](docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md) 及其加固补丁 [2-A1-v0.5.1-管线缺陷级联与修复接头J1-J4](docs/governance/2-A1-v0.5.1-管线缺陷级联与修复接头J1-J4.md)（管线契约经 v6 §0.2 继承声明继续有效）。

---

## 技术栈

### 后端
- **框架**: FastAPI + Python 3.11+ + Pydantic v2
- **AI 服务**: 多 LLM Provider 抽象（OpenAI / Anthropic / DeepSeek / Qwen / Kimi / GLM），chat_json 健壮解析 + 400 降级重试链 + thinking 防护
- **A1 领域层**: 引导访谈（guide_engine）/ 文档解析（worldview_upload）/ 图谱编译（graphify）/ 会话存储（store）/ 警告账本（warning_ledger）/ 问卷树（a1_question_tree）
- **数据库**: SQLite（aiosqlite + SQLAlchemy）
- **图像生成**: ImageGenerator（zhipu / wanxiang / qwen / local 四 provider）
- **测试**: pytest + pytest-cov（1000+ 测试基线）

### 前端
- **框架**: Vite + React 19 + TypeScript
- **样式**: TailwindCSS v4 + 自定义赛博朋克 CRT 效果
- **图可视化**: React Flow（A1 知识图谱层级带状布局）
- **测试**: Vitest + Playwright（E2E）

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
python -m venv .venv
.venv\Scripts\activate
pip install -e .
deactivate
```

复制 `.env.example` 到 `.env`，填入 LLM Provider API 密钥：

```env
ACTIVE_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-key-here
```

支持的 Provider：
| Provider | 配置键 | 默认模型 |
|----------|--------|---------|
| `openai` | `OPENAI_API_KEY` | gpt-4o-mini |
| `anthropic` | `ANTHROPIC_API_KEY` | claude-3-5-sonnet |
| `deepseek` | `DEEPSEEK_API_KEY` | deepseek-v4-flash |
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

> ⚠️ **已知问题（断点 J，未修复）**: `start.ps1` 硬编码 Anaconda 环境路径 `F:\Anaconda\envs\Deepcode\python.exe`。如果 Python 安装位置不同，请修改脚本或使用手动启动。

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

| 路由 | 页面 | 状态 |
|------|------|------|
| `http://localhost:5173/a1` | **A1 世界观工坊（主线入口）** | ✅ 现行主力 |
| `http://localhost:5173/a1/poster` | IP 展板 | ✅ 现行 |
| `http://localhost:5173/` | 交互终端（赛博朋克 Demo） | ✅ 可用（早期 Demo） |
| `http://localhost:5173/graph/editor` | 知识图谱编辑器（React Flow） | ⚙️ 遗留可用 |
| `http://localhost:5173/admin/graph-assets` | 图谱资产生成 | ⚙️ 遗留（部分 Mock） |
| `http://localhost:5173/admin/assets` | 资产审核 | ⚙️ 遗留可用 |

后端 API 文档：`http://localhost:8000/docs`

---

## 当前可用功能

### ✅ A1 世界观工坊（主线，全流程可用）

- **种子选择**：内置 TRPG 预设三件套（模板种子目录 / 预设目录 / 规则书引用）
- **文档上传**：`.txt` 世界观文档 → 自动解析 35 字段预填；逐字保真；缺少依据的字段诚实留空不编造；超长文档截断落账可查
- **引导式访谈**：LLM 逐模块追问（10 模块），fills 自动填空，跑题优雅归档，发散引导跨字段深化
- **定稿门禁**：模块完成度真值化计数（占位答案不计入），未达标 409 + missing_sections
- **知识图谱**：双树结构（背景树=问卷投影 / 深度树=LLM 生成条目）+ 派生边 + 约束节点；tier 七层分组；节点详情面板；搜索；confirmed 边审核（确认/拒绝）；重定稿版本化（stale 标记）
- **IP 展板**：定稿内容一键生成角色/世界观展板视图
- **视觉背景**：场景背景预生成（ImageGenerator）
- **可观测性**：warning ledger 五源披露（upload/convert/graphify/answers/直注），前端图谱页角标展示

### ✅ 交互终端（早期 Demo）

- 自然语言输入 → AI 解析意图 → 规则判决 → 叙事渲染 → 打字机输出
- 状态面板（生命值/力量/物品栏）、神王干涉红光、场景视图

### ⚙️ 遗留功能（六维管线时代产物）

- 图谱编辑器 / 资产生成 / 资产审核页面（仍可访问，与 A1 主线无依赖关系）

> 六维死线代码（seed 五维引擎、6 维约束生成及其孤儿依赖）已于 2026-09-13 批次三删除（备份标签 `backup-20260913-fin` 可恢复）；`prompt_builder` / `prompt_fusion` / `application_tree` 等因仍被活路由与 A1 复用链（constraint_topology）引用而保留。

---

## API 端点总览

### A1 世界观工坊（主线）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/a1/seeds` | 种子预设列表 |
| POST | `/api/a1/session/start` | 开始会话 |
| POST | `/api/a1/chat` | 访谈对话（追问+fills） |
| POST | `/api/a1/chat/confirm` | 确认 fills 写入 |
| POST | `/api/a1/upload` | 上传世界观文档并解析预填 |
| POST | `/api/a1/upload/convert` | 文档格式转换（限额+留痕） |
| GET | `/api/a1/file/{file_id}` | 会话文件状态（含 warning ledger） |
| POST | `/api/a1/file/{file_id}/finalize` | 定稿（门禁：未完成 409） |
| GET | `/api/a1/file/{file_id}/graph` | 定稿知识图谱 |
| GET | `/api/a1/file/{file_id}/poster` | IP 展板数据 |
| POST | `/api/a1/file/{file_id}/poster/generate` | 生成展板视觉 |
| POST | `/api/a1/file/{file_id}/visual-bg/pregenerate` | 视觉背景预生成 |
| POST | `/api/a1/file/{file_id}/edge/{key}/confirm` | 确认概念边 |
| POST | `/api/a1/file/{file_id}/edge/{key}/reject` | 拒绝概念边 |
| POST | `/api/a1/file/{file_id}/terms/confirm` | 术语确认（多格式节点） |

### 交互终端

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/action` | 处理玩家自然语言指令 |
| GET | `/api/scene` | 获取场景数据（含已审批资产） |
| GET | `/api/state` | 获取玩家状态 |
| POST | `/api/reset` | 重置玩家状态 |
| GET | `/api/health` | 健康检查 |

### 知识图谱（遗留编辑器线）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/graph/extract` | LLM 从文本提取图谱 |
| POST | `/api/graph/validate` | 环检测验证 |
| POST | `/api/graph/save` | 保存图谱到数据库 |
| GET/DELETE | `/api/graph/{scene_id}` | 加载/删除图谱 |
| POST | `/api/graph/generate` | 触发 Wave 串行生成 |
| GET | `/api/graphs` | 图谱列表 |

### 资产管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/assets/{id}/generate` | 触发资产生成 |
| PUT | `/api/assets/{id}/approve` | 审批资产 |
| PUT | `/api/assets/{id}/reject` | 拒绝资产 |
| PUT | `/api/assets/{id}/prompt` | 更新提示词 |

### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/register` | 用户注册（MockUserStore，平台线胚胎，未接线） |

---

## 测试与质量

```bash
# 后端
cd backend
pytest                    # 全量（1000+ 基线）
pytest --cov=app          # 带覆盖率
.\scripts\verify.ps1      # 一键验证

# 前端
cd frontend
npm run build             # 构建
npx vitest                # 单元测试
npx playwright test       # E2E
```

- 后端 1000+ 测试全绿为合入基线；A1 线含契约测试（C1-C5）与极限病理测试（xt 系列）
- 前端 Vitest 单测 + Playwright E2E

---

## 文档导航

| 文档 | 地位 |
|------|------|
| **[docs/HUB.md](docs/HUB.md)** | **总目录·唯一入口**（五大类索引——进度/决策/架构/治理/证据；嫌文档散就只看这页） |
| [PROJECT_STATE.md](PROJECT_STATE.md) | **进度真相源**（唯一，每次会话更新） |
| `docs/decision-log.md` | 决策台账（D/B/P 编号唯一源，翻案须升版本号；最新 D21 综合立项 2026-09-27 + D20 补记） |
| `docs/SYSTEM_DESIGN_SPEC_v6.md` | 现行系统设计规范正文（模块化架构，2026-09-22；v6.1 增补 2026-09-27，D20/D21） |
| `docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md` | A1 权威概念模型（管线契约经 v6 §0.2 继续有效） |
| `docs/governance/2-A1-v0.5.1-管线缺陷级联与修复接头J1-J4.md` | A1 加固记录（最新治理版） |
| `docs/governance/0_index-v0.7.md` | 治理体系索引（最新版） |
| `docs/README.md` | 文档中心 MOC（导航入口） |

> 版本规则：v1–v5.1 规格书为历史版本（v1-v4 六维管线时代；v5/v5.1 阶段契约时代，2026-09-26 归档），现行规范 = **v6**（模块化架构，2026-09-22 起）。治理类文档一律"新版本顺延号新建文件，不修改原版"，参考时以最新版为准；过期版本移入对应 `archive/` 目录（规格书 → `docs/archive/`，治理文档 → `docs/governance/archive/`）。

---

## 历史注脚：六维管线时代（2026-07 底 ~ 08 月初）

本项目第一代架构是**六维约束驱动管线**：6 维约束（RED/LAW/ACT/NAR/WST/SOC）× 6 生成维度 × 6×6 权重矩阵 → 知识图谱拆分 → 多维标签合成 Prompt → 资产概念图。设计文档：

- `docs/plans/2026-08-03-layered-constraint-architecture.md`（分层约束架构，六维核心设计）
- `docs/archive/SYSTEM_DESIGN_SPEC_v1~v4.md`（历史规格书，已归档；同目录另存一份根目录早期变体，2026-08-04）
- 断点 A-J 路线图（原记录于本 README，现已判定：10 个断点中 8 个实质死亡）

**现状**：该管线的 seed / constraints 两条路由前端零调用，属遗留死线；A1 主线复用了其中的四件资产——LLM Provider 层、ImageGenerator、dimension 数据模型、constraint_topology。六维时代的完整设计见上述历史文档，此处不再展开。

---

## 部署（容器化，2026-09-13 批次四修复并实测）

```powershell
# 1. 准备环境文件（gitignored，不入库）
Copy-Item .env.example.production .env.production   # 填入真实 LLM key

# 2. 一键部署（构建镜像 + 起栈 + 健康检查）
.\deploy.ps1 -Environment production -SkipTests

# 或直接 compose
docker compose -f docker-compose.production.yml --env-file .env.production up -d --build
```

- **backend**：`python:3.11-slim`（uvicorn :8000；健康检查 `/api/health`；数据卷 `./data:/data`）
- **frontend**：`node:24` 构建 → `nginx:alpine`（:80；同源反代 `/api/`，SPA fallback）
- 端口可用 `WEB_PORT` / `API_PORT` 覆盖（.env.production）
- 已实测全链路：静态页 ✅ / 反代健康 ✅ / A1 端点（`/api/a1/seeds`）✅
- 已知边界：用户体系未建（`JWT_SECRET` 为占位）；前端测试套件有存量失败（部署时 `-SkipTests` 或先修）；前端镜像用 `npm install` 而非 `npm ci`（Windows 生成的锁缺 Linux 平台变体，见 PROJECT_STATE 技术债记录）

本地开发（start.ps1 / 手动启动）不受影响。

---

## 许可

MIT License
