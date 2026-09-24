# 甲计划 learnings

## 2026-09-22 M0 偏转 hotfix（任务 0）实操经验
- 接手中断会话时先 `git diff` 逐行核对已落盘改动，别重读全文假设是基线——前会话 interviewer.py 含 2 处缩进错误（dict 行/类字段行多一空格）导致整文件 ImportError，pytest 报错位置在 import 链（guide_engine）而非案发文件，容易被误导。
- 偏转占位 "（用户跳过）" 要进的是 _PLACEHOLDER_ANSWERS 的**归一化形态** "用户跳过"（_truth_norm 会剥全角括号），不是原串——词典是归一化后精确匹配。
- 故事型条件规则注入用 `*( [...] if cond else [] )` 列表展开插进 prompt 行列表，单一骨架（R2）不破；设定型（creator_primary=""）输出逐字节不变由此保证。
- handle_message 新分支（deflect/素材）都要 _reset_stall_tracking，否则偏转会累积 anti-stall 计数误触发建议卡。
- 素材分支只在 fills 空时兜底（`material and not result.fills`），有 fill 走正常管线——避免 LLM 同时给两者时语义打架。
- open_question_archive 先存 A1Session（C6 dict 格式，零迁移），API 持久化接线留给 M1（a1_routes 不在本轮白名单）——白名单制下宁可留移交项不可越界改。
- 全量回归命令带 --ignore=tests/unit/a1/test_a1_warning_ledger.py；4 个 test_c7_loop_e2e 失败是 preexisting（ModuleNotFoundError: tests.unit，M1a 清债），判断"无新增失败"看计数 837+13=850 而非全绿。

## 2026-09-22 架构梳理交付（产品方指令：模块图/规范更新/详细设计四问）
- 详细设计文档 docs/plans/2026-09-22-jia-modular-architecture-design.md：§1 三张 mermaid（五层总架构/运行时时序/数据流）、§2 调用方案（注册表解析/访谈环/产出触发+依赖链/LLM 封闭清单）、§3 9+1 配方矩阵（DN6 初稿）、§4 store v2 单文件 schema、§5 图谱防乱五防线+C8/C9 建议契约
- SYSTEM_DESIGN_SPEC_v6.md 317 行：12 条继承声明（v5 章节号对照）+ 阶段词汇退役映射 + DN1-6 待裁决登记；v5/v5.1 归档动作留 G 批次
- blocker 更新：M0 done（1082d5b）；M1+ 仍等 DN1-6 裁决或放行

## 2026-09-22 M1a 环境清债（c7/xt collection 修复）
- 根因：`backend/tests/` 无 `__init__.py`，测试用 `from tests.xxx import` 绝对导入；裸 `pytest` exe 不把 cwd 进 sys.path（`python -m pytest` 会），故失败只在裸命令下复现——**复现环境债必须用与基线完全相同的调用方式**，`python -m` 侥幸绿会掩盖问题。
- 修法：pyproject `[tool.pytest.ini_options]` 加 `pythonpath = ["."]`（pytest≥7 内置，相对 rootdir），一行修掉 c7 ModuleNotFoundError: tests.unit + a1_warning_ledger/xt 的 No module named 'tests' 两个同根因错误。
- 诊断技巧：先单文件复现（可能单跑是绿的），再跑全量、再换调用方式（exe vs -m），三步定位"只在某组合下失败"的导入债。
- 新净基线：backend 下裸 pytest：tests/unit 无 ignore = 865P/0F；tests/ 全仓 = 1074P/0F/0 collection error。coverage 门禁未动，--no-cov 照用。

## 2026-09-22 治理批次（G：版本顺延 ×4 + D14）
- 治理版本顺延照旧惯例：git mv 保原文完整性 → 新建顺延号文件。特例确认：无版本号后缀的旧版（2_product-architecture.md）原地保留不移 archive，supersedes 在新文件头部注明即可。
- 2-A2-v0.2 这类被收编（而非推翻）的文档不进 archive，在 A 模块专项表标注收编去向指针。
- v6 §0.2 十二条继承声明是治理文档表述利器：声明"管线契约继续有效"可一次性覆盖 2-A1 系/store/409 族，避免逐条重述。
- D 条目追加时用行尾锚（" | 09-20 |"）做 oldString 比整行安全——D12/D13 单行超长。

## [2026-09-24] Task: M1 模块注册表底座（提交 b6a56f4）
- 双写手冲突教训：本任务执行中检测到另一并发会话对同一批文件做相同方向的编辑（a1_routes 出现重复 import 块 + 重复 start_session 配方落定块）。收尾前必须 grep 关键符号查重复块（如 `resolve_recipe_id(` 应只出现一次调用点）——测试全绿不代表无重复代码（Python 后定义覆盖前者，重复 import 无害但脏）。
- 首轮 test_module_registry 13 失败大半是 __pycache__ 陈旧字节码（中断会话遗留），清 pycache 后实况 = 2 失败。中断现场接手先清缓存再判定 RED 面。
- 配方落定语义：recipe_modules 留空 [] = default 全集（G3 存量零迁移）；start_session 只在非 default 时写 recipe_modules，unknown impulse 不报错降级（与 creator_* 先例一致）。
- graphify 配方并集经 legal_anchors 参数贯穿 validate_anchors/_endpoint_exists/apply_graphify_validation/graphify_llm 四签名，None=全集保证 default 逐字节不变；会话侧 _recipe_legal_anchors(session) = all_subfield_keys(recipe=recipe_modules)。
- 逐字节回归快照放 tests/unit/a1/baseline/m1_default_snapshot.json（module_ids/all_subfield_keys/_build_sections 结构/schema_catalog/default walk 序/graphify prompt sha256/门禁结果），随代码入库可复跑。
- C5 重锚：闭集断言（==module_ids、len==10、禁第 11 模块）改池语义（MODULE_POOL ⊆ TIER_MAP + coverage 空）+ 层值闭集 [0,6] 七层不动（DN2，翻案归 D14）。
- verify.ps1 全绿：pytest 1037 / tsc 0 / vitest 231 / 门禁 80.34%；module_registry.py 行覆盖 100%。

## [2026-09-24] Task: M2 故事模块族 + 4 故事型配方（本会话）
- 双写手现场处置：接手时发现并发会话半途工作落盘（story_modules/registry/tier/树门面 + 一份测试）。处置 = 不重写、以 plan 为准裁决冲突（M11 在前/弧光方向 id=arc_direction/unsure 入口=opening_event），改对齐测试而非推倒——两份测试文件 100/100 共存。
- graphify 逐字节回归的隐形坑：_tier_block 改迭代源（TIER_MAP.items() → module_ids()）行内容相同但**行序不同**，sha 照样变。修复 = 保持原迭代序、只滤故事族键（family=="worldview"）。凡"逐字节"断言，迭代序也是字节。
- UploadRequest 增可选 impulse_primary 实现 DN6 故事门（上传链是"新会话"入口、无 session_id 可依）——不传 = 旧行为逐字节（additive 门模式可复用）。
- 契约测试重锚五处（C5 池语义/graphify 层级表/E1 冒烟首问=剧情.核心抉择/legacy 响应键+recipe_id/队列子集改池语义）全是故事子集语义面，TestDefaultByteEquivalence 六用例零改动仍绿。
- interviewer prompt 单骨架（R2）再验证：素材桥/配方目录都是数据注入 *([...] if cond else [])，default 面零变化。
- M2 新代码覆盖：story_modules 100% / module_registry 100% / guide_engine 93%；interviewer 76% 为存量面（forced_allocate 等），不属新代码核算。


## [2026-09-24] Task: M3 A2 产出模块入池（modules/ 域 + doc 端点 + TD/TC 投影）

- **路径域裁决落定**：端点随既有 a1_routes 惯例 `/api/a1/file/{id}/doc|dice-template|character-template`，不新开 `/api/modules` 域——会话/文件/发号器/registry 全部复用 A1 基建，跨域只增耦合；资源名 = doc（D15，界面「文档输出」）。
- **双写手会话实录（本次最险）**：并发会话与本项目同时在 modules/ 与 a1_routes 落盘——对方写了 `output_modules.py`（池清单纯数据面，保留采纳）+ 一套 dict 风格端点，我方写了 pydantic 风格投影器 + 另一套端点，a1_routes 内出现**两套完整重复端点块 + 双份 import 块 + 双份 _registry_db**。处置：AST dup-symbol sweep（ast.walk 收 FunctionDef 计数）逐符号去重，采纳对方端点块（含 cst_* 约束提取进骰子 Step4、DiceRequiredError 防御性 409 兜底，设计更优），删我方 208 行重复块；测试全绿不代表无重复——收尾必须跑 AST 级 sweep，肉眼 grep 会漏。
- **Edit 工具整段替换的陷阱**：去重 import 时 oldString 跨含"单份夹心 import"的大段，newString 只留重复块之一——瞬间删掉 stale_marker/graphify/warning_ledger 等 8 个单份 import。教训：跨多符号的 import 去重，先 AST 列单份清单再动手，删后必须 `python -c "import app"` 级冒烟。
- **409 契约族接线**：draft → `pending_finalize`（沿用既有裸串 detail 风格）；角色投影缺 TD 产物 → `missing_dice_template`（S1:247 逐字）。分两层：模块层抛 `DiceRequiredError`（纯函数可测），路由层 try/except 转 409——契约语义归路由，依赖判定归域层。
- **stale 永不 409 的双信号判别**：`_graph_is_stale` = registry status==stale **或** 同 IP/stage 存在更高 (instance, version) 产物（覆盖"W1 行未标 stale 但 W2 已注册"的重定稿态）；消费即 `record_stale_usage` 留痕，仅 informational 不阻断。stale_marker 新增 `is_stale()`（additive）。
- **signal_requirements 三档闭集**：required/optional/hard（H §2.2 L174 转译）——optional=缺省+ledger 披露（骰子四步法逐级兜底），hard=前置产物依赖缺→409（角色←骰子、doc⑦⑧节←TD/TC）。键用字段级 `"{module}.{subfield}"`（S2 ★信号源地图转译），入池经 `ModuleDef.signal_requirements: dict[str,str]`（默认空 dict，worldview/story 零扰动）。
- **module_compile 免费线设计**：LLM 单点只产文案（module_fantasy + 节导语），九节树/ScopeBoundary/数值全确定性装配；provider 缺席/异常/形状不符三路都 → None → 答案原文骨架兜底 + `module_compile_degraded` ledger 条目。provider 兼容同步/异步双形态（inspect.isawaitable 分支）——conftest 的 StubLLMProvider 是 async 而测试内临时 stub 常是 sync。
- **测试基建坑**：conftest autouse `_isolated_a1_store` 每测清空 _SESSIONS/_FILES——fixture 注入式造数必须在**测试体内**调用（漏调一行 = 404 file not found，且单测隔离复现更容易误导为路由问题）；boulder 编排方已终验 1162/0 + 81.43% + tsc 0 + vitest 231。

## [2026-09-24] Task: M4a field_sources + 推断包（提交 183f87f）

- **双写手第四次现场（本次最密集）**：guide_engine/a1_routes/我方测试文件三个面同时被并发会话落盘（对方在我首次 Read 之后、Edit 期间写入）。处置复用 M3 范式：不重写、AST dup-symbol sweep 定位重复（guide_engine 双份 FIELD_SOURCES/mark/dice-apply；a1_routes 双份 _get_inference_packer + 双份端点），逐块采纳更优者删冗余。教训升级：**接手即先比对文件 mtime 与首次 Read 的行数**（1051 vs 927 行差直接暴露对方已写入），别等测试失败才发现。
- 对方设计的两处更优点直接采纳：①mark_field_source 不带真值守卫（调用点全部紧跟真值写入之后，不变式由调用结构保证，比函数内兜底更简）；②human/llm_fill 判定放在 _apply_fills 内用 direct_key（session.current_*）一次分流，比我在 handle_message 的事后 override 少一次快照。
- 现实核查记录：骰子推荐今日**不存在** answers 写入路径（derive_dice_recommendation 与 project_dice_template 均只读）——出口 4 按 task 指示落在"该路径应有的唯一定格点"= 确定性 apply_dice_recommendation 函数（J1 闸+clip+标记），无 live 端点，零行为变化。parse_modules 同理是纯函数 → upload_prefill 标记落 _prefill_session（会话构建处）。
- 推断包免费线：provider 兼容 sync/async 双形态（inspect.isawaitable，M3 先例）——conftest StubLLMProvider 是 async、测试内 stub 常 sync，两种都要能吃。J1 拦截在装包前（_filter_valid）而非 confirm 时，placeholder 永不成为提案；"绝不直写 answers"用 install 前后 answers 快照断言锚定。
- creator_confidence 用 dict[bucket,float]（bucket=creator_primary，空="unprofiled"）而非单 float：次冲动/多桶留余地，M4b 坐标观测直接复用。初始 0.5，±0.1 棘轮 [0,1]。
- test_inference_pack 路由测试坑：/session/start 必须 seed_id 或 custom_idea 二选一（400 兜底），裸 user_id 会 400 不是 200。
- verify.ps1 全绿：pytest 1191（+29）/ 81% 门禁 / tsc 0 / vitest 231；inference_pack.py 行覆盖 86%（≥85 新代码线）；三文件 AST sweep 零重复符号。


## [2026-09-24] Task: M4a field_sources 四出口 + 推断包（提交 183f87f）

- **双写手极限现场（M4a 全程双会话并发）**：RED 测试文件（test_field_sources/test_inference_pack）、inference_pack.py 模块本体、a1_routes 的 confirm 双写钩子与 field_sources 响应字段均由并发会话先行落盘——处置 = 逐件"读→采纳/对齐"而非重写：模块 API（InferencePacker(provider).build/install + apply_pack_feedback）照其契约消费；我方 _prefill_session 重复标记块删除保留其单行版；全量跑挂 + ast.parse 通过但 collection 全炸 = 对方正写到一半的瞬时态，清 pycache 重跑即消。收尾时发现对方已把我方改动一并打进同一 commit（183f87f）——git status 干净 ≠ 没干活，先查 git log 再决定是否提交。
- **"直答 human" 的现实锚定坑**：契约测试默认首模块 ≠ IP定位，现实 first_module()=IP定位.name——三个用例按假设写成"侧字段"实为当前问题字段。裁决：契约语义以 TestOutletHuman 类注释为准（当前问题字段=用户口述→human；其余 fills→llm_fill），改测试对齐现实（M2"改对齐测试"先例）。
- **置信棘轮对齐**：apply_pack_feedback 默认桶起点 0.5 vs 测试期望"一次 drop 落 0"——测试即契约，最终以测试面收敛（双写手下"谁对齐谁"的唯一裁判 = 双方都认可的 spec 条款 + 先落盘的实现读作要约）。
- field_sources 出口归属实证：直答=_apply_fills 内 cur_key 判定（非独立写点）；骰子推荐=确定性 apply_dice_recommendation 函数（无 live 端点，E1 前移时直接消费）；A1 当前不存在"骰子推荐写 answers"的既有链路（derive_dice_recommendation 纯展示）。
- 推断包 DN5 留痕：inference_pack.py = A1 域新 LLM 生产方（单生产单消费）；install 是它与 answers 间唯一许可交互面且只写 pending_proposals；G 批次契约评审清单需列入。

## [2026-09-24] Task: M4b 冲动坐标 + ai_fill 字段级 + 看门狗 + live_projection（提交 74b1c89）

- **双写手第五现场（本次最奇特）**：对方会话几乎与我同步从零实现整个 M4b——我写测试时对方已落盘同名测试文件（Write 被拒才发现）。处置 = 全面采纳对方实现（impulse_coords/watchdog 测试契约即要约），只补真空档（live_projection、接线当时尚缺）+ 撤除我方重复编辑（A1Session 双份字段/重复 import 块/冗余 helper——**发现即删，别留"无害重复"**，pydantic 双字段虽 last-wins 不炸但脏）。
- 对方自测矛盾一处：watchdog 边界 done*2 <= len 与其测试（恰好半数触发）相悖——测试即契约，改为 <（进入后半程即触发）；实测 40 新测试全绿。
- 补测试收口新代码覆盖线（85）：impulse_coords 84→98%（unknown signal fail-loud / dashboard 幂等 / output 族零轴移 / 超限留痕四用例）；live_projection 100% / watchdog 95%。
- 真空档补齐清单（接手半成品现场的排查序）：A1Session 字段（message_rounds/impulse_coords）→ 模块本体 → 接线（handle_message 轮次+watchdog 附加键 / resolve_proposal 信号 / start_session init / a1_routes pack 信号+GET 端点）→ _build_graph 装配段抽取。逐项 grep 确认存在再动手。
- verify.ps1 必须用 pwsh7 跑（& 调用），powershell5 把 UTF-8 中文当 GBK 解析直接 ParserError。终态：pytest 1244 / 82% 门禁 / tsc 0 / vitest 231，新代码 98/100/95。

## [2026-09-24] Task: M4b 冲动坐标观测 + ai_fill 字段级 + 看门狗 + live_projection（提交 74b1c89）

- **双写手第五现场（收尾形态）**：本会话全部实现完成后，并发孪生会话把我的文件整体扫进同一 commit（74b1c89，与 M4a 183f87f 同款）并另立 notepad commit。教训固化：`git add` 后 commit 报"nothing staged"≠ add 失败——先 `git log --oneline -3` 查 HEAD 是否已含你的文件，别重复提交。
- spec §10.1 锚点初值（L309）必须逐字：setting_heavy 15 / exploration 25 / character_driven 35 / philosophy 65 / plot 70 / nostalgia 75 / romance 80 / healing 85 / unsure（说不清）70；置信度起步 = 选卡 0.7 / 说不清 0.3（L310），存 A1Session.impulse_coords dict（default {} 零迁移）。
- 阻尼语义按 spec L310：有效步长 = 基准 × 置信度（低置信 → 大阻尼）；轴方向由涉键模块 family 查 MODULE_POOL 确定性得出（story→向 100，worldview→向 0，output→0），无 LLM 判定。
- maybe_reorder 达上限返回**原序副本**而非 None——幂等语义（调用方可无脑用返回值），"无未访模块"才返回 None。
- ai_fill 字段级过滤放 _apply_fills 循环顶部（seen_keys 前）；策略解析用 resolve_recipe_id(creator_primary) 而非 recipe_id——存量会话（recipe_modules 空）与落定会话两态一致；**直答豁免**（key==direct_key 不过滤）保住"留给用户"语义。
- 看门狗"后半程"判定用 done*2 < len（过半即进入后半程）——`<=` 会让恰好半数完成时不触发，与"进度过半"直觉相反。包装器模式：handle_message 原体改 _handle_message_impl，外层 +轮次 +附 watchdog 可选键——存量断言零扰动。
- _build_graph 装配段抽函数（live_projection.assemble_background_tree）逐行保形：module_summaries 参数保留 graphify 摘要路径、TIER_MAP tier 一并带走——m1_default_snapshot 逐字节回归绿即证明抽取无损。
- 新代码覆盖：impulse_coords 98% / watchdog 95% / live_projection 96%；1244/0（+53）+ tsc 0 + vitest 231。

## [2026-09-24] Task: M4c 人格卡 + 埋点三项 + sunset 接口（提交 2c21334）

- **双写手第六现场（本次最"全程贴身"）**：接手时并发会话已完成 M4c 后端主体（persona_card.py 模块+14 用例测试先行落盘），我首份 RED 测试 Write 被拒才发现。处置照 M4a/M4b 范式：全面采纳对方契约（PERSONA_NAME_PLACEHOLDER / entry_card_weight(session, base_weight) / 环境变量开关 A1_ENTRY_SUNSET_ENABLED），我方只补真空档 = additive 端点路由测试 + 收尾验证。frontend telemetry 对方也是边写我边看（schema bump 先落、三个 compute 函数 45s 后补齐）——**对方活跃期内绝不碰同一文件**，等 settle 再验证。
- 对方遗留 2 个真 bug（我修）：①浮点累计 0.7+0.1=0.7999… 与阈值 0.8 的 >= 比较失配 → 实现侧加 1e-9 容差（比改测试更保语义）；②enabled 用例漏 creator_profile_source 导致低置信起步 0.3（对方自己随即也修了，双修一致）。教训：阈值语义接口的浮点比较，容差要进实现不进测试。
- sunset 接口形态（对方设计，采纳）：entry_card_weight(session, base_weight=1.0) 默认恒返 base_weight；sunset_enabled() 读环境变量 A1_ENTRY_SUNSET_ENABLED（默认关）+ SUNSET_CONFIDENCE_THRESHOLD=0.8 + SUNSET_DECAY_FACTOR=0.5 常量齐备，本期零接线零行为变化——"只留接口"的最小忠实实现。
- telemetry v2 演进姿势：存储键 a1_telemetry_v1 **物理键名不变**，schema_version 进事件字段（1|2 联合类型），读取端版本容忍、派生指标对 v1/v2 事件都算——升级/降级都不破坏既有本地数据，v1 fixture 字面量兼容读取回归锚定。
- 人格卡免费线复核：render_persona_card(session) 单参数纯函数（签名即零 LLM 证明）、只看不判（渲染不改 answers/coords/audit）、确定性幂等。route 测试 start 门禁再踩一次：seed_id/custom_idea 二选一，裸 impulse_primary 会 400。
- 终态：verify.ps1 全绿 pytest 1260(+16) / 82% 门禁 / tsc 0 / vitest 239(+8)；a1_routes 与 persona_card AST sweep 零重复符号。plan 文件与 boulder.json 未入库（纪律）。


## [2026-09-24] Task: M4c 人格卡 + 埋点三项 + sunset 接口（提交 2c21334）

- **双写手第六现场（收尾即收编）**：我的 5 个文件在 git add 后瞬间被并发会话扫进同一 commit（2c21334，与 M4a/M4b 同款收尾形态），对方还补了一份 test_persona_card_route.py——`git status` 干净 ≠ 没干活，先 `git log --show-stat` 再决定动作（M4b 教训三连命中）。
- **锚点初值浮点陷阱**：0.7 + 0.1 = 0.7999… < 0.8，置信阈值比较必须带 1e-9 容差（impulse_coords 信号表 ±0.1 步长的必然后果）——任何"累加浮点达阈值"断言都要么容差要么换阈值。
- s.Low-start 陷阱：creator_profile_source 缺省 → 置信 0.3 起步且冷却轮挡二次调整，测试里凑高置信必须显式传 source="impulse_cards"（0.7 起步 + 一次 pack_applied 到位）。
- 前端 schema 升版模式：物理存储键 a1_telemetry_v1 不动，版本在事件字段内演进；读取端本就 cast 容差，v1 兼容读取回归 = 直接塞 v1 payload 断言解析。派生指标（skip_rate/completion/mismatch_map）做成纯函数吃事件数组，对版本无门槛。
- 人格卡 = 确定性投影（creator_profile + impulse_coords 查表/阈值/模板），零 LLM；命名 "ECHO 创作人格" 为未决③占位常量，终名归产品；sunset 只留接口（A1_ENTRY_SUNSET_ENABLED 默认关）+ 默认关闭态本身是测试断言。
- 终态：pytest 1260/0（+16）/ 82% 门禁 / tsc 0 / vitest 239（+8）；persona_card.py 行覆盖 91%；AST sweep 零重复符号。

## [2026-09-24] Task: G 治理四件（D14 扩展 + spec v1.3 + A2 归档头 + B1 提案）

- **D14 已存在（09-22 立），按"扩展不重复"追加实施回写**：用行尾锚（"...待产品方追认 | 09-22 |"）做 oldString 安全插入——与 09-22 惯例一致。回写结构 = 三红线实施结果（DN1 门禁子集/DN2 tier 10→16/契约 v1.3+枚举）+ D12/D13/D15 处置注记（收编实施非推翻）+ DN3 占位 + DN5 生产方三处留痕。
- **"A2 两规格 v0.1/v0.2"实为 S1/S2**：docs/plans/2026-09-17-a2-stage-design-spec.md（S1，P0-P3 版）+ 2026-09-17-a2-stage-handoff-and-design-spec.md（S2，v0/v0.5/v1 版）——证据文件 a2-plan-mining-a2-specs.md 头部明确标注 S1/S2，任务卡里的"v0.1/v0.2"指两文件各自版本号标题（都是 v0.1）。治理目录的 2-A2-v0.2 是另一份愿景稿，不在收编头范围。
- **spec v1.3 = 增量版新文件**（2026-09-18-impulse-entry-system-spec-v1.3.md）：沿用 v5.1 增量补丁范式——只重述 §5.2（配方表）与 §8（模块上线序），其余章节声明"按 v1.2 有效"，避免 447 行全文誊抄。原 v1.2 文件零改动（头注本版仍未标 superseded——按台账元规则翻案认新版文件，原版不动）。
- A2 归档头用 callout 式 `> [!ARCHIVED-ABSORBED]` 单块置顶，原文零改动；权威证据 = a2-plan-mining-*（完整版），jia-mining-* = 中断残版，注记里写明。
- B1 提案关键点：翻案生效途径 = 产品方在台账改写 B1 条目（元规则 2），提案文档只提案不生效。
- PROJECT_STATE 本批模板：当前阶段加第六批段 + 甲计划施工日汇总段（七提交链+覆盖率轨迹），进行中改为"F 待审"，遗留问题顶部加 DN1-6 状态行（默认值生效待终审措辞，不能写成"已裁决"）。

## G 治理批次（2026-09-24）
- 治理文档状态先行核查：会话开始时 decision-log D14 行已被前序会话原地扩展（未提交），G 批次实际剩余工作 = 修失配 wikilink（D14 引用的 spec-v1.3 新文件链改为同文件原地升版链）+ spec v1.3 + A2 归档头 + B1 提案 + PROJECT_STATE。教训：接手前先 git diff，别信任务描述的"从零做"假设。
- impulse spec 版本惯例 = 同文件原地升版 + §0 变更记录（自身头注成文），与治理文档"新版本顺延号新建文件"不同。D14 行引用升版结果时必须链原文件名，否则制造断链。
- PROJECT_STATE 多会话并行追加时"当前阶段"易重复：先查已完成区是否已有本批条目，新"当前阶段"条目只写状态摘要 + 指针，不重复 commit 清单。
- A2 归档头只加注记不改原文；两规格身份以证据文件 a2-plan-mining-a2-specs.md 的 S1/S2 标注为准（非 governance/2-A2-v0.2）。

## [2026-09-24] Task: G 和解批（twin 遗留合并，提交 0f4ad2e）

- **twin 本次抢先 commit（a58f57a）而非只留工作区**——原地 spec v1.3 + twin B1 + PROJECT_STATE +1 + 双方 notepad 追加全部入其提交。和解 = 在其上新建提交（禁 amend），逐文件定向恢复：`git checkout 2788b9e -- <file>` 还原 v1.2 原文与 PROJECT_STATE，`git rm` twin B1。
- **坑：`git checkout -- <file>` 只还原到 index 不还原到 HEAD**——twin 曾把部分文件 staged，必须先 `git reset HEAD -- <paths>` 再看 worktree 真实差异，否则误判"已还原"。
- **配方矩阵代码核验全过**：twin §5.2.1 表五行与 module_registry.py RECIPES 逐字一致（plot/unsure = 剧情→角色→历史时间线→世界本体→设定边界，entry core_dilemma/opening_event；romance = 角色→IP定位→剧情→历史时间线→视觉设计→设定边界 + ai_fill_exclude 文明与社会.faction_type；character_driven 七模块 entry 角色.identity；default 全集；nostalgia/healing 原序全集）。零修正并入 v1.3 文件 §5.2.2，设计约束注（DN6 保序子集/plot·unsure 剔文明与社会/M10 永远在场）随迁。
- B1 去重：twin 三个独有要点（default 逐字节回归前置 / 时点=四审后终审前 / DN 改判联动条款）并入权威版后删 twin 文件。终态 git status = 仅计划文件改 + boulder.json untracked，符合验收。

## F2 Code Quality Review (2026-09-24, HEAD 0f4ad2e)
- verdict APPROVE, 0 blockers, 6 nits (see review output). Snapshot regression = sha256(graphify_prompt) + gate anchors in test_module_registry.py:320-332.
- Pyright strict noise pre-exists repo-wide (interviewer/concept_edge_extractor); new-code errors are TypedDict-invariance/Optional-strictness only, runtime-safe.
- _prefill_session returns _session key popped by both call sites — pattern to not copy.

## F1 Remediation (2026-09-24, m1a-baseline-20260924)
- MODULE_POOL 入池硬约束：module_registry.py 对每个池条目取 `TIER_MAP[m['id']]`——新增池 id 必须同步在 tier_map.py TIER_MAP 加键（闭集 [0,6]），否则 collection 期 KeyError。本次 5 个新产出 id 均沿用上游消费源 tier 值，零新层级语义。
- D18 缓期模式与 DN defaults 同构：池注册先行（数据三键 id/label/signal_requirements）+ 生成管线/路由语义变更缓期 + "待产品方终审追认"。plan 文件只追加 "（D18 缓期）" 标记，不动复选框。
- TDD RED 先改测试（八件池断言 + OUTPUT_MODULE_IDS 序锁定 + 档位闭集校验），确认 2 failed 后再补数据，40/40 绿。
