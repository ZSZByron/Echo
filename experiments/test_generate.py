"""Test script to reset asset status and trigger generation."""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.state.asset_store import AssetStore, AssetStatus


def main():
    """Reset asset to pending and trigger generation."""
    store = AssetStore()
    
    # Reset asset to pending status
    asset_id = "temple_ruins_bg"
    try:
        asset = store.update_asset(asset_id, status=AssetStatus.PENDING)
        print(f"[OK] Asset {asset_id} reset to {asset.status}")
        print(f"  Current status: {asset.status}")
        print(f"  Generation status: {asset.generation_status}")
    except Exception as e:
        print(f"[ERROR] Failed to reset asset: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())