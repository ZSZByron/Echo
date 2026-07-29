"""Reset failed assets to pending for re-generation."""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.state.asset_store import AssetStore, AssetStatus

def main():
    """Reset all failed assets to pending status."""
    store = AssetStore()
    assets = store.list_assets()
    
    failed_assets = [a for a in assets if a.status == AssetStatus.FAILED]
    
    if not failed_assets:
        print("No failed assets found.")
        return 0
    
    print(f"Found {len(failed_assets)} failed assets:")
    for asset in failed_assets:
        print(f"  - {asset.id}: {asset.name}")
    
    print("\nResetting to pending status...")
    
    success_count = 0
    for asset in failed_assets:
        try:
            updated = store.update_asset(asset.id, status=AssetStatus.PENDING)
            print(f"[OK] Reset {asset.id} to {updated.status}")
            success_count += 1
        except Exception as e:
            print(f"[ERROR] Failed to reset {asset.id}: {e}")
    
    print(f"\nSuccessfully reset {success_count}/{len(failed_assets)} assets")
    print("You can now trigger generation via the API or admin panel")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())