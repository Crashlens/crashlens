# CrashLens Production Validation - Automated Test Script
# Windows PowerShell Version
# Date: October 24, 2025

Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "║     CRASHLENS PRODUCTION VALIDATION - AUTOMATED TESTS         ║" -ForegroundColor Yellow
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

$totalTests = 0
$passedTests = 0
$failedTests = 0
$warningTests = 0

function Test-Step {
    param(
        [string]$StepNumber,
        [string]$StepName,
        [scriptblock]$TestCode,
        [scriptblock]$ValidationCode
    )
    
    $script:totalTests++
    
    Write-Host "`n═══════════════════════════════════════════════════════════════" -ForegroundColor DarkCyan
    Write-Host "  STEP $StepNumber - $StepName" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════════`n" -ForegroundColor DarkCyan
    
    try {
        # Run the test
        & $TestCode
        
        # Validate results
        $result = & $ValidationCode
        
        if ($result -eq "PASS") {
            Write-Host "`n✅ STEP $StepNumber PASSED" -ForegroundColor Green
            $script:passedTests++
            return $true
        }
        elseif ($result -eq "WARN") {
            Write-Host "`n⚠️  STEP $StepNumber WARNING" -ForegroundColor Yellow
            $script:warningTests++
            return $true
        }
        else {
            Write-Host "`n❌ STEP $StepNumber FAILED" -ForegroundColor Red
            $script:failedTests++
            return $false
        }
    }
    catch {
        Write-Host "`n❌ STEP $StepNumber EXCEPTION: $($_.Exception.Message)" -ForegroundColor Red
        $script:failedTests++
        return $false
    }
}

# Clean up old test files
Remove-Item validation-*.json, validation-*.log, validation-*.md, test-*.md -ErrorAction SilentlyContinue

# STEP 1: Clean Environment
Test-Step -StepNumber "1" -StepName "Clean Environment Setup" -TestCode {
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor White
    Write-Host "Python version: $(python --version)" -ForegroundColor White
    Write-Host "Git branch: $(git branch --show-current)" -ForegroundColor White
    
    # Check for crashlens installation
    $version = crashlens --version 2>&1
    Write-Host "CrashLens version: $version" -ForegroundColor White
    
} -ValidationCode {
    $pythonVersion = python --version 2>&1
    $branch = git branch --show-current
    
    if ($pythonVersion -match "Python 3\.(8|9|1[0-9])" -and $branch -eq "phase-2") {
        return "PASS"
    }
    else {
        Write-Host "   Python version: $pythonVersion" -ForegroundColor Red
        Write-Host "   Branch: $branch" -ForegroundColor Red
        return "FAIL"
    }
}

# STEP 2: Core Functionality Without Metrics
Test-Step -StepNumber "2" -StepName "Core Scan Functionality" -TestCode {
    Write-Host "Testing core scan without metrics..." -ForegroundColor White
    
    crashlens scan sample-logs/demo-logs.jsonl `
        --format json `
        --report-file validation-core-scan.json `
        --force 2>&1 | Out-Null
    
    Write-Host "Exit code: $LASTEXITCODE" -ForegroundColor $(if ($LASTEXITCODE -eq 0) { "Green" } else { "Red" })
    
    if (Test-Path validation-core-scan.json) {
        $reportSize = (Get-Item validation-core-scan.json).Length
        Write-Host "Report generated: $reportSize bytes" -ForegroundColor Green
    }
    
} -ValidationCode {
    if ($LASTEXITCODE -eq 0 -and (Test-Path validation-core-scan.json)) {
        return "PASS"
    }
    return "FAIL"
}

# STEP 3: Check for Prometheus Client
Test-Step -StepNumber "3" -StepName "Prometheus Client Check" -TestCode {
    Write-Host "Checking for prometheus-client installation..." -ForegroundColor White
    
    $prometheusInstalled = pip list | Select-String "prometheus-client"
    
    if ($prometheusInstalled) {
        Write-Host "✓ prometheus-client found: $prometheusInstalled" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  prometheus-client not installed" -ForegroundColor Yellow
        Write-Host "   This is OK - metrics are optional" -ForegroundColor DarkGray
    }
    
} -ValidationCode {
    $prometheusInstalled = pip list | Select-String "prometheus-client"
    
    if ($prometheusInstalled) {
        return "PASS"
    }
    return "WARN"  # Warning, not failure - metrics are optional
}

# STEP 4: Test CLI Help
Test-Step -StepNumber "4" -StepName "CLI Help & Documentation" -TestCode {
    Write-Host "Testing CLI help system..." -ForegroundColor White
    
    crashlens --help | Out-Null
    $helpExitCode = $LASTEXITCODE
    Write-Host "crashlens --help: Exit code $helpExitCode" -ForegroundColor $(if ($helpExitCode -eq 0) { "Green" } else { "Red" })
    
    crashlens scan --help | Out-Null
    $scanHelpExitCode = $LASTEXITCODE
    Write-Host "crashlens scan --help: Exit code $scanHelpExitCode" -ForegroundColor $(if ($scanHelpExitCode -eq 0) { "Green" } else { "Red" })
    
    # Check for metrics flags in help
    $metricsFlags = crashlens scan --help | Select-String "push-metrics|metrics-http"
    if ($metricsFlags) {
        Write-Host "✓ Metrics flags found in help" -ForegroundColor Green
    }
    
} -ValidationCode {
    if ($helpExitCode -eq 0 -and $scanHelpExitCode -eq 0) {
        return "PASS"
    }
    return "FAIL"
}

# STEP 5: Test Policy Check
Test-Step -StepNumber "5" -StepName "Policy Enforcement" -TestCode {
    Write-Host "Testing policy check..." -ForegroundColor White
    
    crashlens policy-check sample-logs/demo-logs.jsonl `
        --policy-template retry-loop-prevention `
        --report-file validation-policy-check.md `
        --force 2>&1 | Out-Null
    
    Write-Host "Exit code: $LASTEXITCODE" -ForegroundColor $(if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 1) { "Green" } else { "Red" })
    
    if (Test-Path validation-policy-check.md) {
        $reportSize = (Get-Item validation-policy-check.md).Length
        Write-Host "Policy report generated: $reportSize bytes" -ForegroundColor Green
    }
    
} -ValidationCode {
    # Exit code 0 (no violations) or 1 (violations found) are both success
    if (($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 1) -and (Test-Path validation-policy-check.md)) {
        return "PASS"
    }
    return "FAIL"
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
                --force | Out-Null
        } | Select-Object -ExpandProperty TotalSeconds
        
        $runs += $time
        Write-Host "    Time: $([math]::Round($time, 2))s" -ForegroundColor DarkGray
    }
    
    $avg = ($runs | Measure-Object -Average).Average
    $stdDev = [math]::Sqrt((($runs | ForEach-Object { [math]::Pow($_ - $avg, 2) }) | Measure-Object -Sum).Sum / 3)
    
    Write-Host "`nPerformance statistics:" -ForegroundColor Cyan
    Write-Host "  Average: $([math]::Round($avg, 3))s" -ForegroundColor White
    Write-Host "  Std Dev: $([math]::Round($stdDev, 3))s" -ForegroundColor White
    Write-Host "  CV: $([math]::Round(($stdDev/$avg)*100, 2))%" -ForegroundColor White
    
    # Store for later comparison
    $global:baselineAvg = $avg
    $global:baselineStdDev = $stdDev
    
} -ValidationCode {
    if ($global:baselineAvg -gt 0 -and $global:baselineStdDev -ge 0) {
        return "PASS"
    }
    return "FAIL"
}

# STEP 7: Test Different Output Formats
Test-Step -StepNumber "7" -StepName "Output Format Support" -TestCode {
    Write-Host "Testing output formats..." -ForegroundColor White
    
    # Markdown
    crashlens scan sample-logs/demo-logs.jsonl `
        --format markdown `
        --report-file validation-markdown.md `
        --force | Out-Null
    $mdSuccess = $LASTEXITCODE -eq 0 -and (Test-Path validation-markdown.md)
    Write-Host "  Markdown: $(if ($mdSuccess) { '✓' } else { '✗' })" -ForegroundColor $(if ($mdSuccess) { "Green" } else { "Red" })
    
    # JSON
    crashlens scan sample-logs/demo-logs.jsonl `
        --format json `
        --report-file validation-json.json `
        --force | Out-Null
    $jsonSuccess = $LASTEXITCODE -eq 0 -and (Test-Path validation-json.json)
    Write-Host "  JSON: $(if ($jsonSuccess) { '✓' } else { '✗' })" -ForegroundColor $(if ($jsonSuccess) { "Green" } else { "Red" })
    
    # Slack
    crashlens scan sample-logs/demo-logs.jsonl `
        --format slack `
        --report-file validation-slack.md `
        --force | Out-Null
    $slackSuccess = $LASTEXITCODE -eq 0 -and (Test-Path validation-slack.md)
    Write-Host "  Slack: $(if ($slackSuccess) { '✓' } else { '✗' })" -ForegroundColor $(if ($slackSuccess) { "Green" } else { "Red" })
    
    $global:formatTestSuccess = $mdSuccess -and $jsonSuccess -and $slackSuccess
    
} -ValidationCode {
    if ($global:formatTestSuccess) {
        return "PASS"
    }
    return "FAIL"
}

# STEP 8: Test Summary-Only Mode (Privacy)
Test-Step -StepNumber "8" -StepName "Privacy Features (Summary-Only)" -TestCode {
    Write-Host "Testing summary-only mode (privacy feature)..." -ForegroundColor White
    
    crashlens scan sample-logs/demo-logs.jsonl `
        --summary-only `
        --format markdown `
        --report-file validation-summary-only.md `
        --force | Out-Null
    
    if (Test-Path validation-summary-only.md) {
        $content = Get-Content validation-summary-only.md -Raw
        
        # Check that trace IDs are not in summary-only output
        if ($content -match "trace.*id|traceId" -and $content -notmatch "Trace IDs suppressed") {
            Write-Host "  ⚠️  Trace IDs may be exposed in summary-only mode" -ForegroundColor Yellow
        }
        else {
            Write-Host "  ✓ Summary-only mode working (no trace ID exposure)" -ForegroundColor Green
        }
    }
    
} -ValidationCode {
    if ($LASTEXITCODE -eq 0 -and (Test-Path validation-summary-only.md)) {
        return "PASS"
    }
    return "FAIL"
}

# STEP 9: Test CLI Robustness
Test-Step -StepNumber "9" -StepName "CLI Error Handling" -TestCode {
    Write-Host "Testing CLI error handling..." -ForegroundColor White
    
    # Test with non-existent file
    crashlens scan nonexistent-file.jsonl 2>&1 | Out-Null
    $nonExistentExitCode = $LASTEXITCODE
    Write-Host "  Non-existent file: Exit code $nonExistentExitCode $(if ($nonExistentExitCode -ne 0) { '✓' } else { '✗' })" -ForegroundColor $(if ($nonExistentExitCode -ne 0) { "Green" } else { "Red" })
    
    # Test with invalid format
    crashlens scan sample-logs/demo-logs.jsonl --format invalid 2>&1 | Out-Null
    $invalidFormatExitCode = $LASTEXITCODE
    Write-Host "  Invalid format: Exit code $invalidFormatExitCode $(if ($invalidFormatExitCode -ne 0) { '✓' } else { '✗' })" -ForegroundColor $(if ($invalidFormatExitCode -ne 0) { "Green" } else { "Red" })
    
    $global:errorHandlingSuccess = ($nonExistentExitCode -ne 0) -and ($invalidFormatExitCode -ne 0)
    
} -ValidationCode {
    if ($global:errorHandlingSuccess) {
        return "PASS"
    }
    return "FAIL"
}

# STEP 10: Test Demo Mode
Test-Step -StepNumber "10" -StepName "Demo Mode (Built-in Data)" -TestCode {
    Write-Host "Testing demo mode..." -ForegroundColor White
    
    crashlens scan --demo --force 2>&1 | Out-Null
    
    Write-Host "Exit code: $LASTEXITCODE" -ForegroundColor $(if ($LASTEXITCODE -eq 0) { "Green" } else { "Red" })
    
} -ValidationCode {
    if ($LASTEXITCODE -eq 0) {
        return "PASS"
    }
    return "FAIL"
}

# ═══════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════

Write-Host "`n╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "║                    VALIDATION SUMMARY                         ║" -ForegroundColor Yellow
Write-Host "║                                                               ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

Write-Host "Total Tests: $totalTests" -ForegroundColor White
Write-Host "Passed: " -NoNewline -ForegroundColor White
Write-Host "$passedTests" -ForegroundColor Green
Write-Host "Warnings: " -NoNewline -ForegroundColor White
Write-Host "$warningTests" -ForegroundColor Yellow
Write-Host "Failed: " -NoNewline -ForegroundColor White
Write-Host "$failedTests" -ForegroundColor Red

$passRate = [math]::Round(($passedTests / $totalTests) * 100, 1)
Write-Host "`nPass Rate: " -NoNewline -ForegroundColor White
Write-Host "$passRate%" -ForegroundColor $(if ($passRate -ge 90) { "Green" } elseif ($passRate -ge 70) { "Yellow" } else { "Red" })

if ($failedTests -eq 0) {
    Write-Host "`n✅ ALL TESTS PASSED - READY FOR DEMO!" -ForegroundColor Green -BackgroundColor DarkGreen
}
elseif ($failedTests -le 2) {
    Write-Host "`n⚠️  MOSTLY PASSING - Review failures before demo" -ForegroundColor Yellow
}
else {
    Write-Host "`n❌ MULTIPLE FAILURES - Address issues before demo" -ForegroundColor Red -BackgroundColor DarkRed
}

# Performance Summary
if ($global:baselineAvg) {
    Write-Host "`nPerformance Baseline:" -ForegroundColor Cyan
    Write-Host "  Average scan time: $([math]::Round($global:baselineAvg, 2))s" -ForegroundColor White
    Write-Host "  Standard deviation: $([math]::Round($global:baselineStdDev, 3))s" -ForegroundColor White
}

# Cleanup
Write-Host "`nCleaning up test files..." -ForegroundColor DarkGray
Remove-Item validation-*.json, validation-*.md, killswitch-test.log -ErrorAction SilentlyContinue

Write-Host "`n═══════════════════════════════════════════════════════════════`n" -ForegroundColor DarkCyan

# Exit with appropriate code
if ($failedTests -eq 0) {
    exit 0
}
else {
    exit 1
}
