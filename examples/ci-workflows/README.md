# CrashLens CI/CD Workflow Examples

This directory contains example GitHub Actions workflows that you can copy into your own repositories to integrate CrashLens analysis into your CI/CD pipeline.

## Available Examples

### `basic-crashlens.yml.example` - Minimal Setup
**Features:**
- Simple 10-line workflow for quick setup
- Automatic log file detection
- Basic cost analysis

**Best for:** Getting started quickly, minimal configuration needed.

### `crashlens-starter.yml.example` - Basic Policy Check
**Features:**
- Focuses on core issues (retry loops, model overkill)
- Lightweight and fast execution
- Simple artifact uploads
- Essential policy checking only

**Best for:** New projects or teams wanting to start with basic monitoring.

### `crashlens-with-slack.yml.example` - 🔔 **NEW!** Slack Integration
**Features:**
- Complete CrashLens analysis with policy checking
- **Automated Slack notifications** with results
- Rich message formatting with status, costs, and links
- Configurable via workflow inputs
- PR comments and artifact uploads

**Best for:** Teams that want real-time Slack notifications about token waste and policy violations.

### `crashlens-strict.yml.example` - Strict Enforcement (Build-Breaking)
**Features:**
- **FAILS CI/CD builds** when limits are exceeded
- Enforces strict cost limits ($5/day default)
- Enforces performance thresholds (slow traces, error rates)
- Enforces all CrashLens policy violations (high+ severity)
- Detailed violation reporting with remediation suggestions

**Best for:** Production teams that want hard enforcement of AI usage policies.

⚠️ **WARNING**: The strict workflow will break your builds if violations are detected!

## Quick Setup

### 1. Choose Your Workflow
Copy the example that matches your needs:

**For comprehensive analysis:**
```bash
mkdir -p .github/workflows
curl -o .github/workflows/crashlens-analysis.yml \
  https://raw.githubusercontent.com/Crashlens/crashlens/main/examples/ci-workflows/crashlens-analysis.yml.example
```

**For starter/basic checking:**
```bash
mkdir -p .github/workflows
curl -o .github/workflows/crashlens.yml \
  https://raw.githubusercontent.com/Crashlens/crashlens/main/examples/ci-workflows/crashlens-starter.yml.example
```

**For strict enforcement (build-breaking):**
```bash
mkdir -p .github/workflows
curl -o .github/workflows/crashlens-strict.yml \
  https://raw.githubusercontent.com/Crashlens/crashlens/main/examples/ci-workflows/crashlens-strict.yml.example
```

### 2. Customize Configuration
Edit the workflow file to adjust:
- Branch names in the `on:` section
- Environment variables for thresholds and behavior
- Policy templates and severity levels

### 3. Log File Setup
The workflows automatically detect logs from:
- `.llm_logs/` directory (common for LangChain/LangFuse projects)
- `logs/` directory 
- Will generate simulation data if no logs are found

If your logs are elsewhere, modify the "Prepare Log Data" step:
```yaml
- name: Prepare Log Data
  run: |
    mkdir -p logs
    cp your-custom-logs-dir/*.jsonl logs/
```

## Configuration Options

### Environment Variables (Comprehensive Workflow)
```yaml
env:
  # Policy Configuration
  CRASHLENS_TEMPLATES: "retry-loop-prevention,model-overkill-detection,budget-protection"
  CRASHLENS_SEVERITY: "high"                    # low/medium/high/critical
  CRASHLENS_FAIL_ON_VIOLATIONS: "false"        # "true" to break CI on violations
  
  # Cost Monitoring
  DAILY_COST_LIMIT: "10.00"                    # Maximum daily cost in USD
  EXPENSIVE_REQUEST_THRESHOLD: "0.05"          # Flag requests over $0.05
  
  # Performance Limits
  SLOW_RESPONSE_THRESHOLD_MS: "3000"           # Flag responses over 3 seconds
  ERROR_RATE_THRESHOLD: "0.20"                 # Flag if >20% error rate
```

### Strict Enforcement Configuration
The strict workflow has hardcoded limits that **will break your CI** if exceeded:

```bash
# 🔧 STRICT LIMITS - Edit these in the workflow file
DAILY_COST_LIMIT=5.00       # 💰 Fail if total cost exceeds $5/day
SLOW_RESPONSE_LIMIT=20      # ⏱️ Fail if >20 slow traces
EXPENSIVE_REQUEST_LIMIT=10  # 💸 Fail if >10 expensive requests  
ERROR_RATE_THRESHOLD=0.20   # ❗ Fail if >20% error rate
```

**Customization**: Edit the values directly in the `crashlens-strict.yml.example` file before copying to your repo.

### Policy Templates
- `"all"` - Run all available policy checks
- `"retry-loop-prevention"` - Detect retry loops and cascading failures
- `"model-overkill-detection"` - Find cases where smaller models would work
- `"budget-protection"` - Monitor cost thresholds and expensive requests
- `"retry-loop-prevention,model-overkill-detection"` - Combine specific templates

### Severity Levels
- `"critical"` - Only show critical issues
- `"high"` - Show high and critical issues  
- `"medium"` - Show medium, high, and critical issues
- `"low"` - Show all issues

## Workflow Triggers

### Default Triggers
- **Pull Requests** to main branch
- **Manual trigger** via GitHub Actions UI
- **Comprehensive workflow** also runs daily at 6 AM UTC

### Custom Triggers
Modify the `on:` section to customize when workflows run:

```yaml
on:
  # Run on push to specific branches
  push:
    branches: [ main, develop, staging ]
  
  # Run on pull requests
  pull_request:
    branches: [ main ]
  
  # Run on schedule (daily at 2 AM UTC)
  schedule:
    - cron: '0 2 * * *'
  
  # Manual trigger with options
  workflow_dispatch:
    inputs:
      scan_type:
        description: 'Type of scan'
        required: true
        default: 'full'
        type: choice
        options: [full, logs-only, security]
```

## Output and Artifacts

### What Gets Generated
- **Analysis Reports** - Detailed markdown reports with policy violations
- **Log Files** - Original log files for reference
- **Artifacts** - Downloadable zip files with all reports (retained 7-14 days)

### Viewing Results
1. **Workflow Summary** - High-level results in GitHub Actions summary
2. **Artifacts Download** - Detailed reports available as downloadable artifacts
3. **Logs** - Full execution logs in the GitHub Actions run details

## Troubleshooting

### Common Issues

**No logs found:**
```bash
# Solution: Ensure logs are in expected locations or modify the workflow
# The workflow will generate simulation data if no real logs are found
```

**Cost analysis shows zero:**
```bash
# Solution: Ensure your log files contain cost information in 'totalCost' field
# Or customize the cost extraction logic in the workflow
```

**Workflow permission errors:**
```bash
# Solution: Ensure GitHub Actions is enabled and has proper permissions
# Check repository settings > Actions > General
```

**Policy check fails:**
```bash
# Solution: Check the specific error in workflow logs
# Most common: missing dependencies or malformed log files
```

### Getting Help

1. Check the [main CrashLens documentation](../../README.md)
2. Review the [troubleshooting guide](../../docs/TROUBLESHOOTING.md)
3. Open an issue in the CrashLens repository
4. Check workflow run logs for detailed error messages

## Advanced Customization

### Multiple Log Sources
```yaml
- name: Analyze Different Sources
  run: |
    # Analyze production logs separately
    crashlens guard logs/production/*.jsonl \
      --policy-template all --severity-threshold critical > prod-analysis.md
    
    # Analyze development logs with different thresholds  
    crashlens guard logs/development/*.jsonl \
      --policy-template all --severity-threshold medium > dev-analysis.md
```

### Custom Policy Files
```yaml
- name: Use Custom Policy
  run: |
    crashlens guard logs/*.jsonl \
      --policy-file .crashlens/custom-policy.yaml \
      --severity-threshold high
```

### Integration with Existing Workflows
Add CrashLens as a job in your existing workflows:

```yaml
jobs:
  # ... your existing jobs ...
  
  crashlens-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install crashlens
      - run: crashlens guard logs/*.jsonl --policy-template all
```

---

*For the complete CrashLens user guide, see [USER_MANUAL.md](../../USER_MANUAL.md)*
