## Task T-B: 断点B修复 - Output模型结构化字段 (2026-08-21)

**成功实现:**
- ✅ TDD方法论应用: 先写失败测试(43个测试)，再实现功能，确保测试覆盖率
- ✅ 5个Output模型(Law/Act/Nar/Wst/Soc)增加21个结构化字段，每个字段包含validator
- ✅ 字段全部Optional+默认None，实现完全向后兼容
- ✅ 保留所有自由文本字段(rules/actions/style/tone/effects/relations等)
- ✅ 使用tag_dictionary.get_enum_values()进行枚举校验，非法值抛ValueError含合法值列表
- ✅ RedOutput保持不变(断点B清单中无新增)

**技术细节:**
- 字段类型: str | None = None`n- Validator逻辑: 仅当值非None时调用get_enum_values(dim, tag)校验，None通过
- 错误消息格式: Invalid {field} '{value}'. Valid values: {enum_list}`n- 测试结果: 518个测试全部通过(43个新增测试 + 475个原有测试)

**验证场景:**
- QA场景1: LawOutput(rules=['x'], world_structure='FLOATING_ISLANDS') ✅ 通过
- QA场景2: 非法枚举'INVALID_STRUCTURE'被拒绝并显示所有合法值 ✅ 通过

**关键决策:**
- Validator统一使用get_enum_values接口(不直接解析YAML)，确保与T4词典任务解耦
- 字段逐字按断点B清单添加，无额外字段，避免范围蔓延
- 测试用例修正: 修正了2个测试用例中错误的期望(loose validation → strict validation)

**风险缓解:**
- 并行任务T-A(词典YAML合并)正在同时进行，validator接口稳定性至关重要
- 通过get_enum_values()抽象层隔离YAML结构变更，避免直接依赖

T-B断点修复学习记录

## TDD实践验证
- 严格按照RED-GREEN-REFACTOR流程执行
- RED阶段: 32个测试正确失败，证明测试确实在检查新功能
- GREEN阶段: 实现最小化代码，仅添加字段和验证器
- 验证策略对比: 任务文档提到'宽松策略'，但实际需要枚举校验
- 解决方案: 按计划规格a-module-fullstack.md L796实施validator引用T4

## 字段设计模式
- 所有字段使用 str | None = None 确保向后兼容
- 使用Pydantic field_validator进行运行时枚举校验
- 验证器引用tag_dictionary.get_enum_values()获取有效值列表
- 错误消息包含所有有效枚举值，便于调试

## 集成验证发现
- DimensionGenerator相关测试无需修改，说明新字段确实是可选的
- 现有代码创建Output模型时不传新字段，完全兼容
- 518个测试全部通过，超过基线475，新增43个专项测试

## QA场景实用性
- python -c 单行测试非常适合快速验证核心功能
- 比完整测试套件快10倍以上，适合开发过程快速反馈


- [T-A] RealSemanticCompiler实现要点: compile是同步契约但chat_json是async → asyncio.run桥接(FakeProvider里chat_json也要async def); L2规则表启动时即对照get_enum_values过滤(铁律前置); 同(dim,tag)多关键词命中只写一次; FieldWrite.field格式为'DIM.tag'

## T-C 断点C: 约束应用逻辑树 (2026-08-21)
- InjectionRule 6字段逐字 (source_field/target_prompt_layer/target_node_field/target_edge_type/transform/priority)，dimension/layer 为派生字段
- 加载器强校验: 36条不重不漏 + 维度/层完备 + 节点字段合法性(对照 GraphNode/GraphEdge model_fields) + prompt层合法(8层) + 层内priority唯一
- 层级图示例 Geography.vertical_layer 非真实字段→用 description，语义放 transform；RULE_* 为语义边标签，T-F 落为 CROSS 边
- YAML 惯例: 层名作根键（同 weight_matrix.yaml）
- 基线529 → 540 passed，无回归
## T-F constraint_topology

- **Pattern**: Pydantic BaseModel in-place mutation (no deep copy). GraphNode/GraphEdge have no metadata field; source_stage and RULE_* labels go in description/visual_description.
- **Enum gotcha**: DimensionResultSet field validators reject non-dict-enum values. Use get_enum_values(dim, tag) to discover legal values before writing tests.
- **ApplicationTreeLoader**: Lazy singleton via module-level _tree_loader. First call reads YAML, subsequent calls are cached. Safe for import-time usage.
- **Edge type mapping**: A structured field can map to multiple RULE_* labels across layers (e.g. LAW.world_structure -> RULE_SHAPES_GEO world, RULE_SHAPES_GEO location, RULE_SHAPES_MOBILITY subject, RULE_SHAPES_PHYSICS material). For A1 skeleton we pick the first occurrence (world layer).
- **PowerShell workdir**: Set-Location in the same command string as the test invocation is needed. The workdir parameter appears unreliable for Set-Location persistence across calls.
- **CST node level**: Set to 0 (above background level 1) to distinguish constraint nodes from scene hierarchy nodes.
