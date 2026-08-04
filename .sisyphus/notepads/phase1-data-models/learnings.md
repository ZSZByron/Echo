# Learnings - Phase 1 Data Models

## Timestamps of Task Starts
- Session start: 2026-08-01T15:52:26Z

## Key Conventions Discovered
*All models use `Field(default_factory=...)` for mutable defaults*
*All enums use `class X(str, Enum)` pattern with docstrings*
*No `model_config` in existing models - maintain backward compatibility*
*datetime defaults: `Field(default_factory=lambda: datetime.now(timezone.utc))`*

## Gotchas
- **StoryEdge**: New typed model required to replace `list[dict]` for mypy strict
- **Asset extension**: Must NOT modify existing fields, only append at end
- **No exports in __init__.py**: Keep models/__init__.py empty as per existing convention
- **Coverage gate**: pyproject.toml has `--cov-fail-under=85` - all new models need tests

## File Structure Patterns
- Graph models follow: enum → node → edge → graph container
- All models pure Pydantic, no business logic in Phase 1

[2026-08-02 00:00:02] Task 2: story_graph.py implementation
- 6 classes: StoryNodeType(str,Enum), StoryCondition, StoryChoice, StoryEdge, StoryNode, StoryGraph
- All BaseModels (no model_config per codebase pattern)
- StoryEdge is typed model replacing list[dict] from S5
- All mutable defaults use Field(default_factory=...) - verified 9 instances
- mypy --strict: 0 errors
- pytest: 35 tests, 100% coverage on story_graph.py
- Pyright LSP gotcha: dict key access on str|dict union needs isinstance narrowing
- __init__.py kept empty (no export registration)

## Task 6 - Asset Extension (2026-08-02 00:05:13)

### Key Decisions
- AssetClassification placed after AssetType enum, before Candidate class
- 3 new fields appended after depth field, before validators
- Default classification=ENVIRONMENT ensures backward compat

### Gotchas
- mypy --strict has 6 pre-existing errors not caused by our changes
- 3 pre-existing test failures in asset_store and image_generator
- All 9 new tests pass, all 71 pre-existing asset tests pass (zero regression)
