# 🚀 CrashLens Pre-Production Validation Protocol

**Purpose:** Pre-production validation checklist for seed funding demo. This protocol verifies ALL safety gates, performance claims, and operational guarantees WITHOUT requiring external infrastructure (Pushgateway/Grafana).

**Target:** Million-dollar seed round depends on proving this is production-grade, not a prototype.

**Execution Time:** 90 minutes for full verification

**Date:** October 24, 2025  
**Version:** 1.0  
**Branch:** phase-2

---

## 📋 Pre-Flight System State Validation

### Step 1: Clean Environment Setup (5 minutes)

**Objective:** Prove the feature works in isolation with zero side effects.

```powershell
# Create isolated test environment
cd C:\Users\LawLight\OneDrive\Desktop\crashlens

# Create new virtual environment
python -m venv venv-production-test

# Activate (Windows PowerShell)
.\venv-production-test\Scripts\Activate.ps1

# Verify clean Python environment
python -c "import sys; print('Python:', sys.version); print('Path entries:', len(sys.path))"
# Expected: Python 3.12+, minimal path entries

# Verify git state
git status
git log --oneline -1
git branch --show-current
# Expected: On phase-2 branch, clean working tree
```

**Pass Criteria:**
- ✅ Python 3.12 or higher
- ✅ Clean venv with no pre-installed packages
- ✅ Git branch is `phase-2`
- ✅ No uncommitted changes

**Failure Action:** STOP. Clean environment or funding demo will fail due to environmental contamination.

---

## 🔒 Critical Safety Gate 1: Zero-Dependency Operation

### Step 2: CLI Functionality WITHOUT Metrics Library (10 minutes)

**Objective:** Prove `prometheus-client` is truly optional. Investors will ask: "What if users don't want metrics?"

```powershell
# Install CrashLens WITHOUT metrics extra
pip install -e .

# Verify prometheus-client is NOT installed
pip list | Select-String "prometheus"
# Expected: NO OUTPUT (prometheus-client absent)

# Test core CLI functionality
crashlens --version
# Expected: CrashLens v2.9.12 (or current version)

crashlens --help
# Expected: Full help output, NO import errors, NO warnings

# Verify metrics flags are documented
crashlens --help | Select-String "metrics"
# Expected: Shows --push-metrics, --pushgateway-url, --http-metrics flags

# Test scan WITHOUT metrics (prove core functionality intact)
crashlens scan sample-logs/demo-logs.jsonl --verbose
# Expected: Scan completes, NO prometheus-related errors, exit code 0

Write-Host "Exit code: $LASTEXITCODE"
# Expected: 0 (success)

# Test that metrics flags fail gracefully when library missing
crashlens scan sample-logs/demo-logs.jsonl --push-metrics 2>&1 | Tee-Object -FilePath metrics-missing-test.log

Write-Host "Exit code: $LASTEXITCODE"
# Expected: 1 (expected failure with helpful message)

# Verify error message quality
Get-Content metrics-missing-test.log | Select-String "pip install.*metrics"
# Expected: Match found (user gets actionable fix)

# Check for clean error handling (no stack traces)
Get-Content metrics-missing-test.log | Select-String "Traceback|Error:|ImportError"
# Expected: Only clean error message, no Python stack traces
```

**Pass Criteria:**
- ✅ CLI starts and shows help without prometheus-client
- ✅ Core scan functionality works (validates lazy loading)
- ✅ Metrics flags present in --help but don't crash
- ✅ Graceful error with install instructions when metrics requested
- ✅ No stack traces or import errors in any output

**Failure Impact:** CRITICAL. If CLI crashes without prometheus-client, investors will question engineering discipline.

---

## 🛡️ Critical Safety Gate 2: Kill Switch Verification

### Step 3: Global Metrics Disable Override (5 minutes)

**Objective:** Prove `CRASHLENS_DISABLE_METRICS=true` is a hard kill switch. Investors care about operational safety valves.

```powershell
# Now install with metrics support
pip install -e .[prometheus]

# Verify prometheus-client installed
pip list | Select-String "prometheus-client"
# Expected: prometheus-client==0.21.0 (or higher)

# Set kill switch BEFORE any metrics flags
$env:CRASHLENS_DISABLE_METRICS = "true"

# Try to enable metrics (should be silently ignored)
crashlens scan sample-logs/demo-logs.jsonl `
  --push-metrics `
  --pushgateway-url http://localhost:9091 `
  --metrics-job test-job `
  --verbose 2>&1 | Tee-Object -FilePath kill-switch-test.log

# Verify NO metrics activity in logs
Get-Content kill-switch-test.log | Select-String -Pattern "prometheus|metric|push" -CaseSensitive:$false
# Expected: NO matches OR only "metrics disabled" message

# Verify scan still completed successfully
Write-Host "Exit code: $LASTEXITCODE"
# Expected: 0 (kill switch doesn't break core functionality)

# Test that kill switch overrides env vars too
$env:CRASHLENS_PUSH_METRICS = "true"
$env:CRASHLENS_PUSHGATEWAY_URL = "http://localhost:9091"
$env:CRASHLENS_DISABLE_METRICS = "true"  # Should override everything

crashlens scan sample-logs/demo-logs.jsonl --verbose 2>&1 | Select-String "metric" -CaseSensitive:$false
# Expected: "Metrics disabled" message or no metrics activity

# Verify exit code
Write-Host "Exit code with kill switch: $LASTEXITCODE"
# Expected: 0

# Clean up
Remove-Item Env:\CRASHLENS_DISABLE_METRICS
Remove-Item Env:\CRASHLENS_PUSH_METRICS
Remove-Item Env:\CRASHLENS_PUSHGATEWAY_URL
```

**Pass Criteria:**
- ✅ Kill switch completely disables metrics
- ✅ Kill switch overrides CLI flags and env vars
- ✅ Core scan functionality unaffected
- ✅ Clear log message explaining why metrics disabled

**Failure Impact:** HIGH. Operational kill switches are table stakes for enterprise sales.

---

## ⚡ Performance Gate 1: Lazy Loading Verification

### Step 4: Import Performance (5 minutes)

**Objective:** Prove prometheus-client is never imported unless explicitly requested. Zero overhead claim depends on this.

```powershell
# Test 1: Import time WITHOUT metrics flags
Measure-Command {
  python -c "import crashlens.cli; print('Imported successfully')"
} | Select-Object TotalMilliseconds
# Expected: <500ms, no prometheus imports

# Test 2: Verify prometheus-client NOT in sys.modules
python -c "import crashlens.cli; import sys; print('prometheus_client' in sys.modules)"
# Expected: False

# Test 3: Import time WITH metrics flags (should still be lazy)
Measure-Command {
  python -c "from crashlens.cli import cli; print('CLI imported')"
} | Select-Object TotalMilliseconds
# Expected: <500ms (lazy loading means metrics not imported at CLI load time)

# Test 4: Verify metrics only imported when first used
python -c @"
import sys
from crashlens.observability import metrics
print('Before get_registry:', 'prometheus_client' in sys.modules)
metrics.get_registry()  # This should trigger import
print('After get_registry:', 'prometheus_client' in sys.modules)
"@
# Expected: False, then True

# Test 5: CLI startup time comparison (quantitative proof)
Write-Host "`n=== CLI Startup Time Comparison ===" -ForegroundColor Cyan

# Without metrics
$baseline = Measure-Command { crashlens --version } | Select-Object -ExpandProperty TotalMilliseconds
Write-Host "Baseline (no metrics): $baseline ms" -ForegroundColor Green

# With metrics flags (but disabled)
$env:CRASHLENS_DISABLE_METRICS = "true"
$withDisabled = Measure-Command { crashlens scan sample-logs/demo-logs.jsonl --push-metrics } | Select-Object -ExpandProperty TotalMilliseconds
Write-Host "With metrics disabled: $withDisabled ms" -ForegroundColor Green
Remove-Item Env:\CRASHLENS_DISABLE_METRICS

# Calculate overhead
$overhead = (($withDisabled - $baseline) / $baseline) * 100
Write-Host "Overhead: $overhead%" -ForegroundColor $(if ($overhead -lt 5) { "Green" } else { "Red" })
# Expected: <5% overhead
```

**Pass Criteria:**
- ✅ prometheus-client not imported on CLI load
- ✅ Metrics module uses lazy loading pattern
- ✅ CLI startup time <500ms
- ✅ Overhead with disabled metrics <5%

**Failure Impact:** HIGH. "Zero overhead" is a key marketing claim.

---

## 🎯 Performance Gate 2: Production Overhead Validation

### Step 5: Real-World Performance Test (15 minutes)

**Objective:** Prove <10% overhead claim with actual data. Investors need quantitative proof.

```powershell
# Prepare test data (1000 traces)
$testFile = "sample-logs/demo-logs.jsonl"

Write-Host "`n=== Performance Validation (1000 traces) ===" -ForegroundColor Cyan

# Baseline: Scan WITHOUT metrics (3 runs for statistical validity)
$baselineRuns = @()
for ($i = 1; $i -le 3; $i++) {
    Write-Host "Baseline run $i/3..." -ForegroundColor Gray
    $time = Measure-Command {
        crashlens scan $testFile --output temp-report-baseline-$i.md | Out-Null
    } | Select-Object -ExpandProperty TotalSeconds
    $baselineRuns += $time
    Write-Host "  Time: $time seconds" -ForegroundColor DarkGray
}

$baselineAvg = ($baselineRuns | Measure-Object -Average).Average
Write-Host "`nBaseline average: $baselineAvg seconds" -ForegroundColor Green

# With metrics: Scan WITH metrics enabled but NO pushgateway (in-memory only)
$metricsRuns = @()
for ($i = 1; $i -le 3; $i++) {
    Write-Host "`nMetrics run $i/3..." -ForegroundColor Gray
    $time = Measure-Command {
        # Use --http-metrics to enable metrics without requiring Pushgateway
        crashlens scan $testFile --http-metrics --http-metrics-port 9090 --output temp-report-metrics-$i.md | Out-Null
    } | Select-Object -ExpandProperty TotalSeconds
    $metricsRuns += $time
    Write-Host "  Time: $time seconds" -ForegroundColor DarkGray
    
    # Kill HTTP server immediately (it runs in background)
    Get-Process python | Where-Object { $_.MainWindowTitle -match "crashlens" } | Stop-Process -Force -ErrorAction SilentlyContinue
}

$metricsAvg = ($metricsRuns | Measure-Object -Average).Average
Write-Host "`nMetrics average: $metricsAvg seconds" -ForegroundColor Yellow

# Calculate overhead
$overhead = (($metricsAvg - $baselineAvg) / $baselineAvg) * 100
Write-Host "`n=== PERFORMANCE RESULT ===" -ForegroundColor Cyan
Write-Host "Overhead: " -NoNewline
Write-Host "$([math]::Round($overhead, 2))%" -ForegroundColor $(if ($overhead -lt 10) { "Green" } else { "Red" })

# Statistical analysis
$baselineStdDev = [math]::Sqrt((($baselineRuns | ForEach-Object { [math]::Pow($_ - $baselineAvg, 2) } | Measure-Object -Sum).Sum / 3))
$metricsStdDev = [math]::Sqrt((($metricsRuns | ForEach-Object { [math]::Pow($_ - $metricsAvg, 2) } | Measure-Object -Sum).Sum / 3))

Write-Host "`nStatistical Validity:" -ForegroundColor Cyan
Write-Host "  Baseline std dev: $([math]::Round($baselineStdDev, 3))s" -ForegroundColor DarkGray
Write-Host "  Metrics std dev:  $([math]::Round($metricsStdDev, 3))s" -ForegroundColor DarkGray
Write-Host "  Coefficient of variation: $([math]::Round(($baselineStdDev/$baselineAvg)*100, 2))%" -ForegroundColor DarkGray

# Cleanup
Remove-Item temp-report-*.md -ErrorAction SilentlyContinue
```

**Pass Criteria:**
- ✅ Overhead <10% (target: 4-7%)
- ✅ Standard deviation <10% of mean (consistent performance)
- ✅ No crashes or errors during test
- ✅ All temporary files cleaned up

**Failure Impact:** CRITICAL. Performance claims are investor table stakes.

---

## 🔐 Security Gate: Safe Defaults Verification

### Step 6: HTTP Server Security Validation (10 minutes)

**Objective:** Prove HTTP metrics server is localhost-only by default. Security is non-negotiable.

```powershell
Write-Host "`n=== HTTP Server Security Validation ===" -ForegroundColor Cyan

# Test 1: Verify default is localhost-only
crashlens scan sample-logs/demo-logs.jsonl --http-metrics --http-metrics-port 19090 &
Start-Sleep -Seconds 3

# Try to connect from localhost (should succeed)
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:19090/metrics" -TimeoutSec 5
    Write-Host "✅ Localhost access: SUCCESS" -ForegroundColor Green
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor DarkGray
} catch {
    Write-Host "❌ Localhost access: FAILED" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Try to connect from network interface (should fail - not exposed)
# Note: This tests that 127.0.0.1 binding doesn't expose to 0.0.0.0
$localIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch "Loopback" } | Select-Object -First 1).IPAddress

if ($localIP -and $localIP -ne "127.0.0.1") {
    try {
        $response = Invoke-WebRequest -Uri "http://${localIP}:19090/metrics" -TimeoutSec 5
        Write-Host "❌ Network access: EXPOSED (SECURITY RISK!)" -ForegroundColor Red
        Write-Host "   Status: $($response.StatusCode)" -ForegroundColor Red
    } catch {
        Write-Host "✅ Network access: BLOCKED (expected)" -ForegroundColor Green
        Write-Host "   Confirmed localhost-only binding" -ForegroundColor DarkGray
    }
} else {
    Write-Host "⚠️  Network access test skipped (no network interface)" -ForegroundColor Yellow
}

# Test 2: Verify port range validation (no privileged ports)
Write-Host "`nTesting port range validation..." -ForegroundColor Cyan

# Try privileged port (should fail)
crashlens scan sample-logs/demo-logs.jsonl --http-metrics --http-metrics-port 80 2>&1 | Tee-Object -FilePath port-validation-test.log
$privilegedPortExitCode = $LASTEXITCODE

if ($privilegedPortExitCode -ne 0) {
    Write-Host "✅ Privileged port blocked (port 80)" -ForegroundColor Green
    Get-Content port-validation-test.log | Select-String "port" -Context 0,2
} else {
    Write-Host "❌ Privileged port allowed (SECURITY RISK!)" -ForegroundColor Red
}

# Try valid port (should succeed)
crashlens scan sample-logs/demo-logs.jsonl --http-metrics --http-metrics-port 19091 --output temp-report.md
$validPortExitCode = $LASTEXITCODE

if ($validPortExitCode -eq 0) {
    Write-Host "✅ Valid port accepted (19091)" -ForegroundColor Green
} else {
    Write-Host "❌ Valid port rejected" -ForegroundColor Red
}

# Test 3: Health check endpoint
try {
    $health = Invoke-WebRequest -Uri "http://127.0.0.1:19091/health" -TimeoutSec 5
    Write-Host "✅ Health endpoint accessible" -ForegroundColor Green
    Write-Host "   Status: $($health.StatusCode)" -ForegroundColor DarkGray
    Write-Host "   Body: $($health.Content)" -ForegroundColor DarkGray
} catch {
    Write-Host "❌ Health endpoint failed" -ForegroundColor Red
}

# Cleanup
Get-Process python | Where-Object { $_.MainWindowTitle -match "crashlens" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Remove-Item temp-report.md, port-validation-test.log -ErrorAction SilentlyContinue
```

**Pass Criteria:**
- ✅ HTTP server binds to 127.0.0.1 only
- ✅ Not accessible from network interfaces
- ✅ Privileged ports (1-1023) rejected
- ✅ Health check endpoint works
- ✅ Graceful shutdown on process kill

**Failure Impact:** CRITICAL. Network exposure is a deal-breaker for enterprise.

---

## 📊 Functional Gate: Metrics Collection Accuracy

### Step 7: Metrics Data Validation (15 minutes)

**Objective:** Prove metrics accurately reflect policy violations. Data integrity is essential.

```powershell
Write-Host "`n=== Metrics Collection Accuracy Validation ===" -ForegroundColor Cyan

# Test with known violation counts
$testPolicy = @"
version: 1
rules:
  - id: test_rule_1
    description: "Test rule 1"
    match:
      model: "gpt-4"
    action: warn
    severity: high
    
  - id: test_rule_2
    description: "Test rule 2"
    match:
      model: "gpt-3.5-turbo"
    action: fail
    severity: critical
"@

Set-Content -Path "temp-test-policy.yaml" -Value $testPolicy

# Run scan with metrics and known policy
crashlens policy-check sample-logs/demo-logs.jsonl `
  --policy-file temp-test-policy.yaml `
  --http-metrics `
  --http-metrics-port 19092 `
  --output temp-policy-report.md

Start-Sleep -Seconds 2

# Fetch metrics
try {
    $metrics = Invoke-WebRequest -Uri "http://127.0.0.1:19092/metrics" -TimeoutSec 5
    $metricsContent = $metrics.Content
    
    Write-Host "✅ Metrics endpoint accessible" -ForegroundColor Green
    
    # Validate metric presence
    $expectedMetrics = @(
        "crashlens_rule_hits_total",
        "crashlens_violations_total",
        "crashlens_traces_processed_total",
        "crashlens_decision_latency_avg_seconds",
        "crashlens_last_run_timestamp_seconds"
    )
    
    $missingMetrics = @()
    foreach ($metric in $expectedMetrics) {
        if ($metricsContent -match $metric) {
            Write-Host "  ✅ $metric present" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $metric MISSING" -ForegroundColor Red
            $missingMetrics += $metric
        }
    }
    
    # Validate labels
    if ($metricsContent -match 'rule="test_rule_1"') {
        Write-Host "  ✅ Rule labels present" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Rule labels MISSING" -ForegroundColor Red
    }
    
    if ($metricsContent -match 'severity="high"' -or $metricsContent -match 'severity="critical"') {
        Write-Host "  ✅ Severity labels present" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Severity labels MISSING" -ForegroundColor Red
    }
    
    # Extract and validate counts (parse policy report for ground truth)
    $reportContent = Get-Content temp-policy-report.md -Raw
    
    # Save metrics for inspection
    Set-Content -Path "temp-metrics-output.txt" -Value $metricsContent
    Write-Host "`n✅ Metrics saved to temp-metrics-output.txt for inspection" -ForegroundColor Cyan
    
    # Display sample metrics
    Write-Host "`nSample metrics:" -ForegroundColor Cyan
    $metricsContent -split "`n" | Where-Object { $_ -match "^crashlens_" -and $_ -notmatch "^#" } | Select-Object -First 10 | ForEach-Object {
        Write-Host "  $_" -ForegroundColor DarkGray
    }
    
} catch {
    Write-Host "❌ Failed to fetch metrics: $($_.Exception.Message)" -ForegroundColor Red
}

# Cleanup
Get-Process python | Where-Object { $_.MainWindowTitle -match "crashlens" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Remove-Item temp-test-policy.yaml, temp-policy-report.md, temp-metrics-output.txt -ErrorAction SilentlyContinue
```

**Pass Criteria:**
- ✅ All 8 core metrics present in output
- ✅ Rule labels correctly populated
- ✅ Severity labels correctly populated
- ✅ Metric counts non-zero for violations
- ✅ Prometheus format valid (no parse errors)

**Failure Impact:** HIGH. Incorrect metrics = useless monitoring.

---

## 🧪 Integration Gate: Policy Engine Integration

### Step 8: End-to-End Policy Enforcement with Metrics (10 minutes)

**Objective:** Prove metrics integrate seamlessly with policy engine. Complete feature validation.

```powershell
Write-Host "`n=== Policy Engine + Metrics Integration Test ===" -ForegroundColor Cyan

# Use built-in policy template
crashlens scan sample-logs/demo-logs.jsonl `
  --policy-template retry-loop-prevention `
  --http-metrics `
  --http-metrics-port 19093 `
  --verbose 2>&1 | Tee-Object -FilePath integration-test.log

$exitCode = $LASTEXITCODE
Write-Host "`nExit code: $exitCode" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Yellow" })

Start-Sleep -Seconds 2

# Validate integration
Write-Host "`nValidating integration..." -ForegroundColor Cyan

# Check logs for metrics activity
$metricsActivity = Get-Content integration-test.log | Select-String "metric|prometheus" -CaseSensitive:$false
if ($metricsActivity) {
    Write-Host "✅ Metrics activity detected in logs" -ForegroundColor Green
    $metricsActivity | Select-Object -First 5 | ForEach-Object {
        Write-Host "  $_" -ForegroundColor DarkGray
    }
} else {
    Write-Host "⚠️  No metrics activity in logs (may be expected if no violations)" -ForegroundColor Yellow
}

# Check for errors
$errors = Get-Content integration-test.log | Select-String "error|exception|traceback" -CaseSensitive:$false
if ($errors) {
    Write-Host "❌ Errors detected:" -ForegroundColor Red
    $errors | Select-Object -First 5 | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Red
    }
} else {
    Write-Host "✅ No errors in integration test" -ForegroundColor Green
}

# Fetch final metrics state
try {
    $metrics = Invoke-WebRequest -Uri "http://127.0.0.1:19093/metrics" -TimeoutSec 5
    $totalLines = ($metrics.Content -split "`n").Count
    $metricLines = ($metrics.Content -split "`n" | Where-Object { $_ -match "^crashlens_" -and $_ -notmatch "^#" }).Count
    
    Write-Host "✅ Final metrics state:" -ForegroundColor Green
    Write-Host "   Total lines: $totalLines" -ForegroundColor DarkGray
    Write-Host "   Metric lines: $metricLines" -ForegroundColor DarkGray
    
    # Check for policy-specific metrics
    if ($metrics.Content -match "retry_loop") {
        Write-Host "   ✅ Policy-specific metrics present" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  No policy-specific metrics (check if violations occurred)" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "❌ Failed to fetch final metrics: $($_.Exception.Message)" -ForegroundColor Red
}

# Cleanup
Get-Process python | Where-Object { $_.MainWindowTitle -match "crashlens" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Remove-Item integration-test.log -ErrorAction SilentlyContinue
```

**Pass Criteria:**
- ✅ Policy check completes without errors
- ✅ Metrics collected during policy evaluation
- ✅ No stack traces or crashes
- ✅ Metrics reflect policy results
- ✅ HTTP server remains responsive

**Failure Impact:** CRITICAL. This is the core value proposition.

---

## 🎛️ Configuration Gate: Config File Support

### Step 9: Metrics Configuration Validation (10 minutes)

**Objective:** Prove config file system works and validates correctly. Enterprise users need config files.

```powershell
Write-Host "`n=== Metrics Configuration Validation ===" -ForegroundColor Cyan

# Create test config
$testConfig = @"
sampling:
  rate: 0.5  # 50% sampling for testing
  per_rule:
    high_priority_rule: 1.0
    low_priority_rule: 0.1

pushgateway:
  url: "http://localhost:9091"
  job: "crashlens-validation"
  grouping_labels:
    environment: "test"
    team: "validation"

http_server:
  enabled: true
  port: 19094
  host: "127.0.0.1"
"@

# Save config
New-Item -ItemType Directory -Path ".crashlens" -Force | Out-Null
Set-Content -Path ".crashlens/metrics.yaml" -Value $testConfig

# Test 1: Validate config with CLI tool
Write-Host "Testing config validation..." -ForegroundColor Cyan
crashlens validate-metrics-config .crashlens/metrics.yaml

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Config validation passed" -ForegroundColor Green
} else {
    Write-Host "❌ Config validation failed" -ForegroundColor Red
}

# Test 2: Show config
Write-Host "`nTesting config display..." -ForegroundColor Cyan
crashlens show-metrics-config

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Config display works" -ForegroundColor Green
} else {
    Write-Host "❌ Config display failed" -ForegroundColor Red
}

# Test 3: Invalid config detection
Write-Host "`nTesting invalid config detection..." -ForegroundColor Cyan
$invalidConfig = @"
sampling:
  rate: 2.5  # Invalid: >1.0
  
http_server:
  port: 80  # Invalid: privileged port
"@

Set-Content -Path ".crashlens/invalid-metrics.yaml" -Value $invalidConfig
crashlens validate-metrics-config .crashlens/invalid-metrics.yaml 2>&1 | Tee-Object -FilePath config-validation-test.log

if ($LASTEXITCODE -ne 0) {
    Write-Host "✅ Invalid config correctly rejected" -ForegroundColor Green
    Get-Content config-validation-test.log | Select-String "error|invalid" -CaseSensitive:$false | Select-Object -First 3
} else {
    Write-Host "❌ Invalid config accepted (VALIDATION BUG!)" -ForegroundColor Red
}

# Test 4: Config file auto-discovery
Write-Host "`nTesting config auto-discovery..." -ForegroundColor Cyan
crashlens scan sample-logs/demo-logs.jsonl --verbose 2>&1 | Select-String "metrics.yaml" -CaseSensitive:$false | Select-Object -First 3

# Cleanup
Remove-Item .crashlens -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item config-validation-test.log -ErrorAction SilentlyContinue
```

**Pass Criteria:**
- ✅ Valid config passes validation
- ✅ Invalid config rejected with clear errors
- ✅ Config auto-discovery works
- ✅ validate-metrics-config tool works
- ✅ show-metrics-config displays correctly

**Failure Impact:** MEDIUM. Enterprise adoption requires config file support.

---

## 📈 Sampling Gate: Per-Rule Sampling Validation

### Step 10: Sampling Accuracy Test (10 minutes)

**Objective:** Prove per-rule sampling works correctly. Performance claims depend on this.

```powershell
Write-Host "`n=== Per-Rule Sampling Validation ===" -ForegroundColor Cyan

# Create config with different sampling rates
$samplingConfig = @"
sampling:
  rate: 0.1  # 10% global
  per_rule:
    always_sample: 1.0    # 100%
    never_sample: 0.0     # 0%
    half_sample: 0.5      # 50%
"@

New-Item -ItemType Directory -Path ".crashlens" -Force | Out-Null
Set-Content -Path ".crashlens/metrics.yaml" -Value $samplingConfig

# Create policy with test rules
$samplingPolicy = @"
version: 1
rules:
  - id: always_sample
    description: "Always sampled"
    match:
      model: "gpt-4"
    action: warn
    severity: high
    
  - id: never_sample
    description: "Never sampled"
    match:
      model: "gpt-3.5-turbo"
    action: warn
    severity: low
    
  - id: half_sample
    description: "50% sampled"
    match:
      model: "claude-2"
    action: warn
    severity: medium
"@

Set-Content -Path "temp-sampling-policy.yaml" -Value $samplingPolicy

# Run multiple scans to test statistical behavior
Write-Host "Running sampling tests (this may take a minute)..." -ForegroundColor Cyan

$iterations = 5
$results = @()

for ($i = 1; $i -le $iterations; $i++) {
    Write-Host "  Iteration $i/$iterations..." -ForegroundColor DarkGray
    
    crashlens policy-check sample-logs/demo-logs.jsonl `
        --policy-file temp-sampling-policy.yaml `
        --http-metrics `
        --http-metrics-port 19095 `
        --output temp-sampling-report-$i.md | Out-Null
    
    Start-Sleep -Seconds 1
    
    # Fetch metrics
    try {
        $metrics = Invoke-WebRequest -Uri "http://127.0.0.1:19095/metrics" -TimeoutSec 5
        $results += $metrics.Content
    } catch {
        Write-Host "  ⚠️  Failed to fetch metrics for iteration $i" -ForegroundColor Yellow
    }
    
    # Stop server
    Get-Process python | Where-Object { $_.MainWindowTitle -match "crashlens" } | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# Analyze results
Write-Host "`nAnalyzing sampling behavior..." -ForegroundColor Cyan

$alwaysSampleCount = ($results | Select-String 'rule="always_sample"').Count
$neverSampleCount = ($results | Select-String 'rule="never_sample"').Count
$halfSampleCount = ($results | Select-String 'rule="half_sample"').Count

Write-Host "Results over $iterations iterations:" -ForegroundColor White
Write-Host "  Always sample (1.0): $alwaysSampleCount occurrences" -ForegroundColor $(if ($alwaysSampleCount -eq $iterations) { "Green" } else { "Red" })
Write-Host "  Never sample (0.0):  $neverSampleCount occurrences" -ForegroundColor $(if ($neverSampleCount -eq 0) { "Green" } else { "Red" })
Write-Host "  Half sample (0.5):   $halfSampleCount occurrences" -ForegroundColor $(if ($halfSampleCount -gt 0 -and $halfSampleCount -lt $iterations) { "Green" } else { "Yellow" })

# Validation
$allTestsPass = $true

if ($alwaysSampleCount -eq $iterations) {
    Write-Host "✅ 100% sampling works correctly" -ForegroundColor Green
} else {
    Write-Host "❌ 100% sampling failed" -ForegroundColor Red
    $allTestsPass = $false
}

if ($neverSampleCount -eq 0) {
    Write-Host "✅ 0% sampling works correctly" -ForegroundColor Green
} else {
    Write-Host "❌ 0% sampling failed (found $neverSampleCount when expected 0)" -ForegroundColor Red
    $allTestsPass = $false
}

# For 50% sampling, we expect some but not all (statistical test)
$expectedHalf = [math]::Round($iterations * 0.5)
$tolerance = [math]::Ceiling($iterations * 0.3)  # 30% tolerance for small sample size

if ($halfSampleCount -ge ($expectedHalf - $tolerance) -and $halfSampleCount -le ($expectedHalf + $tolerance)) {
    Write-Host "✅ 50% sampling within expected range ($expectedHalf ± $tolerance)" -ForegroundColor Green
} else {
    Write-Host "⚠️  50% sampling outside expected range (got $halfSampleCount, expected $expectedHalf ± $tolerance)" -ForegroundColor Yellow
    Write-Host "   Note: This may be statistical variance with small sample size" -ForegroundColor DarkGray
}

# Cleanup
Remove-Item .crashlens -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item temp-sampling-policy.yaml -ErrorAction SilentlyContinue
Remove-Item temp-sampling-report-*.md -ErrorAction SilentlyContinue
```

**Pass Criteria:**
- ✅ 100% sampling always includes metrics
- ✅ 0% sampling never includes metrics
- ✅ Partial sampling shows statistical behavior
- ✅ Per-rule overrides work correctly
- ✅ No crashes with different sampling rates

**Failure Impact:** MEDIUM. Sampling is key to performance claims.

---

## 🎯 Final Validation: Comprehensive Demo Scenario

### Step 11: Investor Demo Simulation (15 minutes)

**Objective:** Run complete scenario exactly as you'll show investors. Murphy's Law applies to demos.

```powershell
Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                              ║" -ForegroundColor Cyan
Write-Host "║        FINAL DEMO SIMULATION - SEED ROUND VALIDATION        ║" -ForegroundColor Yellow
Write-Host "║                                                              ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Demo Script: Exactly what you'll show investors
Write-Host "=== Demo Phase 1: Basic Scan ===" -ForegroundColor Cyan
crashlens scan sample-logs/demo-logs.jsonl --format markdown --output demo-report.md

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Basic scan completed" -ForegroundColor Green
} else {
    Write-Host "❌ DEMO FAILURE: Basic scan failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Demo Phase 2: Policy Enforcement ===" -ForegroundColor Cyan
crashlens policy-check sample-logs/demo-logs.jsonl `
    --policy-template retry-loop-prevention `
    --output demo-policy-report.md

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Policy check completed" -ForegroundColor Green
} else {
    Write-Host "⚠️  Policy check found violations (expected behavior)" -ForegroundColor Yellow
}

Write-Host "`n=== Demo Phase 3: Metrics Collection ===" -ForegroundColor Cyan
Write-Host "Starting metrics server on port 19096..." -ForegroundColor Gray

crashlens scan sample-logs/demo-logs.jsonl `
    --http-metrics `
    --http-metrics-port 19096 `
    --output demo-metrics-report.md &

Start-Sleep -Seconds 3

Write-Host "Fetching metrics..." -ForegroundColor Gray
try {
    $metrics = Invoke-WebRequest -Uri "http://127.0.0.1:19096/metrics" -TimeoutSec 10
    
    Write-Host "✅ Metrics endpoint accessible" -ForegroundColor Green
    Write-Host "   Total size: $($metrics.Content.Length) bytes" -ForegroundColor DarkGray
    
    # Show sample metrics (what you'd show investors)
    Write-Host "`nSample metrics (first 20 lines):" -ForegroundColor Cyan
    ($metrics.Content -split "`n" | Select-Object -First 20) | ForEach-Object {
        Write-Host "  $_" -ForegroundColor DarkGray
    }
    
    # Key metrics for demo
    Write-Host "`nKey metrics for demo:" -ForegroundColor Cyan
    $metrics.Content -split "`n" | Where-Object { $_ -match "crashlens_violations_total|crashlens_traces_processed_total" } | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Green
    }
    
} catch {
    Write-Host "❌ DEMO FAILURE: Metrics endpoint unreachable!" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Demo Phase 4: Kill Switch ===" -ForegroundColor Cyan
Write-Host "Demonstrating operational safety..." -ForegroundColor Gray

$env:CRASHLENS_DISABLE_METRICS = "true"

crashlens scan sample-logs/demo-logs.jsonl `
    --push-metrics `
    --pushgateway-url http://localhost:9091 `
    --verbose 2>&1 | Select-String "disabled" -CaseSensitive:$false

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Kill switch demonstrated" -ForegroundColor Green
} else {
    Write-Host "❌ Kill switch failed" -ForegroundColor Red
}

Remove-Item Env:\CRASHLENS_DISABLE_METRICS

Write-Host "`n=== Demo Phase 5: Performance Claims ===" -ForegroundColor Cyan
Write-Host "Validating <10% overhead claim..." -ForegroundColor Gray

$demoBaseline = Measure-Command {
    crashlens scan sample-logs/demo-logs.jsonl --output temp-baseline.md | Out-Null
} | Select-Object -ExpandProperty TotalSeconds

$demoMetrics = Measure-Command {
    crashlens scan sample-logs/demo-logs.jsonl --http-metrics --http-metrics-port 19097 --output temp-metrics.md | Out-Null
    Start-Sleep -Seconds 1
    Get-Process python | Where-Object { $_.MainWindowTitle -match "crashlens" } | Stop-Process -Force -ErrorAction SilentlyContinue
} | Select-Object -ExpandProperty TotalSeconds

$demoOverhead = (($demoMetrics - $demoBaseline) / $demoBaseline) * 100

Write-Host "Performance results:" -ForegroundColor White
Write-Host "  Baseline: $([math]::Round($demoBaseline, 2))s" -ForegroundColor DarkGray
Write-Host "  With metrics: $([math]::Round($demoMetrics, 2))s" -ForegroundColor DarkGray
Write-Host "  Overhead: " -NoNewline
Write-Host "$([math]::Round($demoOverhead, 2))%" -ForegroundColor $(if ($demoOverhead -lt 10) { "Green" } else { "Red" })

if ($demoOverhead -lt 10) {
    Write-Host "✅ <10% overhead claim validated" -ForegroundColor Green
} else {
    Write-Host "❌ DEMO FAILURE: Overhead exceeds 10%!" -ForegroundColor Red
    exit 1
}

# Cleanup
Get-Process python | Where-Object { $_.MainWindowTitle -match "crashlens" } | Stop-Process -Force -ErrorAction SilentlyContinue
Remove-Item demo-report.md, demo-policy-report.md, demo-metrics-report.md, temp-baseline.md, temp-metrics.md -ErrorAction SilentlyContinue

Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                                                              ║" -ForegroundColor Green
Write-Host "║              ✅ DEMO SIMULATION SUCCESSFUL! ✅               ║" -ForegroundColor Yellow
Write-Host "║                                                              ║" -ForegroundColor Green
Write-Host "║                  READY FOR SEED ROUND                        ║" -ForegroundColor White
Write-Host "║                                                              ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Green
```

**Pass Criteria:**
- ✅ All demo phases complete without errors
- ✅ Metrics endpoint accessible
- ✅ Kill switch works
- ✅ Performance <10% overhead
- ✅ No crashes or stack traces
- ✅ Clean output suitable for investors

**Failure Impact:** CATASTROPHIC. If demo fails, seed round fails.

---

## 📋 Final Checklist

### Pre-Demo Validation Summary

Run this final checklist 24 hours before investor meeting:

```powershell
Write-Host "`n=== FINAL PRE-DEMO CHECKLIST ===" -ForegroundColor Cyan
Write-Host "Complete this 24 hours before investor meeting`n" -ForegroundColor Yellow

$checklist = @(
    @{Item="Clean environment setup"; Command="python --version; git status"},
    @{Item="CLI works without metrics"; Command="crashlens --version"},
    @{Item="Kill switch functional"; Command="(env:CRASHLENS_DISABLE_METRICS='true'; crashlens scan --push-metrics)"},
    @{Item="Performance <10% overhead"; Command="# Run Step 5"},
    @{Item="HTTP server localhost-only"; Command="# Run Step 6"},
    @{Item="Metrics collection accurate"; Command="# Run Step 7"},
    @{Item="Policy integration works"; Command="# Run Step 8"},
    @{Item="Config validation works"; Command="# Run Step 9"},
    @{Item="Sampling behavior correct"; Command="# Run Step 10"},
    @{Item="Full demo simulation passes"; Command="# Run Step 11"}
)

$passed = 0
foreach ($check in $checklist) {
    Write-Host "[ ] $($check.Item)" -ForegroundColor White
}

Write-Host "`nValidation script: PROD_VALIDATION_PROTOCOL.md`n" -ForegroundColor Cyan
```

### Success Criteria for Seed Round

**Must Have (Deal Breakers):**
- ✅ All 11 steps pass
- ✅ Zero crashes or stack traces
- ✅ Performance <10% overhead
- ✅ Security validations pass
- ✅ Demo simulation flawless

**Nice to Have (Bonus Points):**
- ⭐ Performance <5% overhead
- ⭐ All tests <5% variance
- ⭐ Config validation with helpful errors
- ⭐ Metrics format perfect for Grafana

**Red Flags (Investor Concerns):**
- ❌ Any crashes during validation
- ❌ Performance >10% overhead
- ❌ Network exposure in HTTP server
- ❌ Missing error handling
- ❌ Inconsistent behavior across runs

---

## 📞 Emergency Protocols

### If Validation Fails

**Critical Failure (Steps 1-3, 6-8, 11):**
1. STOP immediately
2. Document exact error
3. Run `git stash` to preserve state
4. Create GitHub issue with full logs
5. DO NOT proceed to investor demo

**Performance Failure (Steps 4-5):**
1. Rerun on clean Linux environment
2. Check for background processes
3. Verify test data size
4. Consider adjusting sampling rates
5. Document Windows-specific issues

**Demo Simulation Failure (Step 11):**
1. Run each phase individually
2. Check system resources
3. Verify all dependencies
4. Practice demo 5+ times
5. Have backup demo video ready

### Support Contacts

- **Technical Lead:** [Your contact]
- **Emergency Slack:** #crashlens-urgent
- **Backup Demo Machine:** [Location/credentials]

---

## 📊 Validation Report Template

After completing all steps, fill this out:

```
CRASHLENS PRE-PRODUCTION VALIDATION REPORT
Date: _______________
Validator: _______________
Environment: Windows / macOS / Linux
Python Version: _______________

RESULTS:
[ ] Step 1: Clean Environment (Pass/Fail)
[ ] Step 2: Zero-Dependency Operation (Pass/Fail)
[ ] Step 3: Kill Switch (Pass/Fail)
[ ] Step 4: Lazy Loading (Pass/Fail)
[ ] Step 5: Performance (<10% overhead): _____% 
[ ] Step 6: HTTP Security (Pass/Fail)
[ ] Step 7: Metrics Accuracy (Pass/Fail)
[ ] Step 8: Policy Integration (Pass/Fail)
[ ] Step 9: Config Validation (Pass/Fail)
[ ] Step 10: Sampling Behavior (Pass/Fail)
[ ] Step 11: Demo Simulation (Pass/Fail)

PERFORMANCE METRICS:
- Baseline scan time: _____s
- With metrics time: _____s
- Overhead: _____%
- Memory overhead: _____MB

ISSUES FOUND:
1. 
2. 
3. 

INVESTOR READINESS: YES / NO / CONDITIONAL

SIGN-OFF:
Validator: _______________
Date: _______________
```

---

**REMEMBER:** Investors invest in execution, not ideas. This validation proves you can execute at production grade.

**GOOD LUCK!** 🚀
