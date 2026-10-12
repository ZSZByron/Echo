# Learnings
- Workspace: D20 in-flight (16 red/18 green baseline). guide_engine.py + interviewer.py modified, test_dynamic_invites.py untracked. 09-26 doc batch UNCOMMITTED - never touch.
- venv: backend/.venv/Scripts/python.exe. Test runner: cd backend; .venv\Scripts\python.exe -m pytest.
- HEAD: 055da41. Committed baseline 1264 tests.

## 2026-09-28 Task3: D20⑤ prompt 键域冲突（设定边界.）
- 根因：_build_prompt 的【不可动清单】标题硬编码「设定边界.不可变集」，半角句点构成 "{mid}." 形态，被 G5 liveness 断言（module_ids() 全闭集 × {mid}. not in prompt）捕获。
- 修复模式（选项a）：prompt 硬编码文案中引用模块 id 时一律用「」括注（「设定边界」），绝不写 模块id. 形态——G5 断言是按字面子串匹配，全角冒号（目录行 {mid}：）安全，半角句点是唯一雷区。
- 排查捷径：先跑红测试看断言输出的实际冲突子串，再 grep 该子串定位唯一产生行；WORLDVIEW_DOMAIN_CATALOG 注入块本身是干净的（全角冒号）。
- 并行任务感知：guide_engine.py 接线任务与本任务并行时，invite 相关红测会随对方收敛自动转绿（观察期约几分钟）——不要越界去修对方的文件。

## 2026-09-28 D20 提议消费接线（task-1）
- 接线点：_handle_message_impl 的 interviewer.interview() 之后，全部 5 条返回路径（deflect/material/innovation/fills/chat）都要消费 result.worldview_invites 并追加 _invite_notice(accepted) 披露，只改 reply 字符串、不动结构键。
- 关键顺序坑：_apply_worldview_invites 内的 _reset_stall_tracking 必须发生在 _apply_stall_guard 之后，否则 chat/fills 分支的 stall guard 会立刻把 stall_subfield/stall_count 重新写上（test_invite_resets_stall_tracking 抓的就是这个）——deflect 分支例外（_handle_deflection 尾部自带 reset）。
- 披露文案追加先例沿用 ai_fill_excluded 模式；拦截（write guard）覆盖 reply 后再追加 notice，诚实可观测不丢失。
- 结果：16red/18green → 3red/31green；剩余 3 红全部是 D20 #8 gate-type（progress()/finalize 仍遍历含 invited 的全 recipe_modules，归并行任务，本任务禁改 progress()）。

## Task 2: D20 门禁排除接线 (progress + finalize)
- 接法：guide_engine.progress() 的 finalizable 与 a1_routes.finalize 的 missing_sections 均改用 core_recipe_modules(session)（recipe_modules - invited）；sections/missing 之外 UI 渲染仍走全 walk。
- core_recipe_modules 对空 recipe_modules（存量/default 会话）退化为 module_ids()，invited 恒空 → 行为与 HEAD 逐字节一致（m1_default_snapshot 类回归全绿，807 passed tests/unit/a1/）。
- FINALIZE_MODULE_THRESHOLD / is_module_over_half 语义未动。
- 陷阱：progress() 的 ordered 同时喂 sections 渲染和 finalizable——只把 finalizable 的 recipe 参数换成 core，勿动 ordered，否则 _build_sections-includes-invited（G5/TestLivePropagation）会红。

## 2026-09-28 Task4 D20 汇合提交
- 全量回归 1298 passed（82.12% 覆盖率门禁过）；单文件跑 test_dynamic_invites 34 passed，cov FAIL 行为已知现象，判定看测试结果行。
- ⚠ 关键教训：commit 会吞掉 index 中**预先 staged** 的改动。本仓库 index 里遗留了 4 个 staged 的 docs 重命名（R 状态），首次 commit 混成 7 files。修正流程：soft reset → 全 unstage → 精确 add 白名单 → 重提交（d8e16ad，恰好 3 files）→ git add -A 恢复原 staged 状态。
- 下次提交前必查：git status --short 第一列非空（已 staged）的非目标项，先 git reset 再精确 add。
- Evidence: .sisyphus/evidence/task-4-commit-proof.txt

## 2026-09-28 task-8: StageCode B/C/O (D22③)
- TDD 流程顺利：5 个 BCO 测试先红（AttributeError/AssertionError，因枚举缺失），仅加枚举成员即全绿——issuer 的 non-S 分支对任意枚举值通用，零逻辑改动。
- C(人物志) ≠ TC(角色投影模板) 语义区分已写入枚举 docstring（D22 明确要求）。
- 前端无 StageCode 字母枚举副本（git grep exit 1），无需前端同步；证据在 task-8-letter-grep-list.md。
- pathspec commit（git commit -- <files>）成功绕开 index 中 4 个 staged docs 重命名，git show --stat HEAD 确认恰好 2 files。PS 环境下 GIT_MASTER=1 前缀命令报错，改用 $env:GIT_MASTER='1' 传环境变量。
- 注意：StageCode 字母名新成员为 BIBLE/CODEX/OUTLINE（W=WORKING 先例，非单字母属性名），value 保持单/双字母。

## Task 5 persona_card 清理 (2026-09-28)
- 删壳留本体落地：删除 persona_card.py、test_persona_card.py、/persona-card 端点（a1_routes.py L1064-1077）+ 局部 import；impulse_coords.py 与 /impulse-coords 零触碰。
- 额外发现：tests/unit/a1/test_persona_card_route.py 是 /persona-card 端点的契约测试（内容 grep "persona_card" 零命中——因文件内只出现 "persona-card" URL 字符串），首次全量 a1 回归时暴露为 FAILED。教训：残留扫描要用宽 pattern（如 "persona"）补一遍，避免 hyphen/snake 变体漏网。
- 回归结果：tests/unit/a1/ 791 passed；-k impulse 41 passed；-k "impulse_coords or coords" 34 passed。
- a1_routes.py 中 D20 finalize gate 未提交改动段未受扰动。

## 2026-09-28 Task7 D22 产出池注册
- 三件（world_bible/character_codex/story_outline）全 optional 入 OUTPUT_MODULES；OUTPUT_MODULE_IDS 由 tuple 生成式自动扩为 11，get_output_module 无需改动。
- ⚠ 约束冲突实录：module_registry 入池写死 tier=TIER_MAP[m["id"]]，新 id 必然 KeyError——"只改 output_modules+测试" 与 "MODULE_POOL lookup works" 不可兼得；最小越界 = tier_map.py 加 3 行（复用既有层值，world_bible→6 / character_codex→2 / story_outline→3）。后续同类注册任务应把 tier_map.py 预先列入白名单。
- 既有闭集测试（test_output_module_ids_order_locked / test_eight_output_modules_in_pool）是逐字元组断言，追加条目必须同步更新，否则 GREEN 被旧断言卡死。
- 回归基线：tests/unit 1149 passed / 0 failed；覆盖率 79.77% 略低于 80% 门禁（-0.23%），归因并行在飞改动（a1_routes/graph_code_issuer/persona_card 删除），D22 三文件为纯数据且被 48 个定向测试全覆盖。
- Evidence: .sisyphus/evidence/task-7-pool-registration.txt + task-7-pool-regression.txt


## 2026-09-28 Task6 closing_gate（共享地基 T10/T18）
- 新模块 backend/app/domains/creation/a1/closing_gate.py：is_preset_phase_complete = phase==PHASE_COMPLETED（问题树走查态，sync_position 置位）AND len(pending_proposals)==0。auto fills（FIELD_SOURCE 直写/空字段 Branch1/prefill 豁免）从不进 pending——语义天然不阻塞收尾，只有 write-guard Branch3 冲突提案阻塞。
- build_output_preview(file_id) 纯拼装：module_coverage（core_recipe_modules + module_done_ratio 真值化）+ gaps + version_chain + stale 双信号（registry status / 同 IP 同 stage 更高 (inst,ver)，口径对齐 _graph_is_stale，查询失败降级不阻断）+ CONSUMER_ARTIFACTS 常量（world_bible/character_codex/story_outline d22 排前 + dice/character_projection trpg）。零 LLM 零权重，排序归 T10。
- 测试注入设计：build_output_preview 关键字参数 sessions/files/registry_db 可注入纯 fixture；缺省时延迟 import a1_routes 的 _SESSIONS/_FILES/_registry_db（调用时导入避免循环）。
- **存储真相（T10 必读）**：a1_routes 是 hybrid——_SESSIONS/_FILES 内存 dict 为写透缓存，A1Store 才是真相源：每次变更 _save_store()（30+ 调用点），启动 _STORE.load() 回载。「改天继续」持久化可用。
- TDD 双收获：测试先抓到 ①畸形 graph_code "IP0001-W1-vX" 使 version_chain int() 崩溃（已 guard）②未知 recipe module 泄入 coverage（progress() 同款 continue 口径修复）。
- 新测试文件不加 --no-cov 会触发 repo 级 80% 全局 cov 阈值误报（18.13%），已知存量问题，非新失败。
- 坑：PowerShell 管道 Select-String 输出中文 mojibake——判断内容用行号+结构，必要时 [Console]::OutputEncoding=UTF8。

## 2026-09-28 Task11 world_bible (D22① 五件套模具复用)
- 模具逐字平移顺利：NINE→SIX 章 BIBLE_CHAPTER_HEADINGS / _CHAPTER_SIGNALS / bible_compile_copy / _skeleton_chapter_body / compile_world_bible 全部镜像 main_module 同名结构，零新装配模式。
- 语义差异裁决：provider is None（零 key 免费线）**不算** degraded（对齐 main_module），只有 provider 存在但失败才发 world_bible_degraded——测试 test_provider_none_is_not_degraded 锁定。
- 缺料披露新增 doc.empty_chapters 字段（main_module 无此先例）：逐章独立降级 world_bible_empty_chapters 条目列出留空章名，结构性不编造可断言。
- B 信签发：compile_world_bible 加 issuer/user_id/ip 可选参数，传入则 issuer.next(stage="B") 覆盖 graph_code——不强制注入，端点层（T18）决定。
- 并行 lane 噪音基线：test_story_outline.py（模块缺失 collection error）/ test_character_codex.py / test_recipe_switch.py 3 失败均与本 lane 零引用关系，回归判定用 --ignore 排除对方文件。
- 结果：20/20 green，world_bible.py 覆盖率 96%（≥85 门禁），Evidence task-11-world-bible.txt + task-11-empty-degrade.txt。

## 2026-09-28 Task13: D22 故事大纲渲染器（O）
- story_outline.py 完全镜像 main_module.py 五件套模具（冻结节树 STORY_SECTIONS 六节=剧情.* 信号域 / SECTION_SIGNALS 与 T7 注册逐字一致由测试锁定 / compile_copy copy-only 失败→None / compile_outline 骨架直投+降级披露 story_outline_degraded / render_markdown 溯源行）。issue_outline_code 薄封装 issuer.next(stage="O")。
- 模具语义坑（测试侧踩过）：copy 契约中 sections 缺失/非 dict → 归一为 {}，lead_in 有效即成功（main_module 同款）——bad-shape 参数化不要把 {"lead_in":"x"} 算失败；无 provider 调 compile_* 必然 degraded，要 ledger 断言而非 []。
- 全量回归 6 failed 全在他人 lane 文件（test_recipe_switch 4 + test_character_codex 2，均 untracked 非本任务产物）；本 lane 15/15 green，模块覆盖率 92%。
- ⚠ 并行会话期间禁止 git stash --include-untracked（会一并藏走并行 lane 的 untracked 文件，本次已安全 pop 恢复，git status 复核无丢失）。验证"失败是否存量"改用只读方式而非 stash。
- Evidence: task-13-story-outline.txt + task-13-empty-degrade.txt

## T14 graph_digest 重建（2026-09-28）
- 测试 patch graph_digest.lookup_graph_json（模块属性）→ interviewer 必须以模块引用调用（rom ... import graph_digest + graph_digest.lookup(...)），from-import 直接绑定名会绕过 patch——D20 注入模式接线时牢记。
- lookup_graph_json 用惰性导入 rom app.api import a1_routes（函数体内）反查 _FILES，避免 routes→interviewer 模块级导入环；请求期执行安全。
- 键域消毒一招制敌：digest 渲染文本全部 . -> ·，裸 {mid}. 断言天然全绿；节点 id 绝不渲染（只渲染 description/标题/子字段中文标签）。
- G5 键域契约的作用域是「注入块内」：prompt 的可填字段清单（_field_catalog）按 M2 设计必须裸露 module.subfield 填充键（dynamic_invites:302 after_invite 依赖）——对整个 prompt 断言无裸键与 G5 liveness 矛盾，已按白名单微调 test_graph_digest 断言作用域至 BEGIN..END 块并记录理由。
- Python 文件全 null 字节损坏（中断写入）：直接删除重建即可，pytest 收集报错与 LSP 均能立刻暴露。

## T10 收尾三连问状态机修复（2026-09-28）
- advance_answer 契约：返回值 = 人话回复文案（非原始语义串）；interject 直接消费，勿二次调 _after_answer。
- Q1「继续」判定必须用显式整句短语集（frozenset 精确匹配），子串匹配会把「继续聊聊主角」这类自由流内容误判为显式选择、覆盖访谈回复——竞态非阻塞语义的根因。
- creator_line 三线闭合映射放在 closing_flow 本地（module_registry 只导出 STORY_PRIMARY_TYPES，不含设定五型）；setting={setting_heavy,philosophy,exploration,nostalgia,healing}。
- 回归基线：tests/unit/a1/ 全绿 939 passed（closing_flow 35/35）。
- 教训：收尾文案 _after_answer(generate_doc) 只点名人话件名（世界圣经/人物志/故事大纲）+ doc 端点，不含 story_outline 等内部 id（TestQuestionCopy 契约）。

## T9/T12 验收证据补全（2026-09-28）
- T9 test_recipe_switch.py：16 passed / 0 failed；五组契约（联合边界含重叠去重 / 切换已访不重复+未访前移 R6 / 单冲动零回归六场景 / D20 invited / API 端点）全绿，五组均有直接对应用例，无缺口。start 双冲动落定实现在 a1_routes.py L646-686（次冲动校验+去重追加）。
- 小坑：test_recipe_switch.py 模块 docstring 提「default 会话 409」，实际断言为 400（test_switch_matches_snapshot_registry），以断言为准，注释级不一致，未改实现。
- T12 test_character_codex.py：18 passed / 0 failed；character_codex.py 覆盖率 92%（≥85%）；五组契约（正常编译/空信号降级/半空独立降级/LLM 失败降级/章节树冻结）+ 小说化 prompt 快照（_CODEX_COMPILE_PROMPT 含「小说化」「不得改写或复述信号原文中的事实」）+ LLM 不改写原话断言（test_llm_never_rewrites_quoted_facts）均核实存在且全绿。
- 证据文件：.sisyphus/evidence/task-9-recipe-switch.txt、task-9-start-api.txt、task-12-character-codex.txt、task-12-empty-degrade.txt。本任务零实现代码改动。

## T15 α 版本体系（draft_version，2026-09-28）
- 新模块 a1/draft_version.py：纯函数 + dict 状态（baseline/round/step），α 标记纯内存，结构性杜绝落库。finalize_version 只做内存记账（baseline+1），发码仍由 issuer 现行 next() 完成——本模块零调用零改动 issuer。
- 标记规则：round 内 step1 = α0.{round}，step k>1 = α0.{round}{k-1}（α0.1→α0.11/α0.12；第二轮 α0.2→α0.21/α0.22）。**坑：finalize 只清 step 保留 round**——复位 round 会让第二轮草稿重回 α0.1；draft_label 判定须 round>0 AND step>0 双条件。
- version_label additive ×4 文档模型（ModuleDocument/BibleDocument/CharacterCodex/StoryOutlineDocument，default None 零迁移）；三态测试：α 期有标 / 定稿 None / 存量 payload 缺字段 model_validate 直通。
- A1Session.draft_alpha additive 字段落在 guide_engine.py（MUST DO 覆盖白名单，仅字段+import）。
- 红测两连抓：finalize round 复位 bug、draft_label 收口后残留——TDD RED 先行再次证明值回票价。
- 回归：tests/unit/a1/+tests/unit = 1326 passed 0 failed；-k 过滤 18 passed。证据 task-15-alpha-version.txt / task-15-no-persistence.txt。

## T16 alignment_flow（2026-09-28）
- 模具完全镜像 inference_pack：SyncStubProvider + propose(chat_json 单调用) + validate_raw_proposals（唯一闸门）+ install（pending_alignments additive 容器）+ resolve（accept 应用/decline 零副作用/not_found 幂等兜底）。
- 键域雷区重演：render_proposal 出不裸 "d:"/"{mid}."——节点 id 绝不渲染，target 只出 title/description 摘引 + "d:" 兜底替换为 "条目·"。
- stale 预警 = 只读查 graph_registry（parent_graph_code 反查 children，alignment_flow 本地 sqlite3 只读查询，不改 stale_marker.py——白名单互斥）；应用路径才复用 mark_downstream_stale。
- 全量回归陷阱重演：tests/unit/a1/ 首跑 1 failed（test_draft_version，T15 并行 lane untracked 文件 mid-write 竞态），单跑 18 passed，复跑全量 974 passed 0 failed——并行期单红先单跑该文件再复跑全量，勿误判。
- -k "align" 会额外命中 test_align 相关既有测试（18 = 17 新 + 1 既有），判定看新文件 17/17。
- Evidence: task-16-align-actions.txt + task-16-no-llm-write.txt

## 2026-09-28 T17 对齐触发时机 + 同帧定序（先对齐后收尾）
- 接线点复用 T10 轮末钩子位置：_handle_message_impl 顶部捕获 pre_module + provider = getattr(interviewer, "_provider", None)（FakeInterviewer 无此属性 → None → 守门零 LLM，T10 既有 35 测试零扰动）；fills/chat 两条尾部收尾钩子统一换成 _round_end_signals。
- 轻量检测 = alignment_hit_terms（节点标题 × 输入的纯字符串交集，零 LLM）；实体词选 title 不选 description（长文本子串误命中）。
- ⚠ AlignmentProposer.propose 在 graph 无效时早退且不调 chat_json——深对齐测试必须挂 graph_json，否则 calls==0 假绿。
- ⚠ sync_position 门禁感知路由（pass1 优先 gate-failing 模块）：首模块答过半（is_module_over_half）后任何一轮都会跳下一模块——"模块内普通 fill 轮"造不出来，非边界轮测试改用 chat 分支（无 fills 指针不动）。
- A1Session 是 pydantic 模型，测试挂 graph_json 用 object.__setattr__（lookup_graph_json 的 getattr 直读路径）。
- 定序显式化：ROUND_SIGNAL_ORDER = ("alignment","closing") 常量 + 测试断言；pending 时收尾延后=跳过 closing hook（advance 也冻结至 resolve），reply 追加 _alignment_notice（render_proposal 复用，键域消毒兜底）。
- 回归: tests/unit/a1/ 988 passed（974 基线 + 14 新）；-k "align and (trigger or ordering or timing)" 14 passed。
- Evidence: .sisyphus/evidence/task-17-trigger-ordering.txt + task-17-zero-llm.txt

## 2026-09-28 T18 D22 三对端点（八步范式接线）
- 八步范式抽了三个本地 helper（_d22_provider / _d22_stale_and_code / _d22_store_and_respond）复刻 doc 端点 Step 顺序——三对端点零逻辑重复；persist 键 world_bible/character_codex/story_outline（additive），响应键 bible_code/codex_code/outline_code。
- 三渲染器签名差异：只有 compile_world_bible 自带 issuer/user_id/ip 可选参；端点层统一做法是在端点里 issuer.next(stage=...) 发号再传 graph_code（不注入 issuer），三件范式完全一致，也覆盖了 codex/outline 无 issuer 参的缺口。
- 空图谱 session 三 POST 均 200：world_bible 披露 world_bible_empty_chapters（答案空 → 六章全留空），codex/outline 披露 *_degraded（provider None 也算 degraded，与 world_bible 的"provider None 不算 degraded"语义不同——披露断言按件分派）。
- closing_flow 预览无需改：closing_gate.CONSUMER_ARTIFACTS T10 已含三件 d22 条目，build_output_preview consumers 直接透出——T18 零收口改动。
- 回归：tests/unit/a1/ 1006 passed（988 基线 + 18 新）；-k 过滤 56 passed。Evidence: task-18-endpoints.txt + task-18-issuance.txt

## T18 (D22 三对端点) — 2026-09-28
- 八步范式抽公共件：`_d22_provider()` / `_d22_stale_and_code(rec, session, stage)` / `_d22_store_and_respond(rec, key, code_key, ...)`——三对端点各 ~15 行，零逻辑重复；后续若有第四件照此抽。
- 发号统一在端点层 `issuer.next(stage=...)`（doc 同范式）；`compile_world_bible` 虽支持 issuer=/user_id=/ip= 内部签发，端点未用——保持三件形状一致。
- 渲染器签名差异：`compile_codex(character_name=...)` 无 issuer 参数；`compile_outline` 有独立 `issue_outline_code` helper——端点一律直调 issuer.next 即可，不必用 helper。
- `_render_*_md` 命名：三渲染器各自导出 `render_markdown`，import 处 alias 防撞 main_module 同名。
- 并发残留注意：a1_routes.py 在会话中途从 2496 行长到 2677 行（前任中断工作实际落盘）——动手前先重新确认文件长度/既有实现，"零进展"情报不可尽信。
- closing_gate CONSUMER_ARTIFACTS id（world_bible/character_codex/story_outline）与端点路径 kebab-case（world-bible/…）对应关系是约定映射，无需代码收口。
- 验证：-k 三词 56 passed；tests/unit/a1/ 1006 passed（基线 988 + 18 新）。

## T19 字母终审（2026-09-28）
- pathspec 提交（git commit -m ... -- <paths>）在 index 有 4 个 docs R 预 staged 时表现完美：只提交 pathspec 内路径，归档重命名原样留在 index，零泄漏——先例如实复现。
- git grep 的中文 pattern 从 PowerShell 传参易编码失败（输出空），改用 Select-String -Encoding UTF8 可靠；证据文件同理用 Set-Content -Encoding UTF8。
- D22 三产物端点依赖 a1_routes 进程内 _SESSIONS/_FILES + issuer DB 全局变量，活栈 curl 无法 HTTP 造 finalized 态；冒烟用「uvicorn 8901 + curl 健康检查」证活栈 + TestClient 脚本做发号断言（IP0001-B1-v1/C1-v1/O1-v1 全 PASS），任务书允许此等效方式。
- from_str 错误消息动态生成（join 枚举值），枚举扩展零改错——判定"无需改"的关键证据模式。
- 全量 pytest 基线实测 1502 passed / cov 83.49%，84s。

## T19 字母终审 + 治理同步（2026-09-28）
- 双会话并行竞态实录：本任务被并行执行——证据文件（task-19-letter-audit.md / audit-verify.txt）已由孪生会话先落盘，冒烟脚本临时文件也被覆写（同路径 t19_smoke.py 内容变更 + 固定 tmp 库触发 UNIQUE 约束）。处置：读后采纳不覆写、证据互补（本会话补 task-19-docs-sync.txt / task-19-smoke.txt / task-19-pytest.txt / task-19-commit-proof.txt）。教训：发现文件已存在先 Read 采纳，同任务竞态以「零重复提交」优先。
- 冒烟链路要点：D22 三端点 GET 导出 = 同路径 + ?format=json 查询参（D15 doc 范式，无 .md/.json 后缀路由）；_d22_store_and_respond 存储键 = {key}（world_bible 等），码键 = bible_code/codex_code/outline_code（非 graph_code）；_get_file 返回 _FILES 原对象，断言应读 a1_routes._FILES 而非本地引用。
- 全量回归：1502 passed / 0 failed（84s，cov 83.49%）；冒烟 12/12 PASS（IP0001-B1/C1/O1-v1 三段全链）。
- 治理同步最终形态：spec 升 v6.2 dated amendment（L244 注 + L316 变更行，v6.1 旧文零动）；decision-log D22 行尾〔施工注记 2026-09-28〕追加式；HUB/README/0_index-v0.7 补记三处；前端手册零字母引用（无同步面）。
- 提交链：5d34253 代码笔（29 files，含 persona_card 删除三件）+ ce5334a 文档笔（5 files：v6/decision-log/HUB/README/0_index-v0.7）；两笔 pathspec 白名单干净，index 遗留 4 个 staged docs 重命名未混入（git show --stat 核验）。PROJECT_STATE.md 未入库（T20 管，文档笔 message 中「PROJECT_STATE sync」字样与实际文件清单不符——实况以 stat 为准）。
- Evidence: task-19-letter-audit.md / task-19-audit-verify.txt / task-19-docs-sync.txt / task-19-smoke.txt / task-19-pytest.txt / task-19-commit-proof.txt

## T20 PROJECT_STATE finalization (2026-09-28)
- Measured baseline drifted from T19 note: fresh full pytest = 1502 passed / cov 83.52% (T19 recorded 83.49%). Coverage is non-deterministic across runs (83.49 vs 83.52) - always use the fresh run's number, never copy from earlier notes.
- Four-section update pattern: current stage gets dense batch entry (commit chain inline); completed gets one summary bullet; in-progress rewritten as next phase pointer (frontend stage, docs/前端手册.md §8); next-step line 92 swapped backend->frontend while historical note line 91 left untouched (per "do not modify historical entries" rule).
- Evidence: .sisyphus/evidence/task-20-state-consistency.txt (numbers cross-checked vs fresh pytest output).
- Commit: pathspec discipline (`-- PROJECT_STATE.md`) leaves the 4 staged docs renames in index untouched.

## T20 (PROJECT_STATE 收尾, 2026-09-28)
- 前任实际已完成闭环: PROJECT_STATE 同步提交 = d029941 "docs(state): D21 backend phase complete - PROJECT_STATE sync" (2026-09-28 20:10:13, 恰 1 文件 +26/-7)。会话内 git log 最初仍显示 ce5334a 为 HEAD, 复查时 d029941 已落——并发会话/被中断会话可能在观察间隙提交, 结论前必须以实时 git status/log 为准。
- 四节核对: 当前阶段(链 d8e16ad→8992239→5d34253→ce5334a)/进行中(前端指针 docs/前端手册.md §8)/下一步(B1+DN1/DN2+⭐) 全部在案, 无缺口无重复, 零文字改动。
- 实测复跑: 全量 pytest 1502 passed / cov 83.52% / 门禁 80% 通过——与文中数字逐字一致 (T19 口径 83.49% 略旧, 文中已是 83.52% 实测值, 未改)。
- 证据: .sisyphus/evidence/task-20-state-consistency.txt。注意: 用 bash here-string + Set-Content 写中文会因控制台编码变 mojibake, 证据文件改用 write 工具写入。
- pathspec 纪律: index 中 4 个 docs 重命名预 staged + 根 README.md 等属 09-26 文档批遗留, 本批零触碰; 因提交已存在, 未产生任何新提交。

## F2 终审整改（2026-09-28）
- 接手时发现前次被中断的整改已落盘（ruff UP009/I001/UP037/SIM118/ARG001 + a1_routes 全部 import 移至模块语句前）——动手前先 git status + git diff --stat 盘点工作区，避免重复劳动（T20 竞态先例重演，本次直接采纳续作）。
- 覆盖率补测口径：term-missing 定位缺口行 → 测真实分支（lookup 三路径/畸形载荷/降级分支），不做凑数断言。graph_digest 84→100%（+10 测试）、alignment_flow 81→99%（+19 测试）。
- 坑：.coverage 数据文件损坏（"no such table: tracer"）→ 删 .coverage 后复跑即恢复；单文件 --cov 触发 repo 级 80% fail-under 误报为已知现象，判定看模块行数字 + passed 行。
- mypy strict 整改最小手法：`-> dict | None` 补 `[str, Any]`、Any 返回值显式中转注解、mypy 收窄用 assert（恒真分支）；--follow-imports=skip 会把 pydantic 变 Any 产生 "Class cannot subclass BaseModel" 伪影，判定要用正常 follow + 文件名过滤。numpy stubs 在 py3.11 口径下报 syntax error → CLI 覆盖 --python-version 3.12。
- ruff 基线对比方法：git worktree add 到 HEAD 再跑 --statistics（当前 vs 基线逐类别对比），残留类别必须逐一在基线中存在才算零新增。
- pathspec 提交第三次成功复现：commit ae3848b 恰 28 files（backend/app 9 + backend/tests 19），index 4 个 docs staged 零泄漏。
- 全量：1531 passed / cov 84.03%（基线 1502 → +29 新测试，零回归）。
- Evidence: .sisyphus/evidence/final-f2-remediation.txt

## F2 REJECT 修复（2026-09-28）
- Ruff 基线对比法：git worktree add @5d34253^ 后用同一 venv ruff 跑两份 concise 输出，按 (file, rule) 二元组集合差判「新增违规」——基线 159 → 修复后 136，新增集为空。行号漂移不影响判定。
- a1_routes import 区重排三要点：① 新插入的 d22 三件 import 移入头部按路径排序 ② TIER_MAP F401 删前必须 grep 全文件确认唯一出现 ③ logger = logging.getLogger(...) 挪到 import 块之后，E402 18→0。
- ruff --fix I001 会把 `render_markdown as _render_codex_md` 这类别名 import 拆成独立 from 语句（合法但丑），手rap合并回单块后再复查 I001 是否复现。
- closing_flow._after_answer 的 session 参数是状态机统一签名约定（调用点恒传），ARG001 用行内 noqa 保位而非改名——改名会破坏调用方。
- 覆盖率竞态实录：F2 证据里 graph_digest 84%/alignment 81%，本会话实测 per-file 已 100%/99%——并行会话已在两测试文件落 F2 补测块（+113/+212 行）。发现「expected outcome 似乎已完成」时先 grep 测试文件里 "F2 补测" 标记，勿盲目重复写测试。
- 同任务竞态处置重演：本会话 lint 修复落工作区后，并行会话将其连同自己的补测一并提交为 ae3848b（恰 28 files 全 backend/，docs staged 重命名未吞）——git log 实时复核 + git show --stat 核验后放弃重复提交，仅独立复测取证（1531 passed / cov 84.01% / 新增违规 0）。
- 注意：pytest-cov 全局门禁跑单测文件必 FAIL（repo 级 80% vs 单文件 19%）属已知现象，判定看测试 passed 行与 --cov 指定模块的行。

## 2026-09-28 Session Close (atlas)
- Plan d21-backend-phase COMPLETE: 24/24 top-level checked, F1-F4 all APPROVE.
- Final baseline: 1531 passed / 0 failed, cov 84.04% (gate 80). Commit chain: d8e16ad / 8992239 / 5d34253 / ce5334a / d029941 / ae3848b.
- Environment lesson: high-parallel sync dispatches (4-6 concurrent) get interrupted; single or 2-parallel dispatches survive; interrupted tasks often completed their work anyway - ALWAYS survey filesystem/git/evidence state before re-dispatching.

## F3 QA D23 (2026-10-08)
- E2E stub: patch app.api.a1_routes._get_interviewer; TestClient must use app.main:app (a1_routes exports router only).
- AnswerNode shape: first write = root text; complement appends to children (answers_tree dumps both).
- All D23 paths verified: equivalent auto-merge+token+undo roundtrip, complement child append, conflict proposal w/ question_text, classify_confirm_intent merge, raise->needs_clarification fallback template byte-identical to 89ffa2f^.
