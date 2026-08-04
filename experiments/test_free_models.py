"""Try to find working free models for DashScope."""
import asyncio
import httpx
import json

async def test_free_models():
    """Test potential free models."""
    api_key = "sk-6551656db8e54b8a87b2e9727019f2a5"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # Potential free model names based on common patterns
    potential_models = [
        # Common free tier models
        "qwen-turbo",
        "qwen-plus",
        "qwen-max",
        
        # Image generation models (various naming patterns)
        "wanx-v1",
        "wanx-v2", 
        "flux-dev",
        "flux-schnell",
        
        # Try the specific model you mentioned
        "wan2.7-t2v-2026-06-12",
        
        # Stability AI models (often have free tiers)
        "stable-diffusion-xl",
        "sd-xl-turbo",
    ]
    
    for model in potential_models:
        print(f"\n=== Testing: {model} ===")
        
        payload = {
            "model": model,
            "input": {
                "prompt": "a simple blue circle",
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
                    headers=headers,
                    json=payload,
                )
                
                print(f"Status: {resp.status_code}")
                
                if resp.status_code == 200:
                    print("SUCCESS! Model is accessible")
                    data = resp.json()
                    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:300]}")
                    return model  # Return first working model
                else:
                    resp_data = resp.json()
                    error_msg = resp_data.get('message', resp_data.get('code', 'Unknown'))
                    print(f"Error: {error_msg}")
                    
        except Exception as e:
            print(f"Exception: {str(e)[:200]}")

if __name__ == "__main__":
    asyncio.run(test_free_models())