# Learnings


## Task 3: Frontend Types + API Client

### New Type Definitions
- File: \rontend/src/types/a1.ts\" >> H:\UGC\.sisyphus\notepads\a1-guided-review-concept-network\learnings.md && echo 
-
Exports:
\A1Proposal\,
\OpenQuestion\,
\EdgeStats\"


## Task 2: Concept Edge Vocabulary Compilation

### Actual Counts from v0.4 Document
- **EDGE_VOCAB**: 16 edges total (not 14 as initially expected)
  - 7 ★ rule edges (pure functions, machine-executable)
  - 5 ◆ semantic edges (LLM inference + user confirmation)
  - 4 ◇ structure edges (answer value parsing/expansion)
- **AXIS_SLOTS**: 8 slots (binary spectrum each with exactly 2 values)

### Slot Naming Alignment Challenges
v0.4 uses concept tree naming (e.g., 力量.载体.权限映射)
A1 answers use questionnaire tree naming (module.subfield, e.g., 力量体系.acquire)

**Key Alignment Mappings Found:**
- v0.4 骰子.概率分布 → A1 骰子设定.probability_distribution
- v0.4 力量.溯源.影响生灵比例 → A1 力量体系.source (bundled in hint)
- v0.4 力量.载体.权限映射 → A1 力量体系.acquire (bundled in hint)
- v0.4 玩法.主要行为 → A1 玩法设计DNA.core_experience
- v0.4 力量.代价.反馈回路 → A1 力量体系.cost (bundled in hint)
- v0.4 文明.核心价值 → A1 文明与社会.core_value
- v0.4 视觉.建筑风格 → A1 视觉设计.architecture
- v0.4 视觉.材质偏好 → A1 视觉设计.material
- v0.4 IP.概念 → A1 IP定位.concept
- v0.4 IP.类型 → A1 IP定位.world_type

### TDD Discipline Followed
1. **RED Phase First**: Created test_concept_edge_vocab.py with all assertions BEFORE implementing
2. **Verified RED**: Watched test fail with ModuleNotFoundError (expected)
3. **GREEN Implementation**: Faithfully transcribed all 16 edges + 8 AXIS slots from v0.4
4. **Verified GREEN**: All 12 tests pass, full regression 704 tests pass
5. **Evidence Files Created**: task-2-vocab-distribution.txt + task-2-name-uniqueness.txt

### Static Module Design (Zero LLM)
- Pure constant module: EDGE_VOCAB, AXIS_SLOTS are frozen lists
- Helper functions: get_vocab_by_level(), is_known_relation()
- No generate(), no llm attributes (verified by test)
- Closed vocabulary: VOCAB_RELATION_NAMES = frozenset of all edge names
- Edge names use v0.4 original text verbatim (no LLM inventions)
## Task 1 Learnings (2026-09-01)

### Model Architecture
- **All models are Pydantic v2 BaseModel** (not dataclass). Uses Field(default_factory=list) for mutable defaults.
- InterviewFill (line 36): 4 fields (module, subfield, value, conflict_note)
- Proposal (line 45): 6 fields (module, subfield, old, new, conflict_note, merge_preview). Uses __init__ override for merge_preview default (fullwidth semicolon ；).
- InterviewResult (line 61): 6 fields (fills, guidance_reply, is_innovative, innovative_category, divergent_question, proposals)

### _build_prompt Signature and answers Flow
- Signature: _build_prompt(self, module: dict, subfield: dict, session: Any) -> str
- nswers is extracted via getattr(session, "answers", {}) — session is an Any-typed namespace, NOT a typed model. Task 4/6 should use session.answers dict.
- The nswers dict uses "module.subfield" keys (e.g. "设定边界.immutable_core")
- _immutable_block(answers) helper (line 150) reads nswers.get("设定边界.immutable_core", "") — the subfield id is immutable_core under module id 设定边界 (confirmed from a1_question_tree.py lines 319-328)

### Three New Rules — Exact Prompt Positions
After Task 1, the prompt order in _build_prompt (line 275+):
- Rules 1-3 (unchanged, lines 296-304 in current file)
- Rule 3.5 冲突预检 (line 305-307)
- 【不可动清单】block with _immutable_block() (lines 308-311)
- Rule 3.6 红线记忆 (line 312-313)
- Rule 3.7 术语转译 (lines 314-316)
- Rules 4-9 (unchanged, renumbered context preserved — rules keep original numbers 4-9)

### FakeInterviewer (line 87)
- Location: same file as RealLLMInterviewer, lines 87-142
- Constructor now has proposals: list[Proposal] | None = None as last optional param (line 99)
- interview() returns InterviewResult(fills=..., guidance_reply=..., is_innovative=..., innovative_category=..., proposals=list(self._proposals))
- Backward compatible: existing tests (692+) pass unchanged

### _parse (line 486)
- Now forwards conflict_note from LLM JSON: item.get("conflict_note") → stripped or None
- Proposals not parsed from LLM (not in prompt schema yet — will be added by Task 4 guard)

### pytest Quirks
- Must use absolute paths when running from H:\UGC root: python -m pytest H:\UGC\backend\tests\...
- workdir parameter in bash tool doesn't affect python -m pytest path resolution
- Coverage fail-under=85% triggers on targeted test runs; use --no-cov for quick checks
- Total after Task 5: 740 tests (692 baseline + 12 Task 2 + 25 Task 1 + 11 Task 5)


## Task 5: Concept Edge Extractor (2026-09-01)

### TDD Discipline Followed
1. **RED Phase First**: Created test_concept_edge_extractor.py with 11 tests (≥8 requirement) BEFORE implementing
2. **Verified RED**: Watched test fail with ModuleNotFoundError (expected)
3. **GREEN Implementation**: Implemented concept_edge_extractor.py with extract_concept_edges function
4. **Verified GREEN**: All 11 tests pass (100% pass rate)
5. **Evidence Files Created**: task-5-extractor.txt with RED/GREEN proof + QA scenario outputs

### Function Signature and Contract
```python
def extract_concept_edges(
    session: Any,                      # Session object with answers dict (35 items expected)
    vocab: Any,                        # EDGE_VOCAB from concept_edge_vocab.py (16 edges)
    provider: LLMProvider | None = None,  # Optional LLM provider (tests inject mock)
) -> ExtractResult:                   # Returns edges, axis_assignments, open_questions, success flag
```

### ExtractResult Fields (Pydantic v2 BaseModel)
- `edges: list[ExtractedEdge]` - 抽取的概念边列表（词表校验后）
- `axis_assignments: list[AxisAssignment]` - AXIS 槽位归类列表（8个二元谱系）
- `open_questions: list[str]` - 表外关系转译的世界观问句（禁术语：拓扑/槽位/派生/枚举/轴向/上游/下游）
- `success: bool` - 是否成功（False on LLM error，Task 7 消费降级）
- `warning: str` - 失败警告（含 "concept_edge" 关键字）

### ExtractedEdge Fields
- `from_slot: str` - 源槽位路径（concept tree naming）
- `to_slot: str` - 目标槽位路径（concept tree naming）
- `relation: str` - 边关系名（必须在 VOCAB_RELATION_NAMES 中）
- `confidence: str` - 可信度（★=rule, ◆=semantic, ◇=structure）
- `rationale: str` - LLM 推理依据
- `confirmed: bool = False` - 是否确认（★ rule 边可由 AXIS 点燃为 True）

### Provider Injection Pattern
- **Optional parameter**: `provider: LLMProvider | None = None`
- **Test injection**: `FakeProvider(response={...})` 注入，照抄 test_guide_engine.py 范式
- **Default fallback**: None 时从 app.ai 依赖获取（单元测试必须注入 mock）

### Rule Edge Ignition Logic
- **Default**: ◆ semantic 边 confirmed=False（需用户确认）
- **Ignition**: ★ rule 边由 axis_assignments 槽位归类值匹配 EDGE_VOCAB level="rule" 条件 → confirmed=True
- **Implementation**: `_apply_rule_edge_ignition(result, vocab)` 函数，检查 from_slot/to_slot 是否在 axis_assignments 中

### Core Logic Implementation
1. **LLM 单次调用**: 复用 provider.chat_json，照抄 interviewer.py 的 RealLLMInterviewer.interview 调用范式
2. **词表校验**: relation ∈ VOCAB_RELATION_NAMES 验证，非法边 → open_questions（转译为世界观问句，禁术语）
3. **空模块跳过 (Metis E7)**: from_slot 槽位对应模块无 answers → 不产出该边（targets can be empty - they're derived）
4. **抽取上限**: 边数 ≤ 1.5×已填条目数，超限截断（优先级 rule > semantic > structure）
5. **异常降级**: try/except 包住所有异常，永不抛出，返回 success=False + warning 含 "concept_edge"
6. **不可动清单注入**: answers["设定边界.immutable_core"] 进入 prompt（如有）
7. **prompt 模板**: 封闭词表约束 + 三段输出 JSON schema（edges/axis_assignments/open_questions）

### Degradation Contract for Task 7 Integration
- **Never raises**: Top-level try/except 包住所有异常
- **Failure mode**: `ExtractResult(success=False, warning="concept_edge extraction failed: ...")`
- **Caller check**: Task 7 finalize 集成时检查 `result.success` 字段，False 时降级处理
- **Zero real API calls**: 全部测试 mock LLM，零网络调用

### Slot Naming Alignment (Task 2 传承)
- Extractor outputs from_slot/to_slot 使用 v0.4 concept tree 命名（如 "世界本体.现实规则"）
- A1 answers 使用 questionnaire tree 命名（如 "世界本体.现实规则"）
- Task 7 finalize 集成时需做节点引用校验（槽位命名对齐映射 v0.4→A1）

## Task 4: 写入守卫 (2026-09-01)

### Implementation State
- **Guard Implementation**: Complete (_apply_fills 三分支 + resolve_proposal + _fallback_divergent + pending_proposals/merge_counts)
- **Test Coverage**: 328 lines test_write_guard.py + 114 lines test_guide_engine.py extension = 19 new tests (all passing)
- **Full Regression**: 758 passed (759 expected after evidence path fix)

### Key API Contracts
- **resolve_proposal(session, key, choice)**: dict with applied=bool, choice=str, error=str|None
  - choice values: replace/merge/skip
  - returns applied=True on success, error message on failure

- **pending_proposals shape**: dict with key mapping to proposal dict
  - key format: module.subfield (e.g., IP定位.name)
  - proposal contains Proposal instance with old/new/merge_preview
  - options: list of choice strings (replace/merge/skip)

- **_apply_fills return**: tuple of (file_diff list, intercepted list or None)
  - file_diff: list of old/new/field changes applied
  - intercepted: None (normal) or list of Proposal objects (guard triggered)

- **Intercepted response shape** (guide_engine.py 550-564):
  - reply: conflict explanation with old/new values
  - next_question: None (单问句铁律 - suspended on interception)
  - file_diff: empty list (no changes applied when intercepted)
  - proposals: list of Proposal.model_dump() (intercepted proposals)

### Legacy Test Migration
- **test_handle_message_overwrite_emits_diff**: Migrated from old contract to G1 contract
  - Old behavior: overwrite applied, file_diff contains old/new
  - New behavior: interception, old value preserved, proposals emitted, next_question=None
  - Critical for Task 6 chat routing integration (expects G1 contract)

### Completion Mode
- **Previous agent**: Interrupted during Task 4 implementation
- **Current agent**: Finish-up only (test migration + bug fix + evidence + commit)
- **Evidence path fix**: test_concept_edge_vocab.py lines 36-41, 64-69 (relative to absolute path)
- **Cleanup**: Removed backend/.sisyphus (untracked incorrect evidence files)

## Task 6: Chat侧集成 (2026-09-01)

### TDD Discipline Followed
1. **RED Phase First**: 10 new tests added to test_a1_routes.py BEFORE implementation
2. **Verified RED**: Watched tests fail with expected errors (missing fields)
3. **GREEN Implementation**: Minimal changes to a1_routes.py (chat + confirm + GET file)
4. **Verified GREEN**: 31/31 tests pass (23 existing + 8 new), 769/769 full regression
5. **Evidence File Created**: task-6-routes-chat.txt with complete RED/GREEN cycle

### API Contract Changes
- **ConfirmRequest**: Added `kind: str = "classification"` field (backward compatible)
- **Chat response**: Always includes `proposals: []` (shape stability, Metis E8)
- **Chat response**: Always includes `divergent_question: None` (when not provided)
- **Chat response**: Proposals from guard include `key` field (from pending_proposals dict)
- **Confirm response**: kind='fill' supports resolve_proposal with natural language mapping
- **Confirm response**: Ambiguous choices (<5 chars, no keywords) → needs_clarification
- **GET file response**: Always includes `open_questions: []` and `edge_stats: {...}`

### Natural Language Choice Mapping (Closed Vocabulary)
- Replace: 替换, 换成 → `replace`
- Merge: 合并, 并存, 都保留, 两个都要 → `merge`
- Drop: 放弃, 算了, 不要了 → `drop`
- Ambiguous (<5 chars without keywords) → `needs_clarification: true` + restatement

### Request/Response Shapes (Frontend Contract)
**Confirm Fill Proposal Request:**
```json
{
  "session_id": "a1_...",
  "kind": "fill",
  "proposal": {"key": "IP定位.name:abc123"},
  "choice": "替换"  // or "merge", "drop", or natural language
}
```

**Needs Clarification Response:**
```json
{
  "needs_clarification": true,
  "reply": "你之前定过【...】是『...』。这次的『...』——是要**替换**它，...",
  "next_question": null
}
```

**GET File Response Extensions:**
```json
{
  "file_id": "...",
  "open_questions": [],  // Always present, empty in draft state
  "edge_stats": {
    "semantic_total": 0,
    "semantic_confirmed": 0,
    "rule_total": 0,
    "structure_total": 0,
    "pending_review": 0
  }
}
```

### Line Ownership Boundaries (Metis G4)
- **Modified**: chat endpoint (lines 328-370), chat/confirm endpoint (lines 373-392), GET file (lines 440-452)
- **Untouched**: finalize endpoint (lines 455-508) - Task 7 territory
- **Untouched**: _build_graph (lines 183-250) - Task 7 territory

### Coexistence Rules (Metis Q6)
- Classification proposals and fill proposals can coexist in responses
- classification_proposal field preserves existing innovation_capture behavior
- proposals array contains fill proposals from guard
- Frontend decides display order (contract: backend provides both)

### Test Results
- **Unit Tests**: 31/31 passed (23 existing + 8 new)
- **Full Regression**: 769/769 passed (exceeds ≥759 target)
- **Zero regressions**: All existing tests unchanged and passing
- **Zero side effects**: No changes to finalize/_build_graph regions

### Task 7 Handoff Ready
- _FILES open_questions/edge_stats fields exist with zero defaults
- Task 7 finalize can populate these fields from concept edge extraction
- GET file already returns these fields (frontend ready for Task 7 data)
- Chat/confirm infrastructure complete for fill proposal workflow
