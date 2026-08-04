"""Pipeline demo: seed -> weight lookup -> prompt assembly -> LLM generation -> 6-dim output.

Usage:
    cd backend
    python -m experiments.demo_pipeline "your_seed"
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
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
    WeightMatrixEntry,
)
from app.domains.creation.constraint.dimension_generator import (
    DimensionGenerator,
    DimensionPromptBuilder,
    WeightMatrixLoader,
)


def print_separator(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_weights(layer: CreationLayer, entry: WeightMatrixEntry) -> None:
    """打印某一层的权重表，带条形图。"""
    layer_name = LAYER_NAMES[layer]
    print(f"\n  层级: {layer.value} ({layer_name})")
    print(f"  {'维度':<8} {'权重':>4}  {'条形图':<22} {'标记':<12} {'描述'}")
    print(f"  {'-'*8} {'-'*4}  {'-'*22} {'-'*12} {'-'*30}")

    weight_dict = entry.to_dict()
    sorted_dims = sorted(weight_dict.items(), key=lambda x: x[1], reverse=True)

    for dim, weight in sorted_dims:
        info = DIMENSION_INFO[dim]
        bar = "#" * (weight // 5) + "." * (20 - weight // 5)

        if weight >= 25:
            marker = ">>> 主约束"
        elif weight <= 5:
            marker = "... 可省略"
        else:
            marker = ""

        print(f"  {dim.value:<8} {weight:>3}%  [{bar}] {marker:<12} {info.name}")

    print(f"\n  行和验证: {entry.sum()} {'OK' if entry.sum() == 100 else 'FAIL'}")


def print_prompt(system_prompt: str, user_prompt: str) -> None:
    """打印组装好的 prompt（截取关键部分）。"""
    print("\n  --- System Prompt (前600字) ---")
    # 截取核心段落
    lines = system_prompt.split("\n")
    for line in lines[:30]:
        print(f"  | {line}")
    if len(lines) > 30:
        print(f"  | ... ({len(lines) - 30} more lines)")

    print("\n  --- User Prompt ---")
    for line in user_prompt.split("\n"):
        print(f"  | {line}")


def print_dimensions(result: DimensionResultSet, weights: WeightMatrixEntry) -> None:
    """打印6维结构化结果，带权重对照。"""
    weight_dict = weights.to_dict()

    dim_map = {
        ConstraintDimension.RED: result.RED,
        ConstraintDimension.LAW: result.LAW,
        ConstraintDimension.ACT: result.ACT,
        ConstraintDimension.NAR: result.NAR,
        ConstraintDimension.WST: result.WST,
        ConstraintDimension.SOC: result.SOC,
    }

    # 按权重降序
    sorted_dims = sorted(weight_dict.items(), key=lambda x: x[1], reverse=True)

    for dim, weight in sorted_dims:
        info = DIMENSION_INFO[dim]
        data = dim_map[dim]
        content_json = json.dumps(data.model_dump(), ensure_ascii=False, indent=2)
        content_size = len(content_json)

        bar = "#" * (weight // 5) + "." * (20 - weight // 5)
        marker = ">>>" if weight >= 25 else ("..." if weight <= 5 else "   ")

        print(f"\n  {marker} {dim.value} ({info.name}) [{bar} {weight}%] [{content_size} chars]")
        print(f"      {info.desc}")

        # 打印每个维度的具体内容
        if dim == ConstraintDimension.RED:
            print(f"      forbidden: {data.forbidden}")
            print(f"      note: {data.note}")
        elif dim == ConstraintDimension.LAW:
            for i, rule in enumerate(data.rules):
                print(f"      rule[{i}]: {rule}")
            print(f"      mechanism: {data.mechanism}")
        elif dim == ConstraintDimension.ACT:
            for i, action in enumerate(data.actions):
                print(f"      action[{i}]:")
                for k, v in action.items():
                    print(f"        {k}: {v}")
        elif dim == ConstraintDimension.NAR:
            print(f"      style: {data.style}")
            print(f"      keywords: {data.keywords}")
            print(f"      tone: {data.tone}")
        elif dim == ConstraintDimension.WST:
            for i, effect in enumerate(data.effects):
                print(f"      effect[{i}]:")
                for k, v in effect.items():
                    print(f"        {k}: {v}")
        elif dim == ConstraintDimension.SOC:
            for i, relation in enumerate(data.relations):
                print(f"      relation[{i}]:")
                for k, v in relation.items():
                    print(f"        {k}: {v}")


async def main() -> None:
    # -----------------------------------------------------------------------
    # Step 0: 获取用户输入
    # -----------------------------------------------------------------------
    if len(sys.argv) > 1:
        seed_input = sys.argv[1]
        seed_description = sys.argv[2] if len(sys.argv) > 2 else ""
    else:
        print_separator("Step 0: 输入种子概念")
        seed_input = input("  请输入种子概念名称: ").strip()
        seed_description = input("  请输入种子描述 (可选, 回车跳过): ").strip()

    layer_input = input("  请输入创作层级 (world/region/scene/campaign/npc/asset): ").strip()
    intent = input("  请输入创作意图 (可选, 回车跳过): ").strip()

    try:
        layer = CreationLayer(layer_input)
    except ValueError:
        print(f"  无效层级: {layer_input}")
        print(f"  可选值: {[l.value for l in CreationLayer]}")
        return

    # -----------------------------------------------------------------------
    # Step 1: 权重查表
    # -----------------------------------------------------------------------
    print_separator(f"Step 1: 权重查表 — 层级={layer.value}")

    loader = WeightMatrixLoader()
    matrix = loader.load()
    weights = matrix.get_entry(layer)

    print_weights(layer, weights)

    # -----------------------------------------------------------------------
    # Step 2: Prompt 组装
    # -----------------------------------------------------------------------
    print_separator("Step 2: Prompt 组装")

    builder = DimensionPromptBuilder()
    system_prompt = builder.build_system_prompt(layer, weights, intent)
    user_prompt = builder.build_user_prompt(seed_input, seed_description)

    print_prompt(system_prompt, user_prompt)

    # -----------------------------------------------------------------------
    # Step 3: LLM 生成
    # -----------------------------------------------------------------------
    print_separator("Step 3: 调用 LLM 生成 6 维约束")

    config = load_provider_config()
    provider = create_provider(config)
    generator = DimensionGenerator(provider=provider, matrix_loader=loader)

    print(f"\n  Provider: {config.provider_type}")
    print(f"  Model: {config.model}")
    print(f"  Seed: {seed_input}")
    print(f"  Layer: {layer.value} ({LAYER_NAMES[layer]})")
    print(f"  Intent: {intent or '(默认)'}")
    print(f"\n  >>> 正在调用 LLM ...")

    start = time.time()
    result = await generator.generate(
        seed_input=seed_input,
        seed_description=seed_description,
        layer=layer,
        intent=intent,
    )
    elapsed = time.time() - start

    print(f"  <<< 完成! 耗时 {elapsed:.1f}s")

    # -----------------------------------------------------------------------
    # Step 4: 6 维结构化结果
    # -----------------------------------------------------------------------
    print_separator("Step 4: 6 维结构化结果 (按权重降序)")

    print_dimensions(result, weights)

    # -----------------------------------------------------------------------
    # Step 5: 密度差异分析
    # -----------------------------------------------------------------------
    print_separator("Step 5: 密度差异分析")

    dim_map = {
        ConstraintDimension.RED: result.RED,
        ConstraintDimension.LAW: result.LAW,
        ConstraintDimension.ACT: result.ACT,
        ConstraintDimension.NAR: result.NAR,
        ConstraintDimension.WST: result.WST,
        ConstraintDimension.SOC: result.SOC,
    }
    weight_dict = weights.to_dict()

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

    print(f"\n  高权重 (>=25%):")
    for name, w, s in high_sizes:
        print(f"    {name} (w={w}%) => {s} chars")
    print(f"    平均: {high_avg:.0f} chars")

    print(f"\n  低权重 (<=5%):")
    for name, w, s in low_sizes:
        print(f"    {name} (w={w}%) => {s} chars")
    print(f"    平均: {low_avg:.0f} chars")

    print(f"\n  密度比值: {ratio:.1f}x {'(PASS >=2.0x)' if ratio >= 2.0 else '(FAIL)'}")

    print(f"\n{'='*70}")
    print(f"  PIPELINE COMPLETE")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
