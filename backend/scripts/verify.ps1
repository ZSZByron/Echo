# ====================================
# Echo UGC Backend - Quality Gate Verification
# 6-Layer Quality Checks
# ====================================

# Error on any failure
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Set-Location $ProjectRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Echo UGC - Quality Gate Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$FailedSteps = @()

# ====================================
# Layer 1: Ruff - Code Style & Linting
# ====================================
Write-Host "[Layer 1/6] Running Ruff checks..." -ForegroundColor Yellow
try {
    ruff check . --max-complexity=10
    if ($LASTEXITCODE -ne 0) {
        throw "Ruff check failed with exit code $LASTEXITCODE"
    }
    Write-Host "✓ Ruff checks passed" -ForegroundColor Green
} catch {
    Write-Host "✗ Ruff checks failed" -ForegroundColor Red
    $FailedSteps += "Ruff"
}

# ====================================
# Layer 2: MyPy - Type Checking
# ====================================
Write-Host ""
Write-Host "[Layer 2/6] Running MyPy type checks..." -ForegroundColor Yellow
try {
    mypy app --strict
    if ($LASTEXITCODE -ne 0) {
        throw "MyPy check failed with exit code $LASTEXITCODE"
    }
    Write-Host "✓ MyPy checks passed" -ForegroundColor Green
} catch {
    Write-Host "✗ MyPy checks failed" -ForegroundColor Red
    $FailedSteps += "MyPy"
}

# ====================================
# Layer 3: Radon - Code Complexity
# ====================================
Write-Host ""
Write-Host "[Layer 3/6] Running Radon complexity analysis..." -ForegroundColor Yellow
try {
    radon cc app -a -s --max-complexity=10
    if ($LASTEXITCODE -ne 0) {
        throw "Radon check failed with exit code $LASTEXITCODE"
    }
    Write-Host "✓ Radon complexity checks passed" -ForegroundColor Green
} catch {
    Write-Host "✗ Radon complexity checks failed" -ForegroundColor Red
    $FailedSteps += "Radon"
}

# ====================================
# Layer 4: Pytest - Unit Tests + Coverage
# ====================================
Write-Host ""
Write-Host "[Layer 4/6] Running Pytest with coverage..." -ForegroundColor Yellow
try {
    pytest tests/ -v --cov=app --cov-report=term-missing --cov-fail-under=85 --cov-branch
    if ($LASTEXITCODE -ne 0) {
        throw "Pytest failed with exit code $LASTEXITCODE"
    }
    Write-Host "✓ Pytest tests passed with ≥85% coverage" -ForegroundColor Green
} catch {
    Write-Host "✗ Pytest tests failed or coverage <85%" -ForegroundColor Red
    $FailedSteps += "Pytest"
}

# ====================================
# Layer 5: Mutmut - Mutation Testing
# ====================================
Write-Host ""
Write-Host "[Layer 5/6] Running Mutmut mutation tests..." -ForegroundColor Yellow
try {
    mutmut run --paths-to-mutate app/engine/
    if ($LASTEXITCODE -ne 0) {
        throw "Mutmut failed with exit code $LASTEXITCODE"
    }
    Write-Host "✓ Mutmut mutation tests passed" -ForegroundColor Green
} catch {
    Write-Host "✗ Mutmut mutation tests failed" -ForegroundColor Red
    $FailedSteps += "Mutmut"
}

# ====================================
# Layer 6: Frontend Quality Checks
# ====================================
Write-Host ""
Write-Host "[Layer 6/6] Running Frontend quality checks..." -ForegroundColor Yellow
$FrontendPath = Join-Path $ProjectRoot "frontend"
if (Test-Path $FrontendPath) {
    try {
        Set-Location $FrontendPath

        # ESLint
        npm run lint --if-present
        if ($LASTEXITCODE -ne 0) {
            throw "ESLint failed with exit code $LASTEXITCODE"
        }

        # TypeScript check
        npm run type-check --if-present
        if ($LASTEXITCODE -ne 0) {
            throw "TypeScript check failed with exit code $LASTEXITCODE"
        }

        # Build check
        npm run build
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend build failed with exit code $LASTEXITCODE"
        }

        Write-Host "✓ Frontend quality checks passed" -ForegroundColor Green
    } catch {
        Write-Host "✗ Frontend quality checks failed" -ForegroundColor Red
        $FailedSteps += "Frontend"
    } finally {
        Set-Location $ProjectRoot
    }
} else {
    Write-Host "⊘ Frontend directory not found - skipping" -ForegroundColor DarkYellow
}

# ====================================
# Final Summary
# ====================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Quality Gate Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($FailedSteps.Count -eq 0) {
    Write-Host "✓ ALL QUALITY GATES PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Code is ready for commit/deployment" -ForegroundColor Green
    exit 0
} else {
    Write-Host "✗ QUALITY GATES FAILED" -ForegroundColor Red
    Write-Host ""
    Write-Host "Failed steps:" -ForegroundColor Red
    foreach ($step in $FailedSteps) {
        Write-Host "  - $step" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Please fix the above issues before proceeding" -ForegroundColor Yellow
    exit 1
}
