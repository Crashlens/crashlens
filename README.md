# CrashLens

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
