# 📘 CrashLens v2.0 User Manual
## Complete Integration Guide for LLM Cost Monitoring

**Version:** 2.0.0  
**Date:** August 6, 2025  
**Audience:** Developers, DevOps Engineers, AI Teams

---

## 🚀 **Quick Start (5 Minutes)**

### Installation
```bash
# Install CrashLens
pip install crashlens

# Verify installation
crashlens --version
# Output: CrashLens CLI v2.0.0 (Policy + Detector Hybrid)
```

### First Run (Local Files)
```bash
# Test with sample logs
crashlens scan examples/test-logs/demo-logs.jsonl --simulate

# Output:
# 🎯 SIMULATION MODE: Policy violations for demo-logs.jsonl
# ================================================
# 📊 Violation Summary:
#    🔴 Critical: 1 violations  
#    🟡 Medium:   2 violations
#    🟢 Low:      0 violations
#    📋 Total:    3 violations
# ✅ SIMULATION COMPLETE - No changes made to production
```

---

## 🏗️ **System Integration Patterns**

### **Pattern 1: Local Development Workflow**

**Where:** Developer's laptop  
**When:** Before committing code  
**What:** Validate LLM usage in development

```bash
# Developer workflow
cd my-ai-project/

# Scan local LLM logs
crashlens scan logs/dev-session.jsonl --policy policies/dev-policy.yaml --simulate

# Example output:
# 🔍 Found 3 policy violations:
#   1. [MEDIUM] expensive_model_simple_task
#      GPT-4 used for 15-token prompt - consider gpt-3.5-turbo
#   2. [MEDIUM] retry_limit_exceeded  
#      5 retries detected - implement exponential backoff
#   3. [CRITICAL] cost_threshold_exceeded
#      Request cost $0.12 exceeds $0.05 limit
```

**Integration Points:**
- Pre-commit hooks
- IDE extensions  
- Local testing scripts

### **Pattern 2: CI/CD Pipeline Integration**

**Where:** GitHub Actions, GitLab CI, Jenkins  
**When:** On every pull request and deployment  
**What:** Automated policy enforcement

#### GitHub Actions Example
```yaml
# .github/workflows/llm-policy-check.yml
name: LLM Policy Validation
on: [push, pull_request]

jobs:
  policy-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install CrashLens
        run: pip install crashlens
        
      - name: Validate LLM Usage
        run: |
          crashlens scan logs/ --policy policies/ci-policy.yaml --format=json --output=violations.json
        env:
          LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
          LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
          
      - name: Upload Violation Report
        uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: llm-violations
          path: violations.json
```

**Exit Codes:**
- `0` - No violations found ✅
- `1` - Policy violations detected ❌
- `2` - Configuration or runtime error ❌

### **Pattern 3: Production Monitoring**

**Where:** Production servers, monitoring systems  
**When:** Scheduled (hourly, daily) or triggered by events  
**What:** Continuous cost monitoring and alerting

#### Cron Job Example
```bash
# /etc/crontab - Run every hour
0 * * * * /usr/local/bin/crashlens scan --source=langfuse --hours-back=1 --policy /etc/crashlens/prod-policy.yaml --slack-webhook=$SLACK_WEBHOOK
```

#### Docker Container
```dockerfile
# Dockerfile
FROM python:3.12-slim
RUN pip install crashlens
COPY policies/ /app/policies/
WORKDIR /app

# Schedule monitoring
CMD ["crashlens", "scan", "--source=langfuse", "--policy=policies/production.yaml", "--format=slack"]
```

---

## 🔧 **Integration Methods**

### **Method 1: File-Based (Local Logs)**

**Use Case:** Analyze local JSONL files from your LLM application

```bash
# Basic file analysis
crashlens scan my-app-logs.jsonl

# With custom policy
crashlens scan logs/ --policy my-team-policy.yaml

# Simulation mode (safe testing)
crashlens scan logs/ --policy strict-policy.yaml --simulate
```

**File Structure:**
```
my-project/
├── logs/
│   ├── production.jsonl      # Production LLM logs
│   ├── development.jsonl     # Dev environment logs
│   └── test-session.jsonl    # Test runs
├── policies/
│   ├── production.yaml       # Strict production rules
│   ├── development.yaml      # Relaxed dev rules
│   └── ci.yaml              # CI/CD validation rules
└── scripts/
    └── check-llm-usage.sh    # Automation script
```

### **Method 2: API Integration (Live Monitoring)**

**Use Case:** Connect directly to LLM platforms for real-time monitoring

#### Langfuse Integration
```bash
# Set up credentials
export LANGFUSE_PUBLIC_KEY="pk-lf-your-public-key"
export LANGFUSE_SECRET_KEY="sk-lf-your-secret-key"

# Monitor last 24 hours
crashlens scan --source=langfuse --hours-back=24 --policy policies/production.yaml

# Real-time monitoring with Slack alerts
crashlens scan --source=langfuse --hours-back=1 --slack-webhook=$WEBHOOK --slack-channel="#ai-alerts"
```

#### OpenAI Integration
```bash
# Set up credentials
export OPENAI_API_KEY="sk-your-openai-key"
export OPENAI_ORG_ID="org-your-organization"

# Monitor organizational usage
crashlens scan --source=openai --organization-id=$OPENAI_ORG_ID --policy policies/cost-limits.yaml
```

#### Helicone Integration
```bash
# Set up credentials  
export HELICONE_API_KEY="sk-your-helicone-key"

# Monitor request analytics
crashlens scan --source=helicone --hours-back=12 --policy policies/performance.yaml
```

### **Method 3: Webhook/Event-Driven**

**Use Case:** Triggered monitoring from external systems

```bash
# Webhook endpoint that triggers CrashLens
curl -X POST webhook.example.com/crashlens-trigger \
  -H "Content-Type: application/json" \
  -d '{"source": "langfuse", "policy": "emergency-limits", "alert": true}'
```

---

## 📊 **Output Formats & What They Show**

### **1. Terminal Output (Default)**
```bash
crashlens scan logs.jsonl

# Output:
🔍 CrashLens v2.0 - Policy Violation Report
==========================================
📁 Analyzed: logs.jsonl (127 traces, 234 log entries)
⏱️  Duration: 2.3 seconds
💰 Total Cost: $12.45

📊 Policy Violations Found: 8
🔴 Critical: 2 violations
🟡 Medium:   4 violations  
🟢 Low:      2 violations

🔍 Critical Violations:
───────────────────────
1. Rule: high_cost_request_block
   Trace: trace_abc123
   Issue: Request cost $0.15 exceeds limit ($0.10)
   💡 Suggestion: Use gpt-3.5-turbo or optimize prompt length

2. Rule: unauthorized_model_usage
   Trace: trace_def456  
   Issue: GPT-4 not allowed in development environment
   💡 Suggestion: Use approved models: gpt-3.5-turbo, gpt-4o-mini

🔄 Medium Violations:
───────────────────
[... detailed violation list ...]

✅ Analysis Complete - See full report: report.md
```

### **2. JSON Output (CI/CD & Automation)**
```bash
crashlens scan logs.jsonl --format=json --output=violations.json

# violations.json:
{
  "summary": {
    "total_violations": 8,
    "critical": 2,
    "medium": 4, 
    "low": 2,
    "total_cost": 12.45,
    "traces_analyzed": 127
  },
  "violations": [
    {
      "rule_id": "high_cost_request_block",
      "severity": "critical",
      "trace_id": "trace_abc123",
      "description": "Request cost $0.15 exceeds limit ($0.10)",
      "suggestion": "Use gpt-3.5-turbo or optimize prompt length",
      "timestamp": "2025-08-06T10:30:00Z",
      "metadata": {
        "model": "gpt-4",
        "tokens": 1250,
        "cost": 0.15
      }
    }
  ]
}
```

### **3. Slack Notifications**
```bash
crashlens scan --source=langfuse --slack-webhook=$WEBHOOK

# Slack Message:
🚨 CrashLens Alert - Policy Violations Detected

📊 Summary (Last Hour):
• 🔴 Critical: 2 violations  
• 🟡 Medium: 4 violations
• 💰 Cost Impact: $3.20 over budget

🔍 Top Issues:
1. GPT-4 overuse in development (4 instances)
2. High-cost requests exceeding $0.10 (2 instances)

🔗 Full Report: [View Details](link-to-report)
📋 Policy: production-limits.yaml
⏰ Checked: 2025-08-06 10:30 UTC
```

### **4. Markdown Reports**
```bash
crashlens scan logs.jsonl --format=markdown --output=weekly-report.md

# weekly-report.md:
# 📊 CrashLens Weekly Report
## August 1-6, 2025

### Executive Summary
- **Total Traces:** 1,247
- **Policy Violations:** 23
- **Cost Savings:** $127.50 (prevented overages)
- **Top Issue:** GPT-4 overuse for simple tasks

### Detailed Analysis
[... charts, trends, recommendations ...]
```

---

## ⚙️ **Configuration & Policies**

### **Policy File Structure**
```yaml
# policies/production.yaml
global:
  max_violations_per_rule: 100
  enable_cost_estimation: true

cost_thresholds:
  warning_threshold: 0.05    # $0.05 per request
  critical_threshold: 0.20   # $0.20 per request
  daily_budget: 100.00       # $100 per day
  monthly_budget: 2000.00    # $2000 per month

rules:
  - id: block_expensive_dev_usage
    description: "Prevent expensive models in development"
    match:
      metadata.env: ["development", "staging"]
      input.model: ["gpt-4", "claude-3-opus"]
    action: fail
    severity: critical
    suggestion: "Use gpt-3.5-turbo or gpt-4o-mini in development"
    
  - id: retry_storm_detection
    description: "Detect excessive retry patterns"
    match:
      retry_count: ">3"
    action: warn
    severity: medium
    suggestion: "Implement exponential backoff and circuit breakers"
```

### **Environment-Specific Policies**

#### Development Policy
```yaml
# policies/development.yaml - Relaxed rules for dev
rules:
  - id: cost_reminder
    match:
      cost: ">0.02"
    action: warn
    suggestion: "Consider cost optimization for production"
```

#### Production Policy  
```yaml
# policies/production.yaml - Strict enforcement
rules:
  - id: cost_enforcement
    match:
      cost: ">0.10"
    action: fail
    suggestion: "Request exceeds production cost limits"
```

#### CI/CD Policy
```yaml
# policies/ci.yaml - Fast validation
rules:
  - id: model_allowlist
    match:
      input.model: "not_in:[gpt-3.5-turbo, gpt-4o-mini]"
    action: fail
    suggestion: "Only approved models allowed in CI"
```

---

## 🔄 **Automation & Scheduling**

### **Daily Monitoring Script**
```bash
#!/bin/bash
# scripts/daily-llm-check.sh

echo "🔍 Starting daily LLM usage analysis..."

# Check production usage
crashlens scan --source=langfuse \
  --hours-back=24 \
  --policy=policies/production.yaml \
  --format=json \
  --output=/var/log/crashlens/daily-$(date +%Y%m%d).json

# Send Slack summary
if [ $? -eq 1 ]; then
  echo "❌ Policy violations detected - sending alert"
  crashlens scan --source=langfuse \
    --hours-back=24 \
    --policy=policies/production.yaml \
    --slack-webhook=$SLACK_WEBHOOK \
    --slack-channel="#ai-monitoring"
else
  echo "✅ No violations - all good!"
fi
```

### **Kubernetes CronJob**
```yaml
# k8s/crashlens-monitor.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: crashlens-monitor
spec:
  schedule: "0 */6 * * *"  # Every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: crashlens
            image: crashlens:2.0.0
            command:
            - crashlens
            - scan
            - --source=langfuse
            - --hours-back=6
            - --policy=/config/production.yaml
            - --slack-webhook=$(SLACK_WEBHOOK)
            env:
            - name: LANGFUSE_PUBLIC_KEY
              valueFrom:
                secretKeyRef:
                  name: langfuse-creds
                  key: public-key
            volumeMounts:
            - name: policy-config
              mountPath: /config
          restartPolicy: OnFailure
```

---

## 📈 **Monitoring & Alerting Setup**

### **Alert Channels**

#### Slack Integration
```bash
# Set up Slack webhook
export SLACK_WEBHOOK="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"

# Test alert
crashlens scan --source=langfuse --simulate --slack-webhook=$SLACK_WEBHOOK
```

#### Email Notifications (via webhook)
```bash
# Custom webhook for email alerts
crashlens scan logs.jsonl --webhook="https://api.example.com/email-alert" --format=json
```

#### PagerDuty Integration
```bash
# Critical violations trigger PagerDuty
if crashlens scan --source=langfuse --policy=critical-only.yaml; then
  echo "✅ No critical issues"
else
  curl -X POST https://events.pagerduty.com/v2/enqueue \
    -H "Content-Type: application/json" \
    -d '{"routing_key": "'$PAGERDUTY_KEY'", "event_action": "trigger", "payload": {"summary": "LLM Cost Alert", "source": "crashlens"}}'
fi
```

### **Dashboard Integration**

#### Grafana Metrics
```bash
# Export metrics for Grafana
crashlens scan --source=langfuse --format=json | jq '.summary' > /var/lib/grafana/crashlens-metrics.json
```

#### Custom Dashboard
```python
# dashboard/app.py - Simple web dashboard
import json
import subprocess

def get_llm_metrics():
    result = subprocess.run([
        'crashlens', 'scan', '--source=langfuse', 
        '--format=json', '--hours-back=24'
    ], capture_output=True, text=True)
    
    return json.loads(result.stdout)

# Display in web UI
metrics = get_llm_metrics()
print(f"Violations: {metrics['summary']['total_violations']}")
print(f"Cost: ${metrics['summary']['total_cost']}")
```

---

## 🚀 **Advanced Use Cases**

### **Multi-Environment Setup**
```bash
# Different policies per environment
crashlens scan logs/prod.jsonl --policy=policies/production.yaml
crashlens scan logs/dev.jsonl --policy=policies/development.yaml  
crashlens scan logs/test.jsonl --policy=policies/ci.yaml
```

### **Cost Budget Enforcement**
```bash
# Daily budget check
crashlens scan --source=openai --hours-back=24 --policy=policies/daily-budget.yaml

# Monthly budget tracking
crashlens scan --source=openai --hours-back=720 --policy=policies/monthly-budget.yaml
```

### **Team-Specific Monitoring**
```bash
# Monitor specific teams/projects
crashlens scan --source=langfuse --policy=policies/team-ai.yaml --format=slack --slack-channel="#team-ai"
crashlens scan --source=langfuse --policy=policies/team-research.yaml --format=slack --slack-channel="#team-research"
```

---

## 🎯 **Best Practices**

### **1. Start with Simulation**
```bash
# Always test policies first
crashlens scan logs.jsonl --policy=new-policy.yaml --simulate
```

### **2. Gradual Policy Rollout**
```bash
# Week 1: Warning only
crashlens scan --policy=policies/warnings-only.yaml

# Week 2: Add medium severity  
crashlens scan --policy=policies/medium-enforcement.yaml

# Week 3: Full enforcement
crashlens scan --policy=policies/full-enforcement.yaml
```

### **3. Regular Policy Reviews**
```bash
# Monthly policy effectiveness review
crashlens scan --source=langfuse --hours-back=720 --format=json > monthly-analysis.json
```

### **4. Team Training**
```bash
# Show team what would be blocked
crashlens scan team-logs.jsonl --simulate --verbose
```

---

## 🔧 **Troubleshooting**

### **Common Issues**

#### Issue: "No violations found but expecting some"
```bash
# Debug with verbose output
crashlens scan logs.jsonl --policy=my-policy.yaml --verbose

# Check policy syntax
crashlens validate-policy my-policy.yaml
```

#### Issue: "API connection failed"
```bash
# Test credentials
export LANGFUSE_PUBLIC_KEY="pk-..."
export LANGFUSE_SECRET_KEY="sk-..."
crashlens scan --source=langfuse --hours-back=1 --verbose
```

#### Issue: "Too many violations"
```bash
# Use simulation to understand patterns
crashlens scan --simulate --verbose

# Start with warnings only
crashlens scan --policy=policies/warnings-only.yaml
```

### **Debug Commands**
```bash
# Check configuration
crashlens info logs.jsonl

# Validate policy files
crashlens validate-policy policies/

# Test with sample data
crashlens scan examples/test-logs/ --simulate
```

---

## 📋 **Summary: Integration Checklist**

### **✅ Initial Setup**
- [ ] Install CrashLens: `pip install crashlens`
- [ ] Test with sample data: `crashlens scan examples/ --simulate`
- [ ] Create initial policy file
- [ ] Set up API credentials (if using plugins)

### **✅ Development Integration**  
- [ ] Add to pre-commit hooks
- [ ] Configure IDE integration
- [ ] Create development-specific policies
- [ ] Train team on simulation mode

### **✅ CI/CD Integration**
- [ ] Add GitHub Actions workflow
- [ ] Configure policy validation in pipelines  
- [ ] Set up artifact collection for violation reports
- [ ] Test with pull request workflows

### **✅ Production Monitoring**
- [ ] Set up scheduled monitoring (cron/k8s)
- [ ] Configure Slack/email alerts
- [ ] Create production policy files
- [ ] Set up dashboard integration

### **✅ Ongoing Maintenance**
- [ ] Monthly policy effectiveness reviews
- [ ] Quarterly cost threshold adjustments
- [ ] Regular team training updates
- [ ] Policy version control and documentation

---

**🎯 With this integration guide, you can deploy CrashLens v2.0 across your entire LLM workflow - from local development to production monitoring - ensuring cost optimization and policy compliance at every stage.**
