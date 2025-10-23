Here’s a **concise, user-friendly CrashLens User Manual** structured for clarity and practical navigation.  
The manual divides commands into intuitive categories—helping new and advanced users quickly locate what they need.

***

# 🧭 CrashLens User Manual  
*Simplified Guide for Efficient Use & Navigation*

CrashLens helps developers detect **token waste**, **retry loops**, and **model inefficiencies** in AI usage logs. This guide summarizes commands logically based on user goals.

***

## 1. Getting Started

### Installation
```bash
pip install crashlens
```

### First Run
```bash
crashlens init          # Interactive setup
crashlens scan --demo   # Quick test with demo data
```
**Tip:** After the first run, configuration is saved in `.crashlens.yaml`.

***

## 2. Analyzing Logs (The Core Command)

### Basic Log Scan
```bash
crashlens scan path/to/your-logs.jsonl
```
Analyzes logs for inefficiency patterns and generates a formatted report (`report.md` by default).

### Input Options
| Input Source | Command Example |
|---------------|----------------|
| File | `crashlens scan logs.jsonl` |
| Standard Input | `cat logs.jsonl | crashlens scan --stdin` |
| Clipboard | `crashlens scan --paste` |
| Demo Data | `crashlens scan --demo` |

***

## 3. Output Formats

CrashLens can generate multiple types of reports for different contexts:

| Type | Description | Command |
|------|--------------|----------|
| Slack | Team-ready short format | `--format slack` |
| Markdown | Detailed human-readable | `--format markdown` |
| JSON | Machine-readable and dashboard-ready | `--format json` |

**Example:**
```bash
crashlens scan logs.jsonl --format markdown
```
**Output File:** `report.md`, `report_format_json.json`, or `report.txt` (depending on format)

***

## 4. Advanced Reporting

### Summaries
```bash
crashlens scan logs.jsonl --summary
```
Displays a brief cost and token usage summary.

### Detailed Reports
```bash
crashlens scan logs.jsonl --detailed
crashlens scan logs.jsonl --detailed --detailed-dir "detailed_output"
```
Creates JSON files grouped by issue type:
- `retry_loop.json`
- `fallback_failure.json`
- `overkill_model.json`
- `fallback_storm.json`

***

## 5. Policy Enforcement

CrashLens supports **rules-based validation** for large-scale monitoring.

### Check Logs Against Policies
```bash
crashlens policy-check logs.jsonl --policy-template all
```
### Fail Builds Automatically in CI
```bash
crashlens policy-check logs.jsonl --fail-on-violations
```

### Example Policy Setup
```bash
crashlens init --non-interactive
```
Creates `.crashlens.yaml` and auto-generates CI workflows for GitHub Actions.

***

## 6. PII Removal

Ensure compliance by removing sensitive data before sharing logs.

| Action | Command |
|---------|----------|
| Remove all PII | `crashlens pii-remove logs.jsonl` |
| Preview only | `crashlens pii-remove logs.jsonl --dry-run` |
| Remove specific types | `crashlens pii-remove logs.jsonl --types email --types phone_us` |
| Custom output | `crashlens pii-remove logs.jsonl --output clean/safe.jsonl` |

***

## 7. Observability & Metrics (for Teams)

Monitor usage with built-in Prometheus and Grafana integrations.

### Quick Start
```bash
pip install crashlens[metrics]
crashlens scan logs.jsonl --push-metrics --metrics-sample-rate 0.1
```
### HTTP Mode (for persistent monitoring)
```bash
export CRASHLENS_ALLOW_HTTP_METRICS=true
crashlens scan logs.jsonl --metrics-http --metrics-port 9090
```

***

## 8. Configuration & Automation

### Environment Variable Setup
```bash
export CRASHLENS_OUTPUT_FORMAT="slack"
export CRASHLENS_SEVERITY="medium"
export CRASHLENS_TEMPLATES="all"
```

### Non-Interactive Setup
```bash
crashlens init --non-interactive
```

### Custom Pricing
```bash
crashlens scan logs.jsonl --config custom-pricing.yaml
```

***

## 9. Slack Integration

### Setup
```bash
export CRASHLENS_SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK"
```

### Auto-send Results
```bash
crashlens scan logs.jsonl --format slack
```

Automatically posts alerts and reports to Slack.

***

## 10. Help & Reference

| Command | Description |
|----------|--------------|
| `crashlens --help` | Show general help |
| `crashlens scan --help` | Details for scanning |
| `crashlens policy-check --help` | Policy options |
| `crashlens init --help` | Setup information |

***

## 11. Example Workflows

### Developer Workflow
```bash
crashlens scan project_logs.jsonl --format markdown --summary
```

### CI/CD Integration
Add to `.github/workflows/crashlens.yml`:
```yaml
- run: crashlens policy-check logs.jsonl --policy-template all --fail-on-violations
```

### Local Testing with Demo
```bash
crashlens scan --demo --format json
open demo/demo_report_markdown.md
```

***

## 12. Troubleshooting

| Problem | Likely Cause | Fix |
|----------|---------------|-----|
| “No traces found” | Empty or malformed logs | Validate `.jsonl` structure |
| “Cost $0.00” | Missing model mapping | Update pricing config |
| “File not found” | Wrong log path | Verify with absolute path |
| “Command not found” | Not in virtual environment | Run with `poetry run crashlens` |

***

**CrashLens is your audit assistant for AI costs.**
Detect inefficiency, enforce policies, save money — all from your terminal.

[1](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/52087858/ff871d5e-4496-4b96-aef9-d9260eb12a27/paste.txt)
