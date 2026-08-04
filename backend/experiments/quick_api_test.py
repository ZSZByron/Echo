"""Quick API connectivity test."""
import asyncio
import os
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

# Load .env manually
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


async def main():
    config = load_provider_config()
    print(f"Provider: {config.provider_type}, Model: {config.model}")
    print(f"Base URL: {config.base_url}")
    provider = create_provider(config)

    print("Sending test message...")
    try:
        result = await asyncio.wait_for(
            provider.chat([{"role": "user", "content": "Reply with only the word: OK"}]),
            timeout=30.0,
        )
        print(f"Response: {result[:200]}")
    except asyncio.TimeoutError:
        print("TIMEOUT after 30s")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
