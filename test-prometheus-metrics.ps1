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
