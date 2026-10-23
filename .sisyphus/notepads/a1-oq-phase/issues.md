# Issues

## [BUG][T5 发现] skip 路径二次收尾 ClosingPanel variant 不切换（frontend，未修）
- 症状：oq_phase 内跳过末题 → 后端正确触发二次收尾（reply 带重定稿文案 + closing.triggered=true），
  但 ClosingPanel 渲染 data-variant="first"（应为 refinalize）。E2E 幕六断言 data-variant="refinalize"
  失败（证据：oq-phase-t5-e2e.txt #13 / oq-phase-t5-gate.txt）。
- 根因：A1Workspace.tsx `skipPendingQuestion`（~L949）只 set closingSignal，缺 closingVariant 判定；
  `sendMessage`（~L868）已有 prevPhase→refinalize 逻辑，skip 路径未镜像。
- 修复（一行级，T4 补丁）：skip 路径在 setOqPhaseActive 前捕获 prevPhase，response.closing?.triggered
  && prevPhase && response.oq_phase_active===false → setClosingVariant("refinalize")。
- 状态：按 T5 MUST NOT DO（禁改 frontend src）未修复；幕六该断言保持红，修复后应即绿。

### [已修复] skip 路径 variant bug（2026-10-20，Orchestrator 授权 T5-FIX）
- 修复：A1Workspace.tsx `skipPendingQuestion` 镜像 sendMessage 判定——捕获 prevPhase，
  `closing.triggered && prevPhase && response.oq_phase_active===false → setClosingVariant("refinalize")`
- 验证：新 vitest 锁定用例（skip 末题响应 → ClosingPanel data-variant="refinalize"）4/4 绿；
  幕六 6/6 passed（oq-phase-t5-e2e.txt）；vitest 344 / tsc 20 delta0（oq-phase-t5-gate.txt 追加节）
