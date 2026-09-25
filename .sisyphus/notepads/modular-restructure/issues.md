
## [2026-09-24] G 治理批：双写冲突——spec v1.3 两版并存（未解决，需 Orchestrator 裁量）

- 提交 2788b9e 时发现另一会话（双写阀模式，同 M4a/b/c）同步在场：①对 v1.2 spec 文件**原地升版**（标题改 v1.3 + §0 追加 v1.3 条 + 新增 §5.2.1 配方重述表，真源引用 module_registry.py RECIPES/M11/M12/entry_subfield——实施细节比本方新文件更精确，但违反"MUST NOT 修改原 v1.2 文件"）②另建 docs/plans/2026-09-24-b1-redefinition-proposal.md（与本方 2026-09-24-b1-acceptance-redefinition-proposal.md 同题异版）。
- 本方处理：只提交自己的六个文件；上述两处变更留在工作区未 staged（v1.2 原地改动 unstaged，对方 B1 文件 untracked），未删除未回滚。
- **待裁决**：spec v1.3 权威载体二选一——本方顺延号新文件（治理规则合规）vs 对方原地 §5.2.1（内容更贴代码现实）。建议合并：以新文件为权威载体，把对方 §5.2.1 的 RECIPES 配方矩阵并入新文件 §5.2.2，然后回滚 v1.2 原地改动。B1 两份提案同理择一归档。
- 另 .sisyphus/plans/modular-restructure.md 有 unstaged 修改（Orchestrator 管理checkbox，未触碰）。

## [2026-09-24] G 治理批（本方收尾会话视角）：2788b9e 之后的工作区增量
- 本会话在 2788b9e 落地后进场，按任务简报权威口径执行：impulse spec = **同文件原地升 v1.3**（spec 自身头注与 §0 台账即成文惯例：任何修订升版本号记 §0，治理文档才用顺延号新文件），D14 行失配 wikilink（指向顺延号新文件）已修正为链原文件名。
- 本提交内容：原 spec 原地 v1.3（§0 条目 + §5.2.1 配方矩阵，真源 = module_registry.py RECIPES）+ B1 提案（2026-09-24-b1-redefinition-proposal.md，任务指定文件名）+ PROJECT_STATE 当前阶段条 + notepad 增量。
- **残留冗余待 Orchestrator 处置**：docs/plans/2026-09-18-impulse-entry-system-spec-v1.3.md（2788b9e 引入的顺延号版本）与原地 v1.3 内容重叠、2026-09-24-b1-acceptance-redefinition-proposal.md 与本方 B1 提案同题异版。本方受 MUST NOT delete 约束未删除；建议择一归档（内容上原地版 §5.2.1 与代码 RECIPES 对齐更紧）。

## [F1 2026-09-24] 合规审计发现（REJECT 两项）
- CHANNELS 未落地：Must Have §97 命名 CHANNELS（探索态+玩法设计链，撤销 exploration 冲动行），实际 exploration 仍是冲动配方行（module_registry.py:46），代码/规格 v1.3 均无 CHANNELS，且无 D 台账缓期记录。
- MODULE_POOL 产出面缩水：§97 要求 L2×5+L3×3，实际仅 L2×3（output_modules.py:35 注释"归后续波次"，无产品方/台账裁决背书）。
- 其余 Must Have/DoD/TODO 验收全部 PASS（verify.ps1 1260/82%/tsc 0/vitest 239）。处置选项：补 D 台账缓期裁决（Orchestrator 呈产品方）或补实施。

## F3 真实手动 QA (2026-09-24)
- **发现 BUG（REJECT 依据）**: POST /api/a1/file/{id}/dice-template → 500。根因: a1_routes.py:2305 _cst_constraints 假设 graph_json.nodes 全为 dict，定稿图含纯字符串节点 → AttributeError: 'str' object has no attribute 'get'。连锁：character-template 永远 409 missing_dice_template（dice 未落库）。复现：plot 会话 finalize 后调 dice-template 必现。
- chat 契约：/api/a1/chat 请求体需 session_id（非 file_id）；dice/character 端点在 finalize 之后才可用（409 pending_finalize 前置）。
- 其余全绿：A1-A5 翻车重放全过（首问=剧情.core_dilemma、deflection 落"（用户跳过）"且指针前进、妹妹剧情细节归档到 secret_layer 无 main_plot 提案）；default 配方首问=IP定位.name；finalize 200；doc 确定性骨架九节；impulse-coords/field_sources/persona-card("ECHO 创作人格") 均 200。
