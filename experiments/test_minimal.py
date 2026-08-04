"""Minimal E2E test."""
import asyncio
import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ["ACTIVE_PROVIDER"] = "openai"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["OPENAI_BASE_URL"] = "http://localhost:1"

from app.main import app
from httpx import AsyncClient, ASGITransport

async def main():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=5.0) as ac:
        print("Testing health...")
        r = await ac.get("/api/health")
        print(f"Health: {r.status_code}")

        print("Testing reset...")
        r = await ac.post("/api/reset")
        print(f"Reset: {r.status_code}")

        print("Testing action (may timeout)...")
        try:
            r = await ac.post("/api/action", json={"player_input": "test"}, timeout=10.0)
            print(f"Action: {r.status_code}")
        except Exception as e:
            print(f"Action error: {e}")

    print("Done")

asyncio.run(main())
