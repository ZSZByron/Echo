# Issues


## T14（2026-09-28）
- test_graph_digest.py::test_graph_present_injects_digest_block 原规格在整个 prompt 断言无裸键，与 test_dynamic_invites G5 liveness（after_invite 需要裸键出现在 prompt）矛盾——已收窄断言作用域至摘要块（实现与测试规格冲突，理由落账 evidence/task-14-digest.txt）。若上游坚持全 prompt 键域清洁，需另行设计 _field_catalog 双形态渲染（功能性改动，超出本任务白名单）。
