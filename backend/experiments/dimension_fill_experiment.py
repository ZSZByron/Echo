"""Bidirectional dimension fill experiment.

Tests core hypothesis: Can an LLM correctly infer missing world dimensions
from a single-dimension seed concept?

Uses GLM-style blank infilling approach:
  - Known dimension = Part A (bidirectional context)
  - Missing dimensions = Part B (autoregressive generation targets)

Experiment:
  - 10 seed concepts covering 5 seed types (asset/story/event/culture/constraint)
  - Each seed provides exactly ONE dimension
  - LLM must fill the other FOUR dimensions
  - Output structured JSON for human evaluation

Usage:
  cd H:\\UGC\\backend
  .venv\\Scripts\\python -m experiments.dimension_fill_experiment

Output:
  experiments/results/dimension_fill_results.json
  experiments/results/dimension_fill_report.md
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — ensure backend/ is on sys.path for app imports
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Load .env manually (avoid python-dotenv dependency)
_ENV_FILE = _BACKEND_DIR / ".env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _, _val = _line.partition("=")
            _key = _key.strip()
            _val = _val.split("#")[0].strip()  # strip inline comments
            if _key and _key not in os.environ:
                os.environ[_key] = _val

from app.ai.config import load_provider_config
from app.ai.provider import LLMProvider, create_provider

# ---------------------------------------------------------------------------
# Experiment seeds — 10 concepts covering 5 seed types
# ---------------------------------------------------------------------------

SEEDS: list[dict[str, Any]] = [
    # --- Asset seeds (输入一个资产，反推其他维度) ---
    {
        "id": "seed_01",
        "seed_type": "asset",
        "raw_input": "古代水晶祭坛",
        "known_dimension": {
            "type": "asset",
            "content": {
                "name": "古代水晶祭坛",
                "description": "由整块水晶雕琢而成的祭坛，表面刻有星辰图案，散发着微弱的蓝色光芒",
                "tags": ["altar", "crystal", "ancient", "ritual", "glowing"],
            },
        },
    },
    {
        "id": "seed_02",
        "seed_type": "asset",
        "raw_input": "锈蚀的机械守护者",
        "known_dimension": {
            "type": "asset",
            "content": {
                "name": "锈蚀的机械守护者",
                "description": "一具古老的青铜机械人偶，关节处覆盖着铜绿，眼中仍然闪烁着红色光芒",
                "tags": ["robot", "ancient", "bronze", "guardian", "rusted"],
            },
        },
    },
    # --- Story seeds (输入一段剧情，反推其他维度) ---
    {
        "id": "seed_03",
        "seed_type": "story",
        "raw_input": "一个失落祭司的遗愿任务",
        "known_dimension": {
            "type": "story",
            "content": {
                "name": "失落祭司的遗愿",
                "description": "玩家发现一个已故祭司的灵魂，他请求玩家完成他生前未完成的仪式",
                "type": "quest",
                "key_elements": ["priest_ghost", "unfinished_ritual", "last_wish"],
            },
        },
    },
    {
        "id": "seed_04",
        "seed_type": "story",
        "raw_input": "帮助叛逃科学家偷回她的研究数据",
        "known_dimension": {
            "type": "story",
            "content": {
                "name": "盗回研究数据",
                "description": "一个叛逃的科学家请求玩家潜入她 former 实验室，偷回被没收的研究数据",
                "type": "quest",
                "key_elements": ["scientist_defector", "stealth_infiltration", "research_data"],
            },
        },
    },
    # --- Event seeds (输入一个事件，反推其他维度) ---
    {
        "id": "seed_05",
        "seed_type": "event",
        "raw_input": "夜晚森林出现狼群袭击",
        "known_dimension": {
            "type": "event",
            "content": {
                "name": "夜狼袭击",
                "description": "夜幕降临时，森林中涌出异常凶猛的狼群攻击旅人",
                "trigger": {"type": "time", "condition": "night", "location": "forest"},
                "event_type": "combat",
            },
        },
    },
    {
        "id": "seed_06",
        "seed_type": "event",
        "raw_input": "暴雨夜废弃矿洞传来哭声",
        "known_dimension": {
            "type": "event",
            "content": {
                "name": "矿洞哭声",
                "description": "暴雨之夜，废弃矿洞深处传来阵阵哭泣声，引人探查",
                "trigger": {"type": "weather", "condition": "heavy_rain", "location": "abandoned_mine"},
                "event_type": "exploration",
            },
        },
    },
    # --- Culture seeds (输入文明概念，反推其他维度) ---
    {
        "id": "seed_07",
        "seed_type": "culture",
        "raw_input": "一个崇拜星辰的古代文明",
        "known_dimension": {
            "type": "culture",
            "content": {
                "name": "星辰文明",
                "values": ["cosmic_harmony", "celestial_wisdom", "light_over_darkness"],
                "aesthetic_principles": ["geometric_patterns", "crystalline_materials", "blue_gold_palette"],
            },
        },
    },
    {
        "id": "seed_08",
        "seed_type": "culture",
        "raw_input": "崇尚生物改造的地下社会",
        "known_dimension": {
            "type": "culture",
            "content": {
                "name": "地下改造者",
                "values": ["evolution_through_modification", "survival_at_any_cost", "rejection_of_natural_order"],
                "aesthetic_principles": ["bioluminescence", "organic_metallic_fusion", "asymmetric_designs"],
            },
        },
    },
    # --- Constraint seeds (输入约束规则，反推其他维度) ---
    {
        "id": "seed_09",
        "seed_type": "constraint",
        "raw_input": "禁止使用任何金属材质的武器",
        "known_dimension": {
            "type": "constraint",
            "content": {
                "rule": "所有武器必须是非金属材质（木、骨、石、水晶）",
                "type": "hard",
                "priority": 100,
                "applicable_types": ["weapon", "armor", "tool"],
            },
        },
    },
    {
        "id": "seed_10",
        "seed_type": "constraint",
        "raw_input": "所有建筑必须悬浮于地面之上",
        "known_dimension": {
            "type": "constraint",
            "content": {
                "rule": "所有建筑结构必须悬浮在地面以上至少3米，通过反重力或磁悬浮支撑",
                "type": "hard",
                "priority": 90,
                "applicable_types": ["building", "structure", "environment"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# GLM-style Blank Infilling Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
你是一个世界构建引擎。你的任务是基于一个已知的"种子维度"，\
推断并生成一个完整游戏世界所需的其余四个维度。

## 五个维度

1. **asset（资产）**：游戏中的视觉对象（道具、场景元素、角色外观）
2. **story（剧情）**：叙事任务、主线/支线、角色动机
3. **event（事件）**：动态触发的事件（战斗、探索、社交）
4. **culture（文化）**：文明体系、价值观念、美学原则
5. **constraint（约束）**：世界规则、硬/软约束、限制条件

## 你的工作方式

用户会给你一个"种子维度"（已知），其余四个维度是空白 [MASK]。\
你需要基于种子的语义，推断最合理的填充。

推断原则：
- **语义一致**：生成的维度必须与种子有逻辑关联
- **互相支撑**：五个维度应该构成一个自洽的世界观
- **具体可玩**：不要泛泛而谈，给出具体的名称、描述、触发条件
- **创新但有约束**：可以创新，但不能与种子矛盾

## 输出格式

输出严格的 JSON，包含四个缺失维度的填充：

```json
{
  "asset": {
    "name": "string",
    "description": "视觉描述",
    "tags": ["tag1", "tag2"]
  },
  "story": {
    "name": "任务名称",
    "description": "剧情描述",
    "type": "quest | main_quest | side_quest",
    "key_elements": ["element1", "element2"]
  },
  "event": {
    "name": "事件名称",
    "description": "事件描述",
    "trigger": {"type": "time | location | state | weather", "condition": "..."},
    "event_type": "combat | exploration | social | quest"
  },
  "culture": {
    "name": "文化名称",
    "values": ["value1", "value2"],
    "aesthetic_principles": ["principle1", "principle2"]
  },
  "constraint": {
    "rule": "规则描述",
    "type": "hard | soft",
    "priority": 0-100,
    "applicable_types": ["type1"]
  }
}
```

只输出 JSON，不要输出其他内容。对于被填充的四个维度，每个维度\
都必须有完整的内容。不要输出种子维度（已知的那一个）。
"""

_USER_PROMPT_TEMPLATE = """\
## 种子维度（已知信息）

**种子类型**: {seed_type}
**原始输入**: {raw_input}

**已知维度 [{known_dim}]**:
```json
{known_content}
```

## 请填充以下四个缺失维度

基于上面的种子维度，推断并生成其余四个维度的内容。
输出 JSON，只包含四个缺失维度的填充（不要包含已知的维度）。
"""


# ---------------------------------------------------------------------------
# JSON repair (same strategy as graph_extractor)
# ---------------------------------------------------------------------------

import re

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def _try_parse_json(raw: str) -> dict[str, Any]:
    """Parse LLM response as JSON with repair strategies."""
    # 1. Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. Strip code fences
    fenced = _CODE_FENCE_RE.findall(raw)
    for candidate in fenced:
        try:
            return json.loads(candidate.strip())
        except json.JSONDecodeError:
            continue

    # 3. Brace extraction
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(raw[first_brace : last_brace + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Failed to parse LLM response as JSON. "
        f"Raw (first 500 chars): {raw[:500]}"
    )


# ---------------------------------------------------------------------------
# Experiment runner
# ---------------------------------------------------------------------------

# All five dimension types
ALL_DIMS = {"asset", "story", "event", "culture", "constraint"}


async def fill_dimensions_for_seed(
    provider: LLMProvider, seed: dict[str, Any]
) -> dict[str, Any]:
    """Fill 4 missing dimensions for a single seed using LLM.

    Returns:
        Dict with keys: seed_id, seed_type, raw_input, known_dimension,
        filled_dimensions, raw_llm_response, elapsed_seconds, error
    """
    known = seed["known_dimension"]
    known_dim = known["type"]
    known_content = json.dumps(known["content"], ensure_ascii=False, indent=2)

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        seed_type=seed["seed_type"],
        raw_input=seed["raw_input"],
        known_dim=known_dim,
        known_content=known_content,
    )

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    start = time.time()
    result: dict[str, Any] = {
        "seed_id": seed["id"],
        "seed_type": seed["seed_type"],
        "raw_input": seed["raw_input"],
        "known_dimension": known_dim,
        "missing_dimensions": sorted(ALL_DIMS - {known_dim}),
        "filled_dimensions": {},
        "raw_llm_response": "",
        "elapsed_seconds": 0.0,
        "error": None,
    }

    try:
        # Try chat_json first, fallback to chat, with 60s per-request timeout
        try:
            raw_output = await asyncio.wait_for(
                provider.chat_json(messages), timeout=60.0
            )
            raw_str = json.dumps(raw_output, ensure_ascii=False)
            filled = raw_output if isinstance(raw_output, dict) else _try_parse_json(raw_str)
        except asyncio.TimeoutError:
            raise RuntimeError("LLM request timed out after 60s")
        except Exception:
            raw_str = await asyncio.wait_for(
                provider.chat(messages), timeout=60.0
            )
            filled = _try_parse_json(raw_str)

        result["filled_dimensions"] = filled
        result["raw_llm_response"] = raw_str

    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["raw_llm_response"] = raw_str if "raw_str" in dir() else ""

    result["elapsed_seconds"] = round(time.time() - start, 2)
    return result


async def run_experiment(output_dir: Path) -> None:
    """Run dimension fill experiment for all 10 seeds."""
    print("=" * 70)
    print("  Bidirectional Dimension Fill Experiment")
    print("  Core hypothesis: Can LLM infer 4 missing world dimensions")
    print("  from a single seed dimension?")
    print("=" * 70)

    # Init provider
    config = load_provider_config()
    provider = create_provider(config)
    print(f"\n  Provider: {config.provider_type} | Model: {config.model}")
    print(f"  Seeds: {len(SEEDS)}")

    # Run each seed sequentially (avoid rate limits)
    results: list[dict[str, Any]] = []
    for i, seed in enumerate(SEEDS, 1):
        print(f"\n  [{i}/{len(SEEDS)}] {seed['id']}: {seed['raw_input']}", flush=True)
        print(f"       Seed type: {seed['seed_type']}, Known dim: {seed['known_dimension']['type']}", flush=True)

        result = await fill_dimensions_for_seed(provider, seed)
        results.append(result)

        if result["error"]:
            print(f"       [FAIL] ERROR: {result['error']}", flush=True)
        else:
            filled_keys = list(result["filled_dimensions"].keys())
            print(f"       [OK] Filled dims: {filled_keys} ({result['elapsed_seconds']}s)", flush=True)

    # Save JSON results
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    json_path = output_dir / f"dimension_fill_results_{timestamp}.json"
    json_path.write_text(
        json.dumps(
            {
                "experiment": "dimension_fill",
                "timestamp": timestamp,
                "provider": config.provider_type,
                "model": config.model,
                "total_seeds": len(SEEDS),
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n  [SAVED] JSON results: {json_path}")

    # Generate markdown report
    report_path = output_dir / f"dimension_fill_report_{timestamp}.md"
    _generate_report(results, report_path, config.provider_type, config.model)
    print(f"  [SAVED] Markdown report: {report_path}")

    # Print summary
    _print_summary(results)


def _generate_report(
    results: list[dict[str, Any]], path: Path, provider: str, model: str
) -> None:
    """Generate a human-readable markdown report for evaluation."""
    lines = [
        "# Dimension Fill Experiment Report",
        "",
        f"- **Provider**: {provider} ({model})",
        f"- **Date**: {datetime.now(timezone.utc).isoformat()}",
        f"- **Total Seeds**: {len(results)}",
        "",
        "## Evaluation Instructions",
        "",
        "For each seed, rate the 4 filled dimensions on a 1-5 scale:",
        "- **5**: Excellent — perfectly consistent, creative, directly usable",
        "- **4**: Good — mostly consistent, minor adjustments needed",
        "- **3**: Okay — plausible but generic, needs significant work",
        "- **2**: Poor — weak connection to seed, mostly irrelevant",
        "- **1**: Bad — contradictory or nonsensical",
        "",
        "Average score ≥ 3.5 → core hypothesis confirmed.",
        "",
        "---",
        "",
    ]

    for r in results:
        lines.append(f"## {r['seed_id']}: {r['raw_input']}")
        lines.append("")
        lines.append(f"**Seed type**: `{r['seed_type']}` | **Known dimension**: `{r['known_dimension']}`")
        lines.append("")

        if r["error"]:
            lines.append(f"⚠️ **ERROR**: `{r['error']}`")
            lines.append("")
            continue

        known = next(s for s in SEEDS if s["id"] == r["seed_id"])
        lines.append("### Known (Seed)")
        lines.append("```json")
        lines.append(json.dumps(known["known_dimension"]["content"], ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

        lines.append("### Filled Dimensions")
        lines.append("```json")
        lines.append(json.dumps(r["filled_dimensions"], ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

        lines.append("### Evaluation")
        lines.append("| Dimension | Score (1-5) | Notes |")
        lines.append("|-----------|-------------|-------|")
        for dim in r["missing_dimensions"]:
            lines.append(f"| {dim} | | |")
        lines.append("")
        lines.append("**Overall**: ___ / 5")
        lines.append("")
        lines.append("---")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _print_summary(results: list[dict[str, Any]]) -> None:
    """Print experiment summary to console."""
    success = sum(1 for r in results if not r["error"])
    failed = len(results) - success
    avg_time = sum(r["elapsed_seconds"] for r in results) / len(results) if results else 0

    print("\n" + "=" * 70)
    print("  EXPERIMENT SUMMARY")
    print("=" * 70)
    print(f"  Total seeds:    {len(results)}")
    print(f"  Success:        {success}")
    print(f"  Failed:         {failed}")
    print(f"  Avg time/seed:  {avg_time:.1f}s")
    print(f"  Total time:     {sum(r['elapsed_seconds'] for r in results):.1f}s")
    print()
    print("\n  >> Next step: Open the markdown report and rate each seed's")
    print("     filled dimensions on a 1-5 scale.")
    print("     Average ≥ 3.5 confirms the core hypothesis.")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _output_dir = _BACKEND_DIR / "experiments" / "results"
    asyncio.run(run_experiment(_output_dir))
