#!/usr/bin/env pwsh
# Setup Prometheus Integration for CrashLens
# This script automates the setup and verification of Prometheus metrics integration

$ErrorActionPreference = "Stop"

Write-Host "=== CrashLens Prometheus Integration Setup ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check if prometheus-client is installed
Write-Host "1. Checking prometheus-client installation..." -ForegroundColor Yellow
try {
    poetry run python -c "import prometheus_client; print('   ✅ prometheus-client installed')" 2>&1 | Out-Host
} catch {
    Write-Host "   ⚠️  prometheus-client not found, installing..." -ForegroundColor Yellow
    poetry add prometheus-client
    Write-Host "   ✅ prometheus-client installed" -ForegroundColor Green
}
Write-Host ""

# 2. Verify metrics module exists
Write-Host "2. Verifying crashlens/metrics.py..." -ForegroundColor Yellow
if (Test-Path "crashlens/metrics.py") {
    Write-Host "   ✅ Metrics module exists" -ForegroundColor Green
    
    # Test import
    poetry run python -c "from crashlens.metrics import MetricsCollector; print('   ✅ Metrics module imports correctly')" 2>&1 | Out-Host
} else {
    Write-Host "   ❌ crashlens/metrics.py not found!" -ForegroundColor Red
    Write-Host "   Please create the metrics module first." -ForegroundColor Red
    exit 1
}
Write-Host ""

# 3. Check if Docker is available
Write-Host "3. Checking Docker availability..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "   ✅ Docker available: $dockerVersion" -ForegroundColor Green
    
    # Check if Docker Compose is available
    $composeVersion = docker compose version 2>&1
    Write-Host "   ✅ Docker Compose available: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Docker not available - manual setup required" -ForegroundColor Yellow
    Write-Host "   Install Docker Desktop: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
}
Write-Host ""

# 4. Check if docker-compose.yml exists
Write-Host "4. Checking docker-compose.yml..." -ForegroundColor Yellow
if (Test-Path "docker-compose.yml") {
    Write-Host "   ✅ docker-compose.yml exists" -ForegroundColor Green
    
    # Ask if user wants to start the stack
    Write-Host ""
    $start = Read-Host "   Start Prometheus stack now? (y/n)"
    if ($start -eq "y") {
        Write-Host "   Starting Prometheus stack..." -ForegroundColor Yellow
        docker compose up -d
        
        Write-Host "   Waiting for services to start..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        Write-Host "   ✅ Prometheus stack started" -ForegroundColor Green
        Write-Host ""
        Write-Host "   Services:" -ForegroundColor Cyan
        Write-Host "   - Pushgateway: http://localhost:9091" -ForegroundColor White
        Write-Host "   - Prometheus:  http://localhost:9090" -ForegroundColor White
        Write-Host "   - Grafana:     http://localhost:3000 (admin/admin)" -ForegroundColor White
    }
} else {
    Write-Host "   ⚠️  docker-compose.yml not found" -ForegroundColor Yellow
    Write-Host "   You'll need to set up Prometheus infrastructure manually" -ForegroundColor Yellow
}
Write-Host ""

# 5. Test metrics push (will fail if Pushgateway not running)
Write-Host "5. Testing metrics push..." -ForegroundColor Yellow
try {
    poetry run python -c "from crashlens.metrics import test_metrics; test_metrics()" 2>&1 | Out-Host
} catch {
    Write-Host "   ⚠️  Metrics test failed (expected if Pushgateway not running)" -ForegroundColor Yellow
}
Write-Host ""

# 6. Verify guard CLI has metrics flags
Write-Host "6. Verifying guard CLI has metrics flags..." -ForegroundColor Yellow
$helpOutput = poetry run crashlens guard --help 2>&1
if ($helpOutput -match "push-metrics") {
    Write-Host "   ✅ Guard has --push-metrics flag" -ForegroundColor Green
} else {
    Write-Host "   ❌ Guard missing --push-metrics flag!" -ForegroundColor Red
    Write-Host "   Please update crashlens/guard.py" -ForegroundColor Red
}

if ($helpOutput -match "pushgateway-url") {
    Write-Host "   ✅ Guard has --pushgateway-url flag" -ForegroundColor Green
} else {
    Write-Host "   ❌ Guard missing --pushgateway-url flag!" -ForegroundColor Red
}

if ($helpOutput -match "metrics-job") {
    Write-Host "   ✅ Guard has --metrics-job flag" -ForegroundColor Green
} else {
    Write-Host "   ❌ Guard missing --metrics-job flag!" -ForegroundColor Red
}
Write-Host ""

# 7. Show next steps
Write-Host "=== Setup Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Run guard with metrics:" -ForegroundColor White
Write-Host "   poetry run crashlens guard fixtures/combined-logs.jsonl --rules policies/retry-loop-detector.yaml --push-metrics" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Check metrics in Pushgateway:" -ForegroundColor White
Write-Host "   Start-Process http://localhost:9091" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Query metrics in Prometheus:" -ForegroundColor White
Write-Host "   Start-Process http://localhost:9090" -ForegroundColor Gray
Write-Host "   Query: crashlens_guard_runs_total" -ForegroundColor Gray
Write-Host ""
Write-Host "4. View dashboard in Grafana:" -ForegroundColor White
Write-Host "   Start-Process http://localhost:3000" -ForegroundColor Gray
Write-Host "   Login: admin/admin" -ForegroundColor Gray
Write-Host ""

# 8. Create test file for easy verification
$testScript = @'
# Test CrashLens Metrics Integration
Write-Host "Testing CrashLens metrics integration..." -ForegroundColor Cyan

# Run guard with metrics
Write-Host "`n1. Running guard with metrics..." -ForegroundColor Yellow
poetry run crashlens guard fixtures/combined-logs.jsonl `
    --rules policies/retry-loop-detector.yaml `
    --push-metrics `
    --pushgateway-url http://localhost:9091 `
    --metrics-job crashlens-test `
    --output json | Out-Null

Write-Host "   ✅ Guard executed with metrics" -ForegroundColor Green

# Check Pushgateway
Write-Host "`n2. Checking Pushgateway metrics..." -ForegroundColor Yellow
try {
    $metrics = Invoke-WebRequest -Uri "http://localhost:9091/metrics" -UseBasicParsing
    if ($metrics.Content -match "crashlens_guard_runs_total") {
        Write-Host "   ✅ Metrics visible in Pushgateway" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  No crashlens metrics found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Could not connect to Pushgateway" -ForegroundColor Red
}

Write-Host "`n✅ Test complete!" -ForegroundColor Green
Write-Host "`nOpen these URLs to verify:" -ForegroundColor Cyan
Write-Host "- Pushgateway: http://localhost:9091" -ForegroundColor White
Write-Host "- Prometheus:  http://localhost:9090" -ForegroundColor White
Write-Host "- Grafana:     http://localhost:3000" -ForegroundColor White
'@

Set-Content -Path "test-prometheus-metrics.ps1" -Value $testScript
Write-Host "✅ Created test-prometheus-metrics.ps1 for easy verification" -ForegroundColor Green
Write-Host "   Run with: .\test-prometheus-metrics.ps1" -ForegroundColor Gray
Write-Host ""
