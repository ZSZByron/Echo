"""Run the full pipeline for 3 layers with a custom seed."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import io
from pathlib import Path
from typing import Any

# Force UTF-8
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
from app.ai.provider import create_provider
from app.models.dimension import (
    ConstraintDimension,
    CreationLayer,
    DIMENSION_INFO,
    LAYER_NAMES,
    DimensionResultSet,
    WeightMatrixEntry,
)
from app.domains.creation.constraint.dimension_generator import (
    DimensionGenerator,
    DimensionPromptBuilder,
    WeightMatrixLoader,
)

# ============================================================
# YOUR INPUT
# ============================================================
SEED_INPUT = "\u5728\u4e16\u56096\u533a\uff0c\u6709\u4e00\u4e2a\u6b7b\u4eba\u5934\uff0c\u6bcf\u5f53\u6709\u4eba\u89c1\u5230\uff0c\u5934\u5c31\u6ca1\u4e86\uff0c\u6d88\u9664\u6076\u7075!"
SEED_DESC = "\u7075\u5f02\u89c4\u5219\u602a\u8c08\u4e16\u754c\uff0c\u8c03\u67e5\u5458\u6e38\u8d70\u5728\u751f\u6b7b\u4e2d\uff0c\u62d4\u9664\u6076\u7075\uff0c\u7834\u89e3\u89c4\u5219"
LAYERS = [CreationLayer.CAMPAIGN, CreationLayer.NPC, CreationLayer.ASSET]
INTENT = "\u8c03\u67e5\u5458\u88ab\u73a9\u5f04\u7684\u6b7b\u53bb\u6d3b\u6765\uff0c\u9b3c\u4e8b\u7684\u80cc\u540e\u662f\u4eba\u4e8b\uff0c\u9690\u85cf\u5728\u5e55\u540e\u7684boss\uff0c\u89c4\u5219\u5bf9\u6297\u89c4\u5219!"


def sep(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def show_weights(layer: CreationLayer, entry: WeightMatrixEntry) -> None:
    layer_name = LAYER_NAMES[layer]
    print(f"\n  Layer: {layer.value} ({layer_name})")
    print(f"  {'Dim':<6} {'Wt':>3}  {'Bar':<22} {'Mark':<12} {'Name'}")
    print(f"  {'-'*6} {'-'*3}  {'-'*22} {'-'*12} {'-'*20}")

    weight_dict = entry.to_dict()
    sorted_dims = sorted(weight_dict.items(), key=lambda x: x[1], reverse=True)

    for dim, weight in sorted_dims:
        info = DIMENSION_INFO[dim]
        bar = "#" * (weight // 5) + "." * (20 - weight // 5)
        if weight >= 25:
            marker = ">>> MAIN"
        elif weight <= 5:
            marker = "... skip"
        else:
            marker = ""
        print(f"  {dim.value:<6} {weight:>3}% [{bar}] {marker:<12} {info.name}")
    print(f"\n  Sum check: {entry.sum()} {'OK' if entry.sum()==100 else 'FAIL'}")


def show_prompt(system_prompt: str, user_prompt: str) -> None:
    print("\n  --- System Prompt (excerpt) ---")
    lines = system_prompt.split("\n")
    for line in lines[:35]:
        print(f"  | {line}")
    if len(lines) > 35:
        print(f"  | ... ({len(lines)-35} more lines)")
    print("\n  --- User Prompt ---")
    for line in user_prompt.split("\n"):
        print(f"  | {line}")


def show_dims(result: DimensionResultSet, weights: WeightMatrixEntry) -> None:
    weight_dict = weights.to_dict()
    dim_map = {
        ConstraintDimension.RED: result.RED,
        ConstraintDimension.LAW: result.LAW,
        ConstraintDimension.ACT: result.ACT,
        ConstraintDimension.NAR: result.NAR,
        ConstraintDimension.WST: result.WST,
        ConstraintDimension.SOC: result.SOC,
    }
    sorted_dims = sorted(weight_dict.items(), key=lambda x: x[1], reverse=True)

    for dim, weight in sorted_dims:
        info = DIMENSION_INFO[dim]
        data = dim_map[dim]
        content_size = len(json.dumps(data.model_dump(), ensure_ascii=False))
        bar = "#" * (weight // 5) + "." * (20 - weight // 5)
        marker = ">>>" if weight >= 25 else ("..." if weight <= 5 else "   ")

        print(f"\n  {marker} {dim.value} ({info.name}) [{bar} {weight}%] [{content_size} chars]")
        print(f"      {info.desc}")

        if dim == ConstraintDimension.RED:
            for item in data.forbidden:
                print(f"      [FORBIDDEN] {item}")
            if data.note:
                print(f"      [NOTE] {data.note}")
        elif dim == ConstraintDimension.LAW:
            for i, rule in enumerate(data.rules):
                print(f"      [RULE {i}] {rule}")
            if data.mechanism:
                print(f"      [MECHANISM] {data.mechanism}")
        elif dim == ConstraintDimension.ACT:
            for i, action in enumerate(data.actions):
                print(f"      [ACTION {i}]")
                for k, v in action.items():
                    print(f"        {k}: {v}")
        elif dim == ConstraintDimension.NAR:
            print(f"      [STYLE] {data.style}")
            print(f"      [KEYWORDS] {data.keywords}")
            print(f"      [TONE] {data.tone}")
        elif dim == ConstraintDimension.WST:
            for i, effect in enumerate(data.effects):
                print(f"      [EFFECT {i}]")
                for k, v in effect.items():
                    print(f"        {k}: {v}")
        elif dim == ConstraintDimension.SOC:
            for i, rel in enumerate(data.relations):
                print(f"      [RELATION {i}]")
                for k, v in rel.items():
                    print(f"        {k}: {v}")


def show_density(result: DimensionResultSet, weights: WeightMatrixEntry) -> dict[str, Any]:
    weight_dict = weights.to_dict()
    dim_map = {
        ConstraintDimension.RED: result.RED,
        ConstraintDimension.LAW: result.LAW,
        ConstraintDimension.ACT: result.ACT,
        ConstraintDimension.NAR: result.NAR,
        ConstraintDimension.WST: result.WST,
        ConstraintDimension.SOC: result.SOC,
    }
    high_sizes = []
    low_sizes = []
    for dim, weight in weight_dict.items():
        content_size = len(json.dumps(dim_map[dim].model_dump(), ensure_ascii=False))
        if weight >= 25:
            high_sizes.append((dim.value, weight, content_size))
        elif weight <= 5:
            low_sizes.append((dim.value, weight, content_size))

    high_avg = sum(s for _, _, s in high_sizes) / len(high_sizes) if high_sizes else 0
    low_avg = sum(s for _, _, s in low_sizes) / len(low_sizes) if low_sizes else 0
    ratio = high_avg / low_avg if low_avg > 0 else 0

    print(f"\n  HIGH (>=25%): ", end="")
    for n, w, s in high_sizes:
        print(f"{n}={s}ch  ", end="")
    print(f"| avg={high_avg:.0f}")

    print(f"  LOW  (<=5%):  ", end="")
    for n, w, s in low_sizes:
        print(f"{n}={s}ch  ", end="")
    print(f"| avg={low_avg:.0f}")

    print(f"\n  >>> DENSITY RATIO: {ratio:.1f}x {'PASS(>=2.0)' if ratio>=2.0 else 'FAIL'}")
    return {"high_avg": high_avg, "low_avg": low_avg, "ratio": ratio}


async def main() -> None:
    sep("SEED INPUT")
    print(f"  Seed:    {SEED_INPUT}")
    print(f"  Desc:    {SEED_DESC}")
    print(f"  Layers:  {[l.value for l in LAYERS]}")
    print(f"  Intent:  {INTENT}")

    # Load config
    config = load_provider_config()
    loader = WeightMatrixLoader()
    builder = DimensionPromptBuilder()
    matrix = loader.load()

    sep("WEIGHT MATRIX (6 layers x 6 dims)")
    for layer in CreationLayer:
        entry = matrix.get_entry(layer)
        w = entry.to_dict()
        print(f"  {layer.value:<10} " + "  ".join(f"{d.value}:{w[d]:>2}" for d in ConstraintDimension) + f"  = {entry.sum()}")

    # Provider
    provider = create_provider(config)
    generator = DimensionGenerator(provider=provider, matrix_loader=loader)

    all_density = []

    for idx, layer in enumerate(LAYERS):
        sep(f"RUN {idx+1}/{len(LAYERS)}: {layer.value} ({LAYER_NAMES[layer]})")

        # Step 1: Weights
        weights = matrix.get_entry(layer)
        print("\n  --- STEP 1: Weight Lookup ---")
        show_weights(layer, weights)

        # Step 2: Prompt
        print("\n  --- STEP 2: Prompt Assembly ---")
        system_prompt = builder.build_system_prompt(layer, weights, INTENT)
        user_prompt = builder.build_user_prompt(SEED_INPUT, SEED_DESC)
        show_prompt(system_prompt, user_prompt)

        # Step 3: LLM
        print(f"\n  --- STEP 3: LLM Call ---")
        print(f"  Provider: {config.provider_type}")
        print(f"  Model:    {config.model}")
        print(f"  >>> Calling LLM ...")

        start = time.time()
        result = await generator.generate(
            seed_input=SEED_INPUT,
            seed_description=SEED_DESC,
            layer=layer,
            intent=INTENT,
        )
        elapsed = time.time() - start
        print(f"  <<< Done in {elapsed:.1f}s")

        # Step 4: Results
        print(f"\n  --- STEP 4: 6-Dimension Output (by weight desc) ---")
        show_dims(result, weights)

        # Step 5: Density
        print(f"\n  --- STEP 5: Density Analysis ---")
        d = show_density(result, weights)
        d["layer"] = layer.value
        all_density.append(d)

    # Summary
    sep("CROSS-LAYER SUMMARY")
    print(f"\n  {'Layer':<10} {'High avg':>10} {'Low avg':>10} {'Ratio':>8} {'Verdict':>8}")
    print(f"  {'-'*10} {'-'*10} {'-'*10} {'-'*8} {'-'*8}")
    for d in all_density:
        verdict = "PASS" if d["ratio"] >= 2.0 else "FAIL"
        print(f"  {d['layer']:<10} {d['high_avg']:>10.0f} {d['low_avg']:>10.0f} {d['ratio']:>7.1f}x {verdict:>8}")

    avg_ratio = sum(d["ratio"] for d in all_density) / len(all_density)
    print(f"\n  Average ratio: {avg_ratio:.1f}x")

    print(f"\n{'='*70}")
    print(f"  PIPELINE COMPLETE - {len(LAYERS)} runs")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
