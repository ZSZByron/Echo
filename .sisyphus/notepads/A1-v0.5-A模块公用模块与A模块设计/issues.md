# Issues - A1-v0.5 A模块公用模块与A模块设计

## Known Issues

### 断点A-H修复风险
**Status**: Pending  
**Tasks**: T-B/T-A/T-C/T-F (批次1) + T-G/T-D/T-E/T-H (批次2)  
**Risk Level**: HIGH  
**Mitigation**: 授权关卡，用户明确授权后才执行

### 依赖链复杂性
**Status**: Pending  
**Chain**: 词典→B→A→C→F；F→G；G→E；{D,E}并行；H独立  
**Risk Level**: MEDIUM  
**Mitigation**: 严格按批次顺序执行，批次内按Wave顺序

### Enum封闭性约束
**Status**: Pending  
**Constraint**: 阶段码/枚举值不允许添加或修改  
**Risk Level**: MEDIUM  
**Mitigation**: TDD测试覆盖，CI检查

### 并发发号原子性
**Status**: Pending  
**Task**: T3 四层编码发号器  
**Risk Level**: MEDIUM  
**Mitigation**: SQL事务 + 唯一索引兜底重试

## Blockers

### Current Blockers
None

### Potential Blockers
- 联网优化检查未完成（正在等待librarian研究结果）

## Workarounds

### SQLite并发限制
**Workaround**: 单写者事务 + 唯一索引重试  
**Impact**: 性能可能略降，但保证数据一致性

### 前端组件库兼容性
**Workaround**: 新主题只影响A模块页面，旧页面不修改  
**Impact**: 渐进式升级，降低风险

## Resolutions

---

*This file is append-only - add new issues/resolutions at the end*
## 预先存在的前端测试失败（非批次1引入）
- src/hooks/__tests__/useTypewriter.test.ts: 6/7失败（旧CRT代码，最后提交b9b927d=7/29）
- tests/e2e/graph.spec.ts: 被vitest误收集的Playwright用例（配置问题）
- 处置: 不在批次1范围，待后续修复
