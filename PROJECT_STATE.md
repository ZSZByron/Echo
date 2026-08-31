# PROJECT_STATE

### 当前阶段
A1 世界观工坊三态流（种子→LLM引导→定稿→图谱/展板）迭代中，工作区存在大量未提交改动。

### 已完成
- 2026-08-28 本次（第三批）：明华修仙.txt 全链路能力实测（DeepSeek deepseek-v4-pro，后端 uvicorn + HTTP 直调，11 次调用 0 服务端错误）：上传解析 35/35 字段全预填、逐字保真、空字段诚实拒绝（check_mode=缺少依据）；空白 session 访谈一句话→4字段分解、跑题优雅归档、种子锚定脚手架示例；定稿图谱 46节点/45 TREE边确定性编译、重定稿 v1→v2+stale、409 门禁契约正确。证据存 %TEMP%\opencode\a1_test\*.json
- A1 全流程：种子选择/上传解析/LLM访谈/定稿/IP展板/视觉背景预生成（前序会话）
- 2026-08-28 本次（第二批）：L1 发散引导解锁——`interviewer.py` 第8条"两句话确认"改为"确认+过渡（四句内）"+新增第9条发散引导指令（fills 非空时锚定用户关键词构造跨字段追问）；`InterviewResult`/`_parse`/prompt schema 三处新增 `divergent_question` 字段（单独问句，guidance_reply 结尾邀请式带出）；`config.py`+`.env.example`+`README` 默认模型 deepseek-chat→deepseek-v4-flash（纯弃用名修正，运行时行为不变）。全量 692/692 通过，ruff/mypy 零新增问题（存量：Pyright 9 错误/ruff 8 错误/覆盖率门禁 71.91% 均为前序遗留，见 lsp 与全量跑归因）
- 2026-08-28 本次：provider 层全厂商加固（`provider.py`）——chat_json 健壮 JSON 提取（剥围栏/前后缀）、response_format 400 降级重试链、thinking 防护扩展到 qwen/glm（原仅 deepseek）、Anthropic system-only 空消息修复 + 多 text block 拼接；test_provider.py 新增 12 测试，全量单测 478/478 通过。A1 访谈器（10模块追问+自动填空）对全部 6 provider 可用性由此保障
- 2026-08-27：定稿图谱条目化拓扑重构（`_build_graph`：约束L0→背景L1→模块L2→条目L3 + TREE 边）
- 2026-08-27 本次：新增只读知识图谱组件 `frontend/src/components/graph/A1KnowledgeGraph.tsx`（React Flow 层级带状布局，TREE实线/CROSS虚线）
- 2026-08-27 本次：回退修复——`graph_view` 双Tab展示页（知识图谱默认+展板预览）；IPPoster「返回世界观工坊」经 `a1_return_intent` 键一步直达 guided_chat；挂载水合恢复 file/进度/graphCode

### 进行中
- A1 引导审核流+概念网 设计已定稿：docs/plans/2026-08-31-a1-guided-review-and-concept-network-design.md（用户已确认模块一/二方向；含 mermaid 架构图、写入守卫流、抽取管线、图谱页线框、验收标准、P1-P4 拆分）——待用户复核全文后进入实施

### 下一步
- L1 排查（实测证据已出）：divergent_question 结构化字段 4/4 轮未触发（2轮已完成session深化+2轮空白访谈），锚定追问只出现在 reply 文本中——需排查 interviewer prompt/_parse 触发条件；另发现"拒答轮静默写入"（file_diff=0 但 concept 被追加）
- P0 修复：已完成 session 深化路径的毁灭性覆盖（3 处文档 canon 字段被新输入整体替换而非合并，违反 immutable_core 精神，无 proposal 确认环节；覆盖直接传导进定稿图谱条目）
- 约束编译死路：上传/访谈两路径均产出纯文本 answers（0 个 tag=value 片段）→ _build_dimension_result_set 空 → cst_* 约束节点恒为 0、CROSS 边恒为 0；L0 语义化改造（v0.4 派生边总表）前图谱=纯行政树
- parse_modules 跨轮不确定性：同文档两次上传 35 vs 34 字段（check_mode 占位符"缺少依据"第二次未产出）；"缺少依据"占位值计入 done/门禁/图谱条目
- L0 引导轮按调用开 thinking（extra_body 覆盖 + max_tokens 8000，`_merge_kwargs` 已支持）；L2 拓扑 hints 注入（v0.4 派生边总表→机器可读【拓扑关系】段）
- 浏览器端手动冒烟（start.ps1）：定稿→图谱Tab→完整展板→一步回退→继续深化→重新定稿
- 前序遗留：useTypewriter.test.ts 6 失败、vitest 误收 tests/e2e/*.spec.ts，均与 A1 无关待修

### 关键决策记录
- 拓扑权威改立：骨架分类=问卷树（v0.3），3_knowledge-assets 实体/边词典降为槽位级"编译目标类型"嵌入使用——权威文档 2-A1-v0.4-世界观底层拓扑概念树.md（L0存在基座→L6治理层七层 + 槽位注册表 + 派生边总表★/◆/◇三级可信度 + LLM填空协议[必问/规则派生/上下文派生/校验]）
- 双序原理：访谈序（问卷序）给人类，拓扑序（底层向上）给 LLM 填空/推导；问卷序本身是拓扑序的合法拓扑排序
- 图谱拓扑设计立场：设定驱动×工程骨架×约束标注，**不从故事出发**（行政拓扑优先于语义拓扑，保证定稿产物确定性）——详见 docs/governance/2-A1-v0.1-定稿图谱拓扑与回退流.md
- 图谱节点 id：模块=module_id，条目=`{module_id}.{subfield_id}`（与 answers key 同构）；cst_* 为约束节点（level 0）
- 回退意图用 localStorage 键 `a1_return_intent='chat'`（A1Workspace 挂载时消费并清除）
- `poster_view` 状态已废弃 → 迁移为 `graph_view`

### 下一步
- 按 v0.4 概念树实施 `_build_graph` 语义化改造（派生边总表 + cst 边重定向 + TREE/DAG 值解析器）
- LLM 访谈器接入 [规则派生]/[上下文派生] 填空策略（拓扑序）

### 遗留问题
- vitest 全量跑会收集 Playwright spec（tests/e2e），需在 vitest config 排除
- useTypewriter 测试失败为前序遗留
- GraphViewContent/A1GraphSection 为组件内嵌套定义，父状态变化会重挂载（当前影响仅为图谱重复 GET，可接受）
