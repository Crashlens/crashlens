# 🔧 Troubleshooting Guide

This guide helps you resolve common issues with Langfuse schema validation.

## 🚨 Common Error Messages

### ❌ "Error: Log file not found"

**Full Error:**
```
❌ Error: Log file not found at path: logs/langfuse-latest.jsonl
```

**Causes:**
- Log file doesn't exist at specified path
- Incorrect file path configuration
- File was not committed to repository

**Solutions:**

1. **Check file existence:**
   ```bash
   ls -la logs/langfuse-latest.jsonl
   ```

2. **Verify file path in workflow:**
   ```yaml
   env:
     LOG_PATH: 'logs/langfuse-latest.jsonl'  # Check this path
   ```

3. **Ensure file is committed:**
   ```bash
   git add logs/langfuse-latest.jsonl
   git commit -m "Add log file"
   git push
   ```

### ❌ "Schema contract violations detected"

**Full Error:**
```
❌ FAILURE: Schema validation failed for langfuse-v1
🚨 Contract violations detected in Langfuse logs
```

**Causes:**
- Missing required fields (usually `traceId`)
- Incorrect field data types
- Malformed JSON structure

**Solutions:**

1. **Check for required fields:**
   ```bash
   # Verify traceId exists in all entries
   jq '.[] | select(.traceId == null)' logs/langfuse-latest.jsonl
   ```

2. **Validate field types:**
   ```bash
   # Check traceId is string
   jq '.[] | .traceId | type' logs/langfuse-latest.jsonl | sort | uniq
   ```

3. **Fix common issues:**
   ```json
   // ❌ Bad: Missing traceId
   {
     "model": "gpt-4",
     "cost": 0.05
   }
   
   // ✅ Good: Has required traceId
   {
     "traceId": "trace_12345",
     "model": "gpt-4",
     "cost": 0.05
   }
   ```

### ❌ "Unsupported log format"

**Full Error:**
```
❌ Error: Unsupported log format: langfuse-v3
```

**Causes:**
- Using a schema version that doesn't exist yet
- Typo in schema version name
- CrashLens version doesn't support the schema

**Solutions:**

1. **Use supported versions:**
   ```bash
   # Try with v1 (always supported)
   crashlens scan logs/langfuse-latest.jsonl --log-format langfuse-v1
   ```

2. **Check available versions:**
   ```python
   from crashlens.parsers.langfuse import LangfuseParser
   parser = LangfuseParser()
   print(parser.get_available_schema_versions())
   ```

3. **Update CrashLens:**
   ```bash
   pip install --upgrade crashlens
   ```

### ❌ "Invalid JSON format"

**Full Error:**
```
json.decoder.JSONDecodeError: Expecting ',' delimiter: line 15 column 5
```

**Causes:**
- Malformed JSON syntax
- Missing commas or quotes
- Invalid escape characters

**Solutions:**

1. **Validate JSON syntax:**
   ```bash
   # Check entire file
   python -m json.tool logs/langfuse-latest.jsonl
   
   # Check specific lines
   sed -n '15p' logs/langfuse-latest.jsonl | python -m json.tool
   ```

2. **Common JSON fixes:**
   ```json
   // ❌ Bad: Missing quotes
   {
     traceId: "trace_123",
     model: gpt-4
   }
   
   // ✅ Good: Proper quotes
   {
     "traceId": "trace_123",
     "model": "gpt-4"
   }
   ```

3. **Use JSONL validator:**
   ```bash
   # Validate each line separately
   while IFS= read -r line; do
     echo "$line" | python -m json.tool > /dev/null || echo "Invalid JSON: $line"
   done < logs/langfuse-latest.jsonl
   ```

## 🔍 Debugging Techniques

### Local Debugging

1. **Test locally before pushing:**
   ```bash
   # Install CrashLens locally
   pip install crashlens
   
   # Test with verbose output
   crashlens scan logs/langfuse-latest.jsonl --log-format langfuse-v1 --verbose
   ```

2. **Check log file structure:**
   ```bash
   # Show first few entries
   head -n 3 logs/langfuse-latest.jsonl
   
   # Count total entries
   wc -l logs/langfuse-latest.jsonl
   
   # Check file size
   du -h logs/langfuse-latest.jsonl
   ```

3. **Validate field presence:**
   ```bash
   # Check all unique fields
   jq -r '.[] | keys[]' logs/langfuse-latest.jsonl | sort | uniq
   
   # Count entries with traceId
   jq '[.[] | select(.traceId != null)] | length' logs/langfuse-latest.jsonl
   ```

### GitHub Actions Debugging

1. **Enable debug logging:**
   ```yaml
   env:
     ACTIONS_STEP_DEBUG: true
   ```

2. **Add debug steps:**
   ```yaml
   - name: Debug Log File
     run: |
       echo "File exists: $(test -f $LOG_PATH && echo 'YES' || echo 'NO')"
       echo "File size: $(du -h $LOG_PATH 2>/dev/null || echo 'N/A')"
       echo "Line count: $(wc -l < $LOG_PATH 2>/dev/null || echo 'N/A')"
       echo "First line: $(head -n 1 $LOG_PATH 2>/dev/null || echo 'N/A')"
   ```

3. **Test JSON parsing:**
   ```yaml
   - name: Validate JSON
     run: |
       if python -m json.tool "$LOG_PATH" > /dev/null 2>&1; then
         echo "✅ Valid JSON structure"
       else
         echo "❌ Invalid JSON structure"
         python -m json.tool "$LOG_PATH"
       fi
   ```

## 🛠️ Fix Generators

### Missing traceId Fix

```bash
#!/bin/bash
# fix-missing-traceid.sh

# Add traceId to entries that don't have one
jq 'if .traceId == null then .traceId = ("trace_" + now | tostring) else . end' \
  logs/langfuse-latest.jsonl > logs/fixed.jsonl

mv logs/fixed.jsonl logs/langfuse-latest.jsonl
```

### Type Conversion Fix

```python
#!/usr/bin/env python3
# fix-field-types.py

import json
import sys

def fix_types(data):
    """Fix common type issues"""
    if isinstance(data, dict):
        # Ensure traceId is string
        if 'traceId' in data and not isinstance(data['traceId'], str):
            data['traceId'] = str(data['traceId'])
        
        # Ensure token counts are integers
        for field in ['prompt_tokens', 'completion_tokens']:
            if field in data:
                try:
                    data[field] = int(data[field])
                except (ValueError, TypeError):
                    data[field] = 0
        
        # Ensure cost is float
        if 'cost' in data:
            try:
                data['cost'] = float(data['cost'])
            except (ValueError, TypeError):
                data['cost'] = 0.0
    
    return data

# Read, fix, and write back
with open('logs/langfuse-latest.jsonl', 'r') as f:
    lines = f.readlines()

with open('logs/langfuse-latest.jsonl', 'w') as f:
    for line in lines:
        try:
            data = json.loads(line)
            fixed_data = fix_types(data)
            f.write(json.dumps(fixed_data) + '\n')
        except json.JSONDecodeError as e:
            print(f"Skipping invalid line: {line.strip()}", file=sys.stderr)
```

### JSON Structure Validator

```python
#!/usr/bin/env python3
# validate-structure.py

import json
import sys

def validate_entry(entry, line_num):
    """Validate a single log entry"""
    errors = []
    
    # Check required fields
    if 'traceId' not in entry:
        errors.append(f"Line {line_num}: Missing required field 'traceId'")
    elif not isinstance(entry['traceId'], str):
        errors.append(f"Line {line_num}: traceId must be string, got {type(entry['traceId'])}")
    
    # Check optional field types
    type_checks = {
        'model': str,
        'prompt_tokens': int,
        'completion_tokens': int,
        'cost': (int, float),
        'userId': str,
        'input': str,
        'output': str
    }
    
    for field, expected_type in type_checks.items():
        if field in entry and not isinstance(entry[field], expected_type):
            errors.append(f"Line {line_num}: {field} should be {expected_type}, got {type(entry[field])}")
    
    return errors

def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else 'logs/langfuse-latest.jsonl'
    all_errors = []
    
    try:
        with open(filename, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    errors = validate_entry(entry, line_num)
                    all_errors.extend(errors)
                except json.JSONDecodeError as e:
                    all_errors.append(f"Line {line_num}: Invalid JSON - {e}")
    
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        sys.exit(1)
    
    if all_errors:
        print("❌ Validation errors found:")
        for error in all_errors:
            print(f"  {error}")
        sys.exit(1)
    else:
        print("✅ All entries valid!")

if __name__ == "__main__":
    main()
```

## 📋 Quick Diagnostics Checklist

### Before Opening an Issue

- [ ] File exists at correct path
- [ ] JSON syntax is valid
- [ ] Required fields are present
- [ ] Field types are correct
- [ ] File is not empty
- [ ] CrashLens is latest version
- [ ] Schema version is supported

### Diagnostic Commands

```bash
# 1. Check file existence and basic info
ls -la logs/langfuse-latest.jsonl

# 2. Validate JSON structure
python -m json.tool logs/langfuse-latest.jsonl > /dev/null && echo "Valid JSON" || echo "Invalid JSON"

# 3. Check required fields
jq '.[] | select(.traceId == null)' logs/langfuse-latest.jsonl

# 4. Test local validation
crashlens scan logs/langfuse-latest.jsonl --log-format langfuse-v1 --verbose

# 5. Check CrashLens version
pip show crashlens | grep Version
```

## 🆘 Getting Help

### Support Channels

1. **GitHub Issues**: [Create an issue](https://github.com/your-repo/issues/new) with:
   - Error message (full output)
   - Sample log data (anonymized)
   - Steps to reproduce
   - Environment details

2. **Discussion Forums**: Check existing discussions for similar issues

3. **Documentation**: Review the [Usage Guide](USAGE.md) and [Schema Versioning](../SCHEMA_VERSIONING.md)

### Issue Template

```markdown
## 🚨 Schema Validation Issue

**Error Message:**
```
[Paste full error message here]
```

**Environment:**
- CrashLens version: [e.g., 1.0.0]
- Python version: [e.g., 3.11]
- OS: [e.g., Ubuntu 22.04]
- Schema version: [e.g., langfuse-v1]

**Sample Log Data:**
```json
[Paste anonymized sample that reproduces the issue]
```

**Steps to Reproduce:**
1. [Step 1]
2. [Step 2]
3. [Error occurs]

**Expected Behavior:**
[What should happen]

**Additional Context:**
[Any other relevant information]
```

## 🔄 Prevention Tips

### Best Practices

1. **Test locally first:**
   ```bash
   # Always test before pushing
   crashlens scan logs/langfuse-latest.jsonl --log-format langfuse-v1
   ```

2. **Use consistent field names:**
   - Stick to the schema specification
   - Avoid changing field names between logs
   - Use consistent data types

3. **Validate before committing:**
   ```bash
   # Add pre-commit hook
   echo 'crashlens scan logs/langfuse-latest.jsonl --log-format langfuse-v1' > .git/hooks/pre-commit
   chmod +x .git/hooks/pre-commit
   ```

4. **Monitor schema changes:**
   - Subscribe to Langfuse release notes
   - Test new versions in staging first
   - Update contracts proactively

### Automated Fixes

Set up automated data cleaning:

```yaml
# .github/workflows/data-cleanup.yml
name: Data Cleanup
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Fix Common Issues
        run: |
          python scripts/fix-field-types.py
          python scripts/validate-structure.py
      - name: Commit fixes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add logs/
          git diff --staged --quiet || git commit -m "Auto-fix log data issues"
          git push
```

This troubleshooting guide should help you resolve most common issues with Langfuse schema validation. If you continue to experience problems, please open an issue with detailed information.
