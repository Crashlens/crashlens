# 🎉 CrashLens New Features

## Latest Updates (v2.9.12)

This document highlights the newest features and enhancements added to CrashLens, including detailed usage examples, output formats, and benefits.

---

## 🆕 Structured JSON Output Format

### Overview
CrashLens now supports **comprehensive structured JSON output** designed specifically for frontend applications, dashboards, and programmatic consumption. This format provides all analysis data in a machine-readable, schema-validated structure with 9 specialized sections.

### Command Usage

```bash
# Basic JSON output
crashlens scan logs.jsonl --format json

# Short form
crashlens scan logs.jsonl -f json

# With demo data
crashlens scan --demo --format json

# From stdin
cat logs.jsonl | crashlens scan --stdin --format json

# Windows PowerShell
Get-Content logs.jsonl | crashlens scan --stdin --format json
```

### Output Location

Reports are intelligently saved based on input source:

| Input Source | Output Location | Filename |
|-------------|-----------------|----------|
| File path | Same directory as input file | `report_format_json.json` |
| `--demo` | `examples-logs/` directory | `report_format_json.json` |
| `--stdin` or `--paste` | Current working directory | `report_format_json.json` |

**Example:**
```bash
# Input: sample-logs/demo-logs.jsonl
# Output: sample-logs/report_format_json.json

crashlens scan sample-logs/demo-logs.jsonl --format json
# [OK] JSON report written to sample-logs/report_format_json.json
```

### JSON Structure (9 Sections)

The JSON output contains the following comprehensive sections:

#### 1. **metadata** - Scan Information
```json
{
  "metadata": {
    "scan_time": "2025-10-11T14:30:00Z",
    "crashlens_version": "2.9.12",
    "schema_version": "1.0.0",
    "log_file": "sample-logs/demo-logs.jsonl",
    "total_traces": 156,
    "scan_duration_ms": 234
  }
}
```

**Purpose:** Version tracking, audit trail, reproducibility

---

#### 2. **summary** - Key Metrics
```json
{
  "summary": {
    "total_cost": 859.52,
    "total_issues": 53185,
    "potential_savings": 859.52,
    "savings_percentage": 100.0,
    "wasted_tokens": 38213010,
    "issues_by_severity": {
      "critical": 125,
      "high": 1200,
      "medium": 45000,
      "low": 6860
    },
    "issues_by_category": {
      "retry_loop": 187,
      "overkill_model": 52998
    }
  }
}
```

**Purpose:** Executive dashboard, KPI tracking, at-a-glance metrics

---

#### 3. **issues** - Detailed Problems
```json
{
  "issues": [
    {
      "category": "retry_loop",
      "severity": "high",
      "count": 187,
      "cost": 859.52,
      "wasted_tokens": 24555498,
      "affected_traces": ["trace_001", "trace_002"],
      "description": "Retry loops detected causing unnecessary API calls",
      "suggestion": "Implement exponential backoff with jitter",
      "fix_priority": 1
    }
  ]
}
```

**Purpose:** Issue tracking, prioritization, detailed analysis

---

#### 4. **traces** - Individual Trace Analysis
```json
{
  "traces": [
    {
      "trace_id": "trace_norm_76",
      "model": "gpt-4",
      "total_cost": 65.78,
      "prompt_tokens": 1200,
      "completion_tokens": 800,
      "issues": ["high_cost"],
      "timestamp": "2025-10-11T12:00:00Z",
      "efficiency_score": 0.65
    }
  ]
}
```

**Purpose:** Trace-level debugging, pattern identification, time-series analysis

---

#### 5. **models** - Per-Model Statistics
```json
{
  "models": [
    {
      "name": "gpt-4",
      "total_cost": 845.65,
      "percentage": 98.4,
      "total_calls": 120,
      "total_tokens": 48000,
      "avg_cost_per_call": 7.05,
      "issues": ["overkill_usage"],
      "optimization_potential": "high"
    },
    {
      "name": "gpt-3.5-turbo",
      "total_cost": 13.87,
      "percentage": 1.6,
      "total_calls": 36,
      "total_tokens": 12000,
      "avg_cost_per_call": 0.39,
      "optimization_potential": "low"
    }
  ]
}
```

**Purpose:** Cost attribution, model selection optimization, budget planning

---

#### 6. **timeline** - Chronological Events
```json
{
  "timeline": [
    {
      "timestamp": "2025-10-11T12:00:00Z",
      "event_type": "api_call",
      "trace_id": "trace_001",
      "model": "gpt-4",
      "cost": 5.50,
      "tokens": 1200,
      "issues": ["retry_detected"]
    },
    {
      "timestamp": "2025-10-11T12:00:05Z",
      "event_type": "retry",
      "trace_id": "trace_001",
      "model": "gpt-4",
      "cost": 5.50,
      "retry_count": 1
    }
  ]
}
```

**Purpose:** Timeline visualization, pattern analysis, debugging retry sequences

---

#### 7. **recommendations** - Prioritized Actions
```json
{
  "recommendations": [
    {
      "priority": 1,
      "category": "retry_loop",
      "title": "Implement Exponential Backoff",
      "description": "187 traces show retry loops without proper backoff strategy",
      "potential_savings": 859.52,
      "implementation_effort": "medium",
      "impact": "high",
      "steps": [
        "Add exponential backoff with jitter",
        "Implement circuit breaker pattern",
        "Set maximum retry limits (3-5 retries)"
      ]
    },
    {
      "priority": 2,
      "category": "model_optimization",
      "title": "Use Cheaper Models for Simple Tasks",
      "description": "52,998 GPT-4 calls with <50 tokens can use GPT-3.5-turbo",
      "potential_savings": 560.24,
      "implementation_effort": "low",
      "impact": "high"
    }
  ]
}
```

**Purpose:** Action planning, team assignment, ROI prioritization

---

#### 8. **alerts** - Critical Warnings
```json
{
  "alerts": [
    {
      "level": "critical",
      "type": "high_cost_spike",
      "message": "Total cost ($859.52) exceeds threshold",
      "threshold": 500.00,
      "current_value": 859.52,
      "triggered_at": "2025-10-11T14:30:00Z",
      "requires_action": true
    },
    {
      "level": "warning",
      "type": "retry_pattern",
      "message": "187 traces showing retry loop patterns",
      "requires_action": true
    }
  ]
}
```

**Purpose:** Real-time monitoring, alerting systems, threshold management

---

#### 9. **export_options** - Data Export Capabilities
```json
{
  "export_options": {
    "formats": ["csv", "excel", "pdf"],
    "endpoints": {
      "raw_data": "/api/export/raw",
      "summary": "/api/export/summary",
      "traces": "/api/export/traces"
    },
    "filters_applied": ["cost > 5.00", "model = gpt-4"]
  }
}
```

**Purpose:** Further processing, data integration, report sharing

---

## 📋 Schema Validation

### Validate JSON Output

CrashLens includes a built-in schema validator to ensure JSON output integrity:

```bash
# Validate a JSON report
python -m crashlens.formatters.schema_validator report_format_json.json

# Output on success:
# ✓ report_format_json.json is valid

# Output on failure:
# ✗ report_format_json.json is invalid
# Error: 'metadata' is a required property
```

### Schema Details

- **Standard**: JSON Schema Draft 7
- **Location**: `crashlens/formatters/schema.json`
- **Size**: 473 lines with comprehensive type definitions
- **Validation**: All 9 sections with required fields and type constraints

### Install Validation Dependencies

```bash
pip install jsonschema
```

---

## 🎯 Benefits of JSON Format

### 1. **Frontend Integration**
- **Direct Consumption**: No parsing required for React, Vue, Angular
- **Type Safety**: TypeScript/Flow interfaces can be generated from schema
- **Nested Structures**: Pre-organized data reduces frontend logic

**Example (React):**
```typescript
import reportData from './report_format_json.json';

function Dashboard() {
  return (
    <div>
      <h1>Total Cost: ${reportData.summary.total_cost}</h1>
      <h2>Issues: {reportData.summary.total_issues}</h2>
      <IssuesList issues={reportData.issues} />
    </div>
  );
}
```

### 2. **Automation & CI/CD**
- **Machine-Readable**: Easy parsing in any programming language
- **Consistent Structure**: Same format across all scans
- **Version Tracking**: Schema version ensures compatibility

**Example (Python):**
```python
import json

with open('report_format_json.json') as f:
    report = json.load(f)
    
if report['summary']['total_cost'] > 1000:
    print("❌ Cost threshold exceeded!")
    exit(1)
```

**Example (GitHub Actions):**
```yaml
- name: Check AI Costs
  run: |
    crashlens scan logs.jsonl --format json
    cost=$(jq '.summary.total_cost' report_format_json.json)
    if (( $(echo "$cost > 500" | bc -l) )); then
      echo "::error::Cost exceeded $500"
      exit 1
    fi
```

### 3. **Dashboard Development**
- **Pre-Calculated Metrics**: No need for aggregation queries
- **Time-Series Data**: Timeline section ready for charts
- **Cost Attribution**: Per-model breakdown for pie charts

**Example Chart Data:**
```javascript
// Pie chart: Cost by model
const chartData = reportData.models.map(m => ({
  name: m.name,
  value: m.total_cost,
  percentage: m.percentage
}));

// Line chart: Timeline
const timelineData = reportData.timeline.map(e => ({
  time: e.timestamp,
  cost: e.cost,
  model: e.model
}));
```

### 4. **API Integration**
- **RESTful Ready**: Can be served directly via API endpoints
- **Caching-Friendly**: Structured data for efficient caching
- **Webhook-Compatible**: Easy to send to monitoring systems

**Example (Express.js):**
```javascript
app.get('/api/scan/:id', (req, res) => {
  const report = require(`./scans/${req.params.id}/report_format_json.json`);
  res.json(report);
});
```

### 5. **Data Analysis**
- **Pandas-Friendly**: Easy import for data science workflows
- **SQL-Compatible**: Can be imported into databases
- **Time-Series Analysis**: Timeline data for trend analysis

**Example (Pandas):**
```python
import pandas as pd
import json

with open('report_format_json.json') as f:
    data = json.load(f)

# Convert traces to DataFrame
df = pd.DataFrame(data['traces'])
print(df.groupby('model')['total_cost'].sum())

# Timeline analysis
timeline_df = pd.DataFrame(data['timeline'])
timeline_df['timestamp'] = pd.to_datetime(timeline_df['timestamp'])
daily_costs = timeline_df.groupby(timeline_df['timestamp'].dt.date)['cost'].sum()
```

---

## 🔄 Comparison: Output Formats

| Feature | Markdown | Slack | JSON |
|---------|----------|-------|------|
| **Human Readable** | ✅ Excellent | ✅ Good | ⚠️ Raw |
| **Machine Readable** | ⚠️ Parsing needed | ❌ No | ✅ Native |
| **Frontend Integration** | ❌ No | ❌ No | ✅ Direct |
| **Schema Validation** | ❌ No | ❌ No | ✅ Yes |
| **Dashboard Ready** | ❌ No | ❌ No | ✅ Yes |
| **File Size** | Small | Small | Medium |
| **Best For** | Documentation | Team Chat | Automation |
| **Output File** | report.md | report.md | report_format_json.json |

---

## 🚀 Real-World Use Cases

### Use Case 1: Daily Cost Monitoring Dashboard

**Goal:** Visualize daily AI spending trends

```bash
# Daily cron job
0 9 * * * /usr/bin/crashlens scan /logs/yesterday.jsonl --format json && \
          cp report_format_json.json /var/www/dashboard/data/$(date +%Y%m%d).json
```

**Frontend:**
- Load JSON files for last 30 days
- Display cost trends with Chart.js/D3.js
- Show alerts and recommendations

### Use Case 2: CI/CD Cost Gate

**Goal:** Fail builds if AI costs exceed budget

```yaml
# .github/workflows/cost-check.yml
- name: Generate Cost Report
  run: crashlens scan test-logs/*.jsonl --format json

- name: Check Budget
  run: |
    COST=$(jq '.summary.total_cost' report_format_json.json)
    BUDGET=100
    if (( $(echo "$COST > $BUDGET" | bc -l) )); then
      echo "Cost $COST exceeds budget $BUDGET"
      exit 1
    fi
```

### Use Case 3: Multi-Team Cost Attribution

**Goal:** Track costs per team/project

```python
# process_reports.py
import json
from pathlib import Path

reports = {}
for team_dir in Path('teams').iterdir():
    with open(team_dir / 'report_format_json.json') as f:
        reports[team_dir.name] = json.load(f)

# Generate team cost summary
for team, report in reports.items():
    print(f"{team}: ${report['summary']['total_cost']:.2f}")
```

### Use Case 4: Automated Alerting

**Goal:** Send Slack alerts when issues detected

```python
# alert_system.py
import json
import requests

with open('report_format_json.json') as f:
    report = json.load(f)

for alert in report['alerts']:
    if alert['level'] == 'critical':
        requests.post(SLACK_WEBHOOK, json={
            'text': f"🚨 {alert['message']}",
            'attachments': [{
                'color': 'danger',
                'fields': [
                    {'title': 'Cost', 'value': f"${alert['current_value']:.2f}"},
                    {'title': 'Threshold', 'value': f"${alert['threshold']:.2f}"}
                ]
            }]
        })
```

---

## 📚 Additional Resources

### Documentation
- **Formatter README**: `crashlens/formatters/README.md` - Detailed formatter documentation
- **JSON Schema**: `crashlens/formatters/schema.json` - Complete schema definition
- **Schema Validator**: `crashlens/formatters/schema_validator.py` - Validation tool source

### Examples
- **Sample Output**: `examples-reports/json_format.json` - Example JSON report
- **Test Logs**: `examples-logs/demo-logs.jsonl` - Sample input data

### Testing
- **Formatter Tests**: `tests/test_json_formatter.py` - 11 comprehensive tests
- **Schema Tests**: `tests/test_schema_validation.py` - 4 validation tests

---

## 🔧 Advanced Usage

### Custom Post-Processing

```python
# enrich_report.py
import json

# Load CrashLens output
with open('report_format_json.json') as f:
    report = json.load(f)

# Add custom fields
report['metadata']['team'] = 'ml-platform'
report['metadata']['environment'] = 'production'
report['custom_metrics'] = {
    'cost_per_user': report['summary']['total_cost'] / 1000,
    'efficiency_score': calculate_efficiency(report)
}

# Save enriched report
with open('enriched_report.json', 'w') as f:
    json.dump(report, f, indent=2)
```

### Database Integration

```python
# store_in_db.py
import json
import sqlite3

conn = sqlite3.connect('crashlens.db')
cursor = conn.cursor()

with open('report_format_json.json') as f:
    report = json.load(f)

cursor.execute('''
    INSERT INTO scans (timestamp, total_cost, total_issues, report_json)
    VALUES (?, ?, ?, ?)
''', (
    report['metadata']['scan_time'],
    report['summary']['total_cost'],
    report['summary']['total_issues'],
    json.dumps(report)
))

conn.commit()
```

### TypeScript Type Definitions

Generate TypeScript interfaces from the schema:

```bash
# Install json-schema-to-typescript
npm install -g json-schema-to-typescript

# Generate types
json2ts crashlens/formatters/schema.json > types/crashlens-report.d.ts
```

---

## 🐛 Troubleshooting

### Issue: "Cannot find module 'jsonschema'"

**Solution:**
```bash
pip install jsonschema
```

### Issue: JSON file not found

**Cause:** Output location depends on input source

**Solution:** Check the correct output location:
- File input: Same directory as input file
- Demo mode: `examples-logs/report_format_json.json`
- stdin/paste: Current working directory

### Issue: Schema validation fails

**Solution:** Ensure you're using the latest CrashLens version:
```bash
pip install --upgrade crashlens
```

---

## 📞 Support

For questions or issues with JSON output:
- Open an issue on GitHub
- Check `crashlens/formatters/README.md` for detailed documentation
- Run `crashlens scan --help` for command options

---

**Happy Analyzing! 🎯**
