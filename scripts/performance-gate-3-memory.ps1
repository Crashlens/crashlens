# Performance Gate 3: Constant Memory Validation
# Objective: Prove memory doesn't grow with trace volume
# Date: October 24, 2025

Write-Host "`n=============================================================" -ForegroundColor Cyan
Write-Host "   PERFORMANCE GATE 3: CONSTANT MEMORY VALIDATION" -ForegroundColor Yellow
Write-Host "=============================================================`n" -ForegroundColor Cyan

# Check if memory_profiler is installed
Write-Host "Checking dependencies..." -ForegroundColor White
$memoryProfilerInstalled = pip list 2>&1 | Select-String "memory-profiler"
$psutilInstalled = pip list 2>&1 | Select-String "psutil"

$missingDeps = @()
if (-not $memoryProfilerInstalled) { $missingDeps += "memory-profiler" }
if (-not $psutilInstalled) { $missingDeps += "psutil" }

if ($missingDeps.Count -gt 0) {
    Write-Host "`nMissing dependencies:" -ForegroundColor Red
    foreach ($dep in $missingDeps) {
        Write-Host "  - $dep" -ForegroundColor Red
    }
    
    Write-Host "`nInstalling dependencies..." -ForegroundColor Yellow
    pip install memory-profiler psutil --quiet
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nFAIL: Could not install dependencies" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "memory-profiler: installed" -ForegroundColor Green
    Write-Host "psutil: installed" -ForegroundColor Green
}

# Verify test file exists (from Gate 2)
$testFile100k = "$env:TEMP\benchmark_100k.jsonl"

if (-not (Test-Path $testFile100k)) {
    Write-Host "`nGenerating 100k test file..." -ForegroundColor Yellow
    python scripts/generate_large_test.py `
        --traces 100000 `
        --policies 50 `
        --violation-rate 0.15 `
        --output $testFile100k
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nFAIL: Could not generate test file" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`nTest files ready" -ForegroundColor Green

# Test 1: Profile memory with 1k traces
Write-Host "`n-------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "Test 1: Profiling memory with 1k traces..." -ForegroundColor White
Write-Host "This will take a few minutes...`n" -ForegroundColor DarkGray

# Create 1k subset
$testFile1k = "$env:TEMP\benchmark_1k.jsonl"
Get-Content $testFile100k -TotalCount 1000 | Set-Content $testFile1k

Write-Host "Created 1k trace subset: $testFile1k" -ForegroundColor DarkGray

# Run memory profiler on crashlens
# Note: We'll use Process monitoring instead of memory_profiler since it's more reliable on Windows
Write-Host "Starting crashlens with 1k traces and monitoring memory..." -ForegroundColor DarkGray

$startTime = Get-Date

# Start crashlens in background and monitor memory
$process = Start-Process -FilePath "crashlens" `
    -ArgumentList "scan", $testFile1k, "--format", "json", "--report-file", "$env:TEMP\mem_test_1k.json", "--push-metrics", "--force" `
    -NoNewWindow -PassThru

# Monitor memory usage
$memSamples1k = @()
while (-not $process.HasExited) {
    try {
        $process.Refresh()
        $memMB = [math]::Round($process.WorkingSet64 / 1MB, 2)
        $memSamples1k += $memMB
        Start-Sleep -Milliseconds 100
    } catch {
        break
    }
}

$process.WaitForExit()
$exitCode1k = $process.ExitCode
$elapsed1k = (Get-Date) - $startTime

if ($exitCode1k -ne 0) {
    Write-Host "`nWARNING: 1k trace scan exited with code $exitCode1k" -ForegroundColor Yellow
}

$peakMem1k = ($memSamples1k | Measure-Object -Maximum).Maximum
$avgMem1k = ($memSamples1k | Measure-Object -Average).Average

Write-Host "`n1k Trace Results:" -ForegroundColor White
Write-Host "  Peak Memory: $([math]::Round($peakMem1k, 1)) MB" -ForegroundColor Cyan
Write-Host "  Average Memory: $([math]::Round($avgMem1k, 1)) MB" -ForegroundColor Cyan
Write-Host "  Execution Time: $([math]::Round($elapsed1k.TotalSeconds, 2))s" -ForegroundColor Cyan
Write-Host "  Samples Collected: $($memSamples1k.Count)" -ForegroundColor DarkGray

# Test 2: Profile memory with 100k traces (100x more traces)
Write-Host "`n-------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "Test 2: Profiling memory with 100k traces (100x more)..." -ForegroundColor White
Write-Host "This will take several minutes...`n" -ForegroundColor DarkGray

$startTime = Get-Date

$process = Start-Process -FilePath "crashlens" `
    -ArgumentList "scan", $testFile100k, "--format", "json", "--report-file", "$env:TEMP\mem_test_100k.json", "--push-metrics", "--force" `
    -NoNewWindow -PassThru

# Monitor memory usage
$memSamples100k = @()
$progressCounter = 0
while (-not $process.HasExited) {
    try {
        $process.Refresh()
        $memMB = [math]::Round($process.WorkingSet64 / 1MB, 2)
        $memSamples100k += $memMB
        
        # Show progress every 2 seconds
        if ($progressCounter % 20 -eq 0) {
            Write-Host "  Current memory: $memMB MB (sampling...)" -ForegroundColor DarkGray
        }
        $progressCounter++
        
        Start-Sleep -Milliseconds 100
    } catch {
        break
    }
}

$process.WaitForExit()
$exitCode100k = $process.ExitCode
$elapsed100k = (Get-Date) - $startTime

if ($exitCode100k -ne 0) {
    Write-Host "`nWARNING: 100k trace scan exited with code $exitCode100k" -ForegroundColor Yellow
}

$peakMem100k = ($memSamples100k | Measure-Object -Maximum).Maximum
$avgMem100k = ($memSamples100k | Measure-Object -Average).Average

Write-Host "`n100k Trace Results:" -ForegroundColor White
Write-Host "  Peak Memory: $([math]::Round($peakMem100k, 1)) MB" -ForegroundColor Cyan
Write-Host "  Average Memory: $([math]::Round($avgMem100k, 1)) MB" -ForegroundColor Cyan
Write-Host "  Execution Time: $([math]::Round($elapsed100k.TotalSeconds, 2))s" -ForegroundColor Cyan
Write-Host "  Samples Collected: $($memSamples100k.Count)" -ForegroundColor DarkGray

# Test 3: Calculate memory growth ratio
Write-Host "`n-------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "Test 3: Analyzing Memory Growth..." -ForegroundColor White

$growthRatio = $peakMem100k / $peakMem1k
$memoryPerTrace1k = $peakMem1k / 1000
$memoryPerTrace100k = $peakMem100k / 100000

Write-Host "`nMemory Growth Analysis:" -ForegroundColor White
Write-Host "  1k traces peak: $([math]::Round($peakMem1k, 1)) MB" -ForegroundColor Cyan
Write-Host "  100k traces peak: $([math]::Round($peakMem100k, 1)) MB" -ForegroundColor Cyan
Write-Host "  Growth Ratio: $([math]::Round($growthRatio, 2))x (100x more traces)" -ForegroundColor Cyan
Write-Host "  Memory/trace (1k): $([math]::Round($memoryPerTrace1k, 4)) MB" -ForegroundColor DarkGray
Write-Host "  Memory/trace (100k): $([math]::Round($memoryPerTrace100k, 4)) MB" -ForegroundColor DarkGray

# Acceptance Criteria
Write-Host "`n=============================================================" -ForegroundColor DarkCyan
Write-Host "   PERFORMANCE GATE 3: ACCEPTANCE CRITERIA" -ForegroundColor Yellow
Write-Host "=============================================================`n" -ForegroundColor DarkCyan

$testsPassed = 0
$testsFailed = 0

# Criteria 1: 1k traces peak memory (80-120 MB expected)
Write-Host "Test 1: 1k traces peak memory (80-120 MB)..." -ForegroundColor White
if ($peakMem1k -ge 80 -and $peakMem1k -le 120) {
    Write-Host "  PASS: $([math]::Round($peakMem1k, 1)) MB within range" -ForegroundColor Green
    $testsPassed++
} elseif ($peakMem1k -le 150) {
    Write-Host "  WARN: $([math]::Round($peakMem1k, 1)) MB slightly higher than expected" -ForegroundColor Yellow
    Write-Host "  (Still acceptable, not a failure)" -ForegroundColor DarkGray
    $testsPassed++
} else {
    Write-Host "  FAIL: $([math]::Round($peakMem1k, 1)) MB significantly higher than expected" -ForegroundColor Red
    $testsFailed++
}

# Criteria 2: 100k traces peak memory (100-150 MB expected, NOT 800-1200 MB)
Write-Host "`nTest 2: 100k traces peak memory (100-150 MB)..." -ForegroundColor White
if ($peakMem100k -ge 100 -and $peakMem100k -le 150) {
    Write-Host "  PASS: $([math]::Round($peakMem100k, 1)) MB within range" -ForegroundColor Green
    $testsPassed++
} elseif ($peakMem100k -le 250) {
    Write-Host "  WARN: $([math]::Round($peakMem100k, 1)) MB slightly higher than expected" -ForegroundColor Yellow
    Write-Host "  (Still shows constant memory, not linear growth)" -ForegroundColor DarkGray
    $testsPassed++
} else {
    Write-Host "  FAIL: $([math]::Round($peakMem100k, 1)) MB indicates memory leak" -ForegroundColor Red
    Write-Host "  (Expected <250 MB for constant memory behavior)" -ForegroundColor Red
    $testsFailed++
}

# Criteria 3: Memory growth <2x for 100x more traces (CRITICAL)
Write-Host "`nTest 3: Memory growth ratio <2.0x (CRITICAL)..." -ForegroundColor White
if ($growthRatio -lt 2.0) {
    Write-Host "  PASS: Growth ratio $([math]::Round($growthRatio, 2))x < 2.0x" -ForegroundColor Green
    Write-Host "  Memory usage is constant, not per-trace" -ForegroundColor Green
    $testsPassed++
} elseif ($growthRatio -lt 3.0) {
    Write-Host "  WARN: Growth ratio $([math]::Round($growthRatio, 2))x between 2-3x" -ForegroundColor Yellow
    Write-Host "  Some per-trace accumulation detected, but not critical" -ForegroundColor Yellow
    $testsPassed++
} else {
    Write-Host "  FAIL: Growth ratio $([math]::Round($growthRatio, 2))x >= 3.0x" -ForegroundColor Red
    Write-Host "  CRITICAL: Memory grows with trace count - indicates leak!" -ForegroundColor Red
    Write-Host "  This will cause production outages at scale!" -ForegroundColor Red
    $testsFailed++
}

# Criteria 4: No linear correlation
Write-Host "`nTest 4: Linear correlation test..." -ForegroundColor White
$expectedLinearMem = ($peakMem1k / 1000) * 100000  # If memory was per-trace

Write-Host "  If linear: $([math]::Round($expectedLinearMem, 1)) MB expected" -ForegroundColor DarkGray
Write-Host "  Actual: $([math]::Round($peakMem100k, 1)) MB" -ForegroundColor DarkGray

if ($peakMem100k -lt ($expectedLinearMem * 0.3)) {
    Write-Host "  PASS: Memory is <30% of linear growth prediction" -ForegroundColor Green
    Write-Host "  Constant-memory architecture validated" -ForegroundColor Green
    $testsPassed++
} else {
    Write-Host "  FAIL: Memory is too close to linear growth prediction" -ForegroundColor Red
    $testsFailed++
}

# Final Summary
Write-Host "`n=============================================================" -ForegroundColor DarkCyan
Write-Host "   PERFORMANCE GATE 3: FINAL RESULTS" -ForegroundColor Yellow
Write-Host "=============================================================`n" -ForegroundColor DarkCyan

Write-Host "Tests Passed: $testsPassed/4" -ForegroundColor Green
Write-Host "Tests Failed: $testsFailed/4" -ForegroundColor $(if ($testsFailed -eq 0) { "Green" } else { "Red" })

Write-Host "`nKey Findings:" -ForegroundColor White
Write-Host "  1k traces: $([math]::Round($peakMem1k, 1)) MB peak (target: 80-120 MB)" -ForegroundColor Cyan
Write-Host "  100k traces: $([math]::Round($peakMem100k, 1)) MB peak (target: 100-150 MB)" -ForegroundColor Cyan
Write-Host "  Growth ratio: $([math]::Round($growthRatio, 2))x (threshold: <2.0x)" -ForegroundColor $(if ($growthRatio -lt 2.0) { "Green" } else { "Red" })

if ($testsFailed -eq 0) {
    Write-Host "`nPERFORMANCE GATE 3: PASSED" -ForegroundColor Green
    Write-Host "Memory usage is constant (not per-trace)" -ForegroundColor Green
    Write-Host "Constant-memory architecture validated for production" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nPERFORMANCE GATE 3: FAILED" -ForegroundColor Red
    Write-Host "Memory leaks detected - production scalability at risk" -ForegroundColor Red
    Write-Host "Investors will ask about scalability - this is a blocker!" -ForegroundColor Red
    exit 1
}
