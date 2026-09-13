
## 2026-09-04 Session Start (Atlas)
- Backend venv: H:\UGC\backend\.venv\Scripts\python.exe (use `.venv\Scripts\python.exe -m pytest`)
- Pytest baseline BEFORE changes: 833 passed, 2m02s. Coverage gate fails (74.21% < 85%) - PRE-EXISTING, not ours. Judge success by "833+ passed, 0 failed".
- Plan says 692 baseline - stale count; real is 833.
- Test paths in plan are ambiguous: actual = backend/tests/unit/a1/test_contracts/ (run from backend dir) or repo root `pytest backend/tests -q`.
- Working dir: H:\UGC (win32). Python on PATH has pytest too but use venv.

## T4 (open_questions C6/C7 model)
- OpenQuestionLog is a pydantic BaseModel wrapping items: list[OpenQuestion]; upsert preserves answered/skipped; from_bare_list assigns oq-NNN ids, all pending.
- Single-file pytest triggers project --cov-fail-under=85 -> use --no-cov for scoped runs; full-suite runs unaffected.
- tests/unit/a1/test_contracts/ needed __init__.py (tests/unit/a1/ already had one).

## T3 (tier map + GraphNode.tier) — 2026-09-04
- GraphNode.tier added as int | None = None; old node dicts deserialize with tier=None (verified by test).
- TIER_MAP lives in app/domains/creation/a1/tier_map.py; keys asserted == module_ids() via module_tier_coverage().
- Gotcha: parallel pytest runs lock backend/.coverage — use -o addopts="" (or unique COVERAGE_FILE) to bypass coverage when running targeted tests.
- Chinese module ids must be verbatim: 世界本体/力量体系/地理空间/文明与社会/历史时间线/视觉设计/玩法设计DNA/骰子设定/IP定位/设定边界.

## T1 graphify.py SIR 契约 (2026-09-04)
- 治理文档 §4 权威 schema：entries 是 [{anchor, items:[{title,content,children}]}] 两层结构 → 用 AnchorEntries(anchor,items) + EntryItem(title,content,children) 递归模型，GraphifyResult.entries: list[AnchorEntries]
- EdgeSpec 用 from_ = Field(alias='from') + populate_by_name，兼容 LLM JSON 的 'from' 关键字
- anchor 合法性直接 set(all_subfield_keys()) 对照；DIM.tag 白名单 STRUCTURED_FIELDS[dim] 列表内 tag 判断（RED 无结构字段）
- 词表以参数注入（allowed_relations: set[str]），不 import concept_edge_vocab（T2 并行改词表）
- GRAPHIFY_TIMEOUT 用 importlib.reload 测 env 覆写（模块级常量在 import 时读 env）
- sanitize: 去':' → \s+ 归一单空格 → strip → 截32字 → 空则'未命名'；depth_id 解析 id[2:].split(':',2)
- dedupe 以 sanitize 后 title 为键，保首条，重复标题返回列表供 caller 出 warning
- 测试 36 passed / 1 xfailed（--no-cov；覆盖率 85% 门禁是全局预存配置，与单测目录无关）

## T5 (2026-09-04) — contract test skeleton + StubLLMProvider
- tests/unit/ has __init__.py but tests/ does NOT → cannot import 	ests.unit.a1.conftest; use factory fixture make_stub_llm from conftest instead of direct import.
- pytest config: asyncio_mode=auto in pyproject.toml → no @pytest.mark.asyncio needed on async tests.
- StubLLMProvider in tests/unit/a1/conftest.py: modes = response dict / raise_error / sleep_seconds (asyncio.sleep); mirrors FakeProvider pattern from test_concept_edge_extractor.py.
- xfail(strict=True) + pytest.fail("not implemented") body = safe placeholder pattern: red now, turns green when implementer replaces body.
- AXIS_SLOTS in concept_edge_vocab.py is [(axis_path, slot_values)] — slot values are NOT relation names; don't assert membership in VOCAB_RELATION_NAMES.
- T2 vocab + T3 tier_map + open_questions.py landed before T5 → C4/C5 written as real assertions (green), not placeholders.
- Full suite after T5: 885 passed / 15 xfailed / 0 failed (baseline was 833).


## T2 词表编译整合 (concept_edge_vocab.py)
- 基线 16 边已完整覆盖 v0.4 §3 总表（7★+5◆+4◇），无需重构；本任务增量补 §2 槽位注册表的 tier 间派生边 10 条（9◆+1★），总计 26 边（8 rule + 14 semantic + 4 structure）。
- 新增中文短边名遵循设计计划 §5.1 形状范本：力量源自(tier0→1)/中心位于(tier2→0)/争夺焦点/纪元塑史(tier2→3)/时间起于(tier0→3)/存在塑力/视觉投影/身份锚定/成长映射/CONSTRAINT_LIMITS（边界锚定）(tier6→0-4)。
- VOCAB_RELATION_NAMES 由 EDGE_VOCAB 自动派生（frozenset），extractor 无需改动即获得新边。
- 测试注意：tests/unit/a1/test_concept_edge_vocab.py 硬编码边数/级分布，扩词表须同步；C4 契约测试(test_contracts/test_c4_vocab_closed.py)偶发全量套件下顺序污染失败，单跑/重跑即过，疑与其它测试的全局状态泄漏有关（未定位，非本任务改动引入）。
- 证据: evidence/task-2-vocab.txt (全量词表), task-2-vocab-negative.txt (表外拒绝), task-2-vocab-distribution.txt (分布)。

## T6 graphify_llm (2026-09-04)
- graphify.py 追加：build_graphify_prompt（answers 全文/不可动清单/C7 证据槽/26 词表/tier 表/d: 编发规则）+ parse_graphify_raw（D4：缺失=空，类型错=抛→整体降级）+ apply_graphify_validation（rule1 非法锚点丢弃 / rule3 表外 relation 转 open_questions+移除 / rule2 幻觉引用边丢弃 / rule4 DIM.tag 白名单外丢弃 / rule5 children 仅 warning）+ graphify_llm（asyncio.run(wait_for(chat_json, timeout))，任何异常 → success=False+warning="graphify failed: …"，永不抛）
- timeout 可 monkeypatch graphify.GRAPHIFY_TIMEOUT 或传 timeout= 参数注入（默认读 import-time 常量）
- warning 分域前缀 [entries]/[edges]/[constraint_fields] 供组装器分域兜底；部分接受时 success 仍 True
- 测试用程序化取 VALID_ANCHOR=sorted(all_subfield_keys())[0]、VALID_CONSTRAINT_KEY=STRUCTURED_FIELDS 构造，避免控制台中文乱码硬编码风险；16 passed
- 注意：full a1 套件中 test_a1_routes::test_finalize_graph_topology 失败 0==1（分条目 TREE 边）——a1_routes.py/test_a1_routes.py 是 T7 并行修改中，非 T6 改动引入（T6 仅动 graphify.py + 新测试文件）
- 证据: evidence/task-6-happy.txt / task-6-timeout.txt / task-6-negative.txt


## T7 (2026-09-04) dual-tree assembly
- `_build_graph(session, file_rec, llm_result=None)`：None=全降级现状路径，旧测试全绿。新 helper 同文件：`_assemble_depth_tree` / `_merge_llm_edges` / `_assemble_assertions`。
- 深度树 serial 三段式 `D{module_serial}-{entry_serial}-{k}`——依赖"仅计有答案模块/条目"的 serial 计数，fixture 需同时答 IP定位.name + 世界本体 origin/existence 才得 D2-2-*。
- level=4 节点有两族：`d:` 深度节点与 `term:` 概念词节点；拓扑不变量过滤要用 id 前缀 `d:`，不能只看 level。
- dead-edge 死区：`_build_graph` 每次重建 `rec["dead_edges"]=[]`，finalize 的 confirmed 快照循环用 `setdefault` 追加（T7 以 3 行替换了旧 ：762 静默 continue——虽在 finalize 内但是 §5c 明确指令，门禁/issuer/visual-bg 保护块未动）。
- 等式不变量 `input_edges == graph_edges + dead_edges` 只在 _merge_llm_edges 内成立；rejected 边暂不过滤（保持等式，T11 处理确认流）。
- GraphifyResult 构造时 `from` 是别名：用 `EdgeSpec(**{"from": ...})`。
- constraint_fields 断言 Phase1 必然触发（无 cst: 节点），仅 log_event 不 raise——T11 接线 apply_constraints 后消失。
- git diff --stat 中 graphify.py/PROJECT_STATE.md/boulder.json 的变化来自并行 T6/orchestrator，非本任务写入。

## T9 frontend L2/L3 adaptation (2026-09-04)
- isConceptTermNode 收紧为仅 	erm: 前缀（原 || level===4 防御分支移除，签名放宽为 {id:string}）；4 调用点 ：216/:543/:961 + termMeta(:219) 核对无语义回归。
- 新增导出 isDepthNode(id)=id.startsWith('d:')；d: 节点渲染分支：细 1px 簇色边框(termClusterColor)+description 全文+title tooltip；MiniMap 同步簇色。
- 关键 gotcha：收紧后 ：543 的 term 行 filter 不再捞到 d: 节点（原靠 level===4 OR），level4 节点会因 LEVEL_Y_POSITIONS 无 4 而无坐标 → 必须在 layoutNodes 里给 d: 节点补一行（新增本地 DEPTH_SPACING=220/y=840 行块，未动 calculateNodePosition）。
- L2 摘要渲染：labelWrapper 加 WebkitLineClamp:2 + title=description 全文 tooltip（labelExtraStyle/toilet 两个 per-branch 变量实现）。
- types/graph.ts GraphNode 增加 tier?: number（对齐后端 T3）。
- 前端 vitest 基建存在（vitest 4 + testing-library），新建 __tests__/A1KnowledgeGraph.predicate.test.ts 判定单测 5 passed（scoped run，36s，主要是 setup/env 开销）。
- npx tsc --noEmit PASS；证据 evidence/task-9-predicate.txt。
- git diff --stat 中 a1_routes.py 属并行 T8，非本任务写入。

## T10 (contracts green) — 2026-09-04
- test_contracts 全绿：79 passed / 4 xfailed（3×C7=T17 范围 + 1×T11 占位 runtime-assertion）。
- graphify_llm 内部用 asyncio.run()：**不可在运行中的 event loop 里调用**（pytest-asyncio auto 模式下 async 测试内调用会降级 success=False）。所有调 graphify_llm 的测试必须是同步 def（与 test_graphify_llm.py 现有范式一致）。asyncio.TimeoutError str 为空 → warning 只能断言 startswith("graphify failed")。
- GraphifyResult 构造时 dict→AnchorEntries/EntryItem 会自动 coerce，但事后对 .items/.entries append 原始 dict 不会（pydantic 不再校验）→ 测试里追加条目须用 EntryItem(...)。
- EdgeType 是 str enum，值为小写（'tree'）；比较用 dge_type == EdgeType.TREE，不要用 .value == "TREE"（后者其实也行但易错）。
- _build_graph 节点 id 无数字断言注意：bg_id = bg_{session_id[:8]}，session_id 含数字会污染断言 → 用纯字母 session_id。
- C2 五类负向全部经 parse_graphify_raw+apply_graphify_validation 拦截（分域 [entries]/[edges]/[constraint_fields]/children warning）；幻觉引用在 T7 _merge_llm_edges 还有第二道防线：落 dead_edges(reason=endpoint_missing) —— 测试两层都断言了。
- _build_graph 会调 apply_constraints(graph, _build_dimension_result_set(session))；纯文本 answers（无 tag=val 片段）不会产生 cst 节点，对不变量测试无干扰。
- test_c3 序号同构实测：module serial 1..n（按答案顺序），entry "{m}-{e}"，depth "D{m}-{e}-{k}"；TREE 边数 == level≥2 节点数（module+entry+depth），roots 差集 == {bg}。


## T8 finalize × graphify 串联 (2026-09-04)
- finalize 新流程：provider 工厂（create_provider(load_provider_config())，try/except→None，与 extract-edges 同范式）→ graphify_llm(session, provider) → _build_graph(session, rec, llm_result)；graphify 永不抛，降级 warning 进 rec["finalize_warnings"]（常驻键，GET file 也输出默认 []）。
- T-B 阶段1 块整体移除：confirmed_edges 快照循环保留但只做 dead_edges 死区追加（reason=endpoint_missing，rejected 跳过）——不再重入图、不再恢复 term: 节点；concept_terms/open_questions 保持常驻键。
- 词表注意：T7 直构 EdgeSpec 的测试用「衍生」不经词表校验；走 graphify_llm 全链路必须用 VOCAB_RELATION_NAMES 实名（如「存在塑力」），否则 rule3 静默转 open_questions。
- graphify 降级触发点：stub 返回 {"unexpected":1} 不降级（D4 缺失字段默认空，success=True）——要触发解析失败需错误容器类型（如 module_summaries 给 list）。
- 测试迁移模式：旧 stage1 测试改为 finalize 后直接向 rec 注入 concept_terms + term: 节点（fixture 模拟 v0.4 遗留数据），继续验证阶段2 extract-edges / confirm/reject 行为不变；重定稿断言改为「边落 dead_edges + 词确认态快照保留」。
- provider stub 注入点：monkeypatch a1_routes.load_provider_config + a1_routes.create_provider（两个名字都在 a1_routes 命名空间）。
- 白名单偏差记录：test_a1_edges.py / test_concept_finalize_v2.py（原 whitelist 外）必须更新——它们 monkeypatch 已移除的 a1_routes.extract_concept_terms，且断言已退役的阶段1行为；0-failed 硬约束优先。
- 全量套件 928 passed / 4 xfailed / 0 failed（先前的 test_contracts 失败未复现）。证据: evidence/task-8-preserve.txt / task-8-degrade-e2e.txt / task-8-fixups.txt

## T12 L4/L5 banded layout (2026-09-04)
- T9 临时块已规范化：DEPTH_SPACING=220 提升进 calculateNodePosition 常量区；LEVEL_Y_POSITIONS 扩为 {0:-260,1:0,2:240,3:500,4:840,5:1000}（L4=840 保留 T9 值，因 term 行占 y=760；L5=1000 按计划）。
- d: 节点布局改为复用 level3 parentX 分组模式：tree 边建 depthParent map → L4 按 L3 父条目 x 分组居中，L5 按 L4 父 x 分组；先放 L4 再放 L5（positionedXById 传递 x）。calculateNodePosition 新增 level 4/5 + parentX 分支，export 供测试。
- fitView 适配画布变高：minZoom 0.2→0.15。MiniMap 深度色 T9 已有（isDepthNode→termClusterColor），未动。
- 图例新增「分条目」项：TERM_CLUSTER_COLORS[0] 1px 细边框方块（与 T9 d: 渲染一致）。
- 测试：新增 __tests__/A1KnowledgeGraph.layout.test.ts（6 用例：L4/L5 y 带、DEPTH_SPACING 间距+父 x 居中、无 parentX 回退、旧带不回归）；scoped vitest 2 files / 11 passed，tsc --noEmit PASS。证据 evidence/task-12-l4-layout.txt。Playwright 截图留给 F3。

## T16 degradation badge UI (2026-09-04)
- finalize_warnings 读取走 A1GraphSection.loadFileTerms 既有通道（GET /api/a1/file/{id} 响应加一行 finalize_warnings?: string[]），无需动 api/a1.ts。
- 角标：finalizeWarnings.length > 0 条件渲染，amber 色 + data-testid=degradation-badge；浮层非模态（absolute right-0 top-full z-20，不挡画布），警告按 [entries]/[edges]/[constraint_fields] 前缀映射 条目/边/约束 标签并 strip 前缀展示。
- tsc --noEmit PASS；Playwright 断言留 F3。证据 evidence/task-16-badge.txt。

## T14 concept-mode tier band layout (2026-09-04)
- layoutNodes 增加第三参 mode:'tree'|'concept'（默认 tree，零回归）；仅 level-2 模块层在 concept 模式走新分支。
- 新导出纯函数 layoutConceptModules(modules)->Map<id,{x,y,tierBand}>：tier 0-6 各占一纵列（col 升序，undefined tier 归 TIER_UNGROUPED=-1 哨兵列排最后），列内纵向堆叠；列组整体以 x=0 居中。常量 CONCEPT_TIER_COLUMN_SPACING=340 / ROW=220 / CONCEPT_MODULE_Y=240。
- TIER_LEGEND 7 色（0 存在基座#38bdf8/1 动力学#f472b6/2 显现#10b981/3 时间#fbbf24/4 表达#a78bfa/5 命题#60a5fa/6 治理#f87171）+ 无分组灰色虚线框；tierLegendColor() undefined→灰。
- 图例：concept 模式渲染 absolute top-16 right-4 面板 data-testid="tier-legend"（左上同位是可信级筛选器，右侧空）。
- 分组开关：现有 UI 无开关体系 → 常开（任务允许）；未加 toggle。
- 模块节点 rfNode.data.testId = tier-group-{tierBand}（React Flow 默认节点不落 DOM，Playwright 断言留给 F3 可改断 data 或换 custom node）。
- 派生边零改动：concept 模式边通道本就是 filteredEdges，tier 间语义边照常渲染。
- 测试：layoutConceptModules 4 用例（同 tier 同列异行 / 异 tier 列升序 / 无分组列最后 / 列组居中）；scoped vitest 2 files 15 passed（11 旧 + 4 新），tsc PASS。证据 evidence/task-14-tier-groups.txt。

## [2026-09-04] graphify live-LLM leakage into unit tests (task-15 fixup)
- finalize now calls graphify_llm with create_provider(load_provider_config()).
  On machines with .env ACTIVE_PROVIDER set (deepseek), unit tests that call
  /finalize get NON-DETERMINISTIC semantic edges -> edge_stats assertions break
  (semantic_total 9/14 instead of 3).
- Pattern: any test needing deterministic graph must monkeypatch
  app.api.a1_routes.graphify_llm to GraphifyResult(success=False, ...) (degrade
  path = pure TREE graph; warning lands in finalize_warnings).
- Do NOT assume "tests have no provider" — the .env is loaded.
- extract-edges endpoint + _compute_edge_stats semantics verified correct under
  v0.5; confirmed=false semantic edges still count into semantic_total.

## 2026-09-04 test-order pollution fix (task-15 fixup)
- Autouse fixture neutralizing finalize's LLM: patch a1_routes.load_provider_config + create_provider with a RAISING StubLLMProvider (not graphify_llm directly). graphify_llm catches any provider error -> degraded GraphifyResult(success=False), pure-TREE graph. Raising stub gives degraded semantics instantly; empty-response stub would give success=True (D4 partial acceptance) instead.
- Reason not to patch graphify_llm directly: several tests (test_a1_routes _t8_patch_provider, test_id_stability _stub_finalize) stub the provider factory and rely on the REAL graphify_llm chain running; a direct graphify_llm lambda breaks them (3 failures observed).
- monkeypatch override ordering: autouse fixture setup runs before test body, so per-test monkeypatch.setattr wins (last-write-wins). Verified by full-suite green.
- Signal for detecting real-LLM leakage in a suite: runtime. 280s -> 7.3s after fix.

## T18 stress script (2026-09-04)
- scripts/stress_graphify.py：手工解析 backend/.env（脚本不在 uvicorn 生命周期，load_provider_config 读不到 env，需 os.environ.setdefault 注入）。
- create_provider 在 app.ai.provider（不是 app.ai.config）；A1Session 最小构造只需 session_id/user_id（graphify 只读 answers/session_id）。
- Windows GBK 控制台：脚本内 sys.stdout.reconfigure(encoding='utf-8') + bash 侧 [Console]::OutputEncoding=UTF8 + Out-File -Encoding utf8，中文证据文件才不乱码。
- 真 deepseek 3 轮实测：输入 12,970 字符全部 success=True，延迟 16-20s，完整率 4/5（constraint_fields 缺是 LLM 白名单归类问题，非长度退化）。
- 分块触发线建议（写入治理文档附录 A1-T18）：输入 ≤10k 字符单调用安全，超过再分块；安全判据 success=True 且完整率 ≥4/5。
- 证据: evidence/task-18-run.txt (dry-run) / task-18-run-real.txt + task-18-real.json + task-18-stress-report.md。

## T17 (C6/C7 全链闭环) learnings
- GraphEdge 模型没有 rationale 字段——graphify 边的 rationale 会被丢弃；T17 用 rec["edge_rationales"]（key=_make_edge_key）持久化，测试断言走这里而非 graph_json。
- chat 通道拿不到 InterviewResult（handle_message 内部消化）——用 duck-typing（set_pending_open_question/take_open_question_answered）挂在 interviewer 实例上跨层传递，DegradingInterviewer 委托 + hasattr 降级，FakeInterviewer 测试替换也兼容。
- _INTERVIEWER 是惰性单例（跨测试缓存），测试注入用 monkeypatch.setattr(a1_routes, "_INTERVIEWER", fake)。
- 待问注入挂起分支：session.pending_proposals 非空 → 不 set_pending + pending_question=None，计数照常返回（前端角标仍可见）。
- skip 通道用 ChatRequest 可选字段 skip_question_id（最小侵入，不碰 stall-guard/序号机制）；OpenQuestionLog.upsert 天然保证 skipped/answered 不复活。

## A1 知识图谱节点遮盖修复 (occlusion-fix, 2026-09-04)

- 根因是 5 个几何碰撞（L3 跨模块互叠 / 条目超宽 / term-L4 垂直距不足 / L4 深度组互叠 / concept tier 列撞全局带）+ 无显式 zIndex。
- 修复核心：抽出纯函数 computeNodeLayout(nodes, edges, mode) 返回 Map<id, {x,y,width,height,zIndex,tierBand?}>，layoutNodes 只做 React Flow 组装。坐标逻辑可测是关键——零重叠不变量测试（fixture A/B/C 两两 bbox 不相交）直接锁死回归。
- 模块/条目间距改为"按需半宽 + minGap 顺序排布再居中"（sequentialCentredXs）：半宽取 max(条目带, 深度槽宽)，同构地解决了 tree 模块、concept tier 列、模块内条目三层的横向防撞。深度子树用"每个 L4 节点预留 (n5-1)*DEPTH_SPACING+DEPTH_SLOT+20 宽度、L5 挂其中心"保证 L5 不越槽。
- concept 模式：tier 列序（T14 契约）保留，但列间距动态化 + 列内 fan-out；detail 带（L3/term/L4/L5）整体下移 CONCEPT_MODULE_Y+(maxRowCount-1)*220+180。
- 坑：concept 模式只下移带不够——同列堆叠模块共享 x，条目带照样互叠，必须列内 fan；固定列距 340 对 5 条目（带宽 ~1000px）也必须动态化。
- 带 Y 常量整合为导出 BAND_Y（L3 500→520, term 760→800, L4 840→1000, L5 1000→1200），相邻带净距 ≥100px。
- 预存失败：A1KnowledgeGraph.test.tsx 曾断言旧的 isConceptTermNode "defensive OR" 行为，与已收紧的 predicate.test.ts（term: 前缀 only）矛盾，属陈旧断言，已同步更新（141 tests 全绿）。
- 证据：.sisyphus/evidence/occlusion-fix.txt

## 2026-09-04 black-screen fix learnings
- Root cause chain: single-line entry spread x per-module dynamic spacing -> graph width
  8310px -> fitView zoom clamped to minZoom 0.15 -> nodes <15px = visual black screen.
- Entry-only wrap is NOT enough: L4 depth chains contribute 300-400px to entry half
  width; depth chains must wrap (2 slots/row) AND the depth-bearing entry must sit in an
  exclusive row or the module envelope stays ~390px.
- sequentialCentredXs (mean-centred) is asymmetric when the widest item leads a row;
  balancedCentredXs (extents-symmetric) keeps L4 slot pokes inside the module envelope.
- fixture degeneration trap: concept fixtures without tier fields collapse to a single
  ungrouped column -> concept layout becomes exactly tree layout. Always tier the fixture
  and assert tree!=concept module xs.
- BAND_Y.TERM-BAND_Y.L3 = 280 only fits 2 entry wrap rows (2*110+64=284 > 280);
  TERM/L4/L5 gaps now scale with (maxEntryRows-1)*ENTRY_ROW_HEIGHT + node heights.
- Final numbers: fixture A tree 3400px (<=3600), concept 3400px (<=4000);
  GRAPH_MIN_ZOOM=0.3 exported; 200px nodes render >=60px wide worst-case (readable).

## 黑屏修复收尾（F1/F2/F3 finalize, 2026-09-04）
- 决策记录：原"fixture A 含深度 ≤3600"目标数学不可达（下限 ~4200），orchestrator 验算后修正为分层目标：纯条目 ≤3600 / 含深度 ≤4700 / concept ≤5000。教训：宽度目标先对"最坏 fixture"做下界验算再写进测试。
- 常量微调（已批准）：MODULE_GAP 40→30、ENTRY_SPACING 200→190、ENTRY_HALF_WIDTH 100→95。安全性锚点：ENTRY_SPACING 190 > L3 宽 180（盒净距 10px）；ENTRY_HALF_WIDTH 95 > 真实半宽 90。
- sequentialCentredXs 加了 gapOf 注入参数：wrap 行内 gap = max(minGap, a+b)（无 module gap 项），模块间仍用 max(minGap, a+b+MODULE_GAP)。同一次参数传递的 minGap 语义=中心距下限，MODULE_GAP 项才是"额外余量"，两者常被混淆——之前宽度算术反复出错的根源。
- 深度条目独占一行（entryDepthPlan.has → exclusive row）比把 226px 深条目塞进 3 列行更省宽：纯行 rowHalf=285 反而主导，深度 extent 207.5 完全被包住。
- L4 槽 wrap 行 y = bandY.L4 + row*ENTRY_ROW_HEIGHT；L5 y = max(bandY.L5, parentY + ENTRY_ROW_HEIGHT + L4.height) —— 保证 L5 行永远清开 L4 第 2 行（+200 vs 行2底 +186）。
- bandTop 计入 entryRowDepth + depthRowDepth（(行数-1)*110），TERM/L4/L5 整体下移，行序不变量（L3<term<L4<L5）天然保持。
- boxSpan 测宽必须用 extents（min x ~ max x+width），raw x span 会漏掉半宽 ~170-285px，目标值虚松。
- 概念模式 fixture 补 tier（m1=0..m6=4）后与 tree 模块 x 全等退化消失，加了 not.toEqual 反退化断言。
- 验证：tsc PASS；vitest graph/__tests__ + guided → 29 passed；宽度实测 3410px（三目标全部通过）。证据：.sisyphus/evidence/black-screen-fix.txt

## 2026-09-04 P0: open_questions 结构化数据 React 白屏修复
- 根因：后端按 C6 契约返回结构化 open_questions（对象数组），前端仍按 string[] 渲染 `{question}` → "Objects are not valid as a React child"
- 修复模式：类型定义 OpenQuestionRecord（A1Workspace 导出）+ 渲染前 useMemo 归一化（legacy string → {id:'legacy-'+i,status:'pending'}）兼容旧会话数据
- "待问 N" 口径统一：只有 status ∈ {pending, asked} 算待问；answered/skipped 不显示不计数（A1GraphSection 角标+overlay、A1KnowledgeGraph 角标三处同步）
- 教训：前后端契约变更时，前端消费端必须同步类型 + 防御性归一化（旧数据混合版本）；渲染对象当 React child 直接白屏，测试 fixture 也必须随契约更新

## 2026-09-04 A1 磁盘持久化落地
- A1Store 单 JSON + os.replace 原子写即可满足单用户场景；corrupt 文件 load 返回空+warning，绝不抛（与 A1 域降级风格一致）。
- lazy load 关键：模块级 _loaded 标志 + 首次访问触发，避免 import 副作用影响 pytest 收集；测试隔离 fixture 必须同时 monkeypatch env、rebind _STORE、重置 _loaded、清空两个内存 dict（env 在 __init__ 时读取，仅 setenv 不够）。
- 接线范式：_load_once 放 _get_file 一处即可覆盖全部 file 端点；save 用 _save_store() 包一层 try/except，持久化失败只记事件不 500；poster/visual-bg 用 finally 保存可覆盖全部状态（completed/failed）。
- gitignore 坑：backend/data 只有 *.db/*.txt 被忽略，新增 JSON 存储必须显式加行，否则用户数据会被提交。

## 2026-09-07 edge confirm/reject v0.5 404 修复
- v0.5 graphify 产出的 pending 语义边只存在于 graph_json.edges（confirmed=false），不再预写 confirmed_edges（那是 v0.4 两阶段流设计）→ confirm/reject API 按 key 查 confirmed_edges 必然 404，前端 console.error 静默 = 按钮无效。
- 修复模式：在现有 404 之前插入 v0.5 路径——用 _make_edge_key(from,to,relation) 在 graph_json.edges 里按三元组匹配；confirm 升格快照（confirmed=True）入 confirmed_edges + edge["confirmed"]=True + 重算 edge_stats + _induct_proposed_relation；reject 快照（confirmed=False）入 rejected_edges + 从 edges 移除 + 重算 edge_stats。图中找不到仍 404。
- 测试注入 pending 边的范式：finalize（graphify monkeypatch 降级）后直接 rec["graph_json"]["edges"].append(...) + 置空 confirmed_edges/rejected_edges，edge key 用 a1_routes._make_edge_key 生成。

## 2026-09-08 L3/L4 去重（行政树渲染降级）
- 有 d: 深度条目的 L3 锚点，label 降级为字段名（parts[0]），全文留在 title tooltip；集合用 useMemo 在组件层算好、闭包传给 toReactFlowNode（deps 加 anchorsWithDepth），无需改函数签名。
- 测试断言去重时用 textContent 不含全文 + title 属性含全文双断言，能同时覆盖降级与 tooltip 行为（textContent 天然不含 title）。

## 2026-09-09 图谱索引化（详情面板/交叉引用/搜索）
- 节点标题提取统一收口 nodeTitle()：d:→id 冒号后段（split(':').slice(2).join(':')，注意 JS split limit=2 会丢第三段，不能照搬 spec 的 split(':',2)[2]）；L3→首个冒号前字段名；L2/L1→description；cst/L0→id。面板/搜索/关联边/术语表四处复用同一函数避免名称漂移。
- buildCrosslinks 用"最长词优先"的正确实现是按长度降序排序后拼接正则 alternation（JS 正则按分支顺序命中，非最长匹配）；术语先过滤 nodeId===selfId 再进正则，避免自引用成链。
- React Flow 无 onInit 时拿不到 setCenter；rfInstance 存 useState，跳转 = flowNodes 查 position + NODE_SIZE_ESTIMATES[kind] 宽高一半居中，setCenter zoom 0.7 duration 400。focusGraphNode 必须定义在 flowNodes memo 之后。
- 详情面板为 graph 子组件时会形成 graph↔panel 循环 import 风险：纯函数（nodeTitle/buildCrosslinks/searchGraphNodes）全部放 panel 文件导出，graph 只 import，不反向。
- vitest 新测试路径陷阱：__tests__ 在 graph/ 目录内，相对导入是 '../NodeDetailPanel' 而非 '../graph/...'。

## 2026-09-09 graphify 大输出截断/超时修复
- LLM 大 JSON 输出被 provider 默认 max_tokens=4000 截断 → chat_json 必须显式传 max_tokens（graphify 用 16000）
- 长创意输入实测 78-121s，60s 默认超时不够 → GRAPHIFY_TIMEOUT 默认 120
- 围栏 JSON 概率用 prompt 尾部约束降低（禁 markdown 围栏 + token 预算引导）
- 教训: 常量默认值改动需同步 test_sir_model.py 的常量断言测试
