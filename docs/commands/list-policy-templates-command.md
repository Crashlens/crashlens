# CrashLens List Policy Templates Command

**View all available built-in policy templates**

---

## Table of Contents

1. [Overview](#overview)
2. [Basic Usage](#basic-usage)
3. [Available Templates](#available-templates)
4. [Template Details](#template-details)
5. [Using Templates](#using-templates)
6. [Integration Examples](#integration-examples)

---

## Overview

The `list-policy-templates` command displays all **built-in policy templates** available in CrashLens for immediate use.

**Key Features**:
✅ **10+ Built-in Templates** - Production-ready policy sets  
✅ **Detailed Descriptions** - Understand what each template detects  
✅ **Rule Counts** - See how many rules in each template  
✅ **Severity Info** - Know the impact level  
✅ **Quick Reference** - Fast lookup for template selection  

**Syntax**:
```bash
crashlens list-policy-templates
```

**Quick Start**:
```bash
# List all templates
crashlens list-policy-templates

# Use a template
crashlens scan logs.jsonl --policy-template retry-loop-prevention
```

---

## Basic Usage

### List All Templates

```bash
crashlens list-policy-templates
```

**Example output**:
```
📋 Available Policy Templates

1. retry-loop-prevention (5 rules)
   Detect excessive retry patterns and duplicate requests
   Severity: fatal, error
   Use: --policy-template retry-loop-prevention

2. model-overkill-detection (4 rules)
   Flag expensive models used on simple tasks
   Severity: error, warn
   Use: --policy-template model-overkill-detection

3. fallback-chain-detector (3 rules)
   Monitor fallback patterns and cascade failures
   Severity: error, warn
   Use: --policy-template fallback-chain-detector

4. budget-protection (6 rules)
   Cost cap enforcement and budget alerts
   Severity: fatal, error, warn
   Use: --policy-template budget-protection

5. rate-limit-management (4 rules)
   Detect rate limit errors and quota exhaustion
   Severity: error, warn
   Use: --policy-template rate-limit-management

6. chain-recursion-prevention (3 rules)
   Prevent infinite loops and circular chains
   Severity: fatal
   Use: --policy-template chain-recursion-prevention

7. pii-exposure-detection (5 rules)
   Detect PII in prompts and responses
   Severity: fatal, error
   Use: --policy-template pii-exposure-detection

8. latency-monitoring (4 rules)
   Alert on slow responses and timeouts
   Severity: warn
   Use: --policy-template latency-monitoring

9. error-storm-detection (3 rules)
   Identify error spikes and cascading failures
   Severity: error
   Use: --policy-template error-storm-detection

10. token-efficiency (5 rules)
    Optimize token usage patterns
    Severity: warn
    Use: --policy-template token-efficiency

💡 Use multiple templates:
   crashlens scan logs.jsonl --policy-template "retry-loop-prevention,budget-protection"

💡 Use all templates:
   crashlens scan logs.jsonl --policy-template all
```

---

## Available Templates

### Quick Reference Table

| Template | Rules | Primary Focus | Max Severity | Best For |
|----------|-------|---------------|--------------|----------|
| `retry-loop-prevention` | 5 | Retry patterns | Fatal | Production monitoring |
| `model-overkill-detection` | 4 | Cost optimization | Error | Cost control |
| `fallback-chain-detector` | 3 | Fallback monitoring | Error | Reliability |
| `budget-protection` | 6 | Cost caps | Fatal | FinOps |
| `rate-limit-management` | 4 | Rate limits | Error | Quota management |
| `chain-recursion-prevention` | 3 | Infinite loops | Fatal | Safety |
| `pii-exposure-detection` | 5 | Data privacy | Fatal | Compliance |
| `latency-monitoring` | 4 | Performance | Warn | SRE monitoring |
| `error-storm-detection` | 3 | Error spikes | Error | Incident response |
| `token-efficiency` | 5 | Token optimization | Warn | Efficiency |
| `all` | All | Comprehensive | Fatal | Complete coverage |

---

## Template Details

### 1. retry-loop-prevention

**Purpose**: Detect excessive retry patterns and duplicate requests

**Rules included**:
- Excessive retry attempts (>3)
- Identical prompts within time window
- Exponential backoff failures
- Retry storm detection
- Cost waste from retries

**Example violations**:
- Same prompt retried 5 times
- No backoff delay between retries
- Total retry cost >$1

**Use when**:
- Implementing retry logic
- Optimizing API resilience
- Reducing token waste

**Command**:
```bash
crashlens scan logs.jsonl --policy-template retry-loop-prevention
```

---

### 2. model-overkill-detection

**Purpose**: Flag expensive models used on simple tasks

**Rules included**:
- GPT-4 with <10 completion tokens
- Expensive models for classification
- Model mismatch detection
- Cost-inefficient patterns

**Example violations**:
- GPT-4 for "yes/no" question ($0.003 wasted)
- Claude-3-opus for simple summaries
- High-cost model for low-value tasks

**Use when**:
- Optimizing model selection
- Reducing AI costs
- Improving efficiency

**Command**:
```bash
crashlens scan logs.jsonl --policy-template model-overkill-detection
```

---

### 3. fallback-chain-detector

**Purpose**: Monitor fallback patterns and cascade failures

**Rules included**:
- Excessive fallback attempts (>3)
- Fallback chain exhaustion
- All fallbacks failing

**Example violations**:
- GPT-4 → GPT-3.5 → Claude → Gemini (all fail)
- >3 fallback models tried
- Cumulative fallback cost >$2

**Use when**:
- Implementing fallback logic
- Monitoring reliability
- Detecting systemic issues

**Command**:
```bash
crashlens scan logs.jsonl --policy-template fallback-chain-detector
```

---

### 4. budget-protection

**Purpose**: Cost cap enforcement and budget alerts

**Rules included**:
- Per-request cost cap
- Daily/weekly budget limits
- Cost threshold alerts
- Cumulative cost tracking
- Budget deviation alerts
- Quota warnings

**Example violations**:
- Single request cost >$5
- Daily cost exceeds $100
- 80% of monthly budget used

**Use when**:
- Enforcing cost controls
- FinOps monitoring
- Budget compliance

**Command**:
```bash
crashlens scan logs.jsonl --policy-template budget-protection
```

---

### 5. rate-limit-management

**Purpose**: Detect rate limit errors and quota exhaustion

**Rules included**:
- 429 (Rate Limit) errors
- Quota exceeded warnings
- RPM/TPM limit detection
- Rate limit storm patterns

**Example violations**:
- >10 rate limit errors in 5 minutes
- Consistent 429 responses
- Quota exhaustion detected

**Use when**:
- Managing API quotas
- Preventing service disruption
- Optimizing request patterns

**Command**:
```bash
crashlens scan logs.jsonl --policy-template rate-limit-management
```

---

### 6. chain-recursion-prevention

**Purpose**: Prevent infinite loops and circular chains

**Rules included**:
- Infinite loop detection
- Circular chain references
- Excessive chain depth (>10)

**Example violations**:
- Chain calls itself recursively
- Circular reference: A → B → C → A
- Chain depth exceeds 10 levels

**Use when**:
- Building agent chains
- Preventing runaway costs
- Safety in production

**Command**:
```bash
crashlens scan logs.jsonl --policy-template chain-recursion-prevention
```

---

### 7. pii-exposure-detection

**Purpose**: Detect PII in prompts and responses

**Rules included**:
- Email addresses in prompts
- Phone numbers in logs
- SSN patterns detected
- Credit card exposure
- IP address leakage

**Example violations**:
- Email in prompt: "user@example.com"
- SSN in response: "123-45-6789"
- Unredacted PII in logs

**Use when**:
- Compliance monitoring (GDPR, HIPAA)
- Data privacy enforcement
- Security audits

**Command**:
```bash
crashlens scan logs.jsonl --policy-template pii-exposure-detection
```

---

### 8. latency-monitoring

**Purpose**: Alert on slow responses and timeouts

**Rules included**:
- Response time >5s
- Timeout errors
- Latency degradation
- P95 latency alerts

**Example violations**:
- Response took 12 seconds
- Request timed out
- P95 latency increased 50%

**Use when**:
- SRE monitoring
- Performance optimization
- User experience tracking

**Command**:
```bash
crashlens scan logs.jsonl --policy-template latency-monitoring
```

---

### 9. error-storm-detection

**Purpose**: Identify error spikes and cascading failures

**Rules included**:
- >10 errors in 5 minutes
- Error rate >50%
- Cascading failures detected

**Example violations**:
- 25 errors in 3 minutes
- Error rate jumped from 5% to 60%
- Multiple services failing

**Use when**:
- Incident detection
- Reliability monitoring
- Alerting systems

**Command**:
```bash
crashlens scan logs.jsonl --policy-template error-storm-detection
```

---

### 10. token-efficiency

**Purpose**: Optimize token usage patterns

**Rules included**:
- Excessive prompt tokens (>4000)
- Inefficient context usage
- Token waste patterns
- Prompt optimization opportunities
- Response truncation detection

**Example violations**:
- Prompt uses 8000 tokens (could be 2000)
- Redundant context included
- Response truncated due to token limit

**Use when**:
- Optimizing costs
- Improving efficiency
- Prompt engineering

**Command**:
```bash
crashlens scan logs.jsonl --policy-template token-efficiency
```

---

### 11. all (Meta-Template)

**Purpose**: Comprehensive coverage with all templates

**Rules included**: All rules from all templates (40+ rules)

**Use when**:
- Initial assessment
- Comprehensive audits
- Don't know which issues to prioritize

**Command**:
```bash
crashlens scan logs.jsonl --policy-template all
```

---

## Using Templates

### Single Template

```bash
# Use one template
crashlens scan logs.jsonl --policy-template retry-loop-prevention
```

### Multiple Templates

```bash
# Combine templates
crashlens scan logs.jsonl \
  --policy-template "retry-loop-prevention,model-overkill-detection,budget-protection"
```

### All Templates

```bash
# Use all templates
crashlens scan logs.jsonl --policy-template all
```

### With Guard Command

```bash
# Guard with template
crashlens guard logs.jsonl \
  --policy-template retry-loop-prevention \
  --fail-on-violations
```

### With Init Command

```bash
# Setup with specific templates
export CRASHLENS_TEMPLATES="retry-loop-prevention,budget-protection"
crashlens init --non-interactive
```

---

## Integration Examples

### Example 1: Cost Optimization Focus

```bash
# Focus on cost-related templates
crashlens scan logs.jsonl \
  --policy-template "model-overkill-detection,budget-protection,token-efficiency"
```

### Example 2: Reliability Monitoring

```bash
# Focus on reliability
crashlens scan logs.jsonl \
  --policy-template "retry-loop-prevention,fallback-chain-detector,error-storm-detection"
```

### Example 3: Compliance & Security

```bash
# Focus on privacy and security
crashlens scan logs.jsonl \
  --policy-template "pii-exposure-detection,chain-recursion-prevention"
```

### Example 4: Performance Monitoring

```bash
# Focus on performance
crashlens scan logs.jsonl \
  --policy-template "latency-monitoring,error-storm-detection"
```

### Example 5: Development Environment

```bash
# Comprehensive for development
crashlens scan logs.jsonl --policy-template all --format markdown
```

### Example 6: Production Gate (CI/CD)

```bash
# Strict production checks
crashlens guard logs.jsonl \
  --policy-template "retry-loop-prevention,budget-protection,pii-exposure-detection" \
  --fail-on-violations \
  --severity fatal
```

### Example 7: Weekly Audit

```bash
# Full weekly audit
crashlens scan weekly-logs.jsonl \
  --policy-template all \
  --detailed \
  --report-dir ./weekly-audit/
```

---

## Combining with Custom Rules

### Template + Custom Rules

```bash
# Use template as base, add custom rules
crashlens scan logs.jsonl \
  --policy-template retry-loop-prevention \
  --policy-file custom-rules.yaml
```

**Note**: Custom rules are evaluated in addition to template rules

### Override Template Rules

```bash
# Suppress specific template rules, keep others
crashlens guard logs.jsonl \
  --policy-template all \
  --suppress RL001 \
  --suppress RL003
```

---

## Template Selection Guide

### By Use Case

**Starting out**:
- Use: `all`
- Why: Discover all issues

**Cost optimization**:
- Use: `model-overkill-detection`, `budget-protection`, `token-efficiency`
- Why: Focus on cost savings

**Reliability**:
- Use: `retry-loop-prevention`, `fallback-chain-detector`, `error-storm-detection`
- Why: Improve service reliability

**Compliance**:
- Use: `pii-exposure-detection`
- Why: GDPR, HIPAA compliance

**Performance**:
- Use: `latency-monitoring`, `rate-limit-management`
- Why: User experience

**Production readiness**:
- Use: `retry-loop-prevention`, `chain-recursion-prevention`, `budget-protection`
- Why: Safety and cost control

### By Environment

**Development**:
```bash
crashlens scan logs.jsonl --policy-template all
```

**Staging**:
```bash
crashlens guard logs.jsonl \
  --policy-template "retry-loop-prevention,model-overkill-detection,budget-protection"
```

**Production**:
```bash
crashlens guard logs.jsonl \
  --policy-template "retry-loop-prevention,budget-protection,pii-exposure-detection,chain-recursion-prevention" \
  --fail-on-violations \
  --severity fatal
```

---

## Best Practices

### 1. Start with All Templates

```bash
# Initial assessment
crashlens scan logs.jsonl --policy-template all --format json

# Identify priority issues
# Then focus on specific templates
```

### 2. Layer Templates by Severity

**Development** (all issues):
```bash
crashlens scan logs.jsonl --policy-template all --severity warn
```

**Staging** (medium issues):
```bash
crashlens scan logs.jsonl --policy-template all --severity error
```

**Production** (critical only):
```bash
crashlens guard logs.jsonl --policy-template all --severity fatal --fail-on-violations
```

### 3. Combine Related Templates

**Cost focus**:
```bash
--policy-template "model-overkill-detection,budget-protection,token-efficiency"
```

**Reliability focus**:
```bash
--policy-template "retry-loop-prevention,fallback-chain-detector,error-storm-detection"
```

### 4. Document Template Choices

```yaml
# .crashlens/config.yaml
templates:
  production:
    - retry-loop-prevention
    - budget-protection
    - pii-exposure-detection
  staging:
    - retry-loop-prevention
    - model-overkill-detection
  development:
    - all
```

### 5. Use with Init Command

```bash
# Setup with specific templates
export CRASHLENS_TEMPLATES="retry-loop-prevention,budget-protection"
crashlens init --non-interactive
```

---

## See Also

- **[Scan Command](./scan-command.md)**: Use templates with scan
- **[Guard Command](./guard-command.md)**: Use templates with guard
- **[Init Command](./init-command.md)**: Setup with templates
- **[CLI Reference](../CLI_COMMAND_REFERENCE.md)**: All commands

---

**Quick Start**: `crashlens list-policy-templates`
