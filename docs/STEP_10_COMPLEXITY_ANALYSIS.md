# Step 10 Cleanup - Complexity Analysis and Recommendation

**Date:** November 8, 2025  
**Status:** ⚠️ COMPLEXITY TOO HIGH FOR IMMEDIATE EXECUTION

---

## Problem Statement

The legacy code cleanup (Step 10) is **more complex than initially assessed**:

1. **guard.py is 1401 lines** with deeply intertwined legacy/unified code paths
2. **119 tests currently failing** (many expecting legacy behavior)
3. **Feature flag references in 100+ locations** across codebase
4. **No production deployment** means we can be aggressive, BUT...
5. **Test suite must remain green** throughout the change

---

## Current State After Partial Cleanup

### ✅ Completed
- Archive created: `legacy/guard_legacy_snapshot.py`
- Git tag created: `v3.0.0-legacy`
- cli.py cleaned: Removed `CRASHLENS_USE_UNIFIED_ENGINE=1` setting from policy-check

### ⏳ In Progress
- guard.py: Attempted cleanup, but file structure too complex for surgical edits

### ❌ Not Started
- guard_adapter.py: Remove feature flag checks
- feature_flags.py: Delete file
- 15+ test files: Remove feature flag mocking
- Documentation: Update to reflect single engine

---

## Complexity Factors

### 1. guard.py Structure (1401 lines)

**Lines 1-870:** Mixed legacy code
- Imports, PII patterns, schemas, Rule dataclass
- Legacy helper functions: `eval_condition()`, `format_*_report()`, etc.
- Streaming reader integration
- All of this is either:
  a) Still needed by unified path, OR  
  b) Redundant but hard to identify without breaking tests

**Lines 870-940:** CLI command definition
- KEEP: This is the interface

**Lines 940-1020:** Unified engine block
- KEEP: This is the new path
- BUT: References legacy structures (Rule dataclass, format functions)

**Lines 1020-1350:** Legacy evaluation loop
- DELETE: This is the redundant first draft
- BUT: Intertwined with unified path via shared variables

**Lines 1350-1401:** Output formatting and exit
- KEEP: Needed by both paths currently
- REFACTOR: Should work with unified-only data

### 2. Test Failures (119 failing)

Many tests are failing because:
- They set `CRASHLENS_USE_UNIFIED_ENGINE=0` (legacy mode)
- Legacy mode is still the **default** in current code
- Tests expect legacy output format
- Tests mock feature flags

**Categories:**
- `test_guard.py`: 10+ failures (expecting legacy behavior)
- `test_autodiscover_rules.py`: Failures due to deprecation warnings
- `test_comprehensive_structure_preservation.py`: 30+ failures (artifact naming)
- `test_guard_cost_cap.py`: 10 failures (output format changes)
- `test_streaming_integration.py`: Failures (streaming mode messages)
- `test_malformed_jsonl.py`: Failures (warning messages changed)

---

## Recommended Approach

### Option A: Gradual Multi-Commit Cleanup (SAFER)

**Commit 1: Default to Unified**
```bash
# Change default from "0" to "1" in guard.py
use_unified_engine = os.getenv("CRASHLENS_USE_UNIFIED_ENGINE", "1") == "1"  # Changed default

# Run tests, fix any that break
# This makes unified the default but keeps legacy as fallback
```

**Commit 2: Fix Tests for Unified Default**
```bash
# Update all tests to expect unified behavior
# Remove tests that explicitly test legacy-only features
# ~20 test files to update
```

**Commit 3: Remove Legacy Code Path**
```bash
# Once tests pass with unified as default, remove legacy block
# Delete lines 1020-1350 from guard.py
# Remove "else:" block
```

**Commit 4: Remove Feature Flag Infrastructure**
```bash
# Delete feature_flags.py
# Remove env var checks from guard.py, guard_adapter.py, cli.py
# Clean up documentation
```

**Commit 5: Final Cleanup**
```bash
# Remove unused imports
# Delete redundant helper functions
# Update docs
```

**Timeline:** 5 commits over 1-2 days  
**Risk:** Low (each commit independently testable)  
**Rollback:** Easy (revert specific commit)

---

### Option B: Atomic Single-Commit Cleanup (FASTER, RISKIER)

**What We'd Do:**
1. Create entirely new `guard_simple.py` with ONLY unified path (~300 lines)
2. Replace `guard.py` with `guard_simple.py`
3. Delete `feature_flags.py`
4. Mass-update all test files (regex find/replace for common patterns)
5. Fix remaining test failures manually
6. Commit everything at once

**Challenges:**
- High chance of missing edge cases
- Hard to debug if something breaks
- All-or-nothing approach (can't partially revert)
- Might take 4-6 hours to get all tests green

**Timeline:** 1 large commit, 4-6 hours work  
**Risk:** Medium (complex change, many moving parts)  
**Rollback:** `git revert HEAD` (but loses all progress)

---

### Option C: Hybrid Approach (RECOMMENDED)

**Phase 1: Make Unified Default (THIS SESSION)**
```bash
# 1. Change default in guard.py (1 line)
use_unified_engine = os.getenv("CRASHLENS_USE_UNIFIED_ENGINE", "1") == "1"

# 2. Run tests, identify failures
poetry run pytest tests/ -v > test_results.txt

# 3. Fix ~10 critical tests that prevent guard from working
# 4. Commit: "feat: Make unified engine default (legacy still available)"
```

**Phase 2: Remove Legacy Path (NEXT SESSION)**
```bash
# 1. Delete legacy code block from guard.py
# 2. Fix remaining test failures
# 3. Commit: "feat: Remove legacy evaluation path"
```

**Phase 3: Clean Infrastructure (FINAL SESSION)**
```bash
# 1. Delete feature_flags.py
# 2. Remove all env var checks
# 3. Update docs
# 4. Commit: "chore: Remove feature flag infrastructure"
```

**Timeline:** 3 sessions, ~2-3 hours total  
**Risk:** Low (incremental, testable at each step)  
**Rollback:** Easy (each phase independently revertible)

---

## Immediate Next Steps (If Proceeding)

### Step 1: Change Default to Unified (5 minutes)

```python
# crashlens/guard.py line 947
# BEFORE:
use_unified_engine = os.getenv("CRASHLENS_USE_UNIFIED_ENGINE", "0") == "1"

# AFTER:
use_unified_engine = os.getenv("CRASHLENS_USE_UNIFIED_ENGINE", "1") == "1"
```

### Step 2: Run Smoke Test (2 minutes)

```bash
poetry run crashlens guard sample-logs/demo-logs.jsonl --rules policies/retry-loop-detector.yaml
# Should work and show unified engine message
```

### Step 3: Identify Critical Test Failures (5 minutes)

```bash
poetry run pytest tests/test_guard.py -v
# Fix these first (they test core guard functionality)
```

### Step 4: Fix Critical Tests (30-60 minutes)

Focus on:
- `test_guard.py` (core functionality)
- `test_cli_alias.py` (command routing)
- `test_guard_unified_integration.py` (unified engine)

### Step 5: Commit Phase 1 (2 minutes)

```bash
git add crashlens/guard.py crashlens/cli.py tests/
git commit -m "feat: Make unified PolicyEngine default

- Change CRASHLENS_USE_UNIFIED_ENGINE default from '0' to '1'
- Unified engine now default, legacy available with =0
- Fix critical tests for unified default

BREAKING: Legacy engine no longer default
Rollback: Set CRASHLENS_USE_UNIFIED_ENGINE=0"
```

---

## Decision Point

**Do you want to:**

**A)** Proceed with **Hybrid Phase 1** now (make unified default, fix critical tests)?  
**B)** Create detailed **Option A plan** (5-commit gradual cleanup) for future execution?  
**C)** Attempt **Option B** (atomic cleanup) despite risks?  
**D)** Stop cleanup, document current state, revisit later?

---

## Files Already Modified (This Session)

1. ✅ `legacy/guard_legacy_snapshot.py` - Archive created
2. ✅ `crashlens/cli.py` - Removed `CRASHLENS_USE_UNIFIED_ENGINE=1` from policy-check
3. ✅ `docs/STEP_10_CLEANUP_PLAN.md` - Implementation plan documented
4. ✅ `docs/STEP_10_COMPLEXITY_ANALYSIS.md` - This file

**Git Status:** 4 new/modified files, not yet committed

---

## Recommendation

**PROCEED WITH HYBRID PHASE 1:**

1. Change default to unified (1 line change in guard.py)
2. Fix 5-10 critical tests (1 hour work)
3. Commit Phase 1 with rollback instructions
4. Schedule Phase 2/3 for future sessions

**Why:**
- Achieves 80% of the goal (unified becomes default)
- Low risk (legacy still available as fallback)
- Manageable scope for one session
- Easy rollback
- Tests will be mostly green

**Alternative if time-constrained:**
- Document current state
- Commit archive and planning docs
- Execute cleanup in future dedicated session

---

**Your call. What would you like to do?**
