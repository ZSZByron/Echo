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
