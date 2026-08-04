# 双向概念映射系统 — 会话交接文档

> **日期**: 2026-08-02
> **项目**: H:\UGC — Echo UGC 游戏世界生成系统
> **目标**: 从不完整输入反推完整世界结构（任意种子 → 五维闭环世界）

---

## 一、用户核心创意

用户提出：系统应支持**任意维度作为种子输入**（剧情/资产/事件/文化/约束），自动检测缺失维度并补全，形成 Story+Event+Asset+Culture+Constraint 五维闭环世界。

### 核心设计（用户确认）

```
任意概念输入
    ↓
概念解析层 (Concept Parser) → ConceptNode {type, tags, dimensions}
    ↓
缺失维度检测 (Gap Detector) → "缺 Story, 缺 Constraint"
    ↓
规则映射表先导 (Rule Mapper) → 标签→维度确定性基线
    ↓
LLM 补全 (基于规则基线 + 风格指令，只补规则覆盖不到的部分)
    ↓
循环一致性校验 (Cycle Check) → Asset→Story→Asset' ≈ Asset?
    ↓
用户确认 → 写入 World KG + 回馈规则表（自学习）
```

转换机制（用户选定）：**混合方案 C** — 规则先导 + LLM 补全 + 用户确认后回馈规则表。

---

## 二、5 个未解决的核心问题

### 问题 1：ConceptNode 中间表示不存在

**现状**：没有 `tags` → 维度映射的中间层。LLM 每次从零生成，没有规则先导，没有确定性。

**需要建**：
```python
class ConceptNode(BaseModel):
    raw_input: str
    detected_type: SeedType  # story|asset|event|culture|constraint|mixed
    tags: list[str]          # 语义标签
    dimensions: dict[str, DimensionStatus]  # 五维状态
    confidence: float

class DimensionStatus(BaseModel):
    status: Literal["empty", "partial", "filled"]
    content: Any | None
    source: Literal["input", "rule_mapped", "llm_generated", "user_confirmed"]
```

**新文件**: `backend/app/models/concept.py`
**依赖**: 无，纯 Pydantic 模型

---

### 问题 2：缺失检测不存在

**现状**：系统不知道"缺了什么"。当前逻辑是固定填四个空位，不是语义缺失检测。

**需要建**：
```python
# services/gap_detector.py
def detect_gaps(concept_node: ConceptNode) -> list[GapReport]:
    """检查五维状态，返回缺失维度列表 + 补全优先级"""
    gaps = []
    for dim, status in concept_node.dimensions.items():
        if status.status == "empty":
            gaps.append(GapReport(
                dimension=dim,
                priority=_calculate_priority(dim, concept_node),
                suggested_source="rule" or "llm"
            ))
    return gaps
```

**新文件**: `backend/app/services/gap_detector.py`
**难度**: ★☆☆ — 纯 Python 规则，零 AI 调用

---

### 问题 3：反向推理不存在

**现状**：用户提出的核心创新——"资产→故事""事件→资产"——还没实现。现在只有一个方向：种子→LLM→四维。

**需要建**：
```python
# services/backward_generator.py
async def backward_generate(
    seed_dim: str,        # "asset"
    seed_content: dict,    # {"name": "水晶祭坛", ...}
    target_dim: str,       # "story"
    style_guide: dict,     # 预设风格指令
    rule_hints: list[dict] # 规则映射表的匹配结果
) -> dict:
    """从 seed_dim 反推 target_dim"""
```

**新文件**: `backend/app/services/backward_generator.py`
**难度**: ★★★ — 需要设计双向映射规则，复用 LLMProvider

---

### 问题 4：循环一致性不存在

**现状**：生成的五维之间没有校验关系。LLM 可能生成矛盾内容，系统不会发现。

**需要建**：
```python
# services/cycle_checker.py
async def cycle_check(
    seed: ConceptNode,
    generated: ConceptNode,
    provider: LLMProvider
) -> CycleReport:
    """
    正向：seed → generated
    反向：generated → seed'
    一致性：seed ≈ seed'?
    """
```

**新文件**: `backend/app/services/cycle_checker.py`
**算法来源**: CycleGAN cycle-consistency（论文已调研，见下文）
**难度**: ★★

---

### 问题 5：规则映射表是空的

**现状**：预设里有 mapping_logic 但那是静态模板，没有运行时逻辑——输入标签 → 查表 → 命中规则 → 注入生成。

**需要建**：
```python
# services/rule_mapper.py
class RuleTable:
    """标签→维度确定性映射规则库"""
    rules: list[RuleEntry]

    def match(self, tags: list[str], target_dim: str) -> list[RuleMatch]:
        """从 tags 匹配规则，返回候选 + 分数"""

    def learn(self, confirmed_mapping: dict):
        """用户确认后回馈新规则到表"""

# data/rule_table.json — 规则表持久化
```

**新文件**: `backend/app/services/rule_mapper.py` + `data/rule_table.json`
**初始数据**: 从实验结果提取（7个成功种子的标签→维度关系）
**难度**: ★★

---

## 三、本会话已完成的工作

### 实验 1：维度填充假设验证 ✅

| 指标 | GLM-4.7 | DeepSeek V4-Pro |
|---|---|---|
| 成功率 | 7/10 | **9-10/10** |
| 平均质量 | 4.64/5 | **4.7/5** |
| 平均速度 | 38.8s/seed | **15.5s/seed** |
| 结论 | 假设确认 | **假设确认（更快更稳定）** |

**产出**: `experiments/dimension_fill_experiment.py`
**结果**: `experiments/results/dimension_fill_FINAL.json`

---

### 实验 2：Thinking 模式 A/B ✅

| 模式 | 成功率 | 平均速度 | 质量 |
|---|---|---|---|
| Thinking ON | 8/10 | 24.7s | 内容更丰富但 JSON 被截断 |
| Thinking OFF | **10/10** | **15.5s** | 质量不降，稳定性更好 |

**决策**: DeepSeek V4-Pro 默认关闭 thinking。

**产出**: `experiments/thinking_ab_test.py`
**改动**: `provider.py` 自动注入 `enable_thinking=False`

---

### 实验 3：预设风格指令验证 ✅

A/B 对比（RAW 无风格 vs PRESET 有风格）：

| 维度 | RAW | PRESET |
|---|---|---|
| 文风 | 通用奇幻语调 | 严格遵循预设风格 |
| 词汇 | 通用词汇 | 使用 lexicon 专有名词 |
| 结构 | 平铺直叙 | 遵循 mapping_logic 模板 |
| 深度 | 基础描述 | 含 Boss悲剧背景/道德选择/调查链 |

**结论**: 风格指令三层（voice + lexicon + mapping_logic）全部生效。

**产出**: `experiments/trpg_presets.py`（8个预设）、`experiments/preset_ab_test.py`

---

### 实验 4：8 个 TRPG 预设库 ✅

| ID | 名称 | 类型 | 映射规则 | 词汇条目 |
|---|---|---|---|---|
| lovecraftian_horror | 深渊低语 | 克苏鲁恐怖 | 5 | 50 |
| cyberpunk_heist | 霓虹窃案 | 赛博朋克 | 5 | 52 |
| dark_fantasy_dungeon | 腐化深渊 | 黑暗奇幻 | 5 | 48 |
| wasteland_survival | 灰烬之路 | 废土生存 | 5 | 51 |
| xianxia_cultivation | 碎天录 | 东方仙侠 | 5 | 54 |
| space_opera | 群星彼岸 | 太空歌剧 | 5 | 53 |
| classic_fantasy | 破晓之剑 | 传统奇幻 | 5 | 55 |
| court_intrigue | 鸩酒与玫瑰 | 权谋阴谋 | 6 | 57 |

每个预设包含三层：
1. **voice_prompt** — 文风指令（语调/句式/修辞/节奏/视角/禁忌）
2. **lexicon** — 专有名词库（生物/地点/物品/概念/修饰语/禁用词）
3. **mapping_logic** — 标签→维度映射规则（含 template 模板）

**关键函数**: `build_system_prompt(preset_id)` → 合并三层为完整 system prompt

---

### 算法研究 ✅

调研了 4 条算法线（3个 librarian agent 并行搜索 + 直接搜索）：

| 算法 | 来源 | 与本项目的关系 |
|---|---|---|
| **GLM Blank Infilling** | Du et al., ACL 2022 | 缺失维度=空白，已有维度=上下文 |
| **Concept Bottleneck Models** | Koh et al., ICML 2020 | ConceptNode = 概念瓶颈层 |
| **CycleGAN Cycle-Consistency** | Zhu et al., 2017 | Asset→Story→Asset' 一致性校验 |
| **Abductive Reasoning** | 2026 survey | 反向推理 = 溯因推理 |
| **TransE/RotatE** | KGE 领域 | 标签→维度映射的向量化 |
| **GraphRAG** | Microsoft | 规则表 = RAG 知识库 |

**核心结论**: 这 4 条线从未被组合。本项目是 GLM 填充 + CBM 瓶颈 + CycleGAN 一致性 + 溯因推理的四路融合。

---

## 四、当前配置状态

### .env（已修改）

```env
ACTIVE_PROVIDER=deepseek
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
DEEPSEEK_API_KEY=<用户已填入有效Key>
```

### config.py（已修改）

```python
max_tokens: int = 4000  # 原为 1000
```

### provider.py（已修改）

```python
# DeepSeek V4 默认关闭 thinking
if config.provider_type == "deepseek":
    self._default_extra_body["enable_thinking"] = False

def _merge_kwargs(self, kwargs):
    """自动合并 default extra_body"""
```

---

## 五、文件清单

### 新建文件

| 文件 | 用途 |
|---|---|
| `backend/experiments/__init__.py` | 包初始化 |
| `backend/experiments/dimension_fill_experiment.py` | 核心实验：10种子×5维度填充 |
| `backend/experiments/thinking_ab_test.py` | Thinking ON/OFF A/B 测试 |
| `backend/experiments/preset_ab_test.py` | 预设风格 RAW vs PRESET A/B 测试 |
| `backend/experiments/trpg_presets.py` | **8个 TRPG 预设**（voice+lexicon+mapping） |
| `backend/experiments/quick_api_test.py` | API 连通性快速测试 |
| `backend/experiments/retry_failed_seeds.py` | 失败种子重试脚本 |
| `backend/experiments/merge_final_report.py` | 合并结果 + 质量评分 |
| `backend/experiments/results/*.json` | 实验结果数据（8个文件） |
| `backend/experiments/results/*.md` | 实验评估报告（7个文件） |

### 修改文件

| 文件 | 改动 |
|---|---|
| `backend/app/ai/config.py` | `max_tokens` 1000→4000 |
| `backend/app/ai/provider.py` | DeepSeek 自动 `enable_thinking=False` |
| `backend/.env` | 切换到 DeepSeek V4-Pro 官方 API |

### 已有相关文件（未修改，但重要）

| 文件 | 内容 |
|---|---|
| `backend/app/models/story_graph.py` | StoryGraph 数据模型（StoryNode/Edge/Choice/Condition） |
| `backend/app/models/event_graph.py` | EventGraph 数据模型（EventNode/Trigger/Action/Reward） |
| `backend/app/models/culture.py` | CultureTree 数据模型（CultureNode/values/aesthetic） |
| `backend/app/models/constraint.py` | ConstraintTree 数据模型（ConstraintNode/type/priority） |
| `backend/app/models/knowledge_graph.py` | KnowledgeGraph 数据模型（GraphNode/Edge/拓扑排序） |
| `backend/app/models/asset.py` | Asset 模型（含 classification 扩展字段） |
| `backend/app/services/graph_extractor.py` | LLM 文本→KnowledgeGraph 提取服务 |
| `backend/app/services/generation_planner.py` | LOD 感知的资产生成排序 |
| `backend/app/services/generation_scheduler.py` | 波次并行图像生成调度 |

---

## 六、下一步建议实施顺序

```
Phase A: 基础层（不碰 LLM，纯 Python）
  ├─ T1: models/concept.py — ConceptNode + DimensionStatus
  ├─ T2: services/gap_detector.py — 缺失维度检测（纯规则）
  └─ T3: services/rule_mapper.py — 规则映射表 + 初始数据提取
  预计: 2-3天

Phase B: LLM 层（复用已有 Provider）
  ├─ T4: services/backward_generator.py — 反向推理（Asset→Story 等）
  ├─ T5: services/cycle_checker.py — 循环一致性校验
  └─ T6: 集成 trpg_presets.py 的风格指令到生成流程
  预计: 3-4天

Phase C: 闭环层
  ├─ T7: services/seed_engine.py — 统一编排（概念解析→缺失检测→规则先导→LLM补全→Cycle校验→用户确认→回馈规则表）
  ├─ T8: api/seed_routes.py — /api/seed 入口端点
  └─ T9: 实验验证全部 5 个问题已解决
  预计: 2-3天
```

**建议新会话第一步**: 读本文档 → 创建 Phase A 的三个文件 → 用已有实验数据初始化规则表。

---

## 七、关键实验数据（供新会话参考）

### 维度填充质量评分（DeepSeek V4-Pro, thinking OFF）

| Seed | 类型 | 评分 | 亮点 |
|---|---|---|---|
| seed_01 水晶祭坛 | asset→ | 4.5 | 星光复苏 + 午夜星潮防御战 |
| seed_02 机械守护者 | asset→ | 4.5 | 最后的协议 + 道德抉择 |
| seed_05 夜狼袭击 | event→ | 5.0 | 堕落德鲁伊操控 + 银月氏族 |
| seed_07 星辰文明 | culture→ | 4.5 | 诸星之寂 + 星潮共鸣 |
| seed_08 生物改造 | culture→ | 5.0 | 飞升协议 + 神经风暴过载 |
| seed_09 禁金属武器 | constraint→ | 5.0 | 晶骨长弓 + 禁忌之秘 |
| seed_10 建筑悬浮 | constraint→ | 5.0 | 重力契约 + 星落之夜 |

**平均**: 4.7/5（远超 3.5 通过门槛）

### 预设风格指令 A/B 对比结论

- **文风**: ✅ RAW 产出通用语调，PRESET 严格遵循类型风格
- **词汇**: ✅ PRESET 输出使用 lexicon 专有名词（印斯茅斯/死灵之书 vs 盖革计数器/辐特宁）
- **映射逻辑**: ✅ PRESET 输出遵循 mapping_logic 结构模板（理智检定/资源消耗/Boss悲剧背景）
