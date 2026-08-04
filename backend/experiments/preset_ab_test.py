"""Preset A/B test: raw dimension-fill vs preset-guided dimension-fill.

Compares LLM output quality with and without genre style guides.
Uses 4 seeds across 4 presets to see the difference.
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
from experiments.dimension_fill_experiment import (
    SEEDS,
    _USER_PROMPT_TEMPLATE,
    _try_parse_json,
    ALL_DIMS,
)
from experiments.trpg_presets import build_system_prompt, PRESETS

# 4 seeds × 4 presets — match seed genre to preset genre
TEST_PAIRS = [
    ("seed_01", "lovecraftian_horror"),   # asset "水晶祭坛" → 克苏鲁风格
    ("seed_03", "dark_fantasy_dungeon"),  # story "失落祭司" → 黑暗奇幻风格
    ("seed_05", "wasteland_survival"),    # event "夜狼袭击" → 废土生存风格
    ("seed_04", "court_intrigue"),        # story "叛逃科学家" → 权谋阴谋风格
]

# Original system prompt (no style guide) from dimension_fill_experiment
from experiments.dimension_fill_experiment import _SYSTEM_PROMPT as RAW_SYSTEM_PROMPT


async def fill_seed(
    provider: LLMProvider,
    seed: dict[str, Any],
    system_prompt: str,
    mode_label: str,
) -> dict[str, Any]:
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
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    start = time.time()
    result: dict[str, Any] = {
        "seed_id": seed["id"],
        "mode": mode_label,
        "filled_dimensions": {},
        "elapsed_seconds": 0.0,
        "error": None,
    }

    try:
        try:
            raw_output = await asyncio.wait_for(
                provider.chat_json(messages), timeout=60.0
            )
            filled = raw_output if isinstance(raw_output, dict) else {}
        except Exception:
            raw_str = await asyncio.wait_for(
                provider.chat(messages), timeout=60.0
            )
            filled = _try_parse_json(raw_str)
        result["filled_dimensions"] = filled
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    result["elapsed_seconds"] = round(time.time() - start, 2)
    return result


async def main() -> None:
    config = load_provider_config()
    provider = create_provider(config)
    print(f"Provider: {config.provider_type} | Model: {config.model}", flush=True)
    print(f"Test pairs: {len(TEST_PAIRS)} seeds x 2 modes (raw vs preset)\n", flush=True)

    seed_map = {s["id"]: s for s in SEEDS}
    results: list[dict[str, Any]] = []

    for i, (seed_id, preset_id) in enumerate(TEST_PAIRS, 1):
        seed = seed_map[seed_id]
        preset_name = next(p["name"] for p in PRESETS if p["id"] == preset_id)

        print(f"[{i}/{len(TEST_PAIRS)}] {seed_id} x {preset_id}", flush=True)
        print(f"  Seed: {seed['raw_input'][:30]} | Preset: {preset_name}", flush=True)

        # --- RAW (no style guide) ---
        print(f"  RAW ...", flush=True)
        r_raw = await fill_seed(provider, seed, RAW_SYSTEM_PROMPT, "raw")
        results.append({**r_raw, "preset_id": preset_id})
        ok = "OK" if r_raw["filled_dimensions"] and not r_raw["error"] else "FAIL"
        print(f"    [{ok}] {r_raw['elapsed_seconds']}s", flush=True)
        await asyncio.sleep(3)

        # --- PRESET (with style guide) ---
        preset_prompt = build_system_prompt(preset_id)
        print(f"  PRESET ...", flush=True)
        r_pre = await fill_seed(provider, seed, preset_prompt, "preset")
        results.append({**r_pre, "preset_id": preset_id})
        ok = "OK" if r_pre["filled_dimensions"] and not r_pre["error"] else "FAIL"
        print(f"    [{ok}] {r_pre['elapsed_seconds']}s", flush=True)
        await asyncio.sleep(3)
        print(flush=True)

    # Save results
    output_dir = _BACKEND_DIR / "experiments" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    json_path = output_dir / f"preset_ab_test_{timestamp}.json"
    json_path.write_text(
        json.dumps(
            {
                "experiment": "preset_ab_test",
                "timestamp": timestamp,
                "provider": config.provider_type,
                "model": config.model,
                "test_pairs": TEST_PAIRS,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[SAVED] {json_path}", flush=True)

    # Generate markdown report
    report_path = output_dir / f"preset_ab_report_{timestamp}.md"
    _generate_report(results, report_path, config.model)
    print(f"[SAVED] {report_path}", flush=True)


def _generate_report(
    results: list[dict[str, Any]],
    path: Path,
    model: str,
) -> None:
    seed_map = {s["id"]: s for s in SEEDS}

    lines = [
        "# Preset A/B Test Report: Raw vs Style-Guided",
        "",
        f"- **Model**: {model}",
        f"- **Date**: {datetime.now(timezone.utc).isoformat()}",
        f"- **Pairs**: {len(TEST_PAIRS)}",
        "",
        "## Goal",
        "",
        "Compare dimension-fill output quality:",
        "- **RAW**: Generic system prompt (no genre guide)",
        "- **PRESET**: Genre-specific voice + lexicon + mapping logic",
        "",
        "Check if preset-guided output uses correct vocabulary, tone, and structure.",
        "",
        "---",
        "",
    ]

    # Group by seed_id
    i = 0
    while i < len(results):
        r_raw = results[i]
        r_pre = results[i + 1] if i + 1 < len(results) else None
        i += 2

        seed_id = r_raw["seed_id"]
        seed = seed_map.get(seed_id, {})
        preset_id = r_raw.get("preset_id", "?")
        preset_name = next((p["name"] for p in PRESETS if p["id"] == preset_id), preset_id)

        lines.append(f"## {seed_id} x {preset_name}")
        lines.append(f"**Seed**: {seed.get('raw_input', seed_id)} ({seed.get('seed_type', '?')})")
        lines.append("")

        # RAW
        lines.append("### RAW (no style guide)")
        if r_raw["error"]:
            lines.append(f"ERROR: `{r_raw['error']}`")
        elif r_raw["filled_dimensions"]:
            lines.append(f"Time: {r_raw['elapsed_seconds']}s")
            lines.append("```json")
            lines.append(json.dumps(r_raw["filled_dimensions"], ensure_ascii=False, indent=2))
            lines.append("```")
        else:
            lines.append("Empty response")
        lines.append("")

        # PRESET
        if r_pre:
            lines.append(f"### PRESET ({preset_name})")
            if r_pre["error"]:
                lines.append(f"ERROR: `{r_pre['error']}`")
            elif r_pre["filled_dimensions"]:
                lines.append(f"Time: {r_pre['elapsed_seconds']}s")
                lines.append("```json")
                lines.append(json.dumps(r_pre["filled_dimensions"], ensure_ascii=False, indent=2))
                lines.append("```")
            else:
                lines.append("Empty response")
        lines.append("")
        lines.append("---")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
