# Decisions - Phase 1 Data Models

## Architectural Choices

### Task Delegation Strategy
- Wave 1 (Parallel): T1-T5 can run simultaneously - no dependencies
- Wave 2 (Sequential): T6 requires T2 (StoryNode) completed first
- Wave Final: F1-F4 run only after T7 completion

### Model Implementation Decisions
- **StoryEdge**: Created new typed model instead of `list[dict]` for mypy strict compliance
- **Asset classification**: Default to `ENVIRONMENT` for backward compatibility
- **No frozen=True**: Avoid complexity with recursive CultureNode
- **Pure models**: Phase 1 is data structures only - no YAML I/O or graph traversal

### Verification Decisions
- mypy strict is non-negotiable
- Coverage gate at 85% from pyproject.toml
- All QA scenarios must produce evidence files
