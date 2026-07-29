# PowerShell API Test for Local Image Generation
Write-Host "=== Complete API Test for Local Image Generation ===" -ForegroundColor Cyan
Write-Host ""

# 1. Stop existing processes
Write-Host "1. Stopping existing backend processes..." -ForegroundColor Yellow
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" } | Stop-Process -Force
Start-Sleep -Seconds 2

# 2. Start backend with local provider
Write-Host "2. Starting backend with IMAGE_PROVIDER=local..." -ForegroundColor Green
$env:IMAGE_PROVIDER = "local"
cd H:\UGC\backend
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m","uvicorn","app.main:app","--reload","--host","0.0.0.0","--port","8000" -WindowStyle Hidden -Environment @{
    IMAGE_PROVIDER = "local"
}

# Wait for startup
Write-Host "   Waiting for backend to start..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# 3. Test backend connection
Write-Host "3. Testing backend connection..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/docs" -Method Head -ErrorAction Stop
    Write-Host "   Backend running! Status: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "   Backend connection failed: $_" -ForegroundColor Red
    exit 1
}

# 4. Reset asset for testing
Write-Host "4. Resetting asset for testing..." -ForegroundColor Yellow
cd H:\UGC
$resetResult = & backend\.venv\Scripts\python.exe test_generate.py
Write-Host "   Asset reset result: $resetResult" -ForegroundColor Gray

# 5. Trigger generation
Write-Host "5. Testing image generation via API..." -ForegroundColor Yellow
$assetId = "temple_ruins_bg"
try {
    $body = @{ asset_id = $assetId } | ConvertTo-Json
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/assets/$assetId/generate" -Method POST -Body $body -ContentType "application/json" -ErrorAction Stop
    
    Write-Host "   Generation triggered successfully!" -ForegroundColor Green
    Write-Host "   Response: $($response.Content)" -ForegroundColor Cyan
    
    # Wait for generation
    Write-Host "   Waiting for generation to complete..." -ForegroundColor Gray
    Start-Sleep -Seconds 8
    
    # Check final status
    $statusResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/assets/$assetId" -Method Get
    $statusData = $statusResponse.Content | ConvertFrom-Json
    
    Write-Host "   Final Status: $($statusData.status)" -ForegroundColor Cyan
    Write-Host "   Generation Status: $($statusData.generation_status)" -ForegroundColor Cyan
    Write-Host "   File Path: $($statusData.file_path)" -ForegroundColor Cyan
    Write-Host "   Error: $($statusData.error_message)" -ForegroundColor Red
    
    if ($statusData.status -eq "completed") {
        Write-Host "   SUCCESS! Image generated and saved!" -ForegroundColor Green
    } else {
        Write-Host "   Generation did not complete successfully" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "   Generation failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
Write-Host "The image should have opened automatically with full prompt information!" -ForegroundColor Green
Write-Host "Admin page: http://localhost:5173/admin/assets" -ForegroundColor White