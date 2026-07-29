# Restart backend with local provider configuration
Write-Host "Restarting backend with local image generation..." -ForegroundColor Cyan

# Stop existing backend
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" } | Stop-Process -Force
Start-Sleep -Seconds 2

# Set environment for this session
$env:IMAGE_PROVIDER = "local"

# Start backend
Write-Host "Starting backend with IMAGE_PROVIDER=local..." -ForegroundColor Green
cd H:\UGC\backend
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","app.main:app","--reload","--host","0.0.0.0","--port","8000" -WindowStyle Hidden

# Wait for startup
Start-Sleep -Seconds 4

# Test if running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/docs" -Method Head -ErrorAction Stop
    Write-Host "Backend started successfully!" -ForegroundColor Green
    Write-Host "Image generation provider: local" -ForegroundColor Cyan
    Write-Host "Assets API: http://localhost:8000/api/assets" -ForegroundColor White
    Write-Host "Admin page: http://localhost:5173/admin/assets" -ForegroundColor White
} catch {
    Write-Host "Backend failed to start" -ForegroundColor Red
}