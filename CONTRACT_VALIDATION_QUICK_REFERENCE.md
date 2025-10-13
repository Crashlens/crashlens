# 🛡️ Schema Contract Validation - Quick Reference

## Commands

### Validate a Log File
```bash
crashlens scan --contract-check logs.jsonl --log-format langfuse-v1
```

### View Schema Requirements
```bash
crashlens scan --contract-info --log-format langfuse-v1
```

### Validate Multiple Files

**Unix/Linux/macOS:**
```bash
find . -name "*.jsonl" -exec crashlens scan --contract-check {} --log-format langfuse-v1 \;
```

**Windows PowerShell:**
```powershell
Get-ChildItem -Recurse -Filter *.jsonl | ForEach-Object { 
    crashlens scan --contract-check $_.FullName --log-format langfuse-v1 
}
```

---

## Output Examples

### ✅ Success
```
🔍 Validating logs.jsonl against langfuse-v1 schema...

============================================================
📊 Validation Summary
============================================================
Total records: 1000
Valid records: 1000
Invalid records: 0

✅ VALIDATION PASSED
All records conform to langfuse-v1 schema
```
**Exit Code:** 0

### ❌ Failure
```
🔍 Validating logs.jsonl against langfuse-v1 schema...

❌ Line 15: Missing required field(s): traceId
❌ Line 42: Missing required field(s): traceId

============================================================
📊 Validation Summary
============================================================
Total records: 150
Valid records: 148
Invalid records: 2

❌ VALIDATION FAILED
Found 2 violation(s) in logs.jsonl
```
**Exit Code:** 1

---

## CI/CD Integration

### GitHub Actions

**Using Official Action:**
```yaml
- name: Validate Logs
  uses: Crashlens/crashlens@main
  with:
    log-paths: '**/*.jsonl'
    log-format: 'langfuse-v1'
    fail-on-violations: 'true'
```

**Manual Setup:**
```yaml
- name: Install & Validate
  run: |
    pip install crashlens
    find ./logs -name "*.jsonl" -exec \
      crashlens scan --contract-check {} --log-format langfuse-v1 \;
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

STAGED=$(git diff --cached --name-only | grep '\.jsonl$')

for file in $STAGED; do
    crashlens scan --contract-check "$file" --log-format langfuse-v1 || exit 1
done
```

---

## Schema Formats

| Format | Required Fields | Warn Fields |
|--------|----------------|-------------|
| `langfuse-v1` | `traceId` | `model`, `prompt_tokens`, `completion_tokens` |

### Langfuse V1 Contract

**Required (Must Have):**
- `traceId` - Unique trace identifier

**Warn (Should Have):**
- `model` - Model name (e.g., gpt-4)
- `prompt_tokens` - Input token count
- `completion_tokens` - Output token count

**All Known Fields (18 total):**
- `completion_tokens`, `cost`, `duration_sec`, `endTime`, `level`
- `metadata.fallback_attempted`, `metadata.fallback_reason`, `metadata.route`
- `metadata.source`, `metadata.team`, `model`, `name`, `prompt`
- `prompt_tokens`, `startTime`, `timestamp`, `traceId`, `userId`

---

## Use Cases

### 1. Block Bad Deployments
```yaml
# CI pipeline
- name: Validate Before Deploy
  run: |
    crashlens scan --contract-check prod-logs.jsonl --log-format langfuse-v1
    if [ $? -ne 0 ]; then
      echo "❌ Logs failed validation. Blocking deployment."
      exit 1
    fi
```

### 2. Local Development Check
```bash
# Before committing
$ crashlens scan --contract-check my-logs.jsonl --log-format langfuse-v1
✅ VALIDATION PASSED
```

### 3. Batch Quality Check
```bash
# Validate all logs in directory
$ for file in logs/*.jsonl; do
    echo "Checking: $file"
    crashlens scan --contract-check "$file" --log-format langfuse-v1
  done
```

---

## Exit Codes

| Code | Meaning | Use Case |
|------|---------|----------|
| `0` | All records valid | Allow deployment |
| `1` | Violations found | Block deployment |

---

## Troubleshooting

### Issue: "No such option: --contract-check"

**Cause:** Using installed version, not local code

**Solution:**
```bash
# Use local code
python -m crashlens scan --contract-check logs.jsonl --log-format langfuse-v1

# Or reinstall
pip install --upgrade crashlens
```

### Issue: "Schema version not found"

**Solution:** Check available versions:
```bash
crashlens scan --contract-info --log-format langfuse-v1
```

### Issue: Too many violations

**Solution:** View requirements first:
```bash
crashlens scan --contract-info --log-format langfuse-v1
```

---

## Quick Tips

✅ **Always use `--log-format`** - Specifies which schema to validate against  
✅ **Check exit codes** - Use `$?` (bash) or `$LASTEXITCODE` (PowerShell)  
✅ **View requirements first** - Use `--contract-info` before validating  
✅ **Automate in CI** - Add to GitHub Actions, GitLab CI, or Jenkins  
✅ **Pre-commit hooks** - Catch issues before pushing  

---

## Related Documentation

- **Full Guide:** [NEW_FEATURES.md](NEW_FEATURES.md) - Complete documentation
- **Implementation:** [CONTRACT_VALIDATION_SUMMARY.md](CONTRACT_VALIDATION_SUMMARY.md) - Technical details
- **General Docs:** [README.md](README.md) - Main documentation

---

**Version:** 2.9.12+  
**Last Updated:** October 11, 2025
