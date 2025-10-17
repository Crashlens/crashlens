# Report Path Handling Improvements

## Summary
Implemented comprehensive report path handling with user-supplied flags, path validation, and clean filename generation.

## Changes Made

### 1. User-Supplied Path Preservation ✅
**Problem**: `--report-dir` and `--report-file` flags were being reset and ignored

**Solution**: Store user inputs early and only apply defaults when flags are absent
```python
user_report_dir = report_dir
user_report_file = report_file
```

**Test Results**:
- ✅ `crashlens scan sample-logs/demo-logs.jsonl` → `sample-logs-reports/demo-logs.md`
- ✅ `crashlens scan sample-logs/retry-test.jsonl --report-file my-custom-report.md` → `my-custom-report.md`
- ✅ `crashlens scan --log-paths "sample-logs/retry*.jsonl" --report-dir final_test` → `final_test/retry-loops-demo.md`

### 2. Path Validation with Clear Errors ✅
**Problem**: Invalid paths failed silently or with cryptic errors

**Solution**: Added `validate_output_dir()` function that:
- Creates directories with `parents=True`
- Tests write permissions with a temporary file
- Provides clear, actionable error messages

**Example Error**:
```
❌ ERROR: Cannot create directory: Z:\nonexistent\path
   Reason: [WinError 3] The system cannot find the path specified: 'Z:\\'
```

### 3. Fixed Filename Extension Handling ✅
**Problem**: `app.log.jsonl` became `app.log.jsonl.md` instead of `app.md`

**Solution**: Created `sanitize_report_filename()` function that:
- Uses `Path.stem` to strip ALL extensions
- Sanitizes special characters (spaces → underscores, removes non-alphanumeric)
- Applies correct extension based on output format

**Examples**:
- `demo-logs.jsonl` → `demo-logs.md` ✅
- `retry-test.jsonl` → `retry-test.md` ✅
- `my logs@data#2.jsonl` → `my_logsdata2.md`

### 4. Improved Aggregate Reports ✅
**Enhancement**: Added richer summary statistics and better formatting

**New Format**:
```markdown
# CrashLens Aggregate Report
Generated: 2025-10-18T03:24:41.796905

## Summary
- Total files scanned: 1
- Successful scans: 1
- Failed scans: 0

## File Details
- **✅ OK** `sample-logs\retry-loops-demo.jsonl` → [report path](report path)
```

### 5. Input Validation Fix ✅
**Problem**: PowerShell glob expansion caused multiple input source errors

**Solution**: Exclude `logfile` from validation when `--log-paths` is provided
```python
input_count = sum([bool(logfile) and not log_paths, demo, stdin, paste, from_langfuse, from_helicone, bool(log_paths)])
```

## Test Coverage

### Single-File Scans
| Test | Command | Expected Output | Status |
|------|---------|----------------|--------|
| Default | `crashlens scan sample-logs/demo-logs.jsonl` | `sample-logs-reports/demo-logs.md` | ✅ |
| Custom Dir | `crashlens scan sample-logs/simple-test.jsonl --report-dir custom_reports` | `custom_reports/simple-test.md` | ✅ |
| Custom File | `crashlens scan sample-logs/retry-test.jsonl --report-file my-custom-report.md` | `my-custom-report.md` | ✅ |
| Invalid Path | `crashlens scan sample-logs/demo-logs.jsonl --report-dir "Z:\nonexistent\path"` | Clear error message | ✅ |

### Batch Scans (`--log-paths`)
| Test | Command | Expected Output | Status |
|------|---------|----------------|--------|
| Default | `crashlens scan --log-paths "sample-logs/*.jsonl" --report-dir batch_test_reports` | Per-file reports + aggregate | ✅ |
| Multi-file | `crashlens scan --log-paths "sample-logs/retry*.jsonl" --report-dir final_test` | Clean filenames + aggregate | ✅ |

## API Reference

### New Functions

#### `validate_output_dir(dir_path: Path) -> Path`
Validates and creates output directory with clear error messages.
- Creates directory tree if needed
- Tests write permissions
- Returns resolved absolute path
- Exits with error code 1 on failure

#### `sanitize_report_filename(source_path: Path, output_format: str = 'md', user_filename: Optional[str] = None) -> str`
Generates safe report filename from source path.
- Strips all extensions using `Path.stem`
- Sanitizes special characters
- Applies correct extension (`.md` or `.json`)
- Handles user-provided filenames

## Files Modified
- `crashlens/cli.py`:
  - Added utility functions (lines 60-117)
  - Updated report path resolution logic (lines 1230-1250)
  - Updated batch scan filename handling (lines 710-850)
  - Fixed input validation for `--log-paths` (line 695)

## Breaking Changes
None - all changes are backwards compatible with existing behavior as defaults.

## Future Improvements
- [ ] Add `--overwrite` flag to control report overwriting behavior
- [ ] Implement JSON aggregate output option
- [ ] Add encoding fallback for non-UTF8 files
- [ ] Consider parallel processing for large batch scans
