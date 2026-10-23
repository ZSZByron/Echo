# Learnings — direction-a-option-forward

## 2026-10-08 T0 D23 E2E 冒烟（施工单第一锤）
- 栈启动：后端用 Start-Process 分离进程（uvicorn 无 --reload，避免文件锁）；前端 npm run dev 经 cmd /c 重定向日志；两服务 ~12s 内健康（8000/api/health、5173/a1）。
- Playwright MCP 截图/文件只能落在允许根（C:\Users\Administrator\.playwright-mcp），证据需手动 Copy-Item 到 .sisyphus\evidence\。
- 访谈流：种子卡 data-testid=impulse-card-*，确认按钮 impulse-confirm；侧栏字段与 file_diff 同步来自 /api/a1/chat 响应，browser_network_requests 序号即响应体抓取索引。
- D23 关键发现：浏览器级等价改写未命中 auto_merges 分支——LLM 要么不产 fill（file_diff=[]），要么走 proposals 冲突确认流（替换/合并/放弃）；AutoMergeBar 只消费响应里的 auto_merges，未出现即无撤销入口。S2（key_relations 追加）与 S3（澄清不复读）浏览器级通过。
- 答非当前所问会被降级为「未能理解」+示例引导；「放弃」proposal 会给当前问题写（用户跳过）(deflected:true)。

## 2026-10-08 T1 契约测试先红（施工单第二锤 2a）
- 测试基建：conftest.py 有 autouse `_isolated_a1_store` + `_no_real_llm_provider`（TestClient 级隔离，engine 级测试直接 new A1Session 即可）；FakeInterviewer 已有 examples 参数（L125）但 interview() **未透传**进 InterviewResult（字段 T2 才加）——test 文件内用 `ExamplesFake(FakeInterviewer)` 子类覆写 interview() 后 setattr 注入，既保证 T2 落地后确定性生效，落地前 ValueError 即红。
- 畸形注入靠 pydantic v2 默认 `validate_assignment=False`：字段落地后 `setattr(result,"examples","非列表")` 不触发校验，正好测引擎侧健壮性。
- 埋点 spy 契约：`inspiration_log.emit_event(event, session, **fields)`；monkeypatch 替换为内存记录器（模块落地前 ImportError 即红），断言 key：session_id/module/subfield/option_index|streak|stall_count。
- "missing degrades" 类纯回归测试天然先绿——必须补一条「新字段存在性」直接属性访问（`s.current_options == []`）才能红。
- 系统提示串断言入口：`RealLLMInterviewer(None)._build_prompt(module, subfield, session)`；8.5 在 `_pending_question_block()`（条件块，需 set_pending_open_question 后取）。
- Select-String 对 UTF-8 中文会假阴（编码问题）——存量断言审计必须用 python 读文件扫描；本锤实测 backend/tests 零命中，生产侧命中 guide_engine.py:943-944。
- 测试模块级常量（OPTION_INVITE_TEMPLATE 期望值）不能从 guide_engine import（会 ImportError 炸收集）——test 文件内复制期望文本 + `getattr(guide_engine, "OPTION_INVITE_TEMPLATE")` 断言相等。
- write-guard 提案轮触发法：预填 `s.answers["IP定位.name"]`，fills 同字段新值 + conflict_note → out["proposals"] 非空。

## 2026-10-09 T2 interviewer 合并（施工单第三锤）
- T2 全部生产改动（InterviewResult.examples 字段 L101、规则块 8.6 三段 L558-570、JSON schema examples 键 L580、解析降级 L876-884、InterviewResult(examples=...) L900）一次落齐，commit bfa05f5，仅 interviewer.py（+30/-1）。
- 红绿真相（contract 测试）：绿 = 3/4/5/6/7/15 共 6 条；红 = 1/2/13 + 8/9/10/11/12/14/16。**1/2/13 的红因全部在 guide_engine 侧**——A1Session 无 current_options 字段（pydantic v2 setattr 直接 ValueError / getattr 直接 AttributeError）+ 无 OPTION_INVITE_TEMPLATE 常量，属 T3 Step 1/2 范围，T2 无法在不越界下转绿。施工单「T2 使 1/2/3/13/15 转绿」的预期与现实不符：1/2/13 实际由 T3 转绿，3/15 由 T2 转绿。
- 4-7（白名单四轮次）为纯回归断言（「无邀请话术」），T2 后天然先绿——learnings L14 先例再次验证。
- FakeInterviewer spy 契约现状：interview() 计数属性名是 calls（契约13 用，已存在）；**无 suggest_calls**（契约9/10 用，T4 落地 reroll 时才需要——届时给 FakeInterviewer 加 suggest_calls 计数或利用 ExamplesFake）；_build_prompt / _pending_question_block / set_pending_open_question 均已存在（契约15 直接过）。
- pydantic v2 默认 validate_assignment=False 只对**已存在字段**生效；未声明字段的 setattr 抛 ValueError('object has no field')，getattr 抛 AttributeError——这就是 T1→T2 之间红测的失败形态，与 T2 之前 notepad 记录一致。
- 全量回归：1594 passed / 10 failed（全部是 option_forward 新契约），旧套件零回归；coverage 84.04% ≥ 80% 门禁。
- 8.5/8.6 锚点（改后）：8.5 块在 _pending_question_block() L592-605（原文逐字节未动）；8.6 块在 _build_prompt 返回列表 L558-570，紧随 *self._pending_question_block()（L557）之后、【可填字段清单】（L572）之前。

## 2026-10-09 T3 guide_engine 接线（第四锤，commit 27200b0）

### Step 0 pending_suggestions 审计表（逐锚点裁决，行号为改后）

| 锚点 | 位置 | 裁决 | 理由 |
|------|------|------|------|
| L348 字段声明 | A1Session | 保留（死字段不删） | 施工单红线：零迁移；注释保留原文 |
| L958 `pending_suggestions=[]` | _apply_stall_guard 填写成功重置 | **保留写入** | 仍服务 stall>=3 分支：stall>=3 无 fill 时 L1019 写入 suggestions，若填写成功不清理，下轮 stall>=3 会复用陈旧示例（L1013 短路跳过 suggest_examples）——这是活逻辑不是死写 |
| L1003 `pending_suggestions=[]` | forced_allocate 成功重置 | **保留写入** | 同 L958 理由 |
| L1013-1024 读取+写入 | stall>=3 无 fill 兜底（渲染"直接回复序号"） | **保留** | 红线 7：stall>=3 分支零改动。**已知退化**：其 reply 引导用户"回复序号"，但直选分支已改读 current_options（此轮被 _attach_default_options(blocked=True) 清空）→ 用户序号回复会落 interview() 而非直选。施工单预期内（"read stale/empty — document"），留待后续任务收口 |
| L1049-1052 _reset_stall_tracking | 含 pending_suggestions 清理 | **保留** | 调用点 L616/1092/1158/1177（提案确认/偏转等路径），清理对死字段无害且喂 L1013 判断 |
| 旧 pick 分支读取/写入 | 原 ~L1251-1280 | **退役** | 直选改读 current_options（D-4） |

### 回复组装点与白名单实现
- 追加位置：fills 分支在 _round_end_signals + auto_merges 披露**之后**末尾 `out_fills["reply"] += "\n" + 邀请块`；chat 分支在 _round_end_signals 之后。blocked 判据：fills=`bool(intercepted) or guard is not None`；chat=`guard is not None`；deflect/story_material 轮内联清空；completed 由 _attach_default_options 内 phase 判断兜底。
- examples 读取在 sync_position **之后**（fills 分支 L1356 先 sync，选项在轮末才挂）→ 推进刷新语义成立（契约14）。
- 空/畸形 examples（getattr+isinstance 双保险）→ current_options=[] 且 reply 逐字节不动——降级零痕迹（契约 _assert_no_options 过）。

### ⚠️ 与施工单预期的偏差（重要）
1. **3 条存量测试随 stall==2 分支退役而转红**（施工单"audit 显示零依赖"结论有误）：test_guide_engine::test_stall_suggests_examples_then_number_pick、test_stall_suggest_unavailable_asks_rephrase、test_blind_recording_fix::test_stall_2_suggestions_unavailable_no_raw_fill。已用 HEAD worktree 验证：HEAD 上 3 条全过 → 红因=本锤删除的 stall==2 分支行为（断言 stall2 回复含"示例"/rephrase 话术/序号直选流），非实现缺陷。契约12 已取代其规格。测试文件本锤禁改 → 记为 known-red，需后续测试清理任务删除/改写。
2. 全量真相：**1597 passed / 7 failed**（4 条 inspiration_log ImportError=T5 范围 + 上述 3 条 legacy 退役红），非施工单预期的 1600/4。
3. 工作树里发现前次会话已写入大部分 T3 代码（未提交未验证）——本锤核对了逐条规格（字段注释逐字、模板逐字、白名单四轮次、pick 语义、skip 锚点、payload additive 键），补齐验证与审计后落 commit 27200b0（仅 guide_engine.py，+82/-47）。

### 验证留痕
- 契约 16 条：12 passed（含 1/2/11/12/13/14 全绿 + 4-7/15 回归保持）；4 failed 全部 ImportError(inspiration_log)=T5。
- a1 子集：1101 passed / 7 failed（同上 7 条）。
- lsp pyright 6 error 均为存量（L529/837/842/861/878/1595，AnswerNode/_SubFieldExtras 型变问题，非本锤触碰行）。

## 2026-10-09 T4 reroll 通道（第五锤，commit 8bdb3ce）

- suggest_examples 真实签名（interviewer.py Protocol L109 / RealLLM L607）：`suggest_examples(self, session, module_id: str, subfield_id: str) -> list[str]`——传 session.current_module / session.current_subfield 即可；返回 [] = 不可用（引擎侧自行降级）。
- **FakeInterviewer 无 suggest_examples / suggest_calls**（测试基建缺口，T5 需补）：本锤验证用 snippet 内 CountingFake(FakeInterviewer) 子类计数；契约 9/10 用的 ExamplesFake 似乎已覆写（test_option_forward 内部类），suggest_calls 属性是否存在 T5 落 telemetry 时要实测。
- 插入点：_handle_message_impl 链序 = 跳过 → 序号直选 → 【新】reroll → interview()。reroll_streak 清零放在函数最顶部（`text.strip() not in REROLL_KEYWORDS` 即清零），skip 分支内原有清零保留（冗余无害）。注意 stripped 变量在 pick 分支前才定义（原 L1273），reroll 分支复用它。
- 新常量：REROLL_KEYWORDS 闭集 {"换一批","再来一批","换组"} / REROLL_CAP=2 / REROLL_CAP_REPLY="示例换了几轮了，先试试直接选一个，或用自己的话说说。"（含契约10要求的两子串）。# telemetry: option_reroll 锚点在成功 emission return 前。
- 降级设计：suggest_examples 返回空/畸形 → current_options=[] + 「这次没想出更多示例…」引导，不计 streak 后退回主路径（避免「换一批」字面量漏进 interview 语义混乱）。
- 验证：定向 54 passed / 4 failed（全为 inspiration_log ImportError=T5）；全量 **1600 passed / 4 failed** 与施工单预期完全一致（T3 时代的 3 条 legacy 红已被 HEAD ed0c2c4 测试改写消化）。lsp 6 error 均为存量型变问题，行号漂移非新增。
- 手动证据（CountingFake）：reroll×2 各 +1 call 且 options 替换、stall_count 恒为 1；第 3 次零调用、cap 话术含「直接选/自己的话」；普通输入后 reroll_streak=0。

## 2026-10-09 T4 reroll 通道（第五锤，commit dc8fa96）
- **HEAD 上已有半成品 T4**：8bdb3ce 已含完整 reroll 分支（L1314-1350，REROLL_KEYWORDS/REROLL_CAP/REROLL_CAP_REPLY 常量 + L1255-1257 早置零），但 emission 只留锚点注释。本锤发现自己插入的重复分支是死代码后 git checkout 回退 guide_engine，仅在既有分支成功路径补 emission 调用（+11 行）。教训：动手前先 git log + grep 全量锚点，T3 的『工作树残留』先例这次发生在已提交层。
- **契约9 转绿的关键在 FakeInterviewer 注入透传**：ExamplesFake 只设 self._inject 不覆写 suggest_examples → FakeInterviewer.suggest_examples 优先 getattr(self, "_inject")（isinstance list 且非空才用），否则回落 _examples/默认三例。生产侧 emission 前提：guide_engine 以模块属性访问 inspiration_log.emit_event（本地 import + 属性调用），monkeypatch 才能拦截。
- **契约10 test_reroll_cap_two 是测试自身 bug（known-red）**：inject=[f"n{i}"...] 的 i 在测试作用域未定义 → NameError，T1 起就红（被 ImportError 掩盖）。生产不可修，禁改测试 → 记入 issues，待测试清理任务改字面量。
- 最终靶向真相：55 passed / 3 failed = 契约8+16（T5 emission）+ 契约10（NameError 测试 bug）。pyright 全部存量错误，无新增。

## 2026-10-09 Reroll branch reconciliation (Sisyphus-Junior)

- Actual tree state differed from task brief: the duplicate reroll branch (~L1362-1408), REROLL_CAP_TEMPLATE, REROLL_REFRESH_TEMPLATE/_render_option_lines, and the redundant post-interview eroll_streak = 0 **did not exist** — only the committed branch (L1318-1359) plus an uncommitted emission-call addition. Reconciliation = verify single branch + keep emission call.
- Final single-branch shape: guard L1318 stripped in REROLL_KEYWORDS and session.current_options; cap L1319 >= REROLL_CAP → REROLL_CAP_REPLY (L451); suggest L1328; eroll_streak += 1 L1331; emission L1335-1343 (inspiration_log.emit_event("option_reroll", ... streak=...)); success reply via _render_option_invite (L1345, OPTION_INVITE_TEMPLATE → "1. n1" satisfies contract 9); degrade path L1351-1359. Constants single set at L446-451.
- Gotcha 1: committed test_option_forward.py L265 had a NameError typo ("n{i}" without loop var) making contract 10 unrunnable; fixed to literals ["n1","m1","o1"] in commit 9200456 (test file untouched otherwise).
- Gotcha 2: orchestrator committed identical 3-file content as dc8fa96 mid-session; source commits: dc8fa96 (source) + 9200456 (test fix).
- Verification: targeted pytest = 2 failed / 56 passed. Remaining 2 failures (test_pick_option_fills, test_telemetry_events_emitted) need option_pick emission = T5 wiring, explicitly out of scope.

## 2026-10-09 T5 telemetry JSON-lines（第六锤，commit 0e2e6dd）

- 实现落点：inspiration_log.py emit_event = LOG_PATH 模块级常量（data/inspiration_log.jsonl，相对 backend cwd）+ mkdir parents + append utf-8 + ensure_ascii=False + 全 except 静默。测试 monkeypatch inspiration_log.LOG_PATH 指向 tmp_path。
- 锚点最终行号（改后 guide_engine.py）：stall emission L980-988（计数站点之后、module_id/sub_id 已解出、get_subfield 之前）；skip emission L1276-1281（return 前，answer_key 尚未推进 → subfield 用 nswer_key.split(".",1)[1]，**不能**用 session.current_subfield——sync_position L1264 已推进指针，契约16 断言被跳字段）；option_pick emission L1329-1337（module_id/sub_id/idx 局部变量，options_digest 需在 current_options 清空前快照，否则落空串）；option_reroll L1367-1374 未动。
- ⚠️ Gotcha：Edit 工具对重复串 subfield=session.current_subfield, 替换会命中 reroll 站点而非 skip 站点（skip 原文同串），造成 UnboundLocalError(answer_key)——多站点相似代码块编辑必须带足上下文锚定。
- .gitignore：根 .gitignore 的 data/*.jsonl 锚定仓库根，**不覆盖** backend/data/；新建 backend/.gitignore 一行 data/*.jsonl。
- 报告脚本：backend/scripts/inspiration_report.py（stdlib Counter；argv[1] 可选路径；畸形行计数 malformed 不参与事件统计）。
- 验证真相：定向 4 文件 60 passed / 0 failed（契约8/16 转绿，reroll 契约9/10 保持，guide_engine + blind_recording_fix 回归全绿）。lsp 0 error（新文件）。契约 10 现已绿——learnings L70 记录的 NameError 已被 commit 9200456 修复。

## 2026-10-09 T5 telemetry jsonl (Sisyphus-Junior)

- **Concurrent-worker reconciliation**: mid-session a parallel worker landed the identical T5 scope as commit 0e2e6dd (same message, same 4 files + .gitignore ignore for data/inspiration_log.jsonl). My Edit/patch attempts found oldStrings already mutated (count=0) — that was the signal, not a patch-script bug. Lesson: on this machine ALWAYS `git diff` + grep current state before patching; working-tree state can change under you between status checks.
- Final wiring line numbers (HEAD 0e2e6dd): stall emission ~L980-989 (_apply_stall_guard, after cur_key.split, before get_subfield); skip ~L1274-1281 (uses answer_key.split(".",1)[1] — answer_key IS bound in skip branch); option_pick ~L1310-1329 (digest = "|".join(str(o) for o in current_options[:3]), captured BEFORE current_options cleared); reroll unchanged (dc8fa96 form).
- LOG_PATH resolution: Path(__file__).resolve().parents[4] = backend/ (parents[3] in task brief was wrong; chain a1→creation→domains→app→backend). data/inspiration_log.jsonl confirmed gitignored.
- Edit tool fails on these files (CRLF + Chinese content, "oldString not found" even after Read); python io.open(newline-universal read, newline="\r\n" write) patch works. inspiration_log.py I rewrote via [IO.File]::WriteAllText UTF8-no-BOM.
- Verification evidence: targeted 18/18 passed (16 contracts + 2); full suite 1606 passed / 0 failed / 67s; report script sanity: missing file → "total: 0", real data (120 events from test runs: pick 2 / skip 8 / stall 110) parses clean.
- Gotcha: report script has NO argparse (--help just prints report of default path); takes sys.argv[1] positionally — fine per spec.

## T6 (2026-10-09, commit b1e2327)
- ANCHOR_BY_TYPE 真身在 app/domains/creation/shared/module_registry.py（非 seed/）；interviewer.py 既有 re-export 兼容导入（L36 noqa: F401），T6 直接复用，零新增导入。
- T6 实现在本会话开始前已在工作区就位（先前执行残留）；本会话补齐契约测试 test_impulse_anchor.py（4 条：双注入点命中/缺省不注入/九句 verbatim + is 同源断言）并提交。注意工作区有并行改动（PROJECT_STATE/README 等 D23 相关），提交严格只含 interviewer.py + 测试文件。
- 条件注入模式沿 M0 先例：*( [line] if cond else [] )，缺省 prompt 逐字节不变。

## 2026-10-09 T6 impulse-anchor injection（第七锤，commit b1e2327）

- ANCHOR_BY_TYPE 实际位置：app/domains/creation/shared/module_registry.py L58-68（非施工单写的 interviewer 内）；interviewer.py L35-39 已有 re-export import（# noqa F401），零新增 import。九键：plot/unsure/philosophy/romance/character_driven/setting_heavy/exploration/nostalgia/healing。
- 注入点行号（改后 interviewer.py）：site 1 = 8.6 块内、防火墙段之后/引用理解段之前（~L572-581）；site 2 = suggest_examples system 列表、故事向条件段之后/「返回严格JSON」之前（~L664-672）。均为 *( [...] if getattr(session,"creator_primary","") in ANCHOR_BY_TYPE else [] ) 单元素条件展开，空 profile 时 prompt 逐字节不变。
- A1Session.creator_primary = guide_engine.py L335 creator_primary: str = ""（字段名与施工单一致，无偏差）。注意 _seed_block L402-409 已有另一路锚点注入（走 Recipe.anchor）——T6 的两处是示例风格锚点，语义不同、共存无害。
- 测试文件 tests/unit/a1/test_impulse_anchor.py 动手前已存在半成品（并行 worker，无 test_nine_anchors_verbatim）——本锤核对规格后仅追加逐键 verbatim 测试（L92-101），不重写既有内容。旈权名 test_anchor_sentences_verbatim 只验表本身不验 prompt 注入，故补齐。
- 验证：pytest tests/unit/a1/test_impulse_anchor.py + test_option_forward.py = 21 passed（契约 15 的 8.6 条款保持）。pyright 报错均为存量 Module/_SubFieldExtras 型变 + chat_json None 类（与 test_option_forward 同型，先例 L55）。提交 b1e2327 仅含两文件（interviewer.py +19、test +100），PROJECT_STATE/README 等脏改动未混入。

## 2026-10-09 T7 验收锤（四点自测 + E0 对比）— Sisyphus-Junior
- E0 对比方法（可复用）：git worktree add $env:TEMP\opencode\pre-a1 <旧commit> → 复制 backend\.env → H:\UGC\backend\.venv 的 python 以 worktree\backend 为 workdir 起 uvicorn 8001（依赖复用主 venv，可行）→ 同一脚本 POST session/start(custom_idea+impulse_primary)+chat×5 抓 file_diff → 完了 Stop-Process + git worktree remove --force。harness 在仓库外：$env:TEMP\opencode\e0_compare.py。
- Playwright MCP 浏览器不稳（页面反复重置 about:blank、"No open pages"）——正解是全部走 browser_run_code_unsafe 单页大脚本：goto→waitForResponse(/api/a1/chat) 逐轮发问→reply+file_diff+options 全量返回，截图用 page.screenshot 绝对路径落 C:\Users\Administrator\.playwright-mcp。逐工具点击式流程在该机上不可靠。
- session/start 需要 seed_id 或 custom_idea 二选一（只发 impulse_primary 会 400）；UI 的「为角色造世界」= custom_idea 我心里有个角色活了起来… + impulse_primary=character_driven。
- 发现真实 UX gap（观察点3b）：直选「1」后推进到的新问句 current_options=[]（pick 路径不产 options），首次「换一批」被 interview() 当自由文本消化 → reroll_streak 少计 1 → 第 3 次连续换一批不触发 REROLL_CAP_REPLY（实际第 4 次才 cap）。非死路非劫持，二期收口。
- next_question.options payload 滞后一轮（带刚答问句的选项），reply 文本才是当轮权威选项来源；前端不消费，无感。
- E0 结论：old(e2b7367) vs new(b1e2327) fills 5/5 对 5/5，质量持平略优（key_relations new 更紧），零选项污染。
- 误劫持：0 例；「把1和3揉一起」正确走理解路径未被劫持为直选。
