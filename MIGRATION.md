# Migration Guide: policy-check → guard

## 🚨 Breaking Change Notice

**Effective:** v1.0.0  
**Date:** January 9, 2025

The `policy-check` command has been **completely removed** and replaced with the unified `guard` command. This is a **breaking change** requiring action from all users.

---

## 📋 Quick Migration Checklist

- [ ] Update all CLI commands from `policy-check` to `guard`
- [ ] Migrate rule files from simple format to nested `if:` format
- [ ] Update CI/CD pipelines and workflows
- [ ] Update documentation and runbooks
- [ ] Test migrated rules with `guard`
- [ ] Update team knowledge base and training materials

---

## 🔄 Command Migration

### Basic Command Structure

**OLD (policy-check):**
```bash
crashlens policy-check logs.jsonl --policy-file rules.yaml --output json
```

**NEW (guard):**
```bash
crashlens guard logs.jsonl --rules rules.yaml --output json
```

### Flag Mappings

| Old Flag | New Flag | Notes |
|----------|----------|-------|
| `--policy-file` | `--rules` | Main rules file |
| `--policy-template` | `--policy-template` | ✅ Same (templates supported) |
| `--output` | `--output` | ✅ Same (json/markdown/slack) |
| `--fail-on-violations` | `--fail-on-violations` | ✅ Same (CI enforcement) |
| `--pii-strip` | `--pii-strip` | ✅ Same (PII removal) |
| `--summary-only` | `--summary-only` | ✅ Same (suppress trace IDs) |
| `--verbose` | `--verbose` | ✅ Same (debug output) |
| `--config` | `--config` | ✅ Same (model pricing) |

### Environment Variables

| Old Variable | New Variable | Notes |
|--------------|--------------|-------|
| `POLICY_CHECK_ENFORCE` | `GUARD_ENFORCE` | CI enforcement toggle |
| `CRASHLENS_QUIET` | `CRASHLENS_QUIET` | ✅ Same (suppress output) |

---

## 📝 Rule File Migration

### Rule Syntax Changes

The most significant change is the **rule condition format**. The old "flat" format with `if_*` fields is replaced with a nested `if:` block.

### Simple Condition

**OLD (policy-check):**
```yaml
rules:
  - id: HIGH_COST
    description: "Detect expensive calls"
    if_cost_gt: 1.0
    action: fail
    severity: fatal
```

**NEW (guard):**
```yaml
rules:
  - id: HIGH_COST
    description: "Detect expensive calls"
    if:
      cost: {'>': 1.0}
    action: fail_ci
    severity: fatal
```

### Multiple Conditions (AND Logic)

**OLD (policy-check):**
```yaml
rules:
  - id: EXPENSIVE_GPT4
    description: "GPT-4 with high tokens"
    if_model: "gpt-4"
    if_tokens_gt: 2000
    action: fail
    severity: fatal
```

**NEW (guard):**
```yaml
rules:
  - id: EXPENSIVE_GPT4
    description: "GPT-4 with high tokens"
    if:
      and:
        - input.model: "gpt-4"
        - usage.prompt_tokens: {'>': 2000}
    action: fail_ci
    severity: fatal
```

### Alternative Conditions (OR Logic)

**OLD (policy-check - NOT SUPPORTED):**
```yaml
# Not possible in old format
```

**NEW (guard):**
```yaml
rules:
  - id: PREMIUM_MODELS
    description: "Any premium model"
    if:
      input.model:
        in: ['gpt-4o', 'claude-3-opus', 'gemini-ultra']
    action: warn
    severity: warn
```

### Exclusions (NOT Logic)

**OLD (policy-check - NOT SUPPORTED):**
```yaml
# Not possible in old format
```

**NEW (guard):**
```yaml
rules:
  - id: NON_STANDARD
    description: "Non-standard models"
    if:
      not:
        input.model: 'gpt-3.5-turbo'
    action: warn
    severity: warn
```

### Nested Fields

**OLD (policy-check):**
```yaml
rules:
  - id: METADATA_CHECK
    description: "Check team metadata"
    if_metadata_team: "production"
    action: warn
    severity: warn
```

**NEW (guard):**
```yaml
rules:
  - id: METADATA_CHECK
    description: "Check team metadata"
    if:
      metadata.team: "production"
    action: warn
    severity: warn
```

---

## 🎯 Complete Migration Examples

### Example 1: Token Limit Policy

**OLD:**
```yaml
version: 1
rules:
  - id: TOKEN_LIMIT
    description: "Block high token usage"
    if_tokens_gt: 5000
    action: fail
    severity: critical
    suggestion: "Use lower token limit or chunking"
```

**NEW:**
```yaml
version: 1
rules:
  - id: TOKEN_LIMIT
    description: "Block high token usage"
    if:
      usage.prompt_tokens: {'>': 5000}
    action: fail_ci
    severity: fatal
    suggestion: "Use lower token limit or chunking"
```

### Example 2: Model Cost Policy

**OLD:**
```yaml
version: 1
rules:
  - id: COST_CONTROL
    description: "Prevent expensive calls"
    if_model: "gpt-4"
    if_cost_gt: 1.0
    action: fail
    severity: high
```

**NEW:**
```yaml
version: 1
rules:
  - id: COST_CONTROL
    description: "Prevent expensive calls"
    if:
      and:
        - input.model: "gpt-4"
        - cost: {'>': 1.0}
    action: fail_ci
    severity: fatal
```

### Example 3: Fallback Detection

**OLD:**
```yaml
version: 1
rules:
  - id: FALLBACK_ALERT
    description: "Alert on fallback usage"
    if_fallback_triggered: true
    action: warn
    severity: medium
```

**NEW:**
```yaml
version: 1
rules:
  - id: FALLBACK_ALERT
    description: "Alert on fallback usage"
    if:
      metadata.fallback_triggered: true
    action: warn
    severity: warn
```

### Example 4: Complex Multi-Condition Rule

**OLD (policy-check - IMPOSSIBLE):**
```yaml
# Complex boolean logic not supported
```

**NEW (guard - FULLY SUPPORTED):**
```yaml
rules:
  - id: PRODUCTION_ALERT
    description: "High-cost production usage"
    if:
      and:
        - or:
            - input.model: 'gpt-4o'
            - input.model: 'claude-3-opus'
        - usage.prompt_tokens: {'>': 1000}
        - not:
            metadata.route: 'cache-hit'
        - metadata.env: 'production'
    action: fail_ci
    severity: fatal
    suggestion: "Use caching or lower-cost models"
```

---

## 🔧 CI/CD Pipeline Migration

### GitHub Actions

**OLD:**
```yaml
- name: Check Policy Violations
  run: |
    crashlens policy-check logs.jsonl \
      --policy-file .crashlens/policy.yaml \
      --fail-on-violations \
      --output json
```

**NEW:**
```yaml
- name: Guard Policy Check
  run: |
    crashlens guard logs.jsonl \
      --rules .crashlens/rules.yaml \
      --fail-on-violations \
      --output json
  env:
    GUARD_ENFORCE: 'true'
```

### Jenkins

**OLD:**
```groovy
stage('Policy Check') {
    steps {
        sh 'crashlens policy-check logs.jsonl --policy-file policy.yaml --fail-on-violations'
    }
}
```

**NEW:**
```groovy
stage('Guard Check') {
    steps {
        sh 'crashlens guard logs.jsonl --rules rules.yaml --fail-on-violations'
    }
}
```

### GitLab CI

**OLD:**
```yaml
policy_check:
  script:
    - crashlens policy-check logs.jsonl --policy-file policy.yaml --fail-on-violations
```

**NEW:**
```yaml
guard_check:
  script:
    - crashlens guard logs.jsonl --rules rules.yaml --fail-on-violations
```

---

## 🛡️ Fail-Safe Enforcement

The `guard` command supports a fail-safe environment variable for easy on/off control:

### Enable Enforcement
```bash
export GUARD_ENFORCE=true
crashlens guard logs.jsonl --rules rules.yaml --fail-on-violations
```

### Disable Enforcement (Emergency)
```bash
export GUARD_ENFORCE=false
crashlens guard logs.jsonl --rules rules.yaml --fail-on-violations
# Will run but NOT fail CI even if violations found
```

### In CI/CD
```yaml
env:
  GUARD_ENFORCE: ${{ secrets.GUARD_ENFORCE }}  # Set to 'false' to disable
```

---

## 🔍 Field Name Mappings

### Top-Level Fields

| Old Field | New Field | Notes |
|-----------|-----------|-------|
| `if_model` | `input.model` | Nested under `input` |
| `if_tokens` | `usage.prompt_tokens` | Nested under `usage` |
| `if_tokens_gt` | `usage.prompt_tokens: {'>': X}` | Operator format |
| `if_cost` | `cost` | ✅ Same (top-level) |
| `if_cost_gt` | `cost: {'>': X}` | Operator format |
| `if_fallback_triggered` | `metadata.fallback_triggered` | Nested under `metadata` |

### Operators

| Old Format | New Format | Example |
|------------|------------|---------|
| `if_tokens_gt: 1000` | `usage.prompt_tokens: {'>': 1000}` | Greater than |
| `if_tokens_lt: 100` | `usage.prompt_tokens: {'<': 100}` | Less than |
| `if_cost_gte: 0.5` | `cost: {'>=': 0.5}` | Greater or equal |
| `if_cost_lte: 2.0` | `cost: {'<=': 2.0}` | Less or equal |
| `if_model: 'gpt-4'` | `input.model: 'gpt-4'` | Equality |
| `if_model_not: 'gpt-3.5'` | `not: {input.model: 'gpt-3.5'}` | Negation |

### Boolean Operators

| Operator | Syntax | Example |
|----------|--------|---------|
| AND | `and: [...]` | Multiple conditions |
| OR | `or: [...]` or `field: [...]` | Alternatives |
| NOT | `not: {...}` | Negation |
| IN | `field: {in: [...]}` | List membership |

---

## 🧪 Testing Your Migration

### Step 1: Validate Rule Syntax
```bash
# Test your migrated rules
crashlens guard sample-logs/demo-logs.jsonl \
  --rules your-migrated-rules.yaml \
  --output json \
  --verbose
```

### Step 2: Compare Outputs
```bash
# Run on same logs to verify behavior matches
crashlens guard logs.jsonl --rules new-rules.yaml --output json > new-output.json

# Check for expected violations
jq '.summary.violations' new-output.json
```

### Step 3: Dry Run in CI
```bash
# Test without enforcement
export GUARD_ENFORCE=false
crashlens guard logs.jsonl --rules rules.yaml --fail-on-violations
```

---

## 📊 What You Gain

### New Features in `guard`

1. **Boolean Logic:** AND, OR, NOT operators
2. **IN Operator:** Efficiently check multiple values (50x faster than OR)
3. **Nested Fields:** Use dot notation (`metadata.team`)
4. **Better Performance:** Constant memory, optimized evaluation
5. **Unified Engine:** Single code path, fewer bugs
6. **Better Errors:** Clear validation messages

### Breaking Changes

1. **Rule syntax** changed from flat to nested
2. **Field names** use dot notation for nested fields
3. **Operators** use explicit dict format (`{'>': 1000}`)
4. **Command name** changed from `policy-check` to `guard`

---

## 🆘 Troubleshooting

### Error: "Unknown command policy-check"
**Cause:** You're using v1.0+ which removed `policy-check`

**Solution:** Replace all instances with `guard`:
```bash
# Find all references
grep -r "policy-check" .

# Replace (example)
sed -i 's/policy-check/guard/g' .github/workflows/*.yml
```

### Error: "Invalid rules.yaml schema"
**Cause:** Using old flat syntax with new `guard` command

**Solution:** Migrate rules to nested format (see examples above)

### Error: "Field 'if_tokens_gt' not recognized"
**Cause:** Old syntax not supported in `guard`

**Solution:** Convert to new operator format:
```yaml
# OLD: if_tokens_gt: 1000
# NEW:
if:
  usage.prompt_tokens: {'>': 1000}
```

### Error: "action: fail not recognized"
**Cause:** Action values changed

**Solution:** Use new action names:
```yaml
# OLD: action: fail
# NEW: action: fail_ci
```

---

## 📚 Additional Resources

- **User Manual:** `docs/USER_MANUAL.md`
- **Guard Documentation:** `docs/GUARD.md`
- **Boolean Logic Guide:** `docs/BOOLEAN_LOGIC_IMPLEMENTATION.md`
- **Examples:** `examples/` directory
- **Policy Templates:** `policies/` directory

---

## 💡 Migration Script (Optional)

For bulk migration, use this Python script:

```python
#!/usr/bin/env python3
"""
Semi-automated migration script for policy-check → guard rules.

WARNING: This is a best-effort converter. ALWAYS manually review output!
"""
import yaml
import sys
from pathlib import Path

def migrate_rule(old_rule):
    """Convert old flat format to new nested format."""
    new_rule = {
        'id': old_rule['id'],
        'description': old_rule.get('description', ''),
        'if': {},
        'action': old_rule.get('action', 'warn').replace('fail', 'fail_ci'),
        'severity': old_rule.get('severity', 'warn').replace('high', 'fatal').replace('medium', 'warn').replace('low', 'warn'),
    }
    
    if 'suggestion' in old_rule:
        new_rule['suggestion'] = old_rule['suggestion']
    
    # Migrate conditions
    conditions = []
    for key, value in old_rule.items():
        if key.startswith('if_'):
            field = key.replace('if_', '')
            
            # Handle operators
            if field.endswith('_gt'):
                field = field.replace('_gt', '')
                conditions.append({f'{field}': {'>': value}})
            elif field.endswith('_lt'):
                field = field.replace('_lt', '')
                conditions.append({f'{field}': {'<': value}})
            elif field.endswith('_gte'):
                field = field.replace('_gte', '')
                conditions.append({f'{field}': {'>=': value}})
            elif field.endswith('_lte'):
                field = field.replace('_lte', '')
                conditions.append({f'{field}': {'<=': value}})
            else:
                # Map old field names to new nested format
                if field == 'model':
                    field = 'input.model'
                elif field == 'tokens':
                    field = 'usage.prompt_tokens'
                elif field.startswith('metadata_'):
                    field = field.replace('metadata_', 'metadata.')
                
                conditions.append({field: value})
    
    # Construct if block
    if len(conditions) == 1:
        new_rule['if'] = conditions[0]
    elif len(conditions) > 1:
        new_rule['if'] = {'and': conditions}
    
    return new_rule

def migrate_file(input_path, output_path):
    """Migrate entire rules file."""
    with open(input_path) as f:
        old_rules = yaml.safe_load(f)
    
    new_rules = {
        'version': old_rules.get('version', 1),
        'rules': [migrate_rule(r) for r in old_rules.get('rules', [])]
    }
    
    with open(output_path, 'w') as f:
        yaml.dump(new_rules, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ Migrated {len(new_rules['rules'])} rules")
    print(f"📝 Output: {output_path}")
    print(f"⚠️  IMPORTANT: Manually review {output_path} before using!")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python migrate_rules.py <old-rules.yaml> <new-rules.yaml>")
        sys.exit(1)
    
    migrate_file(sys.argv[1], sys.argv[2])
```

**Usage:**
```bash
python migrate_rules.py old-policy.yaml new-rules.yaml
# Review new-rules.yaml carefully!
# Test with: crashlens guard logs.jsonl --rules new-rules.yaml
```

---

## 📞 Support

**Questions or Issues?**
- Open an issue: https://github.com/Crashlens/crashlens/issues
- Documentation: `docs/` directory
- Examples: `examples/` directory

---

**Last Updated:** January 9, 2025  
**Version:** 1.0.0  
**Migration Status:** Required for all users
