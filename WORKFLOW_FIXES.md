# GitHub Actions Workflow Fixes - Updated

## Issues Found and Fixed

### Issue 1: Missing Dependency Group ✅
**Error:** `Group(s) not found: metrics (via --with)`

**Root Cause:** 
- Workflow used `poetry install --with metrics`
- But `metrics` is defined as an **extra** (not a dependency group) in `pyproject.toml`

**Fix:**
```yaml
# BEFORE:
poetry install --with metrics

# AFTER:
poetry install --extras metrics
```

---

### Issue 2: Empty Input Variables on Push Events ✅
**Error:** Benchmark script received empty `ITERATIONS` and `TEST_SAMPLING` variables

**Root Cause:**
- `github.event.inputs.*` is only available for `workflow_dispatch` events
- When triggered by `push` to `main`, these variables are null/empty
- Script ran with invalid arguments

**Fix:**
```yaml
# BEFORE:
ITERATIONS=${{ github.event.inputs.iterations }}
TEST_SAMPLING=${{ github.event.inputs.test_sampling }}

# AFTER:
ITERATIONS="${{ github.event.inputs.iterations || '10' }}"
TEST_SAMPLING="${{ github.event.inputs.test_sampling || 'true' }}"
```

---

### Issue 3: Benchmark Script Failures Not Detected ✅
**Error:** Workflow created empty `benchmark_results.txt` even when script failed

**Root Cause:**
- When Python script crashes, `tee` still creates an empty file
- Stderr was not captured
- Exit code was not checked

**Fix:**
```yaml
# Added error detection:
set +e  # Don't exit on error
poetry run python scripts/benchmark_100k_proper.py \
  --iterations "$ITERATIONS" \
  2>&1 | tee benchmark_results.txt  # Capture stderr too
BENCHMARK_EXIT_CODE=${PIPESTATUS[0]}
set -e

echo "Benchmark exit code: $BENCHMARK_EXIT_CODE"
exit $BENCHMARK_EXIT_CODE
```

---

### Issue 4: Empty Output File Not Detected ✅
**Error:** `⚠️ Could not determine benchmark result` (file exists but empty)

**Root Cause:**
- Workflow checked if file exists, but not if it has content
- No file size or line count validation

**Fix:**
```yaml
# Added file validation:
FILE_SIZE=$(wc -c < benchmark_results.txt)
LINE_COUNT=$(wc -l < benchmark_results.txt)

if [ $FILE_SIZE -eq 0 ]; then
  echo "❌ ERROR: benchmark_results.txt is empty"
  exit 1
fi

if [ $LINE_COUNT -lt 10 ]; then
  echo "⚠️  WARNING: Output file is very short ($LINE_COUNT lines)"
  cat benchmark_results.txt
  exit 1
fi
```

---

### Issue 5: Insufficient Error Diagnostics ✅
**Error:** Couldn't determine why benchmark failed

**Root Cause:**
- No search for errors in output
- No benchmark step status check
- Limited debugging info

**Fix:**
```yaml
# Added error search:
grep -i "error\|exception\|traceback" benchmark_results.txt || echo "No errors found"

# Added step status check:
- name: Check benchmark step status
  if: always()
  run: |
    echo "Benchmark step outcome: ${{ steps.benchmark.outcome }}"
    if [ "${{ steps.benchmark.outcome }}" = "failure" ]; then
      echo "⚠️  Benchmark step failed"
    fi
```

---

## All Changes Summary

### 1. Fixed dependency installation ✅
```diff
- poetry install --with metrics
+ poetry install --extras metrics
```

### 2. Fixed input variable defaults ✅
```diff
- ITERATIONS=${{ github.event.inputs.iterations }}
+ ITERATIONS="${{ github.event.inputs.iterations || '10' }}"
```

### 3. Added stderr capture ✅
```diff
- poetry run python ... | tee benchmark_results.txt
+ poetry run python ... 2>&1 | tee benchmark_results.txt
```

### 4. Added exit code tracking ✅
```diff
+ BENCHMARK_EXIT_CODE=${PIPESTATUS[0]}
+ exit $BENCHMARK_EXIT_CODE
```

### 5. Added file size validation ✅
```diff
+ FILE_SIZE=$(wc -c < benchmark_results.txt)
+ if [ $FILE_SIZE -eq 0 ]; then
+   echo "❌ ERROR: benchmark_results.txt is empty"
+   exit 1
+ fi
```

### 6. Added benchmark step status check ✅
```diff
+ - name: Check benchmark step status
+   if: always()
+   run: |
+     echo "Benchmark step outcome: ${{ steps.benchmark.outcome }}"
```

### 7. Enhanced error search ✅
```diff
+ grep -i "error\|exception\|traceback" benchmark_results.txt
```

---

## Expected Behavior After All Fixes

### Successful Run:
```
✅ Install dependencies (with --extras metrics)
✅ Generate 100k test file
✅ Run benchmark (captures stdout + stderr)
✅ Display results (shows file stats)
✅ Check result (finds ✓ PASS or ✗ FAIL)
```

### Failed Run (Better Diagnostics):
```
✅ Install dependencies
✅ Generate test file
❌ Run benchmark (exit code: 1)
⚠️  Benchmark step failed
📊 File size: 0 bytes ← Shows empty file
❌ ERROR: benchmark_results.txt is empty
🔍 Shows errors from output
```

---

## Commit Command

```bash
git add .github/workflows/benchmark-metrics.yml
git add WORKFLOW_FIXES.md
git commit -m "fix: comprehensive workflow error handling

- Capture stderr with 2>&1
- Track and report benchmark exit codes
- Validate file size and line count
- Add step status reporting
- Search for errors in output
- Show file statistics in summary"
git push origin main
```

This will trigger the workflow with complete error detection! 🚀
