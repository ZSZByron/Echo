"""Check backend logs for generation errors."""
import asyncio
import sys
from pathlib import Path

# Force local provider and enable debug logging
import os
os.environ["IMAGE_PROVIDER"] = "local"

# Add backend to path  
sys.path.insert(0, str(Path(__file__).parent.parent))

# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

from app.ai.image_generator import ImageGenerator

async def test_with_debug():
    """Test generation with debug output."""
    
    print("Testing with debug logging...")
    
    try:
        gen = ImageGenerator()
        print(f"Provider: {gen._provider}")
        
        # Use same prompt as the failing asset
        prompt = """cyberpunk ancient civilization, post-human Greek mythology, 
dark decaying grandeur, synthwave lighting, ancient marble temple ruins, 
broken columns, holographic technology overlays, mist and darkness"""
        
        negative_prompt = """people, characters, text, logo, watermark, modern 
buildings, cars, low quality, blurry, distorted, extra limbs"""
        
        print("Starting generation...")
        results = await gen.generate(
            prompt=prompt,
            negative_prompt=negative_prompt, 
            size="1024x1024",
            seed=None,
            num_candidates=1,
            asset_id="temple_ruins_bg"
        )
        
        print(f"Results: {len(results)}")
        if results:
            print("SUCCESS!")
        
        await gen.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_with_debug())