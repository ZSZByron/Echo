# Wave 3 Task Launch Script

## Task 6: 前端全部实现 + 集成验证

READY TO LAUNCH AFTER WAVES 1 & 2 COMPLETE

<task_load>
subagent_type: build
load_skills: ["frontend-ui-ux"]
prompt: Execute Task 6 from the work plan: 前端全部实现 + 集成验证

**CONTEXT**:
Working directory: H:\UGC
Waves 1 & 2 (Tasks 1-5) must be complete first

**WHAT TO DO** (from plan):

**6a. 前端 API Client 扩展**:

1. Extend `frontend/src/api/assets.ts`:
   - Add `Candidate` interface (index, seed, file_path, url, score)
   - Add fields to `Asset` interface: candidates, selected_candidate_index, reference_asset_ids, style_profile
   - Add to `AssetStatus` type: 'candidates_ready' | 'selected'
   - Add function: `selectCandidate(id: string, index: number): Promise<Asset>`

2. Create `frontend/src/api/scenes.ts`:
   - `SceneGraphNode` interface (id, name, type, status, is_future_anchor)
   - `getSceneGraph(sceneId): Promise<{nodes, generation_order, style_sources}>`
   - `orchestrateScene(sceneId): Promise<{order, triggered}>`
   - `getOrchestrateStatus(sceneId): Promise<Record<string, string>>`

**6b. CandidateGrid 组件**:

3. Create `frontend/src/components/CandidateGrid.tsx`:
   - Props: candidates: Candidate[], selectedIndex: number | null, onSelect: (index: number) => void
   - 2x2 grid layout, each candidate shows thumbnail + seed
   - Selected candidate gets neon-cyan border highlight
   - Unselected candidates hover with neon-green border
   - `data-testid="candidate-thumb"` attribute for test定位

**6c. SceneGraphPage 独立页面**:

4. Create `frontend/src/pages/SceneGraphPage.tsx`, route `/scenes/:sceneId`

5. Create `frontend/src/components/SceneGraphSVG.tsx`:
   - Pure SVG radial layout
   - Background node in center, object nodes surround
   - Nodes colored by STATUS_COLORS
   - Edges using SVG <line> connections, labeled "style_ref"
   - Click node → navigate to /assets and select asset

6. Add "编排生成" button:
   - Calls orchestrateScene() → Poll getOrchestrateStatus() → Real-time node status color updates
   - Progress bar: "已生成 N / 总数 M"

**6d. AssetReview 集成**:

7. Modify `AssetReview.tsx`:
   - In preview area: When asset.status === 'candidates_ready', embed <CandidateGrid />
   - Status linkage:
     - candidates_ready: Show candidate grid, approve/reject disabled
     - selected: Main preview shows selected image, approve/reject enabled
   - Add "场景图谱" link in header → Navigate to /scenes/:sceneId

**6e. 集成验证**:

8. End-to-end test temple_ruins scene:
   - Orchestrate → Background generation → Style extraction → Objects with style → Candidate display → Select → Approve
   - Fix integration issues discovered

9. Feature Flag on/off contrast test

**MUST NOT DO**:
- NO D3.js / cytoscape graph visualization libraries
- NO changing existing asset list or property panel layouts
- NO new features in this task - pure integration + fixes only

**REFERENCES**:
- `frontend/src/api/assets.ts:1-152` - Existing API client, needs extension
- `frontend/src/api/client.ts` - fetchWithTimeout utility
- `frontend/src/pages/AssetReview.tsx:1-677` - Existing asset review page, needs CandidateGrid integration
- `frontend/src/pages/AssetReview.tsx:457-503` - Preview area, candidate grid insertion point
- `frontend/src/pages/AssetReview.tsx:605-662` - approve/reject button area, needs selected state linkage
- `frontend/src/pages/AssetReview.tsx:19-44` - STATUS_COLORS / STATUS_TEXT_COLORS mapping, needs new statuses
- `frontend/src/App.tsx` - Needs new /scenes/:sceneId route

**ACCEPTANCE CRITERIA**:
- npm run build passes without TypeScript errors
- assets with status=candidates_ready display 2x2 candidate grid
- Clicking candidate highlights it + enables approve button
- /scenes/temple_ruins route accessible, displays SVG scene graph
- Scene graph node click navigates to asset
- "编排生成" button triggers API and shows progress
- Feature Flag = false still allows candidate grid (just no style injection)

**QA SCENARIOS**:

1. TypeScript compilation passes:
   Steps:
   - cd frontend && npm run build
   Expected: Build succeeds without errors
   Evidence: .sisyphus/evidence/task-6-build.txt

2. Candidate grid display:
   Tool: Playwright
   Preconditions: Backend running, has status=candidates_ready asset
   Steps:
   - Navigate to http://localhost:5173/assets
   - Click that asset
   - Assert [data-testid="candidate-thumb"] element count > 1
   - Screenshot
   Expected: 2x2 grid shows candidate thumbnails
   Evidence: .sisyphus/evidence/task-6-candidate-grid.png

3. Candidate selection interaction:
   Tool: Playwright
   Steps:
   - In candidate grid, click second [data-testid="candidate-thumb"]
   - Assert element has class containing "border-neon-cyan"
   - Assert approve button no longer has "cursor-not-allowed" class
   - Screenshot
   Expected: Selected highlight + approve enabled
   Evidence: .sisyphus/evidence/task-6-select-interaction.png

4. Scene graph page accessible:
   Tool: Playwright
   Steps:
   - Navigate to http://localhost:5173/scenes/temple_ruins
   - Assert [data-testid="scene-graph-svg"] exists
   - Assert SVG has > 2 node elements
   - Screenshot
   Expected: Radial scene graph renders
   Evidence: .sisyphus/evidence/task-6-scene-graph-page.png

5. Orchestrate generation end-to-end:
   Tool: Playwright + Bash
   Preconditions: temple_ruins has pending assets
   Steps:
   - Navigate to /scenes/temple_ruins
   - Click "编排生成" button
   - Wait for confirmation dialog → Confirm
   - Assert progress bar appears
   - Poll wait until all nodes status != generating (max 5 minutes)
   - Navigate to /assets
   - Check each asset candidates non-empty
   - Screenshot
   Expected: Full scene asset generation complete
   Failure: Timeout, candidates empty, node status not updating
   Evidence: .sisyphus/evidence/task-6-e2e-orchestrate.png

6. Feature Flag off contrast:
   Tool: Bash
   Steps:
   - Set FEATURE_SCENE_CONSISTENCY=false, restart backend
   - curl -X POST /api/scenes/temple_ruins/orchestrate
   - Check if object generation has style_profile = None
   Expected: Flag off → style_profile not filled
   Evidence: .sisyphus/evidence/task-6-feature-flag-off.txt

7. Rollback safety - delete candidates, approved assets normal:
   Tool: Bash
   Steps:
   - Find an approved asset
   - Record its file_path
   - curl http://localhost:8000/api/assets/{id} confirm url field non-null
   Expected: Approved assets use file_path fallback, url normal
   Evidence: .sisyphus/evidence/task-6-rollback-safety.txt

**EVIDENCE TO SAVE**:
- .sisyphus/evidence/task-6-build.txt
- .sisyphus/evidence/task-6-candidate-grid.png
- .sisyphus/evidence/task-6-select-interaction.png
- .sisyphus/evidence/task-6-scene-graph-page.png
- .sisyphus/evidence/task-6-e2e-orchestrate.png
- .sisyphus/evidence/task-6-feature-flag-off.txt
- .sisyphus/evidence/task-6-rollback-safety.txt

**COMMIT**: YES
- Message: feat(ui): CandidateGrid component and SceneGraphPage + integration
- Files: frontend/src/api/assets.ts, frontend/src/api/scenes.ts, frontend/src/components/CandidateGrid.tsx, frontend/src/components/SceneGraphSVG.tsx, frontend/src/pages/SceneGraphPage.tsx, frontend/src/pages/AssetReview.tsx, frontend/src/App.tsx

Execute after Waves 1 & 2 complete. Use frontend-ui-ux skill for UI components. Read reference files, implement, run QA scenarios, save evidence, report completion.
</task_load>
