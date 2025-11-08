# Legacy Code Cleanup - Step 10 Implementation Plan

**Date:** November 8, 2025  
**Purpose:** Remove redundant first-draft legacy code, collapse feature flags, unify engine  
**Target:** Single-commit atomic change with full rollback capability

---

## Files to Modify

### 1. Delete Entirely
- `crashlens/utils/feature_flags.py` - Feature flag helpers (no longer needed)

### 2. Major Surgery
- `crashlens/guard.py` - Remove legacy evaluator, keep CLI shell  
- `crashlens/cli.py` - Remove feature flag setting in policy-check  
- `crashlens/guard_adapter.py` - Remove feature flag checks, make unconditional

### 3. Test Updates
- `tests/test_guard_policyengine_integration.py` - Remove feature flag mocking
- `tests/test_guard_unified_integration.py` - Remove legacy path tests
- `tests/test_cli_alias.py` - Remove feature flag assertions
- `tests/integration/test_parity_end_to_end.py` - Remove feature flag env vars
- `bench/benchmark_unified.py` - Remove feature flag logic

### 4. Documentation Updates
- Mark legacy docs as archived
- Update current docs to reflect single engine

---

## Detailed Changes by File

### crashlens/cli.py (Lines 4146-4147)

**REMOVE:**
```python
os.environ['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
```

**REASON:** No longer need to set flag - unified engine is default and only option

---

### crashlens/guard.py

**Lines to DELETE:**
1. Lines 30-31: Comments about feature flag
2. Lines 51-52: Feature flag comments  
3. Lines 887-900: Deprecation warning (no longer relevant)
4. Lines 942-980: Feature flag check and conditional routing
5. Lines 100-870: ALL legacy evaluator functions:
   - `Rule` class
   - `eval_condition()`
   - `eval_boolean_condition()`
   - `evaluate_condition()`
   - `format_json_report()`
   - `format_markdown_report()`
   - `format_html_report()`
   - `format_text_report()`
   - `scrub_pii()`
   - `load_jsonl()`
   - `stream_jsonl_batches()`
   - ALL legacy guard logic

**Lines to KEEP:**
1. Lines 1-29: Imports (clean up unused)
2. Lines 900-941: CLI command definition
3. Lines 981-1003: Guard function - SIMPLIFIED to just call adapter

**NEW guard() function (simplified):**
```python
def guard(...all params...):
    """Guard CLI - unified PolicyEngine only"""
    # No deprecation warning
    # No feature flag check
    # Direct adapter call
    
    from .guard_adapter import GuardPolicyEngineAdapter
    adapter = GuardPolicyEngineAdapter(verbose=verbose)
    result = adapter.run(logfile, rules, ...)
    
    # Format output
    # Exit with result code
```

---

### crashlens/guard_adapter.py

**Lines to REMOVE:**
- Line 7: Feature flag docstring
- Lines 26-32: Feature flag behavior description
- Line 66: Debug print with feature flag
- Line 328: Feature flag check function
- Any conditional logic checking `CRASHLENS_USE_UNIFIED_ENGINE`

**Lines to KEEP:**
- All adapter logic (unconditional now)
- All conversion functions
- All filter application

---

### crashlens/utils/feature_flags.py

**ACTION:** Delete entire file (no longer needed)

---

### tests/test_guard_policyengine_integration.py

**Lines with `CRASHLENS_USE_UNIFIED_ENGINE` to UPDATE:**
- Remove all `monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")` calls
- Remove all `monkeypatch.delenv("CRASHLENS_USE_UNIFIED_ENGINE", raising=False)` calls
- Tests now assume unified engine always active

**BEFORE:**
```python
def test_something(monkeypatch):
    monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")
    result = ...
```

**AFTER:**
```python
def test_something():
    # Unified engine always active
    result = ...
```

---

### tests/test_guard_unified_integration.py

**DECISION:** This file tests "unified vs legacy" comparison  
**ACTION:** Delete tests that compare legacy (lines 305-330)  
**KEEP:** Tests that validate unified engine behavior

---

### tests/test_cli_alias.py

**Lines to UPDATE:**
- Line 73: Remove assertion about setting env var
- Line 218, 229, 304, 374: Remove env var checks
- Tests now validate that both commands work, not that flag is set

---

### tests/integration/test_parity_end_to_end.py

**Lines to UPDATE:**
- Line 114: Remove `env['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'`
- Parity tests no longer need to set flag

---

### bench/benchmark_unified.py

**Lines to UPDATE:**
- Lines 185, 189: Remove env var setting
- Lines 210-211: Remove env var cleanup
- Benchmarks always use unified engine

---

## Expected Test Impact

### Tests That Will Pass Unchanged
- All policy engine tests
- All detector tests  
- All parser tests
- All formatter tests

### Tests Requiring Updates
- ~15 tests in `test_guard_policyengine_integration.py` - Remove env mocking
- ~10 tests in `test_guard_unified_integration.py` - Remove legacy comparisons
- ~5 tests in `test_cli_alias.py` - Remove flag assertions
- ~2 tests in `test_parity_end_to_end.py` - Remove env setting

### Tests to Delete
- Any test validating legacy-only behavior
- Any test comparing legacy vs unified output (parity already proven)

---

## Rollback Plan

### If Anything Fails

**Option 1: Git Revert (Clean)**
```bash
git revert HEAD
```

**Option 2: Git Reset (Nuclear)**
```bash
git reset --hard v3.0.0-legacy
```

**Option 3: Restore from Archive**
```bash
cp legacy/guard_legacy_snapshot.py crashlens/guard.py
git checkout HEAD -- crashlens/utils/feature_flags.py
```

---

## Commit Message

```
feat: Remove legacy guard engine - unified only

BREAKING CHANGE: CRASHLENS_USE_UNIFIED_ENGINE feature flag removed.
Unified PolicyEngine is now the only implementation.

Changes:
- Delete crashlens/utils/feature_flags.py
- Remove legacy evaluator from guard.py (~800 lines)
- Remove feature flag checks from guard_adapter.py, cli.py
- Update tests to remove env var mocking (15 files)
- Delete legacy vs unified comparison tests

Justification:
- Legacy code was redundant first draft
- No production users affected
- Unified engine proven with 177+ passing tests
- 100% parity achieved across all templates
- 14.1% performance improvement over legacy

Migration:
- guard command now always uses unified engine
- policy-check command unchanged (still works)
- No user-facing behavior changes (already using unified)

Rollback:
- git revert HEAD
- Or: git reset --hard v3.0.0-legacy

Files deleted: 1
Files modified: 9
Lines removed: ~950
Tests updated: 32
Tests deleted: 8
```

---

## Pre-Flight Checklist

Before executing:
- [x] Archive created (legacy/guard_legacy_snapshot.py)
- [x] Git tag created (v3.0.0-legacy)
- [ ] All tests passing (verify before changes)
- [ ] Identify exact line numbers for deletions
- [ ] Test suite runs successfully
- [ ] Benchmark still passes
- [ ] Documentation references updated

---

## Execution Order

1. ✅ Create archive (DONE)
2. ✅ Create git tag (DONE)
3. ⏳ Verify current tests pass
4. ⏳ Delete feature_flags.py
5. ⏳ Clean guard.py (remove legacy)
6. ⏳ Clean guard_adapter.py (remove checks)
7. ⏳ Clean cli.py (remove flag setting)
8. ⏳ Update all test files
9. ⏳ Run full test suite
10. ⏳ Run benchmarks
11. ⏳ Git commit
12. ⏳ Verify commit can be reverted

---

**Status:** Ready to execute  
**Confidence:** High (tests will validate)  
**Risk:** Low (full rollback capability)
