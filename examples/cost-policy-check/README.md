# 💰 CrashLens Cost Policy Check Example

This example demonstrates how to use CrashLens to enforce cost and usage policies in your CI/CD pipeline.

## 🎯 What This Example Does

- **Validates LLM logs** against cost and usage policies
- **Blocks PRs** that violate your team's rules
- **Provides clear feedback** on what needs to be fixed
- **Generates reports** for tracking and compliance

## 🚀 How to Use

### 1. Copy this workflow to your repository

Copy `.github/workflows/cost-policy-check.yml` to your repository.

### 2. Create your policy file

Customize `policies/budget.yaml` with your team's rules:

```yaml
rules:
  - id: "no-gpt4-retries"
    match:
      model: "gpt-4" 
      retry_count: ">2"
    action: "fail"
    severity: "high"
    suggestion: "Use GPT-3.5-turbo for retries to save costs"
```

### 3. Test locally

```bash
# Test your logs against the policy
crashlens policy-check policies/budget.yaml logs/*.jsonl

# See detailed JSON output
crashlens policy-check policies/budget.yaml logs/*.jsonl --output-format json
```

## 📊 Example Results

### ✅ Passing Logs
```json
{"traceId": "trace_001", "model": "gpt-3.5-turbo", "retry_count": 1, "cost": 0.002}
```

**Result**: ✅ No policy violations found

### ❌ Failing Logs
```json
{"traceId": "trace_002", "model": "gpt-4", "retry_count": 4, "cost": 0.06}
```

**Result**: 
```
❌ Found 1 policy violation:
  Line 1: no-gpt4-in-retries (high)
    model=gpt-4 AND retry_count=4 (rule: >2)
    💡 Use GPT-3.5-turbo for retries to save costs
```

## 🔧 Policy Rules Reference

### Available Rules in This Example

1. **no-gpt4-in-retries**: Prevents expensive GPT-4 usage in retry scenarios
2. **token-limit-exceeded**: Warns when token usage is very high  
3. **expensive-model-overuse**: Blocks overuse of expensive models
4. **development-model-restriction**: Restricts expensive models in development
5. **excessive-retries**: Prevents retry loops that waste tokens
6. **unauthorized-model**: Blocks usage of unauthorized models

### Rule Structure

```yaml
- id: "rule-name"
  description: "Human readable description"
  match:
    field_name: "condition"  # e.g., ">5", "gpt-4", ["model1", "model2"]
    nested.field: ">1000"    # Supports dot notation
  action: "fail"             # fail, warn, block
  severity: "high"           # low, medium, high, critical
  suggestion: "What to do instead"
```

### Supported Operators

- **Equality**: `"gpt-4"`, `"!=gpt-4"`
- **Numeric**: `">5"`, `"<10"`, `">=100"`, `"<=50"`
- **Lists**: `["gpt-4", "claude-3-opus"]`
- **Regex**: `"regex:gpt-.*"`
- **String**: `"contains:turbo"`, `"startswith:gpt"`, `"endswith:4"`
- **Exclusion**: `"not in:['model1', 'model2']"`

## 🎛️ Workflow Configuration

### Basic Setup (Recommended)

```yaml
- name: Policy Check
  run: crashlens policy-check policies/budget.yaml **/*.jsonl
```

### With JSON Report Generation

```yaml
- name: Generate Report
  run: |
    crashlens policy-check policies/budget.yaml **/*.jsonl \
      --output-format json > policy-report.json
```

### With PR Comments

The workflow automatically comments on PRs when violations are found, showing:
- Number of violations
- Specific rules that failed
- Line numbers and suggestions
- Severity levels

## 📈 Benefits

### For Developers
- **Immediate feedback** on cost-impacting changes
- **Clear guidance** on how to fix violations  
- **Local testing** before pushing to CI

### For Teams
- **Consistent policies** across all team members
- **Prevent costly mistakes** from reaching production
- **Compliance reporting** for finance and governance

### For Organizations
- **Cost control** through automated enforcement
- **Risk mitigation** by blocking unauthorized models
- **Audit trails** with detailed violation reports

## 🚀 Next Steps

1. **Customize the policy** rules for your specific needs
2. **Add environment-specific** policies (dev vs prod)
3. **Integrate with Slack** for team notifications
4. **Set up dashboards** to track compliance over time
5. **Expand to other** log formats and services

## 🆘 Troubleshooting

### Policy not loading
```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('policies/budget.yaml'))"
```

### No violations found when expected
```bash
# Check log format
head -n 1 logs/your-file.jsonl | jq .

# Test a single rule
crashlens policy-check policies/budget.yaml logs/your-file.jsonl
```

### Workflow not triggering
- Ensure `.jsonl` files are being modified in your commits
- Check the `paths` filter in the workflow file
- Look at the Actions logs for detailed error messages

---

**💡 Pro Tip**: Start with `action: "warn"` for new rules, then upgrade to `action: "fail"` once your team is comfortable with the policy.

**🎉 Success**: Once this is working, you'll have automated cost governance for all your LLM usage!
