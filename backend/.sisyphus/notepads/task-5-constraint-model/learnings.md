# Implementation Learnings - Task 5: Constraint Model

## Key Learnings

### Scene_id=None for Global Constraints
- ConstraintTree.scene_id uses str | None = None to support both scene-specific and global constraints
- Global constraints have scene_id=None (tested in test_constraint_global_scene_id_none)
- Pattern matches V3 §17.1 signature exactly

### Default Values and Field Factories
- ConstraintNode priority defaults to 0 (tested)
- All list fields use Field(default_factory=list) to avoid mutable default issues
- ConstraintTree.nodes: list[ConstraintNode] = Field(default_factory=list)
- ConstraintNode.applicable_types: list[str] = Field(default_factory=list)

### Enum Pattern (from asset.py:12-29)
- ConstraintType follows exact pattern: class ConstraintType(str, Enum):
- Docstring on class level: """约束类型。"""
- Inline docstrings for values: HARD = "hard"  # 硬约束：违反则资产生成失败

### Type Checking Success
- mypy --strict passes with 0 errors
- Used dict[str, Any] | None for optional rule_config
- Used str | None for optional scene_id

## Verification Results
- All 4 tests pass (100% coverage on constraint.py)
- mypy strict: 0 errors
- LSP diagnostics: clean
- Evidence files created:
  - task-5-constraint-instantiation.txt: PASS
  - task-5-constraint-global.txt: PASS

## Files Created
1. backend/app/models/constraint.py - 3 classes (ConstraintType, ConstraintNode, ConstraintTree)
2. backend/tests/models/test_constraint.py - 4 test cases
