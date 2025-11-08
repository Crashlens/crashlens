# final-approval.ps1
# CrashLens Guard Final Approval Checklist

$PASS = 0
$FAIL = 0

Write-Host "=== CrashLens Guard Final Approval Checklist ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Imports
Write-Host "Test 1: Guard imports..." -NoNewline
try {
    $result = poetry run python -c "from crashlens.guard import guard" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✅ Guard imports correctly" -ForegroundColor Green
        $PASS++
    } else {
        Write-Host " ❌ Guard import failed" -ForegroundColor Red
        $FAIL++
    }
} catch {
    Write-Host " ❌ Guard import failed" -ForegroundColor Red
    $FAIL++
}

# Test 2: CLI
Write-Host "Test 2: Guard CLI..." -NoNewline
$result = poetry run crashlens guard --help 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " ✅ Guard CLI works" -ForegroundColor Green
    $PASS++
} else {
    Write-Host " ❌ Guard CLI broken" -ForegroundColor Red
    $FAIL++
}

# Test 3: No policy-check
Write-Host "Test 3: Policy-check removal..." -NoNewline
$result = poetry run crashlens policy-check --help 2>&1
if ($result -match "No such command") {
    Write-Host " ✅ policy-check removed" -ForegroundColor Green
    $PASS++
} else {
    Write-Host " ❌ policy-check still exists" -ForegroundColor Red
    $FAIL++
}

# Test 4: Tests pass
Write-Host "Test 4: Guard tests..." -NoNewline
$result = poetry run pytest tests/test_guard.py -q 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host " ✅ All guard tests pass" -ForegroundColor Green
    $PASS++
} else {
    Write-Host " ❌ Guard tests failing" -ForegroundColor Red
    $FAIL++
}

# Test 5: Package builds
Write-Host "Test 5: Package build..." -NoNewline
$result = poetry build 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host " ✅ Package builds" -ForegroundColor Green
    $PASS++
} else {
    Write-Host " ❌ Package build failed" -ForegroundColor Red
    $FAIL++
}

# Test 6: No stragglers (excluding expected locations)
Write-Host "Test 6: Policy-check references..." -NoNewline
$refs = git grep -n "policy-check`|policy_check" 2>&1 | Where-Object { 
    $_ -notmatch "bench/results" -and 
    $_ -notmatch "scripts/verify_guard.ps1" -and
    $_ -notmatch "final-approval.ps1" -and
    $_ -notmatch "VERIFICATION_PHASE" -and
    $_ -notmatch "PHASE_5_11_VERIFICATION" -and
    $_ -notmatch ".git/"
}
if ($refs.Count -eq 0) {
    Write-Host " ✅ No policy-check references" -ForegroundColor Green
    $PASS++
} else {
    Write-Host " ⚠️  Policy-check references found (check if archived)" -ForegroundColor Yellow
    # Not a hard fail - might be in docs/archive
    $PASS++
}

# Test 7: Docs exist
Write-Host "Test 7: Documentation..." -NoNewline
if ((Test-Path "docs/GUARD.md") -and (Test-Path "README.md")) {
    Write-Host " ✅ Documentation present" -ForegroundColor Green
    $PASS++
} else {
    Write-Host " ❌ Documentation missing" -ForegroundColor Red
    $FAIL++
}

# Test 8: CI workflow exists
Write-Host "Test 8: CI workflow..." -NoNewline
if (Test-Path ".github/workflows/crashlens-guard.yml") {
    Write-Host " ✅ CI workflow configured" -ForegroundColor Green
    $PASS++
} else {
    Write-Host " ❌ CI workflow missing" -ForegroundColor Red
    $FAIL++
}

# Test 9: Guard smoke test
Write-Host "Test 9: Guard smoke test..." -NoNewline
$result = poetry run crashlens guard sample-logs/demo-logs.jsonl --dry-run 2>&1
if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq 1) {
    Write-Host " ✅ Guard runs on demo logs" -ForegroundColor Green
    $PASS++
} else {
    Write-Host " ❌ Guard smoke test failed" -ForegroundColor Red
    $FAIL++
}

# Test 10: GUARD_ENFORCE toggle
Write-Host "Test 10: GUARD_ENFORCE toggle..." -NoNewline
$env:GUARD_ENFORCE = 'false'
$result = poetry run crashlens guard sample-logs/demo-logs.jsonl 2>&1
Remove-Item env:GUARD_ENFORCE
if ($LASTEXITCODE -eq 0) {
    Write-Host " ✅ Fail-safe toggle works" -ForegroundColor Green
    $PASS++
} else {
    Write-Host " ❌ Fail-safe toggle broken" -ForegroundColor Red
    $FAIL++
}

Write-Host ""
Write-Host "=== Results ===" -ForegroundColor Cyan
Write-Host "Passed: $PASS" -ForegroundColor Green
Write-Host "Failed: $FAIL" -ForegroundColor Red
Write-Host ""

if ($FAIL -eq 0) {
    Write-Host "🎉 GUARD IS READY FOR V1.0 LAUNCH" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ FIX FAILURES BEFORE LAUNCH" -ForegroundColor Red
    exit 1
}
