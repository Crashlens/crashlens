# Crashlens GitHub Actions Workflow Template

This directory contains the GitHub Actions workflow template for Crashlens policy checking.

## 📁 Files

- `crashlens.yml` - The main workflow template
- `crashlens.properties.json` - Metadata for GitHub's workflow template system

## 🚀 How to Use

### Option 1: Using GitHub's Workflow Templates (Recommended)

1. Navigate to your repository on GitHub
2. Go to the **Actions** tab
3. Click **"New workflow"**
4. Look for **"Crashlens Policy Check"** in the templates
5. Click **"Set up this workflow"**
6. Customize the workflow file if needed
7. Commit the workflow to your repository

### Option 2: Manual Setup

1. Copy `crashlens.yml` to `.github/workflows/crashlens.yml` in your repository
2. Add your `.jsonl` log files to the repository
3. Commit and push - the workflow will run automatically

## 🔧 Configuration Options

### Severity Thresholds
```yaml
# Block only critical violations
--severity-threshold critical

# Block high and critical violations (default)
--severity-threshold high

# Block medium, high, and critical violations  
--severity-threshold medium

# Block all violations including low severity
--severity-threshold low
```

### Policy Templates
```yaml
# Use all built-in templates (recommended)
--policy-template all

# Use specific templates
--policy-template retry-loop-prevention,model-overkill-detection

# Use custom policy file
--policy-file .github/policies/custom.yaml
```

### Workflow Triggers
```yaml
# Default: Run on push/PR to main
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

# Additional options:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday at 2 AM
  workflow_dispatch:      # Manual trigger
```

## 📊 What the Workflow Does

1. **Sets up environment**: Python 3.11, pip caching
2. **Installs Crashlens**: Latest version from PyPI
3. **Finds log files**: Automatically detects `.jsonl` files
4. **Runs policy check**: Uses all built-in templates
5. **Fails CI**: If high/critical severity violations found
6. **Uploads artifacts**: Policy results for review
7. **Adds PR summary**: Results summary in pull requests

## 🛡️ Policy Templates Included

The workflow runs **all 11 built-in policy templates**:

- **Retry Loop Prevention** (Critical)
- **Model Overkill Detection** (High) 
- **Chain Recursion Prevention** (Critical)
- **Fallback Storm Detection** (Critical)
- **Budget Protection** (Critical)
- **Rate Limit Management** (High)
- **Prompt Optimization** (Medium)
- **Error Handling Efficiency** (Medium)
- **Context Window Optimization** (Medium)
- **Batch Processing Efficiency** (Medium)

## 🎯 CI/CD Integration

### Exit Codes
- `0` - No violations or only low/medium severity (CI passes)
- `1` - High/critical violations found (CI fails)

### Artifacts
- Policy check results are uploaded as artifacts
- Available for 30 days after workflow run
- Includes original log files and analysis results

### PR Integration
- Adds policy check summary to pull request
- Shows violation counts and recommendations
- Links to full policy documentation

## 📝 Example Log File Structure

```
your-repo/
├── .github/
│   └── workflows/
│       └── crashlens.yml
├── logs/
│   ├── production.jsonl
│   ├── staging.jsonl
│   └── errors.jsonl
├── data/
│   └── traces.jsonl
└── README.md
```

## 🔍 Customization Examples

### Custom Policy File
```yaml
# Add this step before the policy check
- name: Setup custom policies
  run: |
    mkdir -p .github/policies
    cat > .github/policies/strict.yaml << EOF
    policies:
      - name: "Zero Tolerance Retry"
        conditions:
          - field: "retry_count"
            operator: ">"
            value: 0
        action: "fail"
        severity: "critical"
    EOF

# Update the policy check command
- name: Run Crashlens policy check
  run: |
    crashlens policy-check logs.jsonl --policy-file .github/policies/strict.yaml --fail-on-violations
```

### Multiple Environments
```yaml
strategy:
  matrix:
    environment: [staging, production]
    
steps:
- name: Run policy check for ${{ matrix.environment }}
  run: |
    crashlens policy-check logs/${{ matrix.environment }}.jsonl --policy-template all --fail-on-violations
```

## 📚 Additional Resources

- [Crashlens Documentation](https://github.com/Crashlens/crashlens)
- [Policy Templates Guide](../POLICY_TEMPLATES_COMPLETE.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
