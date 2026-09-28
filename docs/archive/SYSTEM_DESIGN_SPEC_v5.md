# Echo UGC — 系统设计规范 v5.0 (System Design Specification)

> **文档定位**: A模块公用底座接口契约 + A1工作台API规格 + 断点修复模块接口定义
> **版本**: v5.0 — 从A1-v0.5实施计划提取完整模块接口（批次1执行，批次2/3附录参考）
> **日期**: 2026-08-19
> **来源**: `.sisyphus/plans/A1-v0.5-A模块公用模块与A模块设计.md`
> **与v4关系**: v4为通用架构规范，v5聚焦A模块实施接口，增量内容为公用底座模块+断点修复接口

---

## 更新日志

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v5.0 | 2026-08-19 | 新增A模块公用底座完整接口(T1-T8) + A1工作台API契约(T9) + 断点修复模块接口(T-DICT/T-B/T-A/T-C/T-F)，批次1执行批次2/3参考 |
| v4.0 | 2026-08-03 | 新增 §18 6维约束体系接口注册区（枚举定义/权重矩阵/数据模型/接口签名/API端点/数据流图/命名碰撞消解） |
| v3.0 | 2026-08-02 | 新增 §17 分阶段实施接口注册区；同步 §5 模型签名与实际代码一致（修正可变默认值、裸 dict 类型、新增 StoryEdge 类型化模型） |

---

## 目录

1. [批次划分说明](#1-批次划分说明)
2. [第一篇 公用模块接口](#2-第一篇-公用模块接口)
   - T1: 身份层接口
   - T2: 前端API客户端基础设施
   - T3: 四层编码发号器
   - T4: 图谱清单API + stale标记机制
   - T5: Store扩展
   - T6: 语义编译契约
   - T7: 前端公用组件库
   - T8: 公用模块集成验收
3. [第二篇 A1工作台API契约表](#3-第二篇-a1工作台api契约表)
4. [第三篇 断点修复模块接口](#4-第三篇-断点修复模块接口)
   - T-DICT: 标签+枚举词典
   - T-B: Output模型结构化字段
   - T-A: 语义→标签→枚举编译器
   - T-C: 约束应用逻辑树
   - T-F: 约束→拓扑节点/边创建
   - 批次2/3附录: T-G/T-D/T-E/T-H
5. [附录](#5-附录)
   - 依赖链图
   - 三条铁律
   - 授权关卡协议摘要

---

## 1. 批次划分说明

### 批次1（本次执行）
- 第一篇公用模块 T1-T8
- 第二篇 T9 A1工作台
- 第三篇 T-DICT/T-B/T-A/T-C/T-F
- T13a批次终验

### 批次2（后续）
- T10 A2工作台
- T-G/T-D/T-E/T-H（T-G依赖批次1的T-F）

### 批次3（后续）
- T11 A3工作台
- T12 GM大厅
- T13b全链路验收

---

## 2. 第一篇 公用模块接口

### T1: 身份层接口（user_id + UserTier预留）

**文件路径**:
- `backend/app/domains/identity/__init__.py`
- `backend/app/domains/identity/key_manager.py`
- `backend/app/domains/identity/tier.py`
- `backend/app/api/identity_routes.py`

**核心签名**:
```python
class UserTier(str, Enum):
    FREE = "FREE"
    VIP = "VIP"
    SVIP = "SVIP"
    
    @classmethod
    def default(cls) -> "UserTier":
        return cls.FREE

def register(store: UserStore) -> IdentityInfo:
    user_id = f"u_{uuid4().hex[:12]}"
    store.save(user_id, tier=UserTier.default().value)
    return IdentityInfo(user_id=user_id, tier="FREE")
```

**参数**:
- `store: UserStore` - 用户存储实例

**返回值**:
- `IdentityInfo`:
  - `user_id: str` - 格式 `u_{uuid4().hex[:12]}`
  - `tier: str` - 固定返回 `"FREE"`

**错误码**:
- 无

**枚举说明**:
- `UserTier`为封闭枚举，不允许添加或修改
- MVP阶段无差异，仅预留扩展点

**API契约**:
```
POST /api/identity/register
请求: {}
响应: {user_id, tier:"FREE"}
```

---

### T2: 前端API客户端基础设施

**文件路径**:
- `frontend/src/api/client.ts`
- `frontend/src/api/identity.ts`

**核心签名**:
```typescript
export async function fetchWithTimeout<T>(
  url: string,
  init?: RequestInit & {timeoutMs?: number}
): Promise<T>

// 非2xx时抛 ApiError{status, body}；409 时 body 含 missing_sections

export class ApiError extends Error {
  status: number
  body: any
}
```

**参数**:
- `url: string` - 请求URL
- `init: RequestInit & {timeoutMs?: number}` - 请求配置（可选超时毫秒数）

**返回值**:
- `Promise<T>` - 解析后的JSON响应

**错误处理**:
- 非2xx状态码抛出`ApiError`
- 409冲突时`body`包含`missing_sections`字段

**增量模式说明**:
- 保留现有`client.ts`，新增`fetchJson<T>`辅助函数
- `identity.ts`使用新API，其他现有调用点不变

**测试要求**:
- Vitest mock fetch断言超时与409Error.status

---

### T3: 四层编码发号器 GraphCodeIssuer

**文件路径**:
- `backend/app/domains/creation/shared/graph_code_issuer.py`

**编码规则（逐字，不允许偏离）**:
```
格式: IP{序号}-{阶段路径}-v{版本}
示例: IP0142-M2-S1-v2

阶段码封闭枚举: W/M/S/TD/TC/R/G（不允许添加或修改）
- W: Working（工作阶段）
- M: Module（主模组）
- S: Secondary（次级模组）
- TD: Template Dice（骰子模板）
- TC: Template Character（角色模板）
- R: Report（报告）
- G: Graph（图谱）

IP序号: A1会话启动即分配，废弃归档不回收
实例号: 同范围最大+1（S在其父M内递增，其余IP内递增）
版本号: 同实例当前+1，永不覆盖只追加
```

**与 v4 CreationLayer 的区分（消歧，必读）**:

阶段码与 v4 规范 §18 定义的 `CreationLayer` 是**两套正交的封闭枚举，互不替代、不可混用**：

| | v4 CreationLayer（§18） | v5 阶段码 |
|---|---|---|
| 枚举值 | world / region / scene / campaign / npc / asset | W / M / S / TD / TC / R / G |
| 用途 | 6生成维度，驱动权重矩阵与约束分层 | 四层编码的阶段路径，驱动图谱工件发号 |
| 所在系统 | 6维约束体系（dimension.py） | GraphCodeIssuer（graph_code_issuer.py） |

注意：阶段码 W 表示 Working（工作阶段工件），**不等于** CreationLayer 的 world；两者无映射关系。下游计划生成与实现不得将二者混淆或建立转换表。

**核心签名**:
```python
class GraphCodeIssuer:
    def new_ip(self, user_id: str) -> int:
        """分配新IP序号，返回分配的序号"""
        
    def next(
        self,
        user_id: str,
        ip: int,
        stage: str,
        parent_m: Optional[int] = None
    ) -> str:
        """生成下一个编码，返回完整编码字符串"""
```

**原子性保证**:
- Store层原子递增（单写者事务）
- `(user_id, code)` 唯一约束
- 并发50线程发号全部唯一

**编码与主键关系**:
- 编码=检索显示层
- 主键=uuid
- IP名只做display_name不进编码

**测试用例编码序列**:
```python
iss.new_ip("u1") == 1
iss.next("u1", ip=1, stage="W") == "IP0001-W1-v1"
iss.next("u1", ip=1, stage="W") == "IP0001-W1-v2"  # 版本追加
iss.next("u1", ip=1, stage="M") == "IP0001-M1-v1"  # M在IP内递增
iss.next("u1", ip=1, stage="S", parent_m=1) == "IP0001-M1-S1-v1"
iss.next("u1", ip=1, stage="S", parent_m=1) == "IP0001-M1-S2-v1"
```

---

### T4: 图谱清单API + stale标记机制

**文件路径**:
- `backend/app/domains/creation/shared/stale_marker.py`
- `backend/app/api/graph_routes.py`（追加GET /api/graphs端点）

**stale规则（横切，逐字）**:
```
触发: 上游重新定稿（如A1产出W1-v2）→ 自动标记所有 parent_graph_code 指向旧版本的下游图谱 stale

标记: 只标记不删除，附变更集（diff摘要）

消费: 消费上游前检查
  - stale→提示变更集
  - 不阻断不删除
  - 用户坚持继续→留痕（used_stale=true 记录）
```

**核心签名**:
```python
def mark_downstream_stale(
  store,
  old_code: str,
  change_set: ChangeSet
) -> int:
    """遍历 parent_graph_code=old_code 的下游，置 status='stale' 并挂 change_set。返回标记数。"""
```

**API契约**:
```
GET /api/graphs?user_id={user_id}

响应:
{
  ips: [
    {
      ip_code: str,
      display_name: str,
      artifacts: [
        {
          graph_id: str,
          graph_code: str,
          stage: str,
          instance_no: int,
          version: int,
          status: "finalized" | "stale",
          created_at: str,
          parent_graph_code: str
        }
      ]
    }
  ]
}

说明:
- artifacts按created_at倒序
- ips分组按IP序号聚合
```

---

### T5: Store扩展（图谱=事实源，文件单向导出）

**文件路径**:
- `backend/app/state/structured_file_store.py`
- `backend/app/state/user_store.py`
- `backend/app/state/graph_store.py`（追加字段）

**新增字段**:
```python
# graph_store.py 新增字段
status: str  # "draft" | "finalized" | "stale"
parent_graph_code: Optional[str]
change_set: Optional[ChangeSet]

# structured_file_store.py
class StructuredFile:
    file_id: str
    graph_code: str  # 与图谱版本同码
    type: Literal["file", "graph"]  # 类型字段区分
    content: dict
    created_at: str
```

**核心断言**:
```python
def export_file_from_graph(graph: KnowledgeGraph) -> StructuredFile:
    """定稿后单向导出，反向写文件不回写图谱（重新定稿才重建）"""
```

**数据流向**:
```
图谱（事实源） → export_file_from_graph → StructuredFile（单向序列化）
文件修改 → 不回写图谱 → 重新定稿 → 新版本图谱
```

---

### T6: 语义编译契约（断点A接口，实现在第三篇T-A）

**文件路径**:
- `backend/app/domains/creation/shared/semantic_compiler.py`

**Protocol定义**:
```python
class SemanticCompiler(Protocol):
    def compile(
        self,
        session_id: str,
        text: str
    ) -> CompileResult:
        """语义编译接口"""
```

**CompileResult两种形态**:
```python
class CompileResult(TypedDict):
    # 形态1: 常规语句→直接写入结构化文件
    writes: List[Dict[str, Any]]
    
    # 形态2: 创新语句→二选一确认卡
    classification_proposal: ClassificationProposal

class ClassificationProposal(TypedDict):
    suggestions: List[Dict[str, Any]]
    # 用户确认前不落盘
```

**三级匹配说明**:
```
第一级: 种子库级（零LLM成本）
  - 预设种子模板匹配
  - 精确字符串匹配

第二级: 词典规则级（零LLM成本）
  - 标签词典匹配
  - 枚举值映射

第三级: LLM级（调用LLM）
  - 兜底分类
  - 创新语句提案
```

**测试要求**:
- 使用FakeCompiler（确定性）
- 真实词典+LLM实现在第三篇T-B完成后替换注入

---

### T7: 前端公用组件库

**文件路径**:
- `frontend/src/components/guided/GuidedChat.tsx`
- `frontend/src/components/guided/QuestionHint.tsx`
- `frontend/src/components/structured/StructuredFilePanel.tsx`
- `frontend/src/components/structured/DimensionProgress.tsx`
- `frontend/src/components/structured/DiffHighlight.tsx`
- `frontend/src/components/graph/GraphSelector.tsx`
- `frontend/src/components/poster/PosterBoard.tsx`
- `frontend/src/components/IdentityGate.tsx`
- `frontend/src/components/TopNav.tsx`

**组件清单与Props职责**:

| 组件 | Props职责 | 核心功能 |
|------|-----------|----------|
| GuidedChat | `session_id, onMessage, onFinalize` | 引导对话输入，LLM措辞/追问 |
| QuestionHint | `question, hints` | 问题提示浮层 |
| StructuredFilePanel | `file, diff, onEdit` | 实时diff渲染，显示结构化字段 |
| DimensionProgress | `dimensions` | 10板块完成度进度条 |
| DiffHighlight | `before, after` | 差异高亮显示 |
| GraphSelector | `user_id, onSelect, default_latest` | 显式选上游：默认最新+stale徽章+变更集提示 |
| PosterBoard | `panels, ai_image_prompt` | 展板骨架：全屏氛围图+渐变蒙版+设定浮层 |
| IdentityGate | (无props，从LocalStorage读取) | LocalStorage无user_id→调register→显示ID+FREE徽章 |
| TopNav | `current_step` | A1→A2→A3→大厅 流程指示 |

**GraphSelector stale徽章交互**:
```
1. stale徽章可见
2. 点击弹变更集
3. 二选一确认卡出现
  - 留痕使用（used_stale=true）
  - 重新生成
```

**测试要求**:
- Vitest+Testing Library
- GraphSelector stale徽章渲染
- DimensionProgress 10格测试
- IdentityGate register调用测试

---

### T8: 公用模块集成验收

**验收步骤**:
```bash
# 1. 身份注册
POST /api/identity/register → 200 {user_id, tier:"FREE"}

# 2. 编码递增验证
连续GET /api/graphs?user_id={user_id}
- 造3版本数据
- 编码按 W1-v1/v2、M1/S1 递增
- 倒序排列

# 3. stale机制验证
上游发v2 → 下游status=stale+change_set
GET /api/graphs 仍返回stale项（未删除）

# 4. GraphSelector组件验证
stale徽章可见、点击弹变更集、二选一确认卡出现
```

**证据路径**:
`.sisyphus/evidence/v0.5-shared/`

---

## 3. 第二篇 A1工作台API契约表

### T9: A1工作台 /a1（生成器①：三态流）

**文件路径**:
- `backend/app/domains/creation/seed/preset_loader.py`
- `backend/app/domains/creation/seed/seed_generator.py`
- `backend/app/domains/creation/a1/a1_question_tree.py`
- `backend/app/domains/creation/a1/guide_engine.py`
- `backend/app/domains/creation/a1/innovation_capture.py`
- `backend/app/domains/creation/a1/ip_poster.py`
- `backend/app/api/a1_routes.py`
- `frontend/src/pages/a1/A1Workspace.tsx`
- `frontend/src/pages/a1/IPPoster.tsx`

**API契约表（A1）**:

| 端点 | 方法 | 请求→响应 | 错误 |
|------|------|----------|------|
| `/api/a1/seeds` | GET | →`{seeds:[{id,name,genre,description,dimension_defaults}]}` | — |
| `/api/a1/session/start` | POST | `{user_id, seed_id\|custom_idea}`→`{session_id,file_id,ip_code,first_question,file}`（IP序号此时分配） | 400 二选一缺失 |
| `/api/a1/chat` | POST | `{session_id,message}`→`{reply,next_question,file_diff,progress,phase,classification_proposal?}` | — |
| `/api/a1/file/{id}` | GET | →StructuredFile（含status: draft/finalized, graph_id） | 404 |
| `/api/a1/file/{id}/finalize` | POST | →`{graph_id,graph_code,warnings}`（文件→图谱一次性转换：结构化条目→图谱节点+基础边；**约束建边由第三篇T-F实现后注入此挂点**；触发下游stale标记） | **409**+`{missing_sections:[...]}` 10板块未齐 |
| `/api/a1/file/{id}/graph` | GET | →KnowledgeGraph（须已定稿） | 409 pending_finalize |
| `/api/a1/file/{id}/poster` | GET | →`{panels,ai_image_prompt,ai_image_status}` | **409** 未定稿 |

**TDD要点**:
- finalize缺板块→409+缺失清单
- 定稿后文件再改须重新定稿
- 重新定稿产出W1-v2且旧版保留、下游自动stale

**A1Workspace三态流**:
```
态①: SeedSelector
  - 8种子卡片/自定义输入

态②: GuidedChat + StructuredFilePanel实时diff + DimensionProgress + 定稿按钮
  - 未齐不点亮

态③: 内嵌IP展板
  - 会话恢复按status路由
```

**IPPoster修改分支**:
```
/a1/poster: 纯展板 + 【继续修改】
  → 图谱条目浮层
  → 【去修改】回工作台定位板块
  → 重新定稿
  → W1-v2旧版保留
```

---

## 4. 第三篇 断点修复模块接口

### T-DICT: 标签+枚举词典（断点A数据层）

**文件路径**:
- `backend/app/config/tag_dictionary.yaml`

**6维标签组（全部合法标签逐字来自层级图L105-130）**:
```yaml
LAW:
  world_structure: [...]  # 世界结构标签
  gravity: [...]         # 重力规则标签
  conservation: [...]    # 守恒定律标签
  divine_intervention: [...]  # 神王干涉标签
  afterlife: [...]       # 来世设定标签

ACT:
  dice_mode: [...]       # 骰子模式标签
  check_direction: [...] # 检定方向标签
  cost_function: [...]   # 消耗函数标签
  core_action: [...]     # 核心行动标签

NAR:
  era_stage: [...]       # 时代阶段标签
  time_mode: [...]       # 时间模式标签
  trajectory: [...]      # 叙事轨迹标签
  success_granularity: [...]  # 成功粒度标签

WST:
  cost_type: [...]       # 消耗类型标签
  feedback_loop: [...]  # 反馈循环标签
  climate_zone: [...]    # 气候带标签
  power_saturation: [...]  # 力量饱和标签

SOC:
  political_type: [...]  # 政治类型标签
  access_topology: [...] # 接入拓扑标签
  threshold: [...]      # 阈值标签
  economy_type: [...]   # 经济类型标签

# A2新增标签组
LOC:
  loc_topology: [...]    # 地点拓扑标签
  loc_connectivity: [...]  # 地点连通性标签

STY:
  style_keywords: [...]  # 风格关键词标签
  architecture_style: [...]  # 建筑风格标签
```

**枚举值规则**:
- 逐字照抄，不允许添加或修改
- TDD: YAML加载校验（6维齐全+LOC/STY）

---

### T-B: 断点B修复：Output模型结构化字段

**文件路径**:
- `backend/app/models/dimension.py`

**修改内容**:
- 6个Output按断点B清单加结构化字段
- 全部Optional+默认None向后兼容
- 自由文本字段保留

**字段表（来自L795）**:
```python
# 示例（完整字段表见源计划L795）
class LawOutput(BaseModel):
    # 原有自由文本字段保留
    
    # 新增结构化字段
    world_structure: Optional[str] = None
    gravity: Optional[str] = None
    conservation: Optional[str] = None
    divine_intervention: Optional[str] = None
    afterlife: Optional[str] = None
    
    # ...其他维度类似
```

**调用方适配**:
- 适配现有调用点
- 旧测试迁移

---

### T-A: 断点A修复：语义→标签→枚举编译器

**文件路径**:
- `backend/app/domains/creation/a1/semantic_compiler.py`

**三级匹配实现**:
```python
class SemanticCompilerImpl:
    def compile(self, session_id: str, text: str) -> CompileResult:
        # 第一级: 种子库级匹配（零LLM成本）
        if seed_match := self._match_seed_library(text):
            return CompileResult(writes=[seed_match])
        
        # 第二级: 词典规则级匹配（零LLM成本）
        if rule_match := self._match_dictionary(text):
            return CompileResult(writes=[rule_match])
        
        # 第三级: LLM级兜底
        llm_result = self._llm_classify(text)
        if llm_result.is_confident:
            return CompileResult(writes=[llm_result.to_dict()])
        else:
            return CompileResult(
                classification_proposal=llm_result.to_proposal()
            )
```

**输出格式**:
```python
class CompiledTag(TypedDict):
    tag: str           # 标签名
    enum_value: str    # 枚举值
    confidence: float  # 置信度
    source: Literal["seed", "dictionary", "llm"]  # 来源
```

**完成后操作**:
- 替换第一篇T6的FakeCompiler注入
- LLM单测用FakeProvider

---

### T-C: 断点C修复：约束应用逻辑树

**文件路径**:
- `backend/app/domains/creation/constraint/application_tree.py`
- `backend/app/domains/creation/constraint/application_tree.yaml`

**字段定义（逐字来自层级图断点C节）**:
```python
class ApplicationTreeNode(BaseModel):
    source_field: str          # 源字段
    target_prompt_layer: str   # 目标提示词层
    target_node_field: str     # 目标节点字段
    target_edge_type: Optional[str]  # 目标边类型
    transform: Optional[str]  # 转换规则
    priority: int             # 优先级
```

**映射配置（6维×6层=36条）**:
```yaml
# application_tree.yaml 示例
- source_field: "LAW.world_structure"
  target_prompt_layer: "World"
  target_node_field: "physics"
  target_edge_type: "applies_to"
  transform: null
  priority: 1

# ... 完整36条映射见源计划
```

---

### T-F: 断点F修复：约束→拓扑节点/边创建

**文件路径**:
- `backend/app/domains/creation/graph/constraint_topology.py`

**核心签名**:
```python
def apply_constraints(
    graph: KnowledgeGraph,
    dimension_result_set: DimensionResultSet
) -> KnowledgeGraph:
    """应用约束到图谱，创建约束节点和边"""
```

**边类型**:
- `applies_to` - 应用关系
- `constrains` - 约束关系
- `inherits_from` - 继承关系

**完成后操作**:
- 注入A1 finalize挂点
- 使定稿图谱化含约束建边

**依赖**: T-B、T-C

---

### 批次2/3附录: T-G/T-D/T-E/T-H

#### T-G: 断点G修复：约束继承传递【批次2】
**文件路径**: `backend/app/domains/creation/constraint/constraint_inheritor.py`

**规则**:
```
沿图谱边传递约束，按权重过滤密度:
- ≥10%: 完整传递
- 5-10%: 压缩摘要
- <5%: 不传

override可但不可删除
```

**依赖**: T-F

---

#### T-D: 断点D修复：PromptBuilder约束注入【批次2】
**文件路径**: `backend/app/domains/creation/asset/prompt_builder.py`

**修改**: 8层模板引用约束标签（按T-C逻辑树target_prompt_layer路由）

**依赖**: T-C

---

#### T-E: 断点E修复：PromptFusion约束感知【批次2】
**文件路径**: `backend/app/domains/creation/asset/prompt_fusion.py`

**修改**: 3段式组装感知约束（依赖T-G的继承结果）

**依赖**: T-G

---

#### T-H: 断点H修复：层间语义焦点模板【批次2，独立】
**文件路径**: `backend/app/domains/creation/asset/dimension_generator.py`

**修改**: DimensionPromptBuilder（同一维度在6层的不同语义焦点提示模板）

**依赖**: 无（可与D/E并行）

---

## 5. 附录

### 依赖链图

```
批次1 Wave 1（公用底座）:
T1→T3→T4 串行
T2/T5/T6/T7 并行
T-DICT 同波并行

批次1 Wave 2:
T-B → T-A
T8 并行

批次1 Wave 3:
T-C → T-F → T9

批次2:
T-G（依赖批次1的T-F）∥ T-H（独立）∥ T10（A2）

批次3:
T11（A3）→ T12（大厅）→ T13b
```

---

### 三条铁律

**铁律1: 四层编码永不覆盖只追加**
```
版本号=同实例当前+1
IP序号=A1会话启动即分配，废弃归档不回收
实例号=同范围最大+1
```

**铁律2: 修改不污染**
```
图谱=事实源
文件=单向序列化导出
反向写文件不回写图谱（重新定稿才重建）
```

**铁律3: stale不阻断**
```
只标记不删除
stale→提示变更集
用户坚持继续→留痕（used_stale=true）
```

---

### 授权关卡协议摘要

**每个断点任务开工前必须执行**:

1. **呈现解释**
   - 现状：当前问题
   - 修复：实施方案
   - 影响文件：涉及文件列表
   - 风险与回滚：风险评估
   - 引用T2授权文档=源计划L398-403

2. **停下等用户明确授权**
   - 未获授权不得写代码

3. **授权话语存证**
   - 路径: `.sisyphus/evidence/task-{X}-authorization.txt`

4. **后续步骤**
   - pytest基线留存
   - TDD实现
   - 回归验证（基线测试全绿）
   - 证据留痕

---

*文档结束*
