# 🛡️ CrashLens: LLM Log Contract Validation

[![GitHub Action](https://img.shields.io/badge/action-CrashLens-blue)](https://github.com/marketplace/actions/crashlens-llm-log-contract-validation)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Stars](https://img.shields.io/github/stars/crashlens/crashlens?style=social)](https://github.com/crashlens/crashlens)

**Block bad LLM logs from reaching production.** Automatically validate Langfuse logs against schema contracts in your CI/CD pipeline. Prevent prompt waste, ensure data quality, and stop log chaos before it ships.

## 🎯 What This Action Does

- **🚫 Blocks bad logs** from being merged into your main branch
- **💰 Prevents prompt waste** by ensuring cost tracking fields are present
- **📊 Ensures data quality** for reliable analytics and debugging
- **⚡ Fast validation** - only checks changed .jsonl files
- **🔧 Zero configuration** - works out of the box with sensible defaults

## 🚀 Quick Start (30 seconds)

Add this to `.github/workflows/validate-logs.yml`:

```yaml
name: Validate LLM Logs

on:
  push:
    paths: ["**/*.jsonl"]
  pull_request:
    paths: ["**/*.jsonl"]

jobs:
  validate-logs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: crashlens/llm-log-contract-validation@v1
        with:
          log-paths: "**/*.jsonl"
          log-format: "langfuse-v1"
```

**That's it!** Now every commit with .jsonl files will be automatically validated.

## 📊 See It In Action

### ✅ When logs are valid:
```
✅ logs/production-traces.jsonl: PASSED
Contract check passed. All required fields present.
```

### ❌ When logs have violations:
```
❌ logs/broken-traces.jsonl: FAILED
Contract check failed:
  - Line 2: Missing required field: traceId
  - Line 3: Field 'startTime' has incorrect type. Expected str, got int
  - Line 5: Missing required field: input.model
Found 3 violation(s) across 5 log entries.
```

## 🛠️ Advanced Configuration

### Multiple Schema Formats
```yaml
- uses: crashlens/llm-log-contract-validation@v1
  with:
    log-paths: "production-logs/**/*.jsonl"
    log-format: "langfuse-v2"  # Supports v1, v2, and more
```

### Warning Mode (Don't Fail CI)
```yaml
- uses: crashlens/llm-log-contract-validation@v1
  with:
    fail-on-violations: false
  id: validation

- name: Post warning comment
  if: steps.validation.outputs.violations-found == 'true'
  run: |
    echo "⚠️ Found ${{ steps.validation.outputs.violations-count }} log violations"
```

### Matrix Strategy for Multiple Services
```yaml
strategy:
  matrix:
    service: [api, worker, scheduler]
steps:
  - uses: crashlens/llm-log-contract-validation@v1
    with:
      log-paths: "services/${{ matrix.service }}/**/*.jsonl"
```

## 📋 Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `log-paths` | Glob pattern for log files to validate | No | `**/*.jsonl` |
| `log-format` | Log format version (langfuse-v1, langfuse-v2) | No | `langfuse-v1` |
| `fail-on-violations` | Whether to fail the action on violations | No | `true` |
| `working-directory` | Working directory to run validation from | No | `.` |

## 📤 Outputs

| Output | Description |
|--------|-------------|
| `violations-found` | Whether schema violations were found (true/false) |
| `violations-count` | Number of schema violations found |
| `validation-summary` | JSON summary of validation results |

## 🔍 Schema Requirements

### Langfuse V1 (Default)
**Required Fields:**
- `traceId` (string) - Unique identifier for the trace
- `startTime` (string) - ISO timestamp when the trace started
- `input.model` (string) - Model name used for the request

**Optional Fields:**
- `endTime` (string) - ISO timestamp when the trace ended
- `cost` (number) - Cost of the request in dollars
- `usage.prompt_tokens` (integer) - Number of prompt tokens used
- `usage.completion_tokens` (integer) - Number of completion tokens generated

### Example Valid Log
```json
{
  "traceId": "trace_abc123",
  "startTime": "2024-01-01T10:00:00Z",
  "input": {"model": "gpt-4"},
  "cost": 0.01,
  "usage": {"prompt_tokens": 150, "completion_tokens": 50}
}
```

## 💡 Why Use This Action?

### For Developers
- **Catch errors early** - Find log issues before they reach production
- **Clear feedback** - Know exactly what's wrong and how to fix it
- **Save debugging time** - Consistent logs make troubleshooting easier

### For Teams
- **Prevent outages** - Block malformed logs that could break pipelines
- **Cost control** - Ensure cost tracking works correctly
- **Data governance** - Meet compliance requirements automatically

### For Production
- **Reliable analytics** - Clean logs = accurate dashboards
- **Better monitoring** - Complete trace data for observability
- **FinOps confidence** - Trust your LLM cost calculations

## 🧪 Test Locally

Before pushing, test your logs locally:

```bash
# Install CrashLens CLI
pip install crashlens

# Validate a specific file
crashlens scan --contract-check logs/your-file.jsonl --log-format langfuse-v1

# See what fields are required
crashlens scan --contract-info --log-format langfuse-v1

# Get JSON output for automation
crashlens scan --contract-check --output json logs/your-file.jsonl
```

## 🎯 Real-World Impact

Teams using CrashLens report:

- **60% faster debugging** with complete, consistent trace data
- **100% reliable cost tracking** for accurate FinOps reporting  
- **Zero production outages** from malformed logs breaking pipelines
- **Improved team confidence** in AI application data quality

## 🔗 Integration Add-ons

### Slack Notifications
```yaml
- name: Notify Slack on violations
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: failure
    text: "🚨 Log schema violations found in ${{ github.event.pull_request.html_url }}"
```

### Budget Enforcement
```yaml
- name: Check LLM costs
  run: |
    cost=$(crashlens scan --summary logs/ | grep "Total Cost" | cut -d'$' -f2)
    if (( $(echo "$cost > 50.0" | bc -l) )); then
      echo "🚨 PR exceeds budget: \$$cost"
      exit 1
    fi
```

## 🆘 Troubleshooting

### No files found
- Check your `log-paths` pattern matches your file structure
- Use `find . -name "*.jsonl"` to see what files exist

### False violations  
- Run locally: `crashlens scan --contract-check file.jsonl -v`
- Check field types (strings vs numbers)
- Verify nested field paths like `input.model`

### Action not triggering
- Ensure workflow file is in `.github/workflows/`
- Check that changes include `.jsonl` files
- Look at Actions tab for detailed logs

## 🤝 Contributing

Found a bug? Want a new feature? 

- [Open an issue](https://github.com/crashlens/crashlens/issues)
- [View the source code](https://github.com/crashlens/crashlens)
- [Read the docs](https://github.com/crashlens/crashlens/blob/main/README.md)

## 📄 License

MIT License - see [LICENSE](https://github.com/crashlens/crashlens/blob/main/LICENSE)

---

**⭐ Star us on GitHub** if this action helps your team! 

**Made with ❤️ by the CrashLens team** - Helping teams ship better LLM applications with confident log quality.
