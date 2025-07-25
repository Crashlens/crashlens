# CrashLens

_For devs using OpenAI or Claude APIs who want to cut token waste fast—without Grafana, LangSmith, or tracing setups. Works out-of-the-box with LangChain JSONL, OpenAI api.log, LlamaIndex, and custom logs._

---

## ⚠️ Python Requirement

CrashLens requires **Python 3.12 or higher**. [Download Python 3.12+ here.](https://www.python.org/downloads/)

---

## TL;DR

```sh
pip install crashlens
crashlens scan your-logs.jsonl
# Generates report.md with per-trace waste, cost, and suggestions
```

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

```markdown
# CrashLens Token Waste Report

🧾 **Total AI Spend**: $0.123456
💰 **Total Potential Savings**: $0.045678
🎯 **Wasted Tokens**: 1,200
📊 **Issues Found**: 3

| Trace ID   | Model           | Prompt                        | Completion Length | Cost     | Waste Type   |
|-----------|-----------------|-------------------------------|------------------|----------|-------------|
| trace_9   | gpt-3.5-turbo   | How do solar panels work?...  | 110              | $0.00018 | Overkill     |
| trace_10  | gpt-4           | Write a poem about AI...      | 20               | $0.00210 | Overkill     |
| trace_11  | gpt-4           | Summarize this text...        | 15               | $0.00180 | Retry Loop   |

## Overkill Model Usage (2 issues)
- **trace_9**: Used gpt-3.5-turbo for a short completion (110 tokens). Consider using a cheaper model.
- **trace_10**: Used gpt-4 for a very short completion (20 tokens). Consider using gpt-3.5-turbo.

## Retry Loops (1 issue)
- **trace_11**: Multiple retries detected for the same prompt within a short time window.

---

**Suggestions:**
- Route short prompts to cheaper models to save costs.
- Implement retry backoff to avoid unnecessary repeated calls.
```

---

## Why CrashLens? (vs. grep + Excel, LangSmith, or basic logging)

- 🔁 **grep + spreadsheet**: Too manual, error-prone, no cost context
- 💸 **LangSmith**: Powerful but complex, requires full tracing/observability stack
- 🔍 **Logging without cost visibility**: You miss $ waste and optimization opportunities

---

## Features (Ultra-Specific)

- ✅ Detects retry-loop storms across trace IDs
- ✅ Flags gpt-4 usage where gpt-3.5 gives same output
- ✅ Scans stdin logs from LangChain, LlamaIndex, custom logging
- ✅ Generates Markdown cost reports with per-trace waste

---

## What Makes CrashLens Different?

- 🧩 **Pluggable rules** (custom analyzers—extend for your org)
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

💡 CrashLens expects JSONL with per-call metrics (model, tokens, cost). Works with LangChain logs, OpenAI api.log, etc.

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

### 4. **Get help**
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
   crashlens scan my-logs.jsonl
   # OR
   python -m crashlens scan my-logs.jsonl
   ```
3. **Open `report.md`** in your favorite Markdown viewer or editor to review the findings and suggestions.

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
