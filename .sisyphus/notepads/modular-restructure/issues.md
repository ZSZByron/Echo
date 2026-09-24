
## [2026-09-24] G 治理批：双写冲突——spec v1.3 两版并存（未解决，需 Orchestrator 裁量）

- 提交 2788b9e 时发现另一会话（双写阀模式，同 M4a/b/c）同步在场：①对 v1.2 spec 文件**原地升版**（标题改 v1.3 + §0 追加 v1.3 条 + 新增 §5.2.1 配方重述表，真源引用 module_registry.py RECIPES/M11/M12/entry_subfield——实施细节比本方新文件更精确，但违反"MUST NOT 修改原 v1.2 文件"）②另建 docs/plans/2026-09-24-b1-redefinition-proposal.md（与本方 2026-09-24-b1-acceptance-redefinition-proposal.md 同题异版）。
- 本方处理：只提交自己的六个文件；上述两处变更留在工作区未 staged（v1.2 原地改动 unstaged，对方 B1 文件 untracked），未删除未回滚。
- **待裁决**：spec v1.3 权威载体二选一——本方顺延号新文件（治理规则合规）vs 对方原地 §5.2.1（内容更贴代码现实）。建议合并：以新文件为权威载体，把对方 §5.2.1 的 RECIPES 配方矩阵并入新文件 §5.2.2，然后回滚 v1.2 原地改动。B1 两份提案同理择一归档。
- 另 .sisyphus/plans/modular-restructure.md 有 unstaged 修改（Orchestrator 管理checkbox，未触碰）。

## [2026-09-24] G 治理批（本方收尾会话视角）：2788b9e 之后的工作区增量
- 本会话在 2788b9e 落地后进场，按任务简报权威口径执行：impulse spec = **同文件原地升 v1.3**（spec 自身头注与 §0 台账即成文惯例：任何修订升版本号记 §0，治理文档才用顺延号新文件），D14 行失配 wikilink（指向顺延号新文件）已修正为链原文件名。
- 本提交内容：原 spec 原地 v1.3（§0 条目 + §5.2.1 配方矩阵，真源 = module_registry.py RECIPES）+ B1 提案（2026-09-24-b1-redefinition-proposal.md，任务指定文件名）+ PROJECT_STATE 当前阶段条 + notepad 增量。
- **残留冗余待 Orchestrator 处置**：docs/plans/2026-09-18-impulse-entry-system-spec-v1.3.md（2788b9e 引入的顺延号版本）与原地 v1.3 内容重叠、2026-09-24-b1-acceptance-redefinition-proposal.md 与本方 B1 提案同题异版。本方受 MUST NOT delete 约束未删除；建议择一归档（内容上原地版 §5.2.1 与代码 RECIPES 对齐更紧）。
