# Puzzle-Driven Asset Pipeline - Decisions

## Architectural Decisions

### Sprint 1: P0 Fix + Demo Chain
- **Decision**: Fix reference_asset_ids passing first (Task 1) - independent of YAML upgrades
- **Rationale**: Single-function change, no dependencies, unblocks Task 4 verification

### Sprint 2: Architecture Separation  
- **Decision**: Create PuzzleGraph before GenerationPlanner
- **Rationale**: Planner depends on PuzzleGraph for puzzle chain ordering
- **Decision**: Asset views refactor before Planner integration
- **Rationale**: Planner needs to work with updated Asset model

### Sprint 3: Prompt System
- **Decision**: PromptBuilder before template refactor
- **Rationale**: Builder defines template variable names that YAML must match

### Sprint 4: UI + Tests
- **Decision**: Frontend depends on Task 7 completion
- **Rationale**: AssetReview.tsx needs Asset.views structure to display

## Task Dependencies
```
Sprint 1: Tasks 1,2,3 (parallel) → Task 4 (sequential)
Sprint 2: Task 2 → Task 5 → Task 6 → Task 8 (sequential chain)
           Task 2 → Task 7 (parallel with 5,6) → blocks 8,11
Sprint 3: Tasks 9,10 (parallel)
Sprint 4: Tasks 11,12,13 (parallel, all depend on earlier sprints)
```

## Critical Path
Task 1 → Task 4 → Task 5 → Task 6 → Task 8 → Task 13

