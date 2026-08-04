## Learnings
- EventReward probability default 1.0 works as plain float field default (not Field).
- str | dict[str, int|str|bool] union for EventTrigger.condition passes mypy strict but triggers Pyright false positive on dict subscript — use mypy as authoritative checker.
- Field(default_factory=dict) for mutable dict defaults, Field(default_factory=list) for mutable list defaults.
- 100% coverage achievable with 24 tests across 8 classes (3 enum + 5 model).
- No __future__ annotations needed for Pydantic v2 model_dump_json/validate_json.
- test_mutation_safety tests are critical — verify default_factory produces independent instances.
