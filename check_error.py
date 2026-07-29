"""Check specific error message from Wanxiang API."""
import asyncio
import httpx
import os
import json

async def check_error():
    """Check the actual error message."""
    api_key = "sk-6551656db8e54b8a87b2e9727019f2a5"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    
    payload = {
        "model": "wanx-v1",
        "input": {
            "prompt": "test",
        },
        "parameters": {
            "size": "1024*1024",
        },
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
                headers=headers,
                json=payload,
            )
            
            print(f"Status Code: {resp.status_code}")
            print(f"Response Body:")
            print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(check_error())