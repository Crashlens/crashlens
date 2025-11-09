# CrashLens Init Command

**Interactive project setup and configuration wizard**

---

## Table of Contents

1. [Overview](#overview)
2. [Interactive Mode](#interactive-mode)
3. [Non-Interactive Mode](#non-interactive-mode)
4. [Environment Variables](#environment-variables)
5. [GitHub Actions Generation](#github-actions-generation)
6. [Configuration Files Created](#configuration-files-created)
7. [Complete Examples](#complete-examples)
8. [Best Practices](#best-practices)

---

## Overview

The `init` command provides an **interactive setup wizard** to configure CrashLens for your project with zero manual configuration.

**Key Features**:
✅ **Interactive Wizard** - Step-by-step guided setup  
✅ **Non-Interactive Mode** - Automated setup for CI/CD  
✅ **Smart Defaults** - Sensible configuration out-of-the-box  
✅ **GitHub Actions** - Auto-generate workflow files  
✅ **Policy Templates** - Choose from built-in rule sets  
✅ **Environment Support** - Configure via env vars  
✅ **Zero Configuration** - Works immediately after setup  

**Syntax**:
```bash
crashlens init [OPTIONS]
```

**Quick Start**:
```bash
# Interactive setup (recommended for first-time users)
crashlens init

# Non-interactive (CI/CD automation)
crashlens init --non-interactive

# Preview workflow without writing
crashlens init --dry-run-workflow
```

---

## Interactive Mode

### Running the Wizard

**Default interactive setup**:

```bash
crashlens init
```

### Setup Flow

**The wizard walks through 5 key decisions**:

#### 1. Policy Templates

```
? Which policy templates would you like to use?

  [ ] retry-loop-prevention - Detect excessive retries
  [ ] model-overkill-detection - Flag expensive models on simple tasks
  [ ] fallback-chain-detector - Monitor fallback patterns
  [ ] budget-protection - Cost cap enforcement
  [ ] rate-limit-management - Rate limit detection
  [x] all - Use all templates (recommended)

Select: all
```

**Available templates**:
- `retry-loop-prevention`
- `model-overkill-detection`
- `fallback-chain-detector`
- `budget-protection`
- `rate-limit-management`
- `chain-recursion-prevention`
- `all` (recommended for comprehensive coverage)

#### 2. Severity Threshold

```
? What minimum severity level should trigger alerts?

  [ ] warn - All issues (verbose)
  [x] error - Medium and high severity (recommended)
  [ ] fatal - Only critical failures

Select: error
```

**Options**:
- `warn`: Catch everything (development)
- `error`: Balance (staging/production)
- `fatal`: Critical only (production)

#### 3. Fail on Violations

```
? Should CI/CD pipelines fail when violations are found?

  [x] Yes - Fail builds on violations (recommended for production)
  [ ] No - Report violations but don't fail builds

Select: Yes
```

**Recommendation**: Enable for production, disable for initial setup

#### 4. Logs Source

```
? Where do your LLM logs come from?

  [x] local - Local JSONL files
  [ ] langfuse - Langfuse API
  [ ] helicone - Helicone API
  [ ] other - Custom source

Select: local
```

**Options**:
- `local`: File-based logs
- `langfuse`: Langfuse platform integration
- `helicone`: Helicone proxy logs
- `other`: Custom log sources

#### 5. GitHub Actions Workflow

```
? Generate GitHub Actions workflow file?

  [x] Yes - Create .github/workflows/crashlens.yml
  [ ] No - Skip workflow generation

Select: Yes
```

### Interactive Output

**After completion**:

```
✅ CrashLens configuration complete!

Created files:
  📁 .crashlens/
     - rules.yaml (8 rules from selected templates)
     - config.yaml (project configuration)
  📁 .github/workflows/
     - crashlens.yml (CI/CD workflow)

Next steps:
  1. Review .crashlens/rules.yaml
  2. Add logs to your repository: logs/*.jsonl
  3. Run: crashlens guard logs/*.jsonl
  4. Commit .crashlens/ and .github/workflows/

📖 Documentation: https://github.com/Crashlens/crashlens
```

---

## Non-Interactive Mode

### Automated Setup

**For CI/CD pipelines and automation**:

```bash
# Use environment variables for all settings
crashlens init --non-interactive
```

### Environment Variable Configuration

**Required variables** (defaults shown):

```bash
# Policy templates
export CRASHLENS_TEMPLATES="all"

# Severity threshold
export CRASHLENS_SEVERITY="error"

# Fail on violations
export CRASHLENS_FAIL_ON_VIOLATIONS="true"

# Logs source
export CRASHLENS_LOGS_SOURCE="local"

# Create workflow
export CRASHLENS_CREATE_WORKFLOW="false"

# Run init
crashlens init --non-interactive
```

### Non-Interactive Examples

**Example 1: Minimal setup**:
```bash
export CRASHLENS_TEMPLATES="retry-loop-prevention,model-overkill-detection"
export CRASHLENS_SEVERITY="high"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"

crashlens init --non-interactive
```

**Example 2: Langfuse integration**:
```bash
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_LOGS_SOURCE="langfuse"
export CRASHLENS_CREATE_WORKFLOW="true"

crashlens init --non-interactive
```

**Example 3: Permissive (development)**:
```bash
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="warn"
export CRASHLENS_FAIL_ON_VIOLATIONS="false"

crashlens init --non-interactive
```

### Non-Interactive Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--non-interactive` | Flag | False | Skip prompts, use env vars |

---

## Environment Variables

### Complete Variable Reference

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `CRASHLENS_TEMPLATES` | Template names (comma-separated) or `all` | `all` | Policy templates to use |
| `CRASHLENS_SEVERITY` | `warn`, `error`, `fatal` | `error` | Minimum severity threshold |
| `CRASHLENS_FAIL_ON_VIOLATIONS` | `true`, `false` | `true` | Fail CI on violations |
| `CRASHLENS_LOGS_SOURCE` | `local`, `langfuse`, `helicone`, `other` | `local` | Log source type |
| `CRASHLENS_CREATE_WORKFLOW` | `true`, `false` | `false` | Generate GitHub Actions workflow |

### Template Names

**Available template identifiers**:
- `retry-loop-prevention`
- `model-overkill-detection`
- `fallback-chain-detector`
- `budget-protection`
- `rate-limit-management`
- `chain-recursion-prevention`
- `all` (use all templates)

**Comma-separated for multiple**:
```bash
export CRASHLENS_TEMPLATES="retry-loop-prevention,model-overkill-detection,budget-protection"
```

### Environment Variable Examples

**Development setup**:
```bash
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="warn"
export CRASHLENS_FAIL_ON_VIOLATIONS="false"
export CRASHLENS_LOGS_SOURCE="local"
export CRASHLENS_CREATE_WORKFLOW="false"

crashlens init --non-interactive
```

**Production setup**:
```bash
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="fatal"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
export CRASHLENS_LOGS_SOURCE="langfuse"
export CRASHLENS_CREATE_WORKFLOW="true"

crashlens init --non-interactive
```

**Staging setup**:
```bash
export CRASHLENS_TEMPLATES="retry-loop-prevention,model-overkill-detection"
export CRASHLENS_SEVERITY="error"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
export CRASHLENS_LOGS_SOURCE="local"
export CRASHLENS_CREATE_WORKFLOW="true"

crashlens init --non-interactive
```

---

## GitHub Actions Generation

### Workflow File Creation

**Automatically generates `.github/workflows/crashlens.yml`**:

```bash
# Enable workflow generation
crashlens init  # Select "Yes" when prompted

# Or with environment variable
export CRASHLENS_CREATE_WORKFLOW="true"
crashlens init --non-interactive
```

### Generated Workflow Structure

**Example workflow** (for local logs):

```yaml
name: CrashLens Policy Check

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  guard:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install CrashLens
        run: pip install crashlens
      
      - name: Run guard
        run: |
          crashlens guard logs/*.jsonl \
            --rules .crashlens/rules.yaml \
            --fail-on-violations \
            --severity error \
            --output json \
            --report-path crashlens-report.json
      
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: crashlens-report
          path: crashlens-report.json
```

### Workflow Variations

**For Langfuse source**:

```yaml
- name: Fetch logs from Langfuse
  env:
    LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
    LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
  run: crashlens fetch-langfuse --hours-back 24 --output logs.jsonl

- name: Run guard
  run: crashlens guard logs.jsonl --fail-on-violations
```

**For Helicone source**:

```yaml
- name: Fetch logs from Helicone
  env:
    HELICONE_API_KEY: ${{ secrets.HELICONE_API_KEY }}
  run: crashlens fetch-helicone --hours-back 24 --output logs.jsonl

- name: Run guard
  run: crashlens guard logs.jsonl --fail-on-violations
```

### Dry Run Workflow Preview

**Preview workflow without creating file**:

```bash
# See what workflow would be generated
crashlens init --dry-run-workflow
```

**Output**:
```
📄 Preview: .github/workflows/crashlens.yml

name: CrashLens Policy Check
on:
  push:
    branches: [main, develop]
...

💡 To create this workflow, run: crashlens init
```

### Workflow Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--dry-run-workflow` | Flag | False | Preview workflow without writing |

---

## Configuration Files Created

### Directory Structure

**After running `init`**:

```
your-project/
├── .crashlens/
│   ├── rules.yaml          # Policy rules
│   ├── config.yaml         # Project configuration
│   └── suppressions.yaml   # Rule suppressions (optional)
├── .github/
│   └── workflows/
│       └── crashlens.yml   # CI/CD workflow
└── logs/                   # Your log files
    └── *.jsonl
```

### 1. Rules File (`.crashlens/rules.yaml`)

**Generated policy rules**:

```yaml
version: 1

rules:
  - id: RL001
    description: "High token usage on expensive models (gpt-4)"
    if:
      and:
        - input.model: "gpt-4"
        - usage.prompt_tokens:
            '>': 2000
    action: fail_ci
    severity: fatal
    suggestion: "Use gpt-3.5-turbo for shorter prompts or reduce token count"
  
  - id: RL002
    description: "Excessive retry attempts"
    if:
      metadata.retry_count:
        '>': 3
    action: warn
    severity: error
    suggestion: "Implement exponential backoff and circuit breaker"
  
  # ... more rules based on selected templates
```

### 2. Config File (`.crashlens/config.yaml`)

**Project configuration**:

```yaml
version: 1

# Project settings
project:
  name: your-project
  severity_threshold: error
  fail_on_violations: true

# Log sources
sources:
  type: local
  paths:
    - logs/*.jsonl

# Policy templates
templates:
  - retry-loop-prevention
  - model-overkill-detection
  - fallback-chain-detector
  - budget-protection

# Prometheus metrics (optional)
metrics:
  enabled: false
  pushgateway_url: http://localhost:9091
  job_name: crashlens
```

### 3. GitHub Workflow (`.github/workflows/crashlens.yml`)

**CI/CD integration** (see [GitHub Actions Generation](#github-actions-generation))

---

## Complete Examples

### Example 1: First-Time Setup

```bash
# Run interactive wizard
crashlens init

# Follow prompts:
# - Templates: all
# - Severity: error
# - Fail on violations: Yes
# - Logs source: local
# - GitHub workflow: Yes

# Review generated files
cat .crashlens/rules.yaml
cat .github/workflows/crashlens.yml

# Test configuration
crashlens guard logs/*.jsonl --dry-run
```

### Example 2: CI/CD Automated Setup

```bash
# In Dockerfile or CI script
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="fatal"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
export CRASHLENS_LOGS_SOURCE="langfuse"
export CRASHLENS_CREATE_WORKFLOW="true"

# Run non-interactive init
crashlens init --non-interactive

# Commit configuration
git add .crashlens/ .github/workflows/
git commit -m "Add CrashLens configuration"
```

### Example 3: Preview Workflow Only

```bash
# See workflow without creating files
crashlens init --dry-run-workflow > workflow-preview.yml

# Review
cat workflow-preview.yml

# If approved, run full init
crashlens init
```

### Example 4: Minimal Setup (No Workflow)

```bash
# Setup without GitHub Actions
export CRASHLENS_TEMPLATES="retry-loop-prevention,model-overkill-detection"
export CRASHLENS_CREATE_WORKFLOW="false"

crashlens init --non-interactive

# Only creates .crashlens/ directory
```

### Example 5: Development Environment

```bash
# Permissive rules for development
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="warn"
export CRASHLENS_FAIL_ON_VIOLATIONS="false"
export CRASHLENS_LOGS_SOURCE="local"

crashlens init --non-interactive

# Test without failing
crashlens guard logs/*.jsonl --dry-run
```

### Example 6: Production Environment

```bash
# Strict rules for production
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="fatal"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
export CRASHLENS_LOGS_SOURCE="langfuse"
export CRASHLENS_CREATE_WORKFLOW="true"

crashlens init --non-interactive

# Enforce strictly
crashlens guard logs/*.jsonl --fail-on-violations
```

---

## Best Practices

### 1. Start with Interactive Mode

```bash
# First time: use wizard to understand options
crashlens init

# Later: automate with --non-interactive
```

### 2. Use Dry Run for Workflows

```bash
# Preview before creating
crashlens init --dry-run-workflow

# Review output
# Then create if satisfied
crashlens init
```

### 3. Environment-Specific Configuration

**Development**:
```bash
export CRASHLENS_SEVERITY="warn"
export CRASHLENS_FAIL_ON_VIOLATIONS="false"
```

**Staging**:
```bash
export CRASHLENS_SEVERITY="error"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
```

**Production**:
```bash
export CRASHLENS_SEVERITY="fatal"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
```

### 4. Version Control Configuration

```bash
# Commit configuration files
git add .crashlens/
git commit -m "Add CrashLens configuration"

# Optionally include workflow
git add .github/workflows/crashlens.yml
git commit -m "Add CrashLens CI workflow"
```

### 5. Document Custom Changes

```yaml
# .crashlens/rules.yaml
version: 1

# CUSTOM RULES
# Added by: John Doe (2025-01-15)
# Reason: Enforce stricter retry limits for production

rules:
  - id: CUSTOM_001
    description: "Custom retry limit for production"
    # ... rule definition
```

### 6. Test Configuration

```bash
# After init, test with dry run
crashlens guard logs/*.jsonl --dry-run

# Verify rules work as expected
# Adjust .crashlens/rules.yaml if needed
```

### 7. Update Workflow Secrets

```bash
# After generating workflow, add secrets to GitHub:
# - LANGFUSE_PUBLIC_KEY
# - LANGFUSE_SECRET_KEY
# - HELICONE_API_KEY (if using Helicone)

# Settings → Secrets and variables → Actions
```

---

## Troubleshooting

### Issue: Init Overwrites Existing Config

**Problem**: Running init again overwrites configuration

**Solution**:
```bash
# Backup existing config
cp .crashlens/rules.yaml .crashlens/rules.yaml.bak

# Run init
crashlens init

# Merge if needed
# Or restore backup
```

### Issue: Workflow Not Working

**Problem**: Generated workflow fails in CI

**Solution**:
```bash
# Check secrets are set (GitHub Settings → Secrets)
# Verify log paths exist
# Test locally first:
crashlens guard logs/*.jsonl --dry-run
```

### Issue: Wrong Template Selected

**Problem**: Need to change templates after init

**Solution**:
```bash
# Edit .crashlens/rules.yaml directly
nano .crashlens/rules.yaml

# Or re-run init (backup first)
mv .crashlens/rules.yaml .crashlens/rules.yaml.old
crashlens init
```

### Issue: Non-Interactive Mode Not Working

**Problem**: Environment variables not being read

**Solution**:
```bash
# Verify variables are set
env | grep CRASHLENS

# Export in same shell
export CRASHLENS_TEMPLATES="all"
crashlens init --non-interactive

# Or use inline
CRASHLENS_TEMPLATES=all crashlens init --non-interactive
```

---

## Command Reference

### All Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--non-interactive` | Flag | False | Skip prompts, use env vars |
| `--dry-run-workflow` | Flag | False | Preview workflow without writing |

### Environment Variables

| Variable | Values | Default |
|----------|--------|---------|
| `CRASHLENS_TEMPLATES` | Template names or `all` | `all` |
| `CRASHLENS_SEVERITY` | `warn`, `error`, `fatal` | `error` |
| `CRASHLENS_FAIL_ON_VIOLATIONS` | `true`, `false` | `true` |
| `CRASHLENS_LOGS_SOURCE` | `local`, `langfuse`, `helicone`, `other` | `local` |
| `CRASHLENS_CREATE_WORKFLOW` | `true`, `false` | `false` |

---

## See Also

- **[Guard Command](./guard-command.md)**: Policy enforcement
- **[Scan Command](./scan-command.md)**: Token waste detection
- **[List Templates](./list-policy-templates-command.md)**: View available policies
- **[CI/CD Integration](../how-to-guides/ci-cd-integration.md)**: Pipeline setup
- **[CLI Reference](../CLI_COMMAND_REFERENCE.md)**: All commands

---

**Quick Start**: `crashlens init` (interactive) or `crashlens init --non-interactive` (automated)
