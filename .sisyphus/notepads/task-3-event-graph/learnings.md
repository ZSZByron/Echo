## Learnings
- EventReward probability default 1.0 works as plain float field default (not Field).
- str | dict[str, int|str|bool] union for EventTrigger.condition passes mypy strict but triggers Pyright false positive on dict subscript — use mypy as authoritative checker.
- Field(default_factory=dict) for mutable dict defaults, Field(default_factory=list) for mutable list defaults.
- 100% coverage achievable with 24 tests across 8 classes (3 enum + 5 model).
- No __future__ annotations needed for Pydantic v2 model_dump_json/validate_json.
- test_mutation_safety tests are critical — verify default_factory produces independent instances.

## F3 QA D23 (2026-10-08)
- E2E stub: patch app.api.a1_routes._get_interviewer; TestClient must use app.main:app (a1_routes exports router only).
- AnswerNode shape: first write = root text; complement appends to children (answers_tree dumps both).
- All D23 paths verified: equivalent auto-merge+token+undo roundtrip, complement child append, conflict proposal w/ question_text, classify_confirm_intent merge, raise->needs_clarification fallback template byte-identical to 89ffa2f^.
