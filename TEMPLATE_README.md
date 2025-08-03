# 🔍 Langfuse Schema Validation Template

[![Schema Validation](https://github.com/your-username/langfuse-schema-template/actions/workflows/langfuse-schema-check.yml/badge.svg)](https://github.com/your-username/langfuse-schema-template/actions/workflows/langfuse-schema-check.yml)

A template repository for automated Langfuse log schema validation using CrashLens. Fork this repository to automatically validate your Langfuse logs against schema contracts in CI/CD pipelines.

## 🚀 Quick Start

### 1. Fork This Repository
Click the **Fork** button at the top of this repository to create your own copy.

### 2. Add Your Langfuse Logs
Replace the sample file in `logs/langfuse-latest.jsonl` with your actual Langfuse log data:

```bash
# Copy your logs to the repository
cp your-langfuse-logs.jsonl logs/langfuse-latest.jsonl
```

### 3. Enable GitHub Actions
1. Go to your forked repository's **Actions** tab
2. Click **Enable Actions** if prompted
3. The schema validation will run automatically on every push and pull request

### 4. Check Results
- ✅ **Green checkmark**: Your logs pass schema validation
- ❌ **Red X**: Schema contract violations detected
- 🟡 **Yellow dot**: Workflow is running

## 📂 Repository Structure

```
├── .github/
│   └── workflows/
│       └── langfuse-schema-check.yml    # Automated schema validation
├── logs/
│   └── langfuse-latest.jsonl            # Your Langfuse log file
├── README.md                            # This file
└── docs/
    ├── USAGE.md                         # Detailed usage guide
    └── TROUBLESHOOTING.md               # Common issues and solutions
```

## 🛠️ Configuration Options

### Environment Variables

Set these in your repository's **Settings → Secrets and variables → Actions → Variables**:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_PATH` | Path to your Langfuse log file | `logs/langfuse-latest.jsonl` |
| `SCHEMA_VERSION` | Schema version to validate against | `langfuse-v1` |

### Manual Workflow Dispatch

You can manually trigger validation with custom parameters:

1. Go to **Actions → Langfuse Schema Validation**
2. Click **Run workflow**
3. Specify custom log path and schema version

## 🧪 Supported Schema Versions

| Version | Status | Description |
|---------|--------|-------------|
| `langfuse-v1` | ✅ Stable | Current production schema |
| `langfuse-v2` | 🚧 Beta | Future schema (with fallback to v1) |

## 📋 Schema Requirements

### Required Fields (langfuse-v1)
- `traceId` (string): Unique identifier for the trace

### Optional Fields
- `model` (string): LLM model used
- `prompt_tokens` (integer): Input token count
- `completion_tokens` (integer): Output token count
- `cost` (number): API call cost
- `timestamp` (string): ISO 8601 timestamp
- `userId` (string): User identifier
- `input` (string): Input prompt
- `output` (string): Generated response
- `metadata` (object): Additional metadata

### Example Valid Log Entry

```json
{
  "traceId": "trace_12345",
  "model": "gpt-4",
  "prompt_tokens": 150,
  "completion_tokens": 75,
  "cost": 0.0045,
  "timestamp": "2025-08-03T10:30:00Z",
  "userId": "user_abc123",
  "input": "What is the capital of France?",
  "output": "The capital of France is Paris.",
  "metadata": {
    "temperature": 0.7,
    "max_tokens": 100
  }
}
```

## 🔧 Advanced Usage

### Multiple Log Files

To validate multiple log files, modify the workflow matrix:

```yaml
strategy:
  matrix:
    log-file: 
      - logs/production-logs.jsonl
      - logs/staging-logs.jsonl
      - logs/development-logs.jsonl
```

### Custom Validation Rules

Add your own validation logic by extending the workflow:

```yaml
- name: Custom Validation
  run: |
    # Add your custom checks here
    python scripts/custom-validation.py
```

### Integration with Existing CI/CD

Include schema validation in your existing workflows:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate Langfuse Schema
        uses: ./.github/workflows/langfuse-schema-check.yml
```

## 🚨 Troubleshooting

### Common Issues

#### ❌ "Log file not found"
**Solution**: Ensure your log file exists at the specified path
```bash
# Check if file exists
ls -la logs/langfuse-latest.jsonl

# Verify file format
head -n 1 logs/langfuse-latest.jsonl
```

#### ❌ "Schema contract violations"
**Solution**: Check your log format against the schema requirements
- Ensure `traceId` field is present and is a string
- Verify JSON structure is valid
- Check for required field types

#### ❌ "Unsupported schema version"
**Solution**: Use a supported schema version
```bash
# Test locally with supported version
crashlens scan logs/langfuse-latest.jsonl --log-format langfuse-v1
```

### Getting Help

1. **Check the [Troubleshooting Guide](docs/TROUBLESHOOTING.md)**
2. **Review workflow logs** in the Actions tab
3. **Open an issue** with your log samples and error messages

## 🤝 Contributing

### Improving This Template

1. Fork this repository
2. Make your improvements
3. Submit a pull request

### Reporting Issues

Found a bug or have a feature request? [Open an issue](https://github.com/your-username/langfuse-schema-template/issues/new).

## 📚 Additional Resources

- **[CrashLens Documentation](https://github.com/crashlens/crashlens)**: Complete CrashLens usage guide
- **[Langfuse Documentation](https://langfuse.com/docs)**: Official Langfuse documentation
- **[Schema Versioning Guide](SCHEMA_VERSIONING.md)**: Detailed schema contract management

## 📄 License

This template is provided under the MIT License. See [LICENSE](LICENSE) for details.

---

## 🏷️ Template Usage Badge

Add this badge to your repository to show you're using automated schema validation:

```markdown
[![Langfuse Schema Validation](https://img.shields.io/badge/Langfuse-Schema%20Validated-green?logo=github&logoColor=white)](https://github.com/your-username/your-repo-name/actions/workflows/langfuse-schema-check.yml)
```

**Happy validating! 🎉**
