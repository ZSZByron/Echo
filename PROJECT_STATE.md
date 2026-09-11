# PROJECT_STATE

### 当前阶段
A1 图谱化改造 v0.5 治理文档已定型（docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md，approved-for-planning），待生成正式工作计划（.sisyphus/plans/）进入实施。

### 已完成
- 2026-09-03 本次（续）：v0.5 风险评审收编——R1-R4 四个"旧病近亲"补丁全部写入治理文档：(R1)降级可观测三机制（warning持久化rec+图谱页角标+运行时断言 cst=0告警，现行warnings只闪现不落库需修）；(R2)confirmed匹配键=三元组精确匹配写入契约+失效边进审核台失效区禁静默丢弃（现行a1_routes.py:762 continue是静默丢弃）+深度树id改内容锚定 d:{anchor}:{title}（学term:模式，k序号仅进serial）+不变量5跨版本id稳定；(R3)契约注册表补C6（open_questions结构化记录禁裸list[str]）/C7（回答→边转正映射）骨架P0先行实现P4；(R4)P1加超长压测样本定分块触发线。新增验证发现：现行两阶段编排（finalize抽词→确认→POST抽边，2654805）由graphify取代、阶段2端点降级为手动重抽；验收标准扩至12条（负向用例/id快照/降级断言）；风险登记册§11落档
- 2026-09-03 本次：A1 知识图谱构建流程决策考古+统一模型定型——(1) 考古（git log -S 铁证）：08-21 三 commit 曾建完整结构化闭环（RealSemanticCompiler→tag=value→解析→约束边），08-24 e046a3c 范式重构斩断生产方（_COMPILER=None+访谈器输出纯中文）而消费方遗留且同 commit 还增强了解析器容错（M2 讽刺铁证）；08-27 机械投影在前提已死状态下决策；08-31 §10 YAGNI"不复活"定性错误；矛盾文档 .sisyphus/drafts/a1-contradiction-analysis.md（M1-M8+三流程铁律）。(2) 用户确认决策1-4（总结=LLM/一次调用合并/L4先证树/问卷序+LLM深度拓扑）+自然语言原则（结构化+关系化是系统职责）。(3) v0.5 统一模型（docs/governance/2-A1-v0.5-内容图谱化统一模型与契约.md）：三轴分离（数据形态 NL/SIR/KG、双树异号 0,N,N-M vs D{锚点}-{k}、tier≠level 七层以属性+派生边落地）、graphify 五字段 SIR 契约（module_summaries/entries/edges/constraint_fields/open_questions）、契约注册表+集成测试强制、组件修改清单+P0-P4 阶段+验收标准、对 v0.1/v0.4/08-31 的修正清单（§9）
- 2026-09-02 本次：新增认知边界主题纲要 docs/governance/2-A-认知边界与信息框架总纲.md（301行）——按"边界→分题材预期→信息框架→反馈与工具→留白自由度"五段位横向重组A模块设计：角色权限链（厂家>GM>PC）、A1-A3+GM大厅边界矩阵、8题材×四轴（厚度/伤害性/合法知识/泄漏处理）预期表、趣味性/哲理性双轴承载、工具×层级写权限分配表、GM留白节点清单（DC/锚点/结构洞/张力网/open_questions）、玩家身份三阶段；含TRPG领域惯例引证（GM屏风/朗读框/Session 0/Juul双层论）与设计vs实现诚实清单
- 2026-08-28 本次（第三批）：明华修仙.txt 全链路能力实测（DeepSeek deepseek-v4-pro，后端 uvicorn + HTTP 直调，11 次调用 0 服务端错误）：上传解析 35/35 字段全预填、逐字保真、空字段诚实拒绝（check_mode=缺少依据）；空白 session 访谈一句话→4字段分解、跑题优雅归档、种子锚定脚手架示例；定稿图谱 46节点/45 TREE边确定性编译、重定稿 v1→v2+stale、409 门禁契约正确。证据存 %TEMP%\opencode\a1_test\*.json
- A1 全流程：种子选择/上传解析/LLM访谈/定稿/IP展板/视觉背景预生成（前序会话）
- 2026-08-28 本次（第二批）：L1 发散引导解锁——`interviewer.py` 第8条"两句话确认"改为"确认+过渡（四句内）"+新增第9条发散引导指令（fills 非空时锚定用户关键词构造跨字段追问）；`InterviewResult`/`_parse`/prompt schema 三处新增 `divergent_question` 字段（单独问句，guidance_reply 结尾邀请式带出）；`config.py`+`.env.example`+`README` 默认模型 deepseek-chat→deepseek-v4-flash（纯弃用名修正，运行时行为不变）。全量 692/692 通过，ruff/mypy 零新增问题（存量：Pyright 9 错误/ruff 8 错误/覆盖率门禁 71.91% 均为前序遗留，见 lsp 与全量跑归因）
- 2026-08-28 本次：provider 层全厂商加固（`provider.py`）——chat_json 健壮 JSON 提取（剥围栏/前后缀）、response_format 400 降级重试链、thinking 防护扩展到 qwen/glm（原仅 deepseek）、Anthropic system-only 空消息修复 + 多 text block 拼接；test_provider.py 新增 12 测试，全量单测 478/478 通过。A1 访谈器（10模块追问+自动填空）对全部 6 provider 可用性由此保障
- 2026-08-27：定稿图谱条目化拓扑重构（`_build_graph`：约束L0→背景L1→模块L2→条目L3 + TREE 边）
- 2026-08-27 本次：新增只读知识图谱组件 `frontend/src/components/graph/A1KnowledgeGraph.tsx`（React Flow 层级带状布局，TREE实线/CROSS虚线）
- 2026-08-27 本次：回退修复——`graph_view` 双Tab展示页（知识图谱默认+展板预览）；IPPoster「返回世界观工坊」经 `a1_return_intent` 键一步直达 guided_chat；挂载水合恢复 file/进度/graphCode

### 进行中
- v0.5 图谱化改造待排期：按 docs/governance/2-A1-v0.5 §8 生成正式工作计划（P0 契约定型→P1 先证树→P2 深化+cst复活→P3 呈现→P4 待问闭环）；决策5/6/测试策略已按 §8 收口（方案2/tier方案/Tests-after+C1-C5），待用户最终确认排期

### 关键决策记录
- **v0.5 统一模型三轴（2026-09-03 用户确认）**：数据形态 NL/SIR/KG 单生产单消费；概念树序号 0/N/N-M 与深度树 D{锚点}-{k} 异号；tier（v0.4七层语义）≠level（图深度），tier 为模块属性+派生边呈现，不入图加深
- **graphify 五字段 SIR 契约**：定稿时一次 LLM 调用产出 module_summaries/entries/edges/constraint_fields/open_questions；constraint_fields 即考古断链的修复（重建 08-24 被斩断的生产方）；NL 永不携带机器格式
- 三流程铁律（考古沉淀）：诊断"未实现"先 git log -S 排除"曾实现后被废"；范式重构必盘点下游消费方；契约变更双侧签字+集成测试（C1-C5）
- 拓扑权威改立：骨架分类=问卷树（v0.3），3_knowledge-assets 实体/边词典降为槽位级"编译目标类型"嵌入使用——权威文档 2-A1-v0.4-世界观底层拓扑概念树.md（L0存在基座→L6治理层七层 + 槽位注册表 + 派生边总表★/◆/◇三级可信度 + LLM填空协议[必问/规则派生/上下文派生/校验]）——v0.5 后代码语境 L0-L6 一律称 tier
- 双序原理：访谈序（问卷序）给人类，拓扑序（底层向上）给 LLM 填空/推导；问卷序本身是拓扑序的合法拓扑排序
- 图谱拓扑设计立场：设定驱动×工程骨架×约束标注，**不从故事出发**（行政拓扑优先于语义拓扑，保证定稿产物确定性）——详见 docs/governance/2-A1-v0.1-定稿图谱拓扑与回退流.md
- 图谱节点 id：模块=module_id，条目=`{module_id}.{subfield_id}`（与 answers key 同构）；cst_* 为约束节点（level 0）
- 回退意图用 localStorage 键 `a1_return_intent='chat'`（A1Workspace 挂载时消费并清除）
- `poster_view` 状态已废弃 → 迁移为 `graph_view`

### 下一步
- J1-J4 修复接头排期（权威文档已入治理：docs/governance/2-A1-v0.5.1-管线缺陷级联与修复接头J1-J4.md，顺序 J1真值闸→J3披露协议→J4预算护栏→J2规范化层；xt 套件为验收器）
- 生成 v0.5 正式工作计划（.sisyphus/plans/，按治理文档 §8 的 P0-P4 拆分）→ /start-work 实施
- L1 排查（前序遗留）：divergent_question 结构化字段多轮未触发（实测锚定追问只出现在 reply 文本中）——需排查 interviewer prompt/_parse 触发条件
- parse_modules 跨轮不确定性（前序遗留）：同文档两次上传 35 vs 34 字段；"缺少依据"占位值计入 done/门禁/图谱条目【2026-09-10 xt 极限实验注记：显式文档×10 全稳定(spread=0)，边缘证据文档×10 复现 spread=3（32↔35）——病灶定位为边界字段三态随机漂移（缺key/占位值/编造）+ 31/35 字段值级方差；铁律"无依据缺省key"在骰子类字段从未生效（8轮编造+2轮占位）。证据 %TEMP%\opencode\a1_xt\borderline_20260910_234246.json + docs/plans/2026-09-09-a1-extreme-testing-design.md §8】
- 浏览器端手动冒烟（start.ps1）：定稿→图谱Tab→展板→回退→继续深化→重新定稿（v0.5 实施后重跑）

### 遗留问题
- vitest 全量跑会收集 Playwright spec（tests/e2e），需在 vitest config 排除
- useTypewriter 测试失败为前序遗留
- GraphViewContent/A1GraphSection 为组件内嵌套定义，父状态变化会重挂载（当前影响仅为图谱重复 GET，可接受）
