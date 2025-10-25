# Quick Verification Script for Prometheus Test Suite (Windows PowerShell)
# Run this to validate all tests pass in one command
# 
# Usage: .\scripts\run_all_prometheus_tests.ps1

$ErrorActionPreference = "Continue"

Write-Host "========================================================================"
Write-Host "CRASHLENS PROMETHEUS INTEGRATION TEST SUITE"
Write-Host "========================================================================"
Write-Host ""

# Track failures
$FailedTests = @()
$TotalTests = 9
$PassedTests = 0

function Run-Test {
    param(
        [string]$TestNumber,
        [string]$TestFile,
        [string]$Command
    )
    
    Write-Host "[$TestNumber/$TotalTests] Running $TestFile..." -ForegroundColor Yellow
    
    $result = $null
    if ($Command -eq "pytest") {
        $result = & pytest "tests\$TestFile" -v 2>&1
    } else {
        $result = & python $Command 2>&1
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ PASSED" -ForegroundColor Green
        $script:PassedTests++
    } else {
        Write-Host "✗ FAILED" -ForegroundColor Red
        $script:FailedTests += $TestFile
    }
    Write-Host ""
}

# Run all tests
Run-Test "1" "test_lazy_import.py" "pytest"
Run-Test "2" "test_registry_isolation.py" "pytest"
Run-Test "3" "test_cardinality_cap_and_overflow.py" "pytest"
Run-Test "4" "test_fire_and_forget_push_default_non_blocking.py" "pytest"
Run-Test "5" "test_fire_and_forget_push_strict_mode_fails.py" "pytest"
Run-Test "6" "test_push_success_failure_counters.py" "pytest"
Run-Test "7" "test_registry_cardinality_gauge_value.py" "pytest"
Run-Test "8" "test_log_rotation_to_tmp.py" "pytest"
Run-Test "9" "benchmark_memory_and_runtime.py" "benchmarks\benchmark_memory_and_runtime.py"

Write-Host "========================================================================"
if ($FailedTests.Count -eq 0) {
    Write-Host "ALL TESTS PASSED ✓" -ForegroundColor Green
    Write-Host "========================================================================"
    Write-Host "Production Readiness: ✅ VERIFIED"
    Write-Host "  - Lazy loading: ✅"
    Write-Host "  - Registry isolation: ✅"
    Write-Host "  - Cardinality cap (500): ✅"
    Write-Host "  - Non-blocking push: ✅"
    Write-Host "  - Strict mode: ✅"
    Write-Host "  - Push counters: ✅"
    Write-Host "  - Cardinality gauge: ✅"
    Write-Host "  - Log rotation: ✅"
    Write-Host "  - Performance (<10% overhead): ✅"
    Write-Host "========================================================================"
    Write-Host ""
    Write-Host "Summary: $PassedTests/$TotalTests tests passed" -ForegroundColor Green
    exit 0
} else {
    Write-Host "SOME TESTS FAILED ✗" -ForegroundColor Red
    Write-Host "========================================================================"
    Write-Host "Failed tests:"
    foreach ($test in $FailedTests) {
        Write-Host "  ✗ $test" -ForegroundColor Red
    }
    Write-Host "========================================================================"
    Write-Host ""
    Write-Host "Summary: $PassedTests/$TotalTests tests passed" -ForegroundColor Yellow
    exit 1
}
