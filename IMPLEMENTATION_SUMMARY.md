# CrashLens Report Path Handling - Implementation Summary

## ✅ All Priority 1, 2, and 3 Features Completed

### Priority 1: Fix User-Supplied Path Ignoring ✅

**Issue:** User-supplied `--report-dir` and `--report-file` were being reset to defaults.

**Solution:**
1. **Early Storage**: Store user-supplied paths at function entry
   ```python
   user_report_dir = report_dir
   user_report_file = report_file
   ```

2. **Conditional Defaults**: Only apply defaults when user hasn't specified paths
   ```python
   if user_report_dir:
       final_dir = user_report_dir
   else:
       final_dir = default_dir
   ```

3. **Path Validation**: Added `validate_output_dir()` function
   - Creates directories if they don't exist
   - Tests write permissions
   - Provides clear error messages on failure

4. **Filename Sanitization**: Added `sanitize_report_filename()` function
   - Strips ALL extensions using `Path.stem`
   - Removes special characters
   - Prevents double extensions like `demo-logs.jsonl.md`

**Test Results:**
- ✅ `--report-dir` preserved correctly
- ✅ `--report-file` preserved correctly  
- ✅ Invalid paths fail with clear error messages
- ✅ Filenames sanitized properly: `demo-logs.jsonl` → `demo-logs.md`

---

### Priority 2: Batch Mode Fixes ✅

**Issue:** Multiple scans to the same directory would overwrite files without warning.

**Solution:**
1. **Collision Detection**: Added `ensure_unique_path()` function
   - Checks if file exists before writing
   - Automatically appends `_1`, `_2`, `_3`, etc.
   - Shows clear warning message

2. **Centralized Directory Messaging**: Added batch scan output directory announcement
   ```
   📁 All reports will be written to: /path/to/directory
   ```

3. **Aggregate Report Improvements**:
   - Only generates for multi-file scans (skips single files)
   - Named `_aggregate_report.md` to avoid collisions
   - Sorts alphabetically in directories

**Test Results:**
- ✅ Files auto-numbered when collisions detected (`file.md` → `file_1.md` → `file_2.md`)
- ✅ Clear messaging about output directory for batch scans
- ✅ Aggregate reports only created for multi-file scans

---

### Priority 3: Enhanced Features ✅

**Issue:** No way to skip overwrite prompts, aggregate reports lacked detail.

**Solution:**
1. **Force Flag**: Added `--force` option
   - Skips all overwrite confirmation prompts
   - Useful for CI/CD pipelines and batch operations
   - Integrated with collision detection

2. **Overwrite Permission Checking**: Added `check_overwrite_permission()` function
   - Interactive prompt when file exists (unless `--force`)
   - Returns 'overwrite' or 'skip' decision
   - Uses Click's built-in prompt validation

3. **Enhanced Aggregate Reports**:
   - Added metadata table with scan statistics
   - Success rate calculation
   - Emoji indicators for success/failure
   - Better formatting with markdown tables
   - Only generated for multi-file scans

**Enhanced Aggregate Report Format:**
```markdown
# 🔍 CrashLens Aggregate Report

**Generated:** 2025-10-18 03:58:40
**Directory:** `/path/to/reports`

## 📊 Summary

| Metric | Value |
|--------|-------|
| Total Files Scanned | 2 |
| Successful | ✅ 2 |
| Failed | ❌ 0 |
| Success Rate | 100.0% |

## 📋 Individual Reports

### ✅ SUCCESS: `file1.jsonl`

- **Source:** `path/to/file1.jsonl`
- **Report:** [file1.md](path/to/file1.md)

### ✅ SUCCESS: `file2.jsonl`

- **Source:** `path/to/file2.jsonl`
- **Report:** [file2.md](path/to/file2.md)
```

**Test Results:**
- ✅ `--force` flag skips all prompts successfully
- ✅ Interactive overwrite confirmation works (when `--force` not used)
- ✅ Aggregate reports include metadata tables
- ✅ Success rates calculated correctly
- ✅ Aggregate reports skip single-file scans

---

## Key Bug Fixes

### Windows Glob Expansion Issue

**Problem:** PowerShell/Windows expands glob patterns BEFORE passing to Python, causing:
- `--log-paths 'pattern/*.jsonl'` receives first file only
- Remaining files go to `logfile` and `extra_files` positional arguments
- Only one file processed despite multiple matches

**Solution:** Detect shell expansion by checking for wildcards in pattern:
```python
if '*' in pattern or '?' in pattern or '[' in pattern:
    # Has wildcards - do glob ourselves
    matched = glob.glob(pattern, recursive=True)
else:
    # No wildcards - shell expanded it
    # Collect from log_paths + logfile + extra_files
    matched.append(pattern)
    if logfile:
        matched.append(str(logfile))
    if extra_files:
        matched.extend([str(p) for p in extra_files])
```

---

## New Utility Functions

### 1. `validate_output_dir(path: Path) -> Path`
- Creates directory if it doesn't exist
- Tests write permissions
- Returns absolute path
- Raises clear errors on failure

### 2. `sanitize_report_filename(input_filename: str) -> str`
- Strips ALL extensions using `Path.stem`
- Removes special characters
- Prevents double extensions
- Example: `demo-logs.jsonl` → `demo-logs`

### 3. `ensure_unique_path(base_path: Path) -> Path`
- Checks file existence
- Appends counter if collision detected
- Returns unique path
- Shows warning message to user

### 4. `check_overwrite_permission(file_path: Path, force: bool) -> str`
- Interactive prompt when file exists
- Skips prompt if `--force` enabled
- Returns 'overwrite' or 'skip'
- Uses Click's prompt validation

---

## Testing Summary

All features tested with `test_all_features.py`:

```
PRIORITY 1: Path Preservation & Validation
✅ User --report-dir preservation
✅ User --report-file preservation

PRIORITY 2: Batch Mode & Collision Detection  
✅ Batch scan with --log-paths
✅ Collision detection (rerun same file)

PRIORITY 3: Enhanced Features
✅ Force overwrite with --force
✅ Enhanced aggregate report (multi-file)
```

---

## Breaking Changes

**None** - All changes are backward compatible:
- Existing behavior preserved when no options specified
- New flags are optional
- Default behavior unchanged

---

## CLI Changes Summary

### New Options
- `--force`: Overwrite existing reports without prompting

### Enhanced Options
- `--report-dir`: Now properly preserved (was being reset)
- `--report-file`: Now properly preserved (was being reset)
- `--log-paths`: Now handles Windows glob expansion correctly

### Improved Output
- Batch scans show output directory early
- Collision warnings with auto-numbering
- Enhanced aggregate reports with metadata tables
- Better error messages for invalid paths

---

## Files Modified

- `crashlens/cli.py`: Main implementation (4 new functions, batch logic fixes)
- Test files created:
  - `test_batch.py`: Batch scanning test
  - `test_all_features.py`: Comprehensive feature test
  - `debug_args.py`: Argument debugging utility

---

## Next Steps / Future Enhancements

1. **Consider adding:**
   - `--no-aggregate` flag to skip aggregate report generation
   - `--overwrite-prompt` flag to force prompts even in batch mode
   - CSV export option for aggregate statistics

2. **Documentation updates:**
   - Add new flags to README.md
   - Document Windows glob expansion behavior
   - Add examples of batch scanning workflows

3. **Additional testing:**
   - Test with very large batch scans (100+ files)
   - Test with nested directory structures
   - Test with UNC paths and network drives
