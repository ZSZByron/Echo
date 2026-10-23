
## P3 红测（T2）发现 — 2026-10-10

- **stale 根因精确机制**：guide_engine.py:1344-1388 直选硬匹配中，cur_key = session.current_module.current_subfield（当前题）与 session.current_options（上一轮 _attach_default_options L1566 轮末写入的 examples 快照）两来源解耦。主 fills 路径先 sync_position（L1506）推进到下一问、后 attach options——LLM 在上一题语境下生成的 examples 被挂到**下一题**轮末；下一轮用户回 "3" 即把上一题的选项写入当前题 answers 键。
- **病理构造要点（测试侧）**：
  - 键空间：角色.arc_direction / 角色.character_visual 是 M11 相邻两问（story_modules.py:156/163）；ll_subfield_keys() 只含 10 模块问卷树 35 键，**不含故事模块族**（角色/剧情在 MODULE_POOL 不在 _MODULE_ORDER）——预填需补 STORY_MODULES 键，否则 sync_position 找不到未答字段 → phase=completed → 选项被清、场景失真。
  - 配方：默认会话（creator_primary=""、recipe_modules 空）walk 只有 10 树模块，**永不走访 角色**——必须设 creator_primary="plot" + ecipe_modules=["剧情","角色"]（RECIPES['plot'].module_ids 序）。
  - 唯一让 character_visual 成为 sync 落点的办法 = 预填其余全部字段（48 键）。
  - RED 实证：幕一后 current=(角色,character_visual)、current_options=弧光 3 选项；幕二 "3" → nswers["角色.character_visual"] == "原谅自己并重新相信亲密关系"（陈旧弧光选项 3 跨题写入），phase 随即 completed。
- **越界序号现状**："0"/"4"（超出 len(current_options)）不进直选分支（L1351 边界），走 interview 文本路径——已锁定 GREEN。
- **stale 会话容忍现状**：A1Session.model_validate 带残留 current_options 恢复正常；chat 轮末无新 examples → _attach_default_options else 分支清空（安全降级零痕迹）——已锁定 GREEN。
- **测试文件**：	ests/unit/a1/test_option_cross_question.py（未并入 test_option_forward.py——后者是方向A一期 T1 契约全绿锁定件，本文件是 T3 转绿判据，独立成文件便于红/绿分离与白名单提交）。

## P3 修复（T3 GREEN）要点 — 2026-10-10

- **方案选择**：options_key 绑定戳（A1Session 新字段，default 空串零迁移，G3 先例）。备选「推进时清空」会废掉契约11/14 的无死路意图；「attach 时序前移」动主流程面太大。绑定戳最小改动且可表达「这批 options 属于哪一题」。
- **绑定语义**：_attach_default_options 写入 options 时同步打戳 options_key=bound_key=turn-start cur_key（sync_position 推进**前**的题——即 LLM 生成 examples 的语境题）；直选分支加门 options_key in ("", cur_key)：绑定且 ≠ 当前题 → 序号不消费，落 interview 文本路径。空戳 = 直设/旧版存量 → 放行（保契约8 直设 pick 兼容）。
- **清空对称**：attach 两条清空路径、deflect/story_material 白名单路径、直选消费后均同步复位 options_key=空串。reroll 成功分支补一行 options_key=cur_key（reroll 产物=当前题新选项，否则跨题残留下 reroll 后合法 pick 会被误拒；streak/cap/stall 语义零动）。
- **digest 语义修正**：option_pick 的 options_digest 修复后必然记录当前题 options（绑定门放行者只有空戳/当前题两种）。
- **兼容性实证**：旧版序列化（无 options_key）model_validate 恢复保真、options_key=空串；自由文本轮轮末清空残留 → 后续 "3" 走文本路径零误填（evidence wave1-t3-legacy-session.txt）。残余风险：恢复后**首轮即 "3"** 空戳放行仍会消费（与旧行为一致，未恶化）。
- **疑因(b)**：规则 8.6 示例与当前题脱钩（examples 面向生成语境题而非消费题）已存档 wave1-t3-cause-b.txt，归 T10。若 T10 改 prompt 面向 next_question 出例，引擎绑定戳无需再动。
- **验证**：1630 passed / 0 failed（基线 1627+3），cov 84.83%；ruff 增量零（858 E501 为存量）；提交 aa9b1d3 白名单仅 guide_engine.py。

## T5 前置验证要点 — 2026-10-10

- **50/50 一致**：④稿 before 原文与代码逐字符串比对，故事 15（SM）+ 世界观 35（QT）全部定位无不一致；example 代码统一带「如：」前缀，判一致口径已写入 mapping.md。
- **severity 三联动确认**：QT:349（枚举，backend/app 零 import 消费方）+ QT:212-213（key_nodes hint）+ test_question_tree.py:145（锁测试）；graphify/semantic_compiler grep 零命中 → key_nodes 去 severity 安全。world.py:18/29 是六维遗留字段文档，无关。backend/_bq3.py 等 3 个生成脚本有重复 SEVERITY_VALUES（实际在 backend/ 非仓库根），遗留不动。
- **快照不含文案**：m1_default_snapshot.json（4370B）实测无 question/hint 键——文案改写不破 default 配方逐字节快照；高危面只剩 prompt 快照类测试（test_story_outline.py:99 等），归 T8 全量门禁。
- **动态平移 4 字段**：acquire/cost/key_nodes/main_plot 最终问句以⑨稿动态模板为准（④稿为过渡版），T6 施工时需核⑨稿是否已拍板。
- 证据：wave1-t5-mapping.md（50 题映射+契约锁盘点）+ wave1-t5-severity.txt。

## T6 施工要点 — 2026-10-10

- 15 问替换按 T5 行号逐行施工，全部与④稿 §2 after 逐字一致；例句「如：」前缀按代码惯例补齐（④稿口径）。
- 守门测试新立 tests/unit/a1/test_story_modules_copy_rewrite.py（3 用例：15 问 q/h/e 逐字 + multi 锁 + 三宇宙分布断言），防漏改/多改。
- 验证：替换前基线 101 passed（story_modules/m2/d23 三件）；替换后全量 **1633 passed / 0 failed / cov 84.83%**（1630 基线 + 3 守门，零新失败——附录 B prompt 快照类锁未被打破）。
- 红线复核：multi: True 原位（SM key_relations）/ 键名·结构·label 零改动 / 例句宇宙无迁移（林澈2/守夜人1/仙侠2）/ ⑬例去「执行者=」表单腔。
- 提交 6e14d71（白名单 pathspec：story_modules.py + 守门测试），证据 wave1-t6-diff.txt + wave1-t6-universes.txt。
- 注记：工作区既有 README/docs 修改未触碰未带入；Add-Content 写中文默认编码在部分终端出乱码——证据文件改用 write 工具落 UTF-8。

## T7 施工要点 — 2026-10-10

- 35 问按 T5 行号逐行施工：红 13 + 黄 21 替换、绿 1（keywords）字节未动（evidence wave1-t7-keywords-unchanged.txt：git diff 关键词零命中 + 守门 test_keywords_byte_identical）。
- severity 三联动：QT:349 枚举删 / QT:212-213 hint 随④稿重写 / test_question_tree.py:145 锁测试改 TestSeverityRemoved 两断言（枚举不存在 + 全 copy 无 severity/COSMIC 字样）。Select-String backend\app 零命中（evidence wave1-t7-severity-clean.txt）。
- 守门测试新立 tests/unit/a1/test_question_tree_copy_rewrite.py（39 用例：EXPECTED_34 逐字参数化 + coverage=34 断言 + keywords 字节锁 + severity 三断言 + 10模块35键结构锁）。
- 预期内打破并同批修复：m1_default_snapshot.json 的 schema_catalog 键**含 question 文案**（T5"快照不含文案"判定有误——不含的是 default walk 相关键，schema_catalog 是文案快照）→ 按快照重生成流程更新，git diff 仅该键 2 行（indent=1，重生成时勿改缩进否则 diff 116 行）。
- 全量回归：1673 passed / 0 failed / cov 84.83%（基线 1633 + 39 守门 + 1 severity 净增）。
- 工程坑三连：①edit 工具写 \u201c 转义进 py 源码是字面反斜杠序列，运行时才变弯引号——④稿实为 ASCII 直引号(char 34)，逐字校验须比对源文件字节非目验；②④稿 hint 中 **强调** 记号是文稿排版，落码为纯文本；③ruff E501 按 CJK 宽度=2 计（~45 个汉字/行超 100），长 hint 须隐式拼接折行（T6 后新惯例）；④ruff panic "wrong package cache" = 缓存损坏非代码问题，ruff clean 即愈。
- 口径留档：例句尾单句号去（key_nodes 多分句例保留句内标点）；引号沿用④稿 ASCII 直引号；例"如："前缀按 T5 口径。
- 提交 9d1427a 白名单 4 文件：a1_question_tree.py + test_question_tree.py + 守门测试 + m1_default_snapshot.json（快照重生成属 MUST DO"预期内更新"项，白名单扩展已核对）。
- 观察项（④稿外不改，记二期）：④稿直引号在前端 UI 展示无衬线，是否换中文弯引号属产品拍板；黄/红 hint 多处超 ruff 行宽被迫折行，二期改文案时注意。

## T8 施工要点 — 2026-10-10

- **文档 before 与代码现状出入**：④稿 L328 before「用户的初始创意：{种子}。我将围绕它引导你展开世界观。」中后一句在 backend 全域施工前即零命中（疑似仅前端 A1Workspace.tsx L647 同源文案 = 波次三）；后端唯一开场拼接点 = interviewer.py _seed_block 自定义创意行（原 L457）。grep 验收「旧语零命中」天然满足，已留痕。
- 替换后文本用隐式拼接折行三段（T7 后惯例），\\n 用转义序列落源码（运行时真实换行），守门测试逐字断言含种子插值。
- 守门测试 test_seed_opening_rewrite.py 3 用例：全文断言 / 旧语负向断言 / 种子预设行字节不动锁（防误伤波次三前端同源行）。
- 全量 1676 passed / 0 failed / cov 84.82%（基线 1673 + 3，零新失败）；prompt 快照类未被打破。
- 提交白名单：interviewer.py + test_seed_opening_rewrite.py。

## T10 施工要点（投递改写）— 2026-10-11

- **规则 6 改写**：「引回主题」→「接住-归位-回题」三步（接住确认/归位落既有槽+delivery=true/回题=落位确认或桥接句式+温和回题），离题闲聊分支并入规则 6 末段（"第6条"引用语义保持，规则 6.5/7 一字节未动——prompt 侧两条隐式拼接单行被 test_rule65_and_rule7_byte_identical 逐字节冻结 + git diff 双重核验）。
- **prompt 结构坑**：interviewer prompt 规则块大量使用 Python 隐式字符串拼接——源码多行 = prompt 单行。行级断言测试必须按 prompt 实际行（拼接后）冻结，不能按源码行。
- **投递意图键**：InterviewResult.delivery（additive 布尔默认 False，D24 knowledge_used 先例），_parse 直透传、无引擎侧兜底改写；JSON 模板补 "delivery": false。**键空间坑**：测试投递落点必须用问卷树 35 键（IP定位.concept），故事模块族（剧情/角色）不在 all_subfield_keys() 默认全集会被静默丢弃。
- **疑因(b) 核正**：8.6 追加「示例只服务于【当前问题】——序号仅对当前题示例有效」，与引擎 options_key 绑定戳互补（prompt+引擎双闸）。
- **通道优先级锁**：直选（引擎侧先消费，interview 零调用）> 6.5（二段式）> 投递 > 答当前；"3" 直选不受投递拦截由 engine 级用例锁定。
- **零 schema**：A1Session 42 字段冻结集断言 + material_pool 负向断言；ruff --statistics 改动前后完全一致（12 存量）。
- 验证：1687 passed / 0 failed / cov 84.87%（基线 1676 + 11）。证据 wave1-t10-delivery.txt / nohome.txt / dormant.md。休眠 4 式话术存档于 dormant.md（波次二激活时同步改 test_dormant_phrases_absent_from_code）。

## T11 回归护栏要点 — 2026-10-11

- T10 盘点：42 字段冻结、delivery 解析 additive、直选不被投递拦截、6.5>投递优先级均已锁——本任务不重复，只补缺口：①InterviewResult 键集 additive 锁（既有 12 键 + delivery，T10 只锁行为未锁键集）②同会话四通道交错矩阵。
- 共存矩阵关键语义实证：知识态下 delivery=true 携带 fills 照样被冻结闸丢弃（投递不是冻结豁免牌）；投递轮 fill 落位后引擎 sync_position 正常推进（投递不改/不锁答题位置，但当前位置 ≠ 轮前当前题——测试断言要按轮后位置锚定直选键）；腕带两幕重放后投递正常且知识态不复燃（freeze 事件全程仅 1 次）。
- 验证：全量 1691 passed / 0 failed / cov 84.82%（基线 1687 + 4 新增）。D24 四用例逐 node id 全绿、P3 病理 3 用例全绿。证据 wave1-t11-d24-regression.txt / wave1-t11-matrix.txt。
- 提交白名单：tests/unit/a1/test_channel_coexistence_matrix.py（仅此一个新文件）。

## T12 收官要点 — 2026-10-11

- 终门禁亲自复跑：1691 passed / 0 failed / cov 84.82%（84s），Tee-Object 落盘 evidence（pwsh 7 默认 utf8NoBOM，中文零乱码）。
- ruff 增量核对法：全文件存量错误（interviewer.py 12 个）逐个对 1.3 diff hunk 新行范围——命中行若是上下文行（无 + 前缀）即存量，本批增量 = 0。
- D25 编号顺延：grep 确认最大 D24 → D25；台账行格式（| D25 | 内容 | 日期 |）+ frontmatter updated 同步。
- 提交 106c13f 白名单三文件（decision-log / PROJECT_STATE / docs/README），7 插入 2 删除；工作区前批遗留（根 README / HUB / governance/*）未触碰。
- 真机冒烟指引落 evidence wave1-t12-smoke-guide.md（非阻塞）：重启后端 → 离题想法验证接住-归位-回题 → 直选不被干扰 → 记录体感。
- 波次一全链终态：1627（T1 基线）→ 1691（收官），净增 64 用例；波次二 17 项待拍不自动开工。
