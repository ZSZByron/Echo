---
tags: [governance, moc]
updated: 2026-08-04
---

# Echo UGC 项目治理体系 — 总览

> **定位**: 这 5 张表是项目的 **指导文件**，管理"系统演化过程"而非代码本身。
>
> **使用方式**: 先搭架子，随时填肉。每个文件内部有空位和填写指引。

---

## 五表关系

```
                 产品战略目标
                     |
     ================================

     表2  产品架构蓝图          ← 系统"是什么"？空间维度
         |
         ↓
     表3  知识资产体系          ← 创造和管理"什么内容"？
         |
         ↓
     表4  用户体验体系          ← 用户"怎么用"？
         |
         ↓
     表1  项目控制塔            ← "什么时候"完成？时间维度
         |
         ↓
     表5  工程治理体系          ← "如何稳定"实现？

     ================================
               代码与产品
```

一句话：**架构管空间，知识管内容，UX管路径，控制塔管时间，工程管实现。**

---

## 文件清单

| # | 文件 | 管理维度 | 核心问题 | 更新频率 |
|---|------|---------|---------|---------|
| 1 | [[1_project-control-tower]] | **时间** | 什么时候做什么？现在卡在哪？ | 每周 / 每次开发会话 |
| 2 | [[2_product-architecture]] | **空间** | 系统由什么组成？边界在哪？ | 季度（大变更时） |
| 3 | [[3_knowledge-assets]] | **内容** | 世界知识如何组织、连接、复用？ | 新数据模型确定时 |
| 4 | [[4_ux-flow]] | **交互** | 用户如何完成目标？操作路径？ | 每个新页面/功能时 |
| 5 | [[5_engineering-governance]] | **实现** | 代码如何组织？接口契约？ | 持续演进 |

---

## 使用规则

1. **每次开发会话第一步**: 读表1（控制塔），确认当前聚焦
2. **新增功能前**: 查表2（架构）确认系统边界，查表4（UX）确认用户路径
3. **新增数据模型时**: 更新表3（知识资产）
4. **代码结构变更时**: 更新表5（工程治理）
5. **每周回顾**: 更新表1的系统状态矩阵 + 本周聚焦

---

## 与现有文档的关系

| 现有文档 | 归属体系 | 说明 |
|---------|---------|------|
| `README.md` 开发断点 A-J | → [[1_project-control-tower]] 控制塔 | 断点映射为系统状态 |
| `docs/plans/2026-08-04-platform-architecture.md` | → [[2_product-architecture]] 产品架构 | 已有 1039 行，表2 是其摘要索引 |
| `docs/plans/2026-08-04-trpg-pipeline-mapping.md` | → [[2_product-architecture]] 产品架构 | TRPG 全流程映射 |
| `docs/plans/2026-08-04-trpg-pipeline-alignment.md` | → [[2_product-architecture]] 产品架构 | 缺口分析 |
| `docs/SYSTEM_DESIGN_SPEC_v4.md` | → [[3_knowledge-assets]] 知识资产 + [[5_engineering-governance]] 工程 | 3419行设计规范，按章节归入 |
| `docs/plans/2026-08-04-directory-structure-recommendations.md` | → [[5_engineering-governance]] 工程治理 | 目录结构建议 |
| `docs/plans/2026-08-03-layered-constraint-architecture.md` | → [[3_knowledge-assets]] 知识资产 | 分层约束架构 |
| `.sisyphus/plans/*` | → [[1_project-control-tower]] 控制塔 | 具体实施计划 |
