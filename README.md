# 回声·AI交互式规则终端 Demo

## 项目概述

回声（Echo）是一个"AI交互 + 规则判定"新形态的Demo系统。玩家输入自然语言指令，AI解析为结构化意图，Python规则引擎进行确定性判决，AI渲染为赛博朋克风格叙事，前端终端以打字机效果输出。

核心展示"AI创造性 + 代码确定性"的结合：无论玩家如何输入，底层规则引擎都能保持逻辑一致性，然后让AI去解释这个残酷结果。

## 技术栈

### 后端
- **框架**: FastAPI
- **规则引擎**: 纯Python确定性规则
- **AI服务**: 多LLM Provider抽象（支持OpenAI/Anthropic/DeepSeek/Qwen/Kimi/GLM）
- **数据库**: SQLite (aiosqlite + SQLAlchemy)
- **测试**: pytest + pytest-cov + pytest-behave + mutmut

### 前端
- **框架**: Vite + React + TypeScript
- **样式**: TailwindCSS v4 + 自定义赛博朋克CRT效果
- **特性**: 打字机效果、状态面板、神王干涉红光可视化

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- Windows PowerShell 5.1+ 或 PowerShell 7+

### 1. 环境配置

#### 后端配置

```bash
cd backend

# 1. 创建虚拟环境（必须，启动脚本依赖 backend\.venv）
python -m venv .venv

# 2. 激活虚拟环境并安装依赖
.venv\Scripts\activate
pip install -e .

# 3. 退出虚拟环境（依赖已装好，启动脚本会自动使用 .venv）
deactivate
```

复制 `.env.example` 到 `.env`：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的LLM Provider API密钥：

```env
ACTIVE_PROVIDER=openai  # 选择你的provider
OPENAI_API_KEY=sk-your-openai-key-here
```

支持的Provider：
- `openai` - OpenAI (GPT-4o-mini)
- `anthropic` - Anthropic (Claude 3.5 Sonnet)
- `deepseek` - DeepSeek (deepseek-chat)
- `qwen` - Qwen/DashScope (qwen-plus)
- `kimi` - Kimi/Moonshot (moonshot-v1-8k)
- `glm` - GLM/Zhipu (glm-4)

#### 前端配置

```bash
cd frontend
npm install
```

### 2. 启动服务

#### 方法一：使用一键启动脚本（推荐）

```bash
# 在项目根目录运行
.\start.ps1
```

这将同时启动后端（端口8000）和前端（端口5173）。

#### 方法二：手动启动

**启动后端**：

```bash
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**启动前端**（新终端窗口）：

```bash
cd frontend
npm run dev
```

### 3. 访问应用

打开浏览器访问: `http://localhost:5173`

## 使用示例

在终端中输入自然语言指令：

```
我强行砸开这个锁
我悄悄潜入神殿内部
我尝试与守护神对话
```

系统会：
1. AI解析你的意图（动作类型、目标、强度、风险接受度）
2. 规则引擎根据物理规则和神王法则进行判决
3. AI渲染赛博朋克风格的叙事文本
4. 终端以打字机效果输出结果

## 项目结构

```
UGC/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI应用入口
│   │   ├── models/           # Pydantic数据模型
│   │   ├── engine/           # 规则引擎
│   │   ├── services/         # AI服务层
│   │   └── api/              # API路由
│   ├── tests/                # 测试套件
│   ├── .env.example          # 环境变量模板
│   └── pyproject.toml        # Python配置
├── frontend/
│   ├── src/
│   │   ├── components/       # React组件
│   │   ├── types/            # TypeScript类型定义
│   │   └── index.css         # 全局样式（CRT效果）
│   ├── tailwind.config.js    # Tailwind配置
│   ├── vite.config.ts        # Vite配置
│   └── package.json          # 依赖配置
├── start.ps1                 # 一键启动脚本
└── README.md                 # 本文件
```

## 测试

### 后端测试

```bash
cd backend
pytest                          # 运行所有测试
pytest --cov=app               # 带覆盖率测试
behave                          # Gherkin BDD测试
mutmut run                      # 变异测试（仅规则引擎）
```

### 前端测试

```bash
cd frontend
npm run build                   # 构建测试
```

## 质量门禁

项目配置了6层测试体系：

| 层级 | 工具 | 目标 |
|------|------|------|
| 单元测试 | pytest | 全模块覆盖 |
| Gherkin BDD | pytest-behave | 关键流程 |
| 覆盖率 | pytest-cov | 总体≥85%，规则引擎≥95% |
| 代码质量 | ruff + mypy | 类型检查+风格 |
| 变异测试 | mutmut | 规则引擎≥80% |
| QA场景 | Playwright | 端到端测试 |

运行一键验证：

```bash
cd backend
.\scripts\verify.ps1
```

## 故障排除

### 后端启动失败

1. 检查Python版本：`python --version`（需要3.11+）
2. 确认虚拟环境已创建且依赖已安装：`backend\.venv\Scripts\python -m pip install -e .`
3. 检查.env配置：确保API密钥正确

### 前端启动失败

1. 检查Node版本：`node --version`（需要18+）
2. 删除node_modules重新安装：`rm -rf node_modules && npm install`
3. 检查端口占用：`netstat -ano | findstr :5173`

### API调用失败

1. 检查后端是否运行：`http://localhost:8000/docs`
2. 检查CORS配置
3. 检查.env中的ACTIVE_PROVIDER和API密钥

## 开发指南

### 添加新的规则

编辑 `backend/app/engine/rules.py`，遵循确定性原则：

```python
def judge_action(intent: ParsedIntent, state: PlayerState) -> JudgmentResult:
    # 确定性逻辑：相同输入100%相同输出
    if intent.action_type == ActionType.BRUTE_FORCE:
        required_strength = calculate_required_strength(intent.target)
        if state.strength >= required_strength:
            return success_result(...)
    return fail_result(...)
```

### 添加新的LLM Provider

1. 在 `backend/app/services/providers/` 创建新的Adapter
2. 在 `.env.example` 添加配置模板
3. 在ProviderFactory注册新provider

### 自定义UI主题

编辑 `frontend/tailwind.config.js` 和 `frontend/src/index.css` 修改赛博朋克主题。

## 许可

MIT License

## 联系

如有问题，请提交issue或联系开发团队。
