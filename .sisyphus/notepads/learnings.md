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

## T-B: finalize两阶段编排（概念词入图→节点确认→抽边端点+新词入典流）
- finalize 改造（a1_routes.py）：旧槽位级 extract_concept_edges 调用停用（extractor 函数与
  _add_concept_edges_to_graph 文件级保留不调用）。阶段1 extract_concept_terms 成功后：
  - 概念词节点入图：`{id: "term:<词>", serial_number: "", level: 4, description: 词,
    status: "completed"}`（term: 前缀 + level=4 双标识），同词去重，TREE 结构不动
  - _FILES 新键 `concept_terms: list[dict{term,field_key,gloss,confirmed}]`（confirmed 默认 False，
    re-finalize 同词保留 confirmed 态）；finalize 响应新增 `concept_terms_count`
  - 失败降级：warnings 含 "concept_term"，纯 TREE 无 term 节点，finalize 仍 200
- 新端点：
  - `POST /api/a1/file/{file_id}/terms/confirm`，body `{terms:[...]}` 或 `{all:true}` → 更新
    concept_terms.confirmed，返回更新后清单
  - `POST /api/a1/file/{file_id}/concept/extract-edges`：前置校验 confirmed 词 ≥2 否则 400
    `{"detail":"需先确认至少2个概念词"}`；未定稿 409 pending_finalize；成功边入图
    （from/to=`term:词`，引用校验缺失丢弃；rejected 键跳过），失败 200+`{"success":false,"warning":...}`
- _FILES 新键：`proposed_relations: list[{name,from_term,to_term,rationale}]`（is_new_relation 边
  照常入图 confirmed=False 并记此）；`relation_registry: dict{name:{level,gloss}}`（RelationRegistry
  序列化，抽边端点恢复，confirm 新词边时 add 后回写）
- 概念边 key 格式：`term:A/term:B/relation`（沿用 _make_edge_key，:path 转换器 + encodeURIComponent 兼容）
- edge confirm 端点新逻辑：确认含提议新关系的边 → relation 入典（RelationRegistry.add 默认 semantic）
  + 从 proposed_relations 移除（_induct_proposed_relation，两处 return 前调用）；顺带修复
  confirm 未重算 edge_stats 的旧问题（path2 现在也重算）
- re-finalize 恢复：finalize 不再抽边，但按 confirmed_edges 快照把概念边重入图（confirmed 态取快照值，
  rejected 不重现，term 节点缺失的边丢弃）
- GET /api/a1/file/{file_id} 常驻新字段：`concept_terms`（draft 空）、`proposed_relations`（draft 空）
- 测试：新 tests/unit/a1/test_concept_finalize_v2.py（8 场景）；test_a1_edges.py 旧槽位边语义逐个
  迁移（finalize 零概念边/只有 term 节点，edge confirm/reject API 端点不变保留）
- 全量回归 833 passed 零失败（基线 825 + 新增 8）
