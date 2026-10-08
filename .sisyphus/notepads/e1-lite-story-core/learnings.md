# E1-Lite learnings

## 2026-09-21 T5 telemetry attachSessionId (E1-Lite)
- attachSessionId 只对 session_id === undefined 回填，changed 标志避免无谓 localStorage 重写；损坏存储容错免费复用 getImpulseTelemetry 的重置语义（内部调用即得）。
- 签名逐字锁定 `attachSessionId(sessionId: string): void` 供 T4 并行消费；导出顺序放在 exportImpulseTelemetry 之前，与文件"写操作工具"分区一致。

## 2026-09-21 E1-Lite T2 类型驱动队列（sync_position 前移式重排）
- 任务简报引用的 main_plot 文案"当前时间段里世界正在发生什么？"与树不符（那是 time_span 的问题；main_plot="当前时代的主剧情线是什么？"）——断言以 a1_question_tree.py 为准，用"!=time_span.question + id==main_plot"表达意图更稳。
- 无 profile 全量遍历序 != all_subfield_keys() 顺序：gate-aware 语义下 IP定位 3/4 过半后门禁段跳去下一模块，属 preexisting 行为；全遍历测试应断言集合相等+各一次，勿断言线性等于树序。
- 入口子字段置换（TYPE_ENTRY_SUBFIELD）必须同时作用于门禁段与 fallback 段，否则新 plot 会话（全模块 0 答门禁未达）首问仍落 time_span——抽 _module_subfield_ids 闭包统一两段遍历。
- 平行任务文件隔离：T3 正在改 interviewer.py，提交只 add 自己白名单文件。

## 2026-09-21 E1-Lite T3 语气锚点注入（interviewer.py）
- spec §5.2 锚点文案引号形态 = 直引号 U+0022（非弯引号），romance 列原文为"情感张力导向；A1 极轻量化；合规边界（§9）"，与计划转录不一致——以 spec 为权威。
- 逐字核对的可靠方法：Get-Content -Encoding UTF8 → Out-File 到临时文件 → Read 工具看；控制台直接输出中文会乱码。再核对 codepoint（data.find + hex(ord(c))）确认引号形态。
- _seed_block 是 interview/suggest_examples/forced_allocate 三处 prompt 共用的单注入点，锚点注入 _seed_block 内即三处生效，prompt 骨架 count==3 保持不变（R2 数据化差异验证手段：骨架串 count 断言）。
- suggest_examples 测试钩子：RealLLMInterviewer(provider=fake) 后直接调 suggest_examples，fake provider 的 chat_json 捕获 messages[0]["content"] 断言 prompt 内容，无需 LLM。
- pytest 基线更新：803+T1 新增 +15（T3）= 836 passed / 4 failed（preexisting test_c7_loop_e2e，无新增失败）。

## 2026-09-21 E1-Lite T4 前端 impulse 结构化上送（A1Workspace）
- A1Workspace 无既有组件测试，在 impulse __tests__ 新增 A1WorkspaceImpulseSend.test.tsx 挂全组件：stub 全局 fetch（/seeds、/session/start 捕获 init.body），localStorage 清干净保证默认落 impulse_cards 屏。
- jsdom 下 A1Workspace 种子卡无 testid，用 findByText(种子名) 定位点击；first_question: null + file: {} 即可满足 start 响应（StructuredFile 字段全可选）。
- 缺省语义实现：`...(impulse && { impulse_primary, ...(impulse.secondary ? { impulse_secondary } : {}) })`——次空时键彻底缺席而非空串。
- pendingImpulseRef 生命周期：设定侧 confirm 时存、startSession 成功回调统一清（attachSessionId 之后），天然覆盖"种子点击上送后不残留"。
- E2E 请求体断言全是 key-presence 型（toBeDefined/toBe），可选新键不破坏——改请求体前先 grep 确认无 toEqual 全等断言。

## 2026-09-22 E1-Lite T6 集成收尾
- 全量基线更新为 837 passed / 4 failed（基线 836 + 冒烟 1）；4 失败仍为 test_c7_loop_e2e preexisting，逐名核对一致。
- 冒烟测试遍历断言教训：gate-aware 语义下门禁已过模块的剩余字段会推迟到后续 pass，全字段线性单调断言必挂——正确不变量是"模块首次访问序 == 类型序 + 每字段恰好问一次 + 到达 completed"，与 T2 学习一致。
- _build_prompt(module: dict, subfield: dict, session)：module/subfield 必须传 dict（内部 .get），只有 session 用 SimpleNamespace/属性访问。
- 契约审计三查全空（contracts/ question_tree/ FINALIZE_MODULE_THRESHOLD grep）；E2E session-start body 断言复核确认全为 key-presence/点查型，无 toEqual 全等。
- 前端 vitest 本次 22 文件 231 passed（T4 新增 A1WorkspaceImpulseSend.test.tsx 后从 21 文件涨到 22，231 数不变说明 T4 学习记录的"231"是含新文件的数）。

## 收官（2026-09-22，Orchestrator）
- 计划 10/10 闭环（T1-T6 + F1-F4 全勾）；6 提交链 ba75b29..e23670d，四审全 APPROVE（证据 .sisyphus/evidence/final-*）。
- FINAL 波实效：F2 首跑被工具中断，补跑成功——中断的四审补跑是常态路径，勿因单审中断重跑全部。
- 权威链实践：计划转录的锚点文案/main_plot 问题文案与 spec §5.2/问卷树有出入时，实现取更高权威源（spec/树逐字），由 Orchestrator 亲自 Read 比对裁决（控制台乱码不可信，必须 Read 工具看 UTF-8）。
- 环境基线备忘：后端 tests/unit 837P/4F（4 失败=test_c7_loop_e2e 环境性 ModuleNotFoundError: tests.unit）+ tests.xt/test_a1_warning_ledger 收集错误，全部 bc86fb5 基线即有——E2 接手者勿误判为回归；建议环境专项修复。
- 子代理纪律残留：审查类子代理倾向把临时脚本写进仓库（backend/tmp_skeleton_check.py）——prompt 必须显式要求临时文件放 $env:TEMP，收尾时 git status 扫一遍清理。
- E2/A2 交接：①creator_profile 三字段就绪（E2 冲动坐标可直接扩展存储）②TYPE_MODULE_PRIORITY/ANCHOR_BY_TYPE 数据字典就位（E2 若做坐标驱动路由改为查表逻辑即可）③DECISION NEEDED 1/2/3 默认值已生效待产品方追认（队列口径/角色驱动序/未知枚举降级）④A2 P0 是下一站（B1 顺延裁决）。

## 2026-09-22 M0 访谈偏转 hotfix（甲计划任务 0）
- 偏转/素材两个新语义都走 InterviewResult 可选字段（deflect/story_material，Momus G10 向前兼容豁免）；_parse 内 deflect=true 时确定性清空 fills（prompt 规则之外的兜底，不信任 LLM 自律）。
- 故事型条件规则文本（3.8 素材归档 / suggest_examples 换料）用 *[...] if creator_primary in STORY_PRIMARY_TYPES else [] 内联注入——单 prompt 骨架 count==3 断言保绿（R2 验证手段沿用 T3 学习）。
- 偏转占位"（用户跳过）"必须进 _PLACEHOLDER_ANSWERS 词典（归一化剥括号后匹配"用户跳过"），否则 J1 真值闸不拦、门禁虚增——占位词典不许随意扩充的红线通过精确单行新增满足。
- handle_message 只有 A1Session 没有 file rec——open_questions 归档先落 session.open_question_archive（OpenQuestion.dump 结构化格式防裸 list 退化，C6 铁律），file 层接线留给 M1/M2。
- 假 provider 必须 async chat_json（interview 链走 asyncio.run），同步假件报"a coroutine was expected"——与 suggest_examples 测试钩子学习互补（那条只捕获 prompt 不经 asyncio.run 的路径）。
- 全量基线更新：850 passed / 4 failed（837 基线 + 新增 13；4 失败仍 preexisting test_c7_loop_e2e）。

## F3 QA D23 (2026-10-08)
- E2E stub: patch app.api.a1_routes._get_interviewer; TestClient must use app.main:app (a1_routes exports router only).
- AnswerNode shape: first write = root text; complement appends to children (answers_tree dumps both).
- All D23 paths verified: equivalent auto-merge+token+undo roundtrip, complement child append, conflict proposal w/ question_text, classify_confirm_intent merge, raise->needs_clarification fallback template byte-identical to 89ffa2f^.
