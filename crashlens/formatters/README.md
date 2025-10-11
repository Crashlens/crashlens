# CrashLens Formatters

Formatters transform CrashLens analysis results into different output formats for various consumption scenarios.

## Available Formatters

### JSONFormatter

The `JSONFormatter` produces structured JSON output optimized for frontend consumption, programmatic access, and integration with other tools.

#### Usage

```python
from crashlens.formatters import JSONFormatter

# Prepare analysis results
analysis_results = {
    'detectors': [...],
    'log_file': 'path/to/logs.jsonl',
    'total_traces': 100,
    'parse_errors': 0,
    'start_time': datetime.now(),
    'end_time': datetime.now()
}

# Generate JSON output
formatter = JSONFormatter(analysis_results)
json_output = formatter.format()
```

#### CLI Usage

```bash
# Generate JSON report
crashlens scan logs.jsonl --format json

# Output is saved to report.md by default
```

#### Output Structure

The JSON formatter produces a comprehensive output with the following sections:

```json
{
  "metadata": {
    "scan_time": "ISO timestamp",
    "log_file": "string",
    "total_traces": 100,
    "parse_errors": 0,
    "duration_ms": 1500,
    "crashlens_version": "1.0.0",
    "health_score": 85.5
  },
  "summary": {
    "total_issues": 25,
    "critical": 2,
    "high": 8,
    "medium": 10,
    "low": 5,
    "total_cost": 12.45,
    "potential_savings": 5.20,
    "cost_currency": "USD"
  },
  "issues": [
    {
      "id": "retry_loop_0_trace_123",
      "type": "retry_loop",
      "severity": "high",
      "title": "Issue title",
      "description": "Detailed description",
      "trace_id": "trace_123",
      "model": "gpt-4",
      "cost": {
        "total": 1.50,
        "wasted": 0.80,
        "currency": "USD"
      },
      "metrics": {
        "tokens": 5000,
        "calls": 10,
        "latency_ms": 2500
      },
      "recommendation": "Action to fix",
      "timestamp": "ISO timestamp"
    }
  ],
  "traces": [
    {
      "trace_id": "trace_123",
      "issue_count": 2,
      "total_cost": 1.50,
      "models_used": ["gpt-4", "gpt-3.5-turbo"],
      "start_time": "ISO timestamp",
      "duration_ms": 3000,
      "status": "completed"
    }
  ],
  "models": {
    "by_provider": {
      "openai": {
        "models": [
          {
            "name": "gpt-4",
            "calls": 50,
            "tokens": 25000,
            "cost": 8.50,
            "avg_latency_ms": 1200
          }
        ],
        "total_cost": 8.50
      }
    },
    "top_models": [...]
  },
  "timeline": [
    {
      "timestamp": "ISO timestamp",
      "event_type": "retry_loop",
      "trace_id": "trace_123",
      "model": "gpt-4",
      "severity": "high",
      "description": "Event description"
    }
  ],
  "recommendations": [
    {
      "priority": 1,
      "category": "reliability",
      "title": "Reduce retry loops",
      "description": "Detailed recommendation",
      "estimated_savings": 2.50,
      "effort": "medium",
      "impact": "high"
    }
  ],
  "alerts": [
    {
      "level": "critical",
      "title": "High cost detected",
      "message": "Alert message",
      "action_required": true,
      "related_traces": ["trace_123", "trace_456"]
    }
  ],
  "export_options": {
    "formats": ["json", "markdown", "csv", "slack"],
    "detailed_reports": {
      "json": "crashlens-report.json",
      "markdown": "crashlens-report.md",
      "csv": "crashlens-report.csv"
    },
    "filters": {
      "by_severity": ["critical", "high", "medium", "low"],
      "by_type": ["retry_loop", "fallback_storm", "overkill_model"],
      "by_model": ["gpt-4", "gpt-3.5-turbo", "claude-3"]
    }
  }
}
```

#### Features

- **Frontend-Optimized**: Structured for easy consumption by web UIs and dashboards
- **Comprehensive**: Includes metadata, summary, detailed issues, traces, models, timeline, recommendations, and alerts
- **Filterable**: Export options section describes available filters and groupings
- **Actionable**: Recommendations with priority, effort, and impact estimates
- **Cost-Focused**: Detailed cost breakdown by model, provider, and trace
- **Health Score**: 0-100 score indicating overall system health

#### Integration Examples

**JavaScript/TypeScript Frontend**:
```typescript
const report = await fetch('/api/crashlens/report.json').then(r => r.json());

// Display summary
console.log(`Health Score: ${report.metadata.health_score}`);
console.log(`Total Issues: ${report.summary.total_issues}`);
console.log(`Potential Savings: $${report.summary.potential_savings}`);

// Filter high severity issues
const criticalIssues = report.issues.filter(i => i.severity === 'critical');

// Group by trace
const byTrace = report.traces.reduce((acc, trace) => {
  acc[trace.trace_id] = trace;
  return acc;
}, {});
```

**Python Integration**:
```python
import json

with open('report.md', 'r') as f:
    report = json.load(f)

# Extract recommendations
for rec in report['recommendations']:
    print(f"[P{rec['priority']}] {rec['title']} - Est. Savings: ${rec['estimated_savings']}")

# Get traces with issues
problem_traces = [t for t in report['traces'] if t['issue_count'] > 0]
```

#### Sample Output

A complete sample JSON output is available in `examples/json_format_sample.json`.

## Adding New Formatters

To add a new formatter:

1. Create a new file in this directory (e.g., `csv_formatter.py`)
2. Implement a formatter class with a `format()` method
3. Update `__init__.py` to export the new formatter
4. Add CLI integration in `crashlens/cli.py`
5. Document the formatter in this README

Example structure:
```python
class MyFormatter:
    def __init__(self, analysis_results, config=None):
        self.analysis_results = analysis_results
        self.config = config or {}
    
    def format(self) -> str:
        """Generate formatted output"""
        # Implementation here
        return formatted_output
```
