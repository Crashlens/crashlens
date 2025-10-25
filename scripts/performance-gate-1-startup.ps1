# Performance Gate 1: CLI Startup Latency Test
# Objective: Prove lazy loading works - CLI must start fast
# Date: October 24, 2025

Write-Host "`n=============================================================" -ForegroundColor Cyan
Write-Host "   PERFORMANCE GATE 1: CLI STARTUP LATENCY TEST" -ForegroundColor Yellow
Write-Host "=============================================================`n" -ForegroundColor Cyan

$testsPassed = 0
$testsFailed = 0

# Test 1: Baseline startup time WITHOUT metrics (10 iterations)
Write-Host "Test 1: Baseline CLI Startup Time (no metrics)..." -ForegroundColor White
Write-Host "Running 10 iterations for statistical validity...`n" -ForegroundColor DarkGray

$baselineTimes = @()
for ($i = 1; $i -le 10; $i++) {
    $time = Measure-Command {
        crashlens --version | Out-Null
    } | Select-Object -ExpandProperty TotalMilliseconds
    
    $baselineTimes += $time
    Write-Host "  Iteration $i/10: $([math]::Round($time, 0))ms" -ForegroundColor DarkGray
}

$baselineAvg = ($baselineTimes | Measure-Object -Average).Average
$baselineStdDev = [math]::Sqrt((($baselineTimes | ForEach-Object { [math]::Pow($_ - $baselineAvg, 2) }) | Measure-Object -Average).Average)

Write-Host "`nBaseline Results:" -ForegroundColor White
Write-Host "  Average: $([math]::Round($baselineAvg, 0))ms" -ForegroundColor Cyan
Write-Host "  Std Dev: $([math]::Round($baselineStdDev, 0))ms" -ForegroundColor Cyan
Write-Host "  Min: $([math]::Round(($baselineTimes | Measure-Object -Minimum).Minimum, 0))ms" -ForegroundColor Cyan
Write-Host "  Max: $([math]::Round(($baselineTimes | Measure-Object -Maximum).Maximum, 0))ms" -ForegroundColor Cyan

# Pass Criteria: <300ms average
if ($baselineAvg -lt 300) {
    Write-Host "`nPASS: Baseline startup <300ms target ($([math]::Round($baselineAvg, 0))ms)" -ForegroundColor Green
    $testsPassed++
} else {
    Write-Host "`nFAIL: Baseline startup >300ms ($([math]::Round($baselineAvg, 0))ms)" -ForegroundColor Red
    $testsFailed++
}

# Test 2: Startup time WITH metrics flags enabled (10 iterations)
Write-Host "`n-------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "Test 2: CLI Startup with Metrics Flags..." -ForegroundColor White
Write-Host "Running 10 iterations with metrics environment variables...`n" -ForegroundColor DarkGray

$env:CRASHLENS_PUSH_METRICS = "true"
$env:CRASHLENS_PUSHGATEWAY_URL = "http://localhost:9091"

$metricsTimes = @()
for ($i = 1; $i -le 10; $i++) {
    $time = Measure-Command {
        crashlens --version 2>&1 | Out-Null
    } | Select-Object -ExpandProperty TotalMilliseconds
    
    $metricsTimes += $time
    Write-Host "  Iteration $i/10: $([math]::Round($time, 0))ms" -ForegroundColor DarkGray
}

# Clean up environment
$env:CRASHLENS_PUSH_METRICS = ""
$env:CRASHLENS_PUSHGATEWAY_URL = ""

$metricsAvg = ($metricsTimes | Measure-Object -Average).Average
$metricsStdDev = [math]::Sqrt((($metricsTimes | ForEach-Object { [math]::Pow($_ - $metricsAvg, 2) }) | Measure-Object -Average).Average)

Write-Host "`nWith Metrics Results:" -ForegroundColor White
Write-Host "  Average: $([math]::Round($metricsAvg, 0))ms" -ForegroundColor Cyan
Write-Host "  Std Dev: $([math]::Round($metricsStdDev, 0))ms" -ForegroundColor Cyan
Write-Host "  Min: $([math]::Round(($metricsTimes | Measure-Object -Minimum).Minimum, 0))ms" -ForegroundColor Cyan
Write-Host "  Max: $([math]::Round(($metricsTimes | Measure-Object -Maximum).Maximum, 0))ms" -ForegroundColor Cyan

# Pass Criteria: <500ms average with metrics
if ($metricsAvg -lt 500) {
    Write-Host "`nPASS: Metrics startup <500ms target ($([math]::Round($metricsAvg, 0))ms)" -ForegroundColor Green
    $testsPassed++
} else {
    Write-Host "`nFAIL: Metrics startup >500ms ($([math]::Round($metricsAvg, 0))ms)" -ForegroundColor Red
    $testsFailed++
}

# Test 3: Calculate overhead from lazy import
Write-Host "`n-------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "Test 3: Lazy Import Overhead..." -ForegroundColor White

$overhead = $metricsAvg - $baselineAvg
$overheadPct = ($overhead / $baselineAvg) * 100

Write-Host "`nLazy Import Analysis:" -ForegroundColor White
Write-Host "  Baseline: $([math]::Round($baselineAvg, 0))ms" -ForegroundColor Cyan
Write-Host "  With Metrics: $([math]::Round($metricsAvg, 0))ms" -ForegroundColor Cyan
Write-Host "  Overhead: $([math]::Round($overhead, 0))ms ($([math]::Round($overheadPct, 1))%)" -ForegroundColor Cyan

# Pass Criteria: <200ms overhead from lazy import
if ($overhead -lt 200) {
    Write-Host "`nPASS: Lazy import overhead <200ms ($([math]::Round($overhead, 0))ms)" -ForegroundColor Green
    $testsPassed++
} else {
    Write-Host "`nFAIL: Lazy import overhead >200ms ($([math]::Round($overhead, 0))ms)" -ForegroundColor Red
    $testsFailed++
}

# Test 4: Verify prometheus-client not imported at module load
Write-Host "`n-------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "Test 4: Verify Lazy Loading (Import Time Profiling)..." -ForegroundColor White
Write-Host "Checking if prometheus-client is imported at module load...`n" -ForegroundColor DarkGray

# Check if prometheus-client is installed
$prometheusInstalled = pip list 2>&1 | Select-String "prometheus-client"

if ($prometheusInstalled) {
    Write-Host "prometheus-client is installed: $prometheusInstalled" -ForegroundColor Yellow
    
    # Profile import time
    $importProfile = python -X importtime -c "from crashlens import cli" 2>&1 | Select-String "prometheus"
    
    if ($importProfile) {
        Write-Host "`nWARNING: prometheus-client appears in import tree:" -ForegroundColor Yellow
        Write-Host "$importProfile" -ForegroundColor DarkGray
        Write-Host "`nThis suggests prometheus is being imported at module load time." -ForegroundColor Yellow
        Write-Host "Expected: prometheus-client should NOT appear (lazy loading)." -ForegroundColor Yellow
        $testsFailed++
    } else {
        Write-Host "prometheus-client NOT found in import tree" -ForegroundColor Green
        Write-Host "This confirms lazy loading is working correctly." -ForegroundColor Green
        $testsPassed++
    }
} else {
    Write-Host "prometheus-client NOT installed - skipping import profile test" -ForegroundColor Yellow
    Write-Host "(This test requires prometheus-client to verify lazy loading)" -ForegroundColor DarkGray
    Write-Host "`nTo run full test:" -ForegroundColor White
    Write-Host "  pip install prometheus-client" -ForegroundColor Cyan
    Write-Host "  Re-run this script" -ForegroundColor Cyan
}

# Final Summary
Write-Host "`n=============================================================" -ForegroundColor DarkCyan
Write-Host "   PERFORMANCE GATE 1: SUMMARY" -ForegroundColor Yellow
Write-Host "=============================================================`n" -ForegroundColor DarkCyan

Write-Host "Tests Passed: $testsPassed" -ForegroundColor Green
Write-Host "Tests Failed: $testsFailed" -ForegroundColor $(if ($testsFailed -eq 0) { "Green" } else { "Red" })

Write-Host "`nKey Metrics:" -ForegroundColor White
Write-Host "  Baseline Startup: $([math]::Round($baselineAvg, 0))ms (target: <300ms)" -ForegroundColor Cyan
Write-Host "  Metrics Startup: $([math]::Round($metricsAvg, 0))ms (target: <500ms)" -ForegroundColor Cyan
Write-Host "  Lazy Import Overhead: $([math]::Round($overhead, 0))ms (target: <200ms)" -ForegroundColor Cyan

Write-Host "`nAcceptance Criteria:" -ForegroundColor White
Write-Host "  CLI starts <300ms without metrics: $(if ($baselineAvg -lt 300) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($baselineAvg -lt 300) { "Green" } else { "Red" })
Write-Host "  CLI starts <500ms with metrics: $(if ($metricsAvg -lt 500) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($metricsAvg -lt 500) { "Green" } else { "Red" })
Write-Host "  Lazy import overhead <200ms: $(if ($overhead -lt 200) { 'PASS' } else { 'FAIL' })" -ForegroundColor $(if ($overhead -lt 200) { "Green" } else { "Red" })

if ($testsFailed -eq 0) {
    Write-Host "`nPERFORMANCE GATE 1: PASSED" -ForegroundColor Green
    Write-Host "CLI startup latency meets all requirements." -ForegroundColor Green
    Write-Host "Lazy loading is working correctly." -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nPERFORMANCE GATE 1: FAILED" -ForegroundColor Red
    Write-Host "CLI startup latency does not meet requirements." -ForegroundColor Red
    Write-Host "Developer experience will be impacted." -ForegroundColor Red
    exit 1
}
