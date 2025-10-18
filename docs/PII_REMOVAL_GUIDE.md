# CrashLens PII Removal - Quick Reference

## Overview
The `crashlens pii-remove` command sanitizes JSONL log files by detecting and removing personally identifiable information (PII), making logs safe for cloud storage, sharing, or compliance requirements (GDPR, HIPAA, etc.).

## Basic Usage

### Remove all PII types
```bash
crashlens pii-remove logs/production.jsonl
```
Creates: `logs/production_sanitized.jsonl`

### Dry run (analyze without modifying)
```bash
crashlens pii-remove logs/production.jsonl --dry-run
```

### Specify custom output location
```bash
crashlens pii-remove logs/app.jsonl --output clean/app_safe.jsonl
```

### Remove specific PII types only
```bash
crashlens pii-remove logs/app.jsonl --types email --types phone_us
```

## Supported PII Types

| Type | Description | Example |
|------|-------------|---------|
| `email` | Email addresses | user@example.com |
| `phone_us` | US phone numbers | (123) 456-7890, 123-456-7890 |
| `ssn` | Social Security Numbers | 123-45-6789 |
| `credit_card` | Credit card numbers | 1234-5678-9012-3456 |
| `ip_address` | IPv4 addresses | 192.168.1.1 |
| `api_key` | API keys/tokens (32+ chars) | abc123...xyz789 |
| `street_address` | Street addresses | 123 Main Street |
| `date` | Date formats | 01/15/2024, 2024-01-15 |

## Command Options

```
crashlens pii-remove [OPTIONS] INPUT_FILE

Options:
  -o, --output PATH       Output file path (default: <input>_sanitized.jsonl)
  --dry-run              Analyze PII without creating output file
  -t, --types TEXT       Specific PII types to remove (repeatable)
  --list-types           List available PII types and exit
  -v, --verbose          Show detailed statistics
  --help                 Show help message
```

## Examples

### 1. List available PII types
```bash
crashlens pii-remove --list-types
```

### 2. Analyze what PII exists (dry run)
```bash
crashlens pii-remove sample-logs/pii-test.jsonl --dry-run --verbose
```

Output:
```
🔍 Analyzing PII in: sample-logs/pii-test.jsonl

✅ Processing complete!

📊 Summary:
  Records processed: 5
  Total PII found: 12

  PII by type:
    • api_key: 1
    • credit_card: 1
    • date: 1
    • email: 3
    • ip_address: 1
    • phone_us: 2
    • ssn: 1
    • street_address: 1

💡 This was a dry run. No files were modified.
   Remove --dry-run flag to create sanitized output.
```

### 3. Remove only emails and phones
```bash
crashlens pii-remove logs/app.jsonl \
  --types email \
  --types phone_us \
  --output logs/sanitized/app.jsonl
```

### 4. Process with verbose output
```bash
crashlens pii-remove logs/production.jsonl --verbose
```

## How It Works

1. **Pattern Matching**: Uses optimized regex patterns to detect PII
2. **Recursive Processing**: Handles nested JSON structures and arrays
3. **Redaction Tokens**: Replaces PII with clear markers like `[EMAIL_REDACTED]`
4. **Type Preservation**: Maintains all non-string values (numbers, booleans, nulls)
5. **Statistics**: Tracks and reports what was found/removed

## Input/Output Format

### Input (original log):
```json
{"user": "john@example.com", "phone": "123-456-7890", "count": 42}
```

### Output (sanitized):
```json
{"user": "[EMAIL_REDACTED]", "phone": "[PHONE_REDACTED]", "count": 42}
```

## Use Cases

### ✅ Cloud Dashboard Upload
Remove PII before uploading logs to Langfuse, Helicone, or other cloud platforms:
```bash
crashlens pii-remove local-logs/production.jsonl --output upload/safe-logs.jsonl
```

### ✅ Compliance (GDPR/HIPAA)
Ensure logs meet regulatory requirements:
```bash
crashlens pii-remove app-logs/*.jsonl --types email --types ssn --types phone_us
```

### ✅ Log Sharing
Safely share logs with external teams or support:
```bash
crashlens pii-remove debug.jsonl --output shareable/debug-safe.jsonl --verbose
```

### ✅ Testing & Development
Clean production logs for use in dev/test environments:
```bash
crashlens pii-remove prod-logs.jsonl --output dev/test-data.jsonl
```

## Integration with CrashLens Workflow

### 1. Sanitize first, then analyze
```bash
# Step 1: Remove PII
crashlens pii-remove logs/raw.jsonl --output logs/clean.jsonl

# Step 2: Run policy checks on clean logs
crashlens policy-check logs/clean.jsonl --policy-file my-policy.yaml
```

### 2. Chain with scan command
```bash
# Sanitize and scan in one workflow
crashlens pii-remove logs/app.jsonl --output logs/clean.jsonl && \
crashlens scan logs/clean.jsonl --format markdown
```

## Error Handling

- **Invalid JSON lines**: Skipped with warning, processing continues
- **Missing input file**: Clear error message with exit code 1
- **Invalid PII types**: Lists valid types and exits
- **Permission errors**: Reports write permission issues

## Performance

- **Pattern Compilation**: Regex patterns compiled once for efficiency
- **Streaming Processing**: Processes files line-by-line (low memory usage)
- **Large Files**: Handles multi-GB JSONL files without issues

## Testing

Run the included test suite:
```bash
pytest tests/test_pii_removal.py -v
```

## Future Enhancements

Planned features for future releases:
- [ ] International phone number formats
- [ ] Custom regex pattern definitions
- [ ] Whitelist/allowlist support
- [ ] Batch processing of multiple files
- [ ] Progress bar for large files
- [ ] JSON Schema validation
- [ ] Encryption option for redacted data

## Support

For issues or feature requests:
- GitHub Issues: https://github.com/Crashlens/crashlens/issues
- Documentation: See main README.md

---

**Note**: Always test on sample data first before processing production logs!
