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
