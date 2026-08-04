"""Two-stage pipeline: Stage 1 (mask-filling 6-dim) -> Stage 2 (weight mapping).

Stage 1: Seed -> fill RED/LAW/ACT/NAR/WST/SOC one by one (GLM mask infilling)
Stage 2: 6-dim constraints x weight matrix -> 3 layer-specific structured JSONs
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import io
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
INTENT = "\u8c03\u67e5\u5458\u88ab\u73a9\u5f04\u7684\u6b7b\u53bb\u6d3b\u6765\uff0c\u9b3c\u4e8b\u7684\u80cc\u540e\u662f\u4eba\u4e8b\uff0c\u9690\u85cf\u5728\u5e55\u540e\u7684boss\uff0c\u89c4\u5219\u5bf9\u6297\u89c4\u5219!"
TARGET_LAYERS = [CreationLayer.CAMPAIGN, CreationLayer.NPC, CreationLayer.ASSET]

# Dimension fill order (can be any order — GLM span shuffling)
FILL_ORDER = [
    ConstraintDimension.RED,
    ConstraintDimension.LAW,
    ConstraintDimension.ACT,
    ConstraintDimension.NAR,
    ConstraintDimension.WST,
    ConstraintDimension.SOC,
]


def sep(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


# ============================================================
# STAGE 1: Mask-filling — fill each dimension one by one
# ============================================================

def build_mask_prompt(
    dim: ConstraintDimension,
    seed_input: str,
    seed_desc: str,
    intent: str,
    filled_dims: dict[ConstraintDimension, dict[str, Any]],
) -> list[dict[str, str]]:
    """Build prompt for filling ONE dimension mask.

    Part A = seed + already-filled dimensions (visible)
    Part B = the target dimension [MASK] (to generate)
    """
    info = DIMENSION_INFO[dim]

    # Part A: seed context
    context = f"""\
## Seed Concept
**Name**: {seed_input}
**Description**: {seed_desc}
**Intent**: {intent}
"""

    # Add already-filled dimensions as visible context
    if filled_dims:
        context += "\n## Already-Filled Constraints (visible context)\n"
        for prev_dim, prev_data in filled_dims.items():
            prev_info = DIMENSION_INFO[prev_dim]
            prev_json = json.dumps(prev_data, ensure_ascii=False, indent=2)
            context += f"\n### {prev_dim.value} ({prev_info.name})\n```json\n{prev_json}\n```\n"

    # Part B: the mask to fill
    system_prompt = f"""\
You are a constraint designer for a game world building system.

## Current Task
Fill the **{dim.value} ({info.name})** constraint dimension for the seed above.

**{info.name}**: {info.desc}
**Data essence**: {info.data_essence}

## Output Schema for {dim.value}
"""

    # Dimension-specific schema
    schemas = {
        ConstraintDimension.RED: """\
```json
{
  "forbidden": ["item1", "item2"],
  "note": "explanation"
}
```""",
        ConstraintDimension.LAW: """\
```json
{
  "rules": ["rule1", "rule2"],
  "mechanism": "core mechanism description"
}
```""",
        ConstraintDimension.ACT: """\
```json
{
  "actions": [
    {"trigger": "when", "check": "how", "success": "result", "failure": "result"}
  ]
}
```""",
        ConstraintDimension.NAR: """\
```json
{
  "style": "writing style description",
  "keywords": ["word1", "word2"],
  "tone": "emotional tone"
}
```""",
        ConstraintDimension.WST: """\
```json
{
  "effects": [
    {"name": "effect name", "type": "buff/debuff/environment", "magnitude": "value"}
  ]
}
```""",
        ConstraintDimension.SOC: """\
```json
{
  "relations": [
    {"target": "who", "type": "relationship type", "value": "attitude/strength"}
  ]
}
```""",
    }

    system_prompt += schemas[dim] + "\n\nOutput ONLY the JSON. No other text."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]
    return messages


async def stage1_mask_filling(
    provider: LLMProvider,
) -> dict[ConstraintDimension, dict[str, Any]]:
    """Stage 1: Fill 6 dimensions one by one using mask infilling."""

    sep("STAGE 1: 6-Dimension Mask Filling (GLM-style)")
    print(f"\n  Seed:   {SEED_INPUT}")
    print(f"  Desc:   {SEED_DESC}")
    print(f"  Intent: {INTENT}")
    print(f"\n  Fill order: {' -> '.join(d.value for d in FILL_ORDER)}")
    print(f"\n  Strategy: Each dimension sees seed + all previously filled dims")

    filled: dict[ConstraintDimension, dict[str, Any]] = {}

    for i, dim in enumerate(FILL_ORDER):
        info = DIMENSION_INFO[dim]
        print(f"\n  {'-'*60}")
        print(f"  [{i+1}/6] Filling {dim.value} ({info.name}) ...")
        print(f"          {info.desc}")
        visible = [d.value for d in filled.keys()]
        if visible:
            print(f"          Visible context: seed + {', '.join(visible)}")
        else:
            print(f"          Visible context: seed only (first dimension)")

        messages = build_mask_prompt(dim, SEED_INPUT, SEED_DESC, INTENT, filled)

        start = time.time()
        try:
            raw = await provider.chat_json(messages)
            elapsed = time.time() - start

            # Validate
            result = DimensionResultSet.model_validate({dim.value: raw})
            validated = getattr(result, dim.name)  # field names are uppercase: RED, LAW, etc.
            filled[dim] = validated.model_dump()

            content_size = len(json.dumps(raw, ensure_ascii=False))
            print(f"          Done in {elapsed:.1f}s | {content_size} chars")

            # Show brief preview
            for key, val in filled[dim].items():
                if isinstance(val, list) and val:
                    preview = str(val[0])[:80] if val else ""
                    print(f"          {key}: [{len(val)} items] e.g. {preview}")
                elif isinstance(val, str) and val:
                    print(f"          {key}: {val[:80]}")

        except Exception as e:
            elapsed = time.time() - start
            print(f"          ERROR after {elapsed:.1f}s: {e}")
            filled[dim] = {}

    sep("STAGE 1 RESULT: 6-Dimension Constraint Model")
    print(json.dumps(filled, ensure_ascii=False, indent=2))

    return filled


# ============================================================
# STAGE 2: Weight mapping -> layer-specific structured JSON
# ============================================================

def build_mapping_prompt(
    layer: CreationLayer,
    constraints: dict[ConstraintDimension, dict[str, Any]],
    weights: dict[str, int],
    seed_input: str,
    seed_desc: str,
    intent: str,
) -> list[dict[str, str]]:
    """Build prompt for mapping 6-dim constraints into a layer-specific JSON.

    The 6-dim constraints are the rules. The layer weights decide HOW MUCH
    detail each dimension gets in the final output.
    """
    layer_name = LAYER_NAMES[layer]

    # Sort dims by weight descending
    sorted_dims = sorted(weights.items(), key=lambda x: x[1], reverse=True)

    # Build weight bar chart
    dim_lines = []
    for dim_code, weight in sorted_dims:
        info = DIMENSION_INFO[ConstraintDimension(dim_code)]
        bar = "#" * (weight // 5) + "." * (20 - weight // 5)
        if weight >= 25:
            marker = ">>> MAIN (detailed)"
        elif weight <= 5:
            marker = "... minor (brief)"
        else:
            marker = "    normal"
        dim_lines.append(f"  {dim_code} ({info.name}) [{bar} {weight}%] {marker}")

    dims_text = "\n".join(dim_lines)

    # The 6-dim constraints as context (this is the RULE SET)
    constraints_json = json.dumps(constraints, ensure_ascii=False, indent=2)

    system_prompt = f"""\
你是一个分层创作系统中的世界构建引擎。

## 当前任务

DM 正在 **{layer_name} ({layer.value})** 层创作。
创作意图: {intent}

## 种子概念

**名称**: {seed_input}
**描述**: {seed_desc}

## Stage 1 已生成的6维约束框架（你必须遵循这些规则，并在此基础上扩写）

```json
{constraints_json}
```

## 这个层级的约束权重表

每一类约束在 {layer_name} 层的重要性不同。权重越高，你需要在生成内容中\
给予越多的篇幅和细节。标★的是主要约束，必须详细展开。低权重的维度\
可以简单提及甚至省略。

{dims_text}

## 生成原则

1. **基于约束扩写** — 上方的6维约束是框架，你需要在此基础上为{layer_name}层扩写出具体的、可玩的内容
2. **按权重分配注意力** — 高权重维度的内容必须丰富、具体、有细节；低权重维度简略即可
3. **侧重差异要明显** — 同样的约束在不同层级的扩写结果应该截然不同
4. **内容自洽** — 所有扩写内容必须围绕种子概念，与约束框架逻辑一致
5. **具体可玩** — 不要泛泛而谈，给出具体的名称、数值、机制描述

## 输出格式

输出严格的 JSON，包含所有6个约束维度的内容。高权重维度字段内容丰富\
（多个子字段、列表、详细描述），低权重维度可以只有一句话或空列表。

```json
{{
  "RED": {{
    "forbidden": ["禁止的内容1", "禁止的内容2"],
    "note": "说明（如果没有禁忌可以留空列表）"
  }},
  "LAW": {{
    "rules": ["规则描述1", "规则描述2"],
    "mechanism": "核心运行机制描述"
  }},
  "ACT": {{
    "actions": [
      {{"trigger": "触发条件", "check": "判定方式", "success": "成功后果", "failure": "失败后果"}}
    ]
  }},
  "NAR": {{
    "style": "文风/氛围描述",
    "keywords": ["关键词1", "关键词2"],
    "tone": "基调（如：压抑/壮丽/诡异）"
  }},
  "WST": {{
    "effects": [
      {{"name": "效果名", "type": "buff/debuff/环境", "magnitude": "数值或描述"}}
    ]
  }},
  "SOC": {{
    "relations": [
      {{"target": "关系对象", "type": "关系类型", "value": "关系值/态度"}}
    ]
  }}
}}
```

只输出 JSON，不要输出任何其他内容。"""

    user_prompt = f"""\
## 种子概念

**名称**: {seed_input}
**描述**: {seed_desc}

请根据上方权重表和Stage 1的约束框架，在 **{layer_name}** 创作层级下\
扩写这个种子的完整约束内容。记住：高权重维度要详细展开，低权重维度简略即可。"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


async def stage2_weight_mapping(
    provider: LLMProvider,
    constraints: dict[ConstraintDimension, dict[str, Any]],
) -> dict[CreationLayer, dict[str, Any]]:
    """Stage 2: Map constraints to target layers using weight matrix."""

    sep("STAGE 2: Weight Mapping -> Layer-Specific JSONs")

    loader = WeightMatrixLoader()
    matrix = loader.load()

    # Show weight matrix for target layers
    print(f"\n  Target layers: {[l.value for l in TARGET_LAYERS]}")
    print(f"\n  {'Layer':<12} ", end="")
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

        # Show weight profile
        print(f"\n  Weight profile:")
        sorted_w = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        for dim_code, weight in sorted_w:
            info = DIMENSION_INFO[ConstraintDimension(dim_code)]
            bar = "#" * (weight // 5) + "." * (20 - weight // 5)
            marker = ">>>" if weight >= 25 else ("..." if weight <= 5 else "   ")
            print(f"  {marker} {dim_code:<4} [{bar} {weight:>3}%]  {info.name}")

        messages = build_mapping_prompt(
            layer, constraints, weights, SEED_INPUT, SEED_DESC, INTENT
        )

        print(f"\n  >>> Calling LLM with constraint model + {layer.value} weights ...")
        start = time.time()
        try:
            raw = await provider.chat_json(messages)
            elapsed = time.time() - start

            # Validate
            result = DimensionResultSet.model_validate(raw)
            results[layer] = raw

            content_size = len(json.dumps(raw, ensure_ascii=False))
            print(f"  <<< Done in {elapsed:.1f}s | {content_size} chars total")

            # Print each dimension with weight annotation
            print(f"\n  --- {layer_name} Structured Output ---")
            for dim, weight in sorted_w:
                info = DIMENSION_INFO[ConstraintDimension(dim)]
                data = getattr(result, ConstraintDimension(dim).name)  # uppercase field
                data_json = json.dumps(data.model_dump(), ensure_ascii=False)
                data_size = len(data_json)
                bar = "#" * (weight // 5) + "." * (20 - weight // 5)
                marker = ">>>" if weight >= 25 else ("..." if weight <= 5 else "   ")

                print(f"\n  {marker} {dim} ({info.name}) [{bar} {weight}%] [{data_size} chars]")

                if dim == "RED":
                    for item in data.forbidden:
                        print(f"      [FORBIDDEN] {item}")
                    if data.note:
                        print(f"      [NOTE] {data.note}")
                elif dim == "LAW":
                    for j, rule in enumerate(data.rules):
                        print(f"      [RULE {j}] {rule}")
                    if data.mechanism:
                        print(f"      [MECHANISM] {data.mechanism}")
                elif dim == "ACT":
                    for j, action in enumerate(data.actions):
                        print(f"      [ACTION {j}]")
                        for k, v in action.items():
                            print(f"        {k}: {v}")
                elif dim == "NAR":
                    print(f"      [STYLE] {data.style}")
                    print(f"      [KEYWORDS] {data.keywords}")
                    print(f"      [TONE] {data.tone}")
                elif dim == "WST":
                    for j, effect in enumerate(data.effects):
                        print(f"      [EFFECT {j}]")
                        for k, v in effect.items():
                            print(f"        {k}: {v}")
                elif dim == "SOC":
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
  Stage 1: Seed -> Mask-fill 6 dimensions (RED/LAW/ACT/NAR/WST/SOC)
           Each dimension sees seed + all previously filled dims
           Output: One fixed 6-dimension constraint model

  Stage 2: 6-dim constraints x weight matrix -> 3 layer JSONs
           campaign (NAR=40% SOC=30%...) -> campaign JSON
           npc      (SOC=30% ACT=25%...) -> npc JSON
           asset    (LAW=30% ACT=30%...) -> asset JSON

  Seed:   {SEED_INPUT}
  Intent: {INTENT}
  Layers: {[l.value for l in TARGET_LAYERS]}
    """)

    # ---- STAGE 1 ----
    constraints = await stage1_mask_filling(provider)

    # ---- STAGE 2 ----
    layer_results = await stage2_weight_mapping(provider, constraints)

    # ---- SAVE ALL RESULTS TO FILES ----
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    save_dir = Path(_BACKEND_DIR / "experiments" / "results")
    save_dir.mkdir(parents=True, exist_ok=True)

    # Save Stage 1 constraints
    s1_path = save_dir / f"demo_stage1_constraints_{ts}.json"
    s1_data = {
        "seed_input": SEED_INPUT,
        "seed_description": SEED_DESC,
        "intent": INTENT,
        "constraints": {dim.value: constraints.get(dim, {}) for dim in ConstraintDimension},
    }
    s1_path.write_text(json.dumps(s1_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save Stage 2 layer results
    s2_path = save_dir / f"demo_stage2_layers_{ts}.json"
    s2_data = {
        "seed_input": SEED_INPUT,
        "seed_description": SEED_DESC,
        "intent": INTENT,
        "stage1_constraints": {dim.value: constraints.get(dim, {}) for dim in ConstraintDimension},
        "stage2_layers": {layer.value: data for layer, data in layer_results.items()},
    }
    s2_path.write_text(json.dumps(s2_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save each layer as separate file for easy reading
    for layer, data in layer_results.items():
        layer_path = save_dir / f"demo_stage2_{layer.value}_{ts}.json"
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
    print(f"\n  Stage 1 produced 6-dim constraint model:")
    for dim in ConstraintDimension:
        info = DIMENSION_INFO[dim]
        data = constraints.get(dim, {})
        size = len(json.dumps(data, ensure_ascii=False))
        print(f"    {dim.value:<5} {info.name:<8} {size:>4} chars")

    print(f"\n  Stage 2 produced {len(layer_results)} layer-specific JSONs:")
    for layer, data in layer_results.items():
        layer_name = LAYER_NAMES[layer]
        size = len(json.dumps(data, ensure_ascii=False))
        print(f"    {layer.value:<10} {layer_name:<8} {size:>5} chars")

    print(f"\n  === SAVED FILES ===")
    print(f"  Stage 1 constraints: {s1_path}")
    print(f"  Stage 2 all layers:  {s2_path}")
    for layer in layer_results:
        p = save_dir / f"demo_stage2_{layer.value}_{ts}.json"
        print(f"  Stage 2 {layer.value:<10}: {p}")

    print(f"\n{'='*70}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Stage 1: 1 seed -> 6 mask-filled constraint dimensions")
    print(f"  Stage 2: 6 constraints x 3 layer weights -> 3 structured JSONs")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
