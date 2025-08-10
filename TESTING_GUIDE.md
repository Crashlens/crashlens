# 🧪 CRASHLENS TESTING GUIDE - COMPREHENSIVE VERIFICATION

## 🎯 **HOW TO TEST THAT CRASHLENS IS WORKING CORRECTLY**

This guide shows you exactly how to verify that Crashlens has all features implemented and working properly.

## 📋 **QUICK HEALTH CHECK (5 minutes)**

### 1. **Basic CLI Installation Test**
```bash
# Check if CLI is installed and shows correct version
poetry run crashlens --version
# Should show: crashlens.cmd, version 2.5.1

# Check all available commands
poetry run crashlens --help
# Should show: policy-check, list-policy-templates, init, simulate
```

### 2. **Core Command Tests**
```bash
# Test policy templates listing
poetry run crashlens list-policy-templates
# Should show 10+ policy templates with descriptions

# Test simulate command exists
poetry run crashlens simulate --help
# Should show all simulate options and scenarios
```

## 🔍 **COMPREHENSIVE FEATURE TESTING (15 minutes)**

### 3. **Test Simulate Command - All Scenarios**

#### **Normal Scenario Test**
```bash
poetry run crashlens simulate --output test-normal.jsonl --count 10 --scenario normal --seed 42
cat test-normal.jsonl | head -n 3
# Should show: Valid JSONL with realistic traces, mixed success/error
```

#### **Retry-Loop Scenario Test**
```bash
poetry run crashlens simulate --output test-retry.jsonl --count 15 --scenario retry-loop --seed 42
grep "retry_" test-retry.jsonl | head -n 5
# Should show: Same traceId appearing multiple times with same prompts
```

#### **Model-Overkill Scenario Test**
```bash
poetry run crashlens simulate --output test-overkill.jsonl --count 10 --scenario model-overkill --seed 42
grep '"prompt_tokens": [0-9],' test-overkill.jsonl
# Should show: Very low token counts (5-15) with expensive models (gpt-4)
```

#### **Slow Scenario Test**
```bash
poetry run crashlens simulate --output test-slow.jsonl --count 5 --scenario slow --seed 42
grep "duration_ms" test-slow.jsonl
# Should show: Duration values > 5000ms for slow response testing
```

#### **Mixed-Errors Scenario Test**
```bash
poetry run crashlens simulate --output test-mixed.jsonl --count 10 --scenario mixed-errors --seed 42
grep '"error_type"' test-mixed.jsonl
# Should show: Various error types (rate_limit, timeout, network, etc.)
```

### 4. **Test Advanced Simulate Features**

#### **Custom Models Test**
```bash
poetry run crashlens simulate --output test-custom.jsonl --count 5 --models "gpt-4o,claude-3" --seed 42
grep '"model"' test-custom.jsonl
# Should show: Only gpt-4o and claude-3 models used
```

#### **Error Rate Test**
```bash
poetry run crashlens simulate --output test-errors.jsonl --count 20 --error-rate 0.8 --seed 42
grep '"status": "error\|timeout"' test-errors.jsonl | wc -l
# Should show: High number of error traces (around 16 out of 20)
```

#### **Deterministic Output Test**
```bash
poetry run crashlens simulate --output test1.jsonl --count 5 --seed 12345
poetry run crashlens simulate --output test2.jsonl --count 5 --seed 12345
# Compare structure (not timestamps)
grep '"model"' test1.jsonl > models1.txt
grep '"model"' test2.jsonl > models2.txt
diff models1.txt models2.txt
# Should show: No differences (same models chosen)
```

#### **Force Overwrite Test**
```bash
echo "existing content" > existing-file.jsonl
poetry run crashlens simulate --output existing-file.jsonl --count 3 --force
# Should overwrite without prompting
cat existing-file.jsonl | head -n 1
# Should show: Valid JSON trace, not "existing content"
```

### 5. **Test Init Command Features**

#### **Interactive Init Test**
```bash
# Test interactive mode (use Ctrl+C to cancel)
poetry run crashlens init
# Should show: Interactive prompts for templates, severity, etc.
```

#### **Non-Interactive Init Test**
```bash
export CRASHLENS_TEMPLATES="retry-loop-prevention,model-overkill-detection"
export CRASHLENS_SEVERITY="high"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
export CRASHLENS_LOGS_SOURCE="local"

poetry run crashlens init --non-interactive
# Should create: .crashlens/config.yaml with specified settings
cat .crashlens/config.yaml
# Should show: retry-loop-prevention,model-overkill-detection templates
```

#### **Config Validation Test**
```bash
# Test schema validation by creating invalid config
mkdir -p .crashlens
echo "invalid: yaml content
missing: required fields" > .crashlens/config.yaml

poetry run crashlens init --non-interactive
# Should show: Validation errors for invalid config
```

#### **Dry-Run Workflow Test**
```bash
poetry run crashlens init --dry-run-workflow --non-interactive
# Should show: GitHub Actions workflow YAML printed to stdout
# Should NOT create: Any files on disk
```

### 6. **Test Policy Check Integration**

#### **Policy Templates Test**
```bash
poetry run crashlens list-policy-templates
# Should show: 10+ templates with categories and descriptions
# Look for: retry-loop-prevention, model-overkill-detection, etc.
```

#### **Policy Check on Generated Data**
```bash
# Generate test data and run policy check
poetry run crashlens simulate --output policy-test.jsonl --count 20 --scenario retry-loop
poetry run crashlens policy-check policy-test.jsonl --policy-template retry-loop-prevention
# Should complete without errors (may show no violations due to detector implementation)
```

### 7. **Test File Operations & Error Handling**

#### **Directory Creation Test**
```bash
poetry run crashlens simulate --output deep/nested/path/test.jsonl --count 3 --force
ls -la deep/nested/path/
# Should show: test.jsonl created with parent directories
```

#### **Permission Handling Test**
```bash
# Create read-only directory (Unix/Mac)
mkdir readonly-dir 2>/dev/null || true
chmod 444 readonly-dir 2>/dev/null || true
poetry run crashlens simulate --output readonly-dir/test.jsonl --count 3 2>&1 | grep -i "permission\|error"
# Should show: Graceful error handling with clear message
```

#### **Invalid Parameter Tests**
```bash
# Test zero count validation
poetry run crashlens simulate --output test.jsonl --count 0
# Should show: "count must be greater than 0"

# Test invalid error rate
poetry run crashlens simulate --output test.jsonl --error-rate 1.5
# Should show: "error-rate must be between 0.0 and 1.0"

# Test invalid scenario
poetry run crashlens simulate --output test.jsonl --scenario invalid-scenario
# Should show: Choice validation error with valid options
```

## ✅ **VERIFICATION CHECKLIST**

### **Core Functionality** ✅
- [ ] CLI installs and shows correct version
- [ ] All 4 commands available (policy-check, list-policy-templates, init, simulate)
- [ ] Policy templates list displays correctly
- [ ] Basic simulate command generates valid JSONL

### **Simulate Command Features** ✅
- [ ] All 5 scenarios work (normal, retry-loop, model-overkill, slow, mixed-errors)
- [ ] Custom models parameter works
- [ ] Error rate parameter affects output
- [ ] Seed produces deterministic results
- [ ] Force overwrite works
- [ ] File operations create directories as needed

### **Scenario Validation** ✅
- [ ] Retry-loop: Same traceId with identical prompts
- [ ] Model-overkill: Low token counts with expensive models
- [ ] Slow: Duration values > 5000ms
- [ ] Mixed-errors: Various error types with metadata
- [ ] Normal: Balanced success/error mix

### **Init Command Features** ✅
- [ ] Interactive mode prompts correctly
- [ ] Non-interactive mode with environment variables
- [ ] Config validation with schema checking
- [ ] Dry-run workflow prints YAML without file creation
- [ ] Version compatibility warnings

### **Error Handling** ✅
- [ ] Parameter validation with clear messages
- [ ] Graceful handling of missing dependencies
- [ ] File permission errors handled properly
- [ ] Invalid configurations detected

### **Data Quality** ✅
- [ ] Generated JSONL is valid JSON format
- [ ] Traces follow Langfuse schema structure
- [ ] Cost calculations are reasonable
- [ ] Timestamps are properly formatted
- [ ] Token counts are realistic

## 🚀 **AUTOMATED TESTING**

### **Run Unit Test Suite**
```bash
# Run all tests
poetry run pytest tests/test_simulate.py -v
# Should show: 24 tests passing

# Run with coverage if available
poetry run pytest tests/test_simulate.py --cov=crashlens --cov-report=term-missing
```

### **Integration Test Script**
```bash
# Create a comprehensive test script
cat > test_all.sh << 'EOF'
#!/bin/bash
echo "🧪 Running Crashlens Integration Tests..."

# Test all scenarios
for scenario in normal retry-loop model-overkill slow mixed-errors; do
    echo "Testing scenario: $scenario"
    poetry run crashlens simulate --output "test_$scenario.jsonl" --count 5 --scenario "$scenario" --seed 42 --force
    if [ $? -eq 0 ]; then
        echo "✅ $scenario scenario: PASS"
    else
        echo "❌ $scenario scenario: FAIL"
    fi
done

# Test init command
echo "Testing init command..."
export CRASHLENS_TEMPLATES="retry-loop-prevention"
export CRASHLENS_SEVERITY="high"
poetry run crashlens init --non-interactive --force
if [ $? -eq 0 ]; then
    echo "✅ Init command: PASS"
else
    echo "❌ Init command: FAIL"
fi

echo "🎉 Integration tests complete!"
EOF

chmod +x test_all.sh
./test_all.sh
```

## 📊 **SUCCESS INDICATORS**

### **You'll know Crashlens is working correctly when:**

1. **✅ All Commands Respond**: Every command shows help and executes without crashes
2. **✅ Valid Output Generated**: JSONL files contain properly formatted trace data
3. **✅ Scenarios Work Distinctly**: Each scenario produces appropriate patterns
4. **✅ Parameters Validated**: Invalid inputs show clear error messages
5. **✅ Files Created Successfully**: Output files are created in correct locations
6. **✅ Deterministic Results**: Same seed produces consistent outputs
7. **✅ Error Handling Graceful**: Edge cases don't crash the application
8. **✅ Integration Works**: Init command creates proper configs
9. **✅ Performance Adequate**: Generates traces quickly without memory issues
10. **✅ Tests Pass**: Unit test suite runs without failures

## 🎯 **FINAL VERIFICATION COMMANDS**

```bash
# One-line health check
poetry run crashlens --version && poetry run crashlens simulate --output health-check.jsonl --count 5 --seed 42 && echo "✅ Crashlens is working correctly!"

# Quick feature test
poetry run crashlens list-policy-templates | grep -c "Name:" && echo "✅ Policy templates loaded"

# Data quality check
poetry run crashlens simulate --output quality-check.jsonl --count 10 --seed 42 && python -c "
import json
with open('quality-check.jsonl', 'r') as f:
    traces = [json.loads(line) for line in f]
    print(f'✅ Generated {len(traces)} valid JSON traces')
    print(f'✅ Required fields present: {all(\"traceId\" in t and \"usage\" in t for t in traces)}')
    print(f'✅ Cost calculations: {all(\"cost\" in t and t[\"cost\"] >= 0 for t in traces)}')
"
```

**When all these tests pass, you can be confident that Crashlens is fully functional and ready for production use!** 🎉
