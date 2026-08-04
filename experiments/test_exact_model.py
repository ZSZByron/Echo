"""Test the exact model name you provided."""
import asyncio
import httpx
import json

async def test_exact_model():
    """Test the exact model name: wan2.7-t2v-2026-06-12"""
    api_key = "sk-6551656db8e54b8a87b2e9727019f2a5"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # Try different API endpoints
    endpoints = [
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2video/video-synthesis",
    ]
    
    models_to_test = [
        "wan2.7-t2v-2026-06-12",
        "wanx-v1",
        "flux-dev",
    ]
    
    for endpoint in endpoints:
        for model in models_to_test:
            print(f"\nTesting: {model}")
            print(f"Endpoint: {endpoint}")
            
            payload = {
                "model": model,
                "input": {
                    "prompt": "test",
                },
            }
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        endpoint,
                        headers=headers,
                        json=payload,
                    )
                    
                    print(f"Status: {resp.status_code}")
                    resp_data = resp.json()
                    
                    if resp.status_code == 200:
                        print(f"SUCCESS! Response: {json.dumps(resp_data, indent=2, ensure_ascii=False)[:500]}")
                    else:
                        print(f"Failed: {resp_data.get('message', resp_data)[:200]}")
                        
            except Exception as e:
                print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_exact_model())