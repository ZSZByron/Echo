"""Two-stage pipeline v3: Seed -> extract+fill 6-dim -> weight-map to layers.

Stage 1: ONE LLM call — extract 6-dim constraints from seed (fill gaps)
Stage 2: 6-dim constraints x weight matrix -> 3 layer JSONs (LLM expansion)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

_ENV_FILE = _BACKEND_DIR / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _, _val = _line.partition("=")
            _key = _key.strip()
            _val = _val.split("#")[0].strip()
            if _key and _key not in os.environ:
                os.environ[_key] = _val

from app.ai.config import load_provider_config
from app.ai.provider import LLMProvider, create_provider
from app.models.dimension import (
    ConstraintDimension,
    CreationLayer,
    DIMENSION_INFO,
    LAYER_NAMES,
    DimensionResultSet,
)
from app.domains.creation.constraint.dimension_generator import WeightMatrixLoader

# ============================================================
# USER INPUT
# ============================================================
SEED_INPUT = "\u5728\u4e16\u56096\u533a\uff0c\u6709\u4e00\u4e2a\u6b7b\u4eba\u5934\uff0c\u6bcf\u5f53\u6709\u4eba\u89c1\u5230\uff0c\u5934\u5c31\u6ca1\u4e86\uff0c\u6d88\u9664\u6076\u7075!"
SEED_DESC = "\u7075\u5f02\u89c4\u5219\u602a\u8c08\u4e16\u754c\uff0c\u8c03\u67e5\u5458\u6e38\u8d70\u5728\u751f\u6b7b\u4e2d\uff0c\u62d4\u9664\u6076\u7075\uff0c\u7834\u89e3\u89c4\u5219"
INTENT = "\u8c03\u67e5\u5458\u88ab\u73a9\u5f04\u7684\u6b7b\u53bb\u6d3b\u6765\uff0c\u9b3c\u4e8b\u7684\u80cc\u540e\u662f\u4eba\u4e8b\uff0c\u9690\u85cf\u5728\u5e15\u540e\u7684boss\uff0c\u89c4\u5219\u5bf9\u6297\u89c4\u5219!"
TARGET_LAYERS = [CreationLayer.CAMPAIGN, CreationLayer.NPC, CreationLayer.ASSET]


def sep(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


# ============================================================
# STAGE 1: Extract + Fill 6-dim constraints from seed (ONE call)
# ============================================================

def build_extract_prompt(
    seed_input: str,
    seed_desc: str,
    intent: str,
) -> list[dict[str, str]]:
    """Build prompt for extracting 6-dim constraints from seed text.

    LLM reads the seed, extracts what's mentioned, fills what's missing.
    """

    system_prompt = """\
你是一个游戏世界构建系统中的约束提取器。

## 你的任务

读取用户提供的种子概念，从中**提取**并**补写**出完整的6维约束模型。

## 6维约束体系

每个种子概念都必须有6个维度的约束：

| 维度 | 代号 | 含义 | 说明 |
|------|------|------|------|
| 内容红线 | RED | 这个对象不能包含什么 | 禁止清单 |
| 物理法则 | LAW | 这个对象服从什么世界规则 | 规则函数、魔法体系、科技水平 |
| 行为规则 | ACT | 作用于这个对象的行为怎么判定 | 技能检定、社交反馈、伤害计算 |
| 叙事约束 | NAR | 描述这个对象时遵循什么风格 | 文风、词汇、氛围、基调 |
| 世界状态 | WST | 这个对象携带什么动态状态效果 | 天气、环境修正、buff/debuff |
| 社交生态 | SOC | 这个对象和谁有关系、什么关系 | 阵营、声望、亲缘、敌对 |

## 提取规则

1. **种子中明确提到的内容** → 直接提取到对应维度
   - 例: "见到头就没了" → ACT行为规则 (trigger=见到, failure=头消失即死)
   - 例: "消除恶灵" → SOC社交生态 (target=恶灵, type=敌对)
2. **种子中暗示但未明说的内容** → 根据上下文推断补写
   - 例: "灵异规则怪谈" → NAR叙事约束 (style=规则怪谈纪实风, tone=压抑悬疑)
   - 例: "世嘉6区" → WST世界状态 (effects=区域环境效果)
3. **种子完全没提到的内容** → 根据种子主题合理补写
   - 例: 种子没提"禁止什么" → RED根据恐怖怪谈题材补写禁忌清单
   - 例: 种子没提"物理法则" → LAW根据灵异世界观补写规则体系

## 输出格式

输出严格的JSON，包含全部6个维度：

```json
{
  "RED": {
    "forbidden": ["禁止的内容1", "禁止的内容2"],
    "note": "说明"
  },
  "LAW": {
    "rules": ["规则描述1", "规则描述2"],
    "mechanism": "核心运行机制描述"
  },
  "ACT": {
    "actions": [
      {"trigger": "触发条件", "check": "判定方式", "success": "成功后果", "failure": "失败后果"}
    ]
  },
  "NAR": {
    "style": "文风/氛围描述",
    "keywords": ["关键词1", "关键词2"],
    "tone": "基调"
  },
  "WST": {
    "effects": [
      {"name": "效果名", "type": "buff/debuff/环境", "magnitude": "数值或描述"}
    ]
  },
  "SOC": {
    "relations": [
      {"target": "关系对象", "type": "关系类型", "value": "关系值/态度"}
    ]
  }
}
```

只输出JSON，不要输出任何其他内容。"""

    user_prompt = f"""\
## 种子概念

**名称**: {seed_input}
**描述**: {seed_desc}
**创作意图**: {intent}

请从这段种子中提取并补写完整的6维约束模型。
记住：种子提到的内容直接提取，没提到的根据主题合理补写。"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


async def stage1_extract(
    provider: LLMProvider,
) -> dict[ConstraintDimension, dict[str, Any]]:
    """Stage 1: Extract + fill 6-dim constraints from seed in ONE call."""

    sep("STAGE 1: Extract + Fill 6-Dim Constraints from Seed")
    print(f"\n  Seed:   {SEED_INPUT}")
    print(f"  Desc:   {SEED_DESC}")
    print(f"  Intent: {INTENT}")
    print(f"\n  Strategy: ONE LLM call — extract mentioned dims, fill missing dims")

    # Show what the seed mentions vs what needs filling
    print(f"\n  --- Seed Analysis ---")
    seed_text = SEED_INPUT + SEED_DESC + INTENT
    mentions = {
        "RED": ["禁止", "不能", "红线"],
        "LAW": ["规则", "法则", "物理", "魔法"],
        "ACT": ["见到", "触发", "判定", "检定", "行为"],
        "NAR": ["风格", "文风", "氛围", "基调"],
        "WST": ["环境", "天气", "buff", "状态"],
        "SOC": ["恶灵", "boss", "调查员", "敌对", "关系"],
    }
    for dim, keywords in mentions.items():
        found = [kw for kw in keywords if kw in seed_text]
        if found:
            print(f"    {dim}: EXTRACT (found keywords: {found})")
        else:
            print(f"    {dim}: FILL (no direct mention, LLM must infer)")

    print(f"\n  >>> Calling LLM to extract + fill 6 dimensions ...")

    messages = build_extract_prompt(SEED_INPUT, SEED_DESC, INTENT)

    start = time.time()
    raw = await provider.chat_json(messages)
    elapsed = time.time() - start

    # Validate
    result = DimensionResultSet.model_validate(raw)

    print(f"  <<< Done in {elapsed:.1f}s")

    # Show each dimension with source annotation
    print(f"\n  --- 6-Dimension Constraint Model ---")
    constraints: dict[ConstraintDimension, dict[str, Any]] = {}

    for dim in ConstraintDimension:
        info = DIMENSION_INFO[dim]
        data = getattr(result, dim.name)
        data_dict = data.model_dump()
        constraints[dim] = data_dict
        content_size = len(json.dumps(data_dict, ensure_ascii=False))

        # Check if seed mentions this dimension's keywords
        found_kw = mentions.get(dim.value, [])
        is_mentioned = any(kw in seed_text for kw in found_kw)
        source = "EXTRACTED" if is_mentioned else "FILLED"

        print(f"\n  [{source}] {dim.value} ({info.name}) — {content_size} chars")
        print(f"         {info.desc}")

        for key, val in data_dict.items():
            if isinstance(val, list) and val:
                for j, item in enumerate(val):
                    if isinstance(item, dict):
                        preview = json.dumps(item, ensure_ascii=False)
                        if len(preview) > 100:
                            preview = preview[:100] + "..."
                        print(f"         {key}[{j}]: {preview}")
                    else:
                        print(f"         {key}[{j}]: {item}")
            elif isinstance(val, str) and val:
                print(f"         {key}: {val[:120]}")
            elif isinstance(val, list) and not val:
                print(f"         {key}: (empty)")

    return constraints


# ============================================================
# STAGE 2: Weight mapping -> layer-specific expansion
# ============================================================

def build_mapping_prompt(
    layer: CreationLayer,
    constraints: dict[ConstraintDimension, dict[str, Any]],
    weights: dict[str, int],
    seed_input: str,
    seed_desc: str,
    intent: str,
) -> list[dict[str, str]]:
    """Build prompt for expanding constraints into a specific layer with hard quotas."""

    layer_name = LAYER_NAMES[layer]
    TOTAL_BUDGET = 2000

    # Calculate per-dimension quotas
    quota_lines = []
    for dim_code, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
        info = DIMENSION_INFO[ConstraintDimension(dim_code)]
        quota = int(TOTAL_BUDGET * weight / 100)

        if weight >= 25:
            level = "FULL"
            items = "3-5 items"
            desc = "write detailed content: specific names, numbers, mechanics"
        elif weight >= 10:
            level = "MID"
            items = "1-2 items"
            desc = "write brief content: 1-2 short items"
        else:
            level = "MIN"
            items = "0-1 items"
            desc = "ONE sentence max, just acknowledge the constraint exists"

        quota_lines.append(
            f"  {dim_code} ({info.name}) — weight {weight}% — quota {quota} chars — {level} — {items}\n"
            f"    {desc}"
        )

    quotas_text = "\n".join(quota_lines)
    constraints_json = json.dumps(
        {dim.value: constraints.get(dim, {}) for dim in ConstraintDimension},
        ensure_ascii=False, indent=2,
    )

    system_prompt = f"""\
你是一个分层创作系统中的世界构建引擎。

## 当前任务

DM 正在 **{layer_name} ({layer.value})** 层创作。
创作意图: {intent}

## 种子概念

**名称**: {seed_input}
**描述**: {seed_desc}

## Stage 1 提取的6维约束模型（扩写基础）

```json
{constraints_json}
```

## 本层级配额表（必须严格遵守）

每个维度的配额由权重决定。你必须严格控制每个维度的输出量：

{quotas_text}

## 严格遵守的规则

1. **配额是硬限制** — FULL 级别写到配额上限，MIN 级别最多1句话
2. **MIN 维度禁止展开** — 如果某维度是 MIN 级别(<=5%)，只写一句概括，不要列表、不要详细描述
3. **FULL 维度要丰富** — 如果是 FULL 级别(>=25%)，必须有具体名称、数值、机制
4. **基于约束扩写** — 不能偏离 Stage 1 的约束框架
5. **层级差异** — {layer_name} 层的扩写必须体现这一层级的关注重点

## 输出格式

```json
{{
  "RED": {{"forbidden": [...], "note": "..."}},
  "LAW": {{"rules": [...], "mechanism": "..."}},
  "ACT": {{"actions": [{{"trigger": "...", "check": "...", "success": "...", "failure": "..."}}]}},
  "NAR": {{"style": "...", "keywords": [...], "tone": "..."}},
  "WST": {{"effects": [{{"name": "...", "type": "...", "magnitude": "..."}}]}},
  "SOC": {{"relations": [{{"target": "...", "type": "...", "value": "..."}}]}}
}}
```

只输出JSON。"""

    user_prompt = f"""\
种子: {seed_input}
层级: {layer_name}

请严格按照配额表扩写。MIN维度最多1句，FULL维度要丰富具体。"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


async def stage2_weight_mapping(
    provider: LLMProvider,
    constraints: dict[ConstraintDimension, dict[str, Any]],
) -> dict[CreationLayer, dict[str, Any]]:
    """Stage 2: Expand constraints to target layers using weight matrix."""

    sep("STAGE 2: Weight Mapping -> Layer-Specific Expansion")

    loader = WeightMatrixLoader()
    matrix = loader.load()

    print(f"\n  Target layers: {[l.value for l in TARGET_LAYERS]}")
    print(f"\n  Weight matrix:")
    print(f"  {'Layer':<12} ", end="")
    for d in ConstraintDimension:
        print(f"{d.value:>4}", end="")
    print()
    for layer in TARGET_LAYERS:
        entry = matrix.get_entry(layer)
        w = entry.to_dict()
        print(f"  {layer.value:<12} ", end="")
        for d in ConstraintDimension:
            print(f"{w[d]:>4}", end="")
        print()

    results: dict[CreationLayer, dict[str, Any]] = {}

    for layer in TARGET_LAYERS:
        layer_name = LAYER_NAMES[layer]
        entry = matrix.get_entry(layer)
        weights = {d.value: entry.to_dict()[d] for d in ConstraintDimension}

        sep(f"STAGE 2 -> {layer.value} ({layer_name})")

        sorted_w = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        print(f"\n  Weight profile:")
        for dim_code, weight in sorted_w:
            info = DIMENSION_INFO[ConstraintDimension(dim_code)]
            bar = "#" * (weight // 5) + "." * (20 - weight // 5)
            marker = ">>>" if weight >= 25 else ("..." if weight <= 5 else "   ")
            print(f"  {marker} {dim_code:<4} [{bar} {weight:>3}%]  {info.name}")

        messages = build_mapping_prompt(layer, constraints, weights, SEED_INPUT, SEED_DESC, INTENT)

        print(f"\n  >>> Calling LLM [THINKING MODE] with constraints + {layer.value} weights ...")
        start = time.time()
        try:
            raw = await provider.chat_json(
                messages,
                extra_body={"enable_thinking": True, "max_tokens": 8192},
            )
            elapsed = time.time() - start

            result = DimensionResultSet.model_validate(raw)
            results[layer] = raw

            content_size = len(json.dumps(raw, ensure_ascii=False))
            print(f"  <<< Done in {elapsed:.1f}s | {content_size} chars total")

            print(f"\n  --- {layer_name} Expanded Output ---")
            for dim_code, weight in sorted_w:
                info = DIMENSION_INFO[ConstraintDimension(dim_code)]
                data = getattr(result, ConstraintDimension(dim_code).name)
                data_json = json.dumps(data.model_dump(), ensure_ascii=False)
                data_size = len(data_json)
                bar = "#" * (weight // 5) + "." * (20 - weight // 5)
                marker = ">>>" if weight >= 25 else ("..." if weight <= 5 else "   ")

                print(f"\n  {marker} {dim_code} ({info.name}) [{bar} {weight}%] [{data_size} chars]")

                if dim_code == "RED":
                    for item in data.forbidden:
                        print(f"      [FORBIDDEN] {item}")
                    if data.note:
                        print(f"      [NOTE] {data.note}")
                elif dim_code == "LAW":
                    for j, rule in enumerate(data.rules):
                        print(f"      [RULE {j}] {rule}")
                    if data.mechanism:
                        print(f"      [MECHANISM] {data.mechanism}")
                elif dim_code == "ACT":
                    for j, action in enumerate(data.actions):
                        print(f"      [ACTION {j}]")
                        for k, v in action.items():
                            print(f"        {k}: {v}")
                elif dim_code == "NAR":
                    print(f"      [STYLE] {data.style}")
                    print(f"      [KEYWORDS] {data.keywords}")
                    print(f"      [TONE] {data.tone}")
                elif dim_code == "WST":
                    for j, effect in enumerate(data.effects):
                        print(f"      [EFFECT {j}]")
                        for k, v in effect.items():
                            print(f"        {k}: {v}")
                elif dim_code == "SOC":
                    for j, rel in enumerate(data.relations):
                        print(f"      [RELATION {j}]")
                        for k, v in rel.items():
                            print(f"        {k}: {v}")

        except Exception as e:
            elapsed = time.time() - start
            print(f"  ERROR after {elapsed:.1f}s: {e}")
            import traceback
            traceback.print_exc()

    return results


# ============================================================
# MAIN
# ============================================================

async def main() -> None:
    config = load_provider_config()
    provider = create_provider(config)

    sep("PIPELINE OVERVIEW")
    print(f"""
  Stage 1: Seed -> ONE LLM call -> extract + fill 6-dim constraints
           Mentioned in seed: EXTRACT to corresponding dimension
           Not mentioned:     FILL based on seed theme

  Stage 2: 6-dim constraints x weight matrix -> 3 layer JSONs
           campaign (NAR=40% SOC=30%...) -> campaign JSON
           npc      (SOC=30% ACT=25%...) -> npc JSON
           asset    (LAW=30% ACT=30%...) -> asset JSON

  Seed:   {SEED_INPUT}
  Intent: {INTENT}
  Layers: {[l.value for l in TARGET_LAYERS]}
    """)

    # ---- STAGE 1 ----
    constraints = await stage1_extract(provider)

    # ---- STAGE 2 ----
    layer_results = await stage2_weight_mapping(provider, constraints)

    # ---- SAVE ALL RESULTS ----
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    save_dir = Path(_BACKEND_DIR / "experiments" / "results")
    save_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1 file
    s1_data = {
        "seed_input": SEED_INPUT,
        "seed_description": SEED_DESC,
        "intent": INTENT,
        "method": "single_call_extract_and_fill",
        "constraints": {dim.value: constraints.get(dim, {}) for dim in ConstraintDimension},
    }
    s1_path = save_dir / f"v3t_stage1_constraints_{ts}.json"
    s1_path.write_text(json.dumps(s1_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Stage 2 combined
    s2_data = {
        "seed_input": SEED_INPUT,
        "seed_description": SEED_DESC,
        "intent": INTENT,
        "method": "thinking_mode_hard_quota",
        "stage1_constraints": {dim.value: constraints.get(dim, {}) for dim in ConstraintDimension},
        "stage2_layers": {layer.value: data for layer, data in layer_results.items()},
    }
    s2_path = save_dir / f"v3t_stage2_all_layers_{ts}.json"
    s2_path.write_text(json.dumps(s2_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Each layer separate
    for layer, data in layer_results.items():
        layer_path = save_dir / f"v3t_stage2_{layer.value}_{ts}.json"
        layer_data = {
            "layer": layer.value,
            "layer_name": LAYER_NAMES[layer],
            "seed_input": SEED_INPUT,
            "intent": INTENT,
            "dimensions": data,
        }
        layer_path.write_text(json.dumps(layer_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- SUMMARY ----
    sep("FINAL SUMMARY")
    print(f"\n  Stage 1 (1 LLM call):")
    for dim in ConstraintDimension:
        info = DIMENSION_INFO[dim]
        data = constraints.get(dim, {})
        size = len(json.dumps(data, ensure_ascii=False))
        print(f"    {dim.value:<5} {info.name:<8} {size:>4} chars")

    print(f"\n  Stage 2 ({len(layer_results)} LLM calls):")
    for layer, data in layer_results.items():
        layer_name = LAYER_NAMES[layer]
        size = len(json.dumps(data, ensure_ascii=False))
        print(f"    {layer.value:<10} {layer_name:<8} {size:>5} chars")

    print(f"\n  === SAVED FILES ===")
    print(f"  {s1_path.name}")
    print(f"  {s2_path.name}")
    for layer in layer_results:
        print(f"  v3_stage2_{layer.value}_{ts}.json")

    print(f"\n  Total LLM calls: {1 + len(layer_results)}")
    print(f"{'='*70}")
    print(f"  PIPELINE COMPLETE")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
