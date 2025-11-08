# 🔄 Migration Guide: `guard` → `policy-check`

**Effective Version:** v3.0.0  
**Deprecation Status:** `guard` command is now a deprecated alias  
**Timeline:** Full removal planned for v3.1.0 (Q2 2025)

---

## 📋 TL;DR - What Changed?

| Aspect | Old (`guard`) | New (`policy-check`) |
|--------|---------------|----------------------|
| **Command** | `crashlens guard` | `crashlens policy-check` |
| **CLI Alias** | Primary command | Deprecated alias (still works with warning) |
| **Artifact Prefix** | `guard-*.json` | `policy-*.json` |
| **PII Redaction Format** | `[REDACTED-EMAIL]` (hyphen) | `[REDACTED_EMAIL]` (underscore) |
| **Markdown Header** | "Guard Violations Report" | "Policy Violations Report" |
| **Engine** | Legacy guard evaluator | Unified PolicyEngine |
| **Output Structure** | Guard-specific format | Unified policy format |

---

## 🚀 Quick Migration Examples

### Basic Command Migration

**Before (v2.x):**
```bash
crashlens guard logs.jsonl --policy-template all
```

**After (v3.0+):**
```bash
crashlens policy-check logs.jsonl --policy-template all
```

**Compatibility (v3.0 only):**
```bash
# Still works with deprecation warning
crashlens guard logs.jsonl --policy-template all
# Output: ⚠️  DEPRECATION WARNING: 'guard' is deprecated. Use 'policy-check' instead.
```

---

## 🔧 CLI Options Mapping

### Core Options (Unchanged)

| Option | Description | Compatibility |
|--------|-------------|---------------|
| `--policy-template` | Built-in policy templates | ✅ Identical |
| `--policy-file` | Custom policy YAML file | ✅ Identical |
| `--fail-on-violations` | Exit code 1 on violations | ✅ Identical |
| `--severity-threshold` | Filter by severity (low/medium/high/critical) | ✅ Identical |
| `--format` | Output format (markdown/json/slack) | ✅ Identical |

### Removed Options (v3.0)

| Option | Status | Alternative |
|--------|--------|-------------|
| `--suppress` | ❌ Removed | Use policy YAML `enabled: false` for specific rules |
| `--streaming` | ❌ Removed | Use unified streaming in `scan` command |
| `--artifacts-dir` | ❌ Removed | Artifacts auto-saved to `policy-violations/` |

### New Options (v3.0)

| Option | Description | Example |
|--------|-------------|---------|
| `--output` | Specify output file path | `--output results.md` |
| `--quiet` | Suppress deprecation warnings | `--quiet` |
| `--config` | Custom config file | `--config my-config.yaml` |

---

## 📁 Artifact Output Changes

### File Naming

**Before (v2.x):**
```
policy-violations/
├── guard-20250115-103045.json
├── guard-20250115-110230.json
└── traces/
    ├── guard-trace-abc123.json
    └── guard-trace-def456.json
```

**After (v3.0+):**
```
policy-violations/
├── policy-20250115-103045.json
├── policy-20250115-110230.json
└── traces/
    ├── policy-trace-abc123.json
    └── policy-trace-def456.json
```

### Backwards Compatibility

**If you rely on `guard-*.json` filenames in scripts:**
```bash
# Update your scripts
# Before:
ls policy-violations/guard-*.json

# After:
ls policy-violations/policy-*.json

# Transition period workaround (v3.0 only):
ls policy-violations/{guard,policy}-*.json  # Accepts both patterns
```

---

## 📊 Output Format Differences

### Markdown Report Header

**Before (v2.x):**
```markdown
# 🛡️ Guard Violations Report
Generated: 2025-01-15 10:30:45
```

**After (v3.0+):**
```markdown
# 🛡️ Policy Violations Report
Generated: 2025-01-15 10:30:45
```

### PII Redaction Format

**Before (v2.x):**
```json
{
  "prompt": "Send invoice to user-email@example.com",
  "sanitized_prompt": "Send invoice to [REDACTED-EMAIL]"
}
```

**After (v3.0+):**
```json
{
  "prompt": "Send invoice to user-email@example.com",
  "sanitized_prompt": "Send invoice to [REDACTED_EMAIL]"
}
```

**Impact:** Scripts parsing PII redacted strings must update regex:
```python
# Before
pattern = r'\[REDACTED-EMAIL\]'  # Hyphen

# After
pattern = r'\[REDACTED_EMAIL\]'  # Underscore
```

### JSON Schema Changes

**Before (v2.x - Guard Format):**
```json
{
  "violations": [
    {
      "rule_id": "RL001",
      "guard_severity": "high",
      "guard_action": "fail",
      "description": "Excessive retry count"
    }
  ]
}
```

**After (v3.0+ - Unified Format):**
```json
{
  "violations": [
    {
      "rule_id": "RL001",
      "severity": "high",
      "action": "fail",
      "description": "Excessive retry count",
      "policy_engine": "unified",
      "detection_timestamp": "2025-01-15T10:30:45Z"
    }
  ]
}
```

**Breaking Changes:**
- `guard_severity` → `severity`
- `guard_action` → `action`
- Added: `policy_engine` field
- Added: `detection_timestamp` field

---

## 🔄 Policy Rule Format (YAML)

### Rule Syntax (Unchanged)

Both `guard` and `policy-check` use the **same YAML format**:

```yaml
version: 1
rules:
  - id: excessive_retries
    description: "Block traces with >3 retries"
    match:
      retry_count: ">3"
    action: fail
    severity: critical
    suggestion: "Implement exponential backoff"
```

**No migration needed** for policy YAML files.

---

## 🐳 CI/CD Pipeline Updates

### GitHub Actions

**Before (v2.x):**
```yaml
- name: Run CrashLens Guard
  run: |
    crashlens guard logs.jsonl \
      --policy-template all \
      --fail-on-violations
```

**After (v3.0+):**
```yaml
- name: Run CrashLens Policy Check
  run: |
    crashlens policy-check logs.jsonl \
      --policy-template all \
      --fail-on-violations
```

### Pre-commit Hooks

**Before (v2.x - `.pre-commit-config.yaml`):**
```yaml
repos:
  - repo: local
    hooks:
      - id: crashlens-guard
        name: CrashLens Guard - Policy Enforcement
        entry: crashlens guard
        language: system
        files: '\.jsonl$'
```

**After (v3.0+):**
```yaml
repos:
  - repo: local
    hooks:
      - id: crashlens-policy-check
        name: CrashLens Policy Enforcement
        entry: crashlens policy-check
        language: system
        files: '\.jsonl$'
```

### Docker/Container Workflows

**Before (v2.x):**
```dockerfile
RUN crashlens guard /logs/*.jsonl --policy-template all
```

**After (v3.0+):**
```dockerfile
RUN crashlens policy-check /logs/*.jsonl --policy-template all
```

---

## 🧪 Testing & Validation

### Test Suite Updates

**If you have integration tests:**

```python
# Before (v2.x)
from click.testing import CliRunner
from crashlens.cli import cli

runner = CliRunner()
result = runner.invoke(cli, ['guard', 'logs.jsonl', '--policy-template', 'all'])
assert result.exit_code == 0
assert 'guard-' in result.output  # Artifact name

# After (v3.0+)
result = runner.invoke(cli, ['policy-check', 'logs.jsonl', '--policy-template', 'all'])
assert result.exit_code == 0
assert 'policy-' in result.output  # Updated artifact name
```

### Automated Migration Script

**Run this to update all `guard` references in your codebase:**

```bash
# Find all guard command usages
grep -r "crashlens guard" . --include="*.sh" --include="*.yml" --include="*.yaml"

# Automated replacement (use with caution)
find . -type f \( -name "*.sh" -o -name "*.yml" -o -name "*.yaml" \) \
  -exec sed -i 's/crashlens guard/crashlens policy-check/g' {} +

# Verify changes
git diff
```

---

## ⏱️ Deprecation Timeline

| Version | Status | Behavior |
|---------|--------|----------|
| **v2.9.x** (Current) | `guard` is primary | ✅ Fully supported, no warnings |
| **v3.0.0** (2025-01) | `guard` is alias | ⚠️ Works with deprecation warning |
| **v3.1.0** (2025-04) | `guard` removed | ❌ Command not found error |

### How to Suppress Warnings (v3.0 only)

**If you need time to migrate:**
```bash
# Option 1: Use --quiet flag
crashlens guard logs.jsonl --quiet

# Option 2: Set environment variable
export CRASHLENS_QUIET=1
crashlens guard logs.jsonl

# Option 3: Redirect stderr
crashlens guard logs.jsonl 2>/dev/null
```

---

## 🛠️ Troubleshooting

### Issue: "Command 'guard' not found" (v3.1+)

**Error Message:**
```
Error: No such command 'guard'.
Did you mean 'policy-check'?
```

**Solution:**
Update all scripts to use `policy-check`:
```bash
crashlens policy-check logs.jsonl --policy-template all
```

---

### Issue: Scripts break with "guard-*.json not found"

**Error:**
```bash
ls: cannot access 'policy-violations/guard-*.json': No such file or directory
```

**Solution:**
Update filename patterns in scripts:
```bash
# Before
for file in policy-violations/guard-*.json; do
  echo "Processing $file"
done

# After
for file in policy-violations/policy-*.json; do
  echo "Processing $file"
done
```

---

### Issue: PII regex patterns fail

**Error:**
```python
# Pattern doesn't match new format
assert re.search(r'\[REDACTED-EMAIL\]', output)  # Fails
```

**Solution:**
Update regex to use underscore:
```python
assert re.search(r'\[REDACTED_EMAIL\]', output)  # Succeeds
```

---

## 📚 Additional Resources

- **Command Reference**: [`docs/COMMAND-REFERENCE.md`](docs/COMMAND-REFERENCE.md)
- **Policy Engine Documentation**: [`docs/GUARD.md`](docs/GUARD.md)
- **CI/CD Examples**: [`examples/ci-workflows/`](examples/ci-workflows/)
- **Policy Templates**: [`crashlens/policy/templates/`](crashlens/policy/templates/)

---

## ❓ FAQ

### Q: Why was `guard` deprecated?

**A:** The unified `PolicyEngine` consolidates all policy evaluation logic, making `guard` redundant. `policy-check` is the canonical name moving forward.

---

### Q: Will my existing policies still work?

**A:** Yes! Policy YAML format is unchanged. All existing `*.yaml` policy files work with both `guard` (v3.0) and `policy-check`.

---

### Q: Can I use both commands during transition?

**A:** In v3.0, yes. Both `guard` and `policy-check` work identically (with deprecation warning for `guard`). In v3.1+, only `policy-check` is supported.

---

### Q: Do I need to update my policy rules?

**A:** No. Policy YAML syntax is stable. Only CLI command names and output artifact names changed.

---

### Q: How do I update my CI/CD pipelines?

**A:** Replace `crashlens guard` with `crashlens policy-check` in all workflow files (`.github/workflows/*.yml`, `.gitlab-ci.yml`, etc.).

---

## 🤝 Need Help?

- **Report Issues**: [GitHub Issues](https://github.com/Crashlens/crashlens/issues)
- **Discussion**: [GitHub Discussions](https://github.com/Crashlens/crashlens/discussions)
- **Security**: [`SECURITY.md`](SECURITY.md)

---

**Last Updated:** January 2025 (v3.0.0 release)
