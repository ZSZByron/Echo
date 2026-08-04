# 双向概念映射系统 — 研究进度交接

> **日期**: 2026-08-02
> **会话范围**: 从"检查创意是否已有"到"实验验证 + 预设风格系统"
> **下一会话**: 实现核心算法 5 层架构

---

## 一、项目背景

Echo UGC 是一个"AI交互+规则判定"的游戏世界构建系统。用户提出的新设计是：**任意世界概念（剧情/资产/事件/文化/约束）作为种子，通过语义图谱自动补全缺失维度，形成五维闭环世界。**

现有系统是单向流水线（SceneYAML → 资产生成），缺少：概念解析层、反向推理、缺失检测、闭环校验。

## 二、核心问题：5 个未解决

### 问题 1：ConceptNode 中间表示不存在

**现状**：LLM 每次从零生成四维，没有 `tags → 维度映射` 的中间层。
**需要**：统一的 ConceptNode 数据模型。

```python
class ConceptNode(BaseModel):
    raw_input: str                          # 原始输入
    detected_type: SeedType                 # story|asset|event|culture|constraint|mixed
    tags: list[str]                         # 语义标签 ["altar","ritual","ancient"]
    dimensions: dict[str, DimensionStatus]  # 五维状态
    confidence: float                       # 解析置信度

class DimensionStatus(BaseModel):
    status: Literal["empty","partial","filled"]
    content: Any | None
    source: Literal["input","rule_mapped","llm_generated","user_confirmed"]
```

**新建文件**：`backend/app/models/concept.py`
**依赖**：无，纯 Pydantic 模型。

### 问题 2：缺失检测不存在

**现状**：系统固定填四个空位，不检测语义缺失。
**需要**：Gap Detector — 输入 ConceptNode，检测哪些维度是 `"empty"`，输出补全请求列表。

**核心逻辑**：纯 Python 规则，零 AI 调用。
```python
def detect_gaps(node: ConceptNode) -> list[str]:
    return [dim for dim, status in node.dimensions.items() if status.status == "empty"]
```

**新建文件**：`backend/app/services/gap_detector.py`
**难度**：★☆☆ — 最简单的一层。

### 问题 3：反向推理不存在

**现状**：只有种子→LLM→四维，一个方向。
**需要**：Backward Generator — Asset→Story、Event→Asset 等跨维度反推。复用 LLMProvider，多 prompt 模板。

**核心挑战**：设计双向映射规则。比如：
- Asset tags=[altar, ritual] → 反推 Story(type=quest, required_assets=[altar])
- Constraint(禁止金属武器) → 反推 Culture(崇尚自然、有机材料) + Asset(骨器、水晶武器)

**新建文件**：`backend/app/services/backward_generator.py`
**依赖**：问题 1（ConceptNode）+ 现有 LLMProvider。
**难度**：★★★ — 最复杂，需要设计双向映射规则。

### 问题 4：循环一致性不存在

**现状**：生成的五维之间无校验，可能产生矛盾（水晶祭坛+废土文化+赛博朋克事件）。
**需要**：Cycle Consistency Check — 正向生成后反向回推，检查一致性。

**算法来源**：CycleGAN 思想。
```python
def cycle_check(seed, generated, provider):
    # 正向：seed(asset) → generated(story)
    # 反向：generated(story) → reverse(asset')
    # 一致性：asset' ≈ seed(asset)?
    reverse = backward_generate(generated, target_dim=seed.type)
    similarity = semantic_similarity(seed.content, reverse.content)
    return similarity > THRESHOLD
```

**新建文件**：`backend/app/services/cycle_checker.py`
**依赖**：问题 3（Backward Generator）。
**难度**：★★ — 需要语义相似度计算。

### 问题 5：规则映射表是空的

**现状**：预设里有 mapping_logic，但那是静态模板，没有运行时逻辑。
**需要**：Rule Mapper — 输入标签，查表命中规则，生成确定性基线。

**数据来源**：从实验结果中提取标签→维度关系（7 个成功案例 + 8 个预设的 mapping_logic）。

**新建文件**：
- `backend/app/models/mapping_rule.py` — 规则数据模型
- `backend/app/services/rule_mapper.py` — 查表引擎
- `backend/data/rules/mapping_rules.json` — 初始规则表

**难度**：★★ — 规则设计 + 查询引擎。

---

## 三、已完成的工作

### 3.1 代码变更

| 文件 | 状态 | 改动 |
|------|------|------|
| `backend/.env` | **修改** | ACTIVE_PROVIDER=deepseek, DEEPSEEK_MODEL=deepseek-v4-pro, DEEPSEEK_BASE_URL=https://api.deepseek.com |
| `backend/app/ai/config.py` | **修改** | max_tokens: 1000 → 4000 |
| `backend/app/ai/provider.py` | **修改** | 新增 `_default_extra_body` + `_merge_kwargs()`，DeepSeek 自动注入 `enable_thinking=False` |

### 3.2 新建实验文件（全部在 `backend/experiments/`）

| 文件 | 用途 |
|------|------|
| `__init__.py` | 包初始化 |
| `quick_api_test.py` | API 连通性快速验证 |
| `dimension_fill_experiment.py` | **核心实验**：10种子×GLM式空白填充，含 SEEDS 定义 + system/user prompt |
| `retry_failed_seeds.py` | 重试失败种子 |
| `merge_final_report.py` | 合并结果 + 质量评分 |
| `thinking_ab_test.py` | Thinking ON vs OFF A/B 测试 |
| `trpg_presets.py` | **8个类型风格指南**（voice_prompt + lexicon + mapping_logic） |
| `preset_ab_test.py` | RAW vs PRESET 风格对比测试 |

### 3.3 实验结果（全部在 `backend/experiments/results/`）

| 文件 | 内容 |
|------|------|
| `dimension_fill_FINAL.json` | **最终合并结果**（含质量评分） |
| `dimension_fill_results_*.json` | 各轮实验原始数据（4份） |
| `dimension_fill_report_*.md` | 各轮实验人工评估报告（4份） |
| `thinking_ab_test_*.json/md` | Thinking A/B 测试结果 |
| `preset_ab_test_*.json/md` | Preset A/B 测试结果 |

### 3.4 实验结论

#### 维度填充实验（核心假设验证）

| 指标 | GLM-4.7 | DeepSeek V4-Pro (thinking OFF) |
|------|---------|-------------------------------|
| 成功率 | 7/10 | **10/10** |
| 平均耗时 | 38.8s | **15.5s** |
| 质量评分 | 4.64/5 | **~4.7/5** |

**结论**：✅ **核心假设确认** — LLM 能从单维度种子正确推断其他四维。平均质量 4.64/5，远超 3.5 门槛。

#### Thinking A/B 测试

| 指标 | Thinking ON | Thinking OFF |
|------|-------------|-------------|
| 成功率 | 8/10 | **10/10** |
| 平均耗时 | 24.7s | **15.5s** |

**结论**：关闭 thinking 模式后成功率 100%、速度提升 37%、质量不降。已在 provider.py 中默认关闭。

#### Preset 风格对比测试

| 维度 | RAW（无风格指令） | PRESET（有风格指令） |
|------|-------------------|---------------------|
| 文风 | 通用奇幻 | 类型精准（克苏鲁/废土/黑暗奇幻） |
| 词汇 | 通用 | 严格使用 lexicon 专有名词 |
| 结构 | 自由格式 | 遵循 mapping_logic 模板 |

**结论**：✅ **风格指令三层全部生效**（voice + lexicon + mapping_logic）。

---

## 四、算法理论调研

### 4.1 核心算法来源（4路融合）

| 来源 | 论文/算法 | 对应层 |
|------|-----------|--------|
| GLM 空白填充 | Du et al., ACL 2022 — Autoregressive Blank Infilling + 2D Positional Encoding | 维度补全范式 |
| Concept Bottleneck Models | Koh et al., ICML 2020 | ConceptNode 中间层 |
| CycleGAN 循环一致性 | Zhu et al., 2017 | 双向一致性校验 |
| 溯因推理 | Abductive Reasoning, 2026 survey | 反向推理 |

### 4.2 相关算法清单

| 算法 | 用途 | 相关度 |
|------|------|--------|
| GLM Blank Infilling | 缺失维度 = [MASK]，已有维度 = Part A 上下文 | ⭐⭐⭐⭐⭐ |
| Concept Bottleneck Models (CBM) | ConceptNode = 概念瓶颈，信息必须穿过它 | ⭐⭐⭐⭐⭐ |
| CycleGAN Cycle-Consistency | Story→Asset→Story' ≈ Story | ⭐⭐⭐⭐⭐ |
| TransE / RotatE | 规则映射表的向量化（标签→维度嵌入） | ⭐⭐⭐⭐ |
| ANALOGYKB | 类比推理（水晶祭坛→希腊神坛） | ⭐⭐⭐⭐ |
| Dual Learning | 正向+反向联合训练 | ⭐⭐⭐⭐ |
| GraphRAG | 规则表 = RAG 知识库 | ⭐⭐⭐ |
| CREAM (合理CBM) | 概念间图结构约束 + 侧通道补充 | ⭐⭐⭐ |

### 4.3 目标架构（4层）

```
用户输入种子
    ↓
Layer 1: 规则映射表 (TransE/RotatE 嵌入 + CREAM 约束)
    ↓ 确定性基线
Layer 2: GLM-style Blank Infilling (LLM 基于规则+风格生成)
    ↓ 补全缺失
Layer 3: Cycle Consistency Check (正向→反向→验证)
    ↓ 质量保证
Layer 4: 用户闭环 (确认→写入World KG+回馈规则表)
```

---

## 五、TRPG 预设系统（8个类型风格指南）

### 预设清单

每个预设包含三层：**voice_prompt**（文风指令）+ **lexicon**（专有名词库）+ **mapping_logic**（映射规则）。

| ID | 名称 | 类型 | 映射规则数 | 词汇条目 |
|----|------|------|-----------|---------|
| `lovecraftian_horror` | 深渊低语 | 克苏鲁恐怖 | 5 | 50 |
| `cyberpunk_heist` | 霓虹窃案 | 赛博朋克 | 5 | 52 |
| `dark_fantasy_dungeon` | 腐化深渊 | 黑暗奇幻 | 5 | 48 |
| `wasteland_survival` | 灰烬之路 | 废土生存 | 5 | 51 |
| `xianxia_cultivation` | 碎天录 | 东方仙侠 | 5 | 54 |
| `space_opera` | 群星彼岸 | 太空歌剧 | 5 | 53 |
| `classic_fantasy` | 破晓之剑 | 传统奇幻 | 5 | 55 |
| `court_intrigue` | 鸩酒与玫瑰 | 权谋阴谋 | 6 | 57 |

### 关键函数

```python
from experiments.trpg_presets import build_system_prompt, get_style_guide, list_presets

# 构建完整 system prompt（voice + lexicon + mapping_logic）
prompt = build_system_prompt("lovecraftian_horror")

# 获取风格指令组件
guide = get_style_guide("cyberpunk_heist")
# guide["voice_prompt"]  — 文风指令
# guide["lexicon"]       — 词汇库
# guide["mapping_logic"] — 映射规则
```

---

## 六、当前运行配置

```env
# .env 关键配置
ACTIVE_PROVIDER=deepseek
DEEPSEEK_API_KEY=<用户的key>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
```

```python
# config.py
max_tokens: int = 4000  # 从1000调大

# provider.py — DeepSeek 自动关闭 thinking
if config.provider_type == "deepseek":
    self._default_extra_body["enable_thinking"] = False
```

---

## 七、下一步实施计划

### Phase A: ConceptNode + Gap Detector（1-2天）

**产出**：
- `backend/app/models/concept.py` — ConceptNode + DimensionStatus 数据模型
- `backend/app/services/gap_detector.py` — 缺失维度检测（纯 Python 规则）

**验收**：
- ConceptNode 能从 SEEDS 中的任意种子构建
- Gap Detector 正确识别缺失维度
- 单元测试覆盖

### Phase B: Rule Mapper（2-3天）

**产出**：
- `backend/app/models/mapping_rule.py` — 规则数据模型
- `backend/app/services/rule_mapper.py` — 标签→维度查表引擎
- `backend/data/rules/mapping_rules.json` — 初始规则表（从实验结果提取）

**数据来源**：
- `experiments/results/dimension_fill_FINAL.json` — 7个成功案例的标签→维度关系
- `experiments/trpg_presets.py` — 8个预设的 mapping_logic（共 41 条规则）

**验收**：
- 输入标签集，输出匹配的映射规则 + 置信度
- Coverage@1 ≥ 70%（至少命中1个维度）

### Phase C: Backward Generator（2-3天）

**产出**：
- `backend/app/services/backward_generator.py` — 跨维度反向推理

**依赖**：Phase A（ConceptNode）+ 现有 LLMProvider

**验收**：
- Asset→Story、Event→Asset、Constraint→Culture 等方向均能生成
- 生成质量 ≥ 3.5/5

### Phase D: Cycle Consistency（1-2天）

**产出**：
- `backend/app/services/cycle_checker.py` — 循环一致性校验

**依赖**：Phase C（Backward Generator）

**验收**：
- 正向→反向→一致性分数
- 一致性 > 0.7 的结果中 >85% 质量合格

### Phase E: 闭环整合（1天）

**产出**：
- `backend/app/services/seed_engine.py` — 编排层，串联 A→D
- `backend/app/api/seed_routes.py` — `/api/seed` API 端点

**验收**：
- 端到端：任意种子 → ConceptNode → Gap Detect → Rule Map → LLM Fill → Cycle Check → 输出

---

## 八、关键文件索引

### 现有代码（需理解的）

| 文件 | 用途 |
|------|------|
| `backend/app/ai/provider.py` | LLM 抽象层（6家 provider） |
| `backend/app/ai/config.py` | Provider 配置加载 |
| `backend/app/services/graph_extractor.py` | 现有 LLM 图谱提取（可改造为 Concept Parser 的基础） |
| `backend/app/models/story_graph.py` | StoryGraph 数据模型 |
| `backend/app/models/event_graph.py` | EventGraph 数据模型 |
| `backend/app/models/culture.py` | CultureTree 数据模型 |
| `backend/app/models/constraint.py` | ConstraintTree 数据模型 |
| `backend/app/models/knowledge_graph.py` | KnowledgeGraph 数据模型（World KG 基础） |
| `backend/app/models/asset.py` | Asset 数据模型（含 classification 扩展） |

### 设计文档

| 文件 | 用途 |
|------|------|
| `docs/SYSTEM_DESIGN_SPEC_v3.md` | **权威设计规范**（五图模型 + 接口契约 + 实施路线图） |
| `.sisyphus/plans/phase1-data-models.md` | Phase 1 数据模型计划（已完成） |
| `.sisyphus/plans/graph-driven-asset-pipeline.md` | 图谱驱动资产生成（已完成） |

### 本会话新建文件

| 文件 | 用途 |
|------|------|
| `backend/experiments/dimension_fill_experiment.py` | **核心实验脚本**（含 SEEDS + prompt 模板） |
| `backend/experiments/trpg_presets.py` | **8个类型风格指南** |
| `backend/experiments/thinking_ab_test.py` | Thinking A/B 测试 |
| `backend/experiments/preset_ab_test.py` | Preset A/B 测试 |
| `backend/experiments/results/*.json` | 所有实验原始数据 |
| `backend/experiments/results/*.md` | 所有实验报告 |

---

## 九、新会话快速启动指令

```
读取 PROJECT_STATE.md（如不存在则忽略）。
读取 docs/handoff-bidirectional-mapping.md（本文件）。
读取 backend/experiments/trpg_presets.py（预设系统）。
读取 backend/experiments/dimension_fill_experiment.py（实验脚本 + SEEDS 定义）。

任务：开始 Phase A — 实现 ConceptNode + Gap Detector。
```
