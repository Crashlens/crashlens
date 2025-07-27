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

## 📝 Example CrashLens Report

Below is a sample of what the actual `report.md` looks like after running CrashLens:


**CrashLens** is a CLI tool for detecting token waste and inefficiencies in GPT API logs. It analyzes your logs for patterns like fallback failures, retry loops, and overkill model usage, and generates a detailed Markdown report (`report.md`) with cost breakdowns and actionable insights.

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
- Install Poetry:
  ```sh
  curl -sSL https://install.python-poetry.org | python3 -
  # Or with Homebrew:
  brew install poetry
  ```

### Windows
- Install Python from [python.org](https://www.python.org/downloads/)
- Install Poetry:
  ```sh
  (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing | python -)
  # Or download and run the installer from the Poetry website
  ```
- Add Python and Poetry to your PATH if needed.

---

## 3. Set Up the Environment

```sh
# From the project root:
poetry install
```

This will create a virtual environment and install all dependencies.

To activate the environment (optional, for direct python usage):
- **Mac/Linux:**
  ```sh
  source $(poetry env info --path)/bin/activate
  ```
- **Windows:**
  ```sh
  .venv\Scripts\activate
  # Or
  poetry shell
  ```

---

## 4. Running CrashLens

You can run CrashLens via Poetry or as a Python module:

### Basic Scan (from file)
```sh
poetry run crashlens scan examples/retry-test.jsonl
# Or
python -m crashlens scan examples/retry-test.jsonl
```

### Demo Mode (built-in sample data)
```sh
poetry run crashlens scan --demo

```
🔒 CrashLens runs 100% locally. No data leaves your system.


# CrashLens Token Waste Report

**Analysis Date:** 2025-07-25 17:03:57  

**Traces Analyzed:** 156  


## Summary

| Metric | Value |
|--------|-------|
| Total AI Spend | $1.18 |
| Total Potential Savings | $0.8388 |
| Wasted Tokens | 68 |
| Issues Found | 87 |
| Traces Analyzed | 156 |

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


## Unknown (9 issues)

| Metric | Value |
|--------|-------|
| Total Waste Cost | $0.0001 |
| Total Waste Tokens | 68 |

**Issue**: 9 traces flagged by Unknown

**Sample Prompts**:
1. `What is the current time in Tokyo?`
2. `What is the capital of India?`


## Fallback Storm (5 issues)

| Metric | Value |
|--------|-------|
| Total Waste Cost | $0.0669 |
| Total Waste Tokens | 0 |

**Issue**: 5 traces flagged by Fallback Storm

**Sample Prompts**:
1. `Write a Python script to analyze sentiment from a ...`
2. `Create a function in Go to reverse a string, make ...`
3. `Summarize the key arguments in the philosophical t...`


## Unknown (73 issues)

| Metric | Value |
|--------|-------|
| Total Waste Cost | $0.7717 |
| Total Waste Tokens | 0 |

**Issue**: 73 traces flagged by Unknown

**Sample Prompts**:
1. `What is 2+2?`
2. `Draft a comprehensive business plan for a new e-co...`
3. `Generate a complex SQL query to find users who hav...`


## Monthly Projection

Based on current patterns, potential monthly savings: **$25.16**

```

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

---

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
- Runs analysis on built-in example logs (no file needed).

### 3. **Scan from stdin (pipe)**
```sh
cat path/to/your-logs.jsonl | crashlens scan --stdin
```
- Reads logs from standard input (useful for pipelines or quick tests).

### 4. **Paste logs interactively**
```sh
crashlens scan --paste
```
- Allows you to paste log lines directly into the terminal (end input with Ctrl+D).

### 5. **Get help**
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

## 8. Support
For questions, issues, or feature requests, open an issue on GitHub or contact the maintainer.

---

Enjoy using CrashLens! 🎯 

