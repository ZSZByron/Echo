"""A/B comparison: thinking mode ON vs OFF for DeepSeek V4-Pro.

Tests whether disabling thinking mode improves JSON output reliability
and compares quality of dimension fill results.

Usage:
  cd H:\\UGC\\backend
  .venv\\Scripts\\python -m experiments.thinking_ab_test
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

# Load .env
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

# Import seeds and prompt from the main experiment
from experiments.dimension_fill_experiment import (
    SEEDS,
    _SYSTEM_PROMPT,
    _USER_PROMPT_TEMPLATE,
    _try_parse_json,
    ALL_DIMS,
)


async def fill_one_seed(
    provider: LLMProvider,
    seed: dict[str, Any],
    thinking: bool,
) -> dict[str, Any]:
    """Fill dimensions for a single seed with thinking on or off."""
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
    label = "ON" if thinking else "OFF"
    result: dict[str, Any] = {
        "seed_id": seed["id"],
        "seed_type": seed["seed_type"],
        "raw_input": seed["raw_input"],
        "thinking_mode": label,
        "filled_dimensions": {},
        "elapsed_seconds": 0.0,
        "error": None,
    }

    try:
        # Pass enable_thinking via extra_body
        extra = {"extra_body": {"enable_thinking": thinking}}
        try:
            raw_output = await asyncio.wait_for(
                provider.chat_json(messages, **extra), timeout=60.0
            )
            filled = raw_output if isinstance(raw_output, dict) else {}
            result["filled_dimensions"] = filled
        except asyncio.TimeoutError:
            raise RuntimeError("Timeout 60s")
        except Exception:
            # Fallback to chat
            raw_str = await asyncio.wait_for(
                provider.chat(messages, **extra), timeout=60.0
            )
            filled = _try_parse_json(raw_str)
            result["filled_dimensions"] = filled
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"

    result["elapsed_seconds"] = round(time.time() - start, 2)
    return result


async def run_ab_test(output_dir: Path) -> None:
    """Run A/B test: all 10 seeds × thinking ON vs OFF."""
    config = load_provider_config()
    provider = create_provider(config)
    print(f"Provider: {config.provider_type} | Model: {config.model}", flush=True)
    print(f"Seeds: {len(SEEDS)} × 2 modes = {len(SEEDS) * 2} calls\n", flush=True)

    results_on: list[dict[str, Any]] = []
    results_off: list[dict[str, Any]] = []

    for i, seed in enumerate(SEEDS, 1):
        # --- Thinking OFF first (faster, less likely to timeout) ---
        print(f"[{i}/{len(SEEDS)}] {seed['id']} (OFF): {seed['raw_input'][:30]}", flush=True)
        r_off = await fill_one_seed(provider, seed, thinking=False)
        results_off.append(r_off)
        if r_off["error"]:
            print(f"  [FAIL] {r_off['error']}", flush=True)
        else:
            keys = list(r_off["filled_dimensions"].keys())
            print(f"  [OK] dims={keys} ({r_off['elapsed_seconds']}s)", flush=True)

        await asyncio.sleep(3)  # rate limit safety

        # --- Thinking ON ---
        print(f"[{i}/{len(SEEDS)}] {seed['id']} (ON):  {seed['raw_input'][:30]}", flush=True)
        r_on = await fill_one_seed(provider, seed, thinking=True)
        results_on.append(r_on)
        if r_on["error"]:
            print(f"  [FAIL] {r_on['error']}", flush=True)
        else:
            keys = list(r_on["filled_dimensions"].keys())
            print(f"  [OK] dims={keys} ({r_on['elapsed_seconds']}s)", flush=True)

        await asyncio.sleep(3)

    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = output_dir / f"thinking_ab_test_{timestamp}.json"
    json_path.write_text(
        json.dumps(
            {
                "experiment": "thinking_ab_test",
                "timestamp": timestamp,
                "provider": config.provider_type,
                "model": config.model,
                "results_thinking_on": results_on,
                "results_thinking_off": results_off,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n[SAVED] {json_path}", flush=True)

    # Comparison report
    report_path = output_dir / f"thinking_ab_report_{timestamp}.md"
    _generate_comparison_report(results_on, results_off, report_path, config.model)
    print(f"[SAVED] {report_path}", flush=True)

    # Print summary
    _print_summary(results_on, results_off)


def _generate_comparison_report(
    results_on: list[dict[str, Any]],
    results_off: list[dict[str, Any]],
    path: Path,
    model: str,
) -> None:
    """Generate side-by-side comparison markdown."""
    lines = [
        "# Thinking Mode A/B Test Report",
        "",
        f"- **Model**: {model}",
        f"- **Date**: {datetime.now(timezone.utc).isoformat()}",
        f"- **Seeds**: {len(results_on)}",
        "",
        "## Summary",
        "",
        "| Metric | Thinking ON | Thinking OFF |",
        "|---|---|---|",
    ]

    on_success = sum(1 for r in results_on if not r["error"] and r["filled_dimensions"])
    off_success = sum(1 for r in results_off if not r["error"] and r["filled_dimensions"])
    on_empty = sum(1 for r in results_on if not r["error"] and not r["filled_dimensions"])
    off_empty = sum(1 for r in results_off if not r["error"] and not r["filled_dimensions"])
    on_fail = sum(1 for r in results_on if r["error"])
    off_fail = sum(1 for r in results_off if r["error"])
    on_avg_time = sum(r["elapsed_seconds"] for r in results_on) / len(results_on)
    off_avg_time = sum(r["elapsed_seconds"] for r in results_off) / len(results_off)

    lines.extend(
        [
            f"| Success (non-empty) | {on_success}/{len(results_on)} | {off_success}/{len(results_off)} |",
            f"| Empty response | {on_empty} | {off_empty} |",
            f"| Error/timeout | {on_fail} | {off_fail} |",
            f"| Avg time/seed | {on_avg_time:.1f}s | {off_avg_time:.1f}s |",
            f"| Total time | {sum(r['elapsed_seconds'] for r in results_on):.0f}s | {sum(r['elapsed_seconds'] for r in results_off):.0f}s |",
            "",
            "---",
            "",
        ]
    )

    # Per-seed comparison
    for r_on, r_off in zip(results_on, results_off):
        sid = r_on["seed_id"]
        lines.append(f"## {sid}: {r_on['raw_input']}")
        lines.append(f"**Type**: `{r_on['seed_type']}`")
        lines.append("")

        # Thinking OFF
        lines.append("### Thinking OFF")
        if r_off["error"]:
            lines.append(f"❌ ERROR: `{r_off['error']}`")
        elif not r_off["filled_dimensions"]:
            lines.append("⚠️ Empty response `{}`")
        else:
            lines.append(f"⏱ {r_off['elapsed_seconds']}s")
            lines.append("```json")
            lines.append(json.dumps(r_off["filled_dimensions"], ensure_ascii=False, indent=2))
            lines.append("```")
        lines.append("")

        # Thinking ON
        lines.append("### Thinking ON")
        if r_on["error"]:
            lines.append(f"❌ ERROR: `{r_on['error']}`")
        elif not r_on["filled_dimensions"]:
            lines.append("⚠️ Empty response `{}`")
        else:
            lines.append(f"⏱ {r_on['elapsed_seconds']}s")
            lines.append("```json")
            lines.append(json.dumps(r_on["filled_dimensions"], ensure_ascii=False, indent=2))
            lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def _print_summary(
    results_on: list[dict[str, Any]],
    results_off: list[dict[str, Any]],
) -> None:
    """Print comparison summary to console."""
    on_ok = sum(1 for r in results_on if not r["error"] and r["filled_dimensions"])
    off_ok = sum(1 for r in results_off if not r["error"] and r["filled_dimensions"])
    on_time = sum(r["elapsed_seconds"] for r in results_on)
    off_time = sum(r["elapsed_seconds"] for r in results_off)

    print("\n" + "=" * 60, flush=True)
    print("  A/B TEST SUMMARY", flush=True)
    print("=" * 60, flush=True)
    print(f"  {'Metric':<25} {'ON':>10} {'OFF':>10}", flush=True)
    print(f"  {'-'*25} {'-'*10} {'-'*10}", flush=True)
    print(f"  {'Success':.<25} {on_ok:>10} {off_ok:>10}", flush=True)
    print(f"  {'Total time':.<25} {on_time:>9.0f}s {off_time:>9.0f}s", flush=True)
    print(f"  {'Avg time/seed':.<25} {on_time/len(results_on):>9.1f}s {off_time/len(results_off):>9.1f}s", flush=True)
    print("=" * 60, flush=True)


if __name__ == "__main__":
    _output_dir = _BACKEND_DIR / "experiments" / "results"
    asyncio.run(run_ab_test(_output_dir))
