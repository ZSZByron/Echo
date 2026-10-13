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

## 2026-10-12 批C（T7）实现要点（T8 需读）——仓库已迁移至 C:\Users\Administrator\AppData\Local\Temp\opencode\UGC-recovered（原 H:\UGC 灾后弃用，代码随固化提交 2d29545 入库）

### 埋点事件名（inspiration_log.emit_event，fail-silent，T8 直接复用）
- 镜像通道双事件：`mirror_triggered`（带 turns=mirror_thread_turns+1，jsonl 契约锁定）+ `discussion_mirror`（通道级捕获，与 mirror_triggered 同点双发）。位置：guide_engine.py mirror_hit 分支（约 :1969-1977）。
- 重锚通道双事件：`reanchor_triggered`（jsonl 契约锁定，test_reanchor）+ `reanchor`（通用捕获，test_channel_matrix_v2）。位置：guide_engine.py reanchor 分支（约 :1950-1951）。

### 优先级接线点（guide_engine.py _handle_message_impl 内从高到低）
- reanchor 分支在 **规则6.5 知识冻结区之后**（:1939 起）：判定 = `result.reanchor`（LLM）or `text in REANCHOR_TRIGGER_WORDS`（显式元命令「梳理一下」，REANCHOR_TRIGGER_WORDS 集合常量 :811——LLM 已判则以 reanchor 为准，免本地文本对比占租）；进入即双清 knowledge_thread_* + _reset_mirror_thread，folds 无关、fills 零吸收、answers 零变化。
- mirror 分支在 reanchor 之后（:1961 起）：mirror_hit = result.mirror 且非 knowledge_used（知识态优先、讨论态其次）；镜像线程帽 MIRROR_THREAD_CAP=2（:808）——turns>=cap 时第 3 轮确定性桥回当前题并 _reset_mirror_thread，否则 mirror_thread_active=True + turns+=1，reply = guidance_reply + 「先回到当前的问题：{cur_question}」。
- 退出复位：用户离开讨论态（直选/重锚/其它支路命中非 mirror）→ _reset_mirror_thread（:1658，置 mirror_thread_active=False/turns=0）。

### 话术常量与话术区
- interviewer.py：InterviewResult additive 双键 `mirror: bool` / `reanchor: bool`（:119-120，delivery 先例同构）；_parse additive 解析 `raw.get("mirror"/"reanchor")`（:1040-1043）；prompt schema 提示三行（:652-660 mirror=true→fills 须空、:660 reanchor=true→guidance_reply 一句化呼应）+ JSON 示例行 :720。
- guide_engine.py：_build_reanchor_reply（:1664）五段清单拼接——「好的，我们把手上的线头捋一捋」+ 确认要点（answers 逐条）/或空答话术 + 【当前题】module.label + 灵感架素材逐条 + 四选一收束句（「先记这条 / 去掉灵感架上的某条 / 回到当前题 / 灵感架能帮我说」语义）；「已按示例记录」（:1854）原样存活（字节锁）。
- 「记下了」修复行：⑨稿第 31 行 ▶from 模板枚举行（26 模板之一），引擎侧无「记下了：」固定文案（负向保护锁定）。

### 26 模板 / 57 追问
- 六情形闭集（situation 枚举，模板逐字）：arrow_full_question / arrow_from_missing / arrow_to_missing / arrow_trigger_missing / dim_full_question / dim_direction_missing；26 = ▶20+⇄5+支线主问1；57 L3 追问候选键=followup(s)，规范短(≤60)+问句「？」结尾。

### 收尾与环境
- 全量 1789 passed / cov 84.85%（evidence wave2-t7-gate.txt）；ruff 增量交集法本批实测 app 侧 8 处——但 diff ab83518..2d29545 是灾后固化提交（批A/B 增量同入一 diff），批C 单独增量无法隔离，如实登记。
- **新仓库路径（后续任务必读）：C:\Users\Administrator\AppData\Local\Temp\opencode\UGC-recovered**；pytest 一律 `.venv\Scripts\python -m pytest`；.sisyphus/evidence/ gitignored 属正常。

## 2026-10-12 T7 收尾执行补充（零代码改动，evidence 四件 + PROJECT_STATE/learnings 登记）

### 收尾验证实测
- 六测试文件转绿：73 passed（test_channel_matrix_v2 / test_discussion_mirror / test_reanchor / test_three_tier_contract / test_delivery_intent / test_channel_coexistence_matrix）→ evidence/wave2-t7-matrix-green.txt
- 全量门禁复跑：1789 passed / 0 failed / cov 84.87%（≥80 门禁过）→ wave2-t7-gate.txt（尾部附 T7 验收面）
- T7 验收面：test_rule65_and_rule7_byte_identical 实际位于 test_delivery_intent.py，单测 -v 复跑 PASSED（-q 全量输出不显示用例名，需单跑留痕——注意点）；A1Session 五枚 additive 字段实例化默认值：material_pool=[] / list_thread_key='' / list_thread_turns=0 / mirror_thread_active=False / mirror_thread_turns=0（pydantic 模型，验证方式 = A1Session(session_id=...,user_id=...) 后 getattr，不能 __new__ 直读）
- ruff 增量核对口径修正：逐行归类（ab83518..HEAD -U0 + 行号归属新增行）优于"批C 六文件全量计数"——生产侧真实增量仅 4 条 E501（guide_engine:1217 / interviewer:50,718,720），其余 8 条为基线存量；tests 侧 12 条风格类豁免照旧 → wave2-t7-ruff.txt
- 白名单：批 C 收敛于三生产文件 + 六测试文件 + 灵感日志三件；frontend/ 区间 diff 为空 → wave2-t7-whitelist.txt

### 灾难恢复纪要（后续批次必读）
- 新仓库路径（唯一有效）：C:\Users\Administrator\AppData\Local\Temp\opencode\UGC-recovered；**H:\UGC 已损坏废弃，任何操作禁止指向**
- 灾后基线对：ab83518（远程 clone 底座）→ 2d29545（灾后重建提交，波次一+二批A/B/C 全部并入，批 C 无独立提交）
- 增量口径特例：批A/B/C 改动同处 ab83518..2d29545 单 diff，无法单独隔离批 C 增量，核对时用逐行新增行归类
- 临时脚本勿放 $TEMP 根（会被覆盖/找不到），放 C:\Users\Administrator\AppData\Local\Temp\opencode\ 下

## 2026-10-12 批D（T8 灵感架闭环）实现要点

### 引擎接线（guide_engine.py）
- 入架：_handle_message_impl 镜像分支之后/偏转之前新支路——`delivery and not fills` → _stow_delivery（帽满挤最旧，永不拒绝）+ rack_stowed 事件 + 话术（含「灵感架」）。
- 自由流程回收：fills 支路 return 前 _maybe_propose_rack_homing（候选=首条未 declined 条目；目标=suggested_slots[0]；挂 pending_proposals 键 `rack_home:{target}`，entry 带 rack_home/rack_target/rack_text）。
- resolve_proposal additive rack 分支：replace=answers[target] 直写 + pool 过滤移除 + rack_recycled 事件；drop=条目标 `declined:True`（不重复提议；不用新 A1Session 字段——_T9_SESSION_FIELDS 冻结锁禁改）。提案轮/hooks 前置：_try_rack_homing_reply 在 interviewer 之前消费「安进去/先留着」闭集短语（确定性零 LLM）。
- list_append 事件落点两处：_apply_fills 补条支路（children append）+ 首条 complement 直写支路。

### 关键裁定
- suggested_slots 走引擎侧 getattr 发现式消费（model_construct + __dict__ 注入测试，test_channel_matrix_v2 先例）——**InterviewResult 零扩容**，test_channel_coexistence_matrix/matrix_v2 两枚 frozen 键集锁零触碰。pydantic v2 model_construct 不收未知键，非字段属性须 `result.__dict__["k"]=v` 注入。
- 拒绝记忆用 pool 条目内 `declined` 标记（不用 tombstone——pending_proposals 非空会阻塞收尾双条件 is_preset_phase_complete）。
- /file GET 的 material_pool 投影 = 一行 additive（finalize 端点零改动，pool 永不进 missing_sections）。
- closing_flow.maybe_trigger 前置 _rack_inventory_line（空架返回空串，无 pool 字节不变）。

### 环境坑（Windows pwsh）
- `git show | Out-File` 会按控制台编码（GBK）解码 UTF-8 输出 → 基线副本错乱导致 ruff 计数假象（base=144 vs 实际 1）。正确姿势：`git cat-file -p ... > file`（字节直通）。
- ruff 增量口径：基线副本须以 `.py` 扩展名放仓库树内（backend/_basetmp/）跑同配置；逐文件 base vs worktree 计数比对——批D 三生产文件增量 0。

### 收尾
- 全量 1802 passed / 0 failed / cov 84.89%；evidence wave2-t8-{rack-loop,gate-unblocked,gate,whitelist}.txt。

## 2026-10-12 批E-1（T9 graphify 迁移边/衔接边 + 上传值形状联动）实现要点（T10 必读）

### 边类型常量/注册位置（T10 直接引用）
- EdgeType 枚举新增 TRANSITION="transition"（迁移边）/ LINKAGE="linkage"（衔接边）——backend/app/models/knowledge_graph.py（additive，Tree/CROSS/Semantic/Rule/Structure 零改动）。
- 词表铁律落点：transition/linkage 不入 concept_edge_vocab.VOCAB_RELATION_NAMES、不入 build_graphify_prompt（负向锚测 test_not_in_llm_prompt_vocab 锁死）。
- 确定性编译模块：backend/app/domains/creation/a1/value_shape_edges.py，入口 compile_value_shape_edges(session) -> (minted_nodes, edges, warnings)；常量 EDGE_TRANSITION/EDGE_LINKAGE；状态节点 id 方案 v:{l2_id}.{l3_id}:from|to（GraphNode level=4, serial VS{n}-1/2）。

### 装配接线点（T10 复证用）
- a1_routes._build_graph：dead_edges/assemble_warnings 写入之后、KnowledgeGraph 构造之前——compile 产出节点并入 nodes（幂等跳过已存在 id）、边端点双在图内才并、缺席落 dead_edges(reason=endpoint_missing)。
- 旧会话回归锁：无形状 fixture → compile 零产出，_build_graph to_dict sha256 = fe3545a8ef0993f590700aaedcb0f1c288b9c386e14507be554907568afb5f82（nodes=5/edges=4，固化于测试 REGRESSION_SNAPSHOT_SHA）。
- 拒绝线语义：⇄ direction=拒绝 或 magnitude=0 / ▶ from==to → visual_description 尾注「（拒绝线）」，边不丢。
- 支线卡衔接：side_link_mode(●)+side_link_point(▶) 双真值 → linkage 边 branch_card.side_link_point → story_line（概念边家族扩展）；半边不硬接。

### 上传联动（worldview_upload）
- wrap_value_shapes(answers)：vs=from_to 位点扁平键命中 A→B / 从A到B(变成/转为/变为) 正则 → {"from","to"} dict；无形状文本保持纯文本（●降级）。parse_modules 出口统一调用。
- _prefill_session：dict 值经 guide_engine.l3_value_node（新 helper，部件子节点+渲染串 text）转扁平 AnswerNode——pydantic answers: dict[str, str|AnswerNode] 类型闸要求；l3_value_parts 可读回部件。

### 未知边类型降级（s2-unknown-enum 先例）
- KnowledgeGraph.from_dict：EdgeType(...) ValueError → 跳过该边 + degraded_edge_count += 1（新字段 exclude=True，不进 to_dict——序列化字节面零扰动）。

### 门禁
- 全量 1822 passed / 0 failed / cov 84.93%（基线 1802 + 20 新增）；ruff app 增量 0（worldview_upload 仅存量 UP035）；evidence wave2-t9-{edges,regression,gate,whitelist}.txt。
- 坑：pytest 必须以 backend 为工作目录跑（仓库根跑 capture 崩）；evidence 落盘用绝对路径。

## 2026-10-13 批E-2（T10 四幕病理回归 + 存量兼容全检 + 交叉烟测）实现要点

### 范式与选型
- 端点级重放照 D23 F3 先例：TestClient + monkeypatch a1_routes._get_interviewer（_ScriptedStub 按轮弹出 InterviewResult.model_construct 配置：fills/mirror/delivery/knowledge_used，零真实 LLM）。
- 新 L3 位点（side_link_point/side_ending/success_path/failure_path）chat fills 不可达（interviewer 只产旧 35 字段平面 fills）→ 引擎直调 apply_l3_fill + l3_value_parts/read_l3_answer 断言（T5 先例一致）。

### 四幕断言面（test_wave2_pathology_replay.py，11 passed）
- 幕一：complement 补充 → 首条 text 保留 + children+1；pending_proposals=={}（非弹问）；conflict 对照组走三选一拦截。
- 幕二：side_link_point/side_ending 各自 from/to 部件承载；success_path 零污染；半填宽容。
- 幕三：双终点挂 branch_trees L2 锚下（**锚键 = L2 id "branch_trees"，不是 "剧情"**——首版断言写错被红测抓住）；双节点 sources 分流非压缩单值。
- 幕四：LIST_CAPS["key_relations"]==6 锚；×3 追加 turns 推进无提议；children>=cap-1 时 complement 帽满出口③ + equivalent 达帽出口③ 均走提议流且 list_thread 复位；直答（非 complement）出口① / 跳过出口② 复位；拦截态数据不丢。
- 镜像桥回话术实际文案是"（回到当前的问题：…）"——**无"先"字**（learnings 批C 段记录的"先回到当前的问题"与源码有出入，断言以源码为准）。

### 交叉烟测（全通道版）
- 序列：清单追加→镜像→投递入架→知识态→直选→正常追加轮；四状态机逐轮互斥断言零污染。直选复位 knowledge/mirror + options 对称消费，但**不打断 list_thread**（复位出口只有①直答/②跳过/③帽满/④话题离开四条）；knowledge 轮豁免 list_thread 复位（:2327）。

### 存量兼容全检（test_wave2_legacy_compat.py，4 passed）
- fixture 构造法：A1Session(**43旧字段).model_dump() 后手工 pop 五枚新字段（_LEGACY_43_FIELDS 逐字对照 T1 契约）→ {"version":1,"sessions":…,"files":…} 直写 autouse tmp store → _loaded=False 触发懒加载直通。
- 链路：GET file → finalize 409（missing_sections==["角色"] 手工预计算：2/6=33%≤half，recipe_modules=["角色"] 收窄门禁）→ chat 一轮 4 条无 relation ● 纯文本 fills → finalize 200 → graph 断言 edge_type 零 transition/linkage（T9 回归锁语义）→ 再序列化 model_validate 往返。
- finalize 200 在 conftest autouse provider stub 下降级纯 TREE 图，visual bg 后台线程与既有 finalize 测试同范式无害。

### 门禁
- 全量 1837 passed / 0 failed / cov 85.07%（基线 1822 + 15 新增）；两新文件 ruff 全清（I001 自动修 + ARG002 消参）；evidence 四件 wave2-t10-{pathology,legacy-e2e,gate,whitelist}.txt。


## T11 收官记录（2026-10-13）

- 终门禁五件全过：1837 passed / 0 failed / cov 85.09%（门禁 80%）；frontend 零触碰双证（git diff ab83518..HEAD 空 + tsc 0）；批 E 两文件 ruff 全清；白名单链四笔+本笔无越界。证据 wave2-t11-closeout.txt。
- 复跑经验：pytest 全量 ~98s；tsc 需 frontend 目录下 npx tsc --noEmit（npm install 201 包 ~15s，灾后 node_modules 重装可行）。
- 批 E 测试文件实际路径 tests\unit\a1\（非 tests/ 根）——ruff 增量核对注意路径。
- D26 按范式落盘：19 拍板+三自定决策+六通道全序+D21 豁免台账+LIST_CAPS cap 位点表+灾难恢复注记+契约演进两案+遗留清单+验收协议附录（三承诺三原则，波次三沿用）+E0 五事件埋点提示行。
- 两指南 Q16 只加不改：故事向 §15 后插 §16；文案逐句分析 §2.2 尾插 ⑯（Q16 原文即人话态逐字采用）。Q16 原文源 = story_modules.Q16_BRANCH_CARD。
- 收官提交一笔（治理态全量入库）；波次三不自动开工。
