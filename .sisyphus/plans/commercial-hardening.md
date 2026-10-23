# 商业加固批施工单（P0+P1：卡死防线 + F1-F4 + 可观测）

依据：`.sisyphus/evidence/freeze-diagnosis.md`（受控浏览器复现实证）+ 产品方 2026-10-19 拍板「开始」。

## 修复清单（全部 TDD：红测先行）

### P0-1 preview 链修（1 行）
A1Workspace.tsx L1449 一带：`closingState?.preview.consumers ?? []` → `closingState?.preview?.consumers ?? []`

### P0-2 ErrorBoundary（新组件 + 三处包裹）
- 新建 `frontend/src/components/shared/ErrorBoundary.tsx`：class 组件
  （getDerivedStateFromError + componentDidCatch），fallback 渲染 data-testid="error-boundary"
  的错误卡（标题「这块区域出了点问题」+ 错误摘要 + 「重试」按钮 reset state + 「继续其他操作」提示），
  **绝不白屏**
- 包裹三处：main.tsx App 根级；A1Workspace renderGuidedChat 的聊天区
  （GuidedChat + ClosingPanel JSX 外层）；renderGraphView 图谱区外层
- vitest ≥2 用例：子组件抛错 → fallback 显示；点重试 → state 复位子组件恢复

### P0-3 F1 真值闸拦占位填充（后端）
- 现状：LLM 产出 `角色.character_visual = 无（未提供外表特征）` 未被拦，与真值冲突生成无意义提案
- 修法：fills 摄入链路加占位值判定（参考 alignment_flow.py:52 `_PLACEHOLDER_WORDS` 先例）——
  新判定覆盖 `未提供|未提及|未说明|无（未|^无$|^\s*无（`）等 LLM 塞责式填充；命中则**丢弃该 fill**
  （不写答案、不生成提案、不计数），可在 file_diff/warning 留痕但不打断对话
- 红测：fill 值「无（未提供外表特征）」→ answers 零写入 + pending_proposals 空 + 正常值不受影响

### P0-4 F2 提案挂起的 chat 语言消解（后端）
- 现状：pending_proposals 非空时，chat「放弃」走 deflected 通道，提案永不消解（死路）
- 修法：handle_message 入口（或 routes chat 调 engine 前）：pending_proposals 非空 且消息为
  短指令（≤6 字符）且命中 替换/合并/放弃 关键词 → 直接调既有 `resolve_proposal(session, key,
  canonical_choice)`（routes:965 先例；放弃=drop/替换=replace/合并=merge），跳过 LLM 通道竞争
- 红测：构造 pending_proposals 会话 → chat「放弃」→ 提案消解 + answers 保留原值 + reply 示已放弃

### P0-5 F3 已答开放问题不重问（后端）
- 现状：oq-001 已 answered（file 侧），引擎 reply 仍「回到刚才的问题」重问
- 排查：session 侧 interviewer 的 pending open question 状态与 file 侧 oq_log 双源——
  回答落账后 session 侧展示态未刷新（open_questions.py:53 next_pending 只滤 pending/asked，
  但 set_pending_open_question(routes:817) 发生在 handle_message 之前，同轮回答后不回清）
- 修法：回答事件落账时同步清 session 侧 pending open question（或下一轮 present 前重取 next_pending）
- 红测：答完 oq-001 → 下一条 chat 响应的 pending_question/话术不含 oq-001 文本

### P0-6 F4 + P1-6 skip 失败可观测（前端）
- skipPendingQuestion catch（A1Workspace L918-921 一带）：setError('跳过失败，请重试')（现有 error 条渲染）
- sendMessage catch 已有 setError ✓ 不动；确认无其他静默 catch
- 红测：mock fetch reject → 错误条出现 + loading 复位

### P1-5 loading 看门狗（前端）
- A1Workspace 新 useEffect：isChatLoading 置 true 时起 125s 定时器，超时 → setIsChatLoading(false)
  + setError('请求超时，已自动解锁，请重试')；loading 结束/卸载时清定时器
- 红测：fake timers 前进 125s → loading false + 错误条在

### P0-7 E2E 补幕 + 路由遮蔽修
- `a1-wave3-frontend.spec.ts`：closing-state 专用 mock 移到通配 `**/api/a1/file/**` **之后注册**
  （Playwright 后注册优先——当前遮蔽致幕一断言后崩溃仍绿灯）；补带 preview 的正常载荷
- 新增 幕五「崩溃降级」：closing-state mock 故意无 preview → 断言 error-boundary 可见、页面存活
  （textarea 或导航仍在）、刷新/重试可用
- 全部既有四幕断言不变仍须绿

## 门禁
- 后端：新增红测全绿 + pytest 全量 ≥1842+新增 全绿
- 前端：vitest 全量 ≥330+新增 全绿；tsc -b delta=0（20 处 11 文件存量不变）
- Playwright 五幕 chromium 5/5
- 白名单逐文件核对；ruff 增量 0

## 红线
- 不动 graphify/finalize/guide_engine 六通道既有排序逻辑（F2 是**前置**短路，不是通道重排）
- resolve_proposal 复用不改签名；后端其余文件零触碰
- 不做 P2（pendingQuestion 单源/proposal 相位——另批）
- 提交归主会话：代理零 git 操作
