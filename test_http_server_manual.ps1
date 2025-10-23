# HTTP Server Mode - Manual Test Script
# This script tests the HTTP server implementation manually

Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      HTTP SERVER MODE - MANUAL TEST                      ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Step 1: Set required environment variable
Write-Host "[1/5] Setting environment variable..." -ForegroundColor Yellow
$env:CRASHLENS_ALLOW_HTTP_METRICS = "true"
Write-Host "  ✓ CRASHLENS_ALLOW_HTTP_METRICS=true" -ForegroundColor Green

# Step 2: Start HTTP server in background
Write-Host "`n[2/5] Starting HTTP server with demo data..." -ForegroundColor Yellow
$job = Start-Job -ScriptBlock {
    Set-Location "C:\Users\LawLight\OneDrive\Desktop\crashlens"
    $env:CRASHLENS_ALLOW_HTTP_METRICS = "true"
    poetry run crashlens scan --demo --metrics-http --metrics-port 9090 2>&1
}

Write-Host "  ✓ Server starting (job ID: $($job.Id))..." -ForegroundColor Green
Start-Sleep -Seconds 5  # Give server time to start

# Step 3: Check if server is running
Write-Host "`n[3/5] Testing HTTP endpoints..." -ForegroundColor Yellow

try {
    # Test /health endpoint
    Write-Host "  Testing /health endpoint..." -ForegroundColor Gray
    $health = Invoke-WebRequest -Uri "http://localhost:9090/health" -UseBasicParsing
    if ($health.StatusCode -eq 200) {
        Write-Host "  ✓ /health returned 200 OK" -ForegroundColor Green
    }
    
    # Test /metrics endpoint
    Write-Host "  Testing /metrics endpoint..." -ForegroundColor Gray
    $metrics = Invoke-WebRequest -Uri "http://localhost:9090/metrics" -UseBasicParsing
    if ($metrics.StatusCode -eq 200) {
        Write-Host "  ✓ /metrics returned 200 OK" -ForegroundColor Green
        Write-Host "  ✓ Response size: $($metrics.Content.Length) bytes" -ForegroundColor Green
        
        # Check for CrashLens metrics
        if ($metrics.Content -match "crashlens_") {
            Write-Host "  ✓ Found crashlens metrics" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ No crashlens metrics found" -ForegroundColor Yellow
        }
    }
    
    # Test 404 for unknown endpoint
    Write-Host "  Testing 404 for unknown endpoint..." -ForegroundColor Gray
    try {
        $unknown = Invoke-WebRequest -Uri "http://localhost:9090/unknown" -UseBasicParsing
        Write-Host "  ⚠ Expected 404 but got $($unknown.StatusCode)" -ForegroundColor Yellow
    } catch {
        if ($_.Exception.Response.StatusCode -eq 404) {
            Write-Host "  ✓ /unknown correctly returned 404" -ForegroundColor Green
        }
    }
    
} catch {
    Write-Host "  ❌ Error testing server: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Server may not be running yet. Check job output:" -ForegroundColor Yellow
    Receive-Job -Job $job | Select-Object -Last 20
}

# Step 4: Check job output
Write-Host "`n[4/5] Checking server logs..." -ForegroundColor Yellow
$output = Receive-Job -Job $job
if ($output) {
    Write-Host "  Server output:" -ForegroundColor Gray
    $output | Select-Object -Last 10 | ForEach-Object {
        Write-Host "    $_" -ForegroundColor Gray
    }
}

# Step 5: Stop server
Write-Host "`n[5/5] Stopping server..." -ForegroundColor Yellow
Stop-Job -Job $job
Remove-Job -Job $job
Write-Host "  ✓ Server stopped" -ForegroundColor Green

# Summary
Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║      TEST COMPLETE                                        ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

Write-Host "MANUAL TEST CHECKLIST:" -ForegroundColor Yellow
Write-Host "  [ ] Server started without errors" -ForegroundColor White
Write-Host "  [ ] /health endpoint returned 200 OK" -ForegroundColor White
Write-Host "  [ ] /metrics endpoint returned 200 OK" -ForegroundColor White
Write-Host "  [ ] crashlens metrics found in response" -ForegroundColor White
Write-Host "  [ ] /unknown endpoint returned 404" -ForegroundColor White
Write-Host "  [ ] Server stopped cleanly" -ForegroundColor White

Write-Host "`nNext: If all tests passed, continue to Step 1.10 (Benchmark Script)`n" -ForegroundColor Magenta
