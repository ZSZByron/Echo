"""Complete API test with fresh backend restart."""
import subprocess
import time
import requests
import os

# Ensure local provider is set
os.environ["IMAGE_PROVIDER"] = "local"

print("=== Complete API Test for Local Image Generation ===\n")

# 1. Stop existing backend
print("1. Stopping existing backend...")
try:
    subprocess.run(["taskkill", "/F", "/IM", "python.exe"], capture_output=True)
    time.sleep(2)
except:
    pass

# 2. Start backend with local provider  
print("2. Starting backend with local provider...")
backend_proc = subprocess.Popen(
    ["python.exe", "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
    cwd=r"H:\UGC\backend",
    env={**os.environ, "IMAGE_PROVIDER": "local"},
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait for backend to start
print("   Waiting for backend to start...")
time.sleep(5)

# 3. Test if backend is running
print("3. Testing backend connection...")
try:
    response = requests.get("http://localhost:8000/docs")
    print(f"   Backend running! Status: {response.status_code}")
except Exception as e:
    print(f"   Backend connection failed: {e}")
    backend_proc.kill()
    exit(1)

# 4. Check provider configuration
print("4. Checking image generation provider...")
try:
    # Try to list assets to test API
    response = requests.get("http://localhost:8000/api/assets")
    print(f"   Assets API working! Status: {response.status_code}")
except Exception as e:
    print(f"   Assets API failed: {e}")

# 5. Test generation endpoint
print("5. Testing image generation...")
try:
    # First reset asset to pending
    asset_id = "temple_ruins_bg"
    
    # We'll need to call the internal API to reset status
    # For now, let's just try to trigger generation
    print(f"   Attempting to generate asset: {asset_id}")
    
    # Trigger generation
    response = requests.post(
        f"http://localhost:8000/api/assets/{asset_id}/generate",
        json={"asset_id": asset_id}
    )
    
    if response.status_code == 200:
        print(f"   Generation triggered successfully!")
        print(f"   Response: {response.json()}")
        
        # Wait a bit for generation to complete
        print("   Waiting for generation to complete...")
        time.sleep(5)
        
        # Check status
        status_response = requests.get(f"http://localhost:8000/api/assets/{asset_id}/status")
        status_data = status_response.json()
        print(f"   Final status: {status_data}")
        
    else:
        print(f"   Generation trigger failed: {response.status_code} - {response.text}")
        
except Exception as e:
    print(f"   Generation test failed: {e}")

print("\n=== Test Complete ===")
print("Check your image viewer for the generated cyberpunk placeholder!")
print(f"It should contain the full prompt information displayed on the image.")

# Keep backend running
print("\nBackend continues running. Press Ctrl+C to stop.")
try:
    backend_proc.wait()
except KeyboardInterrupt:
    print("\nStopping backend...")
    backend_proc.kill()