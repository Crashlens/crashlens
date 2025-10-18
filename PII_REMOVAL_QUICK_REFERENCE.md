# 🧹 CrashLens PII Removal - Quick Reference Card

## Command Format
```bash
crashlens pii-remove [INPUT_FILE] [OPTIONS]
```

## Common Commands

### 📋 List Available PII Types
```bash
crashlens pii-remove --list-types
```

### 🔍 Analyze Without Modification (Dry Run)
```bash
crashlens pii-remove logs.jsonl --dry-run
crashlens pii-remove logs.jsonl --dry-run --verbose  # with details
```

### 🧹 Remove All PII
```bash
crashlens pii-remove logs.jsonl
crashlens pii-remove logs.jsonl --verbose  # with statistics
```

### 🎯 Remove Specific PII Types
```bash
crashlens pii-remove logs.jsonl --types email
crashlens pii-remove logs.jsonl --types email --types phone_us
```

### 📁 Custom Output Path
```bash
crashlens pii-remove logs.jsonl --output clean/sanitized.jsonl
```

## All Options

| Option | Short | Description |
|--------|-------|-------------|
| `--output PATH` | `-o` | Output file path |
| `--dry-run` | | Analyze only, don't modify |
| `--types TYPE` | `-t` | Specific PII type (repeatable) |
| `--list-types` | | Show available PII types |
| `--verbose` | `-v` | Show detailed statistics |
| `--help` | | Show help message |

## PII Types (8 Total)

| Type | Example | Replacement Token |
|------|---------|-------------------|
| `email` | user@example.com | `[EMAIL_REDACTED]` |
| `phone_us` | (123) 456-7890 | `[PHONE_REDACTED]` |
| `ssn` | 123-45-6789 | `[SSN_REDACTED]` |
| `credit_card` | 1234-5678-9012-3456 | `[CREDIT_CARD_REDACTED]` |
| `ip_address` | 192.168.1.1 | `[IP_REDACTED]` |
| `api_key` | abc123...xyz (32+ chars) | `[API_KEY_REDACTED]` |
| `street_address` | 123 Main Street | `[ADDRESS_REDACTED]` |
| `date` | 01/15/2024 | `[DATE_REDACTED]` |

## Output Example

### Before
```json
{"user": "john@example.com", "phone": "123-456-7890", "count": 42}
```

### After
```json
{"user": "[EMAIL_REDACTED]", "phone": "[PHONE_REDACTED]", "count": 42}
```

## Common Workflows

### 1️⃣ Cloud Upload Prep
```bash
crashlens pii-remove prod.jsonl --output upload.jsonl
# Upload upload.jsonl to Langfuse/Helicone
```

### 2️⃣ Compliance Check
```bash
crashlens pii-remove logs.jsonl --types email --types ssn --types phone_us
```

### 3️⃣ Safe Sharing
```bash
crashlens pii-remove debug.jsonl --output shareable-debug.jsonl
```

### 4️⃣ Full Analysis Pipeline
```bash
# 1. Remove PII
crashlens pii-remove logs.jsonl --output clean.jsonl

# 2. Scan for issues
crashlens scan clean.jsonl --format markdown

# 3. Policy check
crashlens policy-check clean.jsonl --policy-template all
```

## Tips & Tricks

💡 **Always dry-run first:** `--dry-run` shows what will be removed  
💡 **Use verbose mode:** `--verbose` shows detailed statistics  
💡 **Selective removal:** Use `--types` for specific PII only  
💡 **Check output:** Verify sanitized file before uploading  
💡 **Preserve originals:** Keep original logs as backup  

## Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| `Input file not found` | File doesn't exist | Check path |
| `Invalid PII types` | Unknown type specified | Run `--list-types` |
| `No write permission` | Can't create output | Check folder permissions |
| `Invalid JSON line` | Malformed JSONL | Check file format |

## Performance

- ⚡ **Speed:** Thousands of records/second
- 💾 **Memory:** Streaming (low memory usage)
- 📏 **File Size:** Handles multi-GB files

## Help & Documentation

- **Quick Help:** `crashlens pii-remove --help`
- **Full Guide:** `docs/PII_REMOVAL_GUIDE.md`
- **Examples:** `PII_REMOVAL_DEMO_OUTPUT.md`
- **Tests:** `pytest tests/test_pii_removal.py -v`

---

**Print this card for quick reference! 🖨️**
