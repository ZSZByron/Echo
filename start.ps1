# Start script for Echo UGC Demo
# Launches both backend and frontend services

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Echo UGC Demo - Starting Services"  -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if backend .env exists
$envPath = "backend\.env"
if (-not (Test-Path $envPath)) {
    Write-Host "[ERROR] backend\.env not found!" -ForegroundColor Red
    Write-Host "Please copy backend\.env.example to backend\.env and configure your API keys" -ForegroundColor Yellow
    exit 1
}

# Function to cleanup background jobs on exit
function Cleanup-Jobs {
    Write-Host "`nStopping services..." -ForegroundColor Yellow
    Get-Job | Remove-Job -Force
    exit
}

# Set up cleanup on script exit
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup-Jobs } -ErrorAction SilentlyContinue
trap { Cleanup-Jobs }

# Resolve project root from script location (Start-Job does NOT inherit CWD in PS 5.1)
$projectRoot = $PSScriptRoot

# Use Anaconda Deepcode environment
# This ensures all dependencies are available
$venvPython = "F:\Anaconda\envs\Deepcode\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Anaconda Deepcode environment not found!" -ForegroundColor Red
    Write-Host "Please ensure Anaconda is installed and Deepcode environment exists:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Path expected: F:\Anaconda\envs\Deepcode\python.exe" -ForegroundColor White
    Write-Host ""
    exit 1
}
Write-Host "  Using Python: $venvPython" -ForegroundColor Gray

# Start Backend
Write-Host "[1/2] Starting Backend (FastAPI)..." -ForegroundColor Green
$backendJob = Start-Job -ArgumentList $venvPython, $projectRoot -ScriptBlock {
    param($py, $root)
    Set-Location "$root\backend"
    & $py -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
} -Name "EchoBackend"

# Wait for backend to initialize
Write-Host "  Waiting for backend to start..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Check if backend started successfully
if ($backendJob.State -eq "Running") {
    Write-Host "  ✓ Backend started on http://localhost:8000" -ForegroundColor Green
} else {
    Write-Host "  ✗ Backend failed to start (State: $($backendJob.State))" -ForegroundColor Red
    Write-Host "  --- Backend Job Output ---" -ForegroundColor Yellow
    Receive-Job -Job $backendJob 2>&1 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkRed }
    Write-Host "  --- End Output ---" -ForegroundColor Yellow
    Cleanup-Jobs
}

# Start Frontend
Write-Host "[2/2] Starting Frontend (Vite)..." -ForegroundColor Green
$frontendJob = Start-Job -ArgumentList $projectRoot -ScriptBlock {
    param($root)
    Set-Location "$root\frontend"
    npm run dev
} -Name "EchoFrontend"

# Wait for frontend to initialize
Write-Host "  Waiting for frontend to start..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Check if frontend started successfully
if ($frontendJob.State -eq "Running") {
    Write-Host "  ✓ Frontend started on http://localhost:5173" -ForegroundColor Green
} else {
    Write-Host "  ✗ Frontend failed to start (State: $($frontendJob.State))" -ForegroundColor Red
    Write-Host "  --- Frontend Job Output ---" -ForegroundColor Yellow
    Receive-Job -Job $frontendJob 2>&1 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkRed }
    Write-Host "  --- End Output ---" -ForegroundColor Yellow
    Cleanup-Jobs
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Services Running!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Backend API:  http://localhost:8000" -ForegroundColor White
Write-Host "Frontend UI: http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host ""

# Stream output from both jobs
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "  Real-time Logs" -ForegroundColor Gray
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

# Keep script running and monitor jobs
while ($backendJob.State -eq "Running" -or $frontendJob.State -eq "Running") {
    Receive-Job -Job $backendJob -ErrorAction SilentlyContinue | Select-Object -First 1 | ForEach-Object {
        Write-Host "[Backend] $_" -ForegroundColor DarkGray
    }
    Receive-Job -Job $frontendJob -ErrorAction SilentlyContinue | Select-Object -First 1 | ForEach-Object {
        Write-Host "[Frontend] $_" -ForegroundColor DarkGray
    }
    Start-Sleep -Milliseconds 100

    # Check if either job failed
    if ($backendJob.State -eq "Failed" -or $frontendJob.State -eq "Failed") {
        Write-Host ""
        Write-Host "A service has crashed. Stopping..." -ForegroundColor Red
        Cleanup-Jobs
    }
}

Write-Host ""
Write-Host "All services stopped." -ForegroundColor Yellow
