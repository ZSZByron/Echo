# Learnings - v4-dimension-spec-and-step12

## Convention Patterns
- Experiment code follows pattern: WEIGHT_MATRIX (6×6), DIMENSION_INFO (6 dims), LAYER_NAMES (6 layers)
- build_system_prompt() generates weight bar charts (█░) and ★ markers for high-weight dims (≥25%)
- LLM output validation: 6 dims must all be present (RED/LAW/ACT/NAR/WST/SOC)
- Density ratio measurement: high-weight (≥25%) avg content ÷ low-weight (≤5%) avg content ≥ 2.0x

## Code Patterns
- Provider initialization: `load_provider_config()` → `create_provider()` → `provider.chat_json(messages)`
- Results directory: `backend/experiments/results/` with timestamp filenames
- Experiment structure: TEST_CASES list → run_single() loop → aggregate statistics

## Task Completion: v4 SPEC Creation
- Successfully created SYSTEM_DESIGN_SPEC_v4.md from v3
- Added §18 with 9 subsections (18.1-18.9)
- Version header updated to v4.0 / 2026-08-03
- Changelog updated with v4.0 entry
- TOC extended with §18 entry
- All v3 content preserved (verified via grep: StoryGraph=43, EventGraph=25, ConstraintTree=24)
- 8-way grep verification passed: ConstraintDimension(18), CreationLayer(19), WeightMatrix(33), constraints/generate(1), constraints_routes(3), dimension.py(4), weight_matrix.yaml(2)
- Service classes documented: WeightMatrixLoader, DimensionPromptBuilder, DimensionGenerator (14 total occurrences)
- Dimension output models documented: RedOutput, LawOutput, ActOutput, NarOutput, WstOutput, SocOutput (25 total occurrences)
- Container model: DimensionResultSet (11 occurrences)
- API endpoint fully specified: POST /api/constraints/generate with request/response/error contracts
- Weight matrix validation rules documented (8 scenarios with WeightMatrixError(row, detail))
- Naming collision resolution: ConstraintDimension (6 dims) ≠ ConstraintType (HARD/SOFT)
- Data flow diagram complete from YAML → WeightMatrixLoader → prompts → LLM → DimensionResultSet

## Key Learnings from Documentation Process
- Large file handling: v3 (2668 lines) required offset/limit slicing strategy
- Section reference: Read §17 (offset=2359, limit=250) for format/style reference
- Pattern extraction: Experiment code at lines 72-103 (DIMENSION_INFO), 109-125 (WEIGHT_MATRIX), 172-259 (build_system_prompt), 225-256 (JSON output format)
- Verification approach: Multi-stage grep checks for completeness validation

## Task Completion: Step 2 - Weight Matrix & Dimension Models
- Successfully created data/weight_matrix.yaml with 6 layers × 6 dimensions
- All 6 layers validated: world=100, region=100, scene=100, campaign=100, npc=100, asset=100
- Created backend/app/models/dimension.py with complete type system
- ConstraintDimension enum: RED/LAW/ACT/NAR/WST/SOC (6 dims, exact values preserved)
- CreationLayer enum: world/region/scene/campaign/npc/asset (6 layers, exact values preserved)
- DIMENSION_INFO dictionary: 6 dimension metadata entries (逐字迁移 from experiment L72-103)
- LAYER_NAMES dictionary: 6 layer display names (逐字迁移 from experiment)
- Weight matrix models: WeightMatrixError, WeightMatrixEntry, WeightMatrix
- WeightMatrixEntry validates: 6 dims present, all values ≥0, sum=100
- 6 DimensionOutput models: RedOutput, LawOutput, ActOutput, NarOutput, WstOutput, SocOutput
- Container model: DimensionResultSet with 6 typed fields
- All imports verified: from app.models.dimension import *
- LSP diagnostics clean on both files
- Model validation tested with fixture JSON: all 6 dims parse correctly

## Task Completion: Step 4 - Constraints API Routes & Tests
- Successfully created backend/app/api/constraints_routes.py with POST /api/constraints/generate endpoint
- Request model: ConstraintGenerateRequest with seed_input (min_length=1), seed_description, layer, intent
- Response model: ConstraintGenerateResponse with layer, weights, dimensions, elapsed_seconds
- Error handling: WeightMatrixError → 503, DimensionParseError → 502, validation errors → 422
- Extended backend/app/api/deps.py with get_dimension_generator() DI getter (@lru_cache + get_llm_provider pattern)
- Extended backend/app/main.py with constraints_router import and registration
- Router pattern follows graph_routes.py: APIRouter(prefix=..., tags=[...]) + Request/Response models
- DI pattern follows deps.py: @lru_cache(maxsize=1) + get_llm_provider() composition
- Registration pattern follows main.py: app.include_router(router) alongside existing routers
- Created backend/tests/test_constraints_api.py with 4 test cases (all passing):
  1. test_post_generate_returns_200 - valid body → 200 + dimensions
  2. test_post_generate_invalid_layer_returns_422 - invalid layer → 422
  3. test_post_generate_missing_seed_returns_422 - missing seed_input → 422
  4. test_post_generate_empty_seed_returns_422 - empty seed_input → 422
- MockProvider pattern: inherits LLMProvider, implements chat() and chat_json() for test isolation
- Dependency override: app.dependency_overrides[get_dimension_generator] = lambda: mock_gen
- Real DimensionGenerator with MockProvider preserves _loader.get_weights() access in route handler
- All LSP diagnostics clean on constraints_routes.py, deps.py, main.py, test_constraints_api.py
- OpenAPI schema verified: POST /api/constraints/generate registered with proper request/response models
- Smoke test passed: Status 200 with response keys ['layer', 'weights', 'dimensions', 'elapsed_seconds']
- Test coverage for constraints_routes.py: 88% (lines 65-68 uncovered: error path branches)
- WEIGHT_MATRIX_PATH already existed in paths.py (line 39) - Task 3 completed this
- No modification needed to paths.py - already extended in Task 3
