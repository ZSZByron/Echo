# 🗺️ Echo UGC 文档中心 (MOC)

> **用法**: 用 Obsidian 打开 `docs/` 文件夹作为 Vault。
> 所有文档通过 `[[]]` 双链互联，从本页出发可到达任何文档。

---

## 📌 快速入口

| 文档 | 说明 | 更新频率 |
|------|------|---------|
| [[governance/project-control-tower\|🎯 控制塔]] | 进度管理 · 断点 · Milestone · 本周聚焦 | 每周 |
| [[governance/product-architecture\|🏗️ 产品架构]] | 系统边界 · 依赖关系 · TRPG映射 | 季度 |
| [[governance/knowledge-assets\|🧠 知识资产]] | 实体类型 · Schema · 关系语义 · ID规则 | 新模型时 |
| [[governance/ux-flow\|👥 用户体验]] | 用户旅程 · 页面地图 · 交互规则 | 新页面时 |
| [[governance/engineering-governance\|⚙️ 工程治理]] | 代码结构 · API契约 · 编码规范 | 持续 |
| [[governance/index\|📋 五表总览]] | 五表关系图 · 使用规则 | — |

---

## 📐 设计规范

| 文档 | 版本 | 状态 |
|------|------|------|
| [[SYSTEM_DESIGN_SPEC_v5.1\|系统设计规范 v5.1]] | v5.1（current） | ✅ 最新 |
| [[SYSTEM_DESIGN_SPEC_v5\|系统设计规范 v5]] | v5.0 | 📦 归档 |
| [[SYSTEM_DESIGN_SPEC_v4\|系统设计规范 v4]] | v4.0 | 📦 归档 |
| [[SYSTEM_DESIGN_SPEC_v3\|系统设计规范 v3]] | v3.0 | 📦 归档 |
| [[SYSTEM_DESIGN_SPEC_v2\|系统设计规范 v2]] | v2.0 | 📦 归档 |
| [[SYSTEM_DESIGN_SPEC\|系统设计规范 v1]] | v1.0 | 📦 归档 |

---

## 📋 架构设计文档 (Plans)

| 文档 | 内容 | 关联治理表 |
|------|------|-----------|
| [[plans/2026-08-04-platform-architecture\|平台完整架构]] | 7类用户 · 4端 · 8系统 · Sprint路线 | → [[governance/product-architecture]] |
| [[plans/2026-08-04-trpg-pipeline-alignment\|TRPG全流程对齐]] | 8阶段TRPG × 现状对照 · 4大断层 | → [[governance/product-architecture]] |
| [[plans/2026-08-04-trpg-pipeline-mapping\|TRPG全流程映射]] | TRPG阶段 × 平台系统 × 代码文件 三视图映射 | → [[governance/product-architecture]] |
| [[plans/2026-08-04-directory-structure-recommendations\|目录结构建议]] | services→domains 迁移方案 | → [[governance/engineering-governance]] |
| [[plans/2026-08-03-layered-constraint-architecture\|分层约束架构]] | 6维×6层×权重 · 继承模型 · 实施路线 | → [[governance/knowledge-assets]] |
| [[plans/2026-08-01-ai-story-scene-editor-design\|AI编辑器设计]] | 五图模型 · Phase 1-4 编辑器 | → [[governance/ux-flow]] |
| [[handoff-bidirectional-concept-mapping\|双向概念映射（设计）]] | 概念映射设计思路 | → [[governance/knowledge-assets]] |
| [[handoff-bidirectional-mapping\|双向概念映射（实施）]] | 具体实施映射 | → [[governance/knowledge-assets]] |

---

## 🔗 标签导航

- `#governance` — 治理文档（5张表）
- `#design-spec` — 系统设计规范
- `#plan` — 架构设计方案
- `#handoff` — 交接/设计映射文档
- `#current` — 当前版本（唯一）
- `#archived` — 归档版本

---

## 📖 阅读顺序建议

**新会话第一次读**:
1. [[governance/project-control-tower|🎯 控制塔]] — 看进度在哪
2. [[governance/product-architecture|🏗️ 产品架构]] — 看系统边界

**要改数据模型**:
1. [[governance/knowledge-assets|🧠 知识资产]] — 看 Schema 规则
2. [[SYSTEM_DESIGN_SPEC_v4|设计规范 v4]] §5 领域模型 — 看字段定义
3. [[governance/engineering-governance|⚙️ 工程治理]] — 看命名规范

**要加新页面**:
1. [[governance/ux-flow|👥 用户体验]] — 看用户旅程位置
2. [[governance/engineering-governance|⚙️ 工程治理]] — 看 API 规范

**要排期开发**:
1. [[governance/project-control-tower|🎯 控制塔]] — 看断点依赖
2. [[plans/2026-08-04-platform-architecture|平台架构]] — 看 Sprint 路线
