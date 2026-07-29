# Wave 2 Task Launch Scripts

## Task 3: 多候选 API + 选择端点 + 状态流转

READY TO LAUNCH AFTER WAVE 1 COMPLETES

<task_load>
subagent_type: build
load_skills: []
prompt: Execute Task 3 from the work plan: 多候选 API + 选择端点 + 状态流转

**CONTEXT**:
Working directory: H:\UGC
Wave 1 (Tasks 1, 2) must be complete first

**WHAT TO DO** (from plan):

Modify `backend/app/api/assets_routes.py`:

1. Modify `_run_generation()` function:
   - NO LONGER: first = results[0]
   - INSTEAD: convert ALL results to Candidate[] and store in asset.candidates
   - After generation: status flow changes to GENERATING → CANDIDATES_READY (not COMPLETED)

2. Create new endpoint `POST /api/assets/{id}/select-candidate`:
   - Body: {"index": N}
   - Set selected_candidate_index = N
   - Update file_path and seed to match candidate N's values
   - Status transition: CANDIDATES_READY → SELECTED
   - Asset.url computed_field automatically returns selected candidate's URL (from Task 1)

3. Update `generate-all` endpoint:
   - Check Feature Flag: if SCENE_CONSISTENCY=true, suggest using orchestration API instead
   - Keep existing behavior for backward compatibility

4. Add `num_candidates` parameter:
   - Read from environment variable IMAGE_NUM_CANDIDATES (default 4)
   - Pass to ImageGenerator.generate()

5. Status behavior:
   - When status is CANDIDATES_READY, approve/reject buttons are disabled (frontend logic in Task 6)

**MUST NOT DO**:
- NO automatic candidate selection - user MUST manually choose
- NO deleting old single-image logic (backward compatibility for approved assets using file_path)
- NO forcing generate-all to use orchestration

**REFERENCES**:
- `backend/app/api/assets_routes.py:35-94` - _run_generation() function (line 70: first = results[0] is key change point)
- `backend/app/state/asset_store.py:37-50` - _ALLOWED_TRANSITIONS needs CANDIDATES_READY/SELECTED transitions
- `backend/app/state/asset_store.py:77-110` - update_asset() method must support writing candidates array
- `backend/app/models/asset.py` - Task 1 extended model (Candidate + AssetStatus)

**ACCEPTANCE CRITERIA**:
- POST /api/assets/{id}/generate → poll GET /api/assets/{id} → status == "candidates_ready" AND candidates array length == 4
- POST /api/assets/{id}/select-candidate with body {"index": 1} → selected_candidate_index == 1, file_path points to candidate 1
- Status after selection is SELECTED
- Asset.url returns candidate 1's URL after selection

**QA SCENARIOS**:

1. Multi-candidate storage + correct status:
   Preconditions: Backend running, at least one pending asset
   Steps:
   - ASSET_ID=temple_ruins_priest_corpse_01
   - curl -s -X POST http://localhost:8000/api/assets/$ASSET_ID/generate
   - Poll: curl -s http://localhost:8000/api/assets/$ASSET_ID/status until status != "generating" (timeout 120s)
   - curl -s http://localhost:8000/api/assets/$ASSET_ID | python -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='candidates_ready', f'Expected candidates_ready, got {d[\"status\"]}'; assert len(d.get('candidates',[]))>=1, 'candidates empty'; print('candidates:', len(d['candidates']), 'status:', d['status'])"
   Expected: status=candidates_ready, candidates non-empty
   Failure: status=completed (old logic not changed), candidates empty or only 1
   Evidence: .sisyphus/evidence/task-3-candidate-storage.json

2. Candidate selection API linkage:
   Preconditions: Previous scenario complete (asset has candidates)
   Steps:
   - curl -s -X POST http://localhost:8000/api/assets/$ASSET_ID/select-candidate -H "Content-Type: application/json" -d '{"index": 1}'
   - curl -s http://localhost:8000/api/assets/$ASSET_ID | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('selected_candidate_index')==1, f'Expected 1, got {d.get(\"selected_candidate_index\")}'; assert d['status']=='selected', f'Expected selected, got {d[\"status\"]}'; print('file_path:', d['file_path'])"
   Expected: selected_candidate_index=1, status=selected, file_path synced
   Evidence: .sisyphus/evidence/task-3-select-candidate.json

3. Out-of-range index returns 400:
   Steps:
   - curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/assets/$ASSET_ID/select-candidate -H "Content-Type: application/json" -d '{"index": 99}'
   Expected: 400 (not 500)
   Evidence: .sisyphus/evidence/task-3-out-of-range.txt

4. All candidates generation failure → status=failed:
   Preconditions: Construct asset with empty prompt or disconnect network
   Steps:
   - Trigger generation
   - Poll status
   Expected: status=failed AND error_message non-empty, not stuck in generating
   Evidence: .sisyphus/evidence/task-3-all-failed.txt

**EVIDENCE TO SAVE**:
- .sisyphus/evidence/task-3-candidate-storage.json
- .sisyphus/evidence/task-3-select-candidate.json
- .sisyphus/evidence/task-3-out-of-range.txt
- .sisyphus/evidence/task-3-all-failed.txt

**COMMIT**: YES
- Message: feat(api): multi-candidate storage, selection, and CANDIDATES_READY status
- Files: backend/app/api/assets_routes.py, backend/app/state/asset_store.py
- Pre-commit: cd backend && .venv\Scripts\python -m pytest tests/ -x -q

Execute after Wave 1 completes. Read reference files, implement, run QA scenarios, save evidence, report completion.
</task_load>

## Task 4: StyleProfile 提取 + Prompt 注入 + Feature Flag

READY TO LAUNCH AFTER WAVE 1 COMPLETES

<task_load>
subagent_type: build
load_skills: []
prompt: Execute Task 4 from the work plan: StyleProfile 提取 + Prompt 注入 + Feature Flag + base64 降级

**CONTEXT**:
Working directory: H:\UGC
Wave 1 (Task 1) must be complete first

**WHAT TO DO** (from plan):

1. Create `backend/app/ai/style_extractor.py`:
   - extract_style_profile(asset: Asset) -> SceneStyleProfile: Extract five-dimension style from completed asset's prompt
   - Five-dimension keyword library (predefined, text matching, deterministic):
     - palette: cyan, neon-green, deep-black, bronze, amber, red, blue, white...
     - lighting: {type: volumetric/directional/ambient, direction: side/top/bottom}
     - material: marble, metal, stone, bronze, concrete, glass...
     - rendering: {style: cyberpunk/realistic/concept-art, camera: low-angle/wide-shot}
     - atmosphere: {mood: dark/melancholic/mystical, weather: mist/fog/clear}
   - inject_style_prompt(base_prompt: str, profile: SceneStyleProfile) -> str: Convert profile to style prefix and inject
   - Injection format: "Scene style: {palette}, {lighting}, {material}. {base_prompt}"
   - Limit injected tokens to ≤50 words to avoid polluting object description

2. Modify `ImageGenerator.generate()` in `backend/app/ai/image_generator.py`:
   - Add parameter: reference_asset_ids: list[str] = []

3. Modify `_call_qwen()` in `backend/app/ai/image_generator.py`:
   - Three-level fallback strategy:
     1. Level 1 - base64 reference image: Read reference asset's file_path → base64 encode → Add to messages[0].content as {"image": "data:image/png;base64,..."}
     2. Level 2 - StyleProfile Prompt injection: If base64 rejected by API (HTTP 4xx) → Catch exception → Fallback to inject_style_prompt() mode
     3. Level 3 - No reference: If Feature Flag off or no reference assets → Original behavior unchanged
   - Log each fallback with logger.warning() and mark in metadata JSON with reference_mode: "base64" | "prompt" | "none"

4. Feature Flag:
   - SCENE_CONSISTENCY=false forces Level 3 (original behavior)

**MUST NOT DO**:
- NO calling LLM for style extraction (pure keyword matching)
- NO uploading images to public URLs
- NO modifying non-qwen provider behavior
- NO changing background's own prompt (only inject into objects)

**REFERENCES**:
- `backend/app/ai/image_generator.py:113-140` - generate() signature, needs reference_asset_ids parameter
- `backend/app/ai/image_generator.py:344-413` - _call_qwen() method, needs three-level fallback logic
- `backend/app/models/asset.py` - Task 1's SceneStyleProfile model
- `backend/app/config/features.py` - Task 1's Feature Flag
- `data/assets/manifest.json:7-8` - Background asset prompt example ("cyberpunk... marble... neon...")

**ACCEPTANCE CRITERIA**:
- extract_style_profile() extracts ≥2 colors, ≥1 material, lighting.type non-empty from temple_ruins_bg prompt
- inject_style_prompt("a bronze door", profile) returns string containing palette color words
- Same asset extracted multiple times gives identical results (deterministic)
- _call_qwen() behavior unchanged when no reference image
- Feature Flag = false triggers NO style logic

**QA SCENARIOS**:

1. Style extraction determinism + five dimensions:
   Steps:
   - cd backend && .venv\Scripts\python -c "
     from app.ai.style_extractor import extract_style_profile_from_prompt
     from app.models.asset import SceneStyleProfile
     prompt = 'cyberpunk ancient marble temple, cyan neon circuits, volumetric fog, synthwave lighting, dark atmosphere'
     p = extract_style_profile_from_prompt(prompt)
     print('palette:', p.palette)
     print('material:', p.material)
     print('lighting:', p.lighting)
     print('atmosphere:', p.atmosphere)
     assert len(p.palette) >= 2
     assert len(p.material) >= 1
     # Determinism test
     p2 = extract_style_profile_from_prompt(prompt)
     assert p == p2, 'Non-deterministic!'
     print('OK')
     "
   Expected: Five dimensions non-empty, two extractions identical
   Evidence: .sisyphus/evidence/task-4-style-extraction.txt

2. Prompt injection correctness:
   Steps:
   - .venv\Scripts\python -c "
     from app.ai.style_extractor import inject_style_prompt, extract_style_profile_from_prompt
     p = extract_style_profile_from_prompt('cyan neon marble cyberpunk dark')
     result = inject_style_prompt('a bronze door', p)
     print('injected:', result[:100])
     assert 'cyan' in result or 'neon' in result
     print('OK')
     "
   Expected: Injected prompt contains style keywords
   Evidence: .sisyphus/evidence/task-4-prompt-injection.txt

3. Feature Flag off = original behavior:
   Steps:
   - Set FEATURE_SCENE_CONSISTENCY=false
   - .venv\Scripts\python -c "
     import os; os.environ['FEATURE_SCENE_CONSISTENCY']='false'
     from app.config.features import SCENE_CONSISTENCY
     assert not SCENE_CONSISTENCY
     print('Flag off — original behavior preserved')
     "
   Expected: Flag is False
   Evidence: .sisyphus/evidence/task-4-feature-flag-off.txt

4. base64 fallback to prompt:
   Preconditions: Have a completed asset
   Steps:
   - Call generate(reference_asset_ids=["temple_ruins_bg"], num_candidates=1)
   - Check metadata JSON for reference_mode field
   Expected: reference_mode is "base64" or "prompt" (depending on API acceptance), not error
   Failure: Uncaught exception causes generation failure
   Evidence: .sisyphus/evidence/task-4-base64-fallback.txt

**EVIDENCE TO SAVE**:
- .sisyphus/evidence/task-4-style-extraction.txt
- .sisyphus/evidence/task-4-prompt-injection.txt
- .sisyphus/evidence/task-4-feature-flag-off.txt
- .sisyphus/evidence/task-4-base64-fallback.txt

**COMMIT**: YES
- Message: feat(ai): style profile extraction and prompt injection with feature flag
- Files: backend/app/ai/style_extractor.py, backend/app/ai/image_generator.py

Execute after Wave 1 completes. Read reference files, implement, run QA scenarios, save evidence, report completion.
</task_load>

## Task 5: 场景编排 API — 拓扑排序串行触发 + 风格链 + 进度追踪

READY TO LAUNCH AFTER WAVE 1 COMPLETION

<task_load>
subagent_type: build
load_skills: []
prompt: Execute Task 5 from the work plan: 场景编排 API — 拓扑排序串行触发 + 风格链 + 进度追踪

**CONTEXT**:
Working directory: H:\UGC
Wave 1 (Task 2) must be complete first

**WHAT TO DO** (from plan):

Create new scene orchestration endpoints:

1. Create `POST /api/scenes/{scene_id}/orchestrate`:
   - Use SceneGraph.from_yaml(scene_id).generation_order to get topological order
   - Serial triggering: Generate background first → Wait for completion → Extract StyleProfile → Fill pending assets' style_profile in same scene
   - Subsequent object generation automatically injects reference: reference_asset_ids = [scene_id + "_bg"]
   - Return: {order: [...], triggered: N}

2. Create `GET /api/scenes/{scene_id}/graph`:
   - Return: {nodes: {...}, generation_order: [...], style_sources: {...}}

3. Create `GET /api/scenes/{scene_id}/orchestrate/status`:
   - Return each asset's current status
   - Progress tracking

4. Style profile auto-fill:
   - When background completes, automatically call extract_style_profile()
   - Update all pending assets in same scene with style_profile field filled

5. Error handling:
   - If any asset fails during orchestration, log error but continue with subsequent assets (don't block entire chain)

**MUST NOT DO**:
- NO parallel generation of same-scene assets (reference chain needs serial: background→objects)
- NO auto-approve - generation still requires user to select candidates + approve
- NO blocking other scene's generation requests

**REFERENCES**:
- `backend/app/models/scene_graph.py` - Task 2's SceneGraph model
- `backend/app/api/assets_routes.py:185-198` - generate_all() existing bulk logic for reference
- `backend/app/ai/style_extractor.py` - Task 4's style extractor
- `backend/app/config/features.py` - Feature Flag check

**ACCEPTANCE CRITERIA**:
- POST /api/scenes/temple_ruins/orchestrate returns order list with temple_ruins_bg in first position
- GET /api/scenes/temple_ruins/graph returns {nodes, generation_order, style_sources} structure
- Background generation completes → same-scene pending assets' style_profile filled (not None)
- Orchestration with one asset failure doesn't block subsequent assets

**QA SCENARIOS**:

1. Scene graph data returns:
   Steps:
   - curl -s http://localhost:8000/api/scenes/temple_ruins/graph | python -c "
     import sys,json; d=json.load(sys.stdin)
     assert 'nodes' in d and 'generation_order' in d and 'style_sources' in d
     assert 'temple_ruins_bg' in d['nodes']
     assert d['generation_order'][0] == 'temple_ruins_bg'
     print('nodes:', len(d['nodes']), 'order:', d['generation_order'][:3])
     "
   Expected: Structured graph data, background first
   Evidence: .sisyphus/evidence/task-5-scene-graph.json

2. Orchestrate trigger + correct order:
   Preconditions: temple_ruins has pending assets
   Steps:
   - curl -s -X POST http://localhost:8000/api/scenes/temple_ruins/orchestrate | python -c "
     import sys,json; d=json.load(sys.stdin)
     print('order:', d.get('order', []))
     assert d['order'][0] == 'temple_ruins_bg'
     print('triggered:', d.get('triggered', 0))
     "
   Expected: Returns topological order, background first
   Evidence: .sisyphus/evidence/task-5-orchestrate.json

3. Orchestration progress tracking:
   Preconditions: Orchestration triggered
   Steps:
   - curl -s http://localhost:8000/api/scenes/temple_ruins/orchestrate/status | python -c "
     import sys,json; d=json.load(sys.stdin)
     print('assets:', {k:v for k,v in list(d.items())[:3]})
     "
   Expected: Each asset has status field
   Evidence: .sisyphus/evidence/task-5-orchestrate-status.json

4. Style Profile auto-fill:
   Preconditions: Background completed in orchestration
   Steps:
   - .venv\Scripts\python -c "
     from app.state.asset_store import AssetStore
     s = AssetStore()
     for a in s.list_assets():
       if a.parent_scene == 'temple_ruins' and a.type == 'object':
         print(a.id, 'style_profile:', a.style_profile is not None)
     "
   Expected: Objects' style_profile non-None after background completes
   Evidence: .sisyphus/evidence/task-5-style-propagation.txt

**EVIDENCE TO SAVE**:
- .sisyphus/evidence/task-5-scene-graph.json
- .sisyphus/evidence/task-5-orchestrate.json
- .sisyphus/evidence/task-5-orchestrate-status.json
- .sisyphus/evidence/task-5-style-propagation.txt

**COMMIT**: YES
- Message: feat(api): scene orchestration with topological generation order
- Files: backend/app/api/assets_routes.py (or new backend/app/api/scene_routes.py)

Execute after Wave 1 completes. Read reference files, implement, run QA scenarios, save evidence, report completion.
</task_load>
