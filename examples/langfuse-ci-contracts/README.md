# Langfuse CI Contracts Example

This example shows how to set up **automated schema validation** for Langfuse logs in your CI/CD pipeline using CrashLens.

## 🎯 What This Does

- **Blocks bad logs** from being merged into your main branch
- **Enforces schema contracts** for consistent data quality  
- **Provides clear feedback** when logs don't meet requirements
- **Runs automatically** on every push and pull request

## 🚀 Quick Setup (2 minutes)

### 1. Add the workflow file

Create `.github/workflows/langfuse-check.yml`:

```yaml
name: Langfuse Log Validation

on:
  push:
    paths: ["**/*.jsonl"]
  pull_request:
    paths: ["**/*.jsonl"]

jobs:
  validate-logs:
    name: Validate Langfuse Logs
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Validate log schema contracts
        uses: crashlens/contract-check@v1
        with:
          log-paths: "**/*.jsonl"
          log-format: "langfuse-v1"
          fail-on-violations: true
```

### 2. Test with sample logs

Create some test log files to see the validation in action:

**✅ `logs/valid-trace.jsonl`** (This will pass):
```json
{"traceId": "trace_abc123", "startTime": "2024-01-01T10:00:00Z", "input": {"model": "gpt-4"}, "cost": 0.01}
{"traceId": "trace_abc123", "startTime": "2024-01-01T10:00:05Z", "input": {"model": "gpt-4"}, "usage": {"prompt_tokens": 150, "completion_tokens": 50}}
```

**❌ `logs/invalid-trace.jsonl`** (This will fail):
```json
{"startTime": "2024-01-01T10:00:00Z", "input": {"model": "gpt-4"}}
{"traceId": "trace_456", "startTime": 1704110400, "input": {"model": "gpt-4"}}
{"traceId": "trace_789", "startTime": "2024-01-01T10:00:00Z"}
```

### 3. Push and watch it work

```bash
git add .github/workflows/langfuse-check.yml logs/
git commit -m "Add Langfuse log validation"
git push
```

The workflow will run and show you exactly what's wrong with invalid logs! 🎉

## 📊 Example Output

### ✅ When logs are valid:
```
✅ logs/valid-trace.jsonl: PASSED
Contract check passed. All required fields present.
```

### ❌ When logs have violations:
```
❌ logs/invalid-trace.jsonl: FAILED
Contract check failed:
  - Line 1: Missing required field: traceId
  - Line 2: Field 'startTime' has incorrect type. Expected str, got int
  - Line 3: Missing required field: input.model
Found 3 violation(s) across 3 log entries.
```

## 🔧 Advanced Configuration

### Validate Specific Directories Only

```yaml
- uses: crashlens/contract-check@v1
  with:
    log-paths: "production-logs/**/*.jsonl"
    log-format: "langfuse-v1"
```

### Multiple Schema Versions

```yaml
strategy:
  matrix:
    config:
      - { path: "v1-logs/**/*.jsonl", format: "langfuse-v1" }
      - { path: "v2-logs/**/*.jsonl", format: "langfuse-v2" }

steps:
  - uses: crashlens/contract-check@v1
    with:
      log-paths: ${{ matrix.config.path }}
      log-format: ${{ matrix.config.format }}
```

### Warning Mode (Don't Fail CI)

```yaml
- uses: crashlens/contract-check@v1
  with:
    fail-on-violations: false
  id: validation

- name: Post warning if violations found
  if: steps.validation.outputs.violations-found == 'true'
  run: |
    echo "⚠️ Warning: Found ${{ steps.validation.outputs.violations-count }} schema violations"
```

## 🧪 Testing Locally

Before pushing, test your logs locally:

```bash
# Install CrashLens
pip install crashlens

# Check a specific file
crashlens scan --contract-check logs/your-file.jsonl --log-format langfuse-v1

# View schema requirements
crashlens scan --contract-info --log-format langfuse-v1

# Validate all jsonl files
find . -name "*.jsonl" -exec crashlens scan --contract-check {} --log-format langfuse-v1 \;
```

## 📋 Schema Reference

### Langfuse V1 Requirements

**Required Fields:**
- `traceId` (string): Unique identifier for the trace
- `startTime` (string): ISO timestamp when the trace started  
- `input.model` (string): Model name used for the request

**Optional Fields:**
- `endTime` (string): ISO timestamp when the trace ended
- `cost` (number): Cost of the request in dollars
- `usage.prompt_tokens` (integer): Number of prompt tokens
- `usage.completion_tokens` (integer): Number of completion tokens
- `output` (any): Response content

### Valid Examples

```json
// Minimal valid log
{"traceId": "abc123", "startTime": "2024-01-01T10:00:00Z", "input": {"model": "gpt-4"}}

// Full log with all fields
{
  "traceId": "abc123",
  "startTime": "2024-01-01T10:00:00Z", 
  "endTime": "2024-01-01T10:00:05Z",
  "input": {"model": "gpt-4", "prompt": "Hello world"},
  "output": "Hi there!",
  "cost": 0.002,
  "usage": {"prompt_tokens": 10, "completion_tokens": 5}
}
```

### Common Violations

```json
// ❌ Missing traceId
{"startTime": "2024-01-01T10:00:00Z", "input": {"model": "gpt-4"}}

// ❌ Missing input.model  
{"traceId": "abc123", "startTime": "2024-01-01T10:00:00Z", "input": {}}

// ❌ Wrong type (number instead of string)
{"traceId": "abc123", "startTime": 1704110400, "input": {"model": "gpt-4"}}

// ❌ Missing required nested field
{"traceId": "abc123", "startTime": "2024-01-01T10:00:00Z"}
```

## 🎯 Benefits

### For Developers
- **Catch errors early**: Find log issues before they reach production
- **Clear feedback**: Know exactly what's wrong and how to fix it
- **Consistent quality**: Enforce team-wide log standards

### For Teams  
- **Data reliability**: Ensure analytics and monitoring work correctly
- **Compliance**: Meet data governance requirements automatically
- **Debugging**: Better log quality = easier troubleshooting

### For Production
- **Prevent outages**: Block malformed logs that could break pipelines
- **Cost control**: Ensure cost tracking fields are present and accurate
- **Monitoring**: Reliable logs = reliable observability

## 🔗 Next Steps

1. **Set up the workflow** in your repository
2. **Add test log files** to verify it works
3. **Customize validation** rules for your needs
4. **Share with your team** and enforce log quality

## 🆘 Troubleshooting

### No files found
- Check your `log-paths` pattern matches your file structure
- Use `find . -name "*.jsonl"` to see what files exist

### False violations
- Run locally with `-v` flag for detailed output: `crashlens scan --contract-check file.jsonl -v`
- Check field types (strings vs numbers)
- Verify nested field paths like `input.model`

### Workflow not running
- Ensure the workflow file is in `.github/workflows/`
- Check that your file changes include `.jsonl` files
- Look at the Actions tab in GitHub for error details

---

**Questions?** [Open an issue](https://github.com/crashlens/crashlens/issues) or check the [full documentation](https://github.com/crashlens/crashlens).

**Want to contribute?** We'd love your help! See our [contributing guide](https://github.com/crashlens/crashlens/blob/main/CONTRIBUTING.md).
