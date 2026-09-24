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
