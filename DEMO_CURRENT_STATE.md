# 5-Minute CrashLens Demo - Current State

## Quick Demo (What Currently Works)

### 1. Generate Test Data
```bash
crashlens simulate --output demo-test.jsonl --count 20
```

### 2. Check Policy Violations (This Works!)
```bash
crashlens policy-check demo-test.jsonl --policy-file crashlens/config/modern-policy.yaml
```
**Expected**: See policy violations with specific cost thresholds and suggestions

### 3. Get Cost Summary (This Works!)
```bash  
crashlens scan examples-logs/demo-logs.jsonl --summary
```
**Expected**: See $859.52 total cost, model breakdown, top expensive traces

### 4. See the Integration Gap (The Problem)
```bash
crashlens scan examples-logs/demo-logs.jsonl --policy-file crashlens/config/modern-policy.yaml
```
**Expected**: Reports 2,178 violations found, then says "No token waste detected" 

## What You'll See

**Policy Check Output** (Working):
```
⚠️  Found 2178 policy violations:
============================================================

⚠️ HIGH SEVERITY (2178 violations):
  1. high_cost_request (line 62437)
     Reason: cost=0.06075 (rule: >0.05)
     Action: warn
     Suggestion: Consider using a more cost-effective model
```

**Scan Output** (Broken Integration):
```
⚠️  Found 2178 policy violations!
  ⚠️ 2178 high severity violations
🔍 Running additional waste pattern analysis...
✅ *No token waste patterns detected!* Your GPT usage looks efficient. 🎉
```

## The Gap

- Policy engine: ✅ "Found 2,178 violations, cost=0.06075, use cheaper models"
- Waste pattern analysis: ❌ "No waste detected"
- Final report: ❌ Shows waste patterns only, ignores policy results

## Ideal Demo (Once Fixed)

```bash
crashlens scan examples-logs/demo-logs.jsonl --policy-file crashlens/config/modern-policy.yaml

# Should output:
# 🎯 Cost Savings Detected!
# • 2,178 high-cost requests could use cheaper models
# • Potential savings: $400/month (47% reduction)  
# • Switch GPT-4 → GPT-3.5 for simple requests
```
