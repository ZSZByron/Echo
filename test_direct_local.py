"""Direct test of local generator."""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ai.local_generator import LocalImageGenerator

async def main():
    """Test local generator directly."""
    
    print("Testing Local Generator Directly...")
    
    try:
        gen = LocalImageGenerator()
        
        prompt = "cyberpunk ancient temple, neon lights, dark atmosphere"
        negative_prompt = "people, text, watermark"
        
        print("Starting generation...")
        results = await gen.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            size="1024x1024",
            seed=42,
            num_candidates=1,
            asset_id="direct_test"
        )
        
        print(f"Generated {len(results)} image(s)")
        
        if results:
            print("Success! Check the opened image for prompt details.")
            return 0
        else:
            print("No images generated")
            return 1
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))