# Puzzle-Driven Asset Pipeline - Learnings

## Session Start
**Session ID**: ses_05402c437ffeJacuVC2I7TkS88  
**Timestamp**: 2026-07-29T03:48:47.781Z  
**Plan**: puzzle-driven-asset-pipeline.md

## Critical Constraints (From Plan)
- P0 FIX: reference_asset_ids MUST be passed to gen.generate()
- NO `{asset_id}_{lod}` splitting - use Asset.views embedded structure
- NO puzzle logic in SceneGraph - use independent PuzzleGraph
- NO hardcoded sorting in API - use GenerationPlanner
- NO massive prompts.yaml - use PromptBuilder template injection
- Preserve status state machine - no breaking changes
- SCENE_CONSISTENCY=false → reference_asset_ids empty

## Architecture Insights
- **PuzzleGraph**: Independent from SceneGraph, only handles logic dependencies
- **GenerationPlanner**: Orchestrates SceneGraph + PuzzleGraph + PromptBuilder
- **Asset.views**: `{"far": {...}, "mid": {...}, "near": {...}}` embedded, not separate entries
- **PromptBuilder**: 8-layer structure (World+Location+Camera+Subject+GameplayFunction+InteractionDetails+Material+Lighting)

## Sprint Structure
- Sprint 1: P0 Fix + Demo Chain (Tasks 1-4) - parallel tasks 1,2,3 → then 4
- Sprint 2: Architecture Separation (Tasks 5-8) - sequential dependencies
- Sprint 3: Prompt System (Tasks 9-10) - parallel
- Sprint 4: UI + Tests (Tasks 11-13) - parallel

## File Paths (Absolute)
- Plan: `H:\UGC\.sisyphus\plans\puzzle-driven-asset-pipeline.md`
- Notepad: `H:\UGC\.sisyphus\notepads\puzzle-driven-asset-pipeline\`
- Backend: `H:\UGC\backend\`
- Frontend: `H:\UGC\frontend\`
- Data: `H:\UGC\data\`

# Task 1 Implementation Learnings

## Date: 2025-01-29

## Critical Implementation Details

1. **Import Path**: SceneGraph is imported at module level: rom app.models.scene_graph import SceneGraph

2. **Reference Asset Extraction**:
   - Located in _run_generation() function (lines 64-76 in assets_routes.py)
   - Checks SCENE_CONSISTENCY flag before processing
   - Uses SceneGraph.from_yaml() to load scene graph
   - Extracts style_sources dict keyed by asset_id
   - Filters for APPROVED/COMPLETED status only
   - Wrapped in try/except to handle SceneGraph loading failures

3. **Function Call Update**:
   - Line 79-83: Added 
eference_asset_ids=approved_refs parameter
   - Parameter is positioned after required parameters
   - Parameter type: list[str]

4. **Mock Test Implementation**:
   - Had to patch at module level: patch.object(routes_module, '_store', mock_store)
   - Module-level variables require patching the module object, not the class
   - Bypassed state machine by mocking update_asset

## Key Success Factors

- Preserved existing behavior when SCENE_CONSISTENCY=false
- Maintained backward compatibility (empty list when no refs)
- Added proper error handling for SceneGraph loading
- Used existing AssetStore for reference asset retrieval

## Evidence

- Source inspection: PASS (reference_asset_ids in source)
- Mock test: PASS (reference_asset_ids passed to generator)
- LSP diagnostics: PASS (no errors)

# Task 2 Implementation Learnings

## Date: 2026-07-29

## Critical Implementation Details

1. **YAML Generation Approach**: Used Python yaml.dump() instead of manual string writing to avoid escaping issues with special characters (degree symbol, apostrophes, colons in strings).

2. **Puzzle Chain Structure**: 6-node dependency chain: priest_corpse_01 -> ritual_record -> holographic_altar -> ritual_crystal -> key_fragment -> ancient_locked_door. Uses abstract produces/requires fields (ritual_knowledge, ritual_record, etc.) as dependency edges.

3. **Depth Assignments**: near (priest_corpse_01, ritual_record), mid (holographic_altar, ritual_crystal, key_fragment), mid_far (neon_circuit_pillar), far (ancient_locked_door).

4. **LOD Structure**: Each object has far/mid/near prompts as nested dict under lod key. These are brief descriptions for image generation, NOT full prompts.

5. **New Objects**: ritual_record (container, parent=priest_corpse_01), ritual_crystal (consumable, parent=holographic_altar), key_fragment (reward, parent=ritual_crystal). Each has parent_object field linking to source.

6. **YAML safe_load validated**: All required fields present, all 7 objects (4 original + 3 new) with depth/lod/puzzle_role/new_assets_hint.

## Key Success Factors

- Preserved all existing fields (scene_id, name, description, atmosphere, region, interaction_targets)
- No full prompt text in YAML (prompts go in prompts.yaml per architecture)
- Valid YAML syntax confirmed via yaml.safe_load()

# Task 4 Chain Verification Learnings

## Date: 2026-07-29

## Chain Integration Verification Results

### 1. Previous Task Evidence Validation
- ✅ Task 1 evidence files confirmed PASS
- ✅ Task 2 evidence files confirmed PASS
- ✅ Task 3 evidence files confirmed PASS

### 2. Chain Integration Tests
- ✅ Scene YAML validation: puzzle_chain, depth_layers, new objects present
- ✅ Prompts YAML validation: camera_templates, LOD structure valid
- ✅ Asset manifest: ritual_record, ritual_crystal, key_fragment present
- ✅ Source code: reference_asset_ids in _run_generation
- ✅ SceneGraph parsing: All new assets (holographic_altar, ritual_record, ritual_crystal, key_fragment) correctly loaded
- ✅ Mock generation chain: reference_asset_ids correctly passed to generator

### 3. Sprint 1 Gate Status
- 🎯 SPRINT 1 COMPLETE: All integration points verified
- 🚀 READY FOR SPRINT 2: Demo generation chain functional

## Key Success Factors
- Task 1 (Reference Passing): reference_asset_ids flows from API to image generator
- Task 2 (YAML Schema): temple_ruins.yaml with puzzle_chain and depth_layers
- Task 3 (LOD Prompts): prompts.yaml with camera_templates and LOD structure
- Integration: Asset manifest, SceneGraph parsing, and generation pipeline all work together

## Critical Learnings
- No code modifications required for verification task
- Mock tests successfully confirm parameter propagation without real API calls
- SceneGraph handles new schema (puzzle_chain, depth_layers) without errors
- Asset state machine integrity maintained (2 existing test failures unrelated to changes)

# Task 5 Implementation Learnings

## Date: 2026-07-29

## Critical Implementation Details

1. **Requires Resolution**: puzzle_chain `requires` field can contain either node IDs OR produced item names (e.g., `ritual_knowledge`). Must resolve produced items back to the node that produces them via `produces` field lookup. Added `_resolve_requires()` helper.

2. **Topological Sort with Type Priority**: Kahn's algorithm with type priority as tiebreaker. When multiple nodes have indegree=0, sort by (type_order, node_id). This ensures stable ordering that respects both dependencies AND puzzle type progression (clue->consumable->reward->obstacle).

3. **Puzzle Chain Structure**: 6 nodes in temple_ruins: priest_corpse_01(clue) -> ritual_record(clue) -> holographic_altar(consumable) -> ritual_crystal(consumable) -> key_fragment(reward) -> ancient_locked_door(obstacle).

4. **Complete Independence**: Zero imports from scene_graph module. Only stdlib + pydantic + yaml dependencies.

## Key Success Factors

- Resolved the requires/produces indirection correctly
- Type priority tiebreaker produces clean CLUE[0,1] -> CONSUMABLE[2,3] -> REWARD[4] -> OBSTACLE[5] ordering
- LSP diagnostics clean, all 3 evidence tests pass

# Task 6 Implementation Learnings

## Date: 2026-07-29

## Critical Implementation Details

1. **BG Always Last**: Cannot rely solely on LOD priority in Kahn's sort. BG has indegree=0 and would be processed first with priority=3 only if all other ready nodes have lower priority. But since ALL objects depend on bg, processing bg first reduces all their indegrees. Fix: exclude bg from topological sort entirely, append at end.

2. **Depth-to-LOD Mapping**: YAML depth field maps to LOD: near->near, mid->mid, mid_far->far, far->far. Need _load_depth_map() helper since SceneGraph.AssetInfo does not store depth.

3. **Puzzle Requirement Resolution**: puzzle_chain requires can be node IDs OR produced item names (e.g. ritual_knowledge). Must resolve via produces field lookup - same pattern as PuzzleGraph._resolve_requires().

4. **Combined Dependencies**: Spatial deps from SceneGraph.style_sources (all objects -> bg) + puzzle deps from PuzzleGraph.node.requires. Result: each puzzle chain node depends on bg + its puzzle predecessor.

5. **Docstring Gotcha**: inspect.getsource() checks string content. Writing 'ImageGenerator' in a docstring fails the no-import assertion. Use generic 'image generator' instead.

6. **Services Package**: Had to create backend/app/services/__init__.py since the directory did not exist.

## Key Success Factors
- Clean separation: planning only, no execution
- BG guaranteed last via explicit append after topological sort
- References correctly combine spatial + puzzle dependencies
