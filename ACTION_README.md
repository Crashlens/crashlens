# CrashLens GitHub Action

[![GitHub Action](https://img.shields.io/badge/action-crashlens%2Fcontract--check-blue)](https://github.com/marketplace/actions/crashlens-contract-check)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Automatically validate Langfuse logs against schema contracts in your CI/CD pipeline. Block bad logs from shipping and maintain data quality across your entire development lifecycle.

## 🎯 Features

- **Schema Contract Validation**: Enforce required fields and data types
- **Multiple Format Support**: langfuse-v1, langfuse-v2, and more
- **Flexible Input**: Validate specific files or use glob patterns
- **Rich Output**: Detailed violation reports with line numbers
- **Zero Configuration**: Works out of the box with sensible defaults
- **Fast & Lightweight**: Only validates changed log files

## 🚀 Quick Start

Add this to your `.github/workflows/validate-logs.yml`:

```yaml
name: Validate Log Contracts

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
      
      - name: Validate Langfuse logs
        uses: crashlens/contract-check@v1
        with:
          log-paths: "**/*.jsonl"
          log-format: "langfuse-v1"
          fail-on-violations: true
```

## 📋 Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `log-paths` | Glob pattern for log files to validate | No | `**/*.jsonl` |
| `log-format` | Log format version (langfuse-v1, langfuse-v2) | No | `langfuse-v1` |
| `fail-on-violations` | Fail the action on schema violations | No | `true` |
| `working-directory` | Directory to run validation from | No | `.` |

## 📊 Outputs

| Output | Description |
|--------|-------------|
| `violations-found` | Whether schema violations were found (true/false) |
| `violations-count` | Number of schema violations found |
| `validation-summary` | JSON summary of validation results |

## 📖 Advanced Usage

### Validate Specific Files

```yaml
- name: Validate specific log files
  uses: crashlens/contract-check@v1
  with:
    log-paths: "logs/production-*.jsonl"
    log-format: "langfuse-v2"
```

### Continue on Violations (Warning Mode)

```yaml
- name: Validate logs (warning only)
  uses: crashlens/contract-check@v1
  with:
    fail-on-violations: false
  
- name: Report violations
  if: steps.validate.outputs.violations-found == 'true'
  run: |
    echo "⚠️ Found ${{ steps.validate.outputs.violations-count }} schema violations"
    echo "Summary: ${{ steps.validate.outputs.validation-summary }}"
```

### Matrix Strategy for Multiple Formats

```yaml
strategy:
  matrix:
    format: [langfuse-v1, langfuse-v2]
    
steps:
  - name: Validate logs (${{ matrix.format }})
    uses: crashlens/contract-check@v1
    with:
      log-format: ${{ matrix.format }}
```

## 🔍 Schema Contract Examples

### ✅ Valid Langfuse V1 Log

```json
{
  "traceId": "trace_abc123",
  "startTime": "2024-01-01T10:00:00Z",
  "input": {
    "model": "gpt-4"
  },
  "cost": 0.01,
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 50
  }
}
```

### ❌ Invalid Logs (Will Fail)

```json
{"startTime": "2024-01-01T10:00:00Z", "input": {"model": "gpt-4"}}
// Missing: traceId

{"traceId": "trace_123", "startTime": "2024-01-01T10:00:00Z"}  
// Missing: input.model

{"traceId": "trace_123", "startTime": 1704110400, "input": {"model": "gpt-4"}}
// Wrong type: startTime should be string, not number
```

## 🛠️ Local Development

Test the action locally using [act](https://github.com/nektos/act):

```bash
# Install act
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run the action locally
act push -W .github/workflows/validate-logs.yml
```

Or test the CLI directly:

```bash
# Install CrashLens
pip install crashlens

# Validate a file
crashlens scan --contract-check logs.jsonl --log-format langfuse-v1

# View schema requirements
crashlens scan --contract-info --log-format langfuse-v1
```

## 🔧 Integration Examples

### Monorepo with Multiple Services

```yaml
jobs:
  validate-service-logs:
    strategy:
      matrix:
        service: [api, worker, scheduler]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: crashlens/contract-check@v1
        with:
          log-paths: "services/${{ matrix.service }}/**/*.jsonl"
          working-directory: "."
```

### Conditional Validation on Changed Files

```yaml
- name: Get changed files
  id: changed-files
  uses: tj-actions/changed-files@v40
  with:
    files: "**/*.jsonl"

- name: Validate changed logs
  if: steps.changed-files.outputs.any_changed == 'true'
  uses: crashlens/contract-check@v1
  with:
    log-paths: ${{ steps.changed-files.outputs.all_changed_files }}
```

## 📚 Schema Contract Reference

### Langfuse V1 Schema

**Required Fields:**
- `traceId` (string)
- `startTime` (string, ISO timestamp)
- `input.model` (string)

**Optional Fields:**
- `endTime` (string, ISO timestamp)
- `cost` (number)
- `usage.prompt_tokens` (integer)
- `usage.completion_tokens` (integer)
- `output` (any)

### Langfuse V2 Schema

Includes all V1 fields plus:

**Additional Required:**
- `userId` (string)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for your changes
4. Run the test suite: `python test_workflow_locally.py`
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Links

- [CrashLens CLI Documentation](https://github.com/crashlens/crashlens)
- [GitHub Actions Marketplace](https://github.com/marketplace/actions/crashlens-contract-check)
- [Schema Contract Guide](https://github.com/crashlens/crashlens/blob/main/docs/schema-contracts.md)
- [Issue Tracker](https://github.com/crashlens/crashlens/issues)

---

**⚡ Made with ❤️ by the CrashLens team**

*Helping teams ship better LLM applications with confident log quality.*
