# Draft: D21 后端阶段工作计划

## 规划目标（初步）
根据 PROJECT_STATE「进行中」节，为 D21 施工期·后端阶段制定工作计划，候选范围四件：
1. D20 动态模块调用补完（在途 TDD 半成品：test_dynamic_invites 16 红/18 绿，六层缺口=提议消费/游走插入/门禁排除/prompt 目录/键域传播/审计事件；产品方裁决 B=随 D21 后端阶段补完再提交）
2. persona_card.py 清理（清单已定：删整文件 → 摘除 a1_routes.py 的 /persona-card 端点+import → 删对应测试 → 保留 impulse_coords.py + /impulse-coords）
3. 主次配方切换 / 收尾触发双条件 / 对齐循环（问题七）实现
4. D22 通用投影三件（世界圣经/人物志/故事大纲注册产出池，全 optional 档；新发号字母施工时定）

随后为前端阶段（说人话文案整改 + 四组件）——范围待与产品方确认。

## Requirements (confirmed)
- 【产品方已答 2026-09-28】**范围 = A 仅后端阶段**：①D20 动态模块调用补完（六层缺口）②persona_card.py 清理 ③主次配方切换 / 收尾双条件 / 对齐循环（问题七）实现 ④D22 通用投影三件。前端阶段（说人话文案整改+四组件）**排除**，另行规划。
- 【产品方已答 2026-09-28】**测试策略 = TDD**：契约测试先行，16 个红灯测试即 D20 的 RED 基线；延续甲计划纪律（pytest 全绿 + 甲新代码覆盖率 ≥85%）。
- 施工顺序权威 = D21⑭ + PROJECT_STATE：D20 补完 → persona_card 清理 → 主次切换/收尾/对齐循环 + D22（同批）。
- 治理纪律随行：治理登记（D20 提交前补齐——已补记；对齐循环 DN5 第四处扩点评审随施工）、每批结束更新 PROJECT_STATE。

## Technical Decisions
- （待研究+采访）

## Research Findings
### 已核实（决策台账逐字，docs/decision-log.md L37-39）
- **D20 动态模块调用六设计要点**：①LLM 提议（访谈结果可选键）+ 确定性校验（引擎单点消费，LLM 绝不直写状态）②可调用模块=世界建构族闭集（故事/产出模块永不可被调用）③每会话上限 4 个④插入点=当前模块之后⑤门禁零强制（受邀模块不进必答清单）⑥全程披露通知+审计留痕。与 D19 不冲突（D19 管配方静态构成，D20 管配方内动态邀约）。
- **D21 后端相关裁决项**：⑦主次配方结合切换=主∪次联合边界 session/start 一次落定，切换=联合边界内未访序调整（D13 三杠杆第一条兼容，v6.1 注记）；⑧收尾双条件=配方问完+fills 待确认清零 → 可生成物预览（数据源=输出前**确定性图谱识别**：覆盖/缺口/版本/stale 纯代码盘点）→「生成文档/继续访谈录入设定」；三连问=输出成果/AI 补充/改天继续（**同会话持久化**承载）；⑫人格卡划除=删壳留本体（impulse_coords.py + /impulse-coords 完整保留；persona_card.py 寄生的入口单选 sunset 接口连带清理）；⑬对齐循环=会话内「编译→对齐→继续」循环，对齐目标 W/M/S 三图谱，四动作提案（关联/去重/矛盾/更新）+用户确认（推断包交互复用）+stale 影响预警，LLM 绝不直写图谱，阶段性草稿编译复用 D15③ α-β 版本递进，输出物 α 版本可见标记；图谱摘要注入访谈=新 LLM 消费路径（**随施工治理扩点评审**，DN5 第四处）。
- **D22 通用投影三件**：世界圣经（Markdown 设定集）/人物志（角色数据小说化渲染）/故事大纲（剧情信号叙事化渲染）；signal_requirements **全 optional 档**（薄图谱照出、缺料走缺省+ledger 披露、不 409）；渲染器=主模组五件套模具复用（冻结结构模板+信号键绑定+确定性装配+LLM 只叠导语层〔失败降级确定性骨架，免费线可跑通〕+缺料留空诚实不编造）；新发号字母随 D15 字母体系延伸（**具体字母施工时定**）；入口承诺按卡+收尾预览按动机排序（通用投影排前、跑团件标「进阶可用」）；施工=D21 后端阶段（**D20 补完之后，与主次切换/收尾三连问同批**）。
- **D15 发号现状**：W=世界图（L1）/ M=模组产物图族（L2，含 TD/TC/R）/ S=场景图（L3，不停发）。
- **施工顺序（D21⑭ + PROJECT_STATE）**：文档修订（已完成）→ 后端 → 前端。后端 = D20 补完 → persona_card 清理 → 主次切换/收尾触发/对齐循环 + D22 三件。
- 后端测试基线：1264/1264 全绿（D19 落地时），甲计划新代码覆盖率 ≥85 条款，全局门禁 80。
- 台账未决项：外测员姓名（⛔ D7 前置）、产品总名终裁、CRT Demo 杀/留——均不阻塞后端施工。

### 研究代理返回（2026-09-28 三路同步重发后全部成功）

**路一 · D20 在途现状（16红/18绿实测复核）**：
- 根因高度集中：`_apply_worldview_invites`（guide_engine.py:338-385）完整实现但 `_handle_message_impl`（guide_engine.py:930-1147）**零调用**——单一接线点可转绿约 12 个红测试（消费+游走+审计+键域传播连锁）。
- 独立缺口仅两处：③门禁接线（progress guide_engine.py:1146 与 finalize a1_routes.py:1280-1283 未用已实现的 `core_recipe_modules` guide_engine.py:327）；⑤prompt 键域冲突（test_before_invite_zero_worldview_fields 红——D20 域目录注入后 prompt 含 `f"{mid}."` 型子串，需在 interviewer.py:384-530 逐行排查，唯一需先调查再动手的层）。
- 3 个「碰巧绿」测试（unknown_id_dropped / invited_incomplete_still_finalizable / invited_placeholder_never_satisfies_gate）接线后才变真验证，须纳入回归。
- 施工序建议：T1 消费接线（最大杠杆）→ T2 门禁接线 → T3 prompt 键域排查 → T4 全量回归。

**路二 · 三项新机制**：
- **①主次切换**：spec v1.3 §5.4 L67 权威原文；StartRequest 双字段 a1_routes.py:205-211 已有；start 落定只按 primary（L672-676 resolve_recipe_id）；creator_secondary 三处引用（声明 guide_engine.py:177 / 写 a1_routes.py:647 / 读 :666）零路由确认。空白 = 主∪次联合 module_ids 有序集 + 切换机制（端点或 chat 信号重排未访序）。
- **②收尾双条件**：fills 待确认 = `session.pending_proposals`（guide_engine.py:190-201），清零判定 ≈ len==0（须区分 auto fills 语义 L201/L430-431）；确定性图谱识别函数需新建（可拼装 module_done_ratio a1_question_tree.py:465-494 + stale_marker.py 现成件）；空白 = 访谈循环内收尾触发检测点 + 三连问端点/状态机 + 图谱识别函数。
- **③对齐循环**：interviewer 现状不读图谱（验证）；图谱摘要来源 = _FILES[file_id]["graph_json"]（a1_routes.py:688/L1400）+ stale_marker registry；**α 小数版本不存在**（现状 finalize 只发整型 v1/v2，α-β 递进纯新增）；四动作交互先例 = pending_proposals+resolve_proposal（guide_engine.py:401-444）+ 概念边 confirm/reject 端点（a1_routes.py:1960-2064）；D21⑬ 已确认建议方案（含触发时机=每轮轻量命中+模块边界深对齐），无需再问产品方。
- 「改天继续」同会话持久化：代理报告 session 存内存 _SESSIONS dict（a1_routes.py:685）——与 README 技术栈「会话存储 store」存在出入，计划中列为执行时验证点。
- 治理扩点：图谱摘要注入 interviewer = DN5 第四处 LLM 消费路径，须扩点评审登记。

**路三 · D22**：
- 注册 = 纯数据追加：output_modules.py（:24 SIGNAL_LEVELS 三档闭集 required/hard/optional；:27-32 OutputModuleDef；:41-138 现有 8 件即先例；:141-147 闭集元数据）→ module_registry.py 自动入池（:111-143）。**D22 权威文本已定「全 optional 档」**——三件 signal_requirements 全 optional，无 hard 依赖问题（代理提出的档位决策点已被 D22 原文覆盖）。
- 五件套模具 = main_module.py：NINE_SECTION_HEADINGS 冻结模板（:29-32）/_SECTION_SIGNALS 信号键绑定（:35-52）/module_compile_copy LLM 单点失败返 None（:139-176）/compile_document 总装+降级 module_compile_degraded（:179-234）/render_markdown（:98-109）。三件各建渲染器文件复用此结构。
- 端点模板 = doc 端点 finalize 八步范式（a1_routes.py:2320-2374 POST + :2377-2386 GET md/json）；dice-template 零 LLM 四步法（:2389+）。
- **发号**：StageCode 封闭枚举（graph_code_issuer.py:29-43）已占 **W/M/S/TD/TC/R/G**，文件头+行注释双冻结声明「不允许添加或修改」——D22 加字母需显式翻案冻结注释 + decision-log 登记；扩展点 = 仅加枚举成员（_issue :253-260 非 S 分支自动覆盖）。
- 三件数据源全部就绪：世界圣经=设定模块信号（世界本体.*等，大部分已入 _SECTION_SIGNALS）；人物志=角色.*（M11）；故事大纲=剧情.*（M12）——薄图谱照出，无采集缺口。
- 功能分级文档 :36（D22 行提升级 ≈¥0.03/件）+:69-71 付费墙三结论+:77 维护条款（立项后表格同步）。
- 收尾预览排序（D22⑤通用投影排前、跑团件标「进阶可用」）接线点 = 收尾三连问的可生成物预览（与 D21⑧ 同一函数消费）。

## Open Questions
- ~~范围~~ 已答：A 仅后端阶段。
- ~~测试策略~~ 已答：TDD。
- D22 新发号字母：D15 体系已用 W/M/TD/TC/R/S；世界圣经/人物志/故事大纲三件的字母待产品方定（研究中，将附建议选项）。
- 对齐循环（问题七）治理扩点评审：DN5 第四处 LLM 生产方（图谱摘要注入访谈）——计划中将含治理登记任务，随施工做。
- （Question 工具故障两次〔ctx.$ is not a function〕，改文字提问——已恢复正常沟通）

## Requirements (confirmed)（续）
- 【产品方已答 2026-09-28·问题三】**D22 发号字母 = 方案一 B/C/O**：世界圣经=B（Bible）/人物志=C（Character）/故事大纲=O（Outline）。**附加要求：字母须在全项目结构中统一、避免歧义——全局核查**（代码枚举+冻结注释翻案+决策台账登记+治理文档字母体系节同步+全库字母冲突排查）。

## Scope Boundaries（最终）
- INCLUDE：①D20 六层缺口补完（TDD 在途转绿+回归）②persona_card.py 清理 ③主次配方切换/收尾双条件/三连问/对齐循环后端实现 ④D22 三件（产出池注册+渲染器+端点+发号 B/C/O+全局字母统一核查）⑤治理随行（StageCode 冻结翻案登记、DN5 第四处扩点评审、PROJECT_STATE 收尾更新）。
- EXCLUDE：前端阶段（说人话文案整改/罗盘/收尾面板/推测卡/α 标记组件）、B1 终审、DN1/DN2 追认、J2、L1 排查、parse_modules 漂移、浏览器手动冒烟重跑（属前端阶段后）。
