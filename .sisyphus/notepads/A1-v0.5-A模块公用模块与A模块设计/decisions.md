# Decisions - A1-v0.5 A模块公用模块与A模块设计

## Architecture Decisions

### 1. 模块分层架构
**Decision**: 公用模块作为独立层先行交付  
**Rationale**: 被四个工作台共同依赖，先行交付避免重复开发  
**Impact**: 第一篇T1-T8需要优先完成，其他工作台依赖此底座

### 2. 图谱与文件关系
**Decision**: 图谱=事实源，文件=单向序列化导出  
**Rationale**: 保持数据一致性，避免双向同步复杂度  
**Impact**: 定稿后 `export_file_from_graph(graph) -> StructuredFile` 单向导出；反向写文件不回写图谱

### 3. 工作台开发原则
**Decision**: 7生成器"独立开发、独立可用、按需组合"  
**Rationale**: 允许渐进式交付，用户可以只用特定生成器  
**Impact**: 每个工作台页面只是预编排串联，生成器核心保持独立

### 4. 版本管理策略
**Decision**: 四层编码永不覆盖只追加  
**Rationale**: 保留完整历史，支持回溯和对比  
**Impact**: IP序号=A1会话启动即分配，废弃归档不回收；版本号=同实例当前+1

### 5. Stale机制设计
**Decision**: 只标记不删除，不阻断流程  
**Rationale**: 保留用户选择权，避免流程中断  
**Impact**: stale→提示变更集，用户坚持继续→留痕（used_stale=true）

## Technical Decisions

### 1. 数据库选择
**Decision**: SQLite with aiosqlite  
**Rationale**: 轻量级，适合单机部署，支持异步  
**Impact**: 所有Store层基于SQLite构建

### 2. 前端主题策略
**Decision**: 新页面"星空平行宇宙"主题，旧CRT页面不修改  
**Rationale**: 渐进式升级，避免影响现有功能  
**Impact**: 只修改A模块相关页面，其他终端页面保持CRT风格

### 3. 三级匹配架构
**Decision**: 种子库级→词典规则级→LLM级  
**Rationale**: 前两级零LLM成本，降低API调用  
**Impact**: 语义编译优先匹配规则，最后才用LLM

### 4. 测试策略
**Decision**: TDD（写失败测试→实现→PASS）  
**Rationale**: 保证测试覆盖，避免过度工程  
**Impact**: 每个Task都包含测试先行步骤

## Implementation Decisions

### 1. 批次划分
**Decision**: 分3批执行，本次仅执行批次1  
**Rationale**: 避免单次工作量过大，集中完成依赖链  
**Impact**: 批次2/3任务跳过，后续执行

### 2. 并行策略
**Decision**: Wave 1并行 + Wave 2/3串行  
**Rationale**: 独立任务并行提速，依赖任务串行保正确  
**Impact**: T2/T5/T6/T7并行，T1→T3→T4串行

### 3. 授权关卡
**Decision**: 断点修复前必须用户授权  
**Rationale**: 涉及核心约束系统，需要明确同意  
**Impact**: 每个断点任务包含授权步骤

## Pending Decisions

---

*This file is append-only - add new decisions at the end*
## 联网建议接口影响审核（2026-08-19，基于代码实证）

### 证据
- provider.py: 仅 chat()/chat_json() 抽象方法，无词表掩码能力
- database.py/graph_store.py: aiosqlite 惰性连接，无任何 PRAGMA 设置
- dimension.py: 170行纯模型，无 v1/v2 装饰器混用
- frontend/src/api/client.ts: 已存在35行，签名 fetchWithTimeout(url, options): Promise<Response>
- apiClient 被 assets.ts(~10处)/graph.ts(~8处)/useAction.ts(~3处) 共20+处调用
- 前端: React 19.2.7 / Tailwind 4 / Vitest+Testing Library 已就绪；无 @tanstack/query

### 裁决
1. WAL模式 → ✅采纳（融入T5，纯增量无接口变更）
2. Pydantic v2规范 → ✅采纳（新代码，dimension.py无冲突）
3. React19 Compiler/不用手写memo → ✅采纳（T7）
4. frozen dataclass编码对象 → ✅采纳（T3内部表示，不改编码规则）
5. LLM约束解码 → ❌拒绝（需改LLMProvider ABC+全部Provider，与T-A规格chat_json冲突）
6. QuaQue位串版本 → ❌拒绝（改存储模型，与T3/T5冲突）
7. TanStack Query → ⚠️缓议（需加依赖，计划未含；批次1用普通hook）
8. T2 client.ts → ⚠️修正执行方式：禁止覆盖，新增fetchJson<T>并行存在，identity.ts用新API
