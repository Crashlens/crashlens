# 📁 CrashLens Example Repository Structure

This document shows how to structure your repository for optimal CrashLens integration and demonstrates different workflow patterns for various team setups.

## 🏗️ Basic Repository Structure

```
my-llm-project/
├── .github/
│   └── workflows/
│       ├── validate-logs.yml          # Main log validation workflow
│       ├── validate-pr-logs.yml       # PR-specific validation
│       └── daily-log-health.yml       # Scheduled validation
├── logs/
│   ├── production/
│   │   ├── api-traces.jsonl           # Production API logs
│   │   └── worker-traces.jsonl        # Background job logs
│   ├── staging/
│   │   └── test-traces.jsonl          # Staging environment logs
│   └── development/
│       └── dev-traces.jsonl           # Development logs
├── tests/
│   └── fixtures/
│       ├── valid-logs.jsonl           # Test data for validation
│       └── invalid-logs.jsonl         # Test data for failures
└── crashlens-config.yml               # Optional: Custom configuration
```

## 🔧 Workflow Examples

### 1. Basic Validation (Recommended Start)

**File**: `.github/workflows/validate-logs.yml`
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

### 2. Multi-Environment Validation

**File**: `.github/workflows/validate-pr-logs.yml`
```yaml
name: Validate PR Logs

on:
  pull_request:
    paths: ["logs/**/*.jsonl"]

jobs:
  validate-environments:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [development, staging, production]
    steps:
      - uses: actions/checkout@v4
      - name: Validate ${{ matrix.environment }} logs
        uses: crashlens/llm-log-contract-validation@v1
        with:
          log-paths: "logs/${{ matrix.environment }}/**/*.jsonl"
          log-format: "langfuse-v1"
```

### 3. Advanced with Notifications and Budget

**File**: `.github/workflows/validate-with-alerts.yml`
```yaml
name: Validate Logs with Alerts

on:
  push:
    branches: [main]
    paths: ["**/*.jsonl"]

jobs:
  validate-and-alert:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Validate log contracts
        id: validation
        uses: crashlens/llm-log-contract-validation@v1
        with:
          log-paths: "logs/production/**/*.jsonl"
          log-format: "langfuse-v1"
          fail-on-violations: false
        
      - name: Check budget compliance
        if: steps.validation.outputs.violations-found == 'false'
        run: |
          pip install crashlens
          cost=$(crashlens scan --summary logs/production/ | grep "Total Cost" | cut -d'$' -f2)
          if (( $(echo "$cost > 100.0" | bc -l) )); then
            echo "🚨 Weekly budget exceeded: \$$cost"
            echo "budget-exceeded=true" >> $GITHUB_OUTPUT
          fi
        id: budget
        
      - name: Notify Slack on violations
        if: steps.validation.outputs.violations-found == 'true'
        uses: 8398a7/action-slack@v3
        with:
          status: failure
          channel: '#llm-ops'
          text: |
            🚨 Log schema violations found in production logs
            Violations: ${{ steps.validation.outputs.violations-count }}
            Branch: ${{ github.ref_name }}
            Commit: ${{ github.sha }}
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          
      - name: Notify Slack on budget exceeded
        if: steps.budget.outputs.budget-exceeded == 'true'
        uses: 8398a7/action-slack@v3
        with:
          status: custom
          custom_payload: |
            {
              "channel": "#finance",
              "text": "💰 Weekly LLM budget exceeded",
              "attachments": [{
                "color": "warning",
                "fields": [{
                  "title": "Cost",
                  "value": "${{ steps.budget.outputs.cost }}",
                  "short": true
                }, {
                  "title": "Limit", 
                  "value": "$100.00",
                  "short": true
                }]
              }]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### 4. Scheduled Health Checks

**File**: `.github/workflows/daily-log-health.yml`
```yaml
name: Daily Log Health Check

on:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM UTC
  workflow_dispatch:     # Manual trigger

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check all logs
        uses: crashlens/llm-log-contract-validation@v1
        with:
          log-paths: "logs/**/*.jsonl"
          log-format: "langfuse-v1"
          fail-on-violations: false
        id: health
        
      - name: Generate health report
        run: |
          pip install crashlens
          echo "# Daily Log Health Report - $(date)" > health-report.md
          echo "" >> health-report.md
          crashlens scan --summary logs/ >> health-report.md
          
      - name: Create issue on failures
        if: steps.health.outputs.violations-found == 'true'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('health-report.md', 'utf8');
            
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: '🚨 Daily Log Health Check Failed',
              body: `Automated health check found issues:\n\n${report}`,
              labels: ['bug', 'logs', 'automated']
            });
```

## 📊 Sample Log Files

### Valid Production Log
**File**: `logs/production/api-traces.jsonl`
```json
{"traceId": "trace_prod_001", "startTime": "2024-01-15T10:00:00Z", "input": {"model": "gpt-4"}, "cost": 0.05, "usage": {"prompt_tokens": 200, "completion_tokens": 100}}
{"traceId": "trace_prod_002", "startTime": "2024-01-15T10:01:00Z", "input": {"model": "gpt-3.5-turbo"}, "cost": 0.01, "usage": {"prompt_tokens": 150, "completion_tokens": 50}}
```

### Development Log (Relaxed Requirements)
**File**: `logs/development/dev-traces.jsonl`
```json
{"traceId": "trace_dev_001", "startTime": "2024-01-15T10:00:00Z", "input": {"model": "gpt-4"}}
{"traceId": "trace_dev_002", "startTime": "2024-01-15T10:01:00Z", "input": {"model": "gpt-3.5-turbo"}, "endTime": "2024-01-15T10:01:30Z"}
```

### Test Fixtures
**File**: `tests/fixtures/invalid-logs.jsonl`
```json
{"startTime": "2024-01-15T10:00:00Z", "input": {"model": "gpt-4"}}
{"traceId": "trace_002", "input": {"model": "gpt-3.5-turbo"}}
{"traceId": "trace_003", "startTime": "invalid-date", "input": {"model": "gpt-4"}}
```

## ⚙️ Configuration Options

### Custom Configuration File
**File**: `crashlens-config.yml`
```yaml
# CrashLens Configuration
log_format: "langfuse-v1"
validation:
  strict_mode: true
  required_fields:
    - traceId
    - startTime
    - input.model
  optional_fields:
    - cost
    - usage.prompt_tokens
    - usage.completion_tokens
  
environments:
  production:
    strict_mode: true
    budget_limit: 100.0
  staging:
    strict_mode: false
    budget_limit: 50.0
  development:
    strict_mode: false
    
notifications:
  slack:
    enabled: true
    channels:
      violations: "#llm-ops"
      budget: "#finance"
  email:
    enabled: false
```

## 🔧 Team-Specific Patterns

### For Startups (Simple & Fast)
```yaml
# Single workflow, basic validation
- uses: crashlens/llm-log-contract-validation@v1
  with:
    log-paths: "logs/**/*.jsonl"
```

### For Scale-ups (Multi-Environment)
```yaml
# Matrix strategy for different services
strategy:
  matrix:
    service: [api, worker, analytics]
    environment: [staging, production]
```

### For Enterprises (Full Governance)
```yaml
# Comprehensive validation with compliance
- uses: crashlens/llm-log-contract-validation@v1
- name: Compliance check
- name: Cost center allocation
- name: Security scan
- name: Audit logging
```

## 📋 Migration Checklist

### From Manual Validation
- [ ] Add `.github/workflows/validate-logs.yml`
- [ ] Test with existing log files
- [ ] Update team documentation
- [ ] Train team on new workflow

### From Other Tools
- [ ] Compare schema requirements
- [ ] Update log format if needed
- [ ] Migrate configuration settings
- [ ] Test validation behavior

### Gradual Rollout
1. **Week 1**: Add workflow in warning mode (`fail-on-violations: false`)
2. **Week 2**: Fix any violations found
3. **Week 3**: Enable strict mode (`fail-on-violations: true`)
4. **Week 4**: Add notifications and budget checks

## 🎯 Best Practices

### File Organization
- **Separate by environment** (`production/`, `staging/`, `development/`)
- **Group by service** (`api/`, `worker/`, `analytics/`)
- **Use consistent naming** (`service-environment-date.jsonl`)

### Workflow Design
- **Start simple** with basic validation
- **Add complexity gradually** as team matures
- **Use matrix strategies** for multiple services/environments
- **Include manual triggers** for debugging

### Team Adoption
- **Show immediate value** with quick wins
- **Provide clear error messages** for violations
- **Include budget/cost tracking** for business impact
- **Create shared responsibility** across team members

---

**Ready to get started?** Copy one of these workflow examples to your repository and customize the log paths for your project structure!
