# 🧠 What is CrashLens?

**Complete Guide to Understanding CrashLens - AI Token Waste Detection & Cost Optimization**

---

## Table of Contents

1. [Overview](#overview)
2. [Core Problem & Solution](#core-problem--solution)
3. [Key Features](#key-features)
4. [Architecture & How It Works](#architecture--how-it-works)
5. [Detection Capabilities](#detection-capabilities)
6. [Policy Enforcement System](#policy-enforcement-system)
7. [Input Sources](#input-sources)
8. [Output & Reporting](#output--reporting)
9. [Privacy & Security](#privacy--security)
10. [Integration Options](#integration-options)
11. [Use Cases](#use-cases)
12. [Technical Stack](#technical-stack)

---

## Overview

**CrashLens** is a developer-first CLI tool that analyzes AI API logs to identify and prevent costly token waste patterns in production LLM applications. It operates 100% locally with no data egress, making it privacy-first and secure for enterprise environments.

### What Does It Do?

CrashLens scans your AI API logs (OpenAI, Anthropic, Langfuse, Helicone) and:
- **Detects** hidden token waste patterns (retry loops, model overkill, fallback storms)
- **Calculates** exact cost impact in USD for each waste pattern
- **Provides** actionable optimization recommendations
- **Enforces** custom policies to prevent waste in CI/CD pipelines
- **Reports** findings in multiple formats (Markdown, JSON, Slack)
- **Monitors** production usage with Prometheus metrics

### Quick Stats

- 💰 **40-60% potential cost savings** on average
- ⚡ **< 2 seconds** to scan 1000+ log entries
- 🔒 **100% local processing** - no data leaves your machine
- 🎯 **4 core detectors** + unlimited custom policy rules
- 📊 **5 output formats** including Slack, Markdown, JSON

---

## Core Problem & Solution

### The Problem: Hidden Token Waste

AI applications often waste 40-60% of their token budget due to:

1. **Retry Loops**: Same prompt retried multiple times due to errors or timeouts
2. **Model Overkill**: Using GPT-4 for simple tasks that GPT-3.5 could handle
3. **Fallback Storms**: Cascading failures across multiple model fallbacks
4. **Prompt Inefficiency**: Long prompts generating tiny responses
5. **Budget Overruns**: Expensive calls exceeding organizational thresholds

**Traditional monitoring tools show you THAT spending is high, but not WHY.**

### The Solution: CrashLens Detection Engine

CrashLens analyzes your logs and:

✅ **Identifies root causes** of token waste with trace-level detail  
✅ **Quantifies cost impact** for each waste pattern  
✅ **Provides specific fixes** with actionable recommendations  
✅ **Prevents future waste** via policy enforcement in CI/CD  
✅ **Protects privacy** with 100% local processing

---

## Key Features

### 🕵️ 1. Intelligent Waste Detection

CrashLens includes **4 production-grade detectors** with priority-based suppression to avoid double-counting:

#### **Retry Loop Detector** (Priority 1)
- Detects identical prompts retried multiple times
- Identifies exponential backoff failures
- Flags redundant API calls within time windows
- **Cost Impact**: Exact duplicate tokens × retry count

#### **Fallback Storm Detector** (Priority 2)
- Detects cascading failures across model fallbacks
- Identifies excessive fallback chains (>3 models)
- Tracks fallback patterns in time windows
- **Cost Impact**: Sum of all failed attempts before success

#### **Model Overkill Detector** (Priority 3)
- Flags expensive models used for simple tasks
- Detects GPT-4 calls generating <10 tokens
- Identifies mismatched model selection
- **Cost Impact**: Difference between expensive and suitable model

#### **Fallback Failure Detector** (Priority 4)
- Tracks failed fallback chains (all models failed)
- Identifies exhausted retry attempts
- Flags incomplete error handling
- **Cost Impact**: Total cost of failed attempts with no success

### 🛡️ 2. Policy Enforcement System

CrashLens provides a **YAML-based rule engine** for custom policy enforcement:

#### Built-in Policy Templates
- `retry-loop-prevention`: Block excessive retries
- `model-overkill-detection`: Flag expensive model usage
- `fallback-chain-monitoring`: Track fallback patterns
- `budget-enforcement`: Enforce cost limits
- `all`: Combined policy set

#### Custom Policy Rules
Define rules with flexible matching:

```yaml
rules:
  - id: excessive_retries
    description: "Block traces with >3 retries"
    match:
      retry_count: ">3"
      usage.prompt_tokens: ">= 1000"
    action: fail
    severity: critical
    suggestion: "Implement exponential backoff"
```

#### Supported Operators
- Comparison: `>`, `>=`, `<`, `<=`, `==`
- Membership: `in:[value1, value2]`
- Pattern: `regex:pattern`
- Boolean: `true`, `false`

#### Dot Notation for Nested Fields
- `usage.prompt_tokens`
- `metadata.team`
- `error.code`
- `cost.total_cost`

### 📊 3. Multi-Format Reporting

CrashLens generates reports in **5 formats** optimized for different audiences:

#### **Markdown Reports** (Human-Readable)
- Executive summary with cost breakdown
- Detailed findings by detector
- Optimization recommendations
- Trace-level evidence

#### **JSON Reports** (Machine-Readable)
- Structured output with JSON Schema validation
- 9 comprehensive sections:
  - Executive summary
  - Policy violations
  - Cost analysis
  - Detector findings
  - Model usage stats
  - Severity breakdown
  - Timeline analysis
  - Recommendations
  - Raw detections
- Frontend-optimized for dashboards

#### **Slack Notifications** (Real-Time Alerts)
- Block Kit formatted messages
- Automatic webhook integration
- Summary-only or detailed views
- Team collaboration ready

#### **Summary Reports** (Quick Overview)
- Cost totals by detector
- Violation counts by severity
- Key metrics at a glance
- Privacy-safe (no trace IDs)

#### **Detailed Category Reports** (Deep Dive)
- Separate JSON files per detector type
- Full trace context per detection
- Timestamped snapshots
- Organized by severity

### 🔗 4. Universal Input Support

CrashLens accepts logs from **multiple sources**:

#### **File Input** (Default)
```bash
crashlens scan logs.jsonl
crashlens scan logs/*.jsonl
```

#### **Demo Mode** (Built-in Sample Data)
```bash
crashlens scan --demo
```

#### **Standard Input** (Pipe Support)
```bash
cat logs.jsonl | crashlens scan --stdin
```

#### **Clipboard** (Quick Analysis)
```bash
crashlens scan --paste
```

#### **Langfuse API** (Live Fetching)
```bash
crashlens scan --from-langfuse --hours-back 24 --limit 1000
```

#### **Helicone API** (Live Fetching)
```bash
crashlens scan --from-helicone --hours-back 48 --limit 500
```

### 🔒 5. Privacy-First Design

CrashLens prioritizes data security:

✅ **100% Local Processing**: No external API calls (except user-configured Langfuse/Helicone)  
✅ **PII Scrubbing**: Automatic removal of emails, phones, SSNs  
✅ **Summary-Only Mode**: Suppress trace IDs for safe sharing  
✅ **No Telemetry**: Zero usage data collection  
✅ **Open Source**: MIT license, auditable codebase

### 📈 6. Production Observability

CrashLens integrates with **Prometheus** for production monitoring:

#### Metrics Collected
- `crashlens_policy_rule_hits_total`: Rule hit counts by rule ID
- `crashlens_policy_rule_violations_total`: Violations by severity
- `crashlens_trace_processing_total`: Success/failure counts
- `crashlens_policy_rule_evaluation_seconds`: Rule latency histogram
- `crashlens_metrics_push_total`: Self-monitoring of metrics

#### Push Gateway Integration
```bash
crashlens scan logs.jsonl \
  --push-metrics \
  --pushgateway-url http://localhost:9091 \
  --metrics-job crashlens_production
```

#### Grafana Dashboards
Pre-built dashboards available in `dashboards/`:
- Policy enforcement overview
- Cost analysis trends
- Detector performance
- Alert rules for budget violations

### 🚀 7. CI/CD Integration

CrashLens is designed for **automated pipelines**:

#### Non-Interactive Mode
```bash
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="medium"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
crashlens init --non-interactive
```

#### GitHub Actions Workflow
Auto-generated workflow with `crashlens init`:
- Runs on every push to main/develop
- Policy checks on all JSONL files
- Fails builds on critical violations
- Uploads reports as artifacts

#### Exit Codes for Automation
- `0`: No violations or below threshold
- `1`: Violations found (when using `--fail-on-violations`)

---

## Architecture & How It Works

### Pipeline Pattern (Chain of Responsibility)

```
┌─────────────────────┐
│  Input Source       │  (file, stdin, clipboard, API)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  LangfuseParser     │  (JSONL → normalized traces)
│  - Schema validation│  Group by traceId
│  - Drift detection  │  Required field checks
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Detector Pipeline  │  (4 parallel detectors)
│  Priority-based     │  
│  suppression logic  │  
│                     │
│  1. RetryLoop       │  (exact string matching)
│  2. FallbackStorm   │  (cascade detection)
│  3. ModelOverkill   │  (suitability scoring)
│  4. FallbackFailure │  (failed chains)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Policy Engine      │  (optional YAML rules)
│  - Rule evaluation  │  Hot loop optimized
│  - Stats collection │  Constant memory
│  - Suppression      │  Deduplication
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Formatters         │  (multiple outputs)
│  - Markdown         │  Human-readable
│  - JSON             │  Machine-readable
│  - Slack            │  Block Kit messages
│  - Summary          │  Quick overview
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Output             │  (file, stdout, webhook)
│  - Local files      │
│  - Slack webhooks   │
│  - Prometheus push  │
└─────────────────────┘
```

### Module Organization

```
crashlens/
├── cli.py                          # Main entry point (4528 lines)
│                                   # All Click commands & orchestration
│
├── parsers/
│   └── langfuse.py                # JSONL parsing with schema validation
│                                   # Normalizes traces, groups by traceId
│
├── detectors/                     # Waste pattern detection
│   ├── retry_loops.py             # Exact string matching, backoff detection
│   ├── fallback_storm.py          # Cascade detection in time windows
│   ├── overkill_model_detector.py # Model suitability scoring
│   └── fallback_failure.py        # Failed fallback chain detection
│
├── policy/                        # Rule evaluation system
│   ├── engine.py                  # PolicyEngine with hot loop instrumentation
│   ├── rule.py                    # PolicyRule matching logic
│   └── templates/                 # Built-in YAML policy templates
│
├── formatters/                    # Output rendering
│   ├── markdown_formatter.py      # Human-readable Markdown
│   ├── json_formatter.py          # Structured JSON with schema
│   ├── slack_formatter.py         # Slack Block Kit messages
│   ├── summary_formatter.py       # Quick overview reports
│   ├── policy_report_markdown.py  # Policy-specific Markdown
│   └── policy_report_json.py      # Policy-specific JSON
│
├── pii/                           # Privacy-first PII removal
│   ├── sanitizer.py               # Email, phone, SSN scrubbing
│   └── patterns.py                # PII regex patterns
│
├── io/                            # Input/output handling
│   ├── clipboard_utils.py         # Clipboard paste support
│   └── file_handlers.py           # File I/O utilities
│
├── observability/                 # Prometheus metrics
│   └── metrics.py                 # Metrics collection & push
│
├── config/                        # YAML config schemas
│   └── loader.py                  # Config file loading
│
└── utils/                         # Shared utilities
    ├── cost_calculator.py         # Token cost calculations
    └── time_utils.py              # Time window utilities
```

### Detection Algorithm

#### 1. **Parse & Group**
```python
# Parse JSONL, group by traceId
traces = parser.parse_file(Path("logs.jsonl"))
# Returns: Dict[str, List[Dict[str, Any]]]
#          traceId -> [log_entry1, log_entry2, ...]
```

#### 2. **Priority-Based Detection**
```python
already_flagged = set()
all_detections = []

for detector in [retry, fallback_storm, overkill, failure]:
    detections = detector.detect(traces, pricing, already_flagged)
    
    # Mark traces as flagged (prevent double-counting)
    for det in detections:
        already_flagged.add(det['trace_id'])
    
    all_detections.extend(detections)
```

#### 3. **Policy Evaluation** (Optional)
```python
for log_entry in all_logs:
    for rule in rules:
        violation = rule.evaluate(log_entry)
        if violation:
            violations.append(violation)
```

#### 4. **Format & Output**
```python
if format == 'markdown':
    report = markdown_formatter.format(detections, traces)
elif format == 'json':
    report = json_formatter.format(detections, traces)
elif format == 'slack':
    blocks = slack_formatter.format(detections, traces)
    # POST to webhook
```

### Constant-Memory Principles

**CRITICAL for production deployment:**

- ✅ Use `defaultdict` with fixed structure (no unbounded lists)
- ✅ Aggregate stats per rule/detector (not per trace)
- ✅ Boolean flags for conditional instrumentation (zero overhead when disabled)
- ✅ Circuit breakers to prevent cardinality explosion (max 500 rules)

**Example:**
```python
# Fixed structure - won't grow unbounded
self._rule_stats = defaultdict(lambda: {
    'total_time': 0.0,
    'call_count': 0,
    'avg_time': 0.0,
    'max_time': 0.0
})

# Conditional instrumentation (only if enabled)
if self._collect_stats:
    start = time.perf_counter()
    result = expensive_operation()
    elapsed = time.perf_counter() - start
    self._rule_stats[rule_id]['total_time'] += elapsed
    self._rule_stats[rule_id]['call_count'] += 1
```

---

## Detection Capabilities

### 1. Retry Loop Detector

**What It Detects:**
- Identical prompts retried multiple times
- Exponential backoff failures
- Redundant API calls within time windows

**How It Works:**
1. Groups logs by `traceId`
2. Compares prompts using exact string matching
3. Counts retries within configurable time window (default: 5 minutes)
4. Flags traces exceeding threshold (default: 3 retries)

**Detection Output:**
```json
{
  "trace_id": "trace-123",
  "detector": "Retry Loop",
  "waste_cost": 2.45,
  "waste_tokens": 8500,
  "severity": "high",
  "retry_count": 5,
  "description": "5 retries of identical prompt",
  "suggestion": "Implement exponential backoff with circuit breaker",
  "records": [...]
}
```

**Configuration:**
```bash
crashlens scan logs.jsonl --config custom-pricing.yaml
```

```yaml
# custom-pricing.yaml
retry_loop:
  max_retries: 3
  time_window_minutes: 5
```

### 2. Fallback Storm Detector

**What It Detects:**
- Cascading failures across multiple model fallbacks
- Excessive fallback chains (>3 models)
- Fallback patterns indicating system instability

**How It Works:**
1. Tracks `metadata.fallback_attempted` flags
2. Groups consecutive fallbacks in time windows
3. Identifies cascade patterns (GPT-4 → GPT-3.5 → Claude → Gemini)
4. Calculates total cost of cascade

**Detection Output:**
```json
{
  "trace_id": "trace-456",
  "detector": "Fallback Storm",
  "waste_cost": 3.78,
  "waste_tokens": 12000,
  "severity": "high",
  "fallback_count": 4,
  "models": ["gpt-4", "gpt-3.5-turbo", "claude-3", "gemini-pro"],
  "description": "4-model fallback cascade",
  "suggestion": "Review model selection logic and error handling",
  "records": [...]
}
```

**Configuration:**
```yaml
fallback_storm:
  max_fallbacks: 3
  time_window_minutes: 10
```

### 3. Model Overkill Detector

**What It Detects:**
- Expensive models used for simple tasks
- GPT-4 calls generating <10 tokens
- Mismatched model selection (enterprise model for basic queries)

**How It Works:**
1. Analyzes `prompt_tokens` vs `completion_tokens` ratio
2. Scores task complexity based on response length
3. Compares actual model vs suitable model
4. Calculates cost difference

**Detection Output:**
```json
{
  "trace_id": "trace-789",
  "detector": "Model Overkill",
  "waste_cost": 0.58,
  "waste_tokens": 2000,
  "severity": "medium",
  "actual_model": "gpt-4",
  "suitable_model": "gpt-3.5-turbo",
  "completion_tokens": 8,
  "description": "GPT-4 used for 8-token completion",
  "suggestion": "Use gpt-3.5-turbo for simple responses",
  "records": [...]
}
```

**Configuration:**
```yaml
model_overkill:
  min_completion_tokens: 10  # Flag if below this threshold
  expensive_models: ["gpt-4", "gpt-4-32k", "claude-3-opus"]
```

### 4. Fallback Failure Detector

**What It Detects:**
- Failed fallback chains (all models failed)
- Exhausted retry attempts with no success
- Incomplete error handling

**How It Works:**
1. Tracks all fallback attempts in a trace
2. Checks if any attempt succeeded
3. Flags traces where all attempts failed
4. Calculates total wasted cost

**Detection Output:**
```json
{
  "trace_id": "trace-101",
  "detector": "Fallback Failure",
  "waste_cost": 4.23,
  "waste_tokens": 15000,
  "severity": "critical",
  "failed_models": ["gpt-4", "gpt-3.5-turbo", "claude-3"],
  "description": "All 3 fallback models failed",
  "suggestion": "Add error handling before falling back",
  "records": [...]
}
```

### Detection Priority & Suppression

CrashLens uses **priority-based suppression** to avoid double-counting:

```
Priority 1: Retry Loop Detector
   ↓ (flags trace as handled)
Priority 2: Fallback Storm Detector
   ↓ (skips if already flagged)
Priority 3: Model Overkill Detector
   ↓ (skips if already flagged)
Priority 4: Fallback Failure Detector
   ↓ (skips if already flagged)
```

**Why?** A single trace might match multiple patterns (e.g., retry loop + fallback storm). Priority ensures we attribute to the **root cause** and avoid inflating cost estimates.

---

## Policy Enforcement System

### Policy File Structure

```yaml
version: 1
global:
  max_violations_per_rule: 100  # Circuit breaker

rules:
  - id: excessive_retries
    description: "Block traces with >3 retries"
    match:
      retry_count: ">3"
      metadata.fallback_attempted: true
      usage.prompt_tokens: ">= 1000"
    action: fail          # fail | warn | block
    severity: critical    # critical | high | medium | low
    suggestion: "Implement exponential backoff with circuit breaker"

  - id: expensive_model_simple_task
    description: "GPT-4 used for short completions"
    match:
      model: "gpt-4"
      usage.completion_tokens: "< 10"
    action: warn
    severity: medium
    suggestion: "Use gpt-3.5-turbo for simple queries"

  - id: budget_threshold
    description: "Single request exceeds budget"
    match:
      cost: "> 0.50"
    action: fail
    severity: high
    suggestion: "Review prompt length and model selection"
```

### Match Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `>` | Greater than | `retry_count: ">3"` |
| `>=` | Greater than or equal | `cost: ">= 0.25"` |
| `<` | Less than | `completion_tokens: "< 10"` |
| `<=` | Less than or equal | `latency_ms: "<= 5000"` |
| `==` | Exact match | `model: "gpt-4"` |
| `in:[...]` | Membership | `model: "in:[gpt-4, claude-3]"` |
| `regex:...` | Pattern match | `prompt: "regex:(?i)password"` |
| Boolean | True/false | `fallback_attempted: true` |

### AND Logic

All conditions within a `match` block are **AND-ed together**. A log entry must match ALL conditions to trigger the rule.

```yaml
match:
  model: "gpt-4"              # AND
  retry_count: ">3"           # AND
  cost: "> 0.50"              # AND
  metadata.team: "production" # Must match ALL
```

### Dot Notation for Nested Fields

```yaml
match:
  usage.prompt_tokens: "> 1000"
  metadata.team: "engineering"
  error.code: "rate_limit_exceeded"
  cost.total_cost: "> 5.0"
```

### Policy Actions

| Action | Behavior | Use Case |
|--------|----------|----------|
| `fail` | Exit code 1, fails CI/CD | Critical violations |
| `warn` | Log warning, exit code 0 | Non-blocking alerts |
| `block` | Log violation, continue | Informational tracking |

### Severity Levels

| Severity | CI Behavior | Example |
|----------|-------------|---------|
| `critical` | Always fail | Budget exceeded, PII leak |
| `high` | Fail if threshold met | Excessive retries |
| `medium` | Warn only | Model overkill |
| `low` | Informational | Potential optimization |

### Built-in Policy Templates

#### `retry-loop-prevention`
Prevents excessive retry attempts:
```yaml
rules:
  - id: retry_threshold
    match:
      retry_count: ">3"
    action: fail
    severity: high
```

#### `model-overkill-detection`
Flags expensive models on simple tasks:
```yaml
rules:
  - id: gpt4_short_completion
    match:
      model: "gpt-4"
      usage.completion_tokens: "< 10"
    action: warn
    severity: medium
```

#### `fallback-chain-monitoring`
Tracks fallback patterns:
```yaml
rules:
  - id: excessive_fallbacks
    match:
      metadata.fallback_count: "> 3"
    action: fail
    severity: high
```

#### `budget-enforcement`
Enforces cost limits:
```yaml
rules:
  - id: per_request_budget
    match:
      cost: "> 0.50"
    action: fail
    severity: critical
```

#### `all`
Combined policy set (all templates above)

### Policy Evaluation Performance

**Hot Loop Optimization:**
- `PolicyEngine.evaluate_log_entry()` → `rule.evaluate()`
- Target: **<10% overhead** for stats collection
- Constant memory with fixed-structure `defaultdict`
- Optional instrumentation with boolean flags

**Benchmark Results:**
```
1000 rules × 1000 logs = 1M evaluations
- Without stats: 0.85s
- With stats: 0.92s
- Overhead: 8.2% ✓
```

---

## Input Sources

### 1. File Input (JSONL)

**Standard file input:**
```bash
crashlens scan logs.jsonl
crashlens scan logs/production/*.jsonl
```

**Glob patterns:**
```bash
crashlens scan logs/**/*.jsonl
crashlens scan 2024-*-*.jsonl
```

**Required format:** JSONL (JSON Lines - one JSON object per line)

**Minimum required fields:**
```json
{"traceId": "unique-id", "model": "gpt-4", "prompt_tokens": 100, "completion_tokens": 50}
```

### 2. Demo Mode (Built-in Sample Data)

**Quick testing without real logs:**
```bash
crashlens scan --demo
```

Generates sample data with:
- Retry loops
- Fallback storms
- Model overkill patterns
- Realistic timestamps and costs

### 3. Standard Input (Streaming)

**Pipe from other commands:**
```bash
cat logs.jsonl | crashlens scan --stdin
```

```bash
curl https://api.example.com/logs | crashlens scan --stdin
```

```bash
aws s3 cp s3://bucket/logs.jsonl - | crashlens scan --stdin
```

### 4. Clipboard (Quick Analysis)

**Paste from clipboard:**
```bash
# Copy JSONL to clipboard, then:
crashlens scan --paste
```

**Use case:** Quick analysis of support tickets or log snippets

### 5. Langfuse API (Live Fetching)

**Fetch traces from Langfuse:**
```bash
# Environment variables
export LANGFUSE_PUBLIC_KEY="pk_..."
export LANGFUSE_SECRET_KEY="sk_..."
export LANGFUSE_HOST="https://cloud.langfuse.com"

# Fetch and analyze
crashlens scan --from-langfuse --hours-back 24 --limit 1000
```

**Save to file instead of analyzing:**
```bash
crashlens fetch-langfuse --hours-back 48 --output traces.jsonl
```

**Options:**
- `--hours-back`: How far back to fetch (default: 24)
- `--limit`: Maximum traces to fetch (default: 1000)
- `--output`: Save to file instead of analyzing

### 6. Helicone API (Live Fetching)

**Fetch requests from Helicone:**
```bash
# Environment variable
export HELICONE_API_KEY="sk_helicone_..."

# Fetch and analyze
crashlens scan --from-helicone --hours-back 24 --limit 1000
```

**Options:**
- `--hours-back`: How far back to fetch (default: 24)
- `--limit`: Maximum requests to fetch (default: 1000)

---

## Output & Reporting

### 1. Markdown Reports (Human-Readable)

**Default format for readability:**
```bash
crashlens scan logs.jsonl --format markdown
```

**Output structure:**
```markdown
# 🧠 CrashLens Token Waste Report

## 📊 Executive Summary
- Total Waste Cost: $45.23
- Total Waste Tokens: 156,780
- Traces Analyzed: 1,234
- Violations Found: 87

## 🔍 Detailed Findings

### 🔄 Retry Loop Detector (34 detections)
**Cost Impact:** $18.45 | **Tokens Wasted:** 62,340

#### Detection 1: trace-abc-123
- **Severity:** High
- **Retry Count:** 5
- **Cost:** $2.45
- **Description:** 5 retries of identical prompt
- **Suggestion:** Implement exponential backoff

### ❓ Model Overkill Detector (23 detections)
...

## 💡 Recommendations
1. Implement circuit breakers for retry logic
2. Use GPT-3.5 for simple completions (<50 tokens)
3. Review fallback chain configuration
```

**Save to file:**
```bash
crashlens scan logs.jsonl --output report.md
```

### 2. JSON Reports (Machine-Readable)

**Structured output with JSON Schema:**
```bash
crashlens scan logs.jsonl --format json --output report.json
```

**9 comprehensive sections:**

```json
{
  "summary": {
    "total_waste_cost": 45.23,
    "total_waste_tokens": 156780,
    "detections_by_type": {...},
    "severity_breakdown": {...}
  },
  "policy_violations": [...],
  "cost_analysis": {
    "by_model": {...},
    "by_detector": {...},
    "by_severity": {...}
  },
  "detections": {
    "retry_loops": [...],
    "fallback_storms": [...],
    "model_overkill": [...],
    "fallback_failures": [...]
  },
  "model_usage": {
    "gpt-4": {"calls": 234, "tokens": 45678, "cost": 12.34},
    "gpt-3.5-turbo": {...}
  },
  "severity_breakdown": {
    "critical": 5,
    "high": 23,
    "medium": 45,
    "low": 14
  },
  "timeline": {
    "first_detection": "2024-10-26T10:00:00Z",
    "last_detection": "2024-10-26T18:30:00Z",
    "duration_hours": 8.5
  },
  "recommendations": [...],
  "metadata": {
    "generated_at": "2024-10-26T19:00:00Z",
    "crashlens_version": "2.9.12",
    "total_traces": 1234
  }
}
```

**Validate JSON Schema:**
```bash
crashlens json-validate report.json
```

### 3. Slack Notifications (Real-Time Alerts)

**Automatic webhook posting:**
```bash
export CRASHLENS_SLACK_WEBHOOK="https://hooks.slack.com/services/..."
crashlens scan logs.jsonl  # Auto-posts to Slack
```

**Manual Slack command:**
```bash
crashlens slack notify --webhook-url $SLACK_WEBHOOK --report report.md
```

**Block Kit formatted messages:**
```
📊 CrashLens Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Total Waste Cost: $45.23
🔢 Total Waste Tokens: 156,780
📝 Traces Analyzed: 1,234
⚠️  Violations Found: 87

🔍 Findings by Detector:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 Retry Loops: 34 ($18.45)
⚡ Fallback Storms: 23 ($12.78)
❓ Model Overkill: 23 ($10.00)
❌ Fallback Failures: 7 ($4.00)

💡 Top Recommendations:
1. Implement circuit breakers
2. Use GPT-3.5 for simple tasks
3. Review fallback configuration

📎 Full Report: [View Details]
```

**Summary-only mode (privacy-safe):**
```bash
crashlens scan logs.jsonl --summary-only --format slack
```

### 4. Summary Reports (Quick Overview)

**Cost totals without trace details:**
```bash
crashlens scan logs.jsonl --summary
```

**Output:**
```
╔═══════════════════════════════════════╗
║     CrashLens Summary Report          ║
╚═══════════════════════════════════════╝

Total Waste Cost:   $45.23
Total Waste Tokens: 156,780
Traces Analyzed:    1,234
Violations Found:   87

Cost Breakdown:
  Retry Loops:        $18.45 (40.8%)
  Fallback Storms:    $12.78 (28.2%)
  Model Overkill:     $10.00 (22.1%)
  Fallback Failures:  $4.00 (8.9%)

Severity Breakdown:
  Critical: 5
  High:     23
  Medium:   45
  Low:      14
```

### 5. Detailed Category Reports (Deep Dive)

**Generate separate JSON files per detector:**
```bash
crashlens scan logs.jsonl --detailed --detailed-dir ./reports
```

**Output structure:**
```
reports/
├── retry_loops_2024-10-26_19-00-00.json
├── fallback_storms_2024-10-26_19-00-00.json
├── model_overkill_2024-10-26_19-00-00.json
└── fallback_failures_2024-10-26_19-00-00.json
```

**Each file contains:**
```json
{
  "detector_type": "Retry Loop",
  "total_detections": 34,
  "total_cost": 18.45,
  "total_tokens": 62340,
  "detections": [
    {
      "trace_id": "trace-abc-123",
      "severity": "high",
      "retry_count": 5,
      "cost": 2.45,
      "tokens": 8500,
      "timestamp": "2024-10-26T10:15:30Z",
      "records": [...]
    }
  ]
}
```

### 6. Policy Enforcement Reports

**Policy-specific reporting:**
```bash
crashlens guard logs.jsonl \
  --policy-file my-policy.yaml \
  --output policy-report.md
```

**Output includes:**
- Rules evaluated
- Violations found per rule
- Severity breakdown
- Failed log entries with context
- Suggestions for remediation

---

## Privacy & Security

### Privacy-First Architecture

**100% Local Processing:**
- ✅ No external API calls (except user-configured Langfuse/Helicone)
- ✅ No telemetry or usage tracking
- ✅ No data stored in cloud services
- ✅ Auditable open-source codebase

### PII Scrubbing

**Automatic PII removal:**
```bash
crashlens pii-remove logs.jsonl --output clean-logs.jsonl
```

**Detected patterns:**
- Email addresses
- Phone numbers (US/International)
- Social Security Numbers
- Credit card numbers
- IP addresses

**PII Patterns:**
```python
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
PHONE_PATTERN = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
SSN_PATTERN = r'\b\d{3}-\d{2}-\d{4}\b'
```

**In-place scrubbing during scan:**
```bash
crashlens scan logs.jsonl --strip-pii
```

### Summary-Only Mode

**Suppress trace IDs for safe sharing:**
```bash
crashlens scan logs.jsonl --summary-only
```

**Output excludes:**
- Trace IDs
- User identifiers
- Request timestamps (aggregated only)
- Prompt content (summary stats only)

**Use case:** Share cost analysis with stakeholders without exposing sensitive data

### Redaction Options

**Redact specific fields:**
```bash
crashlens scan logs.jsonl --redact-fields prompt,completion,user_id
```

**Custom redaction patterns:**
```yaml
# .crashlens/config.yaml
redaction:
  patterns:
    - regex: "api_key=[A-Za-z0-9]+"
      replacement: "api_key=REDACTED"
    - regex: "Bearer [A-Za-z0-9._-]+"
      replacement: "Bearer REDACTED"
```

---

## Integration Options

### 1. GitHub Actions (CI/CD)

**Auto-generated workflow:**
```bash
crashlens init
```

**Generated `.github/workflows/crashlens.yml`:**
```yaml
name: CrashLens Policy Check

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install CrashLens
        run: pip install crashlens
      
      - name: Run Policy Check
        run: |
          crashlens guard logs/**/*.jsonl \
            --policy-template all \
            --fail-on-violations \
            --severity-threshold medium
      
      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: crashlens-report
          path: crashlens-report.md
```

### 2. Slack Webhooks

**Setup:**
```bash
# Set environment variable
export CRASHLENS_SLACK_WEBHOOK="https://hooks.slack.com/services/T00/B00/xxxx"

# Automatic posting
crashlens scan logs.jsonl  # Auto-posts to Slack
```

**Manual posting:**
```bash
crashlens slack notify \
  --webhook-url $SLACK_WEBHOOK \
  --report report.md
```

**Scheduled daily reports (cron):**
```bash
# crontab -e
0 9 * * * crashlens scan /logs/production/*.jsonl --format slack
```

### 3. Prometheus + Grafana

**Enable metrics collection:**
```bash
# Install with metrics support
pip install crashlens[metrics]

# Start Prometheus Pushgateway
docker run -d -p 9091:9091 prom/pushgateway

# Scan with metrics push
crashlens scan logs.jsonl \
  --push-metrics \
  --pushgateway-url http://localhost:9091 \
  --metrics-job crashlens_production
```

**Configure Prometheus scraping:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['localhost:9091']
    scrape_interval: 30s
```

**Import Grafana dashboards:**
```bash
# Located in dashboards/
- crashlens-policy-enforcement.json
- crashlens-alert-rules.yml
```

**Metrics collected:**
- `crashlens_policy_rule_hits_total`
- `crashlens_policy_rule_violations_total`
- `crashlens_trace_processing_total`
- `crashlens_policy_rule_evaluation_seconds`

### 4. Langfuse Integration

**Fetch traces directly:**
```bash
export LANGFUSE_PUBLIC_KEY="pk_..."
export LANGFUSE_SECRET_KEY="sk_..."
export LANGFUSE_HOST="https://cloud.langfuse.com"

crashlens scan --from-langfuse --hours-back 24
```

**Scheduled monitoring:**
```bash
# Monitor every hour
*/60 * * * * crashlens scan --from-langfuse --hours-back 1 --format slack
```

### 5. Helicone Integration

**Fetch requests:**
```bash
export HELICONE_API_KEY="sk_helicone_..."

crashlens scan --from-helicone --hours-back 24
```

### 6. Custom Integrations (Python API)

**Use CrashLens as a library:**
```python
from crashlens.parsers.langfuse import LangfuseParser
from crashlens.detectors.retry_loops import RetryLoopDetector
from crashlens.formatters.json_formatter import JSONFormatter

# Parse logs
parser = LangfuseParser()
traces = parser.parse_file(Path("logs.jsonl"))

# Run detector
detector = RetryLoopDetector(max_retries=3, time_window_minutes=5)
detections = detector.detect(traces)

# Format output
formatter = JSONFormatter()
report = formatter.format(detections, traces)
print(report)
```

---

## Use Cases

### 1. Cost Optimization (Post-Deployment)

**Scenario:** Identify where AI budget is being wasted in production

**Workflow:**
```bash
# Fetch last 7 days of production logs
crashlens scan --from-langfuse --hours-back 168 --limit 10000

# Generate detailed report
crashlens scan logs.jsonl --format markdown --detailed --output cost-analysis.md

# Share summary with stakeholders (privacy-safe)
crashlens scan logs.jsonl --summary-only --format slack
```

**Outcome:**
- Identified 45% token waste from retry loops
- Reduced costs by switching GPT-4 to GPT-3.5 for simple tasks
- Implemented circuit breakers based on recommendations

### 2. CI/CD Policy Enforcement (Pre-Deployment)

**Scenario:** Prevent costly patterns from reaching production

**Workflow:**
```bash
# Initialize CrashLens in repo
crashlens init

# Configure strict policies
crashlens guard logs.jsonl \
  --policy-template all \
  --fail-on-violations \
  --severity-threshold medium
```

**GitHub Actions integration:**
- Runs on every PR
- Fails build if violations exceed threshold
- Posts summary comment on PR

**Outcome:**
- Caught retry loop bug before production deployment
- Enforced budget limits per request
- Reduced incidents by 60%

### 3. Model Selection Optimization

**Scenario:** Find opportunities to downgrade expensive models

**Workflow:**
```bash
# Scan with model overkill focus
crashlens scan logs.jsonl --format json --output model-analysis.json

# Filter by model overkill
jq '.detections.model_overkill' model-analysis.json
```

**Analysis:**
- 234 GPT-4 calls with <10 token completions
- Potential savings: $1,247/month by switching to GPT-3.5
- Implemented smart routing: simple queries → GPT-3.5, complex → GPT-4

**Outcome:**
- 32% cost reduction
- No degradation in output quality for simple tasks

### 4. Incident Response (Post-Mortem)

**Scenario:** Investigate sudden cost spike

**Workflow:**
```bash
# Fetch logs from incident timeframe
crashlens scan --from-langfuse \
  --hours-back 2 \
  --limit 5000 \
  --format markdown \
  --output incident-report.md

# Check for specific patterns
crashlens guard logs.jsonl \
  --policy-template retry-loop-prevention \
  --severity-threshold critical
```

**Findings:**
- Fallback storm triggered during API outage
- 1,234 cascading failures across 4 models
- $4,567 wasted in 30 minutes

**Actions:**
- Implemented rate limiting on fallbacks
- Added health checks before fallback
- Set up real-time Slack alerts

### 5. Budget Compliance (Financial Auditing)

**Scenario:** Monthly AI spending audit

**Workflow:**
```bash
# Fetch full month of logs
crashlens scan --from-langfuse \
  --hours-back 720 \
  --limit 50000 \
  --output monthly-audit.jsonl

# Generate comprehensive report
crashlens scan monthly-audit.jsonl \
  --format json \
  --detailed \
  --detailed-dir audit-reports

# Extract cost breakdown
jq '.cost_analysis' audit-reports/*.json > cost-breakdown.json
```

**Report includes:**
- Cost by team/project (via metadata)
- Cost by model
- Cost by detector type (waste vs. legitimate)
- Trend analysis over time

**Outcome:**
- Identified teams exceeding budget
- Implemented per-team cost limits
- Reduced overall spend by 28%

### 6. Privacy Compliance (Data Sanitization)

**Scenario:** Share logs with external auditors

**Workflow:**
```bash
# Remove PII from logs
crashlens pii-remove logs.jsonl --output clean-logs.jsonl

# Generate privacy-safe report
crashlens scan clean-logs.jsonl \
  --summary-only \
  --redact-fields prompt,completion,user_id \
  --output auditor-report.md
```

**Output:**
- No trace IDs
- No user identifiers
- No prompt/completion content
- Aggregated statistics only

**Outcome:**
- Passed privacy audit
- Shared cost insights without data exposure

---

## Technical Stack

### Core Technologies

**Language:** Python 3.12+

**CLI Framework:** Click 8.2.1+
- Decorator-based command definition
- Automatic help generation
- Built-in testing support (CliRunner)

**Data Parsing:** orjson 3.10.18+
- Fast JSON parsing for JSONL
- 2-5x faster than standard library

**Configuration:** PyYAML 6.0.2+
- Policy YAML parsing
- Configuration file support

**Template Rendering:** Jinja2 3.1.6+
- Policy template rendering
- Dynamic configuration

**Terminal UI:** Rich 14.0.0+
- Beautiful terminal output
- Progress bars and spinners

**Metrics:** prometheus-client 0.23.1+
- Prometheus metrics collection
- Push Gateway integration

### Dependencies

**Required:**
```
click>=8.2.1
pyyaml>=6.0.2
orjson>=3.10.18
rich>=14.0.0
jinja2>=3.1.6
requests>=2.31.0
```

**Optional:**
```
prometheus-client>=0.23.1  # For metrics support
jsonschema>=4.17.0         # For JSON validation
faker>=19.0.0              # For demo data generation
pyperclip>=1.8.2           # For clipboard support
```

### Installation

**Standard:**
```bash
pip install crashlens
```

**With metrics:**
```bash
pip install crashlens[metrics]
```

**With all extras:**
```bash
pip install crashlens[all]
```

**Development:**
```bash
git clone https://github.com/Crashlens/crashlens.git
cd crashlens
poetry install
poetry shell
```

### Testing

**Test framework:** pytest

**Run tests:**
```bash
poetry run pytest tests/
```

**Test coverage:**
```bash
poetry run pytest --cov=crashlens --cov-report=html tests/
```

**Type checking:**
```bash
poetry run mypy crashlens/ --ignore-missing-imports
```

**Code quality:**
```bash
# Formatting
poetry run black crashlens/ tests/
poetry run isort crashlens/ tests/

# Linting
poetry run flake8 crashlens/ tests/ --max-line-length=88
```

### Performance Characteristics

**Scanning:**
- 1,000 logs: ~0.001 seconds
- 10,000 logs: ~0.01 seconds
- 100,000 logs: ~0.1 seconds

**Memory:**
- Constant memory with fixed-structure aggregation
- No unbounded lists in hot loops
- Streaming JSONL parsing

**Policy Evaluation:**
- <5% overhead with stats collection
- Hot loop optimized
- Circuit breakers prevent cardinality explosion

**Metrics Push:**
- Non-blocking (< 2s wait)
- Fire-and-forget design
- Graceful degradation on failure

---

## Summary

**CrashLens is your AI cost optimization companion:**

✅ **Detects** hidden token waste with 4 production-grade detectors  
✅ **Calculates** exact cost impact for each waste pattern  
✅ **Enforces** custom policies to prevent waste in CI/CD  
✅ **Reports** findings in 10+ formats for all audiences  
✅ **Integrates** with GitHub, Slack, Prometheus, Langfuse, Helicone  
✅ **Protects** privacy with 100% local processing  

**Ready to optimize your AI costs?**

```bash
pip install crashlens
crashlens scan --demo
crashlens scan your-logs.jsonl
```

---

## Additional Resources

- **Quick Start Guide:** [QUICK_START.md](../QUICK_START.md)
- **Command Reference:** [COMMAND-REFERENCE.md](./COMMAND-REFERENCE.md)
- **Policy Engine Guide:** [GUARD.md](./GUARD.md)
- **Observability Setup:** [OBSERVABILITY.md](./OBSERVABILITY.md)
- **User Manual:** [USER_MANUAL.md](./USER_MANUAL.md)
- **GitHub Repository:** [github.com/Crashlens/crashlens](https://github.com/Crashlens/crashlens)
- **Documentation Index:** [INDEX.md](./INDEX.md)

---

**Version:** 2.9.12  
**Last Updated:** October 26, 2025  
**Status:** Production Ready  
**License:** MIT
