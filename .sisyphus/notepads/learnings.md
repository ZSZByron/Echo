# Learnings
## T9-Part2: A1 Routes API
- Files already existed (a1_routes.py, test_a1_routes.py, main.py registration) - task was verification+fix
- stale_marker.ensure_registry() must be called before register_graph/mark_downstream_stale
- Path corruption bug in bash tool: H:\UGC paths get mangled inline. Workaround: assign to PS variables first
- RealSemanticCompiler(provider=None) gives L1/L2 only, skip section with empty answer
- GraphCodeIssuer W-stage: first call W1-v1, second bumps to W1-v2
- Full regression: 588 passed (baseline 579, +9 new A1 tests)

## 2026-09-02 守卫保护对象辨析（用户值 vs LLM 猜测值）
- 写入守卫（Metis G1）保护的是"用户已确定的内容"，不是"会话里已有的任何值"。
  prefill 值是上传时 LLM 的猜测，用户从未确认——对猜测值走提案制是认知错位，
  曾造成产品级死锁：prefill→finalize门禁→topup全被拦→按钮永灰→进不了图谱。
- 修复模式：来源标记豁免。session.prefill_fields 记录猜测键；_apply_fills
  拦截前检查来源，猜测值被用户口述**直接覆盖**（file_diff 记录 old→new 供右栏
  展示，审核权不丢失），并从 prefill_fields 移除——此后该字段回归正常守卫。
- 通用教训：给拦截类守卫加"数据来源"维度（confirmed vs guessed），
  豁免只针对来源，不弱化守卫本身；豁免必须一次性（用后即收回）。
- 验证教训：Windows 下用 Start-Process 启动的 uvicorn，主进程 PID 对
  Get-Process/Get-CimInstance 不可见，需通过 multiprocessing.spawn 子进程
  的 parent_pid 或 netstat 定位并杀子进程才能释放端口。

## T-A: 概念网语义升级——概念关系词典 + 两阶段抽取器
- 新词典 `concept_relation_vocab.py`：RelationSpec(name/level/gloss/example) + 种子10条（★隶属/对立/等同，◆引发/转化/依赖/象征/制约，◇共现/分型）+ RelationRegistry（is_known/add默认semantic/all_specs，add不改全局种子）
- 两阶段（concept_edge_extractor.py 追加，旧 extract_concept_edges 兼容保留）：
  - 阶段1 `extract_concept_terms(session, provider=None) -> TermsResult`：ConceptTerm(term/field_key/gloss/confirmed=False)；同词跨字段去重保留首现 field_key；空answers不调LLM；降级 warning 含 "concept_term"
  - 阶段2 `extract_concept_relations(terms, session, registry, provider=None) -> EdgesV2Result`：ConceptEdgeV2(from_term/to_term/relation/is_new_relation/rationale/confidence/confirmed=False)；只连 confirmed=True 的词；词典关系按 RelationSpec.level 定 confidence；新词 → confidence=semantic + is_new_relation=True（待用户确认入典）；上限 int(len(terms)×1.5)，rule>semantic>structure 截断；降级 warning 含 "concept_edge"
- T-B 与前端将消费：阶段1确认节点 → 阶段2逐条确认边 + 新词确认入典（registry.add）
- 验证：825 passed 零失败（基线801 + 新增24）；TDD RED先行
