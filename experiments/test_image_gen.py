"""Test script to debug image generation."""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ai.image_generator import ImageGenerator, ImageGenerationError


async def main():
    """Test image generation directly."""
    
    # Set environment for wanxiang
    os.environ["IMAGE_PROVIDER"] = "wanxiang"
    os.environ["WANXIANG_API_KEY"] = "sk-6551656db8e54b8a87b2e9727019f2a5"
    
    print("Testing Wanxiang Image Generation...")
    print(f"Provider: wanxiang")
    print(f"API Key: {os.environ['WANXIANG_API_KEY'][:20]}...")
    
    try:
        gen = ImageGenerator()
        print(f"ImageGenerator initialized successfully")
        
        # Test with simple prompt
        results = await gen.generate(
            prompt="a simple blue circle on white background",
            negative_prompt="complex, detailed",
            asset_id="test_001",
            num_candidates=1
        )
        
        print(f"Generation results: {len(results)} images")
        if results:
            for i, result in enumerate(results):
                print(f"  Image {i+1}: seed={result.seed}, url={result.url}")
        
        await gen.close()
        
    except ImageGenerationError as e:
        print(f"[ERROR] ImageGenerationError: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))