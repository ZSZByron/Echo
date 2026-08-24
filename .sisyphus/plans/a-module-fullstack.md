# A模块全栈架构：A1世界观设计 → A2产品策划 → A3内容生产 → GM大厅（含断点A-H全修复）

> 2026-08-19 架构修订：对齐流程图8.19改——A2双路径（策划线/TRPG默认线汇合于主模组生成）、API端点明确化、A1语义编译三级匹配+定稿409校验+IP展板修改分支

## TL;DR

> **Quick Summary**: 在现有 Echo UGC 架构上，构建"A1引导式世界观采集 → A2产品策划（骰子/角色模板投影）→ A3场景资产生成 → GM大厅游玩"完整管线，同时按依赖链修复全部断点A-H。每个断点修复任务内置"解释→用户授权→执行"关卡，全程TDD+过程文件留痕。
>
> **Deliverables**:
> - 架构文档：A模块全部模块清单+数据流图（docs/plans/module-a-inventory.md 等4份）
> - A1工作台（引导机器人+结构化文件+**定稿图谱化finalize**+IP展板）前端+后端
> - A2工作台（策划分析+骰子/角色/主模组展板+提示词组）前端+后端
> - A3工作台（场景+资产扩写→图片生成）前端+后端
> - GM大厅（/lobby，图片载入辅助游玩）
> - 断点A-H全部修复（各自带授权关卡+回归验证）
> - 用户ID+等级预留接口（UserTier枚举，默认FREE）
>
> **Estimated Effort**: XL
> **Parallel Execution**: YES - 5个执行波次 + 最终验证波
> **Critical Path**: 词典→断点B→断点A→断点C→断点F→A1定稿图谱化→A2投影链→A3→大厅→集成验证

---

## Context

### Original Request
用户要求（摘要）：继承当前技术架构（FastAPI+React），设计A模块的前端页面、前后端通信、前端模块清单、后端模块清单，分A1/A2/A3+断点修复。A1用LLM机器人引导式提问（按第4套维度重点问题），种子文件默认填入结构化文件基底，用户回答逐渐修改文件，创新想法写入"其他"字段，最后生成IP展板；结构化文件每用户专属独立ID。A2接收A1文件，机器人引导做产品策划分析（免费完整实现，付费仅预留接口），生成A2'文件→图谱→骰子模板生成器→角色模板生成器→主模组展板+提示词组+A2''文件→图谱。A3接收A2''扩写到场景+资产，提取标签生成提示词，AI生图，载入大厅UI辅助GM游玩。**用户强调：要整体架构说明而非技术细节；断点修复每一步都要解释清楚并获授权后才执行；过程文件留痕每步可查验。**

### Interview Summary
**Key Discussions**:
- 模板与图谱关系：用户困惑→确认采用**投影方案**（一个知识体系，模板=图谱类型化投影，展板=渲染层）
- 4套重命名：第4套→**A1·采集维度集**；第1套→**编译约束维度集**；第2套→**生成层级集**；第3套→**阶段权限集**
- 用户体系：本次只做自动生成user_id（LocalStorage），密钥分享/登录后续迭代
- 展板形态：混合（数据面板为主+AI配图）；**新增用户等级体系**（FREE/VIP/SVIP→不同等级LLM API，后续支持自带key）→本次仅预留枚举接口
- 断点：全部修复，每步"解释→授权→执行"
- 测试：TDD+过程文件留痕
- LLM：多Provider可配置（ACTIVE_PROVIDER）
- 付费：策划分析等完整实现且免费可用，分级限制后期实装

**Research Findings**:
- 后端惯例：`domains/creation/{module}/{module}_engine.py`四件套；`deps.py` Protocol DI；`provider.chat_json()`；GraphStore(aiosqlite)/AssetStore(JSON)
- 前端惯例：App.tsx pathname分发（无React Router）；`fetchWithTimeout`；Terminal+TypewriterText聊天模式可复用；**⚠️用户修正：A模块新页面不沿用赛博朋克CRT风——采用"星空平行宇宙"科幻质感（深空背景/星场粒子/星云渐变/玻璃拟态面板），与旧页面CRT主题并存，不改旧页面样式**
- 种子原型（用户修正）：**权威源=`docs/governance/seed-presets-catalog.md`（8预设：克苏鲁/赛博朋克/黑暗奇幻/废土/仙侠/太空歌剧/传统奇幻/权谋）**，架构定义"预设=目录元数据模板，A1种子文件=运行时生成JSON实例，改目录需重新生成种子"；`backend/experiments/trpg_presets.py`是含其中2预设实现的旧代码。A1种子文件=预设(风格/词汇/映射)+第4套10板块默认值（默认值需新设计，目录不覆盖）
- 断点权威依赖链（以`.sisyphus/drafts/A模块层级图-含断点.md`为准）：**A→B→C→{D,E,F}，F→G，G→E，H独立**

### Metis Review
**Identified Gaps** (addressed):
- A1问题树来源不明 → 已解决：问题树从层级图第4套维度（10大板块）派生，状态机控制顺序，LLM只负责措辞与追问
- A2''文件与图谱"双事实源"悖论 → 已解决：**图谱=事实源，结构化文件=图谱的序列化格式**（文件从图谱导出，单向）
- 授权关卡执行机制 → 已解决：每个断点修复任务第1步=呈现解释（引用T2授权文档），**明确停下等用户授权**，授权后才写代码
- README旧断点（权重动态化、五维→六维B2）混入风险 → 已解决：**明确排除**，本计划只修层级图断点A-H
- 断点修复回归风险 → 已解决：每个断点任务强制 pytest基线→TDD实现→回归验证 三段式
- Output模型加字段会破坏既有测试/签名变更影响调用方 → 已解决：任务内含"调用方适配+旧测试迁移"步骤

---

## A模块总体架构（模块总清单·有逻辑呈现）

### 端到端数据流

```
【用户user_id（自动生成，LocalStorage）+ UserTier（预留，默认FREE）】
    │
    ▼
★四层编码体系（IP身份→阶段→实例→版本）★
  · 编码格式：IP{序号}-{阶段路径}-v{版本}
    例：IP0142-W1-v3（世界观第3版）/ IP0142-M2-v1（主模组实例2）
       / IP0142-M2-S1-v2（主模组2下的次级模组1第2版）
  · 阶段码（封闭枚举）：W世界观图谱/M主模组/S次级模组/
    TD骰子模板/TC角色模板/R策划报告/G资产批次
  · 编码=人类可读检索层，内部主键仍是uuid（改名/归档不动摇关联）
  · IP名只做display_name不进编码（中途改名编码不变）
  · 发号规则（Store层原子递增，(user_id,code)唯一）：
    IP序号=A1会话启动即分配（选种子即IP出生，废弃归档不回收）；
    实例号=同范围最大+1（S在其父M内递增，其余IP内递增）；
    版本号=同实例当前+1，永不覆盖只追加
  · 结构化文件快照与图谱版本共享同一编码（类型字段区分file/graph）
  · 血缘lineage：每产物记录parent_graph_code（跨IP复用本次不做，
    parent必须同IP——留作后续导出/导入功能）
  · 每个生成器每次运行都产出新图谱+新编码（版本追加，永不覆盖）
  · A2/A3各生成器每次运行【显式选择】承接的上游图谱；
    系统默认=最新生成的兼容图谱及其结构化文件
  · stale图谱（上游已变更）仍可选择，但带醒目标记+变更集提示；
    版本链让"谁过期"可查（parent=W1-v2的标stale，parent=W1-v3不受影响）

┌─ 生成器① 世界观IP设计器（A1）────────────────────────────────┐
│ 种子库(8预设目录→运行时种子) ──选大类型──> 结构化文件基底       │
│ 引导机器人(GuideEngine)：状态机按A1·采集维度集10板块顺序提问   │
│   └─ 用户回答 ──语义编译器(断点A)──> 标签=枚举值写入文件      │
│   │  语义编译三级匹配：创新语句→AI分类提案二选一确认卡（归入现有字段/归入其他区）；常规语句→直接写入结构化文件│
│   └─ 创新想法 ──AI分类提案──> 用户确认 ──> 结构化字段 或 "其他"区│
│ 访谈期：结构化文件=工作数据源（此时无图谱，文件可自由修改）    │
│ ★A1定稿(finalize)=图谱化时点★：10板块必答完成→用户点击定稿    │
│   → 定稿前置校验：10板块缺失→HTTP 409+缺失清单→回访谈补齐；齐→文件转图谱一次性转换│
│   → 文件→图谱一次性转换(含断点F约束建边)→存GraphStore         │
│   → 若存在旧版本：diff输出变更集，下游相关图谱标stale（只标记不删）│
│   → 修改分支：IP展板弹出图谱条目浮层→选中条目【去修改】→回工作台定位板块→重新定稿→新版本W1-v2（旧版保留）│
│ 访谈期：结构化文件=工作数据源（此时无图谱，文件可自由修改）    │
│ ★A1定稿(finalize)=图谱化时点★：10板块必答完成→用户点击定稿    │
│   → 文件→图谱一次性转换(含断点F约束建边)→存GraphStore         │
│   → 若存在旧版本：diff输出变更集，下游相关图谱标stale（只标记不删）│
│ 产出：A1图谱(graph_code=IPxxxx-W1-v1)+IP展板 ── 可单独交付"只要IP"│
└──────────────────────────────────────────────────────────────┘
┌─ 其余6个独立生成器（分开开发，按需组合，输入=选定上游图谱）───┐
│ ②产品策划器：输入=选定A1图谱（默认最新已定稿）                │
│   └→ 产出：策划报告+决策记录（策划线，可选增强）               │
│ ③主模组生成器：输入=选定A1图谱（可携带②的决策——策划增强线；│
│   也可不带——TRPG默认线；骰子/角色模板投影后也汇合于此）       │
│   └→ 产出：主模组图谱(IPxxxx-M{实例}-v1)+主模组展板+提示词组+A2''文件；TRPG默认标注+下位拓展│
│ ④骰子投影器：输入=选定A1图谱（生成骰子模板图谱，v+1版本化）     │
│   └→ 产出：骰子模板+骰子展板                                   │
│ ⑤角色投影器：输入=选定图谱+骰子模板（二者一起）                │
│   └→ 产出：角色模板(v+1版本化)+角色展板                       │
│ ⑥次级模组生成器（场景/资产扩写）：输入=选定主模组图谱          │
│   └→ 产出：场景+资产图谱(IPxxxx-M{n}-S{实例}-v1) ── "只要次级模组"│
│ ⑦资产生成器：输入=含场景/资产节点的选定图谱                    │
│   └→ 产出：约束注入提示词→资产图片(版本化，审批后才可用)      │
│ 边界：③⑥最多到地点拓扑关系+风格约束（词典LOC/STY标签承载）   │
│ 消费上游前检查stale：已stale→提示变更集，不阻断不删除（留痕） │
└──────────────────────────────────────────────────────────────┘
    │
    ▼ 组合消费（装配=选定图谱包）
┌─ GM大厅(/lobby)：选定装配包(场景图+资产图片+角色卡+骰子面板   ─┐
│  +交互终端Terminal复用) → 辅助GM游玩                          │
└──────────────────────────────────────────────────────────────┘

推荐组合（工作台页面=预编排的生成器串联，每步可换上游图谱）：
  /a1=①（定稿图谱化） /a2=②→③ 或 ④→⑤→③（双路径汇合于③） /a3=⑥→⑦ /lobby=装配
  每个工作台入口有GraphSelector（显式选上游，默认最新，stale标记可见）
```

### 前端模块清单（8个新路由页 + 3组复用组件库）

| 路由 | 页面 | 组成 |
|------|------|------|
| `/a1` | A1工作台（**单页三态流：选种→访谈→成果，零跳转**） | 态①SeedSelector（"创造你的世界"+8种子卡片）→ 态②GuidedChat（引导对话+创新确认卡）+ StructuredFilePanel（文件实时diff）+ DimensionProgress（10板块完成度）+ 定稿按钮 → 态③内嵌IP展板+GraphPreview；**会话恢复按status自动路由到态②/③** |
| `/a1/poster` | IP展板（须A1已定稿） | **首屏=纯展板：全屏氛围史诗图背景+渐变蒙版+全部A1设定浮层集中展示**（顶部标题+IP码徽章/中部信息带/底部关键词chips+重新生成）+【继续修改】→**弹出图谱·条目浮层**（星图+条目按10大板块分组，选中【去修改】→回工作台定位板块→重新定稿→新版本W1-v2） |
| `/a2` | A2工作台 | **GraphSelector（选A1图谱，默认最新+stale徽章）**+ GuidedChat（策划决策对话）+ ModuleTopologyTree（A2模组拓扑维度树）+ 分析报告面板 + "跳过策划直接生成主模组"入口 |
| `/a2/boards` | A2展板组 | DicePoster / CharacterPoster / ModulePoster（tab切换）+ PromptGroupViewer（提示词组） |
| `/a3` | A3工作台 | **GraphSelector（选主模组图谱，默认最新+stale徽章）**+ 扩写对话 + 场景/资产清单 + 图片生成进度（复用Wave分组模式） |
| `/lobby` | GM大厅 | SceneView（增强：载入A3图片）+ CharacterCardPanel + DicePanel + Terminal |
| （集成） | 身份层 | IdentityGate（首次生成user_id存LocalStorage，显示ID+tier徽章） |
| （集成） | 导航 | 顶部导航条（A1→A2→A3→大厅 流程指示） |

**复用组件库**：`components/guided/`（GuidedChat、QuestionHint）、`components/structured/`（StructuredFilePanel、DimensionProgress、DiffHighlight）、`components/poster/`（PosterBoard骨架、PosterExportButton）、`components/graph/GraphPreview`（React Flow只读）。
**新增API客户端**：`api/identity.ts / a1.ts / a2.ts / a3.ts / lobby.ts`；类型：`types/structured.ts / seed.ts / poster.ts / template.ts`。

### 后端模块清单（5组新域 + 8处断点修复 + 3个新Store）

| 域 | 模块 | 职责 |
|----|------|------|
| `domains/identity/` | key_manager.py（user_id生成）、tier.py（UserTier枚举FREE/VIP/SVIP，默认FREE，路由接口仅TODO占位） | 用户ID+等级预留 |
| `domains/creation/seed/` | preset_loader.py（8预设目录解析）、seed_generator.py（预设→A1种子JSON生成，权威源docs/governance/seed-presets-catalog.md）、a1_question_tree.py（第4套10板块问题树+状态机定义） | 种子与问题树 |
| `domains/creation/a1/` | guide_engine.py（引导状态机）、semantic_compiler.py（断点A）、innovation_capture.py（创新→其他字段）、ip_poster.py（氛围史诗图prompt+展板浮层数据） | A1全部 |
| `domains/creation/a2/` | planning_analyzer.py（策划分析+AGENTS决策循环）、module_topology.py（A2拓扑树）、dice_projector.py、character_projector.py、module_poster.py、report_generator.py（报告，免费完整） | A2全部 |
| `domains/creation/a3/` | scene_expander.py（扩写）、asset_prompt_extractor.py（标签→提示词）、lobby_loader.py（大厅数据包） | A3+大厅 |
| 断点修复（改既有文件） | A:semantic_compiler + 词典；B:models/dimension.py结构化字段；C:constraint/application_tree.py；D:asset/prompt_builder.py注入；E:asset/prompt_fusion.py注入；F:graph/constraint_topology.py；G:constraint/constraint_inheritor.py；H:DimensionPromptBuilder层间语义 | 全部带授权关卡 |
| 新Store | state/structured_file_store.py（SQLite）、state/report_store.py、state/user_store.py | 持久化 |
| 新API路由 | api/identity_routes.py、a1_routes.py、a2_routes.py、a3_routes.py、lobby_routes.py | 对外接口 |

### 前后端通信协议（REST，沿用POST+前端打字机）

| 端点 | 方法 | 请求 → 响应 | 说明 |
|------|------|------------|------|
| `/api/identity/register` | POST | {} → {user_id, tier:"FREE"} | 首次进入自动调用 |
| `/api/a1/seeds` | GET | → {seeds:[{id,name,genre,description,dimension_defaults}]} | 种子大类型列表 |
| `/api/a1/session/start` | POST | {user_id, seed_id? 或 custom_idea?}（二选一：选种子 或 输入框手打奇思妙想） → {session_id, file_id, ip_code, first_question, file} | 建会话+基底填入（种子路径=默认值预填；自定义路径=空模板+奇思妙想注入概念/创新区） |
| `/api/a1/chat` | POST | {session_id, message} → {reply, next_question, file_diff, progress, phase, classification_proposal?} | 引导对话（响应内嵌diff驱动右栏增量更新；创新语句附带分类提案待用户确认） |
| `/api/a1/file/{id}` | GET | → StructuredFile | 文件读取（含status: draft/finalized与graph_id） |
| `/api/a1/file/{id}/finalize` | POST | → {graph_id, warnings} | **★A1定稿=图谱化时点**：10板块必答完成后可调；触发文件→图谱一次性转换（含断点F约束建边）；文件再改动须重新定稿 |
| `/api/a1/file/{id}/graph` | GET | → KnowledgeGraph | A1图谱（**须已定稿**；未定稿返回 status="pending_finalize"，不返回图谱） |
| `/api/a1/file/{id}/poster` | GET | → {panels, ai_image_prompt, ai_image_status} | IP展板数据（**须已定稿**；未定稿返回409+提示先定稿） |
| `/api/graphs` | GET | ?user_id= → {ips:[{ip_code, display_name, artifacts:[{graph_id, graph_code, stage, instance_no, version, status(finalized/stale), created_at, parent_graph_code}]}]} | **用户图谱清单（按IP分组，编码四层体系）**；artifacts按created_at倒序，最新在前） |
| `/api/a2/analyze` | POST | {user_id, upstream_graph_id?（默认=最新已定稿A1图谱）} → {session_id, analysis, questions} | 策划分析启动（**显式选择上游**；所选图谱stale时响应附变更集提示） |
| `/api/a2/decide` | POST | {session_id, decisions} → {a2_prime_file, free_path:"TRPG"} | AGENTS决策落定（生成A2'文件） |
| `/api/a2/report` | GET | ?session_id= → PlanningReport | 查看策划报告（免费完整实现） |
| `/api/a2/file/{id}/dice-template` | POST | {upstream_graph_id?} → DiceTemplate | 骰子投影（上游=A1图谱，默认最新兼容图谱） |
| `/api/a2/file/{id}/character-template` | POST | {upstream_graph_id?, dice_template_id?} → CharacterTemplate | 角色投影（图谱+骰子模板二者一起；默认最新） |
| `/api/a2/file/{id}/finalize` | POST | {upstream_graph_id?（A1图谱，可携带策划决策decision_session_id?）} → {module_graph_code, module_poster, prompt_group, a2_double_prime_file} | **主模组生成器**（独立可用：不带策划=免费TRPG默认线；带=策划增强线；骰子/角色投影后也汇合于此） |
| `/api/a3/expand` | POST | {user_id, upstream_graph_id?（默认=最新主模组图谱）, scope, counts} → {secondary_graph_code, file, graph} | **次级模组生成器**：场景+资产扩写（显式选择上游） |
| `/api/a3/file/{id}/prompts` | GET | → [{asset_id, prompt}] | 提示词组 |
| `/api/a3/assets/generate` | POST | {upstream_graph_id?, scope, counts} → {job_id, status} | **资产生成器**（输入=主模组图谱+scope+counts，异步+Wave分组轮询） |
| `/api/lobby` | GET | ?graph_code=?（默认最新可装配图谱） → {scenes, images, character_card, dice_panel} | 大厅装配数据包 |

---

## Work Objectives

### Core Objective
构建A模块"A1采集→A2策划投影→A3内容生产→GM大厅"完整可用管线，修复全部断点A-H，让约束体系真正贯穿"采集→编译→生成→注入→继承→产出"闭环。

### Concrete Deliverables
- 4份架构文档（模块清单/数据流/断点影响图/重命名术语表）
- 前端6个新页面+3组组件库+5个API客户端
- 后端5个新域+3个新Store+5组新路由
- 断点A-H修复（各带授权关卡）
- 全链路可用：一个新用户从选种子到大厅游玩跑通

### Definition of Done
- [ ] `pytest` 全绿（含新增TDD测试）；`npx vitest run` 全绿；`npm run build` 成功
- [ ] curl 全链路演练：register→seeds→session→chat×10→**finalize(A1图谱化)**→graph→poster→analyze→decide→dice/character→finalize(A2)→expand→generate→lobby 全部200（未定稿访问graph/poster/analyze须409/pending）
- [ ] Playwright：/a1 /a2 /a3 /lobby 四页可交互冒烟通过
- [ ] `.sisyphus/evidence/` 内每任务证据齐全（含断点任务授权记录）

### Must Have
- **A模块新页面（/a1 /a2 /a3 /lobby及展板）统一"星空平行宇宙"科幻视觉主题**：深空背景+星场粒子+星云渐变+玻璃拟态面板（主题token在T7建立，组件在T8统一采用）
- 断点修复顺序遵守依赖链 A→B→C→F→G→{D,E}，H独立
- 每个断点任务：pytest基线→呈现解释→用户授权→TDD实现→回归验证→证据留痕
- **★生成器组合架构**：7个生成器（①IP设计/②产品策划/③主模组/④骰子投影/⑤角色投影/⑥次级模组/⑦资产生成）**独立开发、独立可用、按需组合**——用户可能只要IP、或只要主模组、或只要次级模组，任一生成器产出可单独交付；工作台页面（/a1 /a2 /a3）只是预编排的推荐串联，不是强制路径；②产品策划是③的可选增强而非硬前置（不带策划直接生成主模组=免费TRPG默认线）
- **★四层编码体系与上游显式选择**：编码`IP{序号}-{阶段路径}-v{版本}`（四层=IP身份/阶段/实例/版本；阶段码封闭枚举W/M/S/TD/TC/R/G）；编码=检索显示层，主键=uuid，IP名只做display_name；发号Store层原子递增（IP序号=A1会话启动即分配，废弃不回收；实例号=同范围最大+1，S在父M内递增；版本号只追加）；文件快照与图谱版本同码；lineage记parent_graph_code且parent必须同IP（**跨IP复用本次不做**，留作后续导出/导入）；A2/A3各生成器每次运行必须显式选择承接的上游图谱，**系统默认=最新生成的兼容图谱及其结构化文件**；GET /api/graphs 提供用户图谱清单（**按IP分组**：编码/显示名/阶段/实例/版本/状态/时间/父编码）
- **★修改不污染铁律**：一切修改=**追加新版本**（图谱重建/模板v+1/图片重生成版本化），永不就地覆盖既有数据；上游变更只向下游传播**stale标记（附变更集）**，绝不自动重跑下游；各生成器消费上游前检查stale——提示变更集，不阻断不删除（用户坚持继续须留痕）
- **★A1图谱化时点=定稿动作（finalize）**：访谈期结构化文件=工作数据源（无图谱，可自由修改）；10板块必答完成后用户点击定稿 → 文件→图谱一次性转换（含断点F约束建边）→ 存GraphStore回写graph_id与graph_code → **此后图谱=事实源**；文件再改动须重新定稿（单向重建，不做双向同步）；IP展板与下游生成器均以"已定稿"为前置
- 模板=图谱投影（"图谱为事实源"适用于定稿后的A1图谱及A2''/A3图谱；各阶段结构化文件=图谱的序列化导出，单向）
- 引导式提问用状态机控制（用户不自由跳维度），LLM仅措辞/追问/语义编译
- **★种子优先原则**：回答处理三级匹配（种子库级→词典规则级→LLM级），前两级零LLM成本；板块默认值预填，用户未覆盖处保留种子值——"先用种子里的内容，有需要再额外生成"；问题树=种子内嵌数据（AI不发明问题，只措辞/追问）
- **创新语句：先匹配结构化文件现有类别→AI提案→用户确认→落盘；"其他"仅存放与现有类别不一致的内容（用户确认前不落盘）**
- 种子文件以 `docs/governance/seed-presets-catalog.md`（8预设）为权威源生成，覆盖A1·采集维度集10板块默认值

### Must NOT Have (Guardrails)
- ❌ **不改动现有页面（/、/graph/*、/admin/*）的赛博朋克CRT样式与index.css既有类**（新主题以增量方式加入：独立CSS变量域+独立组件，不覆盖旧token）
- ❌ 不实现等级路由逻辑（UserTier仅枚举+默认FREE+TODO注释）
- ❌ 不实现登录/注册/密钥分享（仅自动user_id）
- ❌ 不修改 ConstraintDimension / CreationLayer 枚举值（封闭枚举）
- ❌ 不做README旧断点（权重动态化、五维→六维B2）——层级图A-H之外不碰
- ❌ 4套重命名仅文档/概念层+UI显示名，不改代码标识符
- ❌ 不引入WebSocket/新框架（通信全走REST+打字机）
- ❌ AI-slop：无用注释、过度抽象、console.log残留、any类型逃逸

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - 技术验证全部agent执行。"用户授权"仅用于断点修复开工前的知情同意，不是测试手段。

### Test Decision
- **Infrastructure exists**: YES（pytest+Vitest+Playwright+CI）
- **Automated tests**: TDD（确定性核心逻辑：词典/编译器/状态机/投影器/逻辑树/继承器/注入器）
- **Framework**: pytest（后端）/ Vitest（前端组件）/ Playwright（E2E）
- **过程留痕（用户要求）**: 每任务产出 `.sisyphus/evidence/task-{N}-*` + 断点任务额外保存 `pytest基线输出` 与 `授权对话记录`

### QA Policy
- 后端：Bash curl 实测端点（请求体/响应字段/错误码逐一断言）
- 前端：Playwright 导航/交互/截图（`.sisyphus/evidence/`）
- LLM相关：用可注入的FakeProvider做确定性单测；真实Provider只做集成冒烟
- 错误场景必测：LLM返回非法JSON、用户矛盾回答、超长prompt截断、无效asset_ids

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1（架构+地基，9任务并行）:
├── T1 架构文档：模块清单+数据流 [writing]
├── T2 断点影响图+授权文档 [writing]
├── T3 4套重命名术语表 [quick]
├── T4 标签+枚举词典（断点A数据层）[deep]
├── T5 StructuredFile模型+用户ID+Tier预留 [deep]
├── T6 种子库迁移+A1问题树种子 [deep]
├── T7 前端骨架：路由/API/类型/身份层 [visual-engineering]
├── T8 前端通用组件库 [visual-engineering]
└── T9 断点B修复⚠️授权关卡 [unspecified-high]

Wave 2（断点编译链+A1，7任务）:
├── T10 断点A修复⚠️语义编译器 [ultrabrain]
├── T11 断点C修复⚠️约束应用逻辑树 [ultrabrain]
├── T12 断点F修复⚠️约束→拓扑 [deep]
├── T13 A1引导引擎（状态机）[deep]
├── T14 A1 API+会话 [unspecified-high]
├── T15 A1前端工作台 [visual-engineering]
└── T16 ★A1定稿图谱化+IP展板 [unspecified-high]

Wave 3（断点G+A2，7任务）:
├── T17 断点G修复⚠️约束继承传递 [deep]
├── T18 A2拓扑树+策划分析器 [deep]
├── T19 A2 AGENTS决策+报告 [unspecified-high]
├── T20 骰子投影器 [deep]
├── T21 角色投影器 [deep]
├── T22 A2 API+A2''定稿 [unspecified-high]
└── T23 A2前端工作台+展板组 [visual-engineering]

Wave 4（断点D/E/H+A3+大厅，8任务）:
├── T24 断点D修复⚠️PromptBuilder注入 [unspecified-high]
├── T25 断点E修复⚠️PromptFusion注入 [unspecified-high]
├── T26 断点H修复⚠️层间语义模板 [quick]
├── T27 A3场景+资产扩写引擎 [deep]
├── T28 A3标签→提示词→图片 [unspecified-high]
├── T29 A3前端工作台 [visual-engineering]
├── T30 大厅后端API [unspecified-high]
└── T31 大厅前端 [visual-engineering]

Wave 5（收尾，2任务）:
├── T32 端到端集成验证 [deep]
└── T33 文档同步更新 [writing]

Wave FINAL（4并行评审，全部APPROVE后呈报用户）:
├── F1 计划合规审计 [oracle]
├── F2 代码质量评审 [unspecified-high]
├── F3 真实手工QA [unspecified-high]
└── F4 范围保真检查 [deep]

Critical Path: T4→T9→T10→T11→T12→T16→T18→T20→T21→T22→T27→T28→T30→T31→T32
Max Concurrent: 9 (Wave 1)
```

### Dependency Matrix

| 任务 | 依赖 | 被依赖 |
|------|------|--------|
| T1,T2,T3,T4,T5,T6,T8,T26 | 无 | 见下 |
| T7 | T5(软) | T15,T23,T29,T31 |
| T9(B) | T4 | T10,T11,T12 |
| T10(A) | T4,T9 | T12,T14 |
| T11(C) | T4,T9 | T12,T24,T25 |
| T12(F) | T10,T11 | T16,T17 |
| T13 | T6 | T14 |
| T14 | T5,T10,T13 | T15,T16 |
| T15 | T7,T8,T14 | T32 |
| T16 | T12,T14 | T18,T32 |
| T17(G) | T12 | T25 |
| T18 | T6,T16 | T19,T20 |
| T19 | T5,T18 | T22 |
| T20 | T18 | T21,T22 |
| T21 | T20 | T22 |
| T22 | T16,T19(软：策划可选),T20,T21 | T23,T27 |
| T23 | T7,T8,T22 | T32 |
| T24(D) | T11 | T28 |
| T25(E) | T11,T17 | T28 |
| T27 | T22 | T28,T30 |
| T28 | T24,T25,T27 | T29,T30 |
| T29 | T7,T8,T28 | T32 |
| T30 | T28 | T31 |
| T31 | T8,T30 | T32 |
| T32 | 全部 | T33 |
| T33 | T32 | F1-F4 |

### Agent Dispatch Summary

- **Wave 1**: T1→writing, T2→writing, T3→quick, T4→deep, T5→deep, T6→deep, T7→visual-engineering, T8→visual-engineering, T9→unspecified-high
- **Wave 2**: T10→ultrabrain, T11→ultrabrain, T12→deep, T13→deep, T14→unspecified-high, T15→visual-engineering, T16→unspecified-high
- **Wave 3**: T17→deep, T18→deep, T19→unspecified-high, T20→deep, T21→deep, T22→unspecified-high, T23→visual-engineering
- **Wave 4**: T24→unspecified-high, T25→unspecified-high, T26→quick, T27→deep, T28→unspecified-high, T29→visual-engineering, T30→unspecified-high, T31→visual-engineering
- **Wave 5**: T32→deep, T33→writing
- **FINAL**: F1→oracle, F2/F3→unspecified-high, F4→deep

---

## TODOs

（任务详情见下方分批写入）

- [ ] 1. 架构文档：A模块模块清单+数据流图

  **What to do**:
  - 将本计划"总体架构"章节扩展为独立文档 `docs/plans/module-a-inventory.md`：每个新模块（前端页面/组件、后端域/Store/路由）的用途、输入、输出、依赖
  - 生成 `docs/plans/module-a-dataflow.md`：A1→A2→A3→大厅交接点（**含A1定稿finalize=图谱化时点的显式节点：draft文件→finalize→图谱+graph_id回写→解锁poster/A2**）、每处跨越边界的数据结构（结构化文件schema、图谱节点/边、图片URL包），附ASCII流程图
  - 文档为**用户首要审阅物**：语言用架构级描述，不堆代码

  **Must NOT do**: 不写任何代码；不虚构不存在的模块

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 纯文档产出，要求逻辑清晰可读
  - **Skills**: [`handle-large-files`]
    - 参考层级图398行大文件时按需切片
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`（无UI实现）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with T2-T9)
  - **Blocks**: T2（引用其模块清单）
  - **Blocked By**: None

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md` 全文 — 断点依赖链与第4套维度结构（权威来源）
  - 本计划"总体架构"章节 — 模块清单初稿
  - `README.md` 技术栈与项目结构章节 — 现有模块对照

  **Acceptance Criteria**:
  - [ ] `docs/plans/module-a-inventory.md` 存在且覆盖全部新模块（6页面/3组件库/5后端域/3Store/5路由/8断点）
  - [ ] `docs/plans/module-a-dataflow.md` 存在且含4个阶段交接点数据结构

  **QA Scenarios**:
  ```
  Scenario: 文档完整性
    Tool: Bash
    Steps:
      1. grep -c "##" docs/plans/module-a-inventory.md — 断言 >= 10 个模块章节
      2. grep "lobby" docs/plans/module-a-dataflow.md — 断言出现（大厅交接点在文档中）
      3. 对照本计划"前端模块清单"表逐行核对 inventory 文档均有着落
    Expected Result: 两文档存在、章节齐全、模块无遗漏
    Evidence: .sisyphus/evidence/task-1-doc-check.txt
  ```

  **Commit**: YES - `docs(architecture): A模块模块清单与数据流图` - docs/plans/module-a-inventory.md, module-a-dataflow.md

- [ ] 2. 断点影响图+授权文档

  **What to do**:
  - 生成 `docs/plans/breakpoint-impact-map.md`：8个断点（A-H）各自：现状（引用层级图原句）、修复做什么、**影响哪些现有文件**、回归风险等级（高/中/低）、回滚策略
  - 每个断点一节，末尾留"用户授权：☐ 已授权（日期/答复）"占位
  - 此文档是后续所有断点任务（T9-T12/T17/T24-T26）授权关卡的解释来源

  **Must NOT do**: 不写代码；风险评级不得凭空捏造（需基于pytest测试数量与调用方数量）

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: 文档产出，要求准确的文件引用与风险陈述
  - **Skills**: [`smart-explore`]
    - 定位断点涉及文件的现有测试与调用方数量
  - **Skills Evaluated but Omitted**: `systematic-debugging`（无bug修复）

  **Parallelization**:
  - **Can Run In Parallel**: YES（与T1共享Wave 1，末尾引用T1清单即可）
  - **Parallel Group**: Wave 1
  - **Blocks**: T9-T12, T17, T24-T26（授权来源）
  - **Blocked By**: None（软依赖T1）

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:105-375` — 断点A-H全部定义与依赖链
  - `backend/app/models/dimension.py` — 断点B现场（Output模型自由文本字段）
  - `backend/app/domains/creation/asset/prompt_builder.py` / `prompt_fusion.py` — 断点D/E现场
  - `backend/tests/` — 统计受影响测试数量

  **Acceptance Criteria**:
  - [ ] 文档含8节（A-H各一节），每节有：现状/修复内容/影响文件/风险/回滚/授权占位
  - [ ] 依赖链与层级图一致：A→B→C→{D,E,F}, F→G, G→E, H独立

  **QA Scenarios**:
  ```
  Scenario: 断点覆盖完整性
    Tool: Bash
    Steps:
      1. for b in A B C D E F G H; do grep -c "断点$b" docs/plans/breakpoint-impact-map.md; done — 断言每项>=1
      2. grep "回滚" docs/plans/breakpoint-impact-map.md | wc -l — 断言 >= 8
      3. 核对每个"影响文件"路径 Test-Path 存在
    Expected Result: 8断点全覆盖，影响文件路径真实存在
    Failure Indicators: 任何断点缺失或文件路径不存在
    Evidence: .sisyphus/evidence/task-2-impact-map-check.txt
  ```

  **Commit**: YES - `docs(breakpoints): 断点影响图与授权文档` - docs/plans/breakpoint-impact-map.md

- [ ] 3. 4套重命名术语表

  **What to do**:
  - 生成 `docs/plans/dimension-set-renames.md`：旧名→新名→出现位置（文档/注释/UI显示）
  - 新增 `backend/app/models/dimension.py` 中4个显示名常量（如 `SET_A1_COLLECTION = "A1·采集维度集"`）供前端API引用——**不改任何既有类名/变量名**
  - 前端 `types/` 增加对应显示名映射（仅展示用途）

  **Must NOT do**: 不改代码标识符（ConstraintDimension/CreationLayer/FIVE_DIMENSIONS等一律不动）；不修改枚举值

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 单文档+少量常量，范围明确
  - **Skills**: []
  - **Skills Evaluated but Omitted**: `git-master`（无复杂git操作）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T7（前端类型引用显示名）
  - **Blocked By**: None

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:16` — "第4套：世界观拓扑维度"定义处
  - `backend/app/models/dimension.py` — 常量添加位置（文件末尾，不动既有定义）

  **Acceptance Criteria**:
  - [ ] 术语表含4行映射且每行列出至少3处出现位置
  - [ ] `pytest tests/models/` 仍全绿（常量添加无副作用）

  **QA Scenarios**:
  ```
  Scenario: 常量可用性
    Tool: Bash (python)
    Steps:
      1. backend/.venv/Scripts/python -c "from app.models.dimension import SET_A1_COLLECTION; print(SET_A1_COLLECTION)"
      2. 断言输出 = "A1·采集维度集"
      3. cd backend && pytest tests/models/ -q — 断言 0 failed
    Expected Result: 常量导入成功且现有模型测试全绿
    Evidence: .sisyphus/evidence/task-3-rename-check.txt
  ```

  **Commit**: YES - `docs(renames): 4套维度重命名术语表+显示常量` - docs/plans/dimension-set-renames.md, backend/app/models/dimension.py

- [ ] 4. 标签词典+枚举词典（断点A数据层）

  **What to do**:
  - TDD：先写 `tests/unit/models/test_tag_dictionary.py`（加载/校验/查询用例）
  - 新建 `backend/app/models/tag_dictionary.py`：TagDictionary Pydantic模型 + 加载器（YAML→内存索引：按约束维度分组、标签→枚举值列表、必选/可选标记）
  - 新建 `backend/app/config/tag_dictionary.yaml`：从层级图第4套与断点B字段清单提炼全部合法标签与枚举值，至少覆盖：LAW(world_structure/gravity/conservation/divine_intervention/afterlife)、ACT(dice_mode/check_direction/cost_function/core_action)、NAR(era_stage/time_mode/trajectory/success_granularity)、WST(cost_type/feedback_loop/climate_zone/power_saturation)、SOC(political_type/access_topology/threshold/economy_type) + **A2新增LOC（地点拓扑：loc_topology/loc_connectivity）与STY（风格：style_keywords/architecture_style）标签组**
  - 枚举值必须封闭（逐字列出，禁止运行时新增）

  **Must NOT do**: 不改dimension.py既有枚举；词典与层级图冲突时以层级图为准并记录

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 领域词典设计需要对照层级图10大板块逐维度提炼，正确性要求高
  - **Skills**: [`test-driven-development`]
    - 核心数据层必须TDD
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`（无前端）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T9, T10, T11（编译链全部依赖词典）
  - **Blocked By**: None

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:105-130` — 断点A/B的标签与枚举需求清单（权威枚举来源）
  - `.sisyphus/drafts/A模块层级图-含断点.md:96-100` — 骰子设定5维映射（ACT词典dice_mode枚依据）
  - `backend/app/config/weight_matrix.yaml` — YAML配置文件格式惯例
  - `backend/app/models/dimension.py` — Output模型字段对齐（词典标签服务于断点B结构化字段）

  **Acceptance Criteria**:
  - [ ] `pytest tests/unit/models/test_tag_dictionary.py -v` 全绿（加载/校验/查询/封闭性≥8用例）
  - [ ] YAML含全部断点B列举标签 + LOC/STY两组
  - [ ] 每个标签的枚举值封闭且非空

  **QA Scenarios**:
  ```
  Scenario: 词典加载与查询
    Tool: Bash
    Steps:
      1. cd backend && pytest tests/unit/models/test_tag_dictionary.py -v — 断言全pass
      2. python -c "from app.models.tag_dictionary import load_tag_dictionary; d=load_tag_dictionary(); assert 'FLOATING_ISLANDS' in d.get_enum_values('LAW','world_structure')"
    Expected Result: 词典加载成功，示例枚举值可查
    Evidence: .sisyphus/evidence/task-4-dictionary-test.txt

  Scenario: 非法枚举拒绝
    Tool: Bash
    Steps:
      1. python -c "from app.models.tag_dictionary import load_tag_dictionary; d=load_tag_dictionary(); assert d.validate('LAW','world_structure','NOT_A_REAL_VALUE') is False"
    Expected Result: 非法枚举值验证返回False（封闭性生效）
    Evidence: .sisyphus/evidence/task-4-dictionary-closed.txt
  ```

  **Commit**: YES - `feat(dictionary): 标签+枚举词典数据层(TDD)` - backend/app/models/tag_dictionary.py, backend/app/config/tag_dictionary.yaml, backend/tests/unit/models/test_tag_dictionary.py

- [ ] 5. StructuredFile模型+用户ID+Tier预留

  **What to do**:
  - TDD：`tests/unit/models/test_structured_file.py` + `tests/unit/state/test_user_store.py`
  - 新建 `backend/app/models/structured_file.py`：StructuredFile（阶段字段 stage: A1/A2_PRIME/A2_DOUBLE_PRIME/A3、user_id、schema版本号、**定稿状态 status: draft|finalized（A1图谱化时点标记）+ can_finalize: bool（10板块必答齐为True）**、A1·采集维度集10板块的嵌套结构、每字段={value: 枚举或文本, source: seed|user|llm, confidence}、"其他/创新"自由文本区、图谱graph_id引用（定稿后回写））
  - 新建 `backend/app/domains/identity/`：key_manager.py（uuid生成user_id）、tier.py（`UserTier`枚举 FREE/VIP/SVIP，默认FREE；文件内仅留 `# TODO: 等级→Provider路由 后期实装` 注释，**无任何路由逻辑**）
  - 新建 `backend/app/state/user_store.py` + `state/structured_file_store.py`（aiosqlite，照graph_store.py惯例：save/get/list_by_user）+ **GraphStore扩展——四层编码发号与字段**：新增字段ip_code/display_name/stage_code(W/M/S/TD/TC/R/G)/instance_no/version/status(finalized/stale)/parent_graph_code；编码生成`IP{序号}-{阶段路径}-v{版本}`（**Store层原子递增发号**：IP序号每用户独立流水、实例号同范围最大+1、S在父M范围内递增、版本号同实例+1；(user_id,graph_code)唯一约束）；list_by_user按IP分组+created_at倒序
  - API：`api/identity_routes.py` POST /api/identity/register → {user_id, tier:"FREE"}；**GET /api/graphs?user_id= → 用户图谱清单（graph_code/stage/version/status/created_at/parent_graph_code）——上游显式选择机制的数据源**

  **Must NOT do**: 不写登录/密钥分享；不写tier路由if/elif；不接支付

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 核心数据模型，全管线都依赖此schema，需谨慎设计
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `kb-retriever`（无知识库检索需求）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T7(软), T13, T14, T18, T19, T27
  - **Blocked By**: None

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:16-103` — 采集维度集10板块结构（schema字段直接对齐）
  - `backend/app/state/graph_store.py` — aiosqlite Store惯例（连接管理/建表/CRUD模式）
  - `backend/app/models/knowledge_graph.py` — Pydantic模型惯例与graph_id关联
  - `backend/app/api/deps.py` — Protocol DI + lru_cache惯例

  **Acceptance Criteria**:
  - [ ] pytest 两测试文件全绿（模型校验/store读写/用户注册≥10用例）
  - [ ] tier.py全文grep无路由逻辑（仅枚举+默认值+TODO）

  **QA Scenarios**:
  ```
  Scenario: 注册与文件存储
    Tool: Bash (curl)
    Steps:
      1. curl -X POST http://localhost:8000/api/identity/register — 断言200且响应含user_id与tier="FREE"
      2. python -c "from app.state.structured_file_store import StructuredFileStore; ..." 保存→读取roundtrip — 断言字段一致
    Expected Result: 注册返回合法uuid；文件存取roundtrip无损
    Evidence: .sisyphus/evidence/task-5-identity-file.txt

  Scenario: Tier仅枚举无路由
    Tool: Bash
    Steps:
      1. grep -n "if.*tier\|elif.*tier\|VIP.*svip" backend/app/domains/identity/tier.py — 断言无匹配
    Expected Result: tier.py中无任何条件路由逻辑
    Evidence: .sisyphus/evidence/task-5-tier-guard.txt
  ```

  **Commit**: YES - `feat(identity): 结构化文件模型+用户ID+等级预留` - backend/app/models/structured_file.py, backend/app/domains/identity/, backend/app/state/user_store.py, structured_file_store.py, backend/app/api/identity_routes.py, 对应测试

- [ ] 6. 种子库：8预设目录载入+预设→种子生成+A1问题树

  **What to do**:
  - **权威源=`docs/governance/seed-presets-catalog.md`（8预设，用户指定）**：新建 `backend/app/domains/creation/seed/preset_loader.py` 解析目录结构（每预设：叙述风格指南voice/领域词汇库lexicon 6组/生成规则映射mapping）→ `PresetDefinition` Pydantic模型；`backend/experiments/trpg_presets.py` 中已实现的2预设（lovecraftian_horror/cyberpunk_heist）内容作为对照校验，原文件保留不删
  - **实现目录声明的架构："预设=模板，种子=运行时实例，改目录需重新生成"**：新建 `seed_generator.py` —— PresetDefinition → A1种子文件（JSON，含：voice_prompt/lexicon/mapping_logic + **dimension_defaults：A1·采集维度集10板块默认值（目录不覆盖，本任务按各流派特征设计，全部取T4词典合法枚举）**）；种子文件落 `backend/data/seeds/`，带 `generated_from` 预设id与时间戳
  - 新建 `backend/app/domains/creation/seed/a1_question_tree.py`：10板块的问题树（每板块3-5个引导问题模板+板块顺序+必答/可选标记）——问题模板含变量槽（如"{seed_name}世界里，力量的来源更接近以下哪种：{enum选项}"）；**问题树=数据文件，支持种子内嵌措辞变体（新增种子不改引擎代码）**；若需AI生成新变体：一次性离线生成+人工校对入库，运行时仍走确定性问题树
  - 8个种子全部生成（克苏鲁/赛博朋克/黑暗奇幻/废土/仙侠/太空歌剧/传统奇幻/权谋）
  - API：GET /api/a1/seeds（返回生成的种子文件内容）
  - TDD：预设解析（8条齐全）/种子生成（10板块默认值合法）/目录修改→重新生成生效 ≥8用例

  **Must NOT do**: 不删experiments原文件；dimension_defaults必须全部来自词典合法枚举（校验测试覆盖）；种子生成是幂等的（重复生成内容一致，时间戳除外）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 需解析481行目录文档+为8流派设计10板块默认值，正确性要求高
  - **Skills**: [`test-driven-development`, `handle-large-files`]
    - 目录文档481行，按预设分节切片读取
  - **Skills Evaluated but Omitted**: `writing`（代码内嵌内容非独立文档）

  **Parallelization**:
  - **Can Run In Parallel**: YES（软依赖T4词典——默认值引用枚举，可先写后对齐）
  - **Parallel Group**: Wave 1
  - **Blocks**: T13, T18
  - **Blocked By**: None（软：T4）

  **References**:
  - `docs/governance/seed-presets-catalog.md` — **权威种子目录**（概览表8预设+每预设voice/lexicon/mapping结构，1-150行为预设1-3，151+为其余5个）
  - `backend/experiments/trpg_presets.py` — 旧实现（2预设代码版，作对照）
  - `.sisyphus/drafts/A模块层级图-含断点.md:16-103` — 10板块=问题树骨架+默认值设计依据
  - `backend/app/domains/creation/seed/seed_engine.py` — seed域现有代码组织

  **Acceptance Criteria**:
  - [ ] pytest种子测试全绿（8预设解析/8种子生成/10板块默认值合法枚举/幂等/目录变更重生成）
  - [ ] GET /api/a1/seeds 返回8种子
  - [ ] `backend/data/seeds/` 存在8个JSON种子文件

  **QA Scenarios**:
  ```
  Scenario: 种子列表
    Tool: Bash (curl)
    Steps:
      1. curl http://localhost:8000/api/a1/seeds — 断言200，json数组=8项
      2. 每项含 id/name/dimension_defaults，且defaults覆盖10板块（len==10）
    Expected Result: 8种子、10板块默认值齐全
    Evidence: .sisyphus/evidence/task-6-seeds.txt

  Scenario: 默认值合法性
    Tool: Bash
    Steps:
      1. pytest tests/unit/domains/test_seed_generator.py -v — 含"默认值∈词典枚举"用例，断言全pass
    Expected Result: 全部默认值通过词典校验
    Evidence: .sisyphus/evidence/task-6-seed-validate.txt

  Scenario: 目录变更重新生成（错误场景）
    Tool: Bash (pytest)
    Steps:
      1. 修改某预设mapping一条规则（测试fixture目录）→ regenerate
      2. 断言新种子文件含新规则且generated_from指向该预设
    Expected Result: "改目录→重新生成"链路生效
    Evidence: .sisyphus/evidence/task-6-regen.txt
  ```

  **Commit**: YES - `feat(seed): 8预设目录载入+预设→种子生成+问题树(TDD)` - backend/app/domains/creation/seed/{preset_loader.py, seed_generator.py, a1_question_tree.py}, backend/data/seeds/*.json, 测试

- [ ] 7. 前端骨架：路由/API/类型/身份层+星空主题地基

  **What to do**:
  - **星空平行宇宙主题地基（用户指定视觉方向）**：
    - 新建 `styles/cosmos.css`：独立CSS变量域（`--cosmos-*`：深空底色#050510级、星云渐变violet/indigo/cyan、玻璃面板rgba+backdrop-blur、星尘文本色阶）——**不触碰index.css既有CRT变量**
    - `StarfieldBackground`组件：CSS动画星场（2-3层视差星点+偶发流星+星云径向渐变光斑），性能友好（纯CSS/少量div，无canvas依赖）
    - tailwind.config.js 增量扩展 `cosmos`色板与动画（不覆盖旧neon）
  - `App.tsx` 增加5个pathname分支：/a1 /a1/poster /a2 /a2/boards /a3 /lobby（先渲染占位页，**占位页即用星空主题**）+ 顶部导航条组件（流程指示 A1→A2→A3→大厅，读LocalStorage user_id显示，玻璃拟态样式）
  - `IdentityGate`组件+`api/identity.ts`：无user_id时自动调 /api/identity/register 并存LocalStorage
  - 新建 api客户端骨架：`a1.ts / a2.ts / a3.ts / lobby.ts`（函数签名按本计划通信协议表，暂用fetchWithTimeout实现，后端未起的端点允许404占位处理）
  - 新建类型：`types/structured.ts / seed.ts / template.ts / poster.ts`（与后端Pydantic 1:1，snake_case）
  - 4套显示名映射常量（引用T3）

  **Must NOT do**: 不引入React Router（沿用pathname分发）；**不修改index.css/tailwind既有类与旧页面样式**；不写业务UI（本任务只搭骨架+主题）；不引入canvas/Three.js等重依赖

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 前端工程骨架+新视觉体系建立
  - **Skills**: [`frontend-ui-ux`]
    - 星空平行宇宙主题的质感设计（星场/星云/玻璃面板层次）
  - **Skills Evaluated but Omitted**: `playwright`（E2E在T32）

  **Parallelization**:
  - **Can Run In Parallel**: YES（类型按本计划协议表定义，不等后端）
  - **Parallel Group**: Wave 1
  - **Blocks**: T8(软，主题token), T15, T23, T29, T31
  - **Blocked By**: T3(软), T5(软)

  **References**:
  - `frontend/src/App.tsx` — pathname分发模式（照抄现有startsWith分支写法）
  - `frontend/src/api/client.ts` — fetchWithTimeout/JSON_HEADERS惯例
  - `frontend/src/api/graph.ts` — 类型化API函数封装模式
  - `frontend/src/types/graph.ts` — 1:1类型映射惯例（含后端对应注释）
  - `frontend/src/index.css` + `tailwind.config.js` — **只增量扩展，作为命名与组织对照**
  - Tailwind v4 CSS-first配置语法 — cosmos.css变量+@theme扩展的正确写法

  **Acceptance Criteria**:
  - [ ] `npm run build` 成功；`npx oxlint` 0 error
  - [ ] 6路由全部可访问（星空主题占位页：可见星场动画+玻璃面板导航）
  - [ ] 旧页面 `/` 与 `/graph/editor` 样式与改动前一致（截图对比）

  **QA Scenarios**:
  ```
  Scenario: 路由骨架冒烟
    Tool: Playwright
    Steps:
      1. 依次 goto /a1 /a1/poster /a2 /a2/boards /a3 /lobby
      2. 每页断言 body 含占位标识（如 data-page="a1"）且含星场容器（[data-testid="starfield"]）
      3. 首次访问断言 LocalStorage 出现 echo_user_id 且导航条显示ID
    Expected Result: 6页渲染+星空主题+自动注册+导航可见
    Evidence: .sisyphus/evidence/task-7-routes.png（每页截图拼接或目录）

  Scenario: 旧页面样式零回归（错误场景反向验证）
    Tool: Playwright
    Steps:
      1. goto / 与 /graph/editor
      2. 断言无 --cosmos-* 变量泄漏到旧页面body、CRT扫描线仍存在
      3. 对比git改动前截图（像素级diff工具或目测截图留档）
    Expected Result: 新旧主题互不污染
    Evidence: .sisyphus/evidence/task-7-legacy-style.png

  Scenario: 后端未起时的降级（错误场景）
    Tool: Playwright
    Steps:
      1. 停掉后端，访问 /a1
      2. 断言页面不白屏，显示错误提示组件（"服务未连接"类文案）
    Expected Result: 优雅降级无崩溃
    Evidence: .sisyphus/evidence/task-7-degraded.png
  ```

  **Commit**: YES - `feat(frontend): A模块路由骨架+身份层+星空平行宇宙主题` - frontend/src/App.tsx, styles/cosmos.css, components/cosmos/StarfieldBackground.tsx, api/, types/, components/IdentityGate.tsx, NavBar.tsx, tailwind.config.js

- [ ] 8. 前端通用组件库

  **What to do**:
  - `components/guided/GuidedChat.tsx`：引导对话组件（消息历史+TypewriterText打字机+受控输入+loading态+快捷选项按钮渲染+**QuickConfirm创新确认卡**：显示AI分类提案+理由，"写入建议字段/归入其他"两按钮），props: onSend, messages, quickOptions, classificationProposal, onConfirmClassification
  - `components/structured/StructuredFilePanel.tsx`：结构化文件面板（10板块折叠卡片、字段值/来源徽章（seed/user/llm三色）、**diff高亮**：接file_diff时新值闪烁）——玻璃拟态卡片样式
  - `components/structured/DimensionProgress.tsx`：板块完成度进度条（已完成/必答剩余）
  - `components/poster/PosterBoard.tsx`：展板骨架（标题区+面板网格+AI配图区+导出按钮留位）——星空主题：星云渐变标题底、玻璃面板
  - `components/graph/GraphPreview.tsx`：React Flow只读图谱预览（复用GraphEditor节点渲染，禁编辑）
  - `components/graph/GraphSelector.tsx`：**上游图谱选择器**（拉取GET /api/graphs：**按IP分组**展示——IP卡（ip_code+display_name）下挂产物列表（graph_code+阶段+版本+时间）；**默认选中全局最新**；stale产物带⚠️徽章+变更集tooltip；选中后回传graph_id）——A2/A3工作台与大厅入口共用
  - **全部组件统一采用cosmos主题token（--cosmos-*变量+玻璃拟态），不引用旧neon类**
  - Vitest组件测试每个至少1个

  **Must NOT do**: 不做业务逻辑（不调真实API，props驱动）；不引入新依赖

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 纯UI组件库，视觉品质要求高
  - **Skills**: [`frontend-ui-ux`]
  - **Skills Evaluated but Omitted**: `test-driven-development`（组件测试随组件写，非严格RED先行）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: T15, T16, T23, T29, T31
  - **Blocked By**: None

  **References**:
  - `frontend/src/components/terminal/Terminal.tsx` — 聊天交互模式（消息列表+表单+loading）
  - `frontend/src/components/terminal/TypewriterText.tsx` + `hooks/useTypewriter.ts` — 打字机复用
  - `frontend/src/components/graph/PromptPreview.tsx` — 折叠面板模式
  - `frontend/src/styles/cosmos.css`(T7) — cosmos主题token（组件样式唯一来源，不用旧neon）
  - `frontend/src/pages/graph/GraphEditor.tsx` — React Flow节点渲染复用

  **Acceptance Criteria**:
  - [ ] `npx vitest run` 组件测试全绿（≥5个测试文件）
  - [ ] `npm run build` 成功

  **QA Scenarios**:
  ```
  Scenario: GuidedChat交互
    Tool: Vitest (@testing-library/react)
    Steps:
      1. 渲染GuidedChat传入mock messages+quickOptions
      2. 断言消息渲染、快捷按钮可点、输入框可输入并触发onSend
    Expected Result: 交互全通
    Evidence: .sisyphus/evidence/task-8-guidedchat.txt（vitest输出）

  Scenario: StructuredFilePanel diff高亮
    Tool: Vitest
    Steps:
      1. 渲染面板传入file+diff {板块:"力量体系", field:"溯源维度", new_value:"意志主导"}
      2. 断言对应字段含高亮class且显示新值
    Expected Result: diff正确呈现
    Evidence: .sisyphus/evidence/task-8-diff.txt
  ```

  **Commit**: YES - `feat(frontend): 通用组件库(引导对话/文件面板/展板骨架/图谱预览)` - frontend/src/components/{guided,structured,poster,graph}/, 测试

- [ ] 9. ⚠️断点B修复：Output模型结构化字段

  **What to do**:
  - **授权关卡（第一优先步骤）**：向用户呈现T2文档中断点B节——现状（LawOutput.rules等自由文本）、修复（增加结构化字段）、影响文件（dimension.py+6个Output模型+现有测试）、风险与回滚；**停下等待用户明确授权**，授权话语记录到 `.sisyphus/evidence/task-9-authorization.txt`
  - 授权后：`pytest --cov=app -q` 保存基线到 evidence
  - TDD：先改测试（结构化字段用例：字段存在/枚举合法/缺省兼容）
  - 修改 `backend/app/models/dimension.py` 6个Output：按断点B清单加结构化字段（LAW: world_structure/gravity/conservation/divine_intervention/afterlife；ACT: dice_mode/check_direction/cost_function/core_action；NAR: era_stage/time_mode/trajectory/success_granularity；WST: cost_type/feedback_loop/climate_zone/power_saturation；SOC: political_type/access_topology/threshold/economy_type），**全部Optional+默认None（向后兼容）**，自由文本字段保留
  - 字段类型=词典枚举的Literal或str+validator（引用T4）
  - 适配调用方：grep DimensionGenerator相关测试，修正因新字段导致的断言（不删测试，只扩展）
  - 回归：pytest全绿+覆盖率不低于基线

  **Must NOT do**: 不删自由文本字段；不修改枚举ConstraintDimension/CreationLayer；未授权不得动手

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 改核心模型+迁移既有测试，需严谨但非创造性问题
  - **Skills**: [`test-driven-development`, `systematic-debugging`]
    - TDD强制；测试失败时系统化排查
  - **Skills Evaluated but Omitted**: `using-git-worktrees`（单任务粒度不需要）

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 1内与其他任务并行；依赖T4词典）
  - **Parallel Group**: Wave 1
  - **Blocks**: T10, T11, T12
  - **Blocked By**: T4（词典枚举类型来源）

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:115-130` — 断点B权威字段清单（逐字对齐）
  - `backend/app/models/dimension.py` — 修改目标（LawOutput等6模型）
  - `backend/app/domains/creation/constraint/dimension_generator.py` — 调用方（生成Output的流程）
  - `backend/app/models/tag_dictionary.py`(T4) — 枚举校验引用
  - `docs/plans/breakpoint-impact-map.md`(T2) — 授权说明来源

  **Acceptance Criteria**:
  - [ ] evidence含：授权记录+pytest基线+回归输出三文件
  - [ ] 6模型全部含断点B清单字段，默认None
  - [ ] pytest全绿且覆盖不低于基线

  **QA Scenarios**:
  ```
  Scenario: 结构化字段生效
    Tool: Bash
    Steps:
      1. python -c "from app.models.dimension import LawOutput; m=LawOutput(rules=['x'], world_structure='FLOATING_ISLANDS'); assert m.world_structure=='FLOATING_ISLANDS'"
      2. pytest tests/models/ -q — 全pass
    Expected Result: 新字段可用且模型测试全绿
    Evidence: .sisyphus/evidence/task-9-fields.txt

  Scenario: 非法枚举拒绝（错误场景）
    Tool: Bash
    Steps:
      1. python -c "from app.models.dimension import LawOutput;
         try: LawOutput(world_structure='BOGUS'); print('FAIL')
         except Exception: print('REJECTED')"
      2. 断言输出REJECTED
    Expected Result: 非法枚举值被validator拒绝
    Evidence: .sisyphus/evidence/task-9-reject.txt

  Scenario: 授权关卡留痕
    Tool: Bash
    Steps:
      1. 检查 .sisyphus/evidence/task-9-authorization.txt 存在且含用户授权原文与时间
    Expected Result: 授权记录在案
    Evidence: 同上文件
  ```

  **Commit**: YES - `fix(breakpoint-b): Output模型结构化字段(TDD+回归)` - backend/app/models/dimension.py, 测试；commit message引用授权记录路径

- [ ] 10. ⚠️断点A修复：语义→标签→枚举编译器

  **What to do**:
  - **授权关卡**：同T9协议，引用T2断点A节，等待授权，记录 `.sisyphus/evidence/task-10-authorization.txt`
  - pytest基线留痕
  - 新建 `backend/app/domains/creation/a1/semantic_compiler.py`：SemanticCompiler类（构造注入LLMProvider）
    - 输入：用户自然语言回答 + 当前板块/问题上下文 + 词典
    - 两级编译：①规则级——词典同义词表直接命中（零LLM，确定性）；②LLM级——规则未命中时 chat_json 请求LLM从**封闭枚举**中选值+置信度；两者都失败→标记"待人工/创新"进自由文本区
    - 输出：`CompiledTag{tag, enum_value, confidence, source: rule|llm|unresolved}`
  - TDD：FakeProvider注入测确定性用例（规则命中/LLM命中/LLM返回非法JSON降级/全失败进自由文本）≥8用例
  - 幂等性：同phase重复编译同输入→结果不变（测试覆盖）

  **Must NOT do**: 编译器绝不产生词典外枚举值；未授权不动手

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: LLM+规则混合编译的降级链路设计是逻辑难点
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 2内与T11并行——C依赖B结构但词典接口已定）
  - **Parallel Group**: Wave 2
  - **Blocks**: T12, T14
  - **Blocked By**: T4, T9

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:105-113` — 断点A定义（输入/输出示例/LLM+规则混合要求）
  - `backend/app/models/tag_dictionary.py`(T4) — 查询接口
  - `backend/app/ai/provider.py` — chat_json接口
  - `backend/app/domains/creation/constraint/dimension_generator.py` — Provider注入模式范例

  **Acceptance Criteria**:
  - [ ] 授权+基线+回归三证据文件在案
  - [ ] pytest编译器测试全绿（≥8用例含全部降级路径）

  **QA Scenarios**:
  ```
  Scenario: 规则级编译
    Tool: Bash
    Steps:
      1. python -c "from app.domains.creation.a1.semantic_compiler import SemanticCompiler; c=SemanticCompiler(provider=None); r=c.compile_rule('漂浮岛屿的世界','LAW','world_structure'); assert r.enum_value=='FLOATING_ISLANDS' and r.source=='rule'"
    Expected Result: 同义词规则命中，零LLM
    Evidence: .sisyphus/evidence/task-10-rule.txt

  Scenario: LLM非法JSON降级（错误场景）
    Tool: Bash (pytest)
    Steps:
      1. FakeProvider返回 "not-json{{{"，调用compile
      2. 断言不抛异常，返回source='unresolved'且原文进自由文本建议
    Expected Result: 畸形LLM输出优雅降级
    Evidence: .sisyphus/evidence/task-10-degrade.txt
  ```

  **Commit**: YES - `fix(breakpoint-a): 语义→标签→枚举编译器(TDD)` - backend/app/domains/creation/a1/semantic_compiler.py, 测试

- [ ] 11. ⚠️断点C修复：约束应用逻辑树

  **What to do**:
  - **授权关卡**：同协议，记录task-11-authorization.txt
  - pytest基线留痕
  - 新建 `backend/app/domains/creation/constraint/application_tree.py`：逻辑树数据结构（source_field/target_prompt_layer/target_node_field/target_edge_type/transform/priority，字段照层级图断点C节逐字）+ `application_tree.yaml`（6维×6层=36条映射，内容按层级图示例扩展：LAW.world_structure在WORLD/NPC/SCENE/ASSET层的不同目标等）
  - 查询API：`get_injections(layer) -> list[InjectionRule]`（按priority排序）
  - TDD：加载/查询/优先级排序/映射完备性（36条不重不漏）≥6用例

  **Must NOT do**: 映射目标字段不得虚构图谱不存在的节点字段（对照knowledge_graph.py校验）

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: 36映射的语义正确性是"核心中的核心"（层级图原话），需深度对照
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `playwright`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: T12, T24, T25
  - **Blocked By**: T4, T9

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:215-245` — 断点C权威定义（数据结构6字段+3个LAW示例）
  - `backend/app/models/knowledge_graph.py` — target_node_field合法性对照（GraphNode/Edge字段）
  - `backend/app/config/weight_matrix.yaml` — YAML配置惯例

  **Acceptance Criteria**:
  - [ ] 36条映射测试全绿；LAW三条示例映射与层级图逐字一致
  - [ ] 授权+基线+回归在案

  **QA Scenarios**:
  ```
  Scenario: 36映射完备
    Tool: Bash
    Steps:
      1. python -c "from app.domains.creation.constraint.application_tree import load_tree; t=load_tree(); assert len(t.rules)==36"
      2. pytest tests/unit/domains/test_application_tree.py -v 全pass
    Expected Result: 36条不重不漏
    Evidence: .sisyphus/evidence/task-11-tree.txt

  Scenario: 层查询排序
    Tool: Bash
    Steps:
      1. get_injections('WORLD') 返回列表priority严格非降序
    Expected Result: 注入顺序确定
    Evidence: .sisyphus/evidence/task-11-order.txt
  ```

  **Commit**: YES - `fix(breakpoint-c): 约束应用逻辑树36映射(TDD)` - backend/app/domains/creation/constraint/application_tree.py, application_tree.yaml, 测试

- [ ] 12. ⚠️断点F修复：约束→拓扑节点/边创建

  **What to do**:
  - **授权关卡**：同协议，记录task-12-authorization.txt
  - pytest基线留痕
  - 新建 `backend/app/domains/creation/graph/constraint_topology.py`：
    - `apply_constraints(graph, dimension_result_set) -> graph'`：为每个结构化约束自动创建Constraint节点（id=cst_xxx, dimension=LAW等）+拓扑边（RULE_SHAPES_GEO等，边类型照层级图断点F节：POWER_SATURATES_GEO/POWER_SOURCES_FROM_GEO/RULE_SHAPES_GEO）
    - Concept(POWER_SYSTEM/PHILOSOPHY)支配关系建边
  - **阶段权限集成**：新节点带source_stage标记（A1阶段建A1骨架边），为第3套权限打地基
  - TDD：约束→节点/边创建、幂等（重复apply不重复建）、阶段标记正确 ≥6用例

  **Must NOT do**: 不改既有GraphNode/Edge模型（用现有字段扩展metadata）；不越权建其他阶段边

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 图谱构建核心，需对KnowledgeGraph API熟练
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `systematic-debugging`

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 2内，依赖已就绪的T10/T11完成）
  - **Parallel Group**: Wave 2
  - **Blocks**: T16, T17
  - **Blocked By**: T10, T11

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:299-314` — 断点F权威定义（3个建边示例）
  - `backend/app/models/knowledge_graph.py` — 节点/边API（add_node/add_edge/环检测）
  - `backend/app/domains/creation/graph/graph_extractor.py` — 图谱域代码惯例
  - `.sisyphus/drafts/A模块层级图-含断点.md:331-343` — 第3套source_stage权限设计

  **Acceptance Criteria**:
  - [ ] pytest全绿：cst节点+3类边创建、幂等、source_stage标记
  - [ ] 授权+基线+回归在案

  **QA Scenarios**:
  ```
  Scenario: 约束建边
    Tool: Bash
    Steps:
      1. 构造含 LAW.world_structure=FLOATING_ISLANDS 的DimensionResultSet，apply到空图
      2. 断言图含 Constraint节点(dimension=LAW) 且存在 RULE_SHAPES_GEO 边指向Geography节点
    Expected Result: 节点+边自动创建
    Evidence: .sisyphus/evidence/task-12-topology.txt

  Scenario: 幂等性（错误场景）
    Tool: Bash
    Steps:
      1. 同一约束apply两次
      2. 断言节点数/边数不变（第二次为no-op）
    Expected Result: 无重复节点边
    Evidence: .sisyphus/evidence/task-12-idempotent.txt
  ```

  **Commit**: YES - `fix(breakpoint-f): 约束自动建拓扑节点边(TDD)` - backend/app/domains/creation/graph/constraint_topology.py, 测试

- [ ] 13. A1引导引擎（状态机）

  **What to do**:
  - 新建 `backend/app/domains/creation/a1/guide_engine.py`：GuideEngine
    - 状态机：phase=10板块顺序推进（必答答完才进下一板块，可选可跳过），**用户不可自由跳维度**（符合"不给太多自由"）
    - 问题生成（**文档驱动+AI受限角色**）：问题树=种子内嵌数据（每种子可有措辞变体），引擎加载执行；LLM只做①措辞个性化（用种子voice_prompt风格说问题）②含糊时clarify追问③语义编译——**不发明问题本身**（保证10板块覆盖/可测试/不跑题）
    - 回答处理（**种子优先三级匹配，逐级降成本**）：①种子库级（零LLM：lexicon/mapping_logic命中→直接用种子内容）→②词典规则级（零LLM：同义词表→枚举值）→③LLM级（语义编译，断点A）→写入StructuredFile对应字段（source=user；**用户未覆盖处保留种子默认值——"先用种子内容，有需要再额外生成"**）
    - **自定义会话（无种子路径）**：custom_idea会话无默认值可预填——问题树照常走，回答处理退化为②词典规则级→③LLM级；custom_idea原文作为种子素材注入"概念/创新区"，机器人开场回应用户构想
    - **完成判定→可定稿**：状态机到终态（10板块必答全部完成）→ file.can_finalize=True 并在chat响应progress中返回 can_finalize:true（提示前端点亮定稿按钮；**定稿/图谱化动作本身在T16的finalize端点，GuideEngine只负责标记**）
    - **定稿后修改=revision模式**（展板浮层【去修改】入口）：定稿文件被要求修改时，session进入revision——**允许直接定位到用户选中的目标板块/字段问答**（首访谈的顺序约束仅约束首访谈；revision定位修改后file.status降draft+图谱标stale，须重新定稿）
    - 生成下一问题：问题模板（T6问题树）+ 词典枚举生成快捷选项 → LLM措辞润色（保留原意，风格贴近种子voice_prompt）
    - 处理回答：SemanticCompiler编译→写入StructuredFile对应字段（source=user）；编译unresolved→innovation_capture.py写入"其他/创新"自由文本区（source=user, raw原文）
    - 矛盾检测：同板块内新回答与已存枚举冲突→追问确认（"你之前选了X，现在是Y，以哪个为准？"），用户确认后覆盖并记confidence
  - 新建 `innovation_capture.py`：**创新分类器（用户存疑AI判断→人机协同确认，AI不得单方面落盘）**
    - 流程：用户语句经SemanticCompiler编译未命中枚举 → innovation_capture.classify() 生成**分类提案** {proposal: "匹配现有字段X"(matched_field+reason) 或 "归入其他"(reason), confidence}
    - 提案随chat响应的 classification_proposal 字段返回 → **前端弹确认卡，用户二选一**：①写入AI建议的现有字段 ②归入"其他/创新"区
    - **"其他"仅存放与结构化文件现有类别不一致的内容**（先匹配、匹配不上才进其他）；用户确认结果+AI提案原文一并留痕（source=user, proposal记录）
  - TDD（FakeProvider）：状态推进/跳过/矛盾追问/创新提案生成/用户确认后落盘/未确认不落盘 ≥10用例

  **Must NOT do**: 状态机不得允许跳到未来板块；LLM不得改枚举值（只措辞）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 多轮会话状态机+LLM协作，是A1体验核心
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2
  - **Blocks**: T14
  - **Blocked By**: T6（问题树）, T10（编译器）

  **References**:
  - `backend/app/domains/creation/seed/a1_question_tree.py`(T6) — 问题模板源
  - `backend/app/domains/creation/a1/semantic_compiler.py`(T10) — 编译调用
  - `backend/app/orchestrator.py` — 现有多轮交互编排器模式（会话状态管理参考）
  - `backend/app/models/structured_file.py`(T5) — 写入目标

  **Acceptance Criteria**:
  - [ ] pytest引导引擎测试全绿（≥8用例：推进/必答门禁/矛盾/创新/幂等）
  - [ ] 状态机无跳 future phase 路径（测试证明）

  **QA Scenarios**:
  ```
  Scenario: 引导推进+文件更新
  Scenario: 引导推进+文件更新
    Tool: Bash (pytest with FakeProvider)
    Steps:
      1. start_session(seed=lovecraftian_horror) → 首问题属"IP定位"板块
      2. 模拟回答"一个意志改变现实的世界" → 断言file中 世界本体.现实规则=意志主导(source=user)且phase推进
    Expected Result: 问答正确写入文件并推进
    Evidence: .sisyphus/evidence/task-13-guide.txt

  Scenario: 矛盾回答追问（错误场景）
    Tool: Bash (pytest)
    Steps:
      1. 先答"意志主导"，再答"物质主导"（同板块）
      2. 断言返回clarify问题而非直接覆盖；确认后覆盖生效
    Expected Result: 矛盾触发确认流
    Evidence: .sisyphus/evidence/task-13-conflict.txt

  Scenario: 创新语句→提案→用户确认落盘
    Tool: Bash (pytest FakeProvider)
    Steps:
      1. 用户输入"我的世界里力量来自梦境编织"（词典未命中）
      2. 断言chat响应含classification_proposal（matched_field或"其他"+reason+confidence）
      3. 断言此时file_diff为空（**未确认不落盘**）
      4. POST confirm-classification {user_choice:"other"} → 断言"其他/创新"区新增原文+提案留痕
    Expected Result: 先匹配→提案→用户确认→落盘，全链留痕
    Evidence: .sisyphus/evidence/task-13-innovation.txt

  Scenario: AI提案匹配成功路径
    Tool: Bash (pytest FakeProvider)
    Steps:
      1. 创新语句"力量靠血脉觉醒遗传" → 提案matched_field="力量体系.载体维度.获取方式=觉醒"
      2. 用户confirm {user_choice:"match"} → 断言该字段值="觉醒"(source=user)且"其他"区无此条
    Expected Result: 可归类创新进结构化字段
    Evidence: .sisyphus/evidence/task-13-match.txt
  ```

  **Commit**: YES - `feat(a1): 引导引擎状态机+创新捕获(TDD)` - backend/app/domains/creation/a1/guide_engine.py, innovation_capture.py, 测试

- [ ] 14. A1 API+会话

  **What to do**:
  - 新建 `backend/app/api/a1_routes.py`（prefix=/api/a1, tags=["a1"]）+ deps注入 + main.py注册：
    - POST /session/start {user_id, seed_id? 或 custom_idea?} → 建StructuredFile（种子路径=默认值填入；**自定义路径=空模板+custom_idea注入"概念/创新区"作为种子素材，GuideEngine以回应用户奇思妙想开场**）+ 会话 + first_question
    - POST /chat {session_id, message} → {reply, next_question, file_diff, progress, phase, classification_proposal?}（调GuideEngine；file_diff=本轮变更字段列表；创新语句时classification_proposal非空，**等待用户确认后才写盘**）
    - POST /confirm-classification {session_id, proposal_id, user_choice: "match"|"other"} → 更新file_diff（确认后生效）
    - GET /file/{id}（含status/can_finalize/graph_id字段）
    - POST /file/{id}/finalize（**★A1图谱化时点入口**；T14先注册路由占位——未实现转换前返回501，实装在T16）
    - GET /file/{id}/graph（未定稿返回 {status:"pending_finalize"}，不返回图谱；已定稿返回图谱——T16实装，T14期已定稿态不可达故为占位）
    - GET /file/{id}/poster（未定稿返回409+提示先定稿；T16实装）
  - 会话状态：内存dict+session_id（uuid），file持久化走StructuredFileStore
  - 集成测试（FakeProvider）：完整一轮 start→chat→file更新→diff返回

  **Must NOT do**: 不在路由层写业务逻辑（全部委托GuideEngine）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 标准CRUD+委托模式，工作量中等
  - **Skills**: []
  - **Skills Evaluated but Omitted**: `test-driven-development`（集成测试随实现）

  **Parallelization**:
  - **Can Run In Parallel**: YES（与T15前端并行，按协议对接）
  - **Parallel Group**: Wave 2
  - **Blocks**: T15, T16
  - **Blocked By**: T5, T10, T13

  **References**:
  - `backend/app/api/constraints_routes.py` — 路由+请求响应模型模式范例
  - `backend/app/api/seed_routes.py` — 会话型端点模式（generate/confirm两段式）
  - `backend/app/api/deps.py` — Depends注入惯例
  - `backend/app/main.py` — include_router注册点

  **Acceptance Criteria**:
  - [ ] pytest integration测试全绿（start/chat/diff/graph占位）
  - [ ] /docs 出现a1标签组

  **QA Scenarios**:
  ```
  Scenario: 会话全流程
    Tool: Bash (curl)
    Steps:
      1. curl -X POST /api/a1/session/start -d '{"user_id":"u_test","seed_id":"lovecraftian_horror"}' — 断言200含session_id/first_question/file（含10板块默认值）
      2. curl -X POST /api/a1/chat -d '{"session_id":"...","message":"意志主导的世界"}' — 断言200含reply/file_diff（世界本体.现实规则变更）/progress
    Expected Result: 两端点协作正确
    Evidence: .sisyphus/evidence/task-14-api.txt

  Scenario: 无效session（错误场景）
    Tool: Bash (curl)
    Steps:
      1. curl -X POST /api/a1/chat -d '{"session_id":"nonexistent","message":"x"}'
      2. 断言404且错误信息含"session"
    Expected Result: 优雅404
    Evidence: .sisyphus/evidence/task-14-404.txt
  ```

  **Commit**: YES - `feat(a1): 会话与文件API` - backend/app/api/a1_routes.py, main.py, 测试

- [ ] 15. A1前端工作台

  **What to do**:
  - `pages/a1/A1Workspace.tsx` 替换占位页，**单页三态流（零跳转）**：
    - **态①欢迎选种**："创造你的世界"大标题+8种子卡片（seed-carousel，选中即POST session/start，发ip_code）+**卡片下方自定义输入框（placeholder"告诉我你的奇思妙想……"+"开始创造"按钮→custom_idea路径进入态②，机器人以回应用户构想开场）**
    - **态②访谈工作台**：左栏GuidedChat（quickOptions快捷枚举选项+**创新确认卡QuickConfirm：AI分类提案+理由，用户二选一**），右栏StructuredFilePanel（实时file_diff高亮）+ DimensionProgress顶部进度+**定稿按钮（can_finalize点亮，未完成置灰+剩余必答提示；成功后原地切态③，提示"修改将需重新定稿"）**
    - **态③成果预览**：定稿成功原地切换——**首屏=纯展板**（内嵌IP展板：氛围史诗图+蒙版+设定浮层+【继续修改】+【分享链接】）；**【继续修改】→弹出图谱·条目浮层**（星图+10板块分组条目，选中条目【去修改】→回态②并定位到对应板块/字段——提示"修改将需重新定稿"）；/a1/poster保持独立成果路由（分享/直达/作品集用），与态③复用同一PosterBoard组件
    - `/a1/poster` 保持独立成果路由（分享/直达/作品集用），**与态③复用同一PosterBoard组件**
  - `api/a1.ts` 对接T14五端点（含confirm-classification与finalize）；聊天loading态+错误横幅；打字机速度15ms；会话恢复：file_id存在时按status路由到态②或态③
  - 会话恢复：file_id存在时直接GET /file/{id}渲染
  - Vitest：渲染/发送/差异更新3用例

  **Must NOT do**: 不改GuidedChat等通用组件内部（只用props）；不mock数据上线（真实API）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`frontend-ui-ux`]
  - **Skills Evaluated but Omitted**: `playwright`（E2E归T32）

  **Parallelization**:
  - **Can Run In Parallel**: YES（与T16并行）
  - **Parallel Group**: Wave 2
  - **Blocks**: T32
  - **Blocked By**: T7, T8, T14

  **References**:
  - `frontend/src/pages/graph/GraphAssetReview.tsx` — 页面数据流模式（加载/渲染/刷新）
  - `frontend/src/components/terminal/Terminal.tsx` — 聊天提交模式
  - 本计划通信协议表 — 端点契约

  **Acceptance Criteria**:
  - [ ] vitest 3用例绿；npm run build成功
  - [ ] Playwright冒烟：/a1可对话且右栏diff闪烁更新

  **QA Scenarios**:
  ```
  Scenario: 引导对话E2E
    Tool: Playwright
    Steps:
      1. goto /a1 → 选种子卡片 data-testid="seed-lovecraftian_horror"
      2. **初始态断言（干净开场）**：对话流无任何用户消息、首问属"IP定位"板块（文案含命名/大类型类提问）、文件面板仅有🌱种子来源字段（无user来源）、进度0/10、创新确认卡不存在
      3. 等待first_question打字机输出 → 首轮快捷选项为大类型选择（种子流派）
      4. 输入自定义文字提交 → 创新确认卡**此时才**弹出
      5. 断言右栏对应字段含新值且有diff高亮class
      6. 截图
    Expected Result: 干净开场→问答→文件更新→创新卡按需弹出，全链符合状态机逻辑
    Evidence: .sisyphus/evidence/task-15-a1-e2e.png

  Scenario: 后端断连（错误场景）
    Tool: Playwright
    Steps:
      1. 停后端，发消息
      2. 断言错误横幅显示且输入不丢失
    Expected Result: 优雅错误提示
    Evidence: .sisyphus/evidence/task-15-error.png
  ```

  **Commit**: YES - `feat(frontend): A1引导工作台` - frontend/src/pages/a1/, api/a1.ts

- [ ] 16. ★A1定稿图谱化+IP展板（图谱化时点实装）

  **What to do**:
  - **实装 POST /api/a1/file/{id}/finalize（★A1图谱化唯一时点，替换T14的501占位）**，管线：
    1. 前置校验：file.can_finalize=True（10板块必答齐），否则409+缺失板块清单
    2. `file_graph_converter.py`：StructuredFile → KnowledgeGraph（10板块→节点，板块关系→边；**每个节点携带category元数据=来源板块（A1·采集维度集10板块），供展板条目分类**；结构化约束经T12 constraint_topology自动建Constraint节点+边）→ 存GraphStore，file.graph_id回写
    3. file.status=draft→finalized；返回 {graph_id, graph_code（**首次=IPxxxx-W1-v1；重新定稿=W1-v2,v3…只追加**）, warnings（如unresolved字段提示）}
    4. **重新定稿**：定稿后文件再被chat修改→status自动降回draft+graph_id标记stale（旧图谱保留只读）→ 须再次finalize重建图谱（**单向：文件→图谱，图谱永不回写文件**）
    5. **变更集+下游stale传播（修改不污染铁律）**：重新finalize时若存在旧版图谱 → diff(旧图谱,新图谱)输出**变更集**（受影响节点/边清单，随响应返回并存evidence）→ 据此将下游引用旧图谱的生成器产物（主模组/骰子/角色/次级模组图谱）**标记stale（只标记，绝不删除/修改/自动重跑）**；下游生成器消费上游前检查stale→提示变更集
  - `ip_poster.py`：**展板=氛围史诗图形态（用户定稿的设计）**——①从已定稿file+图谱合成世界观整体描述总结→氛围史诗图prompt（视觉关键词+基调+哲学+风格约束，走PromptBuilder粗版）→调ImageGenerator生成**一张全屏背景大图**（异步：status轮询；API已验证：zhipu/wanxiang/qwen/local四provider见image_generator.py）②panels数据=蒙版上的设定浮层（IP名称/概念/类型/核心体验/力量体系4维/视觉关键词，从file+图谱提取）
  - 实装 GET /file/{id}/graph（已定稿→图谱；draft/pending_finalize语义见协议表）与 GET /file/{id}/poster（未定稿409；响应={hero_image:{url,status}, panels}）
  - 前端 `pages/a1/IPPoster.tsx`：**首屏=纯展板**（全屏hero氛围史诗图：generating→淡入两态+重新生成按钮→渐变蒙版→全部A1设定浮层集中展示：顶部大标题+IP码徽章/中部信息带：IP定位摘要chips+力量体系4维光条+核心体验/底部视觉关键词chips；底部【继续修改】主按钮+【分享链接】）；**【继续修改】→弹出图谱·条目浮层**（居中大模态+遮罩+×关闭：左GraphPreview星图+右条目列表codex——按结构化文件10大板块分组折叠，每条=条目名+摘要+来源徽章🌱🧑🤖+约束徽章LAW/ACT…+【去修改】；点击条目→星图节点高亮脉冲；浮层底部【带着选中条目去修改】→关闭浮层回态②访谈并把对话定位到该条目对应板块/字段）；未定稿显示"请先完成定稿"引导页；**demo参照=`experiments/a1-three-state-demo.html`态③**
  - TDD：定稿前置校验/转换器板块→节点映射/重新定稿降级draft ≥9用例；poster数据完整性3用例

  **Must NOT do**: 图谱永不回写文件（单向铁律）；未定稿文件绝不产出图谱；finalize不删旧图谱（stale保留供追溯）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`test-driven-development`, `frontend-ui-ux`]
  - **Skills Evaluated but Omitted**: `playwright`

  **Parallelization**:
  - **Can Run In Parallel**: YES（与T15并行）
  - **Parallel Group**: Wave 2
  - **Blocks**: T18（A2以A1定稿图谱为输入）, T32
  - **Blocked By**: T12, T14

  **References**:
  - `backend/app/domains/creation/graph/graph_extractor.py` — 建图模式
  - `backend/app/domains/creation/graph/constraint_topology.py`(T12) — 约束建边调用
  - `backend/app/state/graph_store.py` — 图谱持久化
  - `backend/app/ai/image_generator.py` — 生图调用（zhipu/wanxiang/qwen/local）
  - `backend/app/domains/creation/asset/generation_scheduler.py` — 异步任务+状态模式
  - `frontend/src/components/shared/AssetPlaceholder.tsx` — 加载占位复用
  - 本计划通信协议表 a1 finalize 行 — 契约

  **Acceptance Criteria**:
  - [ ] 定稿管线测试全绿（校验/转换/重定稿降级/stale保留）；poster端点未定稿409
  - [ ] /a1/poster页渲染panels且配图区有loading→就绪两态；未定稿引导页可见

  **QA Scenarios**:
  ```
  Scenario: 定稿→图谱生成（图谱化时点验证）
    Tool: Bash (curl)
    Steps:
      1. 用task-15走完10板块必答的file_id，先调 GET /api/a1/file/{id}/graph
      2. 断言返回 {status:"pending_finalize"}（定稿前无图谱）
      3. POST /api/a1/file/{id}/finalize → 断言200含graph_id
      4. 再GET graph → 断言200，nodes含"IP定位""力量体系"板块节点且edges非空；存在dimension=LAW的Constraint节点
    Expected Result: 定稿前锁、定稿后图谱+约束节点就绪
    Evidence: .sisyphus/evidence/task-16-finalize.json

  Scenario: 重新定稿（错误场景）
    Tool: Bash (curl)
    Steps:
      1. 定稿后再chat修改文件 → GET /file/{id} 断言status=draft且graph_id标记stale
      2. graph端点仍返回旧图谱（stale只读）→ 重新finalize → 断言新graph_id≠旧的
    Expected Result: 单向重建链路正确
    Evidence: .sisyphus/evidence/task-16-refinalize.txt

  Scenario: 未答完强制定稿被拒（错误场景）
    Tool: Bash (curl)
    Steps:
      1. 只答2板块的file调finalize → 断言409且响应含缺失板块清单
    Expected Result: 前置校验拦截
    Evidence: .sisyphus/evidence/task-16-409.txt

  Scenario: 展板渲染
    Tool: Playwright
    Steps:
      1. goto /a1/poster?file_id=xxx（已定稿）
      2. **首屏断言**：hero区存在（[data-testid="poster-hero"]）：generating→淡入两态、蒙版层存在（文字可读）、浮层panels>=4组+重新生成按钮可点；**页面无图谱/条目常驻元素**（纯净展板）
      3. 点击【继续修改】→ 断言浮层弹出（[data-testid="graph-entry-overlay"]）：星图渲染+条目按10大板块分组（组头>=10）、条目含来源徽章；点击条目→星图节点高亮class
      4. 点【带着选中条目去修改】→ 断言回到工作台态②且对话定位到该条目板块（首条消息引用所选条目）
    Expected Result: 纯净展板+按需弹出图谱条目导航+修改定位闭环
    Evidence: .sisyphus/evidence/task-16-poster.png

  Scenario: 生图失败降级（错误场景）
    Tool: Bash
    Steps:
      1. 配置无效provider key调poster生图
      2. 断言status=failed且panels仍完整返回（面板不依赖配图）
    Expected Result: 生图失败不影响数据面板
    Evidence: .sisyphus/evidence/task-16-imgfail.txt
  ```

  **Commit**: YES - `feat(a1): 定稿图谱化(finalize)+IP展板` - backend/app/domains/creation/a1/{file_graph_converter.py, ip_poster.py}, a1_routes.py实装, frontend/src/pages/a1/IPPoster.tsx, 测试

- [ ] 17. ⚠️断点G修复：约束继承传递

  **What to do**:
  - **授权关卡**：同协议，记录task-17-authorization.txt
  - pytest基线留痕
  - 新建 `backend/app/domains/creation/constraint/constraint_inheritor.py`：按层级图断点G设计实现
    - 权重≥10%完整传递 / 5-10%压缩为一句摘要 / <5%不传 / override可覆盖不可删除（原约束保留记录）
    - 传递路径沿边类型：GEO_CONTAINS/GEO_BORDERS/FACTION_OPPOSES/ALLIED/EVENT_CAUSED_BY
    - `inherit(graph, weights) -> inherited_constraints`
  - TDD：4档权重行为/override不可删/沿边路径 ≥8用例

  **Must NOT do**: 不改变约束本体（继承产生副本/摘要，原节点不动）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `systematic-debugging`

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 3）
  - **Parallel Group**: Wave 3
  - **Blocks**: T25
  - **Blocked By**: T12（需要拓扑边存在）

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:316-329` — 断点G权威规则（4档+路径清单）
  - `docs/plans/2026-08-03-layered-constraint-architecture.md` 第五节 — 原设计文档（3_knowledge-assets §7提及）
  - `backend/app/domains/creation/constraint/` — 域内模块惯例

  **Acceptance Criteria**:
  - [ ] 8+用例全绿含4档权重边界（恰好10%/恰好5%）
  - [ ] 授权+基线+回归在案

  **QA Scenarios**:
  ```
  Scenario: 三档传递行为
    Tool: Bash (pytest)
    Steps:
      1. 构造权重12%/7%/3%三约束沿GEO_CONTAINS传递
      2. 断言：12%全文传递、7%为摘要（长度<原文且非空）、3%不出现
    Expected Result: 三档行为分毫不差
    Evidence: .sisyphus/evidence/task-17-inherit.txt

  Scenario: override不可删除（错误场景）
    Tool: Bash (pytest)
    Steps:
      1. 子节点override某约束 → 断言原约束仍记录在parent_history/origin字段
    Expected Result: 可覆盖不可删
    Evidence: .sisyphus/evidence/task-17-override.txt
  ```

  **Commit**: YES - `fix(breakpoint-g): 约束继承传递(TDD)` - backend/app/domains/creation/constraint/constraint_inheritor.py, 测试

- [ ] 18. A2模组拓扑树+策划分析器

  **What to do**:
  - 新建 `backend/app/domains/creation/a2/module_topology.py`：A2模组拓扑维度树（Pydantic树：模组→章节→地点（**边界：最多到地点拓扑关系与风格约束，LOC/STY词典承载）→钩子位），节点含必填度标记
  - `planning_analyzer.py`：PlanningAnalyzer
    - 输入：**用户显式选定的A1图谱（upstream_graph_id，默认=最新已定稿A1图谱）+其结构化文件**——前置校验：所选图谱stage=A1且status=finalized（draft/stale均提示：draft→"请先完成定稿"；stale→返回变更集提示"上游已变更，建议重新定稿或知悉风险继续"，**不阻断，继续须留痕**）
    - LLM分析产出：游戏内容建议（玩法DNA对照）+ **类似IP推荐**（LLM从IP知识推荐3-5个相似IP+借鉴点）+ 风险提示
    - 输出结构化：PlanningAnalysis{game_content, similar_ips, style_constraints, open_questions}
  - TDD（FakeProvider）：分析产出结构/输入校验 ≥6用例

  **Must NOT do**: A2不生成具体场景细节（那是A3的边界）；不修改A1字段（只读A1）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: A2域模型+LLM分析链设计
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: T19, T20
  - **Blocked By**: T6（种子风格）, T16（A1图谱输入）

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:246-266` — REGION层职责（A2区域填充）与SOC/LAW典型约束
  - `backend/app/models/dimension.py` CreationLayer — REGION层定义
  - `backend/app/domains/creation/seed/seed_engine.py` — 分析引擎类结构范例

  **Acceptance Criteria**:
  - [ ] 拓扑树含"模组/章节/地点"3层+地点节点含loc_topology/style字段
  - [ ] 分析器测试全绿（similar_ips 3-5项、open_questions非空）

  **QA Scenarios**:
  ```
  Scenario: 策划分析产出
    Tool: Bash (pytest FakeProvider)
    Steps:
      1. PlanningAnalyzer.analyze(a1_file) 
      2. 断言返回含game_content(非空)、similar_ips(3<=n<=5, 每项含name+借鉴点)、style_constraints(STY词典合法值)
    Expected Result: 分析结构完整
    Evidence: .sisyphus/evidence/task-18-analysis.txt

  Scenario: A1文件缺失（错误场景）
    Tool: Bash
    Steps:
      1. analyze(None或空文件) → 断言抛ValueError含"需要先完成A1"
      2. analyze(未定稿draft文件) → 断言抛ValueError含"请先完成A1定稿"（graph_id为空拦截）
    Expected Result: 前置条件校验（含定稿校验）
    Evidence: .sisyphus/evidence/task-18-guard.txt
  ```

  **Commit**: YES - `feat(a2): 模组拓扑树+策划分析器(TDD)` - backend/app/domains/creation/a2/{module_topology.py, planning_analyzer.py}, 测试

- [ ] 19. A2 AGENTS决策+报告

  **What to do**:
  - 新建 `backend/app/domains/creation/a2/decision_agent.py`：多轮决策循环——针对open_questions逐项向用户提问（选项来自分析+词典）→ 用户答→收敛 → 产出A2'文件（含TRPG标注ip_type="TRPG"免费线默认 + 游戏内容 + 模组拓扑初稿填充）
  - `report_generator.py` + `state/report_store.py`：策划分析报告（分析+决策记录+最终方案）PDF风格Markdown **完整实现免费可看可下载**；`保存到我的存档`动作带tier检查占位（`# TODO: tier>=VIP 启用云端存档`——当前直接本地存档）
  - API（并入a2_routes或新建）：POST /analyze、POST /decide、GET /report/{id}
  - TDD：决策收敛循环/报告字段完整 ≥6用例

  **Must NOT do**: 不写"VIP才能看报告"的拦截逻辑（分级留后期，免费全开放）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `writing`（报告是代码生成物）

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: T22
  - **Blocked By**: T5（tier占位）, T18

  **References**:
  - `backend/app/domains/creation/a1/guide_engine.py`(T13) — 多轮会话模式复用
  - `backend/app/api/seed_routes.py` — generate/confirm两段式会话API模式
  - `backend/app/config/features.py` — 功能开关模式（若需premium flag）

  **Acceptance Criteria**:
  - [ ] 决策循环测试绿；报告含分析/决策/方案三段
  - [ ] grep报告相关代码无tier拦截条件判断

  **QA Scenarios**:
  ```
  Scenario: 决策→A2'文件
    Tool: Bash (curl)
    Steps:
      1. POST /api/a2/analyze {upstream_graph_id} → 得session与questions
      2. POST /api/a2/decide {session_id, decisions:[...]} → 断言200含a2_prime_file（ip_type="TRPG"）
      3. GET /api/a2/report?session_id={session_id} → 断言含similar_ips与decisions记录
    Expected Result: 分析→决策→报告闭环
    Evidence: .sisyphus/evidence/task-19-decide.txt

  Scenario: 免费无拦截（错误场景反向验证）
    Tool: Bash
    Steps:
      1. 以tier=FREE用户调用报告获取 → 断言200全文返回
    Expected Result: 免费用户完整可用
    Evidence: .sisyphus/evidence/task-19-free.txt
  ```

  **Commit**: YES - `feat(a2): AGENTS决策循环+策划报告(免费完整)` - backend/app/domains/creation/a2/{decision_agent.py, report_generator.py}, state/report_store.py, 测试

- [ ] 20. 骰子投影器

  **What to do**:
  - TDD先写：`tests/unit/domains/a2/test_dice_projector.py`
  - 新建 `backend/app/models/template.py`：DiceTemplate（骰子模式/判定方向/代价函数/成功层级/临界规则——字段对齐层级图"骰子设定·5维映射"）+ CharacterTemplate（身份/属性/技能/背景/力量关联）
  - 新建 `backend/app/domains/creation/a2/dice_projector.py`：**投影器=确定性查询器（零LLM）**——从A2'图谱查询 ACT约束(dice_mode/check_direction/...) + 骰子设定映射节点 → 组装DiceTemplate；模板记录来源节点id列表（溯源）
  - 投影可重复：图谱变→重新投影→新模板版本（v+1）

  **Must NOT do**: 投影器内不得调LLM（纯确定性）；不发明图谱中不存在的数值（缺省用模板默认+标记unresolved）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: "模板=投影"核心机制的第一个实现，模式要立对
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3
  - **Blocks**: T21, T22
  - **Blocked By**: T18（A2'图谱）

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:95-100` — 骰子设定5维映射（投影字段权威来源）
  - `backend/app/models/knowledge_graph.py` — 图查询API
  - `backend/app/models/dimension.py` ActOutput — dice_mode等结构化字段（T9产物）

  **Acceptance Criteria**:
  - [ ] 投影器测试绿（映射正确/缺省unresolved/版本递增 ≥5用例）
  - [ ] 投影器源码grep无provider/LLM调用

  **QA Scenarios**:
  ```
  Scenario: 投影正确性
    Tool: Bash (pytest)
    Steps:
      1. 构造含 dice_mode=d20_linear 的A2'图 → project()
      2. 断言DiceTemplate.dice_mode=="d20_linear" 且 source_nodes非空
    Expected Result: 图谱→模板确定性映射
    Evidence: .sisyphus/evidence/task-20-project.txt

  Scenario: 缺省标记（错误场景）
    Tool: Bash (pytest)
    Steps:
      1. 图中无check_direction → 断言模板该字段=默认值且unresolved标记含"check_direction"
    Expected Result: 缺数据不瞎编
    Evidence: .sisyphus/evidence/task-20-unresolved.txt
  ```

  **Commit**: YES - `feat(a2): 骰子投影器+模板模型(TDD)` - backend/app/models/template.py, backend/app/domains/creation/a2/dice_projector.py, 测试

- [ ] 21. 角色投影器

  **What to do**:
  - 新建 `backend/app/domains/creation/a2/character_projector.py`：输入=**图谱+骰子模板（二者一起，按用户描述）** → 查询NPC/Character节点+SOC关系+力量体系关联 → 属性框架按DiceTemplate的骰子模式适配（d20线性→属性修正制；骰池→骰数制）→ CharacterTemplate
  - 角色卡含：身份三阶段（社会→维度→超越，玩法DNA）、初始属性、与地点拓扑的关系钩子
  - TDD ≥5用例（骰子模式适配两种、SOC关系注入背景、溯源）

  **Must NOT do**: 同T20——零LLM纯投影；不生成具体NPC名单（那是A3/用户游玩时的事，这里是"模板框架"）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: NO（依赖T20的DiceTemplate输入）
  - **Parallel Group**: Wave 3（T20后段启动）
  - **Blocks**: T22
  - **Blocked By**: T20

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:91-94` — 玩家身份三阶段（角色卡身份线）
  - `backend/app/models/template.py`(T20) — CharacterTemplate定义处
  - `.sisyphus/drafts/A模块层级图-含断点.md:246-266` — NPC层SOC/ACT典型约束

  **Acceptance Criteria**:
  - [ ] 测试绿：两种骰子模式适配正确、背景含SOC关系、溯源字段
  - [ ] 源码无LLM调用

  **QA Scenarios**:
  ```
  Scenario: 骰子模式适配
    Tool: Bash (pytest)
      1. 同图+两种DiceTemplate(d20_linear/pool) 分别project
      2. 断言属性框架分别为"修正制"/"骰数制"
    Expected Result: 骰子模板影响角色框架
    Evidence: .sisyphus/evidence/task-21-adapt.txt

  Scenario: 图中无NPC节点（错误场景）
    Tool: Bash (pytest)
      1. 空NPC图project → 断言返回"框架模板"（unresolved标记）而非异常
    Expected Result: 缺节点优雅降级
    Evidence: .sisyphus/evidence/task-21-empty.txt
  ```

  **Commit**: YES - `feat(a2): 角色投影器(TDD)` - backend/app/domains/creation/a2/character_projector.py, 测试

- [ ] 22. ★主模组生成器（独立可用）+A2 API+A2''定稿

  **What to do**:
  - a2_routes.py 补齐：POST /file/{id}/dice-template、/character-template（调投影器存Store，均带upstream_graph_id?参数默认最新兼容图谱）、POST /file/{id}/finalize=**主模组生成器**
  - **主模组生成器独立化（组合架构要求）**：输入=选定A1图谱（upstream_graph_id，默认最新已定稿）；**两条线**：①携带策划决策（decision_session_id，经②产品策划器的会话）→决策驱动的拓扑填充；②不带策划→**直接从A1图谱生成**（免费TRPG默认标注+下位拓展）——产品策划是可选增强而非硬前置
  - 上游stale检查：所选A1图谱已stale→响应附变更集提示，不阻断（继续须留痕）
  - `module_poster.py`：finalize流水线——主模组展板数据（模组拓扑树+章节钩子+风格约束面板）+ 提示词组（每章节/地点生成GM提示词，注入ACT/NAR约束）+ **主模组结构化文件（原A2''）=图谱序列化导出**（图谱为事实源，文件是导出快照）+ 主模组图谱转换（经T12建约束拓扑边，**新graph_code=IPxxxx-M{实例号}-v1，实例号=该IP下已有M最大+1（兄弟主模组各占一号），parent_graph_code=所选A1图谱版本**）
  - TDD/集成：两条线各产出五件套（主模组展板数据/提示词组/主模组文件/图谱/模板引用）、无策划线不需要decision_session ≥7用例

  **Must NOT do**: A2''文件不得反向写回图谱（单向：图谱→文件）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: NO（收束任务，依赖T19-T21）
  - **Parallel Group**: Wave 3末
  - **Blocks**: T23, T27
  - **Blocked By**: T19, T21

  **References**:
  - `backend/app/domains/creation/a1/file_graph_converter.py`(T16) — 文件↔图谱转换复用模式
  - `backend/app/domains/creation/asset/prompt_builder.py` — 提示词组装（此处只用基础版，D注入在T24）
  - 本计划通信协议表 — finalize契约

  **Acceptance Criteria**:
  - [ ] finalize返回五件套齐全且A2''文件内容=图谱导出（roundtrip测试）
  - [ ] 提示词组每条含章节/地点标识

  **QA Scenarios**:
  ```
  Scenario: 定稿五件套
    Tool: Bash (curl)
    Steps:
      1. 前置：task-19的a2_prime_file_id
      2. POST dice-template → 200含DiceTemplate；POST character-template → 200
      3. POST finalize → 断言响应含 module_poster(拓扑树可视化数据)/prompt_group(>=1条)/a2_double_prime_file/graph
    Expected Result: A2收束产物完整
    Evidence: .sisyphus/evidence/task-22-finalize.txt

  Scenario: 单向序列化（错误场景）
    Tool: Bash (pytest)
    Steps:
      1. 篡改A2''文件的某字段 → 重新GET图谱 → 断言图谱未变
    Expected Result: 文件不回写图谱
    Evidence: .sisyphus/evidence/task-22-oneway.txt
  ```

  **Commit**: YES - `feat(a2): 投影API+主模组展板+A2''定稿` - backend/app/api/a2_routes.py, backend/app/domains/creation/a2/module_poster.py, 测试

- [ ] 23. A2前端工作台+展板组

  **What to do**:
  - `pages/a2/A2Workspace.tsx`：**入口GraphSelector（显式选A1图谱，默认最新，stale徽章+变更集提示）+ 顶部stale横幅（所选上游已变更时显示"建议重新定稿/知悉风险继续"）**；左GuidedChat（分析问答+决策选项）、右ModuleTopologyTree组件（树形折叠渲染拓扑树）+ 分析报告面板（similar_ips卡片+借鉴点）+ 决策完成后"生成展板"CTA（**也提供"跳过策划直接生成主模组"入口——免费TRPG默认线，组合架构要求**）
  - `pages/a2/A2Boards.tsx`：三tab（骰子展板DicePoster/角色展板CharacterPoster/主模组展板ModulePoster）+ PromptGroupViewer（提示词组复制按钮）
  - 展板视觉：骰子=概率分布图示+判定规则卡；角色=三阶段身份时间线+属性框架；主模组=拓扑树+章节卡；均含AI配图位（复用PosterBoard）
  - api/a2.ts 五端点对接；Vitest ≥4用例

  **Must NOT do**: 展板只读展示（编辑后续迭代）；不内嵌计算逻辑（数据全来自后端）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`frontend-ui-ux`]
  - **Skills Evaluated but Omitted**: `playwright`

  **Parallelization**:
  - **Can Run In Parallel**: YES（与Wave 3后段/Wave 4前段并行，契约已定）
  - **Parallel Group**: Wave 3末-Wave 4
  - **Blocks**: T32
  - **Blocked By**: T7, T8, T22

  **References**:
  - `frontend/src/components/poster/PosterBoard.tsx`(T8) — 展板骨架
  - `frontend/src/components/graph/WaveDivider.tsx` — 分组视觉惯例
  - 本计划通信协议表

  **Acceptance Criteria**:
  - [ ] vitest 4+用例绿；build成功
  - [ ] Playwright：/a2走完决策→展板三tab可见

  **QA Scenarios**:
  ```
  Scenario: A2全流程E2E
    Tool: Playwright
    Steps:
      1. goto /a2?file_id={a1的file_id} → 等分析问题 → 逐项选择决策 → 点"生成展板"
      2. 断言跳转/展示 /a2/boards，三tab（[data-tab="dice"|"character"|"module"]）切换正常
      3. 骰子tab断言含"d20"或"骰池"文案；截图
    Expected Result: 策划→决策→展板闭环
    Evidence: .sisyphus/evidence/task-23-a2-e2e.png

  Scenario: 未完成A1直接进A2（错误场景）
    Tool: Playwright
    Steps:
      1. goto /a2（无file_id且LocalStorage无记录）
      2. 断言显示引导提示"需先完成A1"+跳转链接，页面不白屏
    Expected Result: 前置条件缺失引导
    Evidence: .sisyphus/evidence/task-23-guard.png
  ```

  **Commit**: YES - `feat(frontend): A2工作台+三展板` - frontend/src/pages/a2/, api/a2.ts, components/a2/ModuleTopologyTree.tsx

- [ ] 24. ⚠️断点D修复：PromptBuilder约束注入

  **What to do**:
  - **授权关卡**：同协议，记录task-24-authorization.txt；pytest基线
  - 修改 `backend/app/domains/creation/asset/prompt_builder.py`：build()增加可选参数constraints（DimensionResultSet+层）——通过T11逻辑树get_injections(layer)取注入规则 → 按规则将约束字段注入对应8层模板段落（Layer1 World←LAW.world_structure/energy_flow；Layer4 Subject←SOC relations+ACT abilities；Layer5 Gameplay←ACT dice_mode/check_direction；Layer7 Material←WST cost_type+LAW conservation；Layer8 Lighting←NAR tone/era_stage）
  - **签名向后兼容**：constraints=None时行为与旧版完全一致（既有调用方零改动）
  - 调用方迁移：GenerationScheduler调用点传入真实约束（1处）
  - TDD：注入后8层各含预期约束片段/None时输出与基线diff为空 ≥6用例；超长prompt截断策略（>2000字符摘要化，错误场景用例）

  **Must NOT do**: 不破坏8层模板YAML结构；未授权不动手

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`test-driven-development`, `receiving-code-review`]
    - 修改核心生成链路，需严格回归
  - **Skills Evaluated but Omitted**: `using-git-worktrees`

  **Parallelization**:
  - **Can Run In Parallel**: YES（与T25并行——共享逻辑树但文件不同）
  - **Parallel Group**: Wave 4
  - **Blocks**: T28
  - **Blocked By**: T11

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:268-285` — 断点D权威注入清单（8层↔约束映射）
  - `backend/app/domains/creation/asset/prompt_builder.py` — 修改目标（8层模板逻辑）
  - `backend/app/domains/creation/asset/generation_scheduler.py` — 调用方
  - `backend/app/domains/creation/constraint/application_tree.py`(T11) — 注入规则来源

  **Acceptance Criteria**:
  - [ ] 注入/兼容/截断用例全绿；授权+基线+回归在案
  - [ ] constraints=None时与修改前输出逐字节一致（快照测试）

  **QA Scenarios**:
  ```
  Scenario: 约束注入8层
    Tool: Bash (pytest)
    Steps:
      1. 构造含LAW.world_structure=FLOATING_ISLANDS的约束 → build(constraints=...)
      2. 断言输出World层含"FLOATING_ISLANDS"相关描述
    Expected Result: 约束可见于prompt
    Evidence: .sisyphus/evidence/task-24-inject.txt

  Scenario: 向后兼容
    Tool: Bash (pytest)
    Steps:
      1. build()无constraints → 断言输出==修改前golden快照
    Expected Result: 旧调用零影响
    Evidence: .sisyphus/evidence/task-24-compat.txt
  ```

  **Commit**: YES - `fix(breakpoint-d): PromptBuilder约束注入(TDD+快照兼容)` - prompt_builder.py, generation_scheduler.py调用点, 测试

- [ ] 25. ⚠️断点E修复：PromptFusion约束感知

  **What to do**:
  - **授权关卡**：同协议，记录task-25-authorization.txt；pytest基线
  - 修改 `backend/app/domains/creation/asset/prompt_fusion.py`：3段式增强——Subject段+约束描述（LAW环境效果+SOC关系）；Relation段+约束继承（调T17 inheritor沿边传递）；Background段+WST状态效果
  - 签名向后兼容（constraints可选）；继承链：注入按T17权重档过滤
  - TDD ≥6用例（三段注入/继承过滤/兼容/继承为空时降级）

  **Must NOT do**: 不改变3段式中文标记格式（下游解析依赖）

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `systematic-debugging`

  **Parallelization**:
  - **Can Run In Parallel**: YES（与T24并行）
  - **Parallel Group**: Wave 4
  - **Blocks**: T28
  - **Blocked By**: T11, T17

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:287-297` — 断点E权威定义
  - `backend/app/domains/creation/asset/prompt_fusion.py` — 修改目标
  - `backend/app/domains/creation/constraint/constraint_inheritor.py`(T17) — 继承调用

  **Acceptance Criteria**:
  - [ ] 三段增强+兼容用例全绿；授权三件套在案

  **QA Scenarios**:
  ```
  Scenario: 三段注入
    Tool: Bash (pytest)
      1. 带约束build_prompt → 断言Subject段含LAW描述、Relation段含继承约束、Background段含WST效果
    Expected Result: 三段约束感知
    Evidence: .sisyphus/evidence/task-25-fusion.txt

  Scenario: 无继承约束降级（错误场景）
    Tool: Bash (pytest)
      1. 图无边 → 断言Relation段退化为原文且不报错
    Expected Result: 优雅降级
    Evidence: .sisyphus/evidence/task-25-degrade.txt
  ```

  **Commit**: YES - `fix(breakpoint-e): PromptFusion约束感知(TDD)` - prompt_fusion.py, 测试

- [ ] 26. ⚠️断点H修复：层间语义焦点模板

  **What to do**:
  - **授权关卡**：同协议，记录task-26-authorization.txt；pytest基线
  - 修改 `backend/app/domains/creation/constraint/dimension_generator.py`（或DimensionPromptBuilder所在文件）：system prompt增加"层间语义焦点"段——同一约束维度在6层不同关注点文案表（LAW在WORLD层="世界的物理法则是什么"宏观 / NPC层="该NPC遵守什么物理法则"角色级 / ASSET层="物品的物理属性"物品级，6维×6层=36条焦点文案，YAML配置）
  - TDD：焦点文案出现在对应层prompt、权重排序不变 ≥4用例

  **Must NOT do**: 不改权重逻辑（只加语义焦点段）

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 改prompt模板+配置，范围小（层级图注明"实现难度：低"）
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: YES（独立改善项，随时可做）
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:199-207` — 断点H权威定义（LAW三层示例）
  - `backend/app/domains/creation/constraint/dimension_generator.py` — DimensionPromptBuilder所在

  **Acceptance Criteria**:
  - [ ] 36条焦点文案配置存在且测试验证LAW三层示例逐字出现

  **QA Scenarios**:
  ```
  Scenario: 层间焦点生效
    Tool: Bash (pytest)
      1. NPC层生成prompt → 断言含"该NPC遵守什么物理法则"级文案
      2. WORLD层 → 断言含宏观文案且不含NPC级文案
    Expected Result: 层语义区分
    Evidence: .sisyphus/evidence/task-26-focus.txt

  Scenario: 焦点配置缺层（错误场景）
    Tool: Bash (pytest)
      1. 删YAML某层焦点条目 → 断言加载时报错指明缺失层（快速失败不静默）
    Expected Result: 配置不完整被显式拒绝
    Evidence: .sisyphus/evidence/task-26-config-guard.txt
  ```

  **Commit**: YES - `fix(breakpoint-h): 层间语义焦点模板` - dimension_generator.py, config/layer_focus.yaml, 测试

- [ ] 27. ★次级模组生成器（场景+资产扩写引擎）

  **What to do**:
  - 新建 `backend/app/domains/creation/a3/scene_expander.py`：
    - 输入：**用户显式选定的主模组图谱（upstream_graph_id，默认=最新MODULE图谱）** + 用户范围参数（哪些地点扩写/每地点场景数/每场景资产数——半自动，用户控量）；上游stale→变更集提示不阻断（留痕）
    - LLM扩写：地点→具体场景（Scene节点：氛围/功能/冲突钩子，NAR/WST约束经逻辑树注入prompt）→场景→资产清单（Item节点：名称/用途/视觉标签）
    - 产出次级模组结构化文件（stage=A3，场景+资产板块）+ 次级模组图谱（**新graph_code=IPxxxx-M{n}-S{实例号}-v1，实例号=父M范围内递增，parent_graph_code=所选主模组图谱版本**；新节点沿上游拓扑下挂，**遵守阶段权限：只建A3允许的边类型**CHAR_BELONGS_TO等，不碰A1/A2结构边）
  - TDD（FakeProvider）：范围控制/权限边类型白名单/数量上限 ≥6用例

  **Must NOT do**: 不得创建A1/A2阶段的骨架边（阶段权限硬约束）；单次扩写资产数上限（防LLM失控，如≤20/场景）

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: YES（Wave 4）
  - **Parallel Group**: Wave 4
  - **Blocks**: T28, T30
  - **Blocked By**: T22（A2''输入）

  **References**:
  - `.sisyphus/drafts/A模块层级图-含断点.md:340-343` — A3权限（可建Character/Item/Scene节点+边白名单）
  - `.sisyphus/drafts/A模块层级图-含断点.md:255-266` — SCENE/ASSET层职责
  - `backend/app/domains/creation/a1/file_graph_converter.py`(T16) — 转换复用

  **Acceptance Criteria**:
  - [ ] 测试绿：指定2场景×3资产 → 恰好产出该数量节点；越权边被拒用例
  - [ ] A3图谱节点全部source_stage="A3"

  **QA Scenarios**:
  ```
  Scenario: 定量扩写
    Tool: Bash (pytest FakeProvider)
      1. expand(scope=地点A, scenes=2, assets_per_scene=3)
      2. 断言新增Scene节点2个、Item节点6个、全部挂载于地点A子图
    Expected Result: 数量与挂载精确
    Evidence: .sisyphus/evidence/task-27-expand.txt

  Scenario: 越权边拒绝（错误场景）
    Tool: Bash (pytest)
      1. 构造A3试图建GEO_CONTAINS(A1结构边) → 断言抛PermissionError
    Expected Result: 阶段权限生效
    Evidence: .sisyphus/evidence/task-27-permission.txt
  ```

  **Commit**: YES - `feat(a3): 场景+资产扩写引擎(TDD)` - backend/app/domains/creation/a3/scene_expander.py, 测试

- [ ] 28. A3标签→提示词→图片生成

  **What to do**:
  - 新建 `backend/app/domains/creation/a3/asset_prompt_extractor.py`：
    - 图谱提取场景+资产视觉标签（视觉关键词+材质+风格约束STY）
    - 组装prompt：PromptBuilder.build(constraints=...)（**断点D成果首次实战**）+ PromptFusion三段（**断点E成果**）→ 每资产一条提示词
  - 集成GenerationScheduler+ImageGenerator：批量生图（Wave调度+信号量限流，复用现有）+ 结果持久化AssetStore + 审批流复用（approved资产才进大厅）
  - API：GET /file/{id}/prompts、POST /assets/generate {file_id, asset_ids} → {job_id}、GET /jobs/{job_id}（轮询）
  - RED拦截（bonus）：生成前过RedOutput.forbidden检查（简单关键词匹配版）
  - TDD/集成 ≥5用例

  **Must NOT do**: prompt超长必须截断（T24策略复用）；未审批资产不进大厅数据包

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `playwright`

  **Parallelization**:
  - **Can Run In Parallel**: NO（依赖T24/T25注入就绪+T27图谱）
  - **Parallel Group**: Wave 4后段
  - **Blocks**: T29, T30
  - **Blocked By**: T24, T25, T27

  **References**:
  - `backend/app/domains/creation/asset/generation_scheduler.py` — Wave调度复用
  - `backend/app/ai/image_generator.py` — 生图Provider
  - `backend/app/state/asset_store.py` — 资产持久化+状态机
  - `backend/app/api/assets_routes.py` — 审批API模式

  **Acceptance Criteria**:
  - [ ] prompts端点返回每资产一条含约束痕迹的提示词
  - [ ] 生图job全流程：pending→generating→pending_review（FakeProvider或local provider测试）
  - [ ] RED命中用例：forbidden词的prompt被拦截

  **QA Scenarios**:
  ```
  Scenario: 标签→提示词→生图链
    Tool: Bash (curl)
    Steps:
      1. GET /api/a3/file/{id}/prompts → 断言每条含资产名+风格关键词
      2. POST /api/a3/assets/generate {asset_ids} → job_id
      3. 轮询GET /jobs/{job_id} 至status=done → 断言每资产有image_url或failed原因
    Expected Result: 全链可跑（可用local provider）
    Evidence: .sisyphus/evidence/task-28-pipeline.txt

  Scenario: RED拦截（错误场景）
    Tool: Bash (pytest)
      1. RedOutput.forbidden=["血腥"] + prompt含"血腥" → 断言拦截并返回原因
    Expected Result: 红线前置过滤生效
    Evidence: .sisyphus/evidence/task-28-red.txt
  ```

  **Commit**: YES - `feat(a3): 标签提取→约束注入提示词→批量生图` - backend/app/domains/creation/a3/asset_prompt_extractor.py, a3_routes.py, 测试

- [ ] 29. A3前端工作台

  **What to do**:
  - `pages/a3/A3Workspace.tsx`：**入口GraphSelector（显式选主模组图谱，默认最新，stale徽章）+ 顶部stale横幅**；左扩写对话（范围/数量设置面板：地点多选+场景数+资产数滑块）→ 中场景/资产清单（卡片：名称/状态/缩略图占位）→ 右图片生成管理（选资产→生成→进度条→approve/reject复用审核交互模式）
  - GraphPreview嵌入显示A3图谱增长
  - api/a3.ts对接；Vitest ≥3用例

  **Must NOT do**: 不做图片编辑器（只查看/审批）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`frontend-ui-ux`]
  - **Skills Evaluated but Omitted**: `playwright`

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4末
  - **Blocks**: T32
  - **Blocked By**: T7, T8, T28

  **References**:
  - `frontend/src/pages/graph/AssetReview.tsx` — 审批交互模式复用
  - `frontend/src/pages/graph/GraphAssetReview.tsx` — Wave分组+进度模式复用
  - 本计划通信协议表

  **Acceptance Criteria**:
  - [ ] vitest绿；build成功
  - [ ] Playwright：设置范围→触发扩写→清单出现→生图按钮可见

  **QA Scenarios**:
  ```
  Scenario: A3扩写E2E
    Tool: Playwright
    Steps:
      1. goto /a3?file_id={a2''的id}
      2. 勾选地点A、场景数=2 → 提交 → 断言清单出现2张场景卡
      3. 选一资产点生成 → 断言进度条出现并轮询到终态；截图
    Expected Result: 扩写+生图可视闭环
    Evidence: .sisyphus/evidence/task-29-a3-e2e.png

  Scenario: 范围超限（错误场景）
    Tool: Playwright
    Steps:
      1. 资产数滑块拉到>20 → 断言按钮禁用+提示"单场景资产上限20"
    Expected Result: 上限防护可见
    Evidence: .sisyphus/evidence/task-29-limit.png
  ```

  **Commit**: YES - `feat(frontend): A3工作台` - frontend/src/pages/a3/, api/a3.ts

- [ ] 30. 大厅后端API

  **What to do**:
  - 新建 `backend/app/domains/creation/a3/lobby_loader.py` + `api/lobby_routes.py`：
    - GET /api/lobby?graph_code=（**装配=选定图谱包**，默认最新可装配图谱） → 大厅数据包：{scenes（场景树+背景图URL——approved资产按场景分组）、character_card（CharacterTemplate投影最新版）、dice_panel（DiceTemplate）、prompt_group（GM提示词组）、terminal_config（场景YAML适配现有/api/action引擎）}
    - 图片"编码载入"：返回资产图URL列表+场景挂载映射（复用现有场景资产挂载机制：approved资产自动渲染到场景）
  - TDD：数据包组装/仅approved过滤/缺图降级（占位符URL）≥5用例

  **Must NOT do**: 大厅不改写游戏规则引擎（只喂数据）；未审批资产绝不进包

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`test-driven-development`]
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: NO（依赖T28资产就绪）
  - **Parallel Group**: Wave 4末
  - **Blocks**: T31
  - **Blocked By**: T28

  **References**:
  - `backend/app/engine/world_loader.py` — 场景YAML加载（terminal_config适配）
  - `backend/app/state/asset_store.py` — approved过滤
  - `backend/app/api/routes.py` — /api/scene响应结构（大厅场景视图对齐）

  **Acceptance Criteria**:
  - [ ] 测试绿：包结构五段齐全、rejected资产不出现在images
  - [ ] 端点200且scenes[].background指向真实文件或占位符

  **QA Scenarios**:
  ```
  Scenario: 大厅数据包
    Tool: Bash (curl)
    Steps:
      1. 前置：A3含1 approved+1 rejected资产
      2. GET /api/lobby?file_id= → 断言images只含approved、含character_card与dice_panel、prompt_group非空
    Expected Result: 过滤正确+五段齐全
    Evidence: .sisyphus/evidence/task-30-lobby.json

  Scenario: 无资产降级（错误场景）
    Tool: Bash (curl)
      1. 空A3文件调lobby → 断言200且images为空数组+占位符标记（不500）
    Expected Result: 空数据优雅降级
    Evidence: .sisyphus/evidence/task-30-empty.txt
  ```

  **Commit**: YES - `feat(lobby): GM大厅数据API` - backend/app/domains/creation/a3/lobby_loader.py, api/lobby_routes.py, 测试

- [ ] 31. 大厅前端

  **What to do**:
  - `pages/lobby/Lobby.tsx`：三区布局——左CharacterCardPanel（角色卡）+ DicePanel（骰子规则卡，点击可模拟投骰动画）；中SceneView增强版（背景=A3资产图，资产热点标注）；右Terminal（复用，GM输入指令）
  - 场景切换：scenes列表切换背景与资产挂载；提示词组浮层（GM查看当前场景提示词）
  - api/lobby.ts；资产变更监听复用 `echo-assets-changed` 事件
  - Vitest ≥3用例

  **Must NOT do**: 不重写Terminal/SceneView内部逻辑（props/组合扩展）

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`frontend-ui-ux`]
  - **Skills Evaluated but Omitted**: `test-driven-development`（组件测试随写）

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4末
  - **Blocks**: T32
  - **Blocked By**: T8, T30

  **References**:
  - `frontend/src/components/terminal/SceneView.tsx` — 场景背景渲染（扩展挂载点）
  - `frontend/src/components/terminal/Terminal.tsx` — 直接复用
  - `frontend/src/hooks/useScene.ts` — 事件驱动刷新模式
  - `frontend/src/components/terminal/StatusPanel.tsx` — 面板布局参考

  **Acceptance Criteria**:
  - [ ] vitest绿；build成功
  - [ ] Playwright：/lobby加载出场景背景+角色卡+骰子面板+终端

  **QA Scenarios**:
  ```
  Scenario: 大厅E2E
    Tool: Playwright
    Steps:
      1. goto /lobby?file_id={含approved资产的id}
      2. 断言 [data-testid="scene-bg"] 有背景图、[data-testid="character-card"] 含角色名、[data-testid="dice-panel"] 可见
      3. 终端输入"查看周围" → 断言有叙事输出；截图
    Expected Result: GM大厅四要素齐全可交互
    Evidence: .sisyphus/evidence/task-31-lobby-e2e.png

  Scenario: 无效file_id（错误场景）
    Tool: Playwright
    Steps:
      1. goto /lobby?file_id=nonexistent
      2. 断言显示"未找到模组数据"提示+返回A3链接，不白屏
    Expected Result: 错误参数优雅处理
    Evidence: .sisyphus/evidence/task-31-invalid.png
  ```

  **Commit**: YES - `feat(frontend): GM大厅` - frontend/src/pages/lobby/, api/lobby.ts

- [ ] 32. 端到端集成验证

  **What to do**:
  - 新建 `backend/scripts/e2e_smoke.py`：全链自动演练——register→a1 seeds→session→chat×10（每板块必答各1次，走完状态机）→finalize（★A1图谱化时点，断言返回graph_id与graph_code且编码匹配`^IP\d+-W1-v1$`格式）→file→graph→poster→a2 analyze（前置校验已定稿通过）→decide→dice→character→finalize→a3 expand→prompts→generate（local provider或mock）→approve→lobby——每步断言关键字段，输出PASS/FAIL报告
  - 前端Playwright全页冒烟spec：/a1对话→/a2决策→/a3生图→/lobby游玩（复用各任务E2E场景串联）
  - 全部输出存evidence；失败逐项修复（小修直接改，大修记录并回报）

  **Must NOT do**: 不得为通过测试放宽断言（发现产品bug就修产品）

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: 全链调试需要跨模块理解
  - **Skills**: [`systematic-debugging`, `verification-before-completion`]
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: NO（收束）
  - **Parallel Group**: Wave 5
  - **Blocks**: T33
  - **Blocked By**: T15, T16, T23, T29, T31

  **References**:
  - 本计划通信协议表全部端点
  - 各任务QA场景（串联脚本骨架）
  - `backend/.env.example` — local provider配置（免外部API测试）

  **Acceptance Criteria**:
  - [ ] python scripts/e2e_smoke.py 退出码0，报告全PASS
  - [ ] playwright全页spec绿
  - [ ] evidence含完整链路日志

  **QA Scenarios**:
  ```
  Scenario: 全链无人工
    Tool: Bash
    Steps:
      1. 后端起服（ACTIVE_PROVIDER=local或mock配置）→ python backend/scripts/e2e_smoke.py
      2. 断言退出码0且报告含"ALL PASS"与每步耗时
    Expected Result: 一条命令验证整个A模块
    Evidence: .sisyphus/evidence/task-32-e2e-smoke.txt
  ```

  **Commit**: YES - `test(e2e): A模块全链冒烟` - backend/scripts/e2e_smoke.py, frontend/tests/e2e/amodule.spec.ts

- [ ] 33. 文档同步更新

  **What to do**:
  - README.md：路由表加6新页面、API表加5组新端点、断点状态A-H改为✅已修复、项目结构加新目录（domains/identity、a1/a2/a3、新Store、新前端页面）
  - 术语同步：全文"第X套"标注新名（A1·采集维度集等）
  - 新增"A模块使用指南"小节：从注册到大厅的10步用户旅程
  - 校验：文档内所有路径Test-Path存在、端点与代码一致

  **Must NOT do**: 不夸大状态（未做的不写成已完成，如tier路由标注"预留"）

  **Recommended Agent Profile**:
  - **Category**: `writing`
  - **Skills**: []
  - **Skills Evaluated but Omitted**: `frontend-ui-ux`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 5
  - **Blocks**: F1-F4
  - **Blocked By**: T32

  **References**:
  - `README.md` — 更新目标
  - 本计划架构章节与通信协议表 — 内容来源

  **Acceptance Criteria**:
  - [ ] README路由表6新行、API表17新端点行、断点速查表全部✅
  - [ ] 文档路径校验脚本0缺失

  **QA Scenarios**:
  ```
  Scenario: 文档一致性
    Tool: Bash
    Steps:
      1. grep -c "a1/chat\|a2/decide\|a3/expand\|api/lobby" README.md — 断言>=4
      2. 抽查README提到的5个新文件路径 Test-Path 均存在
    Expected Result: 文档与实现一致
    Evidence: .sisyphus/evidence/task-33-docs.txt
  ```

  **Commit**: YES - `docs(readme): A模块全量文档同步` - README.md

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns (UserTier路由逻辑、登录代码、枚举修改、README旧断点改动) — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest` + `ruff` + `mypy`（后端）; `npm run build` + `oxlint` + `npx vitest run`（前端）. Review all changed files for: `as any`/`@ts-ignore`, empty catches, console.log in prod, commented-out code, unused imports, AI-slop（过度注释/无意义抽象/占位变量名）.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill)
  Start from clean state (delete LocalStorage, fresh SQLite). Execute EVERY QA scenario from EVERY task following exact steps, capture evidence. Test cross-task integration: A1→A2→A3→lobby handoffs. Test edge cases: empty answers, invalid enum, overlong prompts. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — no missing, no creep. Check "Must NOT do" compliance per task. Detect cross-task contamination. Verify 授权关卡 evidence for all 8 breakpoint tasks (T9-T12,T17,T24-T26).
  Output: `Tasks [N/N compliant] | 授权关卡 [8/8 evidenced] | Contamination [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

- 每任务一commit：`feat(a1): ...` / `fix(breakpoint-b): ...` / `feat(frontend): ...` / `docs(architecture): ...`
- 断点任务commit必须引用授权记录路径
- T33文档同步单独commit

---

## Success Criteria

### Verification Commands
```bash
cd backend && pytest --cov=app                # Expected: all pass, cov >= 85%
cd frontend && npm run build                  # Expected: exit 0
cd frontend && npx vitest run                 # Expected: all pass
cd frontend && npx playwright test            # Expected: all pass
# 全链路（T32脚本）:
python scripts/e2e_smoke.py                   # Expected: 全部端点200，大厅返回图片URL
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass（pytest+vitest+playwright）
- [ ] 8个断点任务全部有：授权记录+pytest基线+回归验证证据
- [ ] 全链路可跑通：新用户→种子→引导→IP展板→策划→模板→展板→扩写→生图→大厅
