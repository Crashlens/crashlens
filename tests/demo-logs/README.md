# 🔍 Schema Contract Validation Workflow

This GitHub Actions workflow automatically validates Langfuse log files against schema contracts whenever `.jsonl` or `.py` files are modified.

## 🎯 Overview

The workflow ensures that all Langfuse log entries conform to the required schema by checking for:
- **Required fields**: `traceId`, `startTime`, `input.model`
- **Field types**: Validates that fields have correct data types
- **Nested structures**: Handles nested objects like `input.model` and `usage.prompt_tokens`

## 🚀 Triggers

### Automatic Triggers
- **Push** to any branch when `.jsonl` or `.py` files change
- **Pull Request** when `.jsonl` or `.py` files change

### Manual Trigger
- **Workflow Dispatch** with optional parameters:
  - `log_file`: Custom log file path (default: `tests/demo-logs/sample-violating.jsonl`)
  - `log_format`: Schema version (`langfuse-v1` or `langfuse-v2`)

## 📁 Test Files

### `tests/demo-logs/sample-violating.jsonl`
Contains intentionally invalid log entries to test contract validation:
- Missing `traceId` fields
- Missing `startTime` fields  
- Missing `input.model` fields
- Incorrect field types (number instead of string)

### `tests/demo-logs/sample-valid.jsonl`
Contains valid log entries that pass all schema requirements.

## 🔧 Local Testing

Test the contract validation locally before pushing:

```bash
# Test with violating file (should fail)
crashlens scan --contract-check tests/demo-logs/sample-violating.jsonl --log-format langfuse-v1

# Test with valid file (should pass)
crashlens scan --contract-check tests/demo-logs/sample-valid.jsonl --log-format langfuse-v1

# Show schema requirements
crashlens scan --contract-info --log-format langfuse-v1
```

## 📊 Workflow Results

### ✅ Success Output
```
✅ SUCCESS: All schema contracts validated!
🎉 Log file conforms to langfuse-v1 schema requirements
📊 No contract violations detected
```

### ❌ Failure Output
```
❌ FAILURE: Schema contract violations detected!
🚨 Log file does not conform to langfuse-v1 schema
💡 Check the detailed error messages above

Contract check failed:
  - Line 2: Missing required field: traceId
  - Line 2: Missing required field: input.model
  - Line 4: Missing required field: startTime
Found 3 violation(s) across 7 log entries.
```

## 🛠️ Manual Workflow Dispatch

1. Go to **Actions** → **Schema Contract Check**
2. Click **Run workflow**
3. Optionally specify:
   - **Log file path**: Path to your test file
   - **Log format**: `langfuse-v1` or `langfuse-v2`
4. Click **Run workflow**

## 🔍 Schema Requirements

### Langfuse v1 Schema
**Required Fields:**
- `traceId` (string): Unique trace identifier
- `startTime` (string): ISO timestamp 
- `input.model` (string): Model name nested in input object

**Optional Fields:**
- `endTime` (string): End timestamp
- `cost` (number): API call cost
- `usage.prompt_tokens` (integer): Input token count
- `usage.completion_tokens` (integer): Output token count
- `output` (string): Generated response

### Langfuse v2 Schema
**Additional Requirements:**
- `userId` (string): User identifier

## 🚨 Troubleshooting

### Common Issues

1. **Missing Required Fields**
   ```bash
   # Fix: Ensure all log entries have required fields
   {
     "traceId": "trace_123",
     "startTime": "2025-08-03T10:30:00.000000Z", 
     "input": {
       "model": "gpt-4"
     }
   }
   ```

2. **Incorrect Field Types**
   ```bash
   # ❌ Wrong: startTime as number
   "startTime": 1691234567
   
   # ✅ Correct: startTime as ISO string
   "startTime": "2025-08-03T10:30:00.000000Z"
   ```

3. **Missing Nested Fields**
   ```bash
   # ❌ Wrong: model at top level
   {
     "traceId": "trace_123",
     "model": "gpt-4"
   }
   
   # ✅ Correct: model nested in input
   {
     "traceId": "trace_123", 
     "input": {
       "model": "gpt-4"
     }
   }
   ```

### Debug Commands

```bash
# Check contract requirements
crashlens scan --contract-info --log-format langfuse-v1

# Validate specific file
crashlens scan --contract-check your-file.jsonl --log-format langfuse-v1

# Test with different schema versions
crashlens scan --contract-check your-file.jsonl --log-format langfuse-v2
```

## 🎉 Benefits

- **Early Detection**: Catch schema violations before they reach production
- **Automated Validation**: No manual checking required
- **Clear Feedback**: Detailed error messages with line numbers
- **CI/CD Integration**: Proper exit codes for build pipelines
- **Multi-Schema Support**: Works with different Langfuse schema versions
- **Flexible Testing**: Manual triggers for custom validation

This workflow ensures your Langfuse logs maintain consistent schema compliance across all changes! 🚀
