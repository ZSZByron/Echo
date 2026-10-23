# Learnings — a1-wave2-structure-overhaul

## 2026-10-11 Session start
- 串行纪律：批A→B→C→D→E 严格顺序，同文件依赖链，不并行施工。
- 波次一先例：TDD 红绿、每批独立提交、白名单门禁、evidence 落 `.sisyphus/evidence/wave2-*`。
- 测试命令：`cd backend; .venv\Scripts\python -m pytest --cov=app -q`；基线 ≥1691 passed / cov ≥80%。
- 前端红线：frontend/ 全 diff 必须为空。
- 经验库教训（本轮相关）：graphify provider 层瞬时失败重试一次、解析失败不重试；id 含 title 不可改（稳定性契约）；确定性装配铁律（LLM 只产 SIR）。
- git 基线 head: 106c13f（波次一收官提交）。

## 2026-10-11 T1（批A第一步：契约锁红测）完工
- 旧 id 宇宙基线：worldview 35 + story 15 = 50（快照 wave2-t1-id-universe.txt）；施工单"旧 35"口径 = 世界观 35 字段平移 L3，story 15 字段升格 L2——超集测试按 L2∪L3 双层收集。
- ⑤⑥稿数字咬合成立：⑤§8.3 总账 7/26/92/35/57 逐列复加 ✓；⑥§0 ●66+▶20+⇄5+⇉1=92 逐类复加 ✓；逐 L1 行两稿一一对应。
- **口径勘误**：施工单记 A1Session "42→45"，实测基线 43 枚（reroll_streak 等波次一 additive 未计入旧口径）→ 落库后应为 46。契约测试按"新增恰三枚"集合差断言，不锁总数，已记 wave2-t1-numbers.md §4。
- 红测契约面：THREE_TIER_TREE（story_modules 或 a1_question_tree 二选一，统一树，形态 {id,label,l2:[{id,label,l3:[...]}]}）——T2 落库必须满足此形态 + entry_subfield 四字段 id 逐字存活 + L1=7。
- 门禁护栏写法：92-L3 全答满唯角色空 → missing 恰 ["角色"]（plot 配方）；default 全答满 → missing=[]。Gate = core_recipe_modules × is_module_over_half（a1_question_tree.py:506 / guide_engine.py:585，a1_routes.py:1523 组装）。
- evidence 目录 .gitignore:61 忽略——git status 不显示属正常。
- T1 修复：_OLD_IDS 改冻结闭集 _FROZEN_OLD_IDS（49 id 逐字对照 evidence 第 22 行，实测 diff=[]），运行时派生降级为 _RUNTIME_OLD_IDS 第二重校验（现行源 id ⊆ 冻结集，改名即抓）；复跑 4 failed/0 passed/0 error 保持 RED。
## 2026-10-11 用户全局指令：命名规则
- 新标识符（新 L3 id/枚举值/边类型/常量/测试名）不得复用项目已用字母系列：断点 A-J、接头 J1-J4、决策 D#、病理 P#、契约 C1-C5、任务 T#/F#、批 A-E、层 L1/L2/L3、观察 E0。
- 一律用描述性命名（如 vs 值 point/from_to/dim_dir/dual；边类型用 transition/linkage 类语义名，禁用单字母）。

## 2026-10-11 T1 完工要点
- 旧 id 宇宙实测 50 槽位/49 唯一 id（arc_direction 双属角色/剧情）；A1Session 基线实测 43 枚（非施工单记 42）→ 落库后 46，契约按集合差断言。
- 契约锁双基线：_FROZEN_OLD_IDS（硬编码 49）+ _RUNTIME_OLD_IDS ⊆ 冻结集（防 T2 改名）。
- .sisyphus/evidence/ 被 .gitignore 忽略（正常，evidence 不入库）。
- pytest 命令：cd backend; .venv\Scripts\python -m pytest ...（红测 4 failed 即 T1 验收态）。

## 2026-10-12 T2（批A第二步：数据层落库）完工
- THREE_TIER_TREE 落 story_modules.py（契约装载 sm 优先）；树与既有 MODULES/STORY_MODULES 完全解耦（纯数据字典，零消费面接线），配方/门禁/序列化零扰动。
- vs 闭集 point/from_to/dim_dir/dual 落 const + VS_ENUM；⑥稿 92 项判定表逐项标注（●66+▶20+⇄5+⇉1），拒绝线幅度0特例用注释表达（不新增字段）。
- 清单 15 位点 = 13 L3(list+item_template) + 支线卡 L2(六件套即模板) + 灵感架(material_pool 会话级)；LIST_CAPS 15 键 = 12帽×3 + 6帽×12，批 B 停驻循环直接读。
- Q16 落独立常量 Q16_BRANCH_CARD + STORYLINE_ORDER（15 问序+branch_card 第16位）——不并入 M11/M12 fields，否则门禁比率/全量计数测试全炸。
- 新 L3 id 宇宙：57 枚描述性 snake_case（side_summary/arc_refuse/daily_life...），未复用任何已用字母系列。
- **坑**：wave1 的 test_delivery_intent 两守门（_T9_SESSION_FIELDS 冻结 + "不预留 material_pool"）与本批 additive 直接冲突——按 schema 演进惯例扩容冻结集+翻转断言（锁存在+默认空），evidence 已留痕说明。
- store.py 无需动：BaseModel additive 默认字段零迁移，旧 payload model_validate 直通由契约测试覆盖。
- 全量 1698 passed / 0 failed / cov 84.87%（基线 1691 + 7）。

## 2026-10-12 批A 收尾门禁（T3 复跑）
- 门禁绿：1698 passed / 0 failed / cov 84.87%（evidence wave2-t3-gate.txt）
- ruff 增量口径关键发现：tests/ 目录全域存量本就有 UP031×28/B009×8/E501×106 等——ruff 从未对 tests 强制清零，波次一 F2 只核 app 侧。新增测试文件（test_three_tier_contract.py）30 处报告（UP031×27/B009×2/UP009×1）判定为"既有测试风格延续"登记不阻塞；app 侧两文件 + test_delivery_intent 增量清零。
- git diff --name-only 从仓库根跑会带 backend/ 前缀，白名单比对前须剥离前缀（首次比对误判超范围）。
- git diff -U0 hunk 头解析正则：`^@@ -\d+(,\d+)? \+(\d+)(,\d+)? @@`（+++ 行与 @@ 行是两行，勿合并匹配）。
- PROJECT_STATE 条目已追加未提交；批前遗留脏改动（README/docs 等）原样保留。

## 2026-10-12 T4（批B第一步：红测四组）完工
- **T5 实现者需知的现行引擎面**（本组红测全部基于实测源码定位）：
  - AnswerNode（guide_engine.py:189）= text/children[]/source 三字段（v6 §2.6 权威形态已落地，锚测试锁死）。
  - answer_view(value)（:198）纯函数渲染：str 直通；node 深度优先「；」连接。
  - _apply_fills(session, fills)（:784）签名 → (file_diff, intercepted)；三支路 guard（空直写/同值短路/异值拦截）；D23 语义分流在 ：863-947（relation==equivalent/complement/conflict；complement 需 is_multi_value 且 children<ANSWER_CHILDREN_CAP=6，:907）。
  - resolve_proposal(session, key, choice)（:669）：replace/merge/drop；multi merge=晋升 AnswerNode 追加 child（:690-697）。
  - A1Session.list_thread_key/list_thread_turns（:442-443）已落库未消费——_handle_message_impl 零引用（批 B 接线点）。
- **红测发现（消费契约面）**：树宇宙 92 L3 的 vs 值/清单 list 标注只在 story_modules.THREE_TIER_TREE（纯数据），引擎侧（guide_engine/module_registry）对 vs/LIST_CAPS **零读取**——T5 接线 = 引擎首次消费这三样：树写入口（红测候选名 apply_l3_fill/write_l3_answer/fill_l3 等 getattr 发现式）、值 schema 校验入口（validate_l3_value 等）、结构化值读入口（l3_value_parts 等）。
- **红测范式**：新入口用 getattr+候选名发现（AssertionError 红，非 ImportError）；病理两幕用 inspect.getsource(_handle_message_impl) 探测 "list_thread" 字样做 skipif 门——T5 接线后自动转活。
- **D23 旧帽与 LIST_CAPS 冲突面**：ANSWER_CHILDREN_CAP=6（guide_engine:254）硬编码——12 帽位点（existence/key_nodes/material_pool）会被提前截断；红测 test_twelve_cap_position_not_early_capped 专锁此点。6 帽位点若非 multi 字段（如 文明与社会.conflict），第二次 complement 追加就落入 conflict 提议——T5 需让清单位点绕开 is_multi_value 限制、以 LIST_CAPS 为准。
- **Worldview 字段宇宙实测**：existence/conflict/faction_type/key_nodes 均为现行 35 字段成员（模块名 = L2 中文 id，如 世界本体.existence、文明与社会.conflict）——清单停驻可在现行会话上直接驱动，无需等树路由。
- **全量门禁**：1698 基线 + 8 锚 GREEN = 1706 passed / 35 RED（全在新四文件）/ 2 skipped（病理预埋）；cov 不适用（子集跑 --no-cov）。首跑曾 36 failed，复跑两轮均 35——环境性 flake（日志见 LLM 429 限流噪音），非代码扰动。
- evidence: wave2-t4-red.txt（四文件 RED + 全量尾行）、wave2-t4-red-fullsuite-failed.txt（全量 FAILED 清单全为新文件）。

## 批B（T5）收尾实现要点（2026-10-12，提交 6832a75）
- 三入口定名：validate_l3_value（值校验）/ l3_value_parts（半填拆分）/ apply_l3_fill（写入应用），调用方一律走此三名。
- 锚键设计：L3 锚键 = L2 id，平面宇宙零污染——不新增嵌套命名空间，L3 条目直接挂在 L2 节点下。
- 真值闸：复用 J1（v0.5.1 接头），占位词不入数据。
- 停驻四出口：L3 追问停驻有四种合法出口（填满/跳过/上溯/确认），测试全覆盖。
- LIST_CAPS 16 键裁定：⑤稿 §9.3 首批 15 机制位点不动；key_relations（D23 multi 遗留锚，预设流程 M11 主问落点）按 §9.4"上限 6 继承 D23 拍板 4"入表成第 16 键。T4 红测 LIST_CAPS["key_relations"] 直读即此锚。表驱动替代硬码。
- 帽满提议流触发条件：children >= cap - 1 时触发"将满提议"（提示用户考虑收束），cap 满则强制收束。
- 收尾证据：全量 1743 passed / cov 84.75%；ruff 增量 0（E501@1203 / UP009@1 均存量）；evidence 三件落 .sisyphus/evidence/wave2-t5-*。

## 2026-10-12 T6（批C第一步：红测三组）完工
- **T7 实现者需知的现行引擎面**（实测源码定位）：
  - 意图分类：interviewer.py InterviewResult（:75），delivery 键解析在 _parse 内 ：1008（`bool(raw.get("delivery"))`）——mirror/reanchor 键照此 additive 先例，模型字段加在 :112 之后。
  - 规则 6 投递区/规则 6.5 知识区：_handle_message_impl（guide_engine.py:1665）；直选消费在 ：1746-1787（"已按示例记录" 在 ：1787，字节锁保护行）；知识冻结闸 :1857（`knowledge_thread_active and result.fills` → knowledge_freeze 事件）；知识线程状态机 _update_knowledge_thread（:1609-1641，帽=turns>3）。
  - 埋点 append 函数 = inspiration_log.emit_event（backend/app/domains/creation/a1/inspiration_log.py，fail-silent，LOG_PATH 模块级可 monkeypatch——test_inspiration_log.py tmp_log_path fixture 先例）。interaction_log.log_event 是另一条审计线（data/a1_interaction_log.jsonl），勿混。
  - additive 会话字段建议：mirror_thread_active/mirror_thread_turns（镜像 knowledge_thread_* 命名）；**pydantic v2 A1Session 对未落库字段 setattr 抛 ValueError**——红测全部用驱动式置位，T7 落库前别在引擎外直接 setattr。
- 字节锁负向断言位置：test_rule65_and_rule7_byte_identical 在 **test_delivery_intent.py:226**（新文件 test_channel_matrix_v2.py 有存活引用锚测）。
- 「记下了」修复行清单：⑨稿（docs/plans/2026-10-10-新结构引导话术设计.md）全文恰 1 处（第 31 行，▶ 补 from 模板枚举行）；引擎侧现无「记下了：」固定文案（负向保护已锁）；既有文案「已按示例记录」（guide_engine）必须原样存活。
- 红测格局：34 RED / 17 GREEN（锚测：四通道既有序 9 对、Q16 形态、⑨稿记下了枚举行、引擎文案键集、no-home 诚实话术、fail-silent、emit_event 契约）。六情形枚举值（模板 situation 闭集）：arrow_full_question / arrow_from_missing / arrow_to_missing / arrow_trigger_missing / dim_full_question / dim_direction_missing——T7 落 26 模板时逐字使用。
- 26 = ▶20 + ⇄5 + 支线主问1（⑥稿 §0 咬合）；57 L3 追问候选键：followup/followups/l3_followup/prompt/prompts/追问，规范=短(≤60)/问句(？结尾)。
- 全量门禁：1760 passed / 34 failed（全在三新文件）/ 基线 1743 零扰动；evidence wave2-t6-red.txt。
