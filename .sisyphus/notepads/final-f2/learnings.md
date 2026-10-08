
## 2026-10-08 F2 review fixes（guide_engine / interviewer）
- 环形导入解法先例：interviewer 需要 guide_engine.answer_view 时用函数内延迟 import（a1_routes 同款），模块级 import 会环。
- auto_merge_log 每条带 kind（equivalent/complement），_record_auto_merge 默认参数实现，complement 调用点显式传。
- Branch 2 节点版同值短路口必须放在 relation 提取之后且仅在 relation != "equivalent" 时生效——否则会吞掉 merge_target 指向同级条目的等价合并。
- undo_auto_merge 乱序撤销：恢复旧快照后必须清理同 field_key 的所有后续合并（日志条目 + merge_undo token），否则再次撤销会跳到不一致状态。
- 常量落地：ANSWER_CHILDREN_CAP=6（拍板4）、MERGE_TARGET_PREFIX_CHARS=12，替换散落字面量。
- 注意：git status 中 README.md 的改动是此前会话遗留，非本任务产生。

## F3 QA D23 (2026-10-08)
- E2E stub: patch app.api.a1_routes._get_interviewer; TestClient must use app.main:app (a1_routes exports router only).
- AnswerNode shape: first write = root text; complement appends to children (answers_tree dumps both).
- All D23 paths verified: equivalent auto-merge+token+undo roundtrip, complement child append, conflict proposal w/ question_text, classify_confirm_intent merge, raise->needs_clarification fallback template byte-identical to 89ffa2f^.
