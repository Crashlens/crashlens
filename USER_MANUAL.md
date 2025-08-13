# 📖 CRASHLENS USER MANUAL - COMPLETE SETUP & USAGE GUIDE

## 🎯 **OVERVIEW**

Crashlens is a powerful CLI tool that detects token waste and inefficient patterns in GPT API usage by analyzing Langfuse-style logs. This manual provides complete step-by-step instructions for setting up Crashlens in your GitHub Actions workflow and using all its features.

### **What Crashlens Does:**
- 🔍 **Detects Token Waste**: Identifies retry loops, model overkill, slow responses
- 📊 **Policy Enforcement**: Configurable rules for cost control and efficiency
- 🤖 **CI/CD Integration**: Automated checks in GitHub Actions workflows
- 📈 **Cost Optimization**: Prevents budget overruns and inefficient API usage
- 🛡️ **Quality Assurance**: Ensures optimal GPT API usage patterns

> 📋 **GitHub Actions Templates**: Ready-to-use workflow examples are available in `examples/ci-workflows/`

---

## 🚀 **QUICK START (5 MINUTES)**

### **Step 1: Install Crashlens**
```bash
# Using pip
pip install crashlens

# Using poetry (recommended)
poetry add crashlens

# Verify installation
crashlens --version
# Should output: crashlens, version 2.5.1
```

### **Step 2: Initialize Configuration**
```bash
# Interactive setup (recommended for first time)
crashlens init

# Or automated setup
export CRASHLENS_TEMPLATES="retry-loop-prevention,model-overkill-detection"
export CRASHLENS_SEVERITY="high"
crashlens init --non-interactive
```

### **Step 3: Test with Sample Data**
```bash
# Generate test data
crashlens simulate --output test-logs.jsonl --count 50 --scenario retry-loop

# Run policy check
crashlens policy-check test-logs.jsonl --policy-template retry-loop-prevention
```

---

## 📋 **DETAILED INSTALLATION GUIDE**

### **Prerequisites**
- Python 3.8+ (3.12 recommended)
- Git repository with GitHub Actions enabled
- Basic familiarity with YAML configuration files

### **Installation Methods**

#### **Method 1: Poetry (Recommended)**
```bash
# Add to your project
poetry add crashlens

# Install in development environment
poetry install

# Verify installation
poetry run crashlens --version
```

#### **Method 2: pip**
```bash
# Install globally
pip install crashlens

# Or in virtual environment
python -m venv crashlens-env
source crashlens-env/bin/activate  # Linux/Mac
# crashlens-env\Scripts\activate    # Windows
pip install crashlens
```

#### **Method 3: From Source (Advanced)**
```bash
# Clone repository
git clone https://github.com/Crashlens/crashlens.git
cd crashlens

# Install with poetry
poetry install

# Or with pip
pip install -e .
```

---

## ⚙️ **CONFIGURATION SETUP**

### **Interactive Configuration (Beginner-Friendly)**

Run the setup wizard to configure Crashlens interactively:

```bash
crashlens init
```

You'll be prompted for:
- **Policy Templates**: Choose detection rules (retry-loop, model-overkill, etc.)
- **Severity Threshold**: Set minimum issue severity (low/medium/high/critical)
- **Failure Behavior**: Whether to fail CI/CD on violations
- **Log Source**: Where your logs come from (local/langfuse/helicone)
- **GitHub Workflow**: Whether to create automated workflow

### **Non-Interactive Configuration (CI/CD)**

For automated environments, use environment variables:

```bash
# Set configuration via environment variables
export CRASHLENS_TEMPLATES="retry-loop-prevention,model-overkill-detection,budget-protection"
export CRASHLENS_SEVERITY="high"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
export CRASHLENS_LOGS_SOURCE="langfuse"
export CRASHLENS_CREATE_WORKFLOW="true"

# Run non-interactive setup
crashlens init --non-interactive
```

### **Configuration File Structure**

The setup creates `.crashlens/config.yaml`:

```yaml
# .crashlens/config.yaml
policy_template: retry-loop-prevention,model-overkill-detection
severity_threshold: high
fail_on_violations: true
logs_source: langfuse
created_at: '2025-08-11T10:30:00.000000'
version: 2.5.1
output_directory: .
workflow_config:
  python_version: "3.11"
  fail_on_violations: true
api_keys:
  langfuse_secret_key: ""
  langfuse_public_key: ""
  helicone_api_key: ""
```

---

## 🔧 **GITHUB ACTIONS SETUP**

### **Method 1: Automatic Workflow Creation**

When running `crashlens init`, select "Yes" for GitHub workflow creation. This generates:

**`.github/workflows/crashlens.yml`** (copied from examples)

```yaml
name: 'Crashlens Token Waste Detection'

on:
  workflow_dispatch:
    inputs:
      config_file:
        description: 'Path to Crashlens config file'
        required: false
        default: '.crashlens/config.yaml'
      fail_on_violations:
        description: 'Fail workflow on policy violations'
        required: false
        default: 'true'
        type: boolean
      python_version:
        description: 'Python version'
        required: false
        default: '3.11'

  pull_request:
    branches: [ main, develop ]
  push:
    branches: [ main, develop ]

jobs:
  crashlens-check:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ inputs.python_version || '3.11' }}
        
    - name: Install Poetry
      uses: snok/install-poetry@v1
      with:
        version: latest
        virtualenvs-create: true
        virtualenvs-in-project: true
        
    - name: Load cached venv
      id: cached-poetry-dependencies
      uses: actions/cache@v4
      with:
        path: .venv
        key: venv-${{ runner.os }}-${{ steps.setup-python.outputs.python-version }}-${{ hashFiles('**/poetry.lock') }}
        
    - name: Install dependencies
      if: steps.cached-poetry-dependencies.outputs.cache-hit != 'true'
      run: poetry install --no-interaction --no-root
      
    - name: Install Crashlens
      run: poetry add crashlens
      
    - name: Check for Crashlens config
      run: |
        if [ -f ".crashlens/config.yaml" ]; then
          echo "✅ Found Crashlens config at .crashlens/config.yaml"
          cat .crashlens/config.yaml
        else
          echo "⚠️ No Crashlens config found, using defaults"
        fi
        
    - name: Run Crashlens Policy Check
      env:
        LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
        LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
        HELICONE_API_KEY: ${{ secrets.HELICONE_API_KEY }}
      run: |
        # Find log files
        LOG_FILES=$(find . -name "*.jsonl" -type f | head -10 | tr '\n' ' ')
        
        if [ -z "$LOG_FILES" ]; then
          echo "📝 No .jsonl log files found, generating test data"
          poetry run crashlens simulate --output test-logs.jsonl --count 100 --scenario mixed-errors
          LOG_FILES="test-logs.jsonl"
        else
          echo "📁 Found log files: $LOG_FILES"
        fi
        
        # Run policy check on each file
        for log_file in $LOG_FILES; do
          echo "🔍 Checking $log_file"
          if [ "${{ inputs.fail_on_violations }}" == "true" ]; then
            poetry run crashlens policy-check "$log_file" --policy-template all --fail-on-violations --severity-threshold high
          else
            poetry run crashlens policy-check "$log_file" --policy-template all --severity-threshold high || true
          fi
        done
        
    - name: Generate Crashlens Report
      if: always()
      run: |
        mkdir -p crashlens-reports
        
        # Generate markdown report
        LOG_FILES=$(find . -name "*.jsonl" -type f | head -5 | tr '\n' ' ')
        for log_file in $LOG_FILES; do
          echo "📊 Generating report for $log_file"
          poetry run crashlens policy-check "$log_file" --policy-template all --format markdown > "crashlens-reports/$(basename $log_file .jsonl)-report.md" || true
        done
        
    - name: Upload Crashlens Reports
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: crashlens-reports
        path: crashlens-reports/
        retention-days: 30

    - name: Comment PR with Results
      if: github.event_name == 'pull_request' && always()
      uses: actions/github-script@v7
      with:
        script: |
          const fs = require('fs');
          const path = require('path');
          
          // Read report files
          const reportsDir = 'crashlens-reports';
          if (fs.existsSync(reportsDir)) {
            const reports = fs.readdirSync(reportsDir)
              .filter(file => file.endsWith('.md'))
              .slice(0, 3); // Limit to first 3 reports
              
            let comment = '## 🔍 Crashlens Policy Check Results\n\n';
            
            reports.forEach(reportFile => {
              const content = fs.readFileSync(path.join(reportsDir, reportFile), 'utf8');
              comment += `### ${reportFile}\n\`\`\`\n${content.slice(0, 1000)}...\n\`\`\`\n\n`;
            });
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
          }
```

### **Method 2: Pre-configured Workflows (Recommended)**

CrashLens provides pre-built GitHub Actions workflows that you can copy directly to your repository:

#### **Option A: Comprehensive Analysis Workflow**
For production repositories with complex LLM workflows:
```bash
# Copy the comprehensive workflow
curl -o .github/workflows/crashlens-analysis.yml https://raw.githubusercontent.com/Crashlens/crashlens/main/examples/ci-workflows/crashlens-analysis.yml.example
```

**Features:**
- Complete policy analysis with all rule templates
- Cost monitoring and budget alerts  
- Security dependency scanning
- Performance analysis
- PR comments with detailed results
- Comprehensive reporting and artifacts

#### **Option B: Starter Workflow**
For basic monitoring needs or new projects:
```bash
# Copy the starter workflow  
curl -o .github/workflows/crashlens-starter.yml https://raw.githubusercontent.com/Crashlens/crashlens/main/examples/ci-workflows/crashlens-starter.yml.example
```

**Features:**
- Basic policy checking (retry loops, model overkill)
- Simple PR comments
- Lightweight and fast
- Perfect for getting started

#### **Workflow Configuration**
Both workflows include configurable environment variables:
```yaml
env:
  # Policy Configuration
  CRASHLENS_TEMPLATES: "retry-loop-prevention,model-overkill-detection,budget-protection"
  CRASHLENS_SEVERITY: "high"                    # low/medium/high/critical
  CRASHLENS_FAIL_ON_VIOLATIONS: "false"        # "true" to break CI
  
  # Cost Monitoring
  DAILY_COST_LIMIT: "10.00"                    # Maximum daily cost
  EXPENSIVE_REQUEST_THRESHOLD: "0.05"          # Flag requests over $0.05
  
  # Performance Limits
  SLOW_RESPONSE_THRESHOLD_MS: "3000"           # Flag slow responses
  ERROR_RATE_THRESHOLD: "0.20"                 # Flag high error rates
```

**📖 Complete Setup Guide:** See `examples/ci-workflows/README.md` for detailed configuration options and troubleshooting.

### **Method 3: Manual Workflow Setup**

Create a custom workflow file manually in your repository:

1. **Create directory structure:**
   ```bash
   mkdir -p .github/workflows
   ```

2. **Create workflow file:** Copy a workflow example from `examples/ci-workflows/` to `.github/workflows/crashlens.yml`

3. **Commit and push:**
   ```bash
   git add .github/workflows/crashlens.yml
   git commit -m "Add Crashlens workflow"
   git push
   ```

### **Method 4: Integration with Existing Workflows**

Add Crashlens to your existing CI/CD workflow:

```yaml
# Add this job to your existing workflow
  token-waste-check:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    
    - name: Install Crashlens
      run: pip install crashlens
      
    - name: Run Token Waste Detection
      run: |
        # Check your log files
        crashlens policy-check logs/*.jsonl --policy-template all --fail-on-violations
```

---

## 🔑 **SECRETS AND ENVIRONMENT VARIABLES**

### **Required Secrets (Add to GitHub Repository)**

Navigate to `Settings > Secrets and variables > Actions` and add:

#### **For Langfuse Integration:**
- `LANGFUSE_SECRET_KEY`: Your Langfuse secret key
- `LANGFUSE_PUBLIC_KEY`: Your Langfuse public key

#### **For Helicone Integration:**
- `HELICONE_API_KEY`: Your Helicone API key

#### **For OpenAI Direct (Optional):**
- `OPENAI_API_KEY`: Your OpenAI API key (if checking live data)

### **Environment Variables for Configuration:**

```bash
# Policy Configuration
CRASHLENS_TEMPLATES="retry-loop-prevention,model-overkill-detection,budget-protection"
CRASHLENS_SEVERITY="high"                    # low/medium/high/critical
CRASHLENS_FAIL_ON_VIOLATIONS="true"          # true/false
CRASHLENS_LOGS_SOURCE="langfuse"             # local/langfuse/helicone/other

# Output Configuration  
CRASHLENS_OUTPUT_FORMAT="markdown"           # slack/markdown/json
CRASHLENS_OUTPUT_DIRECTORY="./reports"      # Where to save reports

# Workflow Configuration
CRASHLENS_PYTHON_VERSION="3.11"             # Python version for workflow
```

---

## 📊 **POLICY TEMPLATES & CONFIGURATION**

### **Available Policy Templates**

Crashlens includes 10+ built-in policy templates:

```bash
# List all available templates
crashlens list-policy-templates
```

#### **Core Templates:**
1. **`retry-loop-prevention`** - Detects API retry patterns that waste tokens
2. **`model-overkill-detection`** - Finds expensive models used for simple tasks  
3. **`budget-protection`** - Prevents cost overruns and spending spikes
4. **`fallback-storm-detection`** - Identifies cascading fallback failures
5. **`error-handling-efficiency`** - Optimizes error handling patterns

#### **Advanced Templates:**
6. **`chain-recursion-prevention`** - Prevents infinite loops
7. **`context-window-optimization`** - Optimizes context usage
8. **`batch-processing-efficiency`** - Improves batch processing
9. **`prompt-optimization`** - Identifies inefficient prompts
10. **`rate-limit-management`** - Handles rate limiting issues

### **Template Configuration Examples**

#### **Conservative Setup (Fewer False Positives)**
```yaml
policy_template: retry-loop-prevention,budget-protection
severity_threshold: critical
fail_on_violations: false
```

#### **Aggressive Setup (Maximum Detection)**
```yaml
policy_template: all
severity_threshold: medium
fail_on_violations: true
```

#### **Custom Template Selection**
```yaml
policy_template: retry-loop-prevention,model-overkill-detection,error-handling-efficiency
severity_threshold: high
fail_on_violations: true
```

---

## 🧪 **TESTING AND DATA GENERATION**

### **Generate Test Data for Development**

Crashlens includes a powerful simulation feature for testing:

#### **Basic Test Data Generation**
```bash
# Generate normal usage patterns
crashlens simulate --output normal-logs.jsonl --count 100 --scenario normal

# Generate retry loop patterns (for testing retry detection)
crashlens simulate --output retry-logs.jsonl --count 50 --scenario retry-loop

# Generate model overkill patterns (expensive models for simple tasks)
crashlens simulate --output overkill-logs.jsonl --count 30 --scenario model-overkill
```

#### **Advanced Simulation Options**
```bash
# Custom models and error rates
crashlens simulate \
  --output custom-logs.jsonl \
  --count 200 \
  --scenario mixed-errors \
  --models "gpt-4o,gpt-4-turbo,claude-3" \
  --error-rate 0.3 \
  --seed 42

# Deterministic test data (same every time)
crashlens simulate \
  --output deterministic-test.jsonl \
  --count 100 \
  --seed 12345 \
  --force
```

#### **Scenario Types Available**
- **`normal`**: Balanced mix of successful and error traces
- **`retry-loop`**: Multiple attempts with same prompts (tests retry detection)
- **`model-overkill`**: Expensive models for simple tasks (tests overkill detection)
- **`slow`**: Long response times >5000ms (tests timeout detection)  
- **`mixed-errors`**: Various error types and patterns

### **Test Your Policies Locally**

Before pushing to GitHub Actions, test locally:

```bash
# Generate test data
crashlens simulate --output test-data.jsonl --count 100 --scenario retry-loop

# Test policy detection
crashlens policy-check test-data.jsonl --policy-template retry-loop-prevention --fail-on-violations

# Test with different severity levels
crashlens policy-check test-data.jsonl --policy-template all --severity-threshold medium

# Generate markdown report
crashlens policy-check test-data.jsonl --policy-template all --format markdown > policy-report.md
```

---

## 📈 **USAGE PATTERNS & BEST PRACTICES**

### **Development Workflow Integration**

#### **1. Pre-commit Hooks**
```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: crashlens-check
        name: Crashlens Token Waste Check
        entry: crashlens policy-check
        language: system
        files: '\.jsonl$'
        args: ['--policy-template', 'retry-loop-prevention', '--fail-on-violations']
```

#### **2. Local Development Script**
```bash
#!/bin/bash
# scripts/check-token-waste.sh

echo "🔍 Checking for token waste patterns..."

# Find all log files
LOG_FILES=$(find . -name "*.jsonl" -type f)

if [ -z "$LOG_FILES" ]; then
    echo "📝 No log files found, generating test data"
    crashlens simulate --output dev-test.jsonl --count 50 --scenario mixed-errors
    LOG_FILES="dev-test.jsonl"
fi

# Run checks
for file in $LOG_FILES; do
    echo "Checking $file..."
    crashlens policy-check "$file" --policy-template all --severity-threshold high
done

echo "✅ Token waste check complete!"
```

#### **3. Docker Integration**
```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install Crashlens
RUN pip install crashlens

# Copy logs and config
COPY logs/ /app/logs/
COPY .crashlens/ /app/.crashlens/

WORKDIR /app

# Run policy check
CMD ["crashlens", "policy-check", "logs/", "--policy-template", "all", "--fail-on-violations"]
```

### **Production Monitoring Setup**

#### **Daily Cost Analysis Workflow**
```yaml
# .github/workflows/daily-cost-analysis.yml
name: Daily Token Cost Analysis

on:
  schedule:
    - cron: '0 9 * * *'  # Daily at 9 AM UTC
  workflow_dispatch:

jobs:
  cost-analysis:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Install Crashlens
      run: pip install crashlens
      
    - name: Fetch Yesterday's Logs
      env:
        LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
        LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
      run: |
        # Fetch logs from yesterday
        crashlens fetch-langfuse --days 1 --output yesterday-logs.jsonl
        
    - name: Generate Cost Report
      run: |
        crashlens policy-check yesterday-logs.jsonl \
          --policy-template budget-protection \
          --format markdown > daily-cost-report.md
          
    - name: Send Slack Alert (if violations found)
      if: failure()
      uses: 8398a7/action-slack@v3
      with:
        status: failure
        text: "⚠️ Token waste detected in yesterday's usage!"
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## 🛠️ **COMMAND REFERENCE**

### **Core Commands**

#### **`crashlens policy-check`**
Check log files against policy rules.

```bash
# Basic usage
crashlens policy-check logs.jsonl

# With specific template
crashlens policy-check logs.jsonl --policy-template retry-loop-prevention

# Multiple options
crashlens policy-check logs.jsonl \
  --policy-template all \
  --severity-threshold high \
  --fail-on-violations \
  --format markdown
```

**Options:**
- `--policy-template`: Template to use (or 'all')
- `--severity-threshold`: Minimum severity (low/medium/high/critical)
- `--fail-on-violations`: Exit with error code on violations
- `--format`: Output format (slack/markdown/json)

#### **`crashlens simulate`**
Generate realistic test data for policy testing.

```bash
# Basic simulation
crashlens simulate --output test.jsonl --count 100

# Advanced simulation
crashlens simulate \
  --output advanced-test.jsonl \
  --count 500 \
  --scenario retry-loop \
  --models "gpt-4o,gpt-3.5-turbo" \
  --error-rate 0.2 \
  --seed 42
```

**Options:**
- `--output`: Output file path (required)
- `--count`: Number of traces to generate (default: 100)
- `--scenario`: Scenario type (normal/retry-loop/model-overkill/slow/mixed-errors)
- `--models`: Comma-separated model list
- `--error-rate`: Error probability 0-1 (default: 0.2)
- `--seed`: Random seed for deterministic output
- `--force`: Overwrite existing files
- `--open`: Run policy-check after generation

#### **`crashlens init`**
Initialize Crashlens configuration.

```bash
# Interactive setup
crashlens init

# Non-interactive with environment variables
crashlens init --non-interactive

# Generate workflow only
crashlens init --dry-run-workflow
```

**Options:**
- `--non-interactive`: Use environment variables
- `--dry-run-workflow`: Print workflow YAML to stdout

#### **`crashlens list-policy-templates`**
List available policy templates.

```bash
crashlens list-policy-templates
```

#### **`crashlens fetch-langfuse`**
Fetch traces from Langfuse API.

```bash
# Fetch recent traces
crashlens fetch-langfuse --days 7 --output langfuse-logs.jsonl

# With filtering
crashlens fetch-langfuse \
  --days 30 \
  --output filtered-logs.jsonl \
  --user-id "user123" \
  --limit 1000
```

#### **`crashlens fetch-helicone`**
Fetch requests from Helicone API.

```bash
crashlens fetch-helicone --days 7 --output helicone-logs.jsonl
```

### **Environment Variables Reference**

#### **Configuration Variables:**
```bash
CRASHLENS_TEMPLATES="template1,template2"    # Policy templates
CRASHLENS_SEVERITY="high"                    # Severity threshold  
CRASHLENS_FAIL_ON_VIOLATIONS="true"          # Fail behavior
CRASHLENS_LOGS_SOURCE="langfuse"             # Log source
CRASHLENS_CREATE_WORKFLOW="false"            # Create workflow
CRASHLENS_OUTPUT_DIRECTORY="./reports"       # Output directory
```

#### **API Keys:**
```bash
LANGFUSE_SECRET_KEY="lf_sk_..."              # Langfuse secret key
LANGFUSE_PUBLIC_KEY="lf_pk_..."              # Langfuse public key
HELICONE_API_KEY="sk-helicone-..."           # Helicone API key
OPENAI_API_KEY="sk-..."                      # OpenAI API key
```

---

## 🚨 **TROUBLESHOOTING**

### **Common Issues and Solutions**

#### **1. "crashlens command not found"**
```bash
# Check if installed
pip list | grep crashlens

# If not installed
pip install crashlens

# If using poetry
poetry add crashlens
poetry run crashlens --version
```

#### **2. "No log files found"**
```bash
# Generate test data
crashlens simulate --output test-logs.jsonl --count 50

# Check file paths
ls -la *.jsonl
find . -name "*.jsonl" -type f
```

#### **3. "Policy template not found"**
```bash
# List available templates
crashlens list-policy-templates

# Use correct template name
crashlens policy-check logs.jsonl --policy-template retry-loop-prevention
```

#### **4. "Invalid JSON in log file"**
```bash
# Validate JSONL format
python -c "
import json
with open('logs.jsonl', 'r') as f:
    for i, line in enumerate(f, 1):
        try:
            json.loads(line)
        except json.JSONDecodeError as e:
            print(f'Line {i}: {e}')
"
```

#### **5. "GitHub Actions workflow fails"**
```bash
# Check workflow syntax
# Use GitHub Actions validator or:
yamllint .github/workflows/crashlens.yml

# Check secrets are set
# Go to Settings > Secrets and variables > Actions

# Test locally first
crashlens policy-check test-logs.jsonl --policy-template all
```

#### **6. "Permission denied" errors**
```bash
# Check file permissions
ls -la .crashlens/

# Fix permissions
chmod 755 .crashlens/
chmod 644 .crashlens/config.yaml
```

### **Debug Mode and Verbose Output**

Enable detailed logging for troubleshooting:

```bash
# Enable verbose output (if available)
CRASHLENS_DEBUG=1 crashlens policy-check logs.jsonl

# Check Python environment
python -c "
import sys
print('Python version:', sys.version)
print('Python path:', sys.path)

try:
    import crashlens
    print('Crashlens version:', crashlens.__version__)
except ImportError as e:
    print('Crashlens import error:', e)
"
```

### **Performance Optimization**

For large log files:

```bash
# Split large files
split -l 1000 large-logs.jsonl small-logs-

# Process in parallel (if supported)
ls small-logs-* | xargs -P 4 -I {} crashlens policy-check {}

# Use specific templates only
crashlens policy-check logs.jsonl --policy-template retry-loop-prevention
```

---

## 📚 **ADVANCED USAGE EXAMPLES**

### **Multi-Environment Setup**

#### **Development Environment**
```yaml
# .crashlens/config.dev.yaml
policy_template: retry-loop-prevention,model-overkill-detection
severity_threshold: medium
fail_on_violations: false
logs_source: local
```

#### **Staging Environment**
```yaml
# .crashlens/config.staging.yaml
policy_template: all
severity_threshold: high
fail_on_violations: true
logs_source: langfuse
```

#### **Production Environment**
```yaml
# .crashlens/config.prod.yaml
policy_template: budget-protection,error-handling-efficiency
severity_threshold: critical
fail_on_violations: true
logs_source: helicone
```

#### **Environment-Specific Workflows**
```yaml
# .github/workflows/crashlens-multi-env.yml
name: Multi-Environment Token Waste Check

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test-environments:
    strategy:
      matrix:
        environment: [dev, staging, prod]
    
    runs-on: ubuntu-latest
    environment: ${{ matrix.environment }}
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
        
    - name: Install Crashlens
      run: pip install crashlens
      
    - name: Use Environment Config
      run: |
        if [ -f ".crashlens/config.${{ matrix.environment }}.yaml" ]; then
          cp .crashlens/config.${{ matrix.environment }}.yaml .crashlens/config.yaml
        fi
        
    - name: Run Environment-Specific Check
      run: crashlens policy-check logs/*.jsonl --policy-template all
```

### **Custom Reporting and Notifications**

#### **Slack Integration**
```yaml
- name: Send Slack Notification
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: failure
    custom_payload: |
      {
        "text": "🚨 Token waste detected!",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Token Waste Alert*\n• Repository: ${{ github.repository }}\n• Branch: ${{ github.ref }}\n• Commit: ${{ github.sha }}"
            }
          }
        ]
      }
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

#### **Email Notifications**
```yaml
- name: Send Email Alert
  if: failure()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.MAIL_USERNAME }}
    password: ${{ secrets.MAIL_PASSWORD }}
    subject: "🚨 Token Waste Detected in ${{ github.repository }}"
    body: |
      Token waste patterns were detected in your GPT API usage.
      
      Repository: ${{ github.repository }}
      Branch: ${{ github.ref }}
      Commit: ${{ github.sha }}
      
      Please review the attached report and optimize your API usage.
    to: team@company.com
    from: alerts@company.com
```

### **Integration with Other Tools**

#### **Datadog Integration**
```yaml
- name: Send Metrics to Datadog
  run: |
    # Extract metrics from report
    VIOLATIONS=$(crashlens policy-check logs.jsonl --format json | jq '.violations | length')
    
    # Send to Datadog
    curl -X POST "https://api.datadoghq.com/api/v1/series" \
      -H "Content-Type: application/json" \
      -H "DD-API-KEY: ${{ secrets.DATADOG_API_KEY }}" \
      -d "{
        \"series\": [{
          \"metric\": \"crashlens.violations\",
          \"points\": [[$(date +%s), $VIOLATIONS]],
          \"tags\": [\"env:${{ github.ref }}\", \"repo:${{ github.repository }}\"]
        }]
      }"
```

#### **Grafana Dashboard Data**
```bash
# Export metrics for Grafana
crashlens policy-check logs.jsonl --format json > metrics.json

# Process for Grafana
python scripts/process-for-grafana.py metrics.json > grafana-metrics.json
```

---

## 🔄 **MAINTENANCE AND UPDATES**

### **Keeping Crashlens Updated**

#### **Check for Updates**
```bash
# Check current version
crashlens --version

# Update with pip
pip install --upgrade crashlens

# Update with poetry
poetry update crashlens
```

#### **Version Pinning for Stability**
```yaml
# pyproject.toml
[tool.poetry.dependencies]
crashlens = "^2.5.1"  # Pin to specific version

# requirements.txt
crashlens==2.5.1
```

### **Configuration Maintenance**

#### **Regular Config Review**
```bash
# Review current configuration
cat .crashlens/config.yaml

# Update templates as new ones become available
crashlens list-policy-templates

# Regenerate config with new templates
crashlens init --non-interactive
```

#### **Workflow Updates**
```bash
# Update workflow to use latest actions
# Review .github/workflows/crashlens.yml periodically

# Test workflow changes locally
act -j crashlens-check  # Using nektos/act
```

### **Monitoring and Alerting**

#### **Weekly Review Workflow**
```yaml
name: Weekly Crashlens Review

on:
  schedule:
    - cron: '0 10 * * 1'  # Monday 10 AM

jobs:
  weekly-review:
    runs-on: ubuntu-latest
    steps:
    - name: Generate Weekly Report
      run: |
        # Fetch week's data
        crashlens fetch-langfuse --days 7 --output weekly-logs.jsonl
        
        # Generate comprehensive report
        crashlens policy-check weekly-logs.jsonl --policy-template all --format markdown > weekly-report.md
        
    - name: Create Issue if Problems Found
      if: failure()
      uses: actions/github-script@v7
      with:
        script: |
          github.rest.issues.create({
            owner: context.repo.owner,
            repo: context.repo.repo,
            title: '📊 Weekly Token Waste Review - Issues Found',
            body: 'Automated weekly review found token waste patterns. Please investigate.',
            labels: ['token-waste', 'review-needed']
          })
```

---

## 🎓 **LEARNING RESOURCES**

### **Understanding Token Waste Patterns**

#### **Common Patterns Crashlens Detects:**

1. **Retry Loops**
   - Same prompt sent multiple times
   - Often indicates error handling issues
   - Can waste 3-10x normal token usage

2. **Model Overkill**  
   - Using GPT-4 for simple tasks that GPT-3.5 could handle
   - Can increase costs by 20-60x
   - Common with "always use best model" strategies

3. **Inefficient Context Management**
   - Sending full conversation history every time
   - Not truncating old context
   - Can lead to exponential token growth

4. **Poor Error Handling**
   - Retrying failed requests without exponential backoff
   - Not handling rate limits properly
   - Continuing to send requests after consistent failures

### **Best Practices for Token Efficiency**

#### **1. Smart Model Selection**
```python
# Good: Route based on complexity
def get_model_for_task(task_complexity):
    if task_complexity == "simple":
        return "gpt-3.5-turbo"
    elif task_complexity == "complex":
        return "gpt-4"
    else:
        return "gpt-4o"

# Bad: Always use most expensive
def get_model_for_task(task_complexity):
    return "gpt-4"  # Wastes money on simple tasks
```

#### **2. Efficient Retry Logic**
```python
# Good: Exponential backoff
import time
import random

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            if attempt < max_retries - 1:
                sleep_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(sleep_time)
            else:
                raise

# Bad: Immediate retry
def bad_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except:
            continue  # Immediate retry wastes API calls
```

#### **3. Context Management**
```python
# Good: Truncate old context
def manage_context(conversation, max_tokens=2000):
    while count_tokens(conversation) > max_tokens:
        conversation.pop(1)  # Remove old messages (keep system prompt)
    return conversation

# Bad: Send everything every time
def bad_context_management(conversation):
    return conversation  # Could grow infinitely
```

### **Reading Policy Reports**

#### **Understanding Report Output**
```markdown
## Token Waste Analysis Report

### 🚨 High Severity Issues (3 found)
- **Retry Loop Detected**: Same prompt "What is 2+2?" sent 5 times
  - Cost Impact: $0.15 wasted
  - Recommendation: Implement exponential backoff

- **Model Overkill**: GPT-4 used for simple math question  
  - Cost Impact: 20x more expensive than needed
  - Recommendation: Use GPT-3.5-turbo for simple tasks

### ⚠️ Medium Severity Issues (2 found)
- **Long Context**: 8,000 tokens sent in single request
  - Recommendation: Implement context truncation

### 📊 Usage Summary
- Total Traces Analyzed: 1,247
- Total Cost: $45.67
- Potential Savings: $12.34 (27%)
- Efficiency Score: 73/100
```

---

## 📞 **SUPPORT AND COMMUNITY**

### **Getting Help**

#### **Documentation**
- 📖 Full documentation: [Available in repository]
- 🎯 Quick start guide: See "Quick Start" section above
- 🔧 API reference: Use `crashlens command --help`

#### **Community Support**
- 💬 GitHub Discussions: Post questions and share experiences  
- 🐛 Issues: Report bugs and request features on GitHub
- 📧 Email: Contact maintainers for enterprise support

#### **Contributing**
```bash
# Fork the repository
git clone https://github.com/YOUR-USERNAME/crashlens.git

# Create feature branch
git checkout -b feature/new-policy-template

# Install development dependencies
poetry install --with dev

# Run tests
poetry run pytest

# Submit pull request
```

### **Feedback and Feature Requests**

Help improve Crashlens by:
- ⭐ Starring the repository if you find it useful
- 🐛 Reporting bugs with detailed reproduction steps
- 💡 Suggesting new policy templates or features
- 📝 Contributing documentation improvements
- 🧪 Sharing usage patterns and success stories

---

## 🎉 **SUCCESS CHECKLIST**

By following this manual, you should have:

- [ ] ✅ Crashlens installed and version confirmed
- [ ] ✅ Configuration created with appropriate policy templates  
- [ ] ✅ GitHub Actions workflow set up and running
- [ ] ✅ Secrets configured for API access
- [ ] ✅ Test data generated and policies tested
- [ ] ✅ Local development workflow integrated
- [ ] ✅ Monitoring and alerting configured
- [ ] ✅ Team trained on interpreting reports

### **Validation Commands**
```bash
# Final verification
crashlens --version                                    # Should show 2.5.1+
crashlens list-policy-templates | wc -l               # Should show 10+ templates  
ls .crashlens/config.yaml                             # Config file exists
ls .github/workflows/crashlens.yml                    # Workflow file exists
crashlens simulate --output test.jsonl --count 10     # Generates test data
crashlens policy-check test.jsonl --policy-template all  # Runs successfully
```

**🎊 Congratulations! You now have a complete Crashlens setup that will help you optimize your GPT API usage and prevent token waste!**

---

*This manual covers Crashlens v2.5.1. For the latest updates and features, visit the official repository.*
