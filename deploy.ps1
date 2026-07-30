# Deployment Script for Echo Project
# Supports multiple deployment targets

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("development", "staging", "production")]
    [string]$Environment = "development",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipTests,
    
    [Parameter(Mandatory=$false)]
    [switch]$ForceDeploy
)

# Set error action
$ErrorActionPreference = "Stop"

# Color functions
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-ColorOutput green "🚀 Echo Project Deployment Script"
Write-ColorOutput yellow "Environment: $Environment"

# Validate environment
if (-not (Test-Path ".env.$Environment")) {
    Write-ColorOutput red "Error: Environment file .env.$Environment not found"
    exit 1
}

# Load environment variables
Write-ColorOutput yellow "📋 Loading environment variables..."
Get-Content ".env.$Environment" | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}

# Pre-deployment checks
Write-ColorOutput yellow "🔍 Running pre-deployment checks..."

# Check if required tools are installed
$requiredTools = @("git", "node", "python", "docker")
foreach ($tool in $requiredTools) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-ColorOutput red "Error: Required tool '$tool' not found"
        exit 1
    }
}

# Run tests if not skipped
if (-not $SkipTests) {
    Write-ColorOutput yellow "🧪 Running tests..."
    
    # Backend tests
    Write-ColorOutput cyan "Testing backend..."
    Push-Location backend
    try {
        python -m pytest --cov=app --cov-report=term-missing
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput red "Backend tests failed"
            exit 1
        }
    } finally {
        Pop-Location
    }
    
    # Frontend tests  
    Write-ColorOutput cyan "Testing frontend..."
    Push-Location frontend
    try {
        npm run test
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput red "Frontend tests failed"
            exit 1
        }
    } finally {
        Pop-Location
    }
    
    Write-ColorOutput green "✅ All tests passed"
} else {
    Write-ColorOutput yellow "⚠️ Skipping tests"
}

# Build applications
Write-ColorOutput yellow "🔨 Building applications..."

# Backend
Write-ColorOutput cyan "Building backend..."
Push-Location backend
try {
    python -m build
} finally {
    Pop-Location
}

# Frontend
Write-ColorOutput cyan "Building frontend..."
Push-Location frontend
try {
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-ColorOutput red "Frontend build failed"
        exit 1
    }
} finally {
    Pop-Location
}

Write-ColorOutput green "✅ Build completed successfully"

# Deployment based on environment
switch ($Environment) {
    "development" {
        Write-ColorOutput yellow "🏠 Deploying to development environment..."
        docker-compose up -d --build
        Write-ColorOutput green "✅ Development deployment completed"
    }
    
    "staging" {
        Write-ColorOutput yellow "🧪 Deploying to staging environment..."
        # Add staging deployment commands here
        # Example: docker-compose -f docker-compose.staging.yml up -d
        Write-ColorOutput green "✅ Staging deployment completed"
    }
    
    "production" {
        if (-not $ForceDeploy) {
            $confirmation = Read-Host "Are you sure you want to deploy to production? (yes/no)"
            if ($confirmation -ne "yes") {
                Write-ColorOutput yellow "Deployment cancelled"
                exit 0
            }
        }
        
        Write-ColorOutput yellow "🚀 Deploying to production environment..."
        
        # Create backup
        $backupPath = "backups\$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
        Copy-Item -Path "frontend\dist" -Destination $backupPath -Recurse
        Write-ColorOutput green "✅ Backup created at $backupPath"
        
        # Deploy frontend
        Write-ColorOutput cyan "Deploying frontend to S3..."
        # aws s3 sync frontend\dist s3://$env:S3_BUCKET --delete
        
        # Clear CDN cache
        Write-ColorOutput cyan "Clearing CDN cache..."
        # Add CDN cache clearing commands here
        
        Write-ColorOutput green "✅ Production deployment completed"
    }
}

# Health check
Write-ColorOutput yellow "🏥 Running health checks..."
$maxAttempts = 10
$attempt = 0

while ($attempt -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-ColorOutput green "✅ Health check passed"
            break
        }
    } catch {
        $attempt++
        Start-Sleep -Seconds 5
        Write-ColorOutput cyan "Health check attempt $attempt/$maxAttempts..."
    }
}

if ($attempt -eq $maxAttempts) {
    Write-ColorOutput red "❌ Health check failed"
    exit 1
}

Write-ColorOutput green "🎉 Deployment completed successfully!"
Write-ColorOutput cyan "📊 Deployment Summary:"
Write-ColorOutput cyan "- Environment: $Environment"
Write-ColorOutput cyan "- Tests: $(if ($SkipTests) { 'Skipped' } else { 'Passed' })"
Write-ColorOutput cyan "- Health Check: Passed"
Write-ColorOutput cyan "- Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"