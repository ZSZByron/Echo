# Echo UGC — 系统设计规范 v5.1 (System Design Specification)

> **文档定位**: v5.0 增量补丁 — A1问题树两层重构接口注册 + confirm契约修正 + 工程治理新规
> **版本**: v5.1 — 修复"A1启动崩溃/黑屏"缺陷时引入的接口变更统一注册
> **日期**: 2026-08-24
> **与v5关系**: v5.0 为完整规范（A模块公用底座+A1工作台），本文件仅注册 v5.0 之后的**增量变更**。未在本文注册的接口以 v5.0 为准。

---

## 更新日志

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v5.1 | 2026-08-24 | ① A1问题树从10板块扁平结构（Section API）重构为10模块×子字段两层结构（Module/SubField API），全量接口注册 ② `/api/a1/chat/confirm` 响应契约对齐 chat（补 reply/next_question）③ 前端 classification_proposal 契约修正（对象类型+confirm必带proposal）④ 新增工程治理铁律：FastAPI依赖函数禁止TYPE_CHECKING注解 |
| v5.1 (R5) | 2026-08-24 | **A1访谈交互范式重构**：废弃规则词典编译器主导的模板式访谈，改为 LLM 引导式访谈（Interviewer契约）。自由输入由LLM理解后填入结构化文件（支持一次填多字段）；仅LLM判定超出十大模块体系的内容才进入创新确认。 |

---

## 目录

1. [R1: A1两层问题树接口（重构注册）](#1-r1-a1两层问题树接口重构注册)
2. [R2: /api/a1/chat/confirm 响应契约（修正）](#2-r2-apia1chatconfirm-响应契约修正)
3. [R3: 前端 classification_proposal 契约（修正）](#3-r3-前端-classification_proposal-契约修正)
4. [R4: 工程治理新规（TYPE_CHECKING禁令）](#4-r4-工程治理新规type_checking禁令)
5. [R5: A1 LLM访谈器契约（交互范式重构）](#5-r5-a1-llm访谈器契约交互范式重构)
6. [验证基线](#6-验证基线)

---

## 1. R1: A1两层问题树接口（重构注册）

> **状态**: ✅ 已实现（`backend/app/domains/creation/seed/a1_question_tree.py`）
> **替代**: v5.0 时代的 Section API（first_section/get_section/next_section/section_ids/SECTIONS）**已废弃删除**，消费方已全部迁移。

### 1.1 数据结构

**文件路径**: `backend/app/domains/creation/seed/a1_question_tree.py`

**核心签名**:
```python
class SubField(TypedDict):
    id: str        # 英文稳定slug，如 "name" / "acquire"
    label: str     # 中文显示名，如 "名称与概念" / "获取方式"
    question: str  # 访谈问题
    hint: str      # 提示

class Module(TypedDict):
    id: str                  # 中文模块id（封闭枚举，见1.3）
    label: str               # 中文显示名
    fields: list[SubField]   # 注意：键名是 fields（非 subs）

MODULES: list[Module]  # 权威数据源，按顺序遍历
```

**答案键格式（铁律）**: `"{module_id}.{subfield_id}"`，点号分隔。例：`"IP定位.name"`、`"力量体系.acquire"`。
> 旧格式 `"模块::子项"`（双冒号）已废弃。`_build_dimension_result_set` 解析 `tag=value` 片段时兼容 `LAW.world_structure` 前缀剥离。

### 1.2 函数清单（封闭API，不允许改名）

| 函数 | 签名 | 语义 |
|------|------|------|
| `module_ids()` | `-> list[str]` | 有序返回全部10个模块id |
| `get_module(mid)` | `-> Module \| None` | 按id取模块 |
| `get_subfield(mid, sid)` | `-> SubField \| None` | 按(模块,子字段)取子字段 |
| `first_module()` | `-> Module` | 第一个模块（IP定位） |
| `first_subfield(mid)` | `-> SubField` | 指定模块的第一个子字段 |
| `next_subfield(mid, sid)` | `-> SubField \| None` | **模块内**下一个子字段；`sid=None`返回首个；模块末尾返回`None`（跨模块由调用方处理） |
| `next_module(mid)` | `-> Module \| None` | 顺序下一个模块；末尾返回`None` |
| `subs_for_module(mid)` | `-> list[SubField]` | 模块全部子字段（未知模块返回`[]`） |
| `total_subfield_count()` | `-> int` | 全模块子字段总数 |
| `all_subfield_keys()` | `-> list[str]` | 全部答案键有序列表 |
| `is_module_done(mid, answers)` | `-> bool` | 模块所有子字段的键都在answers中 |

**推进算法**（guide_engine `_advance` 的契约）: `next_subfield` 返回`None` → 调 `next_module` 跨模块 → 全部耗尽 → `phase=completed`。

### 1.3 模块结构（封闭枚举，不允许添加或修改）

| # | 模块id | 子字段数 | 子字段id |
|---|--------|---------|----------|
| 1 | IP定位 | 4 | name / concept / world_type / core_experience |
| 2 | 世界本体 | 3 | origin / existence / reality_rule |
| 3 | 力量体系 | 4 | source / acquire / mechanism / cost |
| 4 | 地理空间 | 3 | terrain / vertical / special_geo |
| 5 | 文明与社会 | 4 | core_value / conflict / faction_type / economy |
| 6 | 历史时间线 | 3 | time_span / key_nodes / main_plot |
| 7 | 视觉设计 | 3 | keywords / architecture / material |
| 8 | 玩法设计DNA | 4 | player_role / main_action / growth / growth_end |
| 9 | 骰子设定 | 5 | probability / dice_count / check_mode / success_check / cost_mech |
| 10 | AI生成边界 | 2 | generable / immutable |

**结构约束**（测试锁定 `tests/unit/a1/test_question_tree.py`）:
- 恰好10个模块，顺序如上
- 每模块2-5个子字段，总数25-40（当前35）
- 子字段id全局唯一
- `历史时间线.key_nodes.hint` 必须包含 severity 四值说明：`COSMIC / MAJOR / REGIONAL / MINOR`

**权威来源**: `.sisyphus/drafts/A模块层级图-含断点.md` 第4套（世界观拓扑维度）。

### 1.4 消费方登记（已迁移完毕）

| 消费方 | 使用的函数 |
|--------|-----------|
| `app/domains/creation/a1/guide_engine.py` | MODULES / first_module / first_subfield / get_module / get_subfield / next_subfield / next_module / total_subfield_count / module_ids / is_module_done / subs_for_module |
| `app/domains/creation/a1/innovation_capture.py` | get_module / get_subfield（+ guide_engine._advance/progress） |
| `app/api/a1_routes.py` | MODULES / first_module / first_subfield / get_subfield / module_ids / get_module / is_module_done / subs_for_module |
| `derive_dice_recommendation`（semantic_compiler） | 读答案键 `世界本体.reality_rule` / `力量体系.source` / `力量体系.acquire` / `玩法设计DNA.main_actions` |

---

## 2. R2: /api/a1/chat/confirm 响应契约（修正）

> **状态**: ✅ 已实现（`backend/app/api/a1_routes.py` chat_confirm）
> **问题**: v5.0 原实现直接返回 confirm_proposal 的 dict（无 reply/next_question），前端无法统一渲染。

**API契约**:
```
POST /api/a1/chat/confirm
请求: {session_id: str, proposal: ClassificationProposal, choice: str}
响应: {
  persisted: bool,
  file_diff: DiffChange[],
  progress: {...},          // 与 /api/a1/chat 相同结构
  phase: str,
  reply: str,               // ★新增: 确认结果文案
  next_question: QuestionPayload | null  // ★新增: 下一题，与 chat 相同负载
}
```

**choice 封闭值（逐字，不允许添加）**: `"其他"`（存 `[其他] 原文`）/ `"放弃"`（不落盘）/ 其他任意值（存 choice 本身）。

**错误码**: 404 session not found / 422 proposal 校验失败。

---

## 3. R3: 前端 classification_proposal 契约（修正）

> **状态**: ✅ 已实现（`frontend/src/pages/a1/A1Workspace.tsx`）
> **缺陷回顾**: v5.0 前端把 proposal 对象存入 `string` state 直接渲染 → React "Objects are not valid as a React child" → 整页黑屏。

**TypeScript 契约**:
```typescript
interface ProposalSuggestion { field: string; category: string; }
interface ClassificationProposalData { suggestions: ProposalSuggestion[]; }

interface ChatResponse {
  ...
  classification_proposal?: ClassificationProposalData;  // ★修正: 对象非字符串
}
```

**confirm 请求体（铁律）**: 必须携带完整 `proposal` 对象回传：
```typescript
{ session_id, proposal: ClassificationProposalData, choice }
```

**Modal 行为**: 渲染 suggestions 列表（原文→建议分类）；按钮「保留原文（其他）」→ choice="其他"，「放弃」→ choice="放弃"。

---

## 4. R4: 工程治理新规（TYPE_CHECKING禁令）

> **缺陷回顾**: deps.py 曾把 `DimensionGenerator` 放在 `TYPE_CHECKING` 下导入，而 `get_dimension_generator() -> DimensionGenerator` 是 FastAPI 依赖函数。Deepcode 运行环境（新版Python的inspect注解求值）在路由注册时 eval 该字符串注解 → NameError → 后端启动崩溃。

**铁律**: **FastAPI 依赖注入链上的函数（路由handler、Depends目标、dependency getter）的参数/返回注解所引用的类型，必须在运行时模块命名空间真实存在。禁止仅通过 `if TYPE_CHECKING:` 导入。**

- ✅ 允许：模块顶层直接导入（当前 deps.py 的做法）
- ✅ 允许：函数体内延迟导入（不涉及注解求值）
- ❌ 禁止：`TYPE_CHECKING` 导入 + 依赖函数注解引用
- 检查方式：`TestClient(app).get("/openapi.json")` 返回200 = 全路由注册通过（import成功不代表注册成功）

---

## 5. R5: A1 LLM访谈器契约（交互范式重构）

> **状态**: ✅ 已实现（`backend/app/domains/creation/a1/interviewer.py` + `guide_engine.py` 重写）
> **范式声明**: 问题树是**进度框架和灵感参考**，不是用户必须逐字段填写的表单。用户自由表达，LLM 理解后填入结构化文件。**普通名称/概念/描述绝不是创新**；仅当 LLM 判定内容为世界观设定且不属于十大模块体系时才进入创新确认（建议新增小类）。

### 5.1 数据结构

```python
class InterviewFill(BaseModel):
    module: str      # 必须是 MODULES 中的合法 id
    subfield: str    # 必须是该模块的合法子字段 id
    value: str       # LLM 提取的简洁中文值

class InterviewResult(BaseModel):
    fills: list[InterviewFill] = []          # 可一次填多个字段
    guidance_reply: str = ""                 # LLM 个性化引导语
    is_innovative: bool = False              # 从严判定：超出十大模块体系
    innovative_category: str | None = None   # 建议新增小类名（中文短语）

class Interviewer(Protocol):
    def interview(self, session: A1Session, text: str) -> InterviewResult: ...
```

### 5.2 引擎分流规则（guide_engine.handle_message）

| LLM 判定 | 行为 |
|----------|------|
| fills 非空 | 写入全部字段（一次可多个）→ `sync_position` 跳到第一个未答子字段 → reply=guidance_reply |
| fills 空 + is_innovative | 返回 classification_proposal（category=建议小类名），不落盘不推进 |
| fills 空 + 非 innovative（闲聊/提问） | 仅 reply，不落盘不推进 |
| "跳过" | 当前子字段存空串并推进 |
| LLM 异常（DegradingInterviewer 降级） | **原文直存当前子字段**——绝不弹创新窗 |

### 5.3 种子上下文（seed context）

`A1Session` 新增字段：`seed_name / seed_genre / seed_description`（默认空串）。

- 选预设 → 三字段填入 preset 的 name/genre/description
- 自定义创意 → `seed_description` = 创意文本（≤500字），不硬编码预填任何 answers（由 LLM 在访谈中理解提取）
- `POST /api/a1/session/start` 响应新增 `seed: {name, genre, description}` 块
- `RealLLMInterviewer` prompt 注入【种子起点】块，引导语与基调保持一致
- 前端访谈页 header 显示所选种子（名称+题材），开场白复述种子/创意

### 5.4 RealLLMInterviewer 约束（铁律）

- prompt 注入：当前访谈位置 + 用户已答摘要（≤12条）+ 全部35字段清单 + 用户输入
- `fills` 校验：`(module, subfield)` 必须逐字命中字段清单，清单外一律丢弃
- 引导语 ≤ 2 句中文，需结合已填内容
- provider 由 `.env` 的 `ACTIVE_PROVIDER` 决定（当前 deepseek）

### 5.5 惰性初始化（时序铁律）

`a1_routes._get_interviewer()` 为惰性单例。**禁止在模块导入期创建 provider**——`main.py` 的 `load_dotenv()` 晚于路由模块导入，导入期创建会看到空 `ACTIVE_PROVIDER` 而永久降级离线。

### 5.6 废弃登记

- `RealSemanticCompiler` 作为 A1 访谈主链路：**废弃**（`_COMPILER = None` 保留占位）。其三级枚举匹配降级为可选的辅助路径，不再是用户输入的门卫。

---

## 6. 验证基线（2026-08-24）

| 检查项 | 结果 |
|--------|------|
| 后端全量测试 `pytest tests/` | 606 passed |
| 前端类型检查 `tsc --noEmit` | 0 errors |
| 前端单元测试 `vitest run` | A1相关 12/12（预存在失败：useTypewriter 6个 + e2e误入1个，与本次变更无关） |
| 路由注册冒烟 `/openapi.json` | 200，37 paths |
| 端到端 | 选种→输入名称→确认弹窗→保留原文→推进下一题 ✅ |
| 全模块导入扫描 `walk_packages(app)` | 0 failures |
| 全项目 TYPE_CHECKING 残留 | 0 处 |

### R5 验证（LLM访谈，2026-08-24 真机 deepseek）

| 场景 | 用户输入 | LLM 行为 | 结果 |
|------|---------|---------|------|
| 名称 | "这个世界叫星陨大陆" | 填入 IP定位.name，个性化引导语 | ✅ 无弹窗，推进到核心概念 |
| 多字段 | "东方仙侠，修士悟道觉醒灵力，施法折损寿元" | 一次填入 3 字段（IP定位.类型 / 力量体系.获取方式 / 力量体系.代价维度） | ✅ 跳到第一个未答字段 |
| 闲聊 | "你好，这个访谈要多久？" | 回应时长+复述已记录内容+引导回当前问题 | ✅ 无落盘无弹窗 |

---

## 附: v5.0 有效性声明

v5.0（`SYSTEM_DESIGN_SPEC_v5.md`）中除以下被本文替代的内容外，其余全部有效：
- T9 中引用的 Section API / `SECTIONS` / `first_section` 系列 → **废弃，以本文R1为准**
- chat/confirm 响应形状 → **以本文R2为准**
