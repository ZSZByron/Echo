# Learnings — d21-frontend-phase

## Session Start (2026-09-28, atlas)
- ACTUAL pytest baseline: **1531 passed / cov 84.04%** (plan says ≥1502 — outdated, F2 remediation commit ae3848b added +29 tests). Gate: 80%. Never cite stale numbers; use fresh run.
- ENVIRONMENT LESSON (from backend phase): sync task dispatches with 3+ parallel get interrupted; max 2 concurrent survives. Orchestrate in pairs.
- a1_routes.py ~2677 lines after T18; plan line refs (746/1054/1075) may have drifted a few lines after ae3848b import reordering — locate by structure/anchor strings, not blind line numbers.
- A1Session is a pydantic model: mutate nested state via `object.__setattr__` in tests; `getattr` direct path for graph_json.
- Git discipline: index has 4 pre-staged docs renames — commit with pathspec (`git commit -m "..." -- <paths>`) to avoid leaking them.
- PowerShell: git grep with Chinese patterns unreliable → use `Select-String -Encoding UTF8`; evidence files written with UTF-8 encoding explicitly.
- 404 detection dual path (frontend): ApiError(.status) AND fetchWithTimeout degraded Error('HTTP 404') — both must be handled.
- Pure-function-first: extract exported pure functions, test those instead of component snapshots (labels/ directory precedent: relationLabel.ts).
- Evidence path: .sisyphus/evidence/task-{N}-*.{ext}

## T1 (2026-09-28)

- a1_routes.py 实际路径：backend/app/api/a1_routes.py（无 routes/ 子目录，plan 路径有偏差）；2674 行。
- chat() 定义在 L747；既有测试用 message="跳过" 走 skip 早退分支（L774-786，无 LLM）——chat additive 注入需同时覆盖主出口（L865 前 return）与 skip 早退出口，两处都加了 `out["closing"] = _closing_signal(session)`。
- build_output_preview(file_id) 真实 preview 键：file_id/exists/closing/module_coverage/gaps/version_chain/stale/stale_warning/consumers；module_coverage 元素键 = module_id/done_ratio/done_fields/total_fields。
- 测试先例目录是 backend/tests/unit/a1/（不是 tests/unit/api/，后者不存在）；fixture：session/start 返回 payload 带 file_id；session 直改 a1_routes._SESSIONS[sid]（pydantic 直接赋值即可，无需 object.__setattr__）。
- chat 既有键逐字清单（skip 路径）：reply/next_question/file_diff/progress/phase/proposals/divergent_question（+open-question payload 键）。
- 全量基线更新：1536 passed / cov 84.06%（1531+5 新增），未动任何既有断言。
- LLM 若无 key 也不影响：closing-state 端点与 chat skip 路径均零 LLM。

## T4 (2026-09-28)
- 旧 formatQuestion（A1Workspace.tsx:269-276）：header = 【{section_label||section}】 或带 sub_label 时 【{section_label||section} · {sub_label}】；example join 格式为 \n💡 示例：{example}（换行 + 💡 示例： 前缀）。已逐字保留 example join，仅去 header。
- 新文件：src/labels/plainQuestion.ts（纯函数 plainQuestion）+ src/labels/__tests__/plainQuestion.test.ts（5 例：无【、零模块名泄漏、拼接保持、无 example、null 输入）。A1Workspace formatQuestion 改为薄接线 + 顶部一行 import。
- 零既有测试断言问题头格式：git grep 【 仅命中 A1Workspace.tsx(2) 与 graph/PromptPreview.tsx(6, 范围外)——无测试需更新。
- tsc 基线坑：npx tsc -b --noEmit 现存 33 行错误（graph 组件/遗留测试/A1Workspace 1515+ 行等，均与本改动无关）；stash 对照验证前后均 33 行，本改动零新增。计划上下文「tsc 基线 0 错」已过时。
- 测试 fixture 坑：sub_label 值不能与 question 文本重叠（初版「开场」撞问句「开场」误报泄漏）→ 改用「世界观背景」。
- vitest：基线 242 绿 → 改后 247 绿（+5）。git grep 【 A1Workspace.tsx 零命中。

## Atlas Verification Notes (2026-09-28, T1+T4 PASS)
- Frontend tsc ACTUAL baseline: **20 pre-existing error lines** (graph/legacy-test files + A1Workspace 1515/1637/1695 hydration regions). Frontend task acceptance = **zero NEW errors** (verify via parent-commit checkout comparison). Verified T4 added zero.
- Frontend vitest baseline after T4: **247 passed / 24 files**. Backend after T1: **1536 passed / cov 84.08%** (fresh full run by atlas).
- venv = `backend/.venv/Scripts/python.exe` (Anaconda F:\ python lacks pytest). Backend a1 routes test dir: `backend/tests/unit/a1/`.
- T1 commits verified: ab26e23 (+169, exactly 2 files). T4: 08f7f31 (+67/−6, exactly 3 files). Both pathspec-clean.

## T5 (2026-09-28) — DimensionProgress count-based plain label
- Created labels/plainProgress.ts (plainQuestion.ts kept question-only; single-responsibility split). plainProgressLabel(done, total) = 「聊聊你的世界 {done}/{total}」.
- Component rewrite: removed module-name tooltip + section label list + English header + 10-cell padding; one cell per section via data-progress-cell, dynamic gridTemplateColumns (no /10 hardcode). Props contract unchanged (Section/DimensionProgressProps untouched) — A1Workspace untouched.
- Old tests testing label-rendering spec replaced; new red-first tests: 3/7 fixture text, zero label leakage (queryByText null + textContent), cell count = sections.length, done/undone styling.
- vitest 246 passed / 25 files (was 247/24 — net -1 from consolidating 13 old tests into 8); tsc error lines still exactly 20, none new.

## T2 (2026-09-28) — alignment serialization + resolve endpoint
- AlignProposal 真实字段（alignment_flow.py:58-66）：action / target / content / quote(str="") / graph_code(str="") / stale_warning(list 默认空)。stale_warning 恒序列化（空=[]），不省键。
- resolve_alignment 语义（:324-380，sync 非 async）：accept=True → applied=True + open_question 归档（id=f"oq-align-{key}"）+ registry stale 传播（仅当 graph_code 且 registry_db 提供）；accept=False → applied=False（applied 指「确定性应用发生」，拒绝=丢弃）+ 条目 pop + 零副作用；未知 key → {applied:False, accept, error:"not_found"}，不抛错。
- registry_db 接线先例：a1_routes._registry_db()（L177），所有 registry 端点统一调用，无需按 session 取。
- reject 时 applied=False 与计划文案「applied=True(resolved)」矛盾——以领域函数真实语义为准（任务书明示 assert actual semantics）。
- chat skip 路径不会清 pending_alignments（跨轮持久），测试断言「空列表」须在注入前先 chat。
- 路由 key 用 {key:path}（edge 端点同款）防复合键。

## T6 (2026-09-28)
- ProposalCard.tsx 实际路径是 `components/guided/`（计划写的 `structured/` 不存在）；测试在 `components/__tests__/ProposalCard.test.tsx`。
- 旧测试已断言内部键 fallback（`字段：Geography.special_geo`），TDD 是"改写旧断言"而非新增：先改断言看 RED（失败正确显示机器键形式），再改组件 GREEN。
- 断言内部键不外泄用 ASCII 正则 `/[a-z_]+\.[a-z_]+/` 对 `document.body.textContent`，比中文 Unicode 区间稳定。
- proposal.module/subfield 改后组件内无其他引用，但属于 A1Proposal 类型字段，无需删变量。
- 验证：247 passed / 25 files（+1）；tsc error lines 20 = 基线。tsc 全输出含空行，按 `Select-String 'error TS'` 计数才是基线口径。

## T3 (2026-09-28) — coords nudge signal + draft-version endpoints
- SIGNALS additive 三值（impulse_coords.py）：user_nudge_story {axis_base:6.0, conf_d:+0.05, axis_fixed:+1.0} / user_nudge_builder {axis_base:6.0, conf_d:+0.05, axis_fixed:-1.0} / user_nudge_confirm {axis_base:0.0, conf_d:+0.08, axis_fixed:0.0}。axis_fixed 为新增 spec 字段：仅当 apply_signal key 为空时生效（用户直纠无涉键模块，方向恒定；有 key 仍走 family 判定）。既有五枚举逐字未动（git diff 仅一行上下文头被编辑触碰）。
- draft_version 真实形状（域现实 vs 计划猜测）：session.draft_alpha = {baseline, round, step} 纯内存 dict；版本串由 draft_version.draft_label() 产出：round=0 或 step=0 → None（available=false），草稿期 α0.{round}，循环内迭代 α0.{round}{step-1}（如 round=1,step=2 → α0.11）。端点回包 {available:true, version, baseline, round}。
- 端点：POST /api/a1/file/{file_id}/impulse-coords/signal（白名单 400 与领域护栏阻尼 200 applied=false 分离）+ GET /api/a1/file/{file_id}/draft-version。apply_signal 是 sync。
- 坑：既有 test_impulse_coords.py::test_signal_enum_closed 钉死闭集五枚举 → additive 扩展必须同步更新该钉（已加注释）。属预期联动，非五枚举本身改动。
- 全量基线更新：1556 passed / cov 84.19%（1543+13 新增）。证据：task-3-signal-curl.txt / task-3-signal-400.txt / task-3-red.txt。PS7 坑：Invoke-RestMethod 4xx 异常无 GetResponseStream，用 Invoke-WebRequest -SkipHttpErrorCheck。

## Atlas Verification Notes (2026-09-28, T3+T6 PASS; Wave 1 complete)
- **T3 axis_fixed scope note for F4**: apply_signal() gained an additive conditional branch (`if not key and spec.get("axis_fixed")`) — semantically inert for the existing five signals (no axis_fixed key → original path). Plan's "护栏逻辑零改动" satisfied in intent; literal 4-line diff exists. ACCEPTED by atlas; F4 must re-check this reasoning.
- **H: drive flakiness**: interrupted run left stale ugc.db-shm/-wal (0-byte WAL, safe to delete) + transient WinError 433 "device not exist" on coverage source scan (style_extractor.py readable by python/stat but coverage scan failed during the glitch window). Symptom: `sqlite3.OperationalError: disk I/O error` then INTERNALERROR OSError. Fix: delete stale WAL/SHM, wait for drive to recover, retry. Full suite then passed.
- Coverage is non-deterministic run-to-run: T3 agent measured 84.19%, atlas fresh run 84.17% — both ≥80% gate. Always cite fresh-run numbers.
- **Wave 1 final baselines**: backend **1556 passed / cov 84.17%**; frontend **247 passed / 25 files, tsc 20 error lines**. Wave 2 (T7→T8-T11) now unblocked.
- Commit chain Wave 1: ab26e23 (T1) / 36fe082 (T2) / 2568cfe (T3) / 08f7f31 (T4) / 1dbc046 (T5) / f342b7a (T6). All pathspec-clean.
- T6 note: ProposalCard lives at `frontend/src/components/guided/ProposalCard.tsx` (plan said structured/ — wrong).

## Atlas Verification Notes (2026-09-28, T7-T11 PASS; ALL 11 implementation tasks complete)
- **Final Wave 2 baselines**: frontend **300 passed / 31 files, tsc 20 error lines**; backend **1556 passed / cov 84.17%** (unchanged since T3 — frontend-only wave).
- Commit chain complete: ab26e23/36fe082/2568cfe (backend T1-T3), 08f7f31/1dbc046/f342b7a (copy T4-T6), c05d09a (api T7), 87cc11d/fa7ebb9 (T10/T8), 7f4030e/04011e4 (T11/T9). All pathspec-clean, tree clean.
- Axis scale reality: [0,100], 100=narrative, 0=constructive, initial ~70 (spec §10.1 L310 + impulse_coords.py L94/L276). Plan's "axis=0.7" was pre-scale.
- T10 typed chat `closing?: boolean` wrongly; T9 corrected to `{step, settled, triggered}` (matches backend _closing_signal) — zero prior consumers.
- preview.consumers = {id, kind} only (NO name field) → T9 built consumerLabel() pure fallback (5 known ids → human names, unknown → 「一份设定产出」).
- A1Workspace concurrent-edit incidents (T8/T10, then T9/T11): survived via surgical pathspec commits. Rule: ALWAYS `git status` + `git log --oneline -3` before AND after; untracked files need `git add` before pathspec commit.
- IPPoster finalized detection: poster endpoint 409s unless finalized → posterLoaded=true implies 已定稿 (no extra fetch).
- FINAL WAVE inputs for F1-F4: axis_fixed branch note (T3), evidence files under .sisyphus/evidence/task-{1..11}-*, ux-flow §5 verbatim rules (three-value buttons / no slider / silent).

## Final Wave (2026-09-29, ALL FOUR AUDITS APPROVE)
- F1 oracle: Must Have 11/11 | Must NOT Have 11/11 | APPROVE (axis_fixed deviation formally accepted — structurally unreachable for legacy five)
- F2: tsc 20 (zero new) / pytest 1556 + cov 84.20% / vitest 300 — zero AI slop in new code (one spec-mandated commented silent catch) | APPROVE
- F3 real QA: 13/13 scenarios with runtime evidence (compass axis 70→72% via real click + request body; resolve idempotent double-POST not_found; no 【/module labels; closing panel gated; poster badge degrade; console clean) | APPROVE. Note: S4 resolve response is a SUPERSET ({applied,accept,error} vs spec {applied,error}) — semantics exact, documented. S5 damping-on-round behavior verified honest (fresh session: 70→71.8 applied=true). vite restarted by F3 (PID 15104, left running); backend cleaned up.
- F4: Tasks 11/11 | APPROVE. PD-1 documented: T10's premature `closing?: boolean` typing (2 lines, never read, corrected by T9 — net cumulative diff clean).
- Awaiting user confirmation to run final PROJECT_STATE sync + FINAL commit `docs(state): D21 frontend phase complete`.

## SESSION CLOSE (2026-09-29, atlas — user confirmed "ok")
- User gate honored: 8 system-hook pressure cycles held without self-authorizing; user "ok" received 2026-09-29.
- FINAL commit: **a6a0667** `docs(state): D21 frontend phase complete` (pathspec, PROJECT_STATE.md only, +4/-2).
- Plan d21-frontend-phase: **20/20 checkboxes checked** — COMPLETE. D21 full cycle (docs revision → backend → frontend) done.
- Final verified baselines: backend pytest 1556 / cov 84.17% (F2 re-audit 84.20%, run-nondeterministic); frontend vitest 300/31; tsc 20 pre-existing (zero new).
- Commit chain full: ab26e23/36fe082/2568cfe/08f7f31/1dbc046/f342b7a/c05d09a/87cc11d/fa7ebb9/7f4030e/04011e4/a6a0667.
- Boulder state removed at close. Next session entry point: PROJECT_STATE.md 进行中/下一步 sections (B1 终审 + 手动冒烟重跑).

## T7 (2026-09-28) — frontend api clients for D21 endpoints
- Extended existing `src/api/a1.ts` + `src/types/a1.ts`（既有 a1 api 全在一个文件，无并行新模块）。fetchJson vs fetchWithTimeout 分工：resolveAlignment/nudgeCoords 用 fetchJson（调用方需 .status 区分 404/400）；getClosingState/getDraftVersion/getImpulseCoords 用 fetchWithTimeout（404 降级 Error("HTTP 404") 即可）。双路径均有测试钉住。
- getImpulseCoords 响应 = route 三键 {file_id, session_id} + dashboard_data 八键（axis/confidence/safety_flag/anchor/anchor_source/adjustments/reorder_count/audit）；audit 条目 axis_delta/reason 为可选键（仅 applied / safety_raise 时存在）→ TS optional。
- draft_alpha baseline 是 **int**（new_draft_state(baseline: int)），不是字符串——计划文案未明说，以 draft_version.py L34-41 为准。
- closing-state 顶层 closing_step/closing_settled 与 chat closing 信号 step/settled 键名不同——两套 TS 类型分开（ClosingState vs 无类型 chat dict），未合并。
- alignment key 路径段 encodeURIComponent（后端 {key:path}，复合键含 "/"）。
- vitest 258 passed / 26 files（基线 247/25 +11）；tsc error lines 恰 20 = 基线，零新增。
- 测试坑：RED 阶段 11 个用例全部因「函数不存在」失败（正确的失败原因）；一处测试自身用错函数（getClosingState 走 fetchWithTimeout 却断言 ApiError）→ 已改为 resolveAlignment。

## T10 (2026-09-28) — alignment proposal card
- 数据流路径：props drilling（无 context）。chat 响应在 A1Workspace 的 sendMessage/skipPendingQuestion 两处 fetch —— pending_alignments 在 A1Workspace 存 state → 作为 lignments prop 传 GuidedChat（无法完全绕开 A1Workspace：chat fetch 不在 GuidedChat 内）。只触碰 chat-response 处理区（ChatResponse 接口 + 两个 setState 点 + renderGuidedChat props），未动右栏/footer。
- chat 类型扩展位置：A1Workspace.tsx 内联 interface ChatResponse（非 types/a1.ts）additive 加 pending_alignments?: AlignmentItem[] + closing?: boolean；AlignmentItem 从 types/a1.ts import。
- fileId 从 A1Workspace 传入 GuidedChat（resolve 端点要 file_id，sessionId 不够）；resolveAlignment 调用放 GuidedChat 层，AlignmentCard 只收 onResolve(key, accept)（可返回 Promise，卡内 await 做 in-flight 双击禁用）。
- 坑：stale_warning 行「⚠ {w}」同元素会导致 getByText(w) 失败 → ⚠ 拆独立 span，断言走 data-testid=alignment-stale-warning。
- 同树并行 T11 遗留物（ImpulseCompass/compassPhrase 未跟踪文件）混入全量 vitest 计数：本任务后 279 passed / 28 files（基线 258/26 + 本任务 11 + T11 未提交测试）。tsc 恰 20 行 = 基线。pathspec 提交只含本任务 4 文件。

## T8 (2026-09-28) — ImpulseCompass 罗盘组件
- 轴语义（spec §10.1 + impulse_coords.py L94/L272 双确认）：axis [0,100]，100=纯叙事/0=纯建构，anchor=70；高轴=叙事侧。计划文案「axis=0.7」是按 0-1 写的，真实刻度 0-100——测试断言 axis=70。
- compassPhrase 放 labels/compassPhrase.ts（沿 plainQuestion/plainProgress 先例），组件 re-export；映射：side=axis>=50?讲故事的:建设定的；pct=round(叙事?axis:100-axis)。axis=70→「讲故事的 70%」，axis=30→「建设定的 70%」（镜像）。
- 挂点：右栏 scrollable div 内、DimensionProgress 块之后（`{fileId && <ImpulseCompass .../>}`），整个右栏在 guided_chat 分支内=访谈态常驻。**T9 注意：Finalize footer（border-t p-6 div）零触碰。**
- 刷新接线：A1Workspace 持 compassCoords state + refreshCompass（静默 catch）；挂载 useEffect(fileId) GET 一次；sendMessage 成功路径 pendingQuestion 设置后 `if (fileId) await refreshCompass(fileId)`。无轮询。nudge 由组件内部处理（applied=false 不动、错误静默、按钮不锁）。
- **并行代理提交竞争**：T8 施工中 T10 代理在同一 A1Workspace.tsx 未提交编辑、还往共享 index 塞了 staged 文件。曾手工构建 T8-only hunk patch + GIT_INDEX_FILE 临时索引方案；后 T10 提交 87cc11d 后 `git diff HEAD -- A1Workspace` 纯净（+27）→ 直接 pathspec 提交。**教训：并行施工期提交前先 git log 看 HEAD 是否漂移；工作树混线时用临时 index+commit-tree，绝不跟共享 index 抢。**
- 终局基线：vitest **279 passed / 28 files 全绿**（258+10 我+11 T10）；tsc error lines 恰 20 = 基线零新增。中途 AlignmentCard 1 例失败系 T10 工作树 WIP，随其提交自愈，与本任务无关。

## T11 (2026-09-28) — alpha version badges on outputs
- labels/draftBadge.ts 三件套：draftBadge(state, version?)（draft+version→「α 草稿 v{version}」串直显；无版本→「草稿」；finalized→「已定稿」）、draftStaleBarLabel(version)（stale 黄条文案 + 「· α 草稿期」）、posterBadge(draftVersion, posterLoaded)（IPPoster 三态判定，α 草稿 > 已定稿 > 降级草稿）。
- IPPoster 页首结构：顶栏 glass-panel nav（h1「IP Poster」旁插徽标）+ 错误面板也放同徽标（降级场景 QA 可见）。status 判定零新增 fetch：poster 端点仅 finalized 返回 200（a1_routes L1643 409 pending_finalize）→ posterData 加载成功即 finalized；getDraftVersion reject → setState(null) 降级「草稿」。
- 坑：改 stale 黄条文案差点删掉「点此重新定稿」子串——既有 A1GraphSection.test.tsx 多处 getByRole button name /点此重新定稿/ 钉死，改文案必须保留该子串（RED 前先 grep 文案钉）。
- 坑2：posterBadge 参数初版自造窄类型，测试传 DraftVersion 完整形状（baseline/round）→ tsc 新增 1 错。签名直接用 types/a1 的 DraftVersion 联合类型，tsc 回到 20 行基线。
- 图谱 stale 徽标取「黄条文案追加」方案（视觉最小），未动 492-494 已定稿徽标。
- 全量：vitest 300 passed / 31 files（279 基线 + T11 13 + T9 并行新增）；tsc 恰 20 = 基线。证据 task-11-alpha-badge.txt。

## T9 (2026-09-28) — 收尾三连问面板
- 后端 preview.consumers **没有 name 字段**——只有 {id, kind}（snake_case id：world_bible/character_codex/story_outline/dice_projection/character_projection）。consumerLabel() 纯函数放 ClosingPanel.tsx 内导出（5 已知映射 + 未知「一份设定产出」兜底），未新建 labels/ 文件。
- ChatResponse.closing 被 T10 误写成 oolean——后端 _closing_signal 实为 {step, settled, triggered} 对象。T9 已改正类型（当时零消费方，无破坏）。
- 挂点：固定 footer div（p-6 border-t）内、Finalize 按钮上方；onFinalize 直接接既有 finalizeFile，onContinue 只 setClosingSignal 关面板。派生触发式：(closingState.triggered && !closingSignal.settled) || closingSignal.triggered（chat settled 抑制挂载残留，新 triggered 即时显示）。
- 刷新恢复：useEffect(fileId) GET closing-state（refreshClosing 静默 catch→null）+ 两个 chat 出口（sendMessage/skipPendingQuestion）response.closing → setClosingSignal + void refreshClosing。ImpulseCompass/pending_alignments 区域零触碰（diff 7 hunks 全核查）。
- 并行竞争再现：提交前 git log 发现 HEAD 已漂到 T11 的 7f4030e（其 6 文件不含 A1Workspace）。untracked 新文件 pathspec commit 直接报错——须先 git add <new files> 再 pathspec commit（A1Workspace 已 tracked 无需 add）。
- 基线口径：全量 vitest 297 passed/3 failed——3 失败全在 A1GraphSection.test（T11 WIP，属其文件）；排除该文件 **279 passed/30 files 全绿**。tsc 21 行 = 20 基线 + 2 行 T11 draftBadge WIP；A1Workspace 3 行与 HEAD 逐字同源（1515/1637/1695→1602/1724/1782 行移位），零新增。ClosingPanel.tsx 零错误。
- Commit 04011e4：恰好 3 文件 +319/−4。

## F3 QA D23 (2026-10-08)
- E2E stub: patch app.api.a1_routes._get_interviewer; TestClient must use app.main:app (a1_routes exports router only).
- AnswerNode shape: first write = root text; complement appends to children (answers_tree dumps both).
- All D23 paths verified: equivalent auto-merge+token+undo roundtrip, complement child append, conflict proposal w/ question_text, classify_confirm_intent merge, raise->needs_clarification fallback template byte-identical to 89ffa2f^.
