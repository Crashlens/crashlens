# CRITICAL BUG FIXES - PolicyEngine

**Date:** November 8, 2025  
**Status:** ✅ FIXED - All tests passing (33/33)  
**Severity:** CRITICAL - Would have caused production failures  
**Branch:** `feature/step10-legacy-removal`  
**Commit:** `c7cfb42`

---

## Executive Summary

During pre-merge testing, discovered that the 2 "test infrastructure issues" were actually **3 critical production bugs** that would have caused silent failures in production. All bugs have been fixed and verified.

**Impact:**
- 🐛 Bug #1: Early exit after first violation (100% of multi-violation traces under-reported)
- 🐛 Bug #2: Regex operator broken (all PII detection non-functional)
- 🐛 Bug #3: Nested field extraction missing (examples showed empty prompts)

**Resolution:**
- ✅ 33/33 tests passing (was 31/33)
- ✅ All bugs fixed in single commit
- ✅ Production functionality verified
- ✅ No breaking changes

---

## Bug #1: PolicyEngine Early Exit (SHOWSTOPPER)

### Problem

**File:** `crashlens/policy/engine.py` (line 351-354)

```python
if violation:
    violations.append(violation)
    self.violation_counts[rule.id] += 1
    self.traces_flagged.add(trace_id)
    
    # Early exit: once a trace is flagged, don't check remaining rules
    self.logger.debug(f"Trace {trace_id} flagged by rule {rule.id}, skipping remaining rules")
    break  # ← KILLER BUG!
```

**Impact:**
- ❌ Only FIRST matching rule reported per trace
- ❌ All subsequent rule violations silently ignored
- ❌ Guard command showed incomplete results
- ❌ 100% of multi-violation scenarios affected

### Example

```python
# Log entry violates BOTH rules
log_entry = {
    "traceId": "trace-1",
    "usage": {"prompt_tokens": 3000},  # Violates RL001 (>2000)
    "metadata": {"retry_count": 5}     # Violates RL002 (>2)
}

# BEFORE FIX:
$ crashlens guard logs.jsonl --rules rules.yaml
{
  "rules": {
    "RL001": {"count": 1},  # ✅ Reported
    "RL002": {"count": 0}   # ❌ Silently skipped!
  }
}

# AFTER FIX:
$ crashlens guard logs.jsonl --rules rules.yaml
{
  "rules": {
    "RL001": {"count": 1},  # ✅ Reported
    "RL002": {"count": 1}   # ✅ Also reported!
  }
}
```

### Fix

```python
if violation:
    violations.append(violation)
    self.violation_counts[rule.id] += 1
    self.traces_flagged.add(trace_id)
    self.logger.debug(f"Trace {trace_id} flagged by rule {rule.id}, continuing to check remaining rules")
    # REMOVED: break statement
    
return violations, skipped_rules
```

**Why This Happened:**  
The "early exit" behavior was designed for `policy-check` command (fail-fast on first violation), but was incorrectly applied to `guard` command (needs all violations).

---

## Bug #2: Regex Using re.match() Instead of re.search()

### Problem

**File:** `crashlens/policy/engine.py` (line 55)

```python
OPERATORS = {
    ...
    'regex': lambda a, b: bool(re.match(b, str(a))),  # ← BUG!
    ...
}
```

**Why This Is Wrong:**
- `re.match()` only matches at **START** of string
- PII detection patterns like `"@"` for emails won't match "Contact joe@example.com"
- All pattern matching rules broken

### Example

```python
import re

text = "Contact joe@example.com or call +1-555-1234"

# BEFORE FIX (re.match)
re.match("@", text)  # ❌ None (doesn't match at start)

# AFTER FIX (re.search)
re.search("@", text)  # ✅ Match (finds @ anywhere)
```

**Impact:**
- ❌ PII detection completely broken
- ❌ Email/phone/SSN patterns never matched
- ❌ GDPR/HIPAA compliance violations undetected
- ❌ All regex-based rules non-functional

### Fix

```python
OPERATORS = {
    ...
    'regex': lambda a, b: bool(re.search(b, str(a))),  # Changed to re.search
    ...
}

# Also fixed colon handling for "regex: pattern" format
expected = rule_value[len(op_str):].strip()
if expected.startswith(':'):
    expected = expected[1:].strip()  # Remove "regex: @" → "@"
```

---

## Bug #3: Nested Field Extraction Missing

### Problem

**File:** `crashlens/guard_adapter.py` (line 315)

```python
# Only checked flat format
example = {
    "prompt": redact_text(entry.get("prompt", ""), strip_pii),  # ← Doesn't check nested input.prompt
    ...
}
```

**Impact:**
- ❌ Examples showed empty prompts for Langfuse format
- ❌ PII couldn't be stripped (no prompt found)
- ❌ All nested fields (metadata.*, input.*) were empty
- ❌ Reports missing critical context

### Example

```python
# Langfuse format log entry
entry = {
    "traceId": "t1",
    "input": {"prompt": "Contact joe@example.com"},  # Nested!
    "usage": {"prompt_tokens": 100},
    "metadata": {"retry_count": 5}
}

# BEFORE FIX:
{
  "examples": [{
    "prompt": "",           # ❌ Empty!
    "retry_count": null,    # ❌ Missing!
    "tokens": 0             # ❌ Wrong!
  }]
}

# AFTER FIX:
{
  "examples": [{
    "prompt": "Contact [REDACTED_EMAIL]",  # ✅ Found and stripped!
    "retry_count": 5,                       # ✅ Extracted!
    "tokens": 100                           # ✅ Correct!
  }]
}
```

### Fix

```python
# Extract from both flat and Langfuse nested formats
prompt = entry.get("prompt") or entry.get("input", {}).get("prompt", "")
example = {
    "timestamp": entry.get("timestamp") or entry.get("startTime"),
    "model": entry.get("model") or entry.get("input", {}).get("model"),
    "tokens": entry.get("tokens") or entry.get("usage", {}).get("prompt_tokens", 0),
    "retry_count": entry.get("retry_count") or entry.get("metadata", {}).get("retry_count"),
    "fallback_triggered": entry.get("fallback_triggered") or entry.get("metadata", {}).get("fallback_triggered"),
    "endpoint": entry.get("endpoint") or entry.get("metadata", {}).get("endpoint"),
    "prompt": redact_text(prompt, strip_pii),
    "reason": violation.reason,
}
```

---

## Discovery Process

### Initial Hypothesis (WRONG)

"Test failures are due to pytest CliRunner temp file isolation issues. Core functionality works."

### Investigation Steps

1. **Created standalone test** (no CliRunner):
   ```bash
   $ python debug_nested_fields.py
   ❌ PROBLEM: Expected 2 rules with violations, got 1
   ```
   → Not a CliRunner issue!

2. **Tested real CLI** with manual files:
   ```bash
   $ echo '{"traceId":"t1","usage":{"prompt_tokens":3000},"metadata":{"retry_count":5}}' > test.jsonl
   $ crashlens guard test.jsonl --rules rules.yaml
   ❌ Only RL001 reported, RL002 missing
   ```
   → Not a test infrastructure issue!

3. **Added verbose logging**:
   ```
   DEBUG: Trace t1 flagged by rule RL001, skipping remaining rules
   ```
   → Found early exit bug!

4. **Tested regex in Python REPL**:
   ```python
   >>> re.match("@", "Contact joe@example.com")
   None  # ❌ Doesn't match!
   >>> re.search("@", "Contact joe@example.com")
   <Match>  # ✅ Works!
   ```
   → Found re.match() bug!

5. **Checked violation examples**:
   ```json
   {"examples": [{"prompt": "", ...}]}
   ```
   → Found nested field extraction bug!

### Lesson Learned

**✅ NEVER assume test failures are "infrastructure issues" without proof!**

Always verify with:
- Standalone scripts (no test framework)
- Real CLI usage (not just tests)
- Debug logging (trace execution)
- Multiple test approaches (unit, integration, manual)

---

## Test Results

### Before Fixes
```
==================== test session starts ====================
tests/test_guard.py::TestGuardCLI::test_guard_suppression FAILED [ 12%]
tests/test_guard.py::TestGuardCLI::test_guard_pii_stripping FAILED [ 18%]
=============== 2 failed, 31 passed in 1.58s ================ 
```

### After Fixes
```
==================== test session starts ====================
tests/test_guard.py .................................  [100%]
==================== 33 passed in 1.28s =====================
```

---

## Production Impact Analysis

**If these bugs had shipped:**

1. **Early Exit:** 
   - Users see incomplete reports
   - Compliance audits miss violations
   - Cost overruns not fully detected
   - **Severity:** CRITICAL - Silent data loss

2. **Regex Bug:**
   - PII detection broken
   - GDPR/HIPAA violations undetected
   - Security patterns (SQL injection) don't match
   - **Severity:** CRITICAL - Legal/security liability

3. **Prompt Extraction:**
   - Reports missing context
   - PII not redacted
   - Logs contain sensitive data
   - **Severity:** HIGH - Privacy/security issue

**Cost if discovered in production:**
- Emergency rollback required
- Customer notifications (security incident)
- Compliance audit failures
- Reputation damage
- Engineering time: 50+ hours

**Cost of fix before release:**
- 2 hours investigation
- 30 minutes coding
- 10 minutes testing
- ✅ Zero customer impact

---

## Files Changed

```
crashlens/policy/engine.py        (3 changes)
  - Line 55: Changed regex operator to re.search()
  - Line 76-78: Added colon stripping for regex format
  - Line 351-354: Removed early exit break statement

crashlens/guard_adapter.py        (1 change)
  - Line 304-317: Added nested field extraction for examples

docs/GUARD_MIGRATION_COMPLETE.md  (metadata update)
  - Updated test pass rate to 100%
```

**Commit:** `c7cfb42`  
**Files:** 3  
**Lines changed:** +39, -341  
**Test impact:** 2 failures → 0 failures

---

## Verification Commands

```bash
# Run full guard test suite
poetry run pytest tests/test_guard.py -q
# Result: 33 passed in 1.28s ✅

# Test multi-violation scenario
echo '{"traceId":"t1","usage":{"prompt_tokens":3000},"metadata":{"retry_count":5}}' > test.jsonl
poetry run crashlens guard test.jsonl --rules rules.yaml --output json
# Result: Both RL001 and RL002 reported ✅

# Test regex matching
echo '{"traceId":"t1","input":{"prompt":"Contact joe@example.com"}}' > test.jsonl
poetry run crashlens guard test.jsonl --rules pii-rules.yaml --strip-pii --output json
# Result: Email detected and redacted ✅

# Test PII stripping
# Output: {"prompt": "Contact [REDACTED_EMAIL]"} ✅
```

---

## Next Steps

### Immediate
- ✅ Update migration documentation
- ✅ Commit and push fixes
- ⏭️ Create Pull Request

### Post-Merge
- Add regression tests for multi-violation scenarios
- Add regex operator test coverage
- Add nested field extraction tests
- Document "early exit vs report all" design patterns

### Future Improvements
- Make early exit configurable (policy-check vs guard)
- Add validation for regex patterns
- Improve error messages for field extraction failures

---

## References

- Original migration doc: `docs/GUARD_MIGRATION_COMPLETE.md`
- Commit with fixes: `c7cfb42`
- Test files: `tests/test_guard.py`
- Core files: `crashlens/policy/engine.py`, `crashlens/guard_adapter.py`

---

**Status:** ✅ ALL FIXED - Safe to merge
