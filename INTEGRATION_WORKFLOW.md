# 🎯 CrashLens v2.0 Integration Workflow

## How CrashLens Fits Into Your System

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR AI/LLM APPLICATION                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   LLM USAGE SOURCES                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   Local     │  │  Langfuse   │  │  Helicone   │       │
│  │ JSONL Files │  │    API      │  │     API     │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│         │                │                │               │
│         └────────────────┼────────────────┘               │
│                          │                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │   OpenAI    │  │  Custom     │  │   Future    │       │
│  │    API      │  │  Webhooks   │  │  Providers  │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    CRASHLENS v2.0                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               PLUGIN SYSTEM                         │   │
│  │  • Data fetching from multiple sources             │   │
│  │  • Format conversion to standard JSONL             │   │
│  │  • Time window and batch processing               │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               POLICY ENGINE                         │   │
│  │  • YAML rule evaluation                            │   │
│  │  • Cost threshold enforcement                      │   │
│  │  • Environment scoping                             │   │
│  │  • Simulation mode                                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               OUTPUT SYSTEM                         │   │
│  │  • Violation detection and reporting               │   │
│  │  • Multiple output formats                         │   │
│  │  • Alert generation                                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  INTEGRATION POINTS                        │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │    LOCAL    │  │    CI/CD    │  │ PRODUCTION  │       │
│  │ DEVELOPMENT │  │  PIPELINES  │  │ MONITORING  │       │
│  │             │  │             │  │             │       │
│  │ • Pre-commit│  │ • GitHub    │  │ • Cron jobs │       │
│  │ • IDE       │  │   Actions   │  │ • K8s       │       │
│  │ • Testing   │  │ • GitLab CI │  │ • Docker    │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│         │                │                │               │
│         └────────────────┼────────────────┘               │
│                          │                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │    SLACK    │  │   EMAIL     │  │  DASHBOARD  │       │
│  │   ALERTS    │  │   ALERTS    │  │ INTEGRATION │       │
│  │             │  │             │  │             │       │
│  │ • Team      │  │ • PagerDuty │  │ • Grafana   │       │
│  │   channels  │  │ • Custom    │  │ • Custom UI │       │
│  │ • Real-time │  │   webhooks  │  │ • Metrics   │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Execution Flow

### 1. Data Collection
```
User runs: crashlens scan --source=langfuse --hours-back=24
           ↓
Plugin fetches data from Langfuse API
           ↓
Converts to standard CrashLens JSONL format
           ↓
Saves to temporary file for processing
```

### 2. Policy Evaluation
```
Policy Engine loads: policies/production.yaml
           ↓
Parses JSONL logs (traces, tokens, costs, metadata)
           ↓
Applies each rule to each log entry
           ↓
Collects violations with severity levels
```

### 3. Output Generation
```
Formats violations based on --format flag
           ↓
Generates reports (terminal, JSON, Slack, markdown)
           ↓
Sends alerts if violations found
           ↓
Returns appropriate exit code for automation
```

## Real-World Usage Patterns

### Pattern A: Developer Workflow
```
Developer codes → Commits → Pre-commit hook runs CrashLens
                              ↓
                         Violations found?
                              ↓
                    Yes: Commit blocked, show suggestions
                    No: Commit proceeds
```

### Pattern B: CI/CD Pipeline
```
Push to repo → GitHub Action triggers
                    ↓
              CrashLens scans recent logs
                    ↓
              Violations found?
                    ↓
         Yes: Pipeline fails, creates artifact
         No: Pipeline continues
```

### Pattern C: Production Monitoring
```
Scheduled job (every hour) → CrashLens scans Langfuse
                                    ↓
                            Critical violations?
                                    ↓
                    Yes: Send Slack alert to #ai-alerts
                    No: Log successful check
```

## What Users See

### Terminal Output (Development)
```bash
$ crashlens scan logs/dev.jsonl --simulate

🔍 CrashLens v2.0 - Policy Violation Report
==========================================
📁 Analyzed: logs/dev.jsonl (47 traces, 89 log entries)
⏱️  Duration: 1.2 seconds
💰 Total Cost: $3.45

📊 Policy Violations Found: 3
🔴 Critical: 0 violations
🟡 Medium:   2 violations  
🟢 Low:      1 violations

🔍 Medium Violations:
───────────────────────
1. Rule: expensive_model_simple_task
   Trace: trace_abc123
   Issue: GPT-4 used for 15-token prompt
   💡 Suggestion: Consider gpt-3.5-turbo for simple tasks
   
2. Rule: retry_limit_exceeded
   Trace: trace_def456
   Issue: 4 retries detected for same request
   💡 Suggestion: Implement exponential backoff

✅ SIMULATION COMPLETE - No changes made to production
```

### Slack Alert (Production)
```
🚨 CrashLens Alert - Policy Violations Detected

📊 Summary (Last Hour):
• 🔴 Critical: 2 violations  
• 🟡 Medium: 1 violation
• 💰 Cost Impact: $2.30 over budget

🔍 Critical Issues:
1. High-cost request: $0.25 (exceeds $0.10 limit)
2. Unauthorized GPT-4 usage in development

🔗 Full Report: report.md
📋 Policy: production-limits.yaml  
⏰ Checked: 2025-08-06 15:30 UTC
```

### JSON Output (CI/CD)
```json
{
  "summary": {
    "total_violations": 3,
    "critical": 2,
    "medium": 1,
    "total_cost": 8.75,
    "traces_analyzed": 156,
    "policy_file": "policies/ci.yaml"
  },
  "violations": [
    {
      "rule_id": "cost_threshold_exceeded",
      "severity": "critical",
      "trace_id": "trace_xyz789",
      "description": "Request cost $0.25 exceeds limit ($0.10)",
      "suggestion": "Use gpt-3.5-turbo or optimize prompt length",
      "timestamp": "2025-08-06T15:30:00Z"
    }
  ],
  "exit_code": 1
}
```

## Where Files Go

```
project-root/
├── crashlens/                    # Installed via pip
├── policies/                     # Your policy files
│   ├── development.yaml          # Relaxed rules for dev
│   ├── production.yaml           # Strict rules for prod
│   ├── ci.yaml                   # Fast validation for CI
│   └── langfuse/                 # Community rule packs
│       ├── retry-loop-detector.yaml
│       ├── cost-per-trace.yaml
│       └── ci-sample.yaml
├── logs/                         # Your LLM logs (optional)
│   ├── production.jsonl
│   └── development.jsonl
├── reports/                      # Generated reports
│   ├── daily-2025-08-06.md
│   └── violations.json
└── scripts/                      # Automation scripts
    ├── daily-check.sh
    └── pre-commit-hook.sh
```

## When It Runs

### Automatic Triggers
- **Pre-commit hooks**: Before code commits
- **CI/CD pipelines**: On push/PR creation  
- **Scheduled jobs**: Hourly/daily monitoring
- **Webhook events**: Custom trigger points

### Manual Triggers  
- **Development testing**: `crashlens scan --simulate`
- **Policy validation**: `crashlens validate-policy`
- **Ad-hoc analysis**: `crashlens scan logs/specific-session.jsonl`
- **Emergency checks**: `crashlens scan --source=langfuse --hours-back=1`

## What Teams Get

### Developers
- Early warning about costly LLM usage
- Suggestions for optimization
- Safe testing with simulation mode
- IDE integration possibilities

### DevOps/SRE  
- Automated policy enforcement in pipelines
- Cost budget monitoring
- Alert integration with existing tools
- Containerized deployment options

### Finance/Management
- Cost visibility and controls
- Budget enforcement mechanisms  
- Regular reporting and analysis
- ROI optimization insights

### AI/ML Teams
- Model usage governance
- Performance pattern detection
- Retry and fallback monitoring
- Best practice enforcement
