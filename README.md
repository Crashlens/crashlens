## 🧠 What is CrashLens?


CrashLens is a developer tool to **analyze GPT API logs** and uncover hidden **token waste**, retry loops, and overkill model usage. It helps you **optimize your OpenAI, Anthropic, or Langfuse API usage** by generating a cost breakdown and **suggesting cost-saving actions**.

#### 🔍 Use it when you want to:

- Understand how your GPT API budget is being spent
- Reduce unnecessary model calls or retries
- Audit logs for fallback logic inefficiencies
- Analyze Langfuse/OpenAI JSONL logs locally, with full privacy

🧾 Supports: OpenAI, Anthropic, Langfuse JSONL logs  
💻 Platform: 100% CLI, 100% local

---

### 💡 Why use CrashLens?

> "You can't optimize what you can't see."
> CrashLens gives you visibility into how you're *actually* using LLMs — and how much it's costing you.

---

## 👨‍💻 Use Cases

- Track and reduce monthly OpenAI bills
- Debug retry loops and fallback logic in LangChain or custom agents
- Detect inefficient prompt-to-model usage (e.g., using GPT-4 for 3-token completions)
- Generate token audit logs for compliance or team analysis
- CLI tool to audit GPT usage and optimize OpenAI API costs
- Analyze GPT token usage and efficiency in LLM logs
- Reduce LLM spending with actionable insights

---

## TL;DR

```sh
pip install crashlens
crashlens scan path/to/your-logs.jsonl
# Generates report.md with per-trace waste, cost, and suggestions
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

**CrashLens** analyzes your logs for patterns like fallback failures, retry loops, and overkill model usage, and generates a detailed Markdown report (`report.md`) with cost breakdowns and actionable insights.

## 📝 Example CrashLens Report

Below is a sample of what the actual `report.md` looks like after running CrashLens:

🚨 **CrashLens Token Waste Report** 🚨
📊 Analysis Date: 2025-07-31 15:24:48

| Metric | Value |
|--------|-------|
| Total AI Spend | $1.18 |
| Total Potential Savings | $0.82 |
| Wasted Tokens | 19,831 |
| Issues Found | 73 |
| Traces Analyzed | 156 |

❓ **Overkill Model** | 59 traces | $0.68 wasted | Fix: optimize usage
   🎯 **Wasted tokens**: 16,496
   🔗 **Traces** (57): trace_overkill_01, trace_norm_02, trace_overkill_02, trace_overkill_03, trace_norm_06, +52 more

📢 **Fallback Failure** | 7 traces | $0.08 wasted | Fix: remove redundant fallbacks
   🎯 **Wasted tokens**: 1,330
   🔗 **Traces** (7): trace_fallback_success_01, trace_fallback_success_02, trace_fallback_success_03, trace_fallback_success_04, trace_fallback_success_05, +2 more

⚡ **Fallback Storm** | 5 traces | $0.07 wasted | Fix: optimize model selection
   🎯 **Wasted tokens**: 1,877
   🔗 **Traces** (5): trace_fallback_failure_01, trace_fallback_failure_02, trace_fallback_failure_03, trace_fallback_failure_04, trace_fallback_failure_05

🔄 **Retry Loop** | 2 traces | $0.0001 wasted | Fix: exponential backoff
   🎯 **Wasted tokens**: 128
   🔗 **Traces** (2): trace_retry_loop_07, trace_retry_loop_10


## Top Expensive Traces

| Rank | Trace ID | Model | Cost |
|------|----------|-------|------|
| 1 | trace_norm_76 | gpt-4 | $0.09 |
| 2 | trace_norm_65 | gpt-4 | $0.07 |
| 3 | trace_norm_38 | gpt-4 | $0.06 |

## Cost by Model

| Model | Cost | Percentage |
|-------|------|------------|
| gpt-4 | $1.16 | 98% |
| gpt-3.5-turbo | $0.02 | 2% |



---

## 🚀 Features
- Detects token waste patterns: fallback failures, retry loops, overkill/short completions
- Supports OpenAI, Anthropic, and Langfuse-style logs (JSONL)
- Robust error handling for malformed or incomplete logs
- Configurable model pricing and thresholds via `pricing.yaml`
- Generates a professional Markdown report (`report.md`) after every scan
- 100% local: No data leaves your machine

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
crashlens scan examples/retry-test.jsonl
```

### Demo Mode (built-in sample data)
```sh
crashlens scan --demo

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

## Why CrashLens? (vs. grep + Excel, LangSmith, or basic logging)

- 🔁 **grep + spreadsheet**: Too manual, error-prone, no cost context
- 💸 **LangSmith**: Powerful but complex, requires full tracing/observability stack
- 🔍 **Logging without cost visibility**: You miss $ waste and optimization opportunities
- 🔒 **CrashLens runs 100% locally—no data leaves your machine.**

---

## Features (Ultra-Specific)

- ✅ Detects retry-loop storms across trace IDs
- ✅ Flags gpt-4, Claude, Gemini, and other expensive model usage where a cheaper model (e.g., gpt-3.5, Claude Instant) would suffice
- ✅ Scans stdin logs from LangChain, LlamaIndex, custom logging
- ✅ Generates Markdown cost reports with per-trace waste

---

## What Makes CrashLens Different?

- 💵 **Model pricing fallback** (auto-detects/corrects missing cost info)
- 🔒 **Security-by-design** (runs 100% locally, no API calls, no data leaves your machine)
- 🚦 **Coming soon**: Policy enforcement, live CLI firewall, more integrations



## 📄 Log File Structure

**Your logs must be in JSONL format (one JSON object per line) and follow this structure:**

```json
{"traceId": "trace_9",  "startTime": "2025-07-19T10:36:13Z", "input": {"model": "gpt-3.5-turbo", "prompt": "How do solar panels work?"}, "usage": {"prompt_tokens": 25, "completion_tokens": 110, "total_tokens": 135}, "cost": 0.000178}
```

- Each line is a separate API call (no commas or blank lines between objects).
- Fields must be nested as shown: `input.model`, `input.prompt`, `usage.completion_tokens`, etc.

**Required fields:**
- `traceId` (string): Unique identifier for a group of related API calls
- `input.model` (string): Model name (e.g., `gpt-4`, `gpt-3.5-turbo`)
- `input.prompt` (string): The prompt sent to the model
- `usage.completion_tokens` (int): Number of completion tokens used

**Optional fields:**
- `cost` (float): Cost of the API call
- `name`, `startTime`, etc.: Any other metadata

💡 CrashLens expects JSONL with per-call metrics (model, tokens, cost). Works with LangChain logs, OpenAI api.log, Claude, Gemini, and more.

---

## 🚀 Usage: Command Line Examples

After installation, use the `crashlens` command in your terminal (or `python -m crashlens` if running from source).

### 1. **Scan a log file**
```sh
crashlens scan path/to/your-logs.jsonl
```
- Scans the specified log file and generates a `report.md` in your current directory.

### 2. **Demo mode (built-in sample data)**
```sh
crashlens scan --demo
```
- Runs analysis on built-in example logs (requires `examples-logs/demo-logs.jsonl` file).
- **Note**: If installing from PyPI, you'll need to create sample logs or use your own data.
- **From source**: Demo data is included in the repository.

### 3. **Scan from stdin (pipe)**
```sh
cat path/to/your-logs.jsonl | crashlens scan --stdin
```
- Reads logs from standard input (useful for pipelines or quick tests).

### 4. **Paste logs interactively**
```sh
crashlens scan --paste
```
- Reads JSONL data from clipboard (paste and press Enter to finish).

### 5. **Generate detailed category reports**
```sh
crashlens scan --detailed
```
- Creates grouped JSON files in `detailed_output/` by issue type (fallback_failure.json, retry_loop.json, etc.).

### 6. **Get cost summaries**
```sh
crashlens scan --summary          # Cost summary with breakdown
crashlens scan --summary-only     # Summary without trace IDs
```
- Shows cost analysis with or without detailed trace information.

### 7. **Change output format**
```sh
crashlens scan --format json      # JSON output
crashlens scan --format markdown  # Markdown format  
```
- Default format is `slack` for team sharing.

### 8. **Get help**
```sh
crashlens --help
crashlens scan --help
```
- Shows all available options and usage details.

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

