"""Test with explicit local provider."""
import asyncio
import sys
import os
from pathlib import Path

# Force local provider
os.environ["IMAGE_PROVIDER"] = "local"

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ai.image_generator import ImageGenerator

async def main():
    """Test with explicit local provider."""
    
    print("Testing with IMAGE_PROVIDER=local...")
    print(f"Environment set: {os.environ.get('IMAGE_PROVIDER')}")
    
    try:
        gen = ImageGenerator()
        print(f"Generator provider: {gen._provider}")
        
        prompt = "cyberpunk ancient civilization, dark decaying grandeur"
        negative_prompt = "people, text, watermark"
        
        results = await gen.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            size="1024x1024", 
            seed=123,
            num_candidates=1,
            asset_id="explicit_local_test"
        )
        
        print(f"Generated {len(results)} image(s)")
        if results:
            for r in results:
                print(f"File: {r.file_path}")
                print(f"Seed: {r.seed}")
        
        await gen.close()
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))