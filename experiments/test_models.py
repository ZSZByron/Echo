"""Test different Wanxiang model names to find available ones."""
import asyncio
import httpx
import os

async def test_model(model_name: str):
    """Test a specific model name."""
    api_key = "sk-6551656db8e54b8a87b2e9727019f2a5"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    
    payload = {
        "model": model_name,
        "input": {
            "prompt": "a simple test image",
        },
        "parameters": {
            "size": "1024*1024",
            "seed": 12345,
        },
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
                headers=headers,
                json=payload,
            )
            
            print(f"Model: {model_name}")
            print(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                print(f"✓ SUCCESS - Model exists and is accessible")
                data = resp.json()
                print(f"Response: {data.get('output', {}).get('task_id', 'N/A')}")
            else:
                print(f"✗ FAILED - {resp.text[:200]}")
            print()
            
    except Exception as e:
        print(f"Model: {model_name} - Exception: {e}")

async def main():
    """Test various model names."""
    
    models_to_test = [
        "wanx-v1",
        "wanx-v2", 
        "wanx-v2-7-32k",
        "flux-dev",
        "flux-schnell",
        "flux-pro",
        "stable-diffusion-xl",
        "sd-xl-turbo",
    ]
    
    print("Testing Wanxiang model availability...")
    print("=" * 50)
    
    for model in models_to_test:
        await test_model(model)

if __name__ == "__main__":
    asyncio.run(main())