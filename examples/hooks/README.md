# CrashLens Pre-commit Hook

Enforce CrashLens Guard policies before commits reach your repository using [pre-commit](https://pre-commit.com/) hooks.

## Quick Start

### 1. Install pre-commit

```bash
# Using pip
pip install pre-commit

# Using Poetry (if using CrashLens dev environment)
poetry add --group dev pre-commit
```

### 2. Install the hooks

From your repository root:

```bash
pre-commit install
```

### 3. Configure rules

Create or use existing rules file:

```bash
# Use default locations (auto-discovered)
# - .crashlens/rules.yaml
# - .github/crashlens/rules.yaml  
# - rules.yaml

# Or set custom path via environment variable
export CRASHLENS_RULES=".crashlens/rules.yaml"
```

### 4. Commit as usual

The hook will automatically run on staged JSONL files:

```bash
git add logs/my-logs.jsonl
git commit -m "Add new logs"

# Hook runs automatically:
# ℹ️  CrashLens Guard - Pre-commit Hook
# ℹ️  Checking 1 JSONL file(s)...
# ✅ Guard passed: No policy violations found
```

## Configuration

### Environment Variables

Configure the hook behavior via environment variables:

```bash
# Path to rules file (default: auto-discover)
export CRASHLENS_RULES=".crashlens/rules.yaml"

# Minimum severity to fail commit (default: error)
export CRASHLENS_SEVERITY="warn"  # Options: warn, error, fatal

# Output format (default: text)
export CRASHLENS_OUTPUT="json"  # Options: text, json, md, html

# Dry-run mode - never fail commits (default: false)
export CRASHLENS_DRY_RUN="true"
```

### Pre-commit Configuration

Edit `.pre-commit-config.yaml` to customize:

```yaml
repos:
  - repo: local
    hooks:
      - id: crashlens-guard
        name: CrashLens Guard - Policy Enforcement
        entry: bash examples/hooks/crashlens-pre-commit.sh
        language: system
        files: '\.jsonl$'
        pass_filenames: true
        verbose: true
```

## Usage Examples

### Basic Usage

```bash
# Normal commit (hook runs automatically)
git commit -m "feat: add logs"

# Bypass hook temporarily
git commit --no-verify -m "feat: bypass guard"

# Run manually on all files
pre-commit run crashlens-guard --all-files
```

### Run on Specific Directories

Add directory-specific hooks in `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: crashlens-guard-logs
      name: CrashLens Guard - Logs Directory
      entry: crashlens guard
      language: system
      args:
        - 'logs/'
        - '--rules'
        - '.crashlens/rules.yaml'
        - '--fail-on-violations'
      files: 'logs/.*\.jsonl$'
```

### Staged Files Only

Check only staged files (default behavior):

```yaml
- repo: local
  hooks:
    - id: crashlens-guard-staged
      name: CrashLens Guard - Staged Only
      entry: bash examples/hooks/crashlens-pre-commit.sh --staged-only
      language: system
      files: '\.jsonl$'
      pass_filenames: false
```

### Multiple Severity Levels

Run different checks at different severity levels:

```yaml
repos:
  - repo: local
    hooks:
      # Fatal violations block commits
      - id: crashlens-guard-fatal
        name: CrashLens Guard - Fatal Violations
        entry: crashlens guard
        args:
          - '--severity'
          - 'fatal'
          - '--fail-on-violations'
        language: system
        files: '\.jsonl$'
        
      # Warnings don't block
      - id: crashlens-guard-warn
        name: CrashLens Guard - Warnings
        entry: crashlens guard
        args:
          - '--severity'
          - 'warn'
          - '--dry-run'  # Never fail
        language: system
        files: '\.jsonl$'
```

## Hook Behavior

### Exit Codes

- **0**: No violations or all below severity threshold (commit proceeds)
- **1**: Violations found at/above severity threshold (commit blocked)

### What Gets Checked

By default, the hook checks:
- All staged JSONL files (files matching `*.jsonl`)
- Files added, modified, or copied (`--diff-filter=ACM`)
- Uses rules from auto-discovered location or `CRASHLENS_RULES`

### Suppressing Violations

If you need to commit despite violations:

```bash
# Temporary bypass (use sparingly)
git commit --no-verify

# Suppress specific rules
git add logs/my-logs.jsonl
CRASHLENS_RULES="rules-no-RL001.yaml" git commit -m "commit with suppression"

# Or use guard --suppress flag
crashlens guard logs/my-logs.jsonl --suppress RL001,RL002
```

## Troubleshooting

### Hook Not Running

```bash
# Re-install hooks
pre-commit uninstall
pre-commit install

# Verify installation
pre-commit run --all-files
```

### Command Not Found

```bash
# Ensure crashlens is installed
which crashlens  # Unix/Mac
where crashlens  # Windows

# Install if missing
poetry install  # If using Poetry
pip install crashlens  # If using pip
```

### Rules Not Found

```bash
# Check auto-discovery paths
ls -la .crashlens/rules.yaml
ls -la .github/crashlens/rules.yaml
ls -la rules.yaml

# Or specify explicitly
export CRASHLENS_RULES="/path/to/rules.yaml"
```

### Permission Denied (Bash Script)

```bash
# Make script executable
chmod +x examples/hooks/crashlens-pre-commit.sh
```

## Advanced Configuration

### Skip Hook for Specific Commits

```bash
# Skip all hooks
SKIP=crashlens-guard git commit -m "skip guard"

# Skip specific hook by ID
SKIP=crashlens-guard-logs git commit -m "skip logs check"
```

### CI/CD Integration

Pre-commit hooks can also run in CI:

```yaml
# .github/workflows/ci.yml
- name: Run pre-commit hooks
  run: |
    pip install pre-commit
    pre-commit run --all-files
```

### Custom Wrapper Script

Create your own wrapper for project-specific logic:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Load project environment
source .env

# Run crashlens with custom config
crashlens guard \
  --rules "$PROJECT_RULES" \
  --severity "$PROJECT_SEVERITY" \
  --fail-on-violations
```

## See Also

- [Pre-commit Documentation](https://pre-commit.com/)
- [CrashLens Guard Documentation](../docs/USER_MANUAL.md)
- [Rule Writing Guide](../policies/README.md)
- [GitHub Integration](../docs/SLACK_INTEGRATION.md)
