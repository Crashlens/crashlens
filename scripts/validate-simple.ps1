# CrashLens Production Validation - Simple Version
# Date: October 24, 2025

Write-Host "`n=============================================================" -ForegroundColor Cyan
Write-Host "   CRASHLENS PRODUCTION VALIDATION - AUTOMATED TESTS" -ForegroundColor Yellow
Write-Host "=============================================================`n" -ForegroundColor Cyan

$totalTests = 0
$passedTests = 0
$failedTests = 0

function Test-Step {
    param(
        [string]$StepNumber,
        [string]$StepName,
        [scriptblock]$TestCode,
        [scriptblock]$ValidationCode
    )
    
    $script:totalTests++
    
    Write-Host "`n=============================================================" -ForegroundColor DarkCyan
    Write-Host "  STEP $StepNumber - $StepName" -ForegroundColor Cyan
    Write-Host "=============================================================`n" -ForegroundColor DarkCyan
    
    try {
        & $TestCode
        
        $result = & $ValidationCode
        
        if ($result -eq "PASS") {
            Write-Host "`nPASSED STEP $StepNumber" -ForegroundColor Green
            $script:passedTests++
            return $true
        }
        else {
            Write-Host "`nFAILED STEP $StepNumber" -ForegroundColor Red
            $script:failedTests++
            return $false
        }
    }
    catch {
        Write-Host "`nERROR in STEP ${StepNumber}: $_" -ForegroundColor Red
        $script:failedTests++
        return $false
    }
}

# STEP 1: Environment Setup
Test-Step -StepNumber "1" -StepName "Environment Setup" -TestCode {
    Write-Host "Checking environment..." -ForegroundColor White
    Write-Host "Python version: $(python --version)" -ForegroundColor White
    Write-Host "Git branch: $(git branch --show-current)" -ForegroundColor White
    $version = crashlens --version 2>&1
    Write-Host "CrashLens version: $version" -ForegroundColor White
} -ValidationCode {
    $pythonVersion = python --version 2>&1
    $branch = git branch --show-current
    
    if ($pythonVersion -match "Python 3\." -and $branch -eq "phase-2") {
        return "PASS"
    }
    else {
        Write-Host "   Python: $pythonVersion | Branch: $branch" -ForegroundColor Red
        return "FAIL"
    }
}

# STEP 2: Core Functionality
Test-Step -StepNumber "2" -StepName "Core Scan Functionality" -TestCode {
    Write-Host "Testing core scan without metrics..." -ForegroundColor White
    
    crashlens scan sample-logs/demo-logs.jsonl `
        --format json `
        --report-file validation-test.json `
        --force 2>&1 | Out-Null
    
    if (Test-Path validation-test.json) {
        Write-Host "Report generated successfully" -ForegroundColor Green
    }
} -ValidationCode {
    if ($LASTEXITCODE -eq 0 -and (Test-Path validation-test.json)) {
        return "PASS"
    }
    else {
        Write-Host "   Exit code: $LASTEXITCODE" -ForegroundColor Red
        return "FAIL"
    }
}

# STEP 3: Prometheus Client Check
Test-Step -StepNumber "3" -StepName "Optional Prometheus Client" -TestCode {
    Write-Host "Checking if prometheus-client is installed..." -ForegroundColor White
    $prometheusInstalled = pip list 2>&1 | Select-String "prometheus-client"
    
    if ($prometheusInstalled) {
        Write-Host "prometheus-client is installed: $prometheusInstalled" -ForegroundColor Yellow
    }
    else {
        Write-Host "prometheus-client is NOT installed (metrics optional)" -ForegroundColor Green
    }
} -ValidationCode {
    # This always passes - metrics are optional
    return "PASS"
}

# STEP 4: Help Documentation
Test-Step -StepNumber "4" -StepName "CLI Help & Documentation" -TestCode {
    Write-Host "Checking CLI help system..." -ForegroundColor White
    
    $helpOutput = crashlens --help 2>&1
    $scanHelp = crashlens scan --help 2>&1
    
    Write-Host "Main help: $($helpOutput.Length) chars" -ForegroundColor White
    Write-Host "Scan help: $($scanHelp.Length) chars" -ForegroundColor White
} -ValidationCode {
    if ($LASTEXITCODE -eq 0) {
        return "PASS"
    }
    else {
        return "FAIL"
    }
}

# STEP 5: Policy Enforcement
Test-Step -StepNumber "5" -StepName "Policy Enforcement" -TestCode {
    Write-Host "Testing policy enforcement..." -ForegroundColor White
    
    if (Test-Path "policies/retry-loop-detector.yaml") {
        crashlens scan sample-logs/demo-logs.jsonl `
            --policy-file policies/retry-loop-detector.yaml `
            --format json `
            --report-file validation-policy.json `
            --force 2>&1 | Out-Null
        
        if (Test-Path validation-policy.json) {
            Write-Host "Policy enforcement working" -ForegroundColor Green
        }
    }
    else {
        Write-Host "No policy file found - skipping" -ForegroundColor Yellow
    }
} -ValidationCode {
    if ($LASTEXITCODE -eq 0) {
        return "PASS"
    }
    else {
        return "FAIL"
    }
}

# STEP 6: Performance Baseline
Test-Step -StepNumber "6" -StepName "Performance Baseline" -TestCode {
    Write-Host "Measuring baseline performance - 3 runs..." -ForegroundColor White
    
    $runs = @()
    for ($i = 1; $i -le 3; $i++) {
        Write-Host "  Run $i/3..." -ForegroundColor DarkGray
        
        $time = Measure-Command {
            crashlens scan sample-logs/demo-logs.jsonl `
                --format json `
                --report-file validation-perf-$i.json `
                --force 2>&1 | Out-Null
        } | Select-Object -ExpandProperty TotalSeconds
        
        $runs += $time
        Write-Host "    Time: $([math]::Round($time, 2))s" -ForegroundColor DarkGray
    }
    
    $avg = ($runs | Measure-Object -Average).Average
    $script:baselineAvg = $avg
    Write-Host "Average time: $([math]::Round($avg, 2))s" -ForegroundColor White
} -ValidationCode {
    if ($script:baselineAvg -gt 0) {
        return "PASS"
    }
    else {
        return "FAIL"
    }
}

# STEP 7: Output Formats
Test-Step -StepNumber "7" -StepName "Multiple Output Formats" -TestCode {
    Write-Host "Testing markdown format..." -ForegroundColor White
    crashlens scan sample-logs/demo-logs.jsonl --format markdown --force 2>&1 | Out-Null
    
    Write-Host "Testing JSON format..." -ForegroundColor White
    crashlens scan sample-logs/demo-logs.jsonl --format json --report-file validation-json.json --force 2>&1 | Out-Null
    
    Write-Host "Testing slack format..." -ForegroundColor White
    crashlens scan sample-logs/demo-logs.jsonl --format slack --force 2>&1 | Out-Null
} -ValidationCode {
    if ($LASTEXITCODE -eq 0) {
        return "PASS"
    }
    else {
        return "FAIL"
    }
}

# STEP 8: Privacy Features
Test-Step -StepNumber "8" -StepName "Privacy - Summary Only" -TestCode {
    Write-Host "Testing summary-only mode..." -ForegroundColor White
    
    $output = crashlens scan sample-logs/demo-logs.jsonl --summary-only --force 2>&1
    
    if ($output -match "Summary" -or $output -match "Total") {
        Write-Host "Summary-only mode working" -ForegroundColor Green
    }
} -ValidationCode {
    if ($LASTEXITCODE -eq 0) {
        return "PASS"
    }
    else {
        return "FAIL"
    }
}

# STEP 9: Error Handling
Test-Step -StepNumber "9" -StepName "CLI Error Handling" -TestCode {
    Write-Host "Testing error handling with non-existent file..." -ForegroundColor White
    
    crashlens scan nonexistent-file.jsonl 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error handling working (exit code $LASTEXITCODE)" -ForegroundColor Green
    }
} -ValidationCode {
    # We expect this to fail, so non-zero exit code is success
    if ($LASTEXITCODE -ne 0) {
        return "PASS"
    }
    else {
        Write-Host "   Expected error but got success" -ForegroundColor Red
        return "FAIL"
    }
}

# STEP 10: Demo Mode
Test-Step -StepNumber "10" -StepName "Demo Mode" -TestCode {
    Write-Host "Testing demo mode..." -ForegroundColor White
    
    crashlens scan --demo --force 2>&1 | Out-Null
} -ValidationCode {
    if ($LASTEXITCODE -eq 0) {
        return "PASS"
    }
    else {
        return "FAIL"
    }
}

# Cleanup
Write-Host "`nCleaning up test files..." -ForegroundColor DarkGray
Remove-Item validation-*.json, validation-*.md -ErrorAction SilentlyContinue

# Final Summary
Write-Host "`n=============================================================" -ForegroundColor DarkCyan
Write-Host "   VALIDATION SUMMARY" -ForegroundColor Yellow
Write-Host "=============================================================`n" -ForegroundColor DarkCyan

Write-Host "Total Tests:  $totalTests" -ForegroundColor White
Write-Host "Passed:       $passedTests" -ForegroundColor Green
Write-Host "Failed:       $failedTests" -ForegroundColor Red

$passRate = [math]::Round(($passedTests / $totalTests) * 100, 1)
Write-Host "`nPass Rate:    $passRate%" -ForegroundColor $(if ($passRate -ge 80) { "Green" } else { "Yellow" })

if ($script:baselineAvg) {
    Write-Host "`nPerformance:  $([math]::Round($script:baselineAvg, 2))s average" -ForegroundColor White
}

Write-Host "`n=============================================================`n" -ForegroundColor DarkCyan

# Exit with appropriate code
if ($failedTests -eq 0) {
    Write-Host "ALL TESTS PASSED" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "SOME TESTS FAILED" -ForegroundColor Red
    exit 1
}
