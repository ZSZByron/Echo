"""Test local image generation with auto-open."""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ai.image_generator import ImageGenerator

async def main():
    """Test local image generation."""
    
    print("Testing Local Image Generation...")
    print("This will:")
    print("1. Generate a cyberpunk-style placeholder with prompts")
    print("2. Save it to data/assets/")
    print("3. Automatically open the image")
    print("4. Display prompt information")
    print()
    
    try:
        # Create generator (will use local provider from .env)
        gen = ImageGenerator()
        print(f"Provider: {gen._provider}")
        print(f"Model: {getattr(gen, '_model', 'N/A')}")
        print()
        
        # Test generation with interesting cyberpunk prompt
        prompt = """cyberpunk ancient civilization, post-human Greek mythology, 
dark decaying grandeur, synthwave lighting, massive bronze doors inscribed 
with quantum-lock runes, holographic chains binding it shut, faint temporal shimmer, 
breathing metal texture, faint red danger glow around the lock mechanism"""
        
        negative_prompt = """people, characters, text, logo, watermark, modern buildings, 
cars, low quality, blurry, distorted, extra limbs, warm light, yellow light, cheerful"""
        
        print("Starting generation...")
        results = await gen.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            size="1024x1024",
            seed=42,
            num_candidates=1,
            asset_id="test_local_gen"
        )
        
        print(f"\nGeneration complete! Generated {len(results)} image(s)")
        
        if results:
            for i, result in enumerate(results):
                print(f"Image {i+1}:")
                print(f"  Seed: {result.seed}")
                print(f"  File: {result.file_path}")
                print(f"  URL: {result.url}")
        
        await gen.close()
        
    except Exception as e:
        print(f"[ERROR] Generation failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))