
## F2 review of 89ffa2f^..12f80a1 (D23 semantic merge) — REJECT, 1 blocker
- BLOCKER interviewer.py:272 _answers_digest v[:40] TypeError on AnswerNode (raw session.answers via getattr at 404/597/661) -> DegradingInterviewer swallows -> every LLM turn degrades once a node lands in first 12 answered keys. Fix: pass answer_view-rendered dict at interviewer boundary.
- WARNING guide_engine.py:1077 deflect file_diff "new" may emit raw AnswerNode object (missing answer_view).
- WARNING AutoMergeDisclosure.kind required in TS but backend _record_auto_merge never emits "kind" (contract drift).
- WARNING Branch 2 node same-value short-circuit precedes relation dispatch; can swallow equivalent+merge_target when fill_value exactly equals an unrelated child text.
- WARNING undo of older token silently reverts newer merge on same key while its log entry stays (ledger/state divergence).
- NIT inline magic numbers 6 (children cap) / 12 (prefix len) unnamed; chat_confirm clarification reply keeps a third literal copy of the three-choice template.

## F2 re-verdict on 75f0467 — all 7 findings resolved (7=WONTFIX documented), APPROVE
- Deferred import verified cycle-free (interviewer has no top-level guide_engine import); digest renders AnswerNode "甲；乙".
- Guard reorder preserves legacy skip for missing-relation fills (relation="" != "equivalent" still short-circuits).
- Undo purge semantics: any same-key entry other than the undone token is purged — over-purge on newest-token undo is intended (older snapshots invalid anyway).
- Local verification: D23 32 passed; full tests/unit/a1 1092 passed.
