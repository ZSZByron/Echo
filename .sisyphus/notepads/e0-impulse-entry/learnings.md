
## T1 D9 (2026-09-20)
- tsc 基线 16 错在工作树中已为零（先于本任务）——后续任务不要假设仍需修类型。
- useTypewriter：effect 内同步 tick() → 挂载后首字符已显示；fake timers 下 RTL waitFor 会卡死（内部轮询定时器不走 fake clock），用 act(advanceTimersByTime)+同步断言替代。
- vitest 与 playwright 并存：vitest.config.ts 需 exclude tests/e2e/**（用 configDefaults.exclude 展开）。
- .sisyphus/evidence 被 gitignore——证据只落盘不提交，属预期。

## T2 (2026-09-20)
- 违禁词 grep 会命中注释：初稿注释含'擦边'被扫出，注释措辞也要避开违禁词表
- vitest 基线 191→213（含他人并行新增），本任务新增 4 用例；单文件验证用 npx vitest run <path>
- .sisyphus/ 整目录未被 gitignore（boulder.json/notepads 出现在 status），仅 evidence 被忽略——提交时须显式只 add 代码文件

## T5 (ImpulseCards) learnings
- A1Workspace.tsx 未导出 Seed 接口——seedGrouping.ts 的结构副本即组件消费源，直接 import type 即可，无需改 T4 文件
- 令牌色系：stardust(主高亮)/nebula(次高亮)/void(弱化文字)/space-950(按钮文字)；glass-card + starry-gradient 是既有卡片风格基线
- 主/次选中区分：primary 实线描边 ring-1 + "主"角标，secondary 虚线描边 + "次"角标
- 事件守卫用 useRef(StrictMode 双挂载)；测试不用 fake timers/waitFor，fireEvent 后同步断言即可
- 现有 Seed 数据里 genre 为中文；测试 fixture 只需满足 Seed 结构，1 个即够（组件不消费 seeds 内容，仅 props 透传）

## T8 (2026-09-20, commit d8d0c7c)
- E2E 策略：全 A1 端点 page.route mock（seeds/session-start/chat/upload/file hydration），零后端/零 LLM 依赖；graph.spec 惯例沿用。
- 关键坑：**必须 mock /api/a1/file/****——fileId 水合 404 触发 handleStaleSession 回退种子页（后端在跑时才暴露；后端不在时 502 被静默 catch）。
- playwright 每次运行清空 test-results/（导出落盘文件会被后续 run 抹掉，证据要 Copy-Item 出来）。
- ESM 下 spec 无 __dirname，用 path.resolve(process.cwd(),...)。
- 导出按钮只在卡片屏；回卡片屏 = 清 localStorage（先暂存 a1_telemetry_v1 再回写）+ reload（impulse_cards 不持久化）。
- graph.spec 存量基线：chromium 23 failed / 3 passed（与后端启停无关，strict-mode violation 等，先于 T8）。

## F3a (scenarios 1-6, browser replay) 2026-09-21
- 独立 node+playwright 脚本（frontend/scripts/f3a-replay.mjs）替代 playwright test 跑 QA 重放，6 场景全 PASS，总耗时 ~30s（远低于 10min 预算）
- 上传链不能走 filechooser 事件（UploadToolbar 用隐藏 input[type=file]，点击按钮不触发 filechooser）——直接 setInputFiles 到 locator('input[type="file"]')
- 继续→访谈的断言锚点 = input[placeholder="Type your message..."]（first_question 文本在上传链不一定渲染）
- 效率关键：每场景独立 browser context + Promise.race 90s 超时 + 证据即时落盘

## 收官（2026-09-20，Orchestrator）
- 计划 12/12 闭环（T1-T8 + F1-F4 全勾）；9 提交链 fd6f687..0fb6178，后端全程零改动。
- FINAL 波实效：F3 抓到 S10 真实缺陷（impulse_cards 分支无 error banner）——T8 E2E 未覆盖的失败路径由手动 QA 兜住，修复 0fb6178 行级落地后复验翻转。多通道验证不是冗余。
- 基础设施教训：>10 分钟的浏览器重放类同步任务必撞轮询上限（T8 首跑 30min 超时、F3 两次中断）——拆分为 ≤10min 子任务 + 独立 node 脚本（Promise.race 超时保护 + 证据增量落盘）是稳定形态（f3a/f3b-replay.mjs 可复用）。
- E1 交接备忘：①首答埋点移至响应成功后 ②Seed 类型收敛共享导出 ③file 水合 404 会踢回种子页（E2E mock 必须覆盖 /api/a1/file/**）④graph.spec 存量失败基线 23F/3P（chromium，与本计划无关）⑤8+1 文案待产品方终审（task-2-copy-review-checklist.md）。
