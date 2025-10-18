# 📁 CrashLens File Handling Manual

**Complete Guide to File Management and Report Generation**

---

## Table of Contents

1. [Introduction](#introduction)
2. [Basic File Operations](#basic-file-operations)
3. [Single File Handling](#single-file-handling)
4. [Multi-File Batch Operations](#multi-file-batch-operations)
5. [Directory Structure Management](#directory-structure-management)
6. [Report Organization](#report-organization)
7. [Advanced File Patterns](#advanced-file-patterns)
8. [Automation and CI/CD](#automation-and-cicd)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Introduction

CrashLens provides powerful file handling capabilities for analyzing LLM API logs. This manual teaches you how to effectively manage input files, organize reports, and handle various file scenarios.

### What You'll Learn
- ✅ How to scan single and multiple files
- ✅ How to organize reports effectively
- ✅ How to prevent filename collisions
- ✅ How to use glob patterns for batch scanning
- ✅ How to automate file processing
- ✅ How to handle different directory structures

---

## Basic File Operations

### Supported Input Formats

CrashLens accepts log files in **JSONL format** (JSON Lines):
- One JSON object per line
- Langfuse-compatible schema
- UTF-8 encoding

**Example Valid Log File**:
```json
{"id":"1","traceId":"trace-1","type":"generation","startTime":"2024-01-01T10:00:00Z","input":{"model":"gpt-4","prompt":"test"},"usage":{"prompt_tokens":50,"completion_tokens":100,"total_tokens":150}}
{"id":"2","traceId":"trace-2","type":"generation","startTime":"2024-01-01T10:01:00Z","input":{"model":"gpt-3.5-turbo","prompt":"test"},"usage":{"prompt_tokens":30,"completion_tokens":80,"total_tokens":110}}
```

### Supported Output Formats

CrashLens generates reports in multiple formats:
- **Markdown** (`.md`) - Human-readable reports
- **Slack** - Formatted for Slack messaging
- **JSON** - Machine-readable structured data

---

## Single File Handling

### Basic Single File Scan

**Command**:
```bash
crashlens scan my-logs.jsonl
```

**What Happens**:
- Reads `my-logs.jsonl` from current directory
- Analyzes for cost and waste patterns
- Outputs to console (default: Slack format)

### Single File with Custom Output

**Command**:
```bash
crashlens scan my-logs.jsonl --format markdown --report-dir ./reports/
```

**What Happens**:
- Reads `my-logs.jsonl`
- Generates `my-logs.md` in `./reports/` directory
- Uses Markdown format

**Directory Structure**:
```
./
├── my-logs.jsonl          (input)
└── reports/
    └── my-logs.md         (output)
```

### Single File with Specific Report Name

**Command**:
```bash
crashlens scan logs/prod.jsonl --report-file ./reports/production-analysis.md
```

**What Happens**:
- Reads `logs/prod.jsonl`
- Creates report at exact path specified
- Filename is `production-analysis.md`

**Directory Structure**:
```
./
├── logs/
│   └── prod.jsonl         (input)
└── reports/
    └── production-analysis.md  (output)
```

---

## Multi-File Batch Operations

### Scanning Multiple Specific Files

**Command**:
```bash
crashlens scan --log-paths "logs/file1.jsonl" --log-paths "logs/file2.jsonl" --report-dir ./reports/
```

**What Happens**:
- Processes both files
- Generates individual reports for each
- Creates aggregate summary

**Better Approach - Use Glob Patterns** (see next section)

### Batch Scan with Glob Pattern

**Command**:
```bash
crashlens scan --log-paths "logs/*.jsonl" --report-dir ./reports/
```

**What Happens**:
- Finds all `.jsonl` files in `logs/` directory
- Processes each file
- Generates individual reports
- Creates `_aggregate_report.md` summary

**Directory Structure**:
```
./
├── logs/
│   ├── file1.jsonl
│   ├── file2.jsonl
│   └── file3.jsonl
└── reports/
    ├── [path-to]/logs/file1.md
    ├── [path-to]/logs/file2.md
    ├── [path-to]/logs/file3.md
    └── _aggregate_report.md
```

### Recursive Batch Scan

**Command**:
```bash
crashlens scan --log-paths "logs/**/*.jsonl" --report-dir ./reports/
```

**What Happens**:
- Finds all `.jsonl` files recursively in `logs/` and subdirectories
- Processes each file
- Preserves directory structure in reports
- Creates aggregate summary

**Example Input**:
```
logs/
├── prod/
│   ├── api.jsonl
│   └── worker.jsonl
└── staging/
    └── api.jsonl
```

**Example Output** (default structure preservation):
```
reports/
├── [absolute-path]/logs/
│   ├── prod/
│   │   ├── api.md
│   │   └── worker.md
│   └── staging/
│       └── api.md
└── _aggregate_report.md
```

---

## Directory Structure Management

CrashLens offers two modes for organizing reports:

### Mode 1: Structure Preservation (Default)

**Purpose**: Prevents filename collisions when multiple files have the same name.

**Command**:
```bash
crashlens scan --log-paths "logs/**/*.jsonl" --report-dir ./reports/
```

**Use Case**: You have files like:
```
logs/
├── prod/app.jsonl
├── staging/app.jsonl
└── dev/app.jsonl
```

**Output**: Each `app.jsonl` gets its own report in separate directories:
```
reports/
├── C/Users/You/project/logs/
│   ├── prod/app.md
│   ├── staging/app.md
│   └── dev/app.md
└── _aggregate_report.md
```

**Benefits**:
- ✅ No filename collisions
- ✅ Clear source file identification
- ✅ Maintains organizational context

**Drawbacks**:
- ⚠️ Creates nested directory structure
- ⚠️ Uses absolute paths

---

### Mode 2: Flatten Mode (Legacy)

**Purpose**: Places all reports in single directory (legacy behavior).

**Command**:
```bash
crashlens scan --log-paths "logs/**/*.jsonl" --report-dir ./reports/ --flatten
```

**Same Input**:
```
logs/
├── prod/app.jsonl
├── staging/app.jsonl
└── dev/app.jsonl
```

**Output**: All reports at root level with collision handling:
```
reports/
├── app.md         (from prod)
├── app_1.md       (from staging)
├── app_2.md       (from dev)
└── _aggregate_report.md
```

**Benefits**:
- ✅ Simple flat structure
- ✅ All reports in one place
- ✅ Easy to browse

**Drawbacks**:
- ⚠️ Filename collision handling required
- ⚠️ Harder to identify source files

**When to Use Flatten Mode**:
- All input files have unique names
- You prefer simple directory structure
- Compatibility with legacy workflows

---

## Report Organization

### Understanding Report Types

#### 1. Individual Reports

**What**: Detailed analysis for each input file

**Filename**: Based on input filename (e.g., `api.jsonl` → `api.md`)

**Contains**:
- Detailed cost analysis
- Issue detection results
- Retry quality scores
- Trace-level information

#### 2. Aggregate Report

**What**: Summary of all scanned files

**Filename**: Always `_aggregate_report.md`

**Location**: Root of `--report-dir`

**Contains**:
- List of all processed files
- Total cost across all files
- Issue count summary
- Links to individual reports

**When Created**:
- ✅ Batch scans (2+ files)
- ❌ Single file scans

---

### Organizing Reports by Environment

**Best Practice**: Use subdirectories for different environments.

**Directory Structure**:
```
logs/
├── prod/
│   ├── api.jsonl
│   └── worker.jsonl
├── staging/
│   └── api.jsonl
└── dev/
    └── api.jsonl
```

**Command**:
```bash
crashlens scan --log-paths "logs/**/*.jsonl" --report-dir ./reports/
```

**Result**: Structure preserved, easy to navigate by environment.

---

### Organizing Reports by Date

**Best Practice**: Include date in directory names.

**Example**:
```bash
# Create daily reports
crashlens scan --log-paths "logs/*.jsonl" --report-dir "./reports/2024-01-15/"

# Create weekly reports
crashlens scan --log-paths "logs/*.jsonl" --report-dir "./reports/week-02/"
```

**Directory Structure**:
```
reports/
├── 2024-01-15/
│   ├── [reports]
│   └── _aggregate_report.md
├── 2024-01-16/
│   ├── [reports]
│   └── _aggregate_report.md
└── 2024-01-17/
    ├── [reports]
    └── _aggregate_report.md
```

---

## Advanced File Patterns

### Glob Pattern Reference

CrashLens uses glob patterns for flexible file matching:

| Pattern | Matches | Example |
|---------|---------|---------|
| `*` | Any characters (single level) | `logs/*.jsonl` matches `logs/api.jsonl` |
| `**` | Any characters (recursive) | `logs/**/*.jsonl` matches `logs/prod/api.jsonl` |
| `?` | Single character | `log?.jsonl` matches `log1.jsonl` |
| `[abc]` | Character set | `log[123].jsonl` matches `log1.jsonl` |
| `[!abc]` | Negated set | `log[!0].jsonl` matches `log1.jsonl` but not `log0.jsonl` |

### Common Pattern Examples

#### Match All JSONL Files in Directory
```bash
crashlens scan --log-paths "logs/*.jsonl" --report-dir ./reports/
```

#### Match All JSONL Files Recursively
```bash
crashlens scan --log-paths "logs/**/*.jsonl" --report-dir ./reports/
```

#### Match Specific Prefix
```bash
# Match all files starting with "prod-"
crashlens scan --log-paths "logs/prod-*.jsonl" --report-dir ./reports/
```

#### Match Multiple Patterns
```bash
# Match production and staging only
crashlens scan --log-paths "logs/{prod,staging}/*.jsonl" --report-dir ./reports/
```

#### Match by Date Pattern
```bash
# Match logs from January 2024
crashlens scan --log-paths "logs/2024-01-*.jsonl" --report-dir ./reports/
```

#### Match Nested Directories
```bash
# Match all api.jsonl files in any subdirectory
crashlens scan --log-paths "**/api.jsonl" --report-dir ./reports/
```

---

## Automation and CI/CD

### Force Flag for Non-Interactive Mode

**Problem**: CrashLens prompts before overwriting existing reports.

**Solution**: Use `--force` flag to skip prompts.

**Command**:
```bash
crashlens scan --log-paths "logs/**/*.jsonl" --report-dir ./reports/ --force
```

**Result**: Overwrites existing reports without confirmation (perfect for automation).

---

### CI/CD Pipeline Example (GitHub Actions)

**File**: `.github/workflows/crashlens-analysis.yml`

```yaml
name: CrashLens Analysis

on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight
  workflow_dispatch:

jobs:
  analyze:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install CrashLens
        run: pip install crashlens
      
      - name: Run CrashLens Analysis
        run: |
          crashlens scan \
            --log-paths "logs/**/*.jsonl" \
            --report-dir ./reports/ \
            --format markdown \
            --force
      
      - name: Upload Reports as Artifacts
        uses: actions/upload-artifact@v3
        with:
          name: crashlens-reports
          path: reports/
      
      - name: Check for High Severity Issues
        run: |
          if grep -q "HIGH severity" reports/_aggregate_report.md; then
            echo "⚠️ High severity issues detected!"
            exit 1
          fi
```

---

### Automated Daily Reports Script

**File**: `daily-analysis.sh`

```bash
#!/bin/bash

# Configuration
LOG_DIR="./logs"
REPORT_DIR="./reports/$(date +%Y-%m-%d)"
EMAIL="team@example.com"

# Run CrashLens
crashlens scan \
  --log-paths "$LOG_DIR/**/*.jsonl" \
  --report-dir "$REPORT_DIR" \
  --format markdown \
  --force

# Send aggregate report via email
mail -s "CrashLens Daily Report - $(date +%Y-%m-%d)" \
  "$EMAIL" < "$REPORT_DIR/_aggregate_report.md"

echo "✅ Daily analysis complete. Reports saved to $REPORT_DIR"
```

**Make Executable**:
```bash
chmod +x daily-analysis.sh
```

**Run Daily via Cron**:
```bash
# Edit crontab
crontab -e

# Add line (runs daily at 2 AM)
0 2 * * * /path/to/daily-analysis.sh
```

---

## Best Practices

### 1. Organize Input Files by Context

**Good**:
```
logs/
├── prod/
│   ├── api-2024-01-15.jsonl
│   └── worker-2024-01-15.jsonl
├── staging/
│   └── api-2024-01-15.jsonl
└── dev/
    └── api-2024-01-15.jsonl
```

**Why**: Easy to scan by environment, clear organization.

---

### 2. Use Consistent Naming Conventions

**Good**:
```
logs/
├── api-prod-2024-01-15.jsonl
├── api-staging-2024-01-15.jsonl
└── api-dev-2024-01-15.jsonl
```

**Pattern**: `{service}-{env}-{date}.jsonl`

**Why**: Easy to filter with glob patterns.

**Command**:
```bash
# Scan only production logs
crashlens scan --log-paths "logs/*-prod-*.jsonl" --report-dir ./reports/
```

---

### 3. Separate Reports by Time Period

**Good**:
```
reports/
├── 2024-01/
│   ├── week-01/
│   ├── week-02/
│   └── week-03/
└── 2024-02/
    └── week-01/
```

**Command**:
```bash
# Weekly reports
crashlens scan \
  --log-paths "logs/2024-01-week-01/*.jsonl" \
  --report-dir "./reports/2024-01/week-01/" \
  --force
```

---

### 4. Use Flatten Mode for Simple Cases

**When to Use Flatten**:
- All input files have unique names
- Single directory of logs
- Simple reporting needs

**Command**:
```bash
crashlens scan \
  --log-paths "logs/*.jsonl" \
  --report-dir ./reports/ \
  --flatten
```

---

### 5. Use Structure Preservation for Complex Cases

**When to Use Structure Preservation**:
- Multiple directories with same filenames
- Need to maintain organizational context
- Preventing filename collisions

**Command**:
```bash
crashlens scan \
  --log-paths "logs/**/*.jsonl" \
  --report-dir ./reports/
```

---

### 6. Always Use --force in Automation

**Why**: Prevents scripts from hanging on overwrite prompts.

**Command**:
```bash
crashlens scan \
  --log-paths "logs/**/*.jsonl" \
  --report-dir ./reports/ \
  --force
```

---

### 7. Archive Old Reports

**Script**: `archive-old-reports.sh`

```bash
#!/bin/bash

# Archive reports older than 30 days
find ./reports/ -type f -mtime +30 -name "*.md" -exec gzip {} \;

# Move to archive directory
mkdir -p ./reports-archive/
find ./reports/ -type f -name "*.md.gz" -exec mv {} ./reports-archive/ \;

echo "✅ Old reports archived"
```

---

### 8. Use Descriptive Report Directories

**Good**:
```bash
crashlens scan \
  --log-paths "logs/prod/*.jsonl" \
  --report-dir "./reports/prod-analysis-2024-01-15/" \
  --force
```

**Bad**:
```bash
crashlens scan \
  --log-paths "logs/prod/*.jsonl" \
  --report-dir "./output/" \
  --force
```

**Why**: Clear naming makes reports easier to find later.

---

## Troubleshooting

### Problem 1: No Files Found

**Error**:
```
No files found for pattern: logs/**/*.jsonl
```

**Solutions**:

1. **Check Pattern Syntax**:
```bash
# Wrong (missing quotes on Windows)
crashlens scan --log-paths logs/**/*.jsonl

# Correct (use quotes)
crashlens scan --log-paths "logs/**/*.jsonl"
```

2. **Verify File Extension**:
```bash
# Check what files exist
ls logs/

# Make sure files end in .jsonl, not .json
```

3. **Check Working Directory**:
```bash
# Print current directory
pwd

# Make sure logs/ exists in current directory
ls -la logs/
```

---

### Problem 2: Reports Not Where Expected

**Issue**: Reports created in unexpected location.

**Solutions**:

1. **Check Absolute Path**:
```bash
# Use absolute paths for clarity
crashlens scan \
  --log-paths "/full/path/to/logs/*.jsonl" \
  --report-dir "/full/path/to/reports/"
```

2. **Verify Report Directory**:
```bash
# CrashLens creates the directory if it doesn't exist
# Check where it was created
find . -name "_aggregate_report.md"
```

---

### Problem 3: Filename Collisions

**Issue**: Multiple files named `app.jsonl` overwriting each other.

**Solution 1**: Use Structure Preservation (default)
```bash
crashlens scan \
  --log-paths "logs/**/*.jsonl" \
  --report-dir ./reports/
# Each app.jsonl gets separate directory
```

**Solution 2**: Rename files before scanning
```bash
# Rename with environment prefix
mv logs/prod/app.jsonl logs/prod/prod-app.jsonl
mv logs/dev/app.jsonl logs/dev/dev-app.jsonl

# Now scan with flatten
crashlens scan \
  --log-paths "logs/**/*.jsonl" \
  --report-dir ./reports/ \
  --flatten
```

---

### Problem 4: Permission Denied

**Error**:
```
❌ ERROR: No write permission for directory: /reports
```

**Solutions**:

1. **Use User-Writable Directory**:
```bash
# Use home directory or current directory
crashlens scan \
  --log-paths "logs/*.jsonl" \
  --report-dir "./reports/"
```

2. **Check Permissions**:
```bash
# Check directory permissions
ls -la ./reports/

# Fix permissions if needed
chmod 755 ./reports/
```

---

### Problem 5: Overwrite Prompt in Automation

**Issue**: Script hangs waiting for overwrite confirmation.

**Solution**: Always use `--force` in automation
```bash
crashlens scan \
  --log-paths "logs/**/*.jsonl" \
  --report-dir ./reports/ \
  --force
```

---

### Problem 6: Aggregate Report Not Created

**Issue**: Expected `_aggregate_report.md` but it doesn't exist.

**Cause**: Aggregate only created for 2+ files.

**Solutions**:

1. **Check File Count**:
```bash
# Count matching files
ls logs/*.jsonl | wc -l

# If only 1 file, no aggregate is created
```

2. **Scan Multiple Files**:
```bash
# Make sure pattern matches 2+ files
crashlens scan \
  --log-paths "logs/**/*.jsonl" \
  --report-dir ./reports/
```

---

### Problem 7: Invalid JSON Errors

**Error**:
```
❌ Error: Failed to parse line 5: Invalid JSON
```

**Solutions**:

1. **Validate JSON Format**:
```bash
# Check file is valid JSONL
cat logs/test.jsonl | jq . > /dev/null
```

2. **Check for Common Issues**:
- Each line must be valid JSON
- No trailing commas
- Use double quotes (not single)
- No comments in JSON

3. **Example Valid JSONL**:
```jsonl
{"id":"1","traceId":"t1","type":"generation"}
{"id":"2","traceId":"t2","type":"generation"}
```

4. **Example Invalid JSONL**:
```jsonl
{"id":"1","traceId":"t1","type":"generation"},  ❌ Trailing comma
{'id':'2','traceId':'t2','type':'generation'}   ❌ Single quotes
```

---

## Quick Reference Commands

### Common Workflows

**Single File Analysis**:
```bash
crashlens scan my-logs.jsonl --format markdown
```

**Batch Analysis (Structure Preserved)**:
```bash
crashlens scan --log-paths "logs/**/*.jsonl" --report-dir ./reports/
```

**Batch Analysis (Flat Structure)**:
```bash
crashlens scan --log-paths "logs/**/*.jsonl" --report-dir ./reports/ --flatten
```

**Automation Mode**:
```bash
crashlens scan --log-paths "logs/**/*.jsonl" --report-dir ./reports/ --force
```

**Environment-Specific Scan**:
```bash
crashlens scan --log-paths "logs/prod/*.jsonl" --report-dir ./reports/prod/
```

**Date-Based Scan**:
```bash
crashlens scan --log-paths "logs/2024-01-*.jsonl" --report-dir ./reports/january/
```

---

## Command Reference Table

| Use Case | Command |
|----------|---------|
| Single file, console output | `crashlens scan file.jsonl` |
| Single file, markdown report | `crashlens scan file.jsonl --format markdown --report-dir ./reports/` |
| Batch scan, structure preserved | `crashlens scan --log-paths "logs/**/*.jsonl" --report-dir ./reports/` |
| Batch scan, flat structure | `crashlens scan --log-paths "logs/**/*.jsonl" --report-dir ./reports/ --flatten` |
| Automation mode | `crashlens scan --log-paths "logs/**/*.jsonl" --report-dir ./reports/ --force` |
| Specific file pattern | `crashlens scan --log-paths "logs/prod-*.jsonl" --report-dir ./reports/` |
| Custom report name | `crashlens scan file.jsonl --report-file ./custom-name.md` |
| Multiple formats | `crashlens scan file.jsonl --format markdown --detailed` |

---

## File Handling Checklist

Before running CrashLens:

- ✅ Input files are valid JSONL format
- ✅ Input files use UTF-8 encoding
- ✅ Glob patterns are quoted (e.g., `"logs/**/*.jsonl"`)
- ✅ Report directory is writable
- ✅ Using `--force` for automation
- ✅ Using `--flatten` or structure preservation intentionally
- ✅ File naming conventions are consistent

After running CrashLens:

- ✅ Check `_aggregate_report.md` for overview
- ✅ Review individual reports for details
- ✅ Archive old reports periodically
- ✅ Verify no HIGH severity issues
- ✅ Monitor report disk usage

---

## Summary

### Key Takeaways

1. **Single Files**: Use `crashlens scan file.jsonl`
2. **Multiple Files**: Use `--log-paths "pattern"` with glob patterns
3. **Structure Preservation**: Default behavior, prevents collisions
4. **Flatten Mode**: Use `--flatten` for simple flat structure
5. **Automation**: Always use `--force` flag
6. **Aggregate Reports**: Auto-created for 2+ files
7. **Organization**: Use consistent naming and directory structure

### Next Steps

1. Read `QUICK_REFERENCE.md` for command examples
2. Try manual testing from `FEATURE_IMPLEMENTATION_REPORT.md`
3. Review `ACCEPTANCE_CRITERIA_FINAL.md` for best practices
4. Set up automation using examples in this manual

---

**Manual Version**: 1.0  
**Last Updated**: October 18, 2025  
**For CrashLens Version**: 1.0+

**Need Help?** See troubleshooting section or review test files in `tests/` directory.
