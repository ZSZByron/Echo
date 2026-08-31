# A1 世界观文档直传功能设计

日期：2026-08-25
状态：设计定稿（①②③均已确认）

## 目标

在 A1 初始界面（seed_selector）底部新增上传工具条，用户直接上传世界观文档（.txt/.md），经 LLM 版权检测与解析后预填 10 模块，并提取创新点作为第 11 附加模块。

## 总体流程（设计稿 ①）

```
[A1 seed_selector 底部工具条]
  └─ "上传世界观" 按钮 → 选 .txt/.md（前端 FileReader 读文本）
      ↓
POST /api/a1/upload  { filename, content }
      ↓ ① 格式检测（规则）：长度≥200字、文本占比（防伪装二进制）、<2MB
      ↓ ② extract_entities（LLM①）：主要角色名(≤10)、力量体系专名(≤8)、
          世界观关键词(≤8)、疑似作品名
      ↓ ③ check_copyright（LLM②，知识判断）：逐专名判断是否属于已发布
          小说/游戏/影视（含网文）→ {risk_level, hits:[{term, work, evidence}]}
      ↓
  ├── 命中已知IP → { status:"copyright_hit", upload_id, report }
  │     前端弹窗展示命中详情（作品名/相似元素）
  │     用户选择：[转换使用] / [取消上传]
  │       └─ 转换使用 → POST /api/a1/upload/convert
  │            LLM④ 净化改写（替换专名+调整关联设定）→ 回到解析主流程
  │
  └── 未命中 → ④ parse_worldview（LLM③）：
        按 MODULES schema 输出 answers（"模块id.字段id" → str）
        + innovations: [{field, suggestion}]（ClassificationProposal 结构）
        ↓
  创建 session（guided_chat 预填模式，source:"upload"）
  前端进入 guided_chat，逐模块可查看/修改，创新点走现有
  confirm_proposal 确认流，以第 11 模块卡片展示（不进 MODULES 顺序锁）
```

## 已定决策

| 决策点 | 结论 |
|---|---|
| 版权比对方式 | LLM 知识判断（零新依赖）；检测器抽成独立环节，返回 risk_level+evidence，后续可换 Tavily/Serp 实现而不动流水线 |
| 转换使用 | LLM 自动改名+改设定规避相似性后继续 |
| 解析后去向 | guided_chat 预填模式（可逐模块检查修正） |
| 创新模块 | 第 11 附加模块，复用 ClassificationProposal/confirm_proposal 确认流 |
| 文件格式 | txt/md 先行，接口按"文本内容"设计，docx/pdf 留扩展 |
| 降级 | provider 不可用 → /upload 返回 503 明确提示"需要 LLM 服务"，不静默降级 |
| 成本 | 正常 3 次 LLM 调用；命中版权 4 次 |

## 接口契约（设计稿 ②）

### 新增后端文件

`backend/app/domains/creation/a1/worldview_upload.py` — 纯函数流水线：

```python
extract_entities(text) -> Entities
check_copyright(entities, text) -> Report   # risk_level, matches, evidence
convert_text(text, report) -> str           # 净化文本
parse_modules(text) -> ParsedWorldview      # answers(31字段) + innovations
```

均通过 `create_provider` 惰性单例（仿 `_get_interviewer` 模式）。

### 新增端点（a1_routes.py 追加 2 个）

| 端点 | 行为 |
|---|---|
| `POST /api/a1/upload` `{filename, content}` | 格式检测→实体→版权；422 格式失败 / 200 copyright_hit / 200 parsed+session_id+answers+innovations |
| `POST /api/a1/upload/convert` `{upload_id, decision}` | decision ∈ "convert"(净化后重走解析) / "cancel" |

中间态存内存 `_UPLOADS`（与 `_SESSIONS`/`_FILES` 同模式，MVP 不持久化）。

### session 预填

批量写入 `A1Session.answers`（key="模块.字段"）后 `sync_position`；session 标记 `source:"upload"`。

## 前端改动（A1Workspace.tsx + 2 新组件）

1. seed 卡片网格与 custom input 之间新增上传工具条：⇪按钮 + 隐藏 input[accept=".txt,.md"] + FileReader，>2MB 拒绝
2. 分析中：spinner + 三段进度文案（格式检测中→版权比对中→解析填充中）
3. copyright_hit 弹窗（CopyrightDialog.tsx）：命中表格 + [转换使用][取消]
4. 成功后携 session_id 切入 guided_chat；预填字段标"预填"；创新点以第 11 模块卡片追加（仅展示+可编辑）

## LLM Prompt 设计（设计稿 ③）

全部走 `provider.chat_json`，schema 见流程图。

- **parse_worldview 核心**：遍历 `MODULES` 程序化生成 `模块id.字段id | question | example` 注入 prompt —— 与 a1_question_tree.py 单一事实源同步，永不漂移。同一调用附加输出 `innovations:[{field, suggestion}]`。
- **check_copyright 从严**：仅确定命中输出 high；不确定/冷门 → low 留空 hits。任一 hit 为主要角色或核心力量体系 → copyright_hit。
- **convert_worldview**：保留世界观结构、剧情逻辑与体验设计，替换全部命中专名为风格一致原创名，调整与原作直接关联的独特设定表述。

## 测试计划

| 层 | 内容 |
|---|---|
| 单测 | worldview_upload.py 用 FakeProvider：格式拒绝（短/二进制）、risk 边界、answers key 与 MODULES 31 字段全量对齐、convert 专名替换 |
| API | upload 三分支（422/copyright_hit/parsed）、convert 端点、预填后 progress() 跳过已填字段 |
| 前端 | 手动验收；Playwright E2E 后补 |

## 不做的事（YAGNI）

- 不接外部搜索 API（接口可替换设计已预留）
- 不做 docx/pdf 解析
- 不持久化上传中间态（与现有 MVP 内存态一致）
- 不改动 graph/poster 后半段流程
