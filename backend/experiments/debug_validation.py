"""Quick test to debug the validation script."""
import sys
import os
import asyncio
from pathlib import Path

# Add backend to path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

# Load .env file
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

print("1. Starting debug test...")

try:
    from app.ai.config import load_provider_config
    print("2. load_provider_config imported successfully")
    
    config = load_provider_config()
    print(f"3. Provider loaded: {config.provider_type} / {config.model}")
    
    from app.ai.provider import create_provider
    print("4. create_provider imported successfully")
    
    provider = create_provider(config)
    print(f"5. Provider created: {provider}")
    
    from experiments.layered_weight_experiment import WEIGHT_MATRIX
    print(f"6. WEIGHT_MATRIX imported: {len(WEIGHT_MATRIX)} layers")
    
    print("SUCCESS: All imports completed")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
