# 🚀 CrashLens Non-Interactive Quick Reference

## Command
```bash
crashlens init --non-interactive [--dry-run-workflow]
```

## Environment Variables
| Variable | Default | Values |
|----------|---------|--------|
| `CRASHLENS_TEMPLATES` | `all` | Template names or `all` |
| `CRASHLENS_SEVERITY` | `high` | `low`, `medium`, `high`, `critical` |
| `CRASHLENS_FAIL_ON_VIOLATIONS` | `True` | `true`, `false`, `1`, `0` |
| `CRASHLENS_LOGS_SOURCE` | `local` | `local`, `langfuse`, `helicone`, `other` |
| `CRASHLENS_CREATE_WORKFLOW` | `False` | `true`, `false`, `1`, `0` |

## PowerShell Examples
```powershell
# Single line
$env:CRASHLENS_TEMPLATES="retry-loop-prevention"; $env:CRASHLENS_SEVERITY="medium"; crashlens init --non-interactive

# Multi-line
$env:CRASHLENS_TEMPLATES="all"
$env:CRASHLENS_SEVERITY="high"
$env:CRASHLENS_FAIL_ON_VIOLATIONS="true"
crashlens init --non-interactive

# Check variables
echo "Templates: $env:CRASHLENS_TEMPLATES"

# Clear variables
Remove-Item Env:\CRASHLENS_TEMPLATES -ErrorAction SilentlyContinue
```

## Bash Examples
```bash
# Single line
CRASHLENS_TEMPLATES="retry-loop-prevention" CRASHLENS_SEVERITY="medium" crashlens init --non-interactive

# Export
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="high"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
crashlens init --non-interactive

# Check variables
echo "Templates: $CRASHLENS_TEMPLATES"

# Clear variables
unset CRASHLENS_TEMPLATES
```

## CI/CD Examples

### GitHub Actions
```yaml
- name: Configure CrashLens
  env:
    CRASHLENS_TEMPLATES: "retry-loop-prevention"
    CRASHLENS_SEVERITY: "high"
    CRASHLENS_FAIL_ON_VIOLATIONS: "true"
  run: crashlens init --non-interactive
```

### Docker
```dockerfile
ENV CRASHLENS_TEMPLATES="all"
ENV CRASHLENS_SEVERITY="high"
RUN crashlens init --non-interactive
```

## Policy Templates
- `retry-loop-prevention`
- `model-overkill-detection`
- `chain-recursion-prevention`
- `fallback-storm-detection`
- `budget-protection`
- `rate-limit-management`
- `prompt-optimization`
- `error-handling-efficiency`
- `context-window-optimization`
- `batch-processing-efficiency`
- `all`

## Output
```
🤖 Running in non-interactive mode...
📋 Policy templates: retry-loop-prevention
📊 Severity threshold: high
🚨 Fail on violations: True
📁 Logs source: local
⚙️  Create workflow: False
✅ Configuration saved at .crashlens\config.yaml
```

## Generated Files
- `.crashlens/config.yaml` - Configuration file
- `.github/workflows/crashlens.yml` - GitHub Actions workflow (if enabled)
