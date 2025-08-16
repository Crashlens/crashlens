# 🔍 CrashLens Architecture Analysis: Policy vs Scan Discrepancy

## 🚨 Problem Identified

**The Issue**: `crashlens policy-check` finds **0 violations** while `crashlens scan` finds **53,185 issues** costing **$1,419.77** in the same log file.

## 🔬 Root Cause Analysis

### Policy Templates Expect Metadata That Doesn't Exist

**Policy templates look for:**
```yaml
# From model-overkill-detection.yaml
match:
  input.model: ["gpt-4", "gpt-4-turbo", "gpt-4o"]
  OR:
    - usage.prompt_tokens: "<50"        # ✅ EXISTS
    - input.prompt_length: "<200"      # ❌ DOESN'T EXIST
    - task_complexity: "simple"        # ❌ DOESN'T EXIST

# From retry-loop-prevention.yaml  
match:
  retry_count: ">3"                     # ❌ DOESN'T EXIST
  time_between_retries: "<10"          # ❌ DOESN'T EXIST
```

**Actual log data structure:**
```json
{
  "traceId": "trace_overkill_01",
  "startTime": "2025-07-22T10:30:25Z",
  "input": {
    "model": "gpt-4",                   # ✅ EXISTS
    "prompt": "What is 2+2?"           # ✅ EXISTS (but no prompt_length)
  },
  "usage": {
    "prompt_tokens": 5,                 # ✅ EXISTS
    "completion_tokens": 3,             # ✅ EXISTS
    "total_tokens": 8                   # ✅ EXISTS
  },
  "cost": 0.00033                       # ✅ EXISTS
}
```

### Scan Detectors Work on Actual Data

**Scan detectors analyze real fields:**
```python
# OverkillModelDetector checks:
- input.model == "gpt-4"               # ✅ EXISTS
- usage.prompt_tokens < 20             # ✅ EXISTS
- len(input.prompt) < 150              # ✅ DERIVED FROM EXISTING

# RetryLoopDetector infers:
- Multiple entries with same traceId   # ✅ CAN ANALYZE
- Time patterns between calls          # ✅ CAN DERIVE
- Cost accumulation patterns           # ✅ CAN CALCULATE
```

## 📊 Evidence: What Each System Found

### Policy-Check Results: 0 Violations
```
🔍 Checking 141570 log entries against policy rules...
✅ No policy violations found! Your usage patterns look compliant.
```

**Reason**: Policy rules look for `retry_count`, `task_complexity`, `input.prompt_length` - none of which exist in the actual logs.

### Scan Results: 53,185 Issues
```
🔄 Retry Loops: 187 traces • $859.52 wasted
❓ Overkill Models: 52998 traces • $560.24 wasted
Total: 53185 issues • $1419.77 wasted
```

**Reason**: Scan detectors analyze the actual data:
- **Overkill**: `gpt-4` model + `usage.prompt_tokens: 5` + `prompt: "What is 2+2?"` = Clear overkill
- **Retry Loops**: Multiple entries with same `traceId` + temporal analysis = Retry pattern detection

## 🏗️ Architectural Mismatch

### Two Separate Systems
1. **Policy Engine**: Rule-based, expects structured metadata
2. **Waste Detectors**: Heuristic-based, works on actual log data

### Integration Gap
- Policy engine and waste detectors don't share logic
- No unified violation detection system
- Different data expectations and analysis methods

## 🛠️ Solutions

### Immediate Fix Option 1: Update Policy Templates
Modify policy templates to use actual log fields:

```yaml
# BEFORE (doesn't work) - Current model-overkill-detection.yaml
rules:
  - id: gpt4_for_simple_tasks
    match:
      input.model: ["gpt-4", "gpt-4-turbo", "gpt-4o"]
      OR:
        - usage.prompt_tokens: "<50"        # ✅ EXISTS but OR logic broken
        - input.prompt_length: "<200"      # ❌ DOESN'T EXIST
        - task_complexity: "simple"        # ❌ DOESN'T EXIST

# AFTER (would work) - Fixed version
rules:
  - id: gpt4_for_simple_tasks
    match:
      input.model: ["gpt-4", "gpt-4-turbo", "gpt-4o"]
      usage.prompt_tokens: "<50"           # ✅ Simple condition that exists
```

### Immediate Fix Option 2: Create Working Policy Templates
Replace the broken templates with ones that use actual log structure:

```yaml
# working-model-overkill-detection.yaml
rules:
  - id: gpt4_for_tiny_prompts
    description: "GPT-4 used for very small prompts (wasteful)"
    match:
      input.model: ["gpt-4", "gpt-4-turbo", "gpt-4o"]
      usage.prompt_tokens: "<20"
    action: fail
    severity: high
    
  - id: expensive_model_small_response
    description: "Expensive model generating tiny responses"
    match:
      input.model: ["gpt-4", "gpt-4-turbo", "claude-3-opus"]
      usage.completion_tokens: "<10"
    action: warn
    severity: medium
```

### Immediate Fix Option 2: Enhance Policy Engine
Make policy engine derive missing fields:

```python
# In policy evaluation
def enhance_log_entry(log_entry):
    # Add derived fields that policies expect
    if 'input' in log_entry and 'prompt' in log_entry['input']:
        log_entry['input']['prompt_length'] = len(log_entry['input']['prompt'])
    
    # Analyze for task complexity
    prompt = log_entry.get('input', {}).get('prompt', '')
    if is_simple_task(prompt):
        log_entry['task_complexity'] = 'simple'
```

### Long-term Fix: Unified Detection System
Merge policy and detector logic:

```python
class UnifiedDetector:
    def analyze_logs(self, logs):
        # Use both policy rules AND heuristic detectors
        policy_violations = self.policy_engine.evaluate(logs)
        waste_patterns = self.waste_detectors.detect(logs)
        
        # Combine and deduplicate
        return self.merge_findings(policy_violations, waste_patterns)
```

## 🧪 Test Case Verification

### Log Entry Analysis
```json
{
  "input": {"model": "gpt-4", "prompt": "What is 2+2?"},
  "usage": {"prompt_tokens": 5},
  "cost": 0.00033
}
```

**Policy Engine**: ❌ No violation (looks for non-existent `input.prompt_length`)
**Scan Detector**: ✅ Overkill detected (`gpt-4` + 5 tokens + simple math = overkill)

### Why Scan Works Better
1. **Data-driven**: Uses actual log structure
2. **Inferential**: Derives patterns from available data
3. **Cost-aware**: Calculates actual waste based on pricing
4. **Context-aware**: Analyzes prompt content and complexity

### Why Policy Fails
1. **Metadata-dependent**: Expects fields that don't exist
2. **Rigid**: Can't adapt to actual log structure
3. **Assumptions**: Assumes enriched data with derived fields

## 📈 Impact Assessment

### Production Impact
- **Users see**: "No policy violations" but massive waste detected
- **Trust issue**: Contradictory results from same tool
- **Missing value**: Policy templates don't provide value in current state

### Cost Impact  
- **Missed savings**: $1,419.77 in waste undetected by policies
- **False confidence**: Users think they're compliant when they're not
- **Tool reliability**: Questions about accuracy and usefulness

## 🎯 Recommended Action Plan

### Phase 1: Quick Fix (1-2 days)
1. Update policy templates to use actual log fields
2. Add field derivation to policy engine  
3. Test with retry-test.jsonl to ensure violations are detected

### Phase 2: Integration (1 week)
1. Merge policy and detector findings in scan command
2. Show unified results in reports
3. Add policy violation details to waste analysis

### Phase 3: Architecture (2-3 weeks)
1. Design unified detection framework
2. Consolidate duplicate logic between systems
3. Create single source of truth for violation detection

## 🧾 Verification Steps

To verify fixes work:
```bash
# Should find violations after fix
crashlens policy-check examples-logs/retry-test.jsonl --policy-template model-overkill-detection

# Should show similar issues to scan command
crashlens policy-check examples-logs/retry-test.jsonl --policy-template all --fail-on-violations
```

Expected results after fix:
- Policy-check should find ~53k violations similar to scan
- Both commands should identify the same expensive patterns
- No contradictory "0 violations" vs "$1,419 wasted" messages
