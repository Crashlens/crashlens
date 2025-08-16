# 🤖 CrashLens Non-Interactive Mode Guide

## Overview

The **non-interactive mode** (`crashlens init --non-interactive`) enables automated setup of CrashLens configuration without user prompts. This is essential for CI/CD pipelines, Docker containers, and automated deployment scenarios where human interaction isn't possible.

## 🎯 Purpose

- **Automated CI/CD Integration**: Set up CrashLens in GitHub Actions, GitLab CI, Jenkins, etc.
- **Container Deployments**: Pre-configure CrashLens during Docker image builds
- **Infrastructure as Code**: Integrate with Terraform, Ansible, CloudFormation
- **Batch Configurations**: Configure multiple environments consistently
- **Headless Environments**: Work in environments without terminal interaction

## 🔧 Basic Usage

### Command Syntax
```bash
crashlens init --non-interactive [--dry-run-workflow]
```

### Environment Variables
All configuration is controlled through environment variables:

| Variable | Description | Default | Valid Values |
|----------|-------------|---------|--------------|
| `CRASHLENS_TEMPLATES` | Policy templates to use | `all` | Template names (comma-separated) or `all` |
| `CRASHLENS_SEVERITY` | Minimum severity threshold | `high` | `low`, `medium`, `high`, `critical` |
| `CRASHLENS_FAIL_ON_VIOLATIONS` | Exit with error on violations | `True` | `true`, `false`, `1`, `0`, `yes`, `no` |
| `CRASHLENS_LOGS_SOURCE` | Source of log data | `local` | `local`, `langfuse`, `helicone`, `other` |
| `CRASHLENS_CREATE_WORKFLOW` | Generate GitHub Actions workflow | `False` | `true`, `false`, `1`, `0`, `yes`, `no` |

## 📋 Platform-Specific Examples

### PowerShell (Windows)

#### Single Command
```powershell
$env:CRASHLENS_TEMPLATES="retry-loop-prevention,budget-protection"; $env:CRASHLENS_SEVERITY="medium"; $env:CRASHLENS_FAIL_ON_VIOLATIONS="false"; crashlens init --non-interactive
```

#### Multi-Line Setup
```powershell
$env:CRASHLENS_TEMPLATES="retry-loop-prevention,budget-protection"
$env:CRASHLENS_SEVERITY="medium"
$env:CRASHLENS_FAIL_ON_VIOLATIONS="false"
$env:CRASHLENS_LOGS_SOURCE="langfuse"
$env:CRASHLENS_CREATE_WORKFLOW="true"
crashlens init --non-interactive
```

#### Check Current Variables
```powershell
Write-Host "CRASHLENS_TEMPLATES: $env:CRASHLENS_TEMPLATES"
Write-Host "CRASHLENS_SEVERITY: $env:CRASHLENS_SEVERITY" 
Write-Host "CRASHLENS_FAIL_ON_VIOLATIONS: $env:CRASHLENS_FAIL_ON_VIOLATIONS"
```

#### Clear Variables
```powershell
Remove-Item Env:\CRASHLENS_TEMPLATES -ErrorAction SilentlyContinue
Remove-Item Env:\CRASHLENS_SEVERITY -ErrorAction SilentlyContinue
Remove-Item Env:\CRASHLENS_FAIL_ON_VIOLATIONS -ErrorAction SilentlyContinue
```

### Bash/Zsh (Linux/macOS)

#### Single Command
```bash
CRASHLENS_TEMPLATES="retry-loop-prevention,budget-protection" CRASHLENS_SEVERITY="medium" CRASHLENS_FAIL_ON_VIOLATIONS="false" crashlens init --non-interactive
```

#### Export Variables
```bash
export CRASHLENS_TEMPLATES="retry-loop-prevention,budget-protection"
export CRASHLENS_SEVERITY="medium"
export CRASHLENS_FAIL_ON_VIOLATIONS="false"
export CRASHLENS_LOGS_SOURCE="langfuse"
export CRASHLENS_CREATE_WORKFLOW="true"
crashlens init --non-interactive
```

#### Check Variables
```bash
echo "CRASHLENS_TEMPLATES: $CRASHLENS_TEMPLATES"
echo "CRASHLENS_SEVERITY: $CRASHLENS_SEVERITY"
echo "CRASHLENS_FAIL_ON_VIOLATIONS: $CRASHLENS_FAIL_ON_VIOLATIONS"
```

#### Unset Variables
```bash
unset CRASHLENS_TEMPLATES
unset CRASHLENS_SEVERITY
unset CRASHLENS_FAIL_ON_VIOLATIONS
```

### Command Prompt (Windows)

#### Set Variables and Run
```cmd
set CRASHLENS_TEMPLATES=retry-loop-prevention,budget-protection
set CRASHLENS_SEVERITY=medium
set CRASHLENS_FAIL_ON_VIOLATIONS=false
crashlens init --non-interactive
```

## 🚀 CI/CD Integration Examples

### GitHub Actions

```yaml
name: Setup CrashLens
on: [push, pull_request]

jobs:
  setup-crashlens:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install CrashLens
      run: pip install crashlens
    
    - name: Configure CrashLens
      env:
        CRASHLENS_TEMPLATES: "retry-loop-prevention,budget-protection"
        CRASHLENS_SEVERITY: "high"
        CRASHLENS_FAIL_ON_VIOLATIONS: "true"
        CRASHLENS_CREATE_WORKFLOW: "false"
      run: crashlens init --non-interactive
    
    - name: Run Policy Check
      run: crashlens policy-check logs.jsonl --fail-on-violations
```

### GitLab CI

```yaml
stages:
  - setup
  - analyze

setup_crashlens:
  stage: setup
  image: python:3.11
  variables:
    CRASHLENS_TEMPLATES: "all"
    CRASHLENS_SEVERITY: "medium"
    CRASHLENS_FAIL_ON_VIOLATIONS: "true"
  script:
    - pip install crashlens
    - crashlens init --non-interactive
  artifacts:
    paths:
      - .crashlens/

analyze_logs:
  stage: analyze
  dependencies:
    - setup_crashlens
  script:
    - crashlens scan logs.jsonl
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    environment {
        CRASHLENS_TEMPLATES = "retry-loop-prevention,budget-protection"
        CRASHLENS_SEVERITY = "high"
        CRASHLENS_FAIL_ON_VIOLATIONS = "true"
    }
    stages {
        stage('Setup') {
            steps {
                sh 'pip install crashlens'
                sh 'crashlens init --non-interactive'
            }
        }
        stage('Analyze') {
            steps {
                sh 'crashlens scan logs.jsonl'
            }
        }
    }
}
```

### Docker

#### Dockerfile
```dockerfile
FROM python:3.11-slim

# Install CrashLens
RUN pip install crashlens

# Set configuration via environment variables
ENV CRASHLENS_TEMPLATES="all"
ENV CRASHLENS_SEVERITY="high"
ENV CRASHLENS_FAIL_ON_VIOLATIONS="true"
ENV CRASHLENS_LOGS_SOURCE="local"

# Configure CrashLens during build
RUN crashlens init --non-interactive

# Copy application files
COPY . /app
WORKDIR /app

# Run analysis on container start
CMD ["crashlens", "scan", "logs.jsonl"]
```

#### Docker Compose
```yaml
version: '3.8'
services:
  crashlens:
    build: .
    environment:
      - CRASHLENS_TEMPLATES=retry-loop-prevention,budget-protection
      - CRASHLENS_SEVERITY=medium
      - CRASHLENS_FAIL_ON_VIOLATIONS=false
      - CRASHLENS_LOGS_SOURCE=langfuse
    volumes:
      - ./logs:/app/logs
    command: crashlens scan /app/logs/traces.jsonl
```

## 🎛️ Configuration Scenarios

### Development Environment
```bash
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="low"
export CRASHLENS_FAIL_ON_VIOLATIONS="false"
export CRASHLENS_LOGS_SOURCE="local"
crashlens init --non-interactive
```

### Staging Environment
```bash
export CRASHLENS_TEMPLATES="retry-loop-prevention,budget-protection,fallback-storm-detection"
export CRASHLENS_SEVERITY="medium"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
export CRASHLENS_LOGS_SOURCE="langfuse"
crashlens init --non-interactive
```

### Production Environment
```bash
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="high"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
export CRASHLENS_LOGS_SOURCE="langfuse"
export CRASHLENS_CREATE_WORKFLOW="true"
crashlens init --non-interactive
```

## 🔍 Dry Run Mode

Generate workflow files without saving configuration:

### PowerShell
```powershell
$env:CRASHLENS_TEMPLATES="all"
$env:CRASHLENS_SEVERITY="high"
crashlens init --non-interactive --dry-run-workflow > workflow.yml
```

### Bash
```bash
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="high"
crashlens init --non-interactive --dry-run-workflow > workflow.yml
```

## 📊 Output and Results

### Successful Execution
```
🤖 Running in non-interactive mode...

📋 Policy templates: retry-loop-prevention,budget-protection
📊 Severity threshold: medium
🚨 Fail on violations: False
📁 Logs source: local
⚙️  Create workflow: False

✅ Configuration saved at .crashlens\config.yaml

🎉 Crashlens setup complete!
👉 Next steps:
   1. Add your log files (.jsonl format)
   2. Run: crashlens scan logs.jsonl
   3. Or use policy-check: crashlens policy-check logs.jsonl
   4. View config: cat .crashlens\config.yaml
```

### Generated Configuration (`.crashlens/config.yaml`)
```yaml
created_at: '2025-08-17T01:15:16.579308'
fail_on_violations: true
logs_source: local
output_directory: .
policy_template: budget-protection
severity_threshold: critical
version: 2.9.5
```

### Error Handling
```
🤖 Running in non-interactive mode...

❌ Invalid CRASHLENS_SEVERITY: invalid_value
❌ Non-interactive mode failed due to invalid environment variables.
```

## 🛠️ Available Policy Templates

Use any of these templates in `CRASHLENS_TEMPLATES`:

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
- `all` (includes all templates)

### Multiple Templates
```bash
# Comma-separated list
CRASHLENS_TEMPLATES="retry-loop-prevention,budget-protection,fallback-storm-detection"

# All templates
CRASHLENS_TEMPLATES="all"
```

## ⚠️ Error Scenarios and Troubleshooting

### Invalid Template Names
```bash
❌ Invalid templates: invalid-template-name
❌ Non-interactive mode failed due to invalid environment variables.
```

**Solution**: Use valid template names from the list above.

### Invalid Severity Level
```bash
❌ Invalid CRASHLENS_SEVERITY: invalid
❌ Non-interactive mode failed due to invalid environment variables.
```

**Solution**: Use `low`, `medium`, `high`, or `critical`.

### Missing Environment Variables
If no environment variables are set, defaults are used:
- Templates: `all`
- Severity: `high`
- Fail on violations: `True`
- Logs source: `local`
- Create workflow: `False`

### Permission Issues
```bash
❌ Error during setup: [Errno 13] Permission denied: '.crashlens'
```

**Solution**: Ensure write permissions in the current directory.

## 📈 Best Practices

### 1. **Environment-Specific Configurations**
Create different configurations for different environments:

```bash
# .env.development
CRASHLENS_TEMPLATES=all
CRASHLENS_SEVERITY=low
CRASHLENS_FAIL_ON_VIOLATIONS=false

# .env.production  
CRASHLENS_TEMPLATES=retry-loop-prevention,budget-protection
CRASHLENS_SEVERITY=high
CRASHLENS_FAIL_ON_VIOLATIONS=true
```

### 2. **Validation Scripts**
Create scripts to validate environment variables:

```bash
#!/bin/bash
# validate-crashlens-env.sh

VALID_TEMPLATES="retry-loop-prevention,model-overkill-detection,chain-recursion-prevention,fallback-storm-detection,budget-protection,rate-limit-management,prompt-optimization,error-handling-efficiency,context-window-optimization,batch-processing-efficiency,all"
VALID_SEVERITIES="low,medium,high,critical"
VALID_SOURCES="local,langfuse,helicone,other"

if [[ "$CRASHLENS_SEVERITY" && ! "$VALID_SEVERITIES" =~ "$CRASHLENS_SEVERITY" ]]; then
    echo "❌ Invalid CRASHLENS_SEVERITY: $CRASHLENS_SEVERITY"
    exit 1
fi

echo "✅ Environment variables validated"
```

### 3. **Terraform Integration**
```hcl
resource "null_resource" "crashlens_setup" {
  provisioner "local-exec" {
    environment = {
      CRASHLENS_TEMPLATES = var.crashlens_templates
      CRASHLENS_SEVERITY = var.crashlens_severity
      CRASHLENS_FAIL_ON_VIOLATIONS = var.fail_on_violations
    }
    command = "crashlens init --non-interactive"
  }
}
```

### 4. **Kubernetes ConfigMaps**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: crashlens-config
data:
  CRASHLENS_TEMPLATES: "retry-loop-prevention,budget-protection"
  CRASHLENS_SEVERITY: "high"
  CRASHLENS_FAIL_ON_VIOLATIONS: "true"
  CRASHLENS_LOGS_SOURCE: "langfuse"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crashlens-analyzer
spec:
  template:
    spec:
      containers:
      - name: crashlens
        image: crashlens:latest
        envFrom:
        - configMapRef:
            name: crashlens-config
        command: ["crashlens", "init", "--non-interactive"]
```

## 🔗 Related Commands

After setting up with non-interactive mode, use these commands:

```bash
# Scan logs with the configuration
crashlens scan logs.jsonl

# Policy check with specific templates
crashlens policy-check logs.jsonl --policy-template retry-loop-prevention

# List available templates
crashlens list-policy-templates

# Check current configuration
cat .crashlens/config.yaml
```

## 📚 Additional Resources

- **Main Documentation**: `docs/USAGE.md`
- **Policy Templates**: `crashlens list-policy-templates`
- **GitHub Actions Setup**: `docs/slack-webhook-setup.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`

The non-interactive mode is designed to be **robust**, **flexible**, and **automation-friendly**, making it perfect for modern DevOps workflows where manual intervention isn't possible or practical.
