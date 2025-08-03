# 🚀 CrashLens CI Integration Guide

This guide shows you how to integrate CrashLens into your CI/CD pipeline for automated LLM log validation and policy enforcement.

## 🎯 Quick Start (2 minutes)

### 1. Basic Schema Validation

Add this workflow to `.github/workflows/validate-logs.yml`:

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
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install crashlens
      - run: crashlens scan **/*.jsonl --contract-check --log-format langfuse-v1
```

### 2. Policy Enforcement

Create a policy file at `policies/budget.yaml` and add policy validation:

```yaml
name: Policy Enforcement

on:
  push:
    paths: ["**/*.jsonl"]
  pull_request:
    paths: ["**/*.jsonl"]

jobs:
  policy-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install crashlens
      - run: crashlens scan **/*.jsonl --policy policies/budget.yaml --fail-on-policy
```

## 🔧 Advanced Configurations

### Multi-Environment Strategy

```yaml
name: Multi-Environment Validation

on:
  push:
    branches: [main]
  pull_request:

jobs:
  validate-logs:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [development, staging, production]
        include:
          - environment: development
            policy: policies/development.yaml
            fail-on: ""
          - environment: staging
            policy: policies/budget.yaml
            fail-on: "policy-violation"
          - environment: production
            policy: policies/budget.yaml
            fail-on: "retry,fallback,overkill,policy-violation"
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install crashlens
      
      - name: Validate ${{ matrix.environment }} logs
        run: |
          crashlens scan logs/${{ matrix.environment }}/**/*.jsonl \
            --policy ${{ matrix.policy }} \
            --fail-on ${{ matrix.fail-on }} \
            --output json > ${{ matrix.environment }}-report.json
        
      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.environment }}-validation-report
          path: ${{ matrix.environment }}-report.json
```

### Comprehensive Enforcement with Notifications

```yaml
name: Comprehensive Log Validation

on:
  push:
    branches: [main]
    paths: ["**/*.jsonl"]
  pull_request:
    paths: ["**/*.jsonl"]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install crashlens
      
      # Schema validation
      - name: Schema contract check
        run: crashlens scan **/*.jsonl --contract-check --log-format langfuse-v1
        
      # Policy enforcement
      - name: Policy validation
        id: policy
        run: |
          crashlens scan **/*.jsonl \
            --policy policies/budget.yaml \
            --fail-on policy-violation \
            --output json > policy-report.json
        continue-on-error: true
        
      # Pattern detection
      - name: Waste pattern detection
        id: patterns
        run: |
          crashlens scan **/*.jsonl \
            --fail-on retry,fallback,overkill \
            --output json > patterns-report.json
        continue-on-error: true
        
      # Generate summary
      - name: Generate validation summary
        run: |
          echo "# 📊 CrashLens Validation Report" > validation-summary.md
          echo "" >> validation-summary.md
          echo "## Policy Violations" >> validation-summary.md
          if [ -f policy-report.json ]; then
            crashlens policy-check policies/budget.yaml **/*.jsonl --output-format text >> validation-summary.md
          else
            echo "✅ No policy violations found" >> validation-summary.md
          fi
          echo "" >> validation-summary.md
          echo "## Waste Patterns" >> validation-summary.md
          crashlens scan **/*.jsonl --summary-only >> validation-summary.md
        
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const summary = fs.readFileSync('validation-summary.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: summary
            });
            
      - name: Notify Slack on failures
        if: failure()
        uses: 8398a7/action-slack@v3
        with:
          status: failure
          channel: '#llm-ops'
          text: |
            🚨 LLM log validation failed
            Branch: ${{ github.ref_name }}
            Commit: ${{ github.sha }}
            Check the validation report for details.
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

## 📋 Policy File Examples

### Basic Budget Control

```yaml
# policies/budget.yaml
metadata:
  name: "Budget Control Policy"
  version: "1.0"

rules:
  - id: "no-gpt4-retries"
    match:
      model: "gpt-4"
      retry_count: ">2"
    action: "fail"
    severity: "high"
    suggestion: "Use GPT-3.5-turbo for retries to save costs"

  - id: "token-limit"
    match:
      usage.total_tokens: ">10000"
    action: "warn"
    severity: "medium"
    suggestion: "Consider breaking down large prompts"
```

### Development Environment

```yaml
# policies/development.yaml
metadata:
  name: "Development Policy"
  
rules:
  - id: "dev-model-recommendation"
    match:
      model: ["gpt-4", "claude-3-opus"]
      environment: "development"
    action: "warn"
    severity: "medium"
    suggestion: "Consider using GPT-3.5-turbo for faster development"
```

### Production Enforcement

```yaml
# policies/production.yaml
metadata:
  name: "Production Policy"
  
rules:
  - id: "unauthorized-models"
    match:
      model: "not in:['gpt-3.5-turbo', 'gpt-4']"
    action: "block"
    severity: "critical"
    suggestion: "Only approved models allowed in production"
    
  - id: "excessive-costs"
    match:
      cost: ">1.0"
    action: "fail"
    severity: "high"
    suggestion: "Single requests over $1 require approval"
```

## 🎛️ CLI Reference

### Schema Validation
```bash
# Basic schema check
crashlens scan logs.jsonl --contract-check

# Specific schema version
crashlens scan logs.jsonl --contract-check --log-format langfuse-v2

# JSON output for automation
crashlens scan logs.jsonl --contract-check --output json
```

### Policy Enforcement
```bash
# Basic policy check
crashlens scan logs.jsonl --policy budget.yaml

# Fail on policy violations
crashlens scan logs.jsonl --policy budget.yaml --fail-on-policy

# Dedicated policy command
crashlens policy-check budget.yaml logs.jsonl
```

### Pattern Detection with Selective Failure
```bash
# Fail only on specific patterns
crashlens scan logs.jsonl --fail-on retry,policy-violation

# All patterns but don't fail CI
crashlens scan logs.jsonl --summary-only

# Detailed reports for investigation
crashlens scan logs.jsonl --detailed --detailed-dir reports/
```

## 🔍 Troubleshooting

### Common Issues

**No files found**
```bash
# Check file patterns
find . -name "*.jsonl" -type f

# Use specific paths
crashlens scan logs/production/*.jsonl
```

**Policy not loading**
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('policy.yaml'))"

# Check file permissions
ls -la policy.yaml
```

**Schema validation failing**
```bash
# Check log format
head -n 1 logs.jsonl | jq .

# Validate JSON syntax
cat logs.jsonl | jq . > /dev/null
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
export CRASHLENS_DEBUG=1
crashlens scan logs.jsonl --policy budget.yaml
```

## 📊 Success Metrics

Track these metrics to measure the impact of CrashLens in your CI:

- **Policy Violations Prevented**: Number of PRs blocked by policy rules
- **Cost Savings**: Estimated savings from prevented waste patterns  
- **Compliance Rate**: Percentage of logs passing schema validation
- **Time to Resolution**: How quickly teams fix violations

### Example Metrics Dashboard

```yaml
# .github/workflows/metrics.yml
name: CrashLens Metrics

on:
  schedule:
    - cron: '0 9 * * 1'  # Weekly on Monday

jobs:
  metrics:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install crashlens
      
      - name: Generate weekly report
        run: |
          echo "# 📊 Weekly CrashLens Report" > weekly-report.md
          echo "Period: $(date -d '7 days ago' +%Y-%m-%d) to $(date +%Y-%m-%d)" >> weekly-report.md
          
          # Find all log files from the past week
          find . -name "*.jsonl" -mtime -7 | while read file; do
            echo "## Analysis: $file" >> weekly-report.md
            crashlens scan "$file" --summary-only >> weekly-report.md
            echo "" >> weekly-report.md
          done
```

## 🚀 Advanced Integrations

### Budget Tracking Integration

```yaml
- name: Track LLM costs
  run: |
    total_cost=$(crashlens scan logs/**/*.jsonl --summary | grep "Total Cost" | cut -d'$' -f2)
    echo "WEEKLY_LLM_COST=$total_cost" >> $GITHUB_ENV
    
    if (( $(echo "$total_cost > 100.0" | bc -l) )); then
      echo "::warning::Weekly LLM cost ($${total_cost}) exceeds budget"
    fi
```

### Security Integration

```yaml
- name: PII detection
  run: |
    crashlens scan logs/**/*.jsonl --detect-pii --fail-on-pii
```

### Performance Integration

```yaml
- name: Performance analysis
  run: |
    crashlens scan logs/**/*.jsonl --analyze-performance --output json > perf-report.json
    
    # Check for slow requests
    slow_requests=$(jq '.slow_requests | length' perf-report.json)
    if [ "$slow_requests" -gt 5 ]; then
      echo "::warning::Found $slow_requests slow requests"
    fi
```

---

## 🎉 You're Ready!

With CrashLens integrated into your CI pipeline, you now have:

- ✅ **Automated schema validation** preventing malformed logs
- ✅ **Policy enforcement** ensuring cost and usage compliance  
- ✅ **Pattern detection** catching waste before it costs money
- ✅ **Team notifications** keeping everyone informed
- ✅ **Detailed reporting** for continuous improvement

Your LLM logs are now protected by production-grade quality gates! 🛡️

**Next Steps:**
1. Start with basic schema validation
2. Add policy rules for your specific needs
3. Gradually increase enforcement strictness
4. Monitor metrics and adjust policies as needed
5. Share success stories with your team! 🎊
