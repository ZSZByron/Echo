# Draft: A1 访谈体验升级·总基线开工（波次施工计划）

## 来源
用户指令（2026-10-10）：「根据 oc://renderer/SDpcVUdD/session/ses_edc0a1395ffeuR3Lbg3CAYFB9y 最后的计划，开工」。
上一会话（Sisyphus Ultraworker，104 消息，6 小时）产出 9 份文稿（①-⑨），收官件 = 总基线计划。

## Requirements (confirmed)
- 「开工」：按总基线计划（docs/plans/2026-10-10-A1访谈体验升级-总基线计划.md）启动施工
- 施工纪律（项目既有）：单锤单日 / writing-plans 施工单 / decision-log 记台账 / TDD（契约锁定→替换→全量回归）
- 波次一三子任务互不依赖、改动面互斥、串行 1.1→1.2→1.3（同文件纪律）

## 计划核心结构（来自总基线）
- **波次一【止血+快赢】纯后端**：
  - 1.1 P3 序号跨题错配修复（guide_engine options 序列化区；正在丢数据，最急；已归口只等开工）
  - 1.2 50 问文案说人话（story_modules + a1_question_tree；重写18/微调31/保留1；契约锁定→替换→字节 diff 白名单）
  - 1.3 投递一期（规则 6「引回」改「接住-归位-回题」+ ⑨§3 投递话术族 6 式模板变量化；零 schema 变更）
- **波次二【结构大锤】一锤禁拆散**：2.1 三级树+值形态+D23-B+⑦二期+⑨§1/§2 话术+⑤§9 清单型机制 合流（P2 顺路收编）
- **波次三【前端+二期】**：3.1 活地图/label层/开场语前端；3.2 D24 二期按钮（等 E0 数据）

## 拍板池 25 项（全部附推荐）
- 波次一 5 项（拍1-1 至 拍1-5）：示范稿四题采用=是 / 骰子术语分级=是 / severity 移除=是（施工前验证 graphify 不依赖）/ 规则6 改写=是 / 一期先行=是
- 波次二 17 项（拍2-1 至 拍2-17）：全部有推荐（世界本体归位=是 / 剧情对称升格=是 / L3 全量=全量 / 视觉候选=先不加 / D23-B 合流=是 / 分级访问=是 / 支线结构=加 / 三形态=是 / 边界五裁定=是 / 19组转换=确认 / 值schema=是 / 拒绝线=是 / 灵感架=是 / 半填=是 / 全量话术=是 / 清单机制=是 / 清单上限=放宽到12）
- 波次三 3 项：开场语连前端=一并改 / label 层二期=记 / 活地图=是

## Open Questions（待用户回答）
1. 波次一 5 项是否全按推荐拍板？
2. 开工范围：仅波次一出施工计划，还是波次一+二+三全量一个计划（波二 17 项也现在拍）？

## Research Findings
- 上会话已做全部代码实读（story_modules.py / a1_question_tree.py / module_registry.py 269 行 / interviewer 规则6 区 / guide_engine options 序列化区 / 前端 A1Workspace L647）
- 测试基线：后端 pytest 1627 passed / cov 84.82%（D24 收锤后）；前端 vitest 310 / tsc 0
- .sisyphus/plans/ 先例：direction-a-option-forward.md（8 锤完成）、d23-semantic-merge-and-hierarchy.md（三提交完成）——执行通道已验证

## Scope Boundaries
- INCLUDE: 按总基线三波次路线生成可执行施工计划（.sisyphus/plans/*.md），含 TDD 任务、QA 场景、白名单、红线
- EXCLUDE: 不改业务代码（我是规划者）；不推翻既有治理（D19-D24 裁决全部顺延）
