#!/usr/bin/env pwsh
# CrashLens Guard Verification Script (PowerShell version)
# Performs automated smoke and E2E checks

$ErrorActionPreference = "Continue"
$ROOT = Get-Location
$TIMESTAMP = Get-Date -Format "yyyyMMddHHmmss"

Write-Host "=== CrashLens Guard Verification ==="
Write-Host "Repository: $ROOT"
Write-Host "Timestamp: $TIMESTAMP"
Write-Host ""

$fail = 0

# Check for safety tag
Write-Host "0) Safety tag check"
$tag = git tag --list | Select-String "pre-verify-guard-"
if ($tag) {
    Write-Host "✅ Safety tag found: $tag"
} else {
    Write-Host "⚠️  No pre-verify-guard tag found"
}
Write-Host ""

# 1. CLI help check
Write-Host "1) CLI help check"
python -m crashlens.cli --help > $null 2>&1
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) {
    Write-Host "❌ ERROR: CLI top-level help failed (exit $LASTEXITCODE)"
    $fail++
} else {
    Write-Host "✅ CLI help loads"
}
Write-Host ""

# 2. guard help check
Write-Host "2) guard help check"
python -m crashlens.cli guard --help > $null 2>&1
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) {
    Write-Host "❌ ERROR: guard help failed (exit $LASTEXITCODE)"
    $fail++
} else {
    Write-Host "✅ guard help displays"
}
Write-Host ""

# 3. policy-check MUST be absent
Write-Host "3) policy-check absence check"
python -m crashlens.cli policy-check --help > $null 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "❌ ERROR: policy-check still exists"
    $fail++
} else {
    Write-Host "✅ policy-check absent (expected)"
}
Write-Host ""

# 4. Run guard -> json
Write-Host "4) Run guard with JSON output"
$SAMPLE = "fixtures/combined-logs.jsonl"
$RULES = ".crashlens/rules.yaml"
$OUT = "verify-guard-out-$TIMESTAMP.json"

if (!(Test-Path $SAMPLE)) {
    Write-Host "❌ ERROR: Sample file not found: $SAMPLE"
    $fail++
} elseif (!(Test-Path $RULES)) {
    Write-Host "❌ ERROR: Rules file not found: $RULES"
    $fail++
} else {
    python -m crashlens.cli guard $SAMPLE --rules $RULES --output json 2> "verify-stderr-$TIMESTAMP.log" | Out-File -Encoding utf8 $OUT
    $rc = $LASTEXITCODE
    
    if ($rc -ne 0 -and $rc -ne 1) {
        Write-Host "❌ ERROR: guard exited with $rc"
        Write-Host "Stderr log:"
        Get-Content "verify-stderr-$TIMESTAMP.log" | Select-Object -First 10
        $fail++
    } else {
        Write-Host "✅ guard exit $rc (acceptable)"
    }
}
Write-Host ""

# 5. Validate JSON
Write-Host "5) Validate JSON output"
if (Test-Path $OUT) {
    try {
        $json = Get-Content $OUT -Raw | ConvertFrom-Json
        Write-Host "✅ JSON valid"
        Write-Host "   Summary - Rules: $($json.summary.total_rules), Violations: $($json.summary.violations)"
    } catch {
        Write-Host "❌ ERROR: JSON invalid"
        Write-Host "   Error: $_"
        Write-Host "   First 10 lines:"
        Get-Content $OUT | Select-Object -First 10
        $fail++
    }
} else {
    Write-Host "❌ ERROR: Output file not created: $OUT"
    $fail++
}
Write-Host ""

# 6. Grep for policy-check in repo (excluding historical benchmark results)
Write-Host "6) Search for policy-check references"
$refs = git grep -n "policy-check\|policy_check" 2>&1 | Where-Object { $_ -notmatch "LASTEXITCODE" -and $_ -notmatch "bench/results" -and $_ -notmatch "scripts/verify_guard.ps1" }
if ($refs) {
    Write-Host "❌ ERROR: Found policy-check references:"
    $refs | Select-Object -First 10 | ForEach-Object { Write-Host "   $_" }
    $fail++
} else {
    Write-Host "✅ No policy-check references found (excluding historical benchmark data)"
}
Write-Host ""

# 7. Docs check
Write-Host "7) Documentation check"
$doc_refs = git grep -n "policy-check" -- "*.md" "docs/" ".github/" 2>&1 | Where-Object { $_ -notmatch "LASTEXITCODE" }
if ($doc_refs) {
    Write-Host "❌ ERROR: Docs contain policy-check:"
    $doc_refs | Select-Object -First 5 | ForEach-Object { Write-Host "   $_" }
    $fail++
} else {
    Write-Host "✅ Docs clean"
}
Write-Host ""

# 8. Run unit subset
Write-Host "8) Unit test subset"
poetry run pytest -q tests/test_guard_edge_cases_v1_launch.py -k "not slow" > "verify-tests-$TIMESTAMP.log" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Unit tests passed"
} else {
    Write-Host "❌ Unit tests failed (exit $LASTEXITCODE)"
    Get-Content "verify-tests-$TIMESTAMP.log" | Select-Object -Last 20
    $fail++
}
Write-Host ""

# Final summary
Write-Host "=== VERIFICATION SUMMARY ==="
if ($fail -eq 0) {
    Write-Host "✅ ALL CHECKS PASSED ($fail failures)"
    Write-Host "Status: READY FOR PRODUCTION"
    exit 0
} else {
    Write-Host "❌ FAILURES DETECTED ($fail failures)"
    Write-Host "Status: NOT READY - Fix issues before deployment"
    exit 2
}
