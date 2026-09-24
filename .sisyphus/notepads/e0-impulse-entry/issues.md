
## F3b 2026-09-21
- [DEFECT-F3-S10] session/start 失败（疗愈直达路径）无错误提示可见：A1Workspace.tsx error state 仅在 seed_selector(:1063)/guided_chat(:1225)/graph_view(:1611) 渲染，impulse_cards 分支(:1443)不渲染 error。页面不白屏、停在卡片屏可操作，但违反 T7 QA 预期『错误提示可见且回到可操作状态』。T8 E2E 未覆盖此失败路径故漏网。建议修复：在 impulse_cards 分支或全局层加 error banner（一处 <p className='text-cosmos-error'>{error}</p> 级插入，注意 A1Workspace 所有权在 T7）
- verify-telemetry-metrics.mjs 成功输出含字面量『无 NaN』，自动化断言需防字面量误报（f3b-replay 用 /=\s*NaN/ + 断言『无 NaN』存在）
- 导出按钮 data-testid=impulse-export，仅在卡片屏页脚；种子页导出须 keep-telemetry + reload 回卡片屏
