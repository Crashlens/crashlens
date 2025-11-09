# CrashLens PII Remove Command

**Data sanitization for LLM API logs**

---

## Table of Contents

1. [Overview](#overview)
2. [Basic Usage](#basic-usage)
3. [PII Types & Patterns](#pii-types--patterns)
4. [Dry Run Mode](#dry-run-mode)
5. [Selective Removal](#selective-removal)
6. [Verbose Logging](#verbose-logging)
7. [Batch Processing](#batch-processing)
8. [Integration with Guard](#integration-with-guard)
9. [Complete Examples](#complete-examples)
10. [Best Practices](#best-practices)

---

## Overview

The `pii-remove` command **sanitizes JSONL log files** by detecting and removing personally identifiable information (PII) before analysis or sharing.

**Key Features**:
✅ **7 PII Types** - Emails, phones, SSNs, credit cards, IPs, names, addresses  
✅ **Dry Run Preview** - See what will be removed without making changes  
✅ **Selective Removal** - Choose specific PII types to remove  
✅ **Verbose Logging** - Detailed detection reports  
✅ **Pattern Discovery** - List all available PII patterns  
✅ **Batch Processing** - Handle multiple files at once  
✅ **Privacy First** - Local processing, no external API calls  

**Syntax**:
```bash
crashlens pii-remove INPUT [OPTIONS]
```

**Quick Start**:
```bash
# Remove all PII types
crashlens pii-remove logs.jsonl

# Preview changes
crashlens pii-remove logs.jsonl --dry-run

# Remove specific types
crashlens pii-remove logs.jsonl --types email,phone
```

---

## Basic Usage

### Remove All PII

```bash
# Default: removes all PII types
crashlens pii-remove logs.jsonl

# Output: logs-cleaned.jsonl (automatic naming)
```

### Custom Output Path

```bash
# Specify output file
crashlens pii-remove logs.jsonl --output sanitized.jsonl

# Output to different directory
crashlens pii-remove logs.jsonl --output ./clean/logs.jsonl
```

### Alias Command

```bash
# pii-clean is an alias for pii-remove
crashlens pii-clean logs.jsonl

# Both commands work identically
crashlens pii-remove logs.jsonl
```

### Basic Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `INPUT` | Path | Required | Input JSONL file |
| `--output` | Path | `<input>-cleaned.jsonl` | Output file path |

---

## PII Types & Patterns

### Available PII Types

**7 detection categories**:

1. **email** - Email addresses
2. **phone** - Phone numbers (US/international)
3. **ssn** - Social Security Numbers
4. **credit-card** - Credit card numbers
5. **ip** - IP addresses (IPv4/IPv6)
6. **name** - Person names (first, last, full)
7. **address** - Physical addresses

### List Available Patterns

**See all detection patterns**:

```bash
# Show all PII types and their patterns
crashlens pii-remove --list-types
```

**Example output**:
```
📋 Available PII Types & Patterns

1. email
   Pattern: [a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
   Examples: user@example.com, john.doe@company.org
   Replacement: [EMAIL_REDACTED]

2. phone
   Pattern: \+?1?\d{10,14}
   Examples: +1-555-123-4567, (555) 123-4567
   Replacement: [PHONE_REDACTED]

3. ssn
   Pattern: \d{3}-\d{2}-\d{4}
   Examples: 123-45-6789
   Replacement: [SSN_REDACTED]

4. credit-card
   Pattern: \d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}
   Examples: 1234-5678-9012-3456
   Replacement: [CC_REDACTED]

5. ip
   Pattern: IPv4 and IPv6 formats
   Examples: 192.168.1.1, 2001:0db8::1
   Replacement: [IP_REDACTED]

6. name (requires NLP model)
   Pattern: Named entity recognition
   Examples: John Smith, Jane Doe
   Replacement: [NAME_REDACTED]

7. address (requires NLP model)
   Pattern: Address parsing
   Examples: 123 Main St, New York, NY 10001
   Replacement: [ADDRESS_REDACTED]
```

### Pattern Matching

**How detection works**:

- **Regex-based**: email, phone, ssn, credit-card, ip
- **NLP-based**: name, address (optional, requires model)
- **Context-aware**: Reduces false positives
- **JSON-safe**: Preserves log structure

### Detection Examples

**Before sanitization**:
```json
{
  "traceId": "abc123",
  "input": {
    "prompt": "Send invoice to john.doe@company.com or call 555-123-4567"
  },
  "metadata": {
    "user_email": "jane@example.org",
    "user_ip": "192.168.1.100"
  }
}
```

**After sanitization**:
```json
{
  "traceId": "abc123",
  "input": {
    "prompt": "Send invoice to [EMAIL_REDACTED] or call [PHONE_REDACTED]"
  },
  "metadata": {
    "user_email": "[EMAIL_REDACTED]",
    "user_ip": "[IP_REDACTED]"
  }
}
```

---

## Dry Run Mode

### Preview Changes

**See what will be removed WITHOUT modifying files**:

```bash
# Dry run: show detections but don't write output
crashlens pii-remove logs.jsonl --dry-run
```

**Example output**:
```
🔍 DRY RUN MODE - No files will be modified

Scanning: logs.jsonl
Lines processed: 1000

📊 PII Detection Summary:
  ✓ Emails found: 45
  ✓ Phone numbers found: 23
  ✓ SSNs found: 2
  ✓ Credit cards found: 1
  ✓ IP addresses found: 156

Sample detections:
  Line 10: Email "user@example.com" → [EMAIL_REDACTED]
  Line 15: Phone "+1-555-123-4567" → [PHONE_REDACTED]
  Line 42: IP "192.168.1.100" → [IP_REDACTED]

💡 To apply changes, remove --dry-run flag
```

### Dry Run Use Cases

1. **Audit**: Review PII exposure before sharing
2. **Testing**: Verify patterns match expected data
3. **Compliance**: Generate detection reports
4. **Validation**: Ensure no false positives

### Dry Run Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dry-run` | Flag | False | Preview without writing output |

---

## Selective Removal

### Remove Specific Types

**Choose which PII types to remove**:

```bash
# Remove only emails
crashlens pii-remove logs.jsonl --types email

# Remove emails and phones
crashlens pii-remove logs.jsonl --types email,phone

# Remove all except IPs
crashlens pii-remove logs.jsonl --types email,phone,ssn,credit-card,name,address
```

### Common Combinations

**Recommended type selections**:

```bash
# Minimal (most sensitive)
crashlens pii-remove logs.jsonl --types ssn,credit-card

# Standard (common PII)
crashlens pii-remove logs.jsonl --types email,phone,ssn

# Comprehensive (all types)
crashlens pii-remove logs.jsonl --types all  # or omit --types
```

### Use Case Examples

**Internal audit** (keep emails for tracking):
```bash
crashlens pii-remove logs.jsonl --types phone,ssn,credit-card,ip
```

**External sharing** (remove everything):
```bash
crashlens pii-remove logs.jsonl --types all
```

**Development testing** (keep IPs for debugging):
```bash
crashlens pii-remove logs.jsonl --types email,phone,ssn,credit-card
```

### Type Selection Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--types` | String | `all` | Comma-separated list or `all` |

---

## Verbose Logging

### Detailed Detection Reports

**Enable comprehensive logging**:

```bash
# Verbose mode: show all detections
crashlens pii-remove logs.jsonl --verbose
```

**Example output**:
```
🔍 Starting PII removal...

Configuration:
  Input: logs.jsonl (1.2 MB, 1000 lines)
  Output: logs-cleaned.jsonl
  Types: all (7 types enabled)

Processing line 1/1000...
  ✓ Detected 2 emails: user@example.com, admin@company.org
  ✓ Detected 1 phone: +1-555-123-4567

Processing line 2/1000...
  ✓ Detected 1 IP: 192.168.1.100

...

Processing line 1000/1000...

📊 Final Summary:
  Lines processed: 1000
  Lines modified: 234
  PII instances removed: 567
  
  Breakdown by type:
    - Emails: 45 instances
    - Phones: 23 instances
    - SSNs: 2 instances
    - Credit cards: 1 instance
    - IPs: 156 instances
    - Names: 89 instances (NLP)
    - Addresses: 12 instances (NLP)

✅ Output written to: logs-cleaned.jsonl (1.1 MB)
   Size reduction: 8.3% (100 KB)
```

### Verbose Use Cases

1. **Debugging**: Verify pattern matching
2. **Auditing**: Generate detailed reports
3. **Compliance**: Document PII removal
4. **Optimization**: Identify patterns to improve

### Logging Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--verbose` | Flag | False | Enable detailed logging |

---

## Batch Processing

### Process Multiple Files

**Handle multiple files at once**:

```bash
# Process all files in directory
for file in logs/*.jsonl; do
  crashlens pii-remove "$file" --types email,phone
done

# Parallel processing (PowerShell)
Get-ChildItem logs\*.jsonl | ForEach-Object -Parallel {
  crashlens pii-remove $_.FullName --types all
} -ThrottleLimit 4

# Parallel processing (bash)
find logs/ -name "*.jsonl" | parallel crashlens pii-remove {} --types all
```

### Organized Output

**Maintain directory structure**:

```bash
# Process with subdirectories
for file in logs/**/*.jsonl; do
  output="clean/${file#logs/}"
  mkdir -p "$(dirname "$output")"
  crashlens pii-remove "$file" --output "$output"
done
```

### Batch Script Example

```bash
#!/bin/bash
# batch-pii-removal.sh

INPUT_DIR="logs/"
OUTPUT_DIR="clean/"
TYPES="email,phone,ssn,credit-card"

mkdir -p "$OUTPUT_DIR"

for file in "$INPUT_DIR"*.jsonl; do
  filename=$(basename "$file")
  echo "Processing: $filename"
  
  crashlens pii-remove "$file" \
    --output "$OUTPUT_DIR$filename" \
    --types "$TYPES" \
    --verbose
  
  echo "✓ Completed: $filename"
done

echo "✅ Batch processing complete!"
```

---

## Integration with Guard

### Combined Workflow

**Sanitize before policy enforcement**:

```bash
# Step 1: Remove PII
crashlens pii-remove raw-logs.jsonl --output clean-logs.jsonl

# Step 2: Run guard on clean data
crashlens guard clean-logs.jsonl --fail-on-violations
```

### CI/CD Pipeline

```yaml
name: Sanitize and Guard

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install CrashLens
        run: pip install crashlens
      
      - name: Fetch logs
        run: crashlens fetch-langfuse --hours-back 24 --output raw-logs.jsonl
      
      - name: Remove PII
        run: |
          crashlens pii-remove raw-logs.jsonl \
            --output clean-logs.jsonl \
            --types all \
            --verbose
      
      - name: Run guard
        run: |
          crashlens guard clean-logs.jsonl \
            --fail-on-violations \
            --no-content \
            --summary-only
      
      - name: Upload sanitized logs
        uses: actions/upload-artifact@v4
        with:
          name: clean-logs
          path: clean-logs.jsonl
```

### Guard with Built-in PII Stripping

**Alternative: Use guard's --strip-pii flag**:

```bash
# Guard strips PII in-memory (doesn't modify source file)
crashlens guard logs.jsonl --strip-pii --no-content

# For permanent sanitization, use pii-remove first
crashlens pii-remove logs.jsonl --output clean.jsonl
crashlens guard clean.jsonl
```

---

## Complete Examples

### 1. Quick Sanitization

```bash
# Remove all PII types
crashlens pii-remove logs.jsonl

# Output: logs-cleaned.jsonl
```

### 2. Preview Before Removing

```bash
# Dry run with verbose output
crashlens pii-remove logs.jsonl --dry-run --verbose

# Review, then apply
crashlens pii-remove logs.jsonl --verbose
```

### 3. Selective Removal for Internal Use

```bash
# Keep emails, remove everything else
crashlens pii-remove logs.jsonl \
  --types phone,ssn,credit-card,ip,name,address \
  --output internal-logs.jsonl
```

### 4. External Sharing (Maximum Privacy)

```bash
# Remove all PII with detailed logging
crashlens pii-remove logs.jsonl \
  --types all \
  --output external-logs.jsonl \
  --verbose
```

### 5. Compliance Audit

```bash
# Dry run to generate detection report
crashlens pii-remove logs.jsonl \
  --dry-run \
  --verbose \
  > pii-audit-report.txt

# Review report before proceeding
```

### 6. Batch Processing with Custom Types

```bash
# Process all files, remove specific types
for file in logs/*.jsonl; do
  base=$(basename "$file" .jsonl)
  crashlens pii-remove "$file" \
    --types email,phone,ssn \
    --output "clean/${base}-sanitized.jsonl" \
    --verbose
done
```

### 7. CI/CD Integration

```bash
# Automated pipeline
crashlens pii-remove production-logs.jsonl \
  --types all \
  --output clean-logs.jsonl \
  --verbose

# Then analyze clean logs
crashlens scan clean-logs.jsonl --format json
```

---

## Best Practices

### 1. Always Use Dry Run First

```bash
# Preview detections
crashlens pii-remove logs.jsonl --dry-run --verbose

# Review output, then proceed
crashlens pii-remove logs.jsonl
```

### 2. Choose Appropriate Types

**By use case**:

- **Internal analysis**: Remove SSN, credit cards only
- **Team sharing**: Remove emails, phones, SSNs
- **External sharing**: Remove all types
- **Compliance audit**: Document with dry run

```bash
# Example: Internal use
crashlens pii-remove logs.jsonl --types ssn,credit-card
```

### 3. Verify Output

```bash
# Remove PII
crashlens pii-remove logs.jsonl --output clean.jsonl

# Verify no PII remains
grep -E "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" clean.jsonl
# Should return no matches
```

### 4. Keep Original Files

```bash
# Always keep original (don't overwrite)
crashlens pii-remove logs.jsonl --output logs-clean.jsonl

# Store originals securely
mv logs.jsonl secure-archive/
```

### 5. Document Removal

```bash
# Generate audit trail
crashlens pii-remove logs.jsonl --dry-run --verbose > pii-audit.txt

# Apply removal
crashlens pii-remove logs.jsonl --verbose >> pii-audit.txt

# Store audit log
mv pii-audit.txt compliance/$(date +%Y-%m-%d)-pii-removal.txt
```

### 6. Combine with Guard

```bash
# Sanitize first
crashlens pii-remove logs.jsonl --output clean.jsonl

# Then enforce policies on clean data
crashlens guard clean.jsonl --no-content --summary-only
```

### 7. Test Patterns

```bash
# Use --list-types to see patterns
crashlens pii-remove --list-types

# Test on sample data
echo '{"prompt":"Contact user@example.com"}' | \
  crashlens pii-remove --stdin --types email --verbose
```

---

## Performance Considerations

### Large Files

**Optimize for large log files**:

```bash
# Process in chunks
split -l 10000 large.jsonl chunk-

for chunk in chunk-*; do
  crashlens pii-remove "$chunk" --types email,phone &
done
wait

# Combine results
cat chunk-*-cleaned.jsonl > large-cleaned.jsonl
rm chunk-*
```

### Parallel Processing

```bash
# PowerShell parallel processing
Get-ChildItem logs\*.jsonl | ForEach-Object -Parallel {
  crashlens pii-remove $_.FullName --types all
} -ThrottleLimit 8

# Bash parallel processing
ls logs/*.jsonl | parallel -j 8 crashlens pii-remove {} --types all
```

---

## Troubleshooting

### Issue: False Positives

**Problem**: Legitimate data flagged as PII

**Solution**:
```bash
# Use selective types (avoid NLP-based)
crashlens pii-remove logs.jsonl --types email,phone,ssn,credit-card

# Review with dry run
crashlens pii-remove logs.jsonl --dry-run --verbose
```

### Issue: Missing Detections

**Problem**: PII not being caught

**Solution**:
```bash
# Check available patterns
crashlens pii-remove --list-types

# Enable verbose to see what's detected
crashlens pii-remove logs.jsonl --dry-run --verbose

# Consider custom patterns (future feature)
```

### Issue: Large Output Files

**Problem**: Cleaned files still too large

**Solution**:
```bash
# Combine with summary-only in guard
crashlens pii-remove logs.jsonl --output clean.jsonl
crashlens guard clean.jsonl --summary-only --no-content
```

### Issue: Performance Slow

**Problem**: Processing takes too long

**Solution**:
```bash
# Use selective types (fewer regex operations)
crashlens pii-remove logs.jsonl --types email,phone

# Process in parallel
# See "Parallel Processing" section above
```

---

## Command Reference

### All Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `INPUT` | Path | Required | Input JSONL file |
| `--output` | Path | `<input>-cleaned.jsonl` | Output file path |
| `--types` | String | `all` | PII types: `email`, `phone`, `ssn`, `credit-card`, `ip`, `name`, `address`, or `all` |
| `--dry-run` | Flag | False | Preview without writing |
| `--verbose` | Flag | False | Detailed logging |
| `--list-types` | Flag | False | Show available PII patterns |

### PII Type Codes

| Code | Description | Replacement |
|------|-------------|-------------|
| `email` | Email addresses | `[EMAIL_REDACTED]` |
| `phone` | Phone numbers | `[PHONE_REDACTED]` |
| `ssn` | Social Security Numbers | `[SSN_REDACTED]` |
| `credit-card` | Credit card numbers | `[CC_REDACTED]` |
| `ip` | IP addresses | `[IP_REDACTED]` |
| `name` | Person names | `[NAME_REDACTED]` |
| `address` | Physical addresses | `[ADDRESS_REDACTED]` |
| `all` | All types | (respective) |

---

## See Also

- **[Guard Command](./guard-command.md)**: Policy enforcement with --strip-pii
- **[Scan Command](./scan-command.md)**: Analysis with privacy options
- **[PII Removal Guide](../how-to-guides/pii-removal.md)**: Comprehensive guide
- **[CLI Reference](../CLI_COMMAND_REFERENCE.md)**: All commands

---

**Quick Start**: `crashlens pii-remove logs.jsonl --dry-run --verbose`
