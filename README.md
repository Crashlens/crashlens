# 💰 CrashLens - AI Cost Policy Enforcement

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-3.0.0-green.svg)](https://github.com/crashlens/crashlens)

## 🧠 What is CrashLens?

CrashLens is a **policy-driven AI cost optimization tool** that enforces custom **YAML rules** to prevent LLM waste, detect retry loops, and optimize model usage. Instead of hardcoded detection logic, you define your own policies to match your team's budget and usage requirements.

#### 🔍 Use it when you want to:

- **Enforce cost policies** with custom YAML rules
- **Prevent budget overruns** before they happen
- **Detect retry loops** and fallback inefficiencies  
- **Optimize model selection** based on usage patterns
- **Generate compliance reports** for team analysis
- **Integrate with CI/CD** for automated enforcement

🧾 **Supports**: OpenAI, Anthropic, Langfuse JSONL logs  
💻 **Platform**: 100% CLI, 100% local, policy-driven

---

### 💡 Why use CrashLens v3.0?

> **"Policy-driven cost control beats reactive monitoring."**
> 
> CrashLens v3.0 replaces hardcoded detection logic with flexible YAML policies, giving you complete control over what gets flagged and how your team manages AI costs.

---

## 👨‍💻 Use Cases

- **Budget enforcement**: Custom spending thresholds and model restrictions
- **Retry loop detection**: Configurable retry count limits and patterns
- **Model optimization**: Flag expensive models for simple tasks
- **Compliance reporting**: Generate audit trails for cost governance  
- **CI/CD integration**: Prevent bad patterns from reaching production
- **Team policy management**: Shared YAML configs across projects

---

## TL;DR

```sh
pip install crashlens
crashlens scan logs.jsonl --policy budget.yaml
# Enforces your custom YAML policies and generates detailed reports
```

---

## ⚠️ Python Requirement

CrashLens requires **Python 3.12 or higher**. [Download Python 3.12+ here.](https://www.python.org/downloads/)

---

## ⚠️ Windows PATH Warning

If you see a warning like:

```
WARNING: The script crashlens.exe is installed in 'C:\Users\<user>\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\Scripts' which is not on PATH.
Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
```

This means the `crashlens` command may not work from any folder until you add the above Scripts directory to your system PATH.

**How to fix:**
1. Copy the path shown in the warning (ending with `\Scripts`).
2. Open the Windows Start menu, search for "Environment Variables", and open "Edit the system environment variables".
3. Click "Environment Variables...".
4. Under "User variables" or "System variables", select `Path` and click "Edit".
5. Click "New" and paste the Scripts path.
6. Click OK to save. Restart your terminal/command prompt.

Now you can run `crashlens` from any folder.

---

**CrashLens** enforces YAML-based policies to detect violations, analyze costs, and prevent wasteful patterns. It generates detailed reports with policy-specific recommendations and actionable insights.

## 📝 Example Policy-Based Analysis

Below is what CrashLens outputs when policy violations are detected:

```
❌ Policy Violations Found

🚨 excessive-retries (HIGH): 3 violations
   💰 Estimated waste: $0.45
   � Implement circuit breaker to avoid retry storms
   � Lines: 15, 23, 31

⚠️  high-cost-threshold (MEDIUM): 1 violation  
   💰 Estimated cost: $1.25
   � Consider breaking down expensive requests
   � Lines: 8

✅ Cost Analysis Summary:
   Total Spend: $2.34
   Policy Violations: 4
   Estimated Savings: $0.68
```



---

## 🚀 Features

### ✅ **Policy-Driven Architecture** 
- **Custom YAML rules** instead of hardcoded detection
- **Flexible matching** with operators: `>`, `<`, `==`, `in`, `regex`
- **Configurable actions**: `fail`, `warn`, `ignore`
- **Rich metadata**: severity levels, suggestions, rule IDs

### ✅ **Enterprise-Ready**
- **License gating** for premium policy features
- **CI/CD integration** with GitHub Actions
- **Multiple output formats**: JSON, Markdown, Slack
- **Cost estimation** with token-level pricing

### ✅ **Developer Experience**
- **Policy validation**: `crashlens validate-policy budget.yaml`
- **Log file info**: `crashlens info logs.jsonl`
- **Debug output**: `--debug-license`, `--verbose`
- **Local execution**: No data leaves your machine

---

## 1. Clone the Repository

Replace `<repo-link>` with the actual GitHub URL:

```sh
git clone <repo-link>
cd crashlens
```

---

## 2. Install Python & Poetry

CrashLens requires **Python 3.8+** and [Poetry](https://python-poetry.org/) for dependency management.

### MacOS
- Install Python (if not already):
  ```sh
  brew install python@3.12
  ```
- Install Poetry (stable version):
  ```sh
  curl -sSL https://install.python-poetry.org | python3 - --version 1.8.2
  # Or with Homebrew:
  brew install poetry
  ```
- Add Poetry to your PATH if needed:
  ```sh
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zprofile
  source ~/.zprofile
  ```
- Verify installation:
  ```sh
  poetry --version
  # Should show: Poetry (version 1.8.2)
  ```

### Windows
⚠️ **Use PowerShell, not CMD, for these commands.**

- Install Python from [python.org](https://www.python.org/downloads/)
- Install Poetry (stable version):
  ```powershell
  (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python - --version 1.8.2
  ```
- Add Poetry to your PATH if `poetry --version` returns "not found":
  ```powershell
  $userPoetryBin = "$HOME\AppData\Roaming\Python\Scripts"
  
  if (Test-Path $userPoetryBin -and -not ($env:Path -like "*$userPoetryBin*")) {
      $env:Path += ";$userPoetryBin"
      [Environment]::SetEnvironmentVariable("Path", $env:Path, "User")
      Write-Output "✅ Poetry path added. Restart your terminal."
  } else {
      Write-Output "⚠️ Poetry path not found or already added. You may need to locate poetry.exe manually."
  }
  ```
  **⚠️ Restart your terminal/PowerShell after adding to PATH.**
- Verify installation:
  ```powershell
  poetry --version
  # Should show: Poetry (version 1.8.2)
  ```

---

## 3. Set Up the Environment

```sh
# From the project root:
poetry install
```

This will create a virtual environment and install all dependencies.

To activate the environment :
  ```sh
  poetry shell
  ```

---

## 4. Running CrashLens

You can run CrashLens via Poetry or as a Python module:

### Basic Scan (from file)
```sh
crashlens scan examples/retry-test.jsonl --policy budget.yaml
```

### Policy Validation
```sh
crashlens validate-policy budget.yaml
```

### Demo Mode (built-in sample data)
```sh
crashlens scan --demo --policy crashlens/config/crashlens-policy.yaml
```

```
🚨 **CrashLens Token Waste Report** 🚨
📊 Analysis Date: 2025-07-31 15:22:08

| Metric | Value |
|--------|-------|
| Total AI Spend | $0.09 |
| Total Potential Savings | $0.07 |
| Wasted Tokens | 1,414 |
| Issues Found | 8 |
| Traces Analyzed | 12 |

📢 **Fallback Failure** | 5 traces | $0.07 wasted | Fix: remove redundant fallbacks
   🎯 **Wasted tokens**: 1,275
   🔗 **Traces** (5): demo_fallback_01, demo_fallback_02, demo_fallback_03, demo_fallback_04, demo_fallback_05

❓ **Overkill Model** | 2 traces | $0.0007 wasted | Fix: optimize usage
   🎯 **Wasted tokens**: 31
   🔗 **Traces** (2): demo_overkill_01, demo_overkill_02

🔄 **Retry Loop** | 1 traces | $0.0002 wasted | Fix: exponential backoff
   🎯 **Wasted tokens**: 108
   🔗 **Traces** (1): demo_retry_01


## Top Expensive Traces

| Rank | Trace ID | Model | Cost |
|------|----------|-------|------|
| 1 | demo_norm_03 | gpt-4 | $0.03 |
| 2 | demo_norm_04 | gpt-4 | $0.02 |
| 3 | demo_fallback_05 | gpt-3.5-turbo | $0.02 |

## Cost by Model

| Model | Cost | Percentage |
|-------|------|------------|
| gpt-4 | $0.09 | 99% |
| gpt-3.5-turbo | $0.0012 | 1% |



---

## Why CrashLens v3.0? (vs. grep + Excel, LangSmith, or basic logging)

- 🔁 **grep + spreadsheet**: Too manual, error-prone, no cost context
- 💸 **LangSmith**: Powerful but complex, requires full tracing/observability stack
- 🔍 **Logging without cost visibility**: You miss $ waste and optimization opportunities
- � **CrashLens v3.0**: Policy-driven rules, flexible enforcement, 100% local execution

---

## Features (Policy-Driven v3.0)

- ✅ **YAML Policy Engine**: Define custom rules instead of hardcoded detection
- ✅ **Flexible Matching**: Operators like `>`, `<`, `==`, `in`, `regex` for any log field
- ✅ **Configurable Actions**: `fail`, `warn`, `ignore` with custom severity levels
- ✅ **Enterprise Features**: License gating, CI/CD integration, multiple output formats
- ✅ **Local Execution**: No data transmission, complete privacy

---

## What Makes CrashLens v3.0 Different?

- � **Policy-first architecture** (define your own rules in YAML)
- 🔒 **Security-by-design** (runs 100% locally, no API calls, no data leaves your machine)
- 🚦 **Enterprise-ready**: License management, CI/CD workflows, team policies



## 📄 Log File Structure

**Your logs must be in JSONL format (one JSON object per line) and follow this structure:**

```json
{"traceId": "trace_9", "model": "gpt-3.5-turbo", "usage": {"prompt_tokens": 25, "completion_tokens": 110, "total_tokens": 135}, "cost": 0.000178}
```

- Each line is a separate API call (no commas or blank lines between objects).
- Fields can be nested or flat depending on your logging format.

**Required fields for policy matching:**
- `traceId` (string): Unique identifier for a group of related API calls
- `model` (string): Model name (e.g., `gpt-4`, `gpt-3.5-turbo`)
- `usage.total_tokens` (int): Number of tokens used
- Any fields referenced in your YAML policy rules

**Optional fields:**
- `cost` (float): Cost of the API call
- `retry_count` (int): Number of retries for this request
- `startTime`, `endTime`, etc.: Any other metadata

💡 CrashLens expects JSONL with per-call metrics (model, tokens, cost). Works with LangChain logs, OpenAI api.log, Claude, Gemini, and more.

---

## 🚀 Usage: Command Line Examples

After installation, use the `crashlens` command in your terminal (or `python -m crashlens` if running from source).

### 1. **Scan with policy enforcement**
```sh
crashlens scan path/to/your-logs.jsonl --policy budget.yaml
```
- Scans the specified log file using your YAML policy and generates a detailed report.

### 2. **Validate policy files**
```sh
crashlens validate-policy budget.yaml
```
- Validates your YAML policy syntax and rules before using it.

### 3. **Get log file information**
```sh
crashlens info path/to/your-logs.jsonl
```
- Shows statistics about your log file (number of entries, models used, etc.).

### 4. **Demo mode (built-in sample data)**
```sh
crashlens scan --demo --policy crashlens/config/crashlens-policy.yaml
```
- Runs analysis on built-in example logs with the default policy.

### 5. **Policy enforcement with CI/CD**
```sh
crashlens scan logs.jsonl --policy budget.yaml --fail-on-policy
```
- Fails with exit code 1 if policy violations are found (perfect for CI/CD).

### 6. **Multiple output formats**
```sh
crashlens scan logs.jsonl --policy budget.yaml --output json
crashlens scan logs.jsonl --policy budget.yaml --output markdown
```
- Generate reports in different formats for automation or documentation.

### 7. **Debug and licensing**
```sh
crashlens scan logs.jsonl --policy budget.yaml --debug-license
```
- Debug licensing issues and premium policy features.

### 8. **Get help**
```sh
crashlens --help
crashlens scan --help
crashlens validate-policy --help
```
- Shows all available options and usage details.

---

## ✅ GitHub Actions Integration (CI)

CrashLens can validate logs during CI to prevent bad traces from entering production.

### Example Workflow (`.github/workflows/log-check.yml`)
```yaml
name: Check Langfuse Logs

on:
  push:
    paths:
      - logs/**
  workflow_dispatch:

jobs:
  validate-logs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install CrashLens
        run: pip install crashlens

      # Schema Contract Validation
      - name: Contract Check
        run: |
          echo "## 📋 Schema Validation" >> $GITHUB_STEP_SUMMARY
          crashlens scan logs/*.jsonl \
            --contract-check \
            --log-format langfuse-v1 \
            --output markdown >> $GITHUB_STEP_SUMMARY
            
      # Policy Enforcement  
      - name: Policy Check
        run: |
          echo "## 🚨 Policy Violations" >> $GITHUB_STEP_SUMMARY
          crashlens scan logs/*.jsonl \
            --policy policies/budget.yaml \
            --log-format langfuse-v1 \
            --output markdown \
            --summary-only \
            --fail-on-policy >> $GITHUB_STEP_SUMMARY
            
      # Token Waste Analysis
      - name: Waste Analysis
        run: |
          echo "## 💰 Cost Analysis" >> $GITHUB_STEP_SUMMARY
          crashlens scan logs/*.jsonl \
            --log-format langfuse-v1 \
            --summary-only >> $GITHUB_STEP_SUMMARY
```

This comprehensive workflow validates schema contracts, enforces policies, and analyzes token waste!

### CI Integration Features

- **📋 Contract Validation**: Enforce schema contracts with `--contract-check`
- **🚨 Policy Enforcement**: Custom YAML policies with `--policy` and `--fail-on-policy`
- **📊 Markdown Output**: CI-friendly tables with `--output markdown`
- **🔄 Exit Codes**: Proper CI failure handling with non-zero exit codes
- **📈 GitHub Summary**: Rich markdown reports in `$GITHUB_STEP_SUMMARY`

### Schema Contract Validation
```bash
# Basic schema validation
crashlens scan logs.jsonl --contract-check

# Markdown table output for CI
crashlens scan logs.jsonl --contract-check --output markdown

# JSON output for automation
crashlens scan logs.jsonl --contract-check --output json
```

### Policy Enforcement
```bash
# Basic policy check
crashlens scan logs.jsonl --policy policies/budget.yaml

# Fail CI on policy violations
crashlens scan logs.jsonl --policy policies/budget.yaml --fail-on-policy

# Markdown output for CI summaries
crashlens scan logs.jsonl --policy policies/budget.yaml --output markdown --summary-only
```

### Example CI Outputs

**Contract Violations:**
```markdown
❌ **Contract Check Failed**
| Line | Rule ID | Error Message |
|------|---------|---------------|
| 2 | missing-field | Missing required field 'traceId' |
| 3 | invalid-type | Field 'startTime' has incorrect type |
**Found 2 violation(s) across 3 log entries.**
```

**Policy Violations:**
```markdown
❌ **Policy Violations Found**
| Rule ID | Severity | Action | Reason | Suggestion |
|---------|----------|--------|--------|------------|
| excessive-retries | high | fail | retry_count=6 (rule: >=5) | Implement circuit breaker |
| token-limit-exceeded | medium | warn | usage.total_tokens=15000 | Break down large prompts |
**Found 2 policy violation(s).**
```

---

## 🧩 Example Workflow

1. **Install CrashLens:**
   ```sh
   pip install crashlens
   # OR clone and install from source as above
   ```
2. **Scan your logs:**
   ```sh
   crashlens scan path/to/your-logs.jsonl
   # OR
   python -m crashlens scan path/to/your-logs.jsonl
   ```
3. **Open `report.md`** in your favorite Markdown viewer or editor to review the findings and suggestions.

---

## 📝 Logging Helper

To make log analysis seamless, you can use our [`crashlens-logger`](https://github.com/Crashlens/logger) package to emit logs in the correct structure for CrashLens. This ensures compatibility and reduces manual formatting.

**Example usage:**
```sh
pip install --upgrade crashlens_logger
```
```python
from crashlens_logger import CrashLensLogger

logger = CrashLensLogger()
logger.log_event(
    traceId=trace_id,
    startTime=start_time,
    endTime=end_time,
    input={"model": model, "prompt": prompt},
    usage=usage
    # Optionally add: type, level, metadata, name, etc.
)
```

- The logger writes each call as a JSONL line in the required format.
- See the [`crashlens-logger` repo](https://github.com/Crashlens/logger) for full docs and advanced usage.

---

## 🆘 Troubleshooting & Tips

- **File not found:** Make sure the path to your log file is correct.
- **No traces found:** Your log file may be empty or not in the expected format.
- **Cost is $0.00:** Check that your log’s model names match those in the pricing config.
- **Virtual environment issues:** Make sure you’re using the right Python environment.
- **Need help?** Use `crashlens --help` for all options.

---

## 🛠️ Full Installation (Advanced/Dev)

### **Alternative: Install from Source (GitHub)**

If you want the latest development version or want to contribute, you can install CrashLens from source:

1. **Clone the repository:**
   ```sh
   git clone <repo-link>
   cd crashlens
   ```
2. **(Optional but recommended) Create a virtual environment:**
   - **On Mac/Linux:**
     ```sh
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - **On Windows:**
     ```sh
     python -m venv .venv
     .venv\Scripts\activate
     ```
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   # Or, if using Poetry:
   poetry install
   ```
4. **Run CrashLens:**
   ```sh
   python -m crashlens scan path/to/your-logs.jsonl
   # Or, if using Poetry:
   poetry run crashlens scan path/to/your-logs.jsonl
   ```

---

## 📬 Support
For questions, issues, or feature requests, open an issue on GitHub or contact the maintainer.

---

## 📄 License
MIT License - see LICENSE file for details.

---

**CrashLens: Find your wasted tokens. Save money. Optimize your AI usage.** 

### Scan from stdin (pipe or paste)
```sh
cat examples/retry-test.jsonl | poetry run crashlens scan --stdin
```

---

## 5. Output: The Markdown Report

After every scan, CrashLens creates or updates `report.md` in your current directory.

### Example Structure
```
# CrashLens Token Waste Report

🧾 **Total AI Spend**: $0.123456
💰 **Total Potential Savings**: $0.045678

| Trace ID | Model | Prompt | Completion Length | Cost | Waste Type |
|----------|-------|--------|------------------|------|------------|
| trace_001 | gpt-4 | ... | 3 | $0.00033 | Overkill |
| ...      | ...   | ...    | ...              | ...  | ...        |

## Overkill Model Usage (5 issues)
- ...

## Retry Loops (3 issues)
- ...

## Fallback Failures (2 issues)
- ...
```

---

## 6. Troubleshooting
- **File not found:** Ensure the path to your log file is correct.
- **No traces found:** Your log file may be empty or malformed.
- **Cost is $0.00:** Check that your `pricing.yaml` matches the model names in your logs.
- **Virtual environment issues:** Use `poetry run` to ensure dependencies are available.

---

## 7. Example Commands

```sh
# Scan a log file
poetry run crashlens scan examples/demo-logs.jsonl

# Use demo data
poetry run crashlens scan --demo

# Scan from stdin
cat examples/demo-logs.jsonl | poetry run crashlens scan --stdin
```

---

## 📚 Complete Command Reference

### Basic Usage
```sh
crashlens scan [OPTIONS] [LOGFILE]
```

### 🎯 Examples
```sh
# Scan a specific log file
crashlens scan logs.jsonl

# Run on built-in sample logs
crashlens scan --demo

# Pipe logs via stdin
cat logs.jsonl | crashlens scan --stdin

# Read logs from clipboard
crashlens scan --paste

# Generate detailed category JSON reports
crashlens scan --detailed

# Cost summary with categories
crashlens scan --summary

# Show summary only (no trace details)
crashlens scan --summary-only
```

### 🔧 All Options

| Option | Description | Example |
|--------|-------------|---------|
| `-f, --format` | Output format: `slack`, `markdown`, `json` | `--format json` |
| `-c, --config` | Custom pricing config file path | `--config my-pricing.yaml` |
| `--demo` | Use built-in demo data (requires examples-logs/demo-logs.jsonl) | `crashlens scan --demo` |
| `--stdin` | Read from standard input | `cat logs.jsonl \| crashlens scan --stdin` |
| `--paste` | Read JSONL data from clipboard | `crashlens scan --paste` |
| `--summary` | Show cost summary with breakdown | `crashlens scan --summary` |
| `--summary-only` | Summary without trace IDs | `crashlens scan --summary-only` |
| `--detailed` | Generate detailed category JSON reports | `crashlens scan --detailed` |
| `--detailed-dir` | Directory for detailed reports (default: detailed_output) | `--detailed-dir my_reports` |
| `--help` | Show help message | `crashlens scan --help` |

### 📂 Detailed Reports
When using `--detailed`, CrashLens generates grouped category files:
- `detailed_output/fallback_failure.json` - All fallback failure issues
- `detailed_output/retry_loop.json` - All retry loop issues  
- `detailed_output/fallback_storm.json` - All fallback storm issues
- `detailed_output/overkill_model.json` - All overkill model issues

Each file contains:
- Summary with total issues, affected traces, costs
- All issues of that type with trace IDs and details
- Specific suggestions for that category

### 🔍 Input Sources
CrashLens supports multiple input methods:

1. **File input**: `crashlens scan path/to/logs.jsonl`
2. **Demo mode**: `crashlens scan --demo` (requires examples-logs/demo-logs.jsonl file)
3. **Standard input**: `cat logs.jsonl | crashlens scan --stdin`
4. **Clipboard**: `crashlens scan --paste` (paste logs interactively)

### 📊 Output Formats
- **slack** (default): Slack-formatted report for team sharing
- **markdown**: Clean Markdown for documentation
- **json**: Machine-readable JSON for automation

### 💡 Pro Tips
- Use `--demo` to test CrashLens without your own logs
- Use `--detailed` to get actionable JSON reports for each issue category
- Use `--summary-only` for executive summaries without trace details
- Combine `--stdin` with shell pipelines for automation

---

## 8. Support
For questions, issues, or feature requests, open an issue on GitHub or contact the maintainer.

---

Enjoy using CrashLens! 🎯 

