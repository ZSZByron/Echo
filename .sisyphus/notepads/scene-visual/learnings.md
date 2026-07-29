## AssetPlaceholder (T0c) - Completed

- **Tailwind v4** uses @import "tailwindcss" in index.css; custom colors still defined in tailwind.config.js (
eon-green, 
eon-cyan, 
eon-red).
- **No .crt-scanlines utility class exists** — inline epeating-linear-gradient via style={{...}} is the codebase pattern (see GodWatchIndicator.tsx).
- **Named exports** are the convention (Terminal.tsx, GodWatchIndicator.tsx both use xport function).
- **GodWatchIndicator pattern**: uses ixed inset-0 + pointer-events-none for overlays, inline style for gradients/shadows, Tailwind classes for colors/animation.
- **TypeScript strict**: 	sc --noEmit passes clean with the new component.
- For object placeholder, used min-w-20 min-h-20 (not w-20 h-20) so consumers can override size via className while keeping minimum bounds.
- React.CSSProperties import not needed — React namespace available globally via tsconfig JSX settings.

---

## AssetReview page scaffold (T0d) - Completed (2026-07-27)

### What was built
- `frontend/src/pages/AssetReview.tsx` — named-export component, three-column layout: list `w-80` / preview `flex-1` / properties `w-96`. Full-screen `h-screen w-screen bg-black text-neon-green font-mono overflow-hidden`.
- `frontend/src/App.tsx` — added `window.location.pathname.startsWith('/admin/assets')` detection inside `AppContent`; game rendering untouched in else branch. `GameStateProvider` still wraps both routes.

### Design system reuse (no new tokens introduced)
- Status dot colors: `bg-gray-500` (pending), `bg-neon-cyan` (completed), `bg-neon-green` (approved), `bg-neon-red` (rejected). Pending uses tailwind default gray per spec — NOT a custom neon token (matches StatusPanel precedent of using `bg-gray-800` for tracks).
- Type icons use Unicode glyphs: `▦` (background), `◈` (object) — no image assets needed.
- Borders: `border-2 border-neon-green` for major sections; `border-dashed` for preview placeholder; `border-r-2` / `border-l-2` for column separators.

### Routing approach
- NO react-router. `window.location.pathname.startsWith('/admin/assets')` + `<a href="/">`. Full-page reload on switch — acceptable for scaffold; `GameStateProvider` re-inits from API on mount.
- T5 will refine z-index layering (per task context).

### Verification
- `npx tsc --noEmit` PASSES (no output, exit 0).
- LSP `typescript-language-server` not installed globally — relied on `tsc` as authoritative.

### Gotchas for T4
- `MOCK_ASSETS` constant must be replaced with `GET /api/assets` call.
- All action buttons (GENERATE / APPROVE / REJECT / REGENERATE / GENERATE ALL PENDING) are `disabled` with `cursor-not-allowed` — remove `disabled` + wire handlers in T4.
- First asset is pre-selected (`useState<string | null>(MOCK_ASSETS[0]?.id ?? null)`) so panels are populated on mount.
- `MockAsset` interface includes `negativePrompt` field beyond the required `prompt` (spec asked for negative prompt textarea).
- Filter buttons: ALL / PENDING / COMPLETED / APPROVED / REJECTED. Type alias `FilterType = 'all' | AssetStatus`.

## T0d: Asset Manifest System (completed)

### Files Created
- ackend/app/models/asset.py — Asset Pydantic model + AssetStatus/AssetType enums
- ackend/app/state/asset_store.py — AssetStore CRUD over JSON manifest + init_manifest()
- ackend/tests/unit/test_asset_store.py — 30 tests, all passing
- data/assets/manifest.json — 5 assets (1 bg + 4 objects from temple_ruins)

### Key Patterns
- **Project root resolution**: Path(__file__).resolve().parent.parent.parent.parent from ackend/app/state/ → UGC root (3 parents = state→app→backend→UGC). Mirrors world_loader.py which uses 4 parents from pp/engine/.
- **Manifest shape**: {"assets": [...], "version": "1.0", "updated_at": "<iso>"} — plain JSON, no SQLite.
- **Idempotent init**: checks existing asset IDs before adding, never overwrites.
- **Transition validation**: allowed set = {(PENDING,GENERATING), (GENERATING,COMPLETED), (GENERATING,FAILED), (COMPLETED,APPROVED), (COMPLETED,REJECTED), (REJECTED,PENDING), (FAILED,PENDING), (APPROVED,PENDING)}. All others raise InvalidTransitionError.
- **generation_status auto-sync**: when status changes to generating/completed/failed, generation_status is updated automatically.
- **approved_at auto-set**: when transitioning to APPROVED, approved_at timestamp is set if not already present.

### Test Strategy
- Uses 	mp_path fixture to avoid clobbering real manifest.
- Disallowed transitions tested parametrically (9 cases).
- _set_status_directly() helper walks valid paths to reach any status for negative tests.

---

## T0a: AI Image Generation Runtime

- PowerShell here-strings mangle Python triple-quotes. Use the `write` tool for .py files.
- `[System.IO.File]::WriteAllText` with UTF8 adds BOM. Use the `write` tool instead.
- `patch("builtins.__import__")` causes infinite recursion. Use `sys.modules` manipulation instead.
- When mocking `httpx.AsyncClient` via `patch`, do NOT use `spec=httpx.AsyncClient` inside the patch context.
- `from rembg import remove` inside a function means `patch("app.ai.bg_remover.remove")` fails. Install fake module in `sys.modules` then patch `rembg.remove`.

## T0f: Assets API Routes - Completed (2026-07-27)

- Module-level _store injection: tests replace ar._store before importing app
- _run_generation is module-level async function for AsyncMock replacement
- Lazy import of ImageGenerator keeps routes importable without AI SDKs
- generate-all/bulk-approve skip InvalidTransitionError silently
- TestClient fixture imports app AFTER patching module globals

## T4: SceneView/SceneObject/useScene/types-scene - Completed (2026-07-27)

### Files Created
- frontend/src/types/scene.ts — Position, SceneObjectDTO, SceneResponse (exact shape from task spec)
- frontend/src/hooks/useScene.ts — named `useScene` returning {scene, loading, error}; AbortController-timeout mirroring api/client.ts
- frontend/src/components/SceneObject.tsx — positioned sprite with primary/secondary variants + holographic_altar mix-blend screen
- frontend/src/components/SceneView.tsx — absolute inset-0 z-0 container wiring useScene + AssetPlaceholder fallback + loading/error overlays

### Key Decisions
- **Hook does NOT use apiClient singleton** — apiClient has no `getScene` method and task said "mirror api/client.ts pattern" (the AbortController-timeout), not "use apiClient". Used raw fetch with same TIMEOUT_MS=30000.
- **onObjectClick threaded through SceneView -> SceneObject**: task spec gave SceneView an internal `handleObjectClick` "no-op/console.log" but also said "Accept an onObjectClick? prop". Chose the prop-forwarding approach — cleaner handoff to T6 (no rewrite needed).
- **scene!.background_asset non-null assertion** used inside `hasBackground` guard branch: TypeScript can't narrow across the `scene?.background_asset && !bgBroken` short-circuit for the inner `scene!.background_asset as string` cast — used assertion + cast to satisfy strict mode.
- **img onError triggers local state** (`useState(false)` per-image) rather than global "asset broken" — each object/bg tracks its own failure independently so one broken asset doesn't disable others.
- **mixBlendMode typed as `'screen' as const`** inside CSSProperties spread — required because TS widens string literal otherwise.
- **role="button" only for primary objects** — secondary objects are decorative (no click affordance expected per spec "no glow" + opacity-70).

### Verification
- `npx tsc --noEmit` PASSES (exit 0, no output).
- typescript-language-server STILL not installed globally — tsc remains authoritative (consistent with T0c, T0d notepads).

### Handoffs
- **T5 (App.tsx integration)**: SceneView container is `absolute inset-0 z-0` — parent MUST be `relative` (or otherwise positioned). T5 owns z-index layering above z-0 (terminal/status panels).
- **T6 (click->input wiring)**: SceneView accepts `onObjectClick?: (objectId, objectName, isPrimary) => void`. T6 passes a callback that focuses/populates the input bar; no SceneView changes needed.
- **T2 (/api/scene endpoint)**: hook codes against SceneResponse interface — when backend lands, response shape MUST match Position {x,y}, SceneObjectDTO fields, SceneResponse fields exactly.
- **T9 (holographic refinement)**: current impl is a string-contains check on `object.id` for "holographic_altar" applying `mixBlendMode: screen`. T9 will refine visual treatment.

### Gotchas
- typescript-language-server still not installed in this env — verification via `tsc` only.
- React.CSSProperties type used directly without React import (works because tsconfig JSX auto-imports React types — same pattern as AssetPlaceholder T0c).

## T8: Visual Spec Layer (style_bible, palette, prompts) - Completed (2026-07-27)

### Files created
- `data/visual/style_bible.md` — 8 sections: World, Architecture, Technology, Atmosphere, Lighting, Color Palette, Object Generation Rules, Background Generation Rules
- `data/visual/palette.yaml` — background (3 tones), neon (4), material (3), text (3), glow reference
- `data/visual/prompts.yaml` — 1 background (temple_ruins_bg) + 4 objects, all prompts fully expanded inline

### Key decisions
- **Five-segment format**: segments dict kept as reference, but all `full_prompt` strings have segments expanded inline (no template variables at runtime). This means consumers can use the prompt string directly without interpolation.
- **prompts.yaml object keys** use `temple_ruins_` prefix (e.g. `temple_ruins_ancient_locked_door`) matching scene_id + object_id convention for asset lookup.
- **holographic_altar** has `special: "mix-blend-mode: screen"` — black bg becomes transparent via CSS, skip bg removal.
- **Danger glow on door**: added "faint red danger glow" to the locked door prompt since interaction_targets marks it is_dangerous: true.

### Verification gotcha
- Windows default encoding is GBK. `yaml.safe_load(open(path))` fails with UnicodeDecodeError on UTF-8 files. Must use `open(path, encoding='utf-8')`. The task verification command should be updated for Windows or files must be ASCII-only. Prompts contain em-dash characters so UTF-8 is required.
- All three files verified: both YAML files parse cleanly with explicit UTF-8 encoding.
## T0f-wire: AssetReview API wiring (completed 2026-07-27)

### Files
- CREATED frontend/src/api/assets.ts: typed client - 9 functions mirroring assets_routes.py
- MODIFIED frontend/src/api/client.ts: exported fetchWithTimeout so assets.ts could reuse it
- REWROTE frontend/src/pages/AssetReview.tsx: replaced MOCK_ASSETS with real API + full functionality

### Key Decisions
- snake_case everywhere on the wire: Backend Pydantic default is snake_case. Frontend Asset interface matches 1:1 (negative_prompt, generation_status, file_path, parent_scene, reviewer_note, error_message, approved_at, created_at). No camelCase mapping layer.
- fetchWithTimeout exported from client.ts: simplest reuse path. Already correct (AbortController + 30s timeout). Marking export is non-breaking.
- Polling strategy: single setInterval in one useEffect keyed on generatingIds (memoized array). Each tick fetches status for every generating asset in parallel via Promise.all; if ANY transitioned out of generating, triggers full refresh(). 3s cadence per spec.
- assetsRef pattern: useRef mirror of assets so polling closure reads latest IDs without re-subscribing interval every render. Effect depends only on generatingIds (identity changes only when the set of generating assets changes).
- Prompt drafts are local state: promptDraft/negativeDraft synced from selected asset via dedicated effect, separate dirty-check effect. SAVE disabled until dirty. Avoids clobbering user edits when polling refresh mutates asset list.
- Status color map: 6 entries. generating = neon-cyan + animate-pulse; failed = neon-red + opacity-60. Both dot and text use same class string.
- Filters: added GENERATING and FAILED to original 5.
- Preview rendering: file_path !== null AND status in {approved, completed} -> img; else AssetPlaceholder. Added onError handler to hide broken images at runtime.

### Gotchas
- T0d scaffold used MockAsset with camelCase negativePrompt; real API is snake_case negative_prompt. New Asset interface uses snake_case.
- Pre-selection effect: selectedId starts null and set to assets[0].id only after initial fetch resolves.
- handleReject sends empty reviewer_note (spec allows optional). No modal prompt for note.
- busyIds is ReadonlySet<string> to prevent accidental mutation; updates create a new Set.
- REGENERATE = GENERATE + window.confirm. Both share same enable condition (GENERATABLE_STATUSES).
- flashNotice auto-clears after 3.5s via setTimeout. No toast library.

### Verification
- npx tsc --noEmit PASSES (no output, exit 0).
- LSP typescript-language-server still not installed globally - relied on tsc as authoritative.

## T2 Scene API Endpoint (GET /api/scene)

- AssetStore instantiation: routes.py creates AssetStore() per-request (not singleton). For testing, patch app.api.routes.AssetStore with a factory returning the test store.
- WorldLoader: Available via get_world_loader() from app.api.deps. load_scene(scene_id) returns a Scene pydantic model.
- GameObject extra field: Added optional position: Optional[dict[str, float]] to GameObject in world.py so YAML positions are parsed into the model.
- Asset path convention: Approved assets return /assets/{asset_id}.png as their URL path, mapped to StaticFiles mount at /assets -> data/assets/.
- is_primary logic: object.is_future_anchor == true OR corresponding interaction_target.is_dangerous == true.
- Test pattern: Use unittest.mock.patch on app.api.routes.AssetStore as a context manager around TestClient(app). Store fixture uses init_manifest() from temp path.
- StaticFiles path: Path(__file__).resolve().parent.parent.parent from main.py gives project root (UGC/), then / data / assets.

## T6: Scene Click -> Input Bar (click->input data flow)

### What was done
- `Terminal.tsx`: Added `TerminalProps` interface with `pendingInput?: string` + `onPendingInputConsumed?: () => void`. Added `inputRef` (`useRef<HTMLInputElement>`) attached to the `<input>` element. Added `useEffect` that watches `pendingInput`: sets input value, focuses input, calls consumed callback. Does NOT auto-submit.
- `App.tsx`: Added `useState('')` for `pendingInput`. Added `handleObjectClick(objectId, objectName, isPrimary)` that builds primary=`检查 X（id）` / secondary=`查看 X` text. Passed `onObjectClick` to `<SceneView>` and `pendingInput`/`onPendingInputConsumed` to `<Terminal>`.
- `SceneObject.tsx` / `SceneView.tsx` (T3): Already correctly implemented — onClick wiring + hover effects (primary: cyan glow + scale-105; secondary: opacity transitions). No changes needed.

### Coordination with T5 (parallel layout task)
- T5 restructured App.tsx layout into overlay layers (SceneView z-0, terminal/status/topbar z-20). When T6 ran, the file had ALREADY been modified by T5. T6's edits (state + handler + props on SceneView/Terminal) were in different regions than T5's layout wrapper divs, so no conflict. Lesson: always re-read App.tsx before editing if a parallel task touches it.

### Verification
- `npx tsc --noEmit` in `frontend/` => clean (zero errors).
- LSP typescript-language-server not installed in this env; tsc is authoritative.

### Pattern: parent->child prefill without submit
Use a `pendingInput` string prop + `onConsumed` callback. Child `useEffect` watches prop, sets internal state, focuses, then calls consumed so parent clears. Player manually presses Enter. Avoids coupling click to submit logic.

## T5: App.tsx z-index layering refactor - Completed (2026-07-27)

### Files modified
- frontend/src/App.tsx - game-scene branch rewritten as z-layered overlay layout
- frontend/src/components/Terminal.tsx - root div h-screen w-2/3 -> h-full w-full; inner output minHeight 400px -> 0
- frontend/src/components/StatusPanel.tsx - both branches w-1/3 bg-black border-2 rounded -> h-full w-full overflow-y-auto

### Layout structure (z-axis)
- Outer: elative min-h-screen w-screen overflow-hidden bg-black (positioning context for all overlays)
- z-0: <SceneView /> (absolute inset-0, fullscreen background — unchanged internally)
- z-20 top bar: bsolute top-0 left-0 right-[320px] p-3 bg-black/70 backdrop-blur-sm border-b border-neon-green (title + ResetButton)
- z-20 terminal overlay: bsolute bottom-0 left-0 right-[320px] bg-black/70 backdrop-blur-sm border-t border-neon-green style={{height:'45%'}}
- z-20 status overlay: bsolute top-0 right-0 w-[300px] h-full bg-black/70 backdrop-blur-sm border-l border-neon-green
- z-50: <GodWatchIndicator /> (fixed inset-0 pointer-events-none, unchanged)

### Key Decisions
- **right-[320px] on top bar + terminal overlay vs w-[300px] on status panel**: 320 leaves 20px gap between terminal region and status panel edge. Acceptable: the 20px strip shows scene background through, acting as a visual separator. Alternative would be right-[300px] for flush fit; chose 320 to match task spec verbatim.
- **Dropped border-2/rounded/bg-black from StatusPanel root**: overlay container already supplies bg-black/70 + border-l. Keeping them would double-border. Inner content keeps its own section dividers (border-t border-neon-green pt-4) which still render correctly.
- **Terminal inner minHeight 400px -> 0**: 45% of a 1080px viewport = ~486px. Minus p-4 (32px) + form (~50px) = ~404px available. 400px minHeight was borderline and would force overflow at smaller viewports. Switched to 0 so flex-1 + overflow-y-auto behaves correctly inside the constrained overlay. NOT a logic change (layout-only).
- **Kept bg-black border-2 border-neon-green rounded on Terminal's inner output area**: it's a nested scroll container, looks fine inside the overlay. Only root sizing changed.

### Verification
- 
px tsc --noEmit PASSES (exit 0, no output)
- LSP typescript-language-server STILL not installed - tsc authoritative (consistent with T0c/T0d/T4 notepads)
- Confirmed via Select-String: no stale h-screen w-2/3 or w-1/3 p-4 remain in the three modified files

### Coexistence with T6 (click->input wiring)
- App.tsx on disk already had T6's handleObjectClick + pendingInput state + <SceneView onObjectClick=...> + <Terminal pendingInput=... onPendingInputConsumed=...> merged in when I read it. My edits layered the z-index layout on top of that wiring without conflict. Both features coexist cleanly.

### Handoff to T8 (visual verification)
- Scene objects at y<50% (door y=35, pillar y=30) will be visible above the terminal overlay (bottom 45%). Corpse at y=65 and altar at y=55 MAY be partially covered by terminal overlay - acceptable per task spec ("y < 50% must NOT be covered" - the explicit constraint).
- Status panel covers full height on right 300px - any scene content in that strip is occluded. Acceptable.
- Top bar is thin (~60px) - minimal occlusion at very top.

## T7: Display Components (echo_vision, available_actions, tension_level) - DONE

### What was done
- **ActionHints.tsx** created: clickable tag buttons, null on empty, calls onActionClick
- **useGameState.tsx**: added `'echo'` to TerminalLine type union; added `availableActions: string[]` to GameState; added `SET_AVAILABLE_ACTIONS` action + reducer case
- **Terminal.tsx**: renders echo lines with magenta glow (`#ff00ff` text-shadow); dispatches SET_AVAILABLE_ACTIONS on response; renders `<ActionHints>` between terminal output and input bar; clicking a hint fills the input (setInput + focus)
- **StatusPanel.tsx**: added TENSION progress bar (derived from godWatchLevel 0-3 → 0/33/66/100%), gradient green→red; added ATMOSPHERE static text section

### Key patterns
- echo_vision rendered as inline-styled div (no tailwind token for magenta glow — used `style={{ color, textShadow }}`)
- available_actions stored in global game state via reducer, not local component state — allows ActionHints to render in any component
- Action click fills input via `setInput(action)` — does NOT auto-submit (per requirement)
- Tension derived from existing godWatchLevel, no backend field needed

### Verification
- `npx tsc --noEmit` passes clean (0 errors)

## T9: Prompt Template Integration + Coordinate Tuning - Completed (2026-07-27)

### Files Modified
- `backend/app/state/asset_store.py` — Added `_PROMPTS_PATH` constant + `_load_prompts()` module-level helper; modified `init_manifest()` to load `data/visual/prompts.yaml` once and populate `prompt`/`negative_prompt` for new bg + object assets.
- `data/scenes/temple_ruins.yaml` — Adjusted positions: door (50,30), corpse (20,50), altar (70,45), pillar unchanged (15,30). All y < 55 to avoid terminal overlay.
- `frontend/src/components/SceneObject.tsx` — NO CHANGES. T3 already correctly implements `mixBlendMode: 'screen' as const` for `object.id.includes('holographic_altar')`.

### Key Decisions
- **Module-level `_load_prompts()`**: Returns `{}` on missing file so callers fall back gracefully. Loaded ONCE per `init_manifest()` call, shared across all scenes (efficient — no repeated file reads).
- **Fallback chain for object prompts**: `prompts.yaml.full_prompt` → `scene_yaml.description` → `""`. Background: `prompts.yaml.full_prompt` → `""` (no description field on scene root used for bg prompt).
- **Idempotency preserved**: The `existing` set check happens BEFORE prompt lookup, so prompts.yaml is never consulted for assets that already exist. Verified empirically: tampered prompt survives re-init.
- **Coordinate adjustments**: corpse moved y65→50 (was fully covered by terminal), altar y55→45 + x75→70 (borderline + status panel risk). All 4 objects now have y ≤ 50.
- **SceneObject holographic check**: `object.id.includes('holographic_altar')` matches asset ID `temple_ruins_holographic_altar` correctly. Case-sensitive but the ID is always lowercase in our data. No refinement needed.

### Verification
- `pytest tests/unit/test_asset_store.py -v --no-cov` → 30/30 PASSED.
- `npx tsc --noEmit` → clean (exit 0, no output).
- Fresh manifest test: all 5 assets have prompt (568-690 chars) + negative_prompt (146 chars) from prompts.yaml.
- Idempotency test: tampered prompt survives `init_manifest()` re-run.

### Gotchas
- prompts.yaml object keys use `temple_ruins_` prefix (matches `f"{scene_id}_{obj_id}"` asset_id convention). Critical for correct lookup.
- The 30 existing tests still pass unchanged — they use synthetic scene YAML in tmp_path and don't rely on prompts.yaml content. The prompts.yaml integration is purely additive (only affects assets that had empty prompts before).
- Asset.negative_prompt field already existed (default `""`) — no model change needed.
