"""Retry failed seeds only."""
import asyncio
import os
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
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

# Import experiment module
from experiments.dimension_fill_experiment import (
    SEEDS,
    fill_dimensions_for_seed,
)
from app.ai.config import load_provider_config
from app.ai.provider import create_provider
import json
from datetime import datetime, timezone

RETRY_IDS = {"seed_05", "seed_08", "seed_09", "seed_10"}


async def main():
    config = load_provider_config()
    provider = create_provider(config)
    print(f"Provider: {config.provider_type} | Model: {config.model}", flush=True)

    retry_seeds = [s for s in SEEDS if s["id"] in RETRY_IDS]
    print(f"Retrying {len(retry_seeds)} failed seeds with 10s delay between each\n", flush=True)

    results = []
    for i, seed in enumerate(retry_seeds, 1):
        print(f"[{i}/{len(retry_seeds)}] {seed['id']}: {seed['raw_input']}", flush=True)
        await asyncio.sleep(10)  # delay between requests
        result = await fill_dimensions_for_seed(provider, seed)
        results.append(result)
        if result["error"]:
            print(f"  [FAIL] {result['error']}", flush=True)
        else:
            keys = list(result["filled_dimensions"].keys())
            print(f"  [OK] Dims: {keys} ({result['elapsed_seconds']}s)", flush=True)

    # Save results
    output_dir = _BACKEND_DIR / "experiments" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    json_path = output_dir / f"dimension_fill_retry_{timestamp}.json"
    json_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[SAVED] {json_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
