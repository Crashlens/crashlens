# CrashLens Simulate Command

**Generate realistic test data for policy development and testing**

---

## Table of Contents

1. [Overview](#overview)
2. [Basic Usage](#basic-usage)
3. [Scenario Types](#scenario-types)
4. [Customization Options](#customization-options)
5. [Deterministic Generation](#deterministic-generation)
6. [Integration with Guard](#integration-with-guard)
7. [Complete Examples](#complete-examples)
8. [Best Practices](#best-practices)

---

## Overview

The `simulate` command generates **realistic Langfuse-style JSONL test data** for policy testing, development, and demonstrations.

**Key Features**:
✅ **6 Built-in Scenarios** - Normal, retry-loop, model-overkill, slow, mixed-errors, fallback-storm  
✅ **Customizable Volume** - Generate 10 to 100,000+ traces  
✅ **Realistic Patterns** - Based on production LLM usage  
✅ **Deterministic Output** - Reproducible with seed parameter  
✅ **Instant Testing** - `--open` flag runs guard immediately  
✅ **Cost Calculation** - Includes token counts and pricing  
✅ **Multiple Models** - GPT-4, GPT-3.5, Claude, custom models  

**Syntax**:
```bash
crashlens simulate --output FILE [OPTIONS]
```

**Quick Start**:
```bash
# Generate 100 traces with normal patterns
crashlens simulate --output test.jsonl

# Generate retry loop scenario
crashlens simulate --output retry-test.jsonl --scenario retry-loop --count 500

# Generate and test immediately
crashlens simulate --output test.jsonl --scenario mixed-errors --open
```

---

## Basic Usage

### Generate Default Data

```bash
# 100 traces with normal scenario
crashlens simulate --output test.jsonl
```

**Output**: `test.jsonl` with 100 realistic traces

### Specify Trace Count

```bash
# Generate specific number of traces
crashlens simulate --output test.jsonl --count 500

# Large dataset
crashlens simulate --output large.jsonl --count 10000

# Small dataset for quick testing
crashlens simulate --output small.jsonl --count 10
```

### Overwrite Existing Files

```bash
# Force overwrite without prompting
crashlens simulate --output test.jsonl --force

# Useful in scripts/automation
crashlens simulate --output test.jsonl --count 1000 --force
```

### Basic Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` | Path | Required | Path to write JSONL file |
| `--count` | Int | 100 | Number of traces to generate |
| `--force` | Flag | False | Overwrite without prompting |

---

## Scenario Types

### 1. Normal (Default)

**Realistic production-like traces**:

```bash
crashlens simulate --output normal.jsonl --scenario normal --count 500
```

**Characteristics**:
- ✅ Mix of successful and failed requests
- ✅ Various models (GPT-4, GPT-3.5, Claude)
- ✅ Realistic token distributions
- ✅ Occasional errors (~10%)
- ✅ Varied response times

**Use cases**:
- Baseline testing
- General policy validation
- Performance benchmarking

### 2. Retry Loop

**Excessive retry patterns**:

```bash
crashlens simulate --output retry-test.jsonl --scenario retry-loop --count 200
```

**Characteristics**:
- ⚠️ Multiple retries on identical prompts (3-7 retries)
- ⚠️ Exponential backoff failures
- ⚠️ High token waste from duplicates
- ⚠️ Same errors repeated
- ⚠️ Timestamp clustering

**Use cases**:
- Test retry-loop-prevention policies
- Validate exponential backoff detection
- Cost waste identification

**Example output**:
```json
{"traceId": "retry-1", "input": {"prompt": "summarize document"}, "metadata": {"retry_count": 1}, "usage": {"prompt_tokens": 500}}
{"traceId": "retry-1", "input": {"prompt": "summarize document"}, "metadata": {"retry_count": 2}, "usage": {"prompt_tokens": 500}}
{"traceId": "retry-1", "input": {"prompt": "summarize document"}, "metadata": {"retry_count": 3}, "usage": {"prompt_tokens": 500}}
```

### 3. Model Overkill

**Expensive models on simple tasks**:

```bash
crashlens simulate --output overkill.jsonl --scenario model-overkill --count 300
```

**Characteristics**:
- 💸 GPT-4 for simple tasks (<20 completion tokens)
- 💸 Expensive models for trivial queries
- 💸 Cost inefficiencies
- 💸 Token mismatches (high input, low output)

**Use cases**:
- Test model-overkill-detection policies
- Cost optimization validation
- Model selection analysis

**Example output**:
```json
{"traceId": "overkill-1", "input": {"model": "gpt-4", "prompt": "yes or no?"}, "usage": {"prompt_tokens": 50, "completion_tokens": 2}, "cost": 0.003}
```

### 4. Slow

**Performance issues and timeouts**:

```bash
crashlens simulate --output slow.jsonl --scenario slow --count 250
```

**Characteristics**:
- 🐌 Response times >5 seconds
- 🐌 Timeout errors
- 🐌 Performance degradation patterns
- 🐌 High latency variability

**Use cases**:
- Test latency policies
- Timeout detection
- Performance regression alerts

### 5. Mixed Errors

**Variety of error patterns**:

```bash
crashlens simulate --output errors.jsonl --scenario mixed-errors --count 400
```

**Characteristics**:
- ❌ Rate limit errors (429)
- ❌ Authentication failures (401)
- ❌ Server errors (500, 503)
- ❌ Invalid requests (400)
- ❌ Quota exceeded errors

**Use cases**:
- Error handling policy testing
- Comprehensive policy validation
- Edge case coverage

### 6. Fallback Storm

**Cascading fallback failures**:

```bash
crashlens simulate --output fallback.jsonl --scenario fallback-storm --count 200
```

**Characteristics**:
- 🌪️ Multiple fallback attempts (GPT-4 → GPT-3.5 → Claude)
- 🌪️ Fallback chain exhaustion
- 🌪️ All models failing in sequence
- 🌪️ High cumulative costs

**Use cases**:
- Test fallback-chain policies
- Cascade failure detection
- Cost accumulation tracking

### Scenario Comparison

| Scenario | Primary Pattern | Error Rate | Cost Impact | Use Case |
|----------|----------------|------------|-------------|----------|
| `normal` | Balanced mix | 10% | Low | Baseline testing |
| `retry-loop` | Duplicate retries | 30% | High | Retry detection |
| `model-overkill` | Expensive models | 5% | Very High | Cost optimization |
| `slow` | High latency | 20% | Medium | Performance alerts |
| `mixed-errors` | Various errors | 50% | Low | Error handling |
| `fallback-storm` | Cascading failures | 80% | Very High | Fallback policies |

---

## Customization Options

### Custom Models

**Specify model distribution**:

```bash
# Default models: gpt-4, gpt-3.5-turbo, claude-3-opus
crashlens simulate --output test.jsonl

# Custom models
crashlens simulate --output test.jsonl \
  --models "gpt-4,gpt-3.5-turbo,claude-3-opus,claude-3-sonnet"

# Single model only
crashlens simulate --output gpt4-only.jsonl --models "gpt-4"

# Custom model names
crashlens simulate --output custom.jsonl \
  --models "my-custom-model,another-model"
```

### Error Rate Control

**Adjust error probability**:

```bash
# High error rate (50%)
crashlens simulate --output high-errors.jsonl --error-rate 0.5

# Low error rate (5%)
crashlens simulate --output low-errors.jsonl --error-rate 0.05

# No errors
crashlens simulate --output no-errors.jsonl --error-rate 0.0

# All errors (testing error handling)
crashlens simulate --output all-errors.jsonl --error-rate 1.0
```

**Valid range**: 0.0 (0%) to 1.0 (100%)

### Customization Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--scenario` | Choice | `normal` | Scenario type |
| `--models` | String | Common models | Comma-separated model list |
| `--error-rate` | Float | 0.2 | Error probability (0-1) |

---

## Deterministic Generation

### Reproducible Output

**Use seed for identical results**:

```bash
# Generate with seed
crashlens simulate --output test1.jsonl --seed 42

# Same seed = identical output
crashlens simulate --output test2.jsonl --seed 42

# Verify
diff test1.jsonl test2.jsonl  # No differences
```

### Use Cases for Seeds

1. **Test consistency**: Ensure tests pass with same data
2. **Debugging**: Reproduce exact scenarios
3. **Benchmarking**: Compare performance on identical datasets
4. **Documentation**: Shareable, reproducible examples

### Seed Examples

```bash
# Reproducible retry loop
crashlens simulate --output retry.jsonl \
  --scenario retry-loop \
  --count 100 \
  --seed 123

# Reproducible baseline
crashlens simulate --output baseline.jsonl \
  --scenario normal \
  --count 1000 \
  --seed 456
```

### Deterministic Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--seed` | Int | None (random) | Random seed for reproducibility |

---

## Integration with Guard

### Instant Testing

**Generate and test in one command**:

```bash
# Simulate and immediately run guard
crashlens simulate --output test.jsonl --scenario retry-loop --open
```

**What happens**:
1. Generates test data (`test.jsonl`)
2. Automatically runs `crashlens guard test.jsonl`
3. Shows policy violations immediately

### Policy Development Workflow

**Iterative policy testing**:

```bash
# 1. Generate test data
crashlens simulate --output test.jsonl --scenario retry-loop --count 200

# 2. Create policy
cat > rules.yaml <<EOF
rules:
  - id: TEST_RETRY
    description: "Test retry detection"
    if:
      metadata.retry_count:
        '>': 3
    action: fail_ci
    severity: fatal
EOF

# 3. Test policy
crashlens guard test.jsonl --rules rules.yaml --dry-run

# 4. Refine policy and re-test
# ... edit rules.yaml ...
crashlens guard test.jsonl --rules rules.yaml
```

### CI/CD Testing

**Use simulate for CI pipeline validation**:

```yaml
# .github/workflows/test-policies.yml
name: Test Policies

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install CrashLens
        run: pip install crashlens
      
      - name: Generate test data
        run: |
          crashlens simulate --output test-retry.jsonl \
            --scenario retry-loop \
            --count 500 \
            --seed 42
      
      - name: Test policies
        run: |
          crashlens guard test-retry.jsonl \
            --rules .crashlens/rules.yaml \
            --fail-on-violations
```

### Integration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--open` | Flag | False | Run guard immediately after generation |

---

## Complete Examples

### Example 1: Quick Test Dataset

```bash
# Small dataset for rapid testing
crashlens simulate --output quick-test.jsonl --count 50 --force
crashlens guard quick-test.jsonl --dry-run
```

### Example 2: Retry Loop Testing

```bash
# Generate retry patterns
crashlens simulate --output retry.jsonl \
  --scenario retry-loop \
  --count 300 \
  --seed 123 \
  --force

# Test with retry policy
crashlens guard retry.jsonl \
  --rules policies/retry-loop-detector.yaml \
  --fail-on-violations
```

### Example 3: Model Overkill Detection

```bash
# Generate overkill patterns
crashlens simulate --output overkill.jsonl \
  --scenario model-overkill \
  --count 400 \
  --models "gpt-4,gpt-3.5-turbo" \
  --error-rate 0.1

# Detect overkill
crashlens guard overkill.jsonl \
  --rules policies/model-overkill-detection.yaml
```

### Example 4: High-Volume Production Simulation

```bash
# Large realistic dataset
crashlens simulate --output production-sim.jsonl \
  --scenario normal \
  --count 10000 \
  --models "gpt-4,gpt-3.5-turbo,claude-3-opus,claude-3-sonnet" \
  --error-rate 0.15 \
  --seed 789

# Analyze
crashlens scan production-sim.jsonl --format json --detailed
```

### Example 5: Error Handling Testing

```bash
# High error rate
crashlens simulate --output errors.jsonl \
  --scenario mixed-errors \
  --count 200 \
  --error-rate 0.7 \
  --open
```

### Example 6: Fallback Chain Testing

```bash
# Fallback storm with immediate testing
crashlens simulate --output fallback.jsonl \
  --scenario fallback-storm \
  --count 150 \
  --seed 456 \
  --open
```

### Example 7: Policy Development Cycle

```bash
# Generate multiple scenarios
crashlens simulate --output normal.jsonl --scenario normal --count 500
crashlens simulate --output retry.jsonl --scenario retry-loop --count 300
crashlens simulate --output overkill.jsonl --scenario model-overkill --count 200

# Test all scenarios
for file in *.jsonl; do
  echo "Testing: $file"
  crashlens guard "$file" --rules .crashlens/rules.yaml --dry-run
done
```

### Example 8: Reproducible Benchmarking

```bash
# Baseline benchmark (week 1)
crashlens simulate --output baseline.jsonl \
  --scenario normal \
  --count 1000 \
  --seed 42

crashlens scan baseline.jsonl --format json > baseline-results.json

# Comparison benchmark (week 2)
# Same seed = identical data for fair comparison
crashlens simulate --output baseline.jsonl \
  --scenario normal \
  --count 1000 \
  --seed 42

crashlens scan baseline.jsonl --format json > week2-results.json

# Compare results
diff baseline-results.json week2-results.json
```

---

## Best Practices

### 1. Use Seeds for Reproducibility

```bash
# Always use seeds in CI/CD
crashlens simulate --output test.jsonl --seed 42

# Document seed values
echo "Test data generated with seed: 42" > test-readme.txt
```

### 2. Match Scenarios to Policies

**Test specific patterns**:

```bash
# Testing retry policy? Use retry-loop scenario
crashlens simulate --output test.jsonl --scenario retry-loop

# Testing cost policy? Use model-overkill scenario
crashlens simulate --output test.jsonl --scenario model-overkill
```

### 3. Start Small, Scale Up

```bash
# Quick iteration: small datasets
crashlens simulate --output test.jsonl --count 50

# Once policies work: larger datasets
crashlens simulate --output test.jsonl --count 1000
```

### 4. Use --open for Rapid Iteration

```bash
# Edit policy, test immediately
crashlens simulate --output test.jsonl --scenario retry-loop --open --force

# Repeat until satisfied
```

### 5. Version Control Test Data Seeds

```yaml
# .github/workflows/test.yml
env:
  TEST_SEED: 42
  TEST_COUNT: 500

- name: Generate test data
  run: |
    crashlens simulate --output test.jsonl \
      --seed ${{ env.TEST_SEED }} \
      --count ${{ env.TEST_COUNT }}
```

### 6. Organize Test Data

```bash
# Separate by scenario
mkdir -p test-data
crashlens simulate --output test-data/normal.jsonl --scenario normal
crashlens simulate --output test-data/retry.jsonl --scenario retry-loop
crashlens simulate --output test-data/overkill.jsonl --scenario model-overkill

# Version in git
git add test-data/*.jsonl
git commit -m "Add test datasets"
```

### 7. Document Generation Parameters

```bash
# Create metadata file
cat > test-data/README.md <<EOF
# Test Data

Generated: $(date)

- normal.jsonl: 500 traces, seed 42, scenario normal
- retry.jsonl: 300 traces, seed 123, scenario retry-loop
- overkill.jsonl: 200 traces, seed 456, scenario model-overkill

Regenerate with:
  crashlens simulate --output normal.jsonl --count 500 --seed 42
EOF
```

---

## Performance Considerations

### Large Datasets

**Optimize for high volume**:

```bash
# Generate 100k traces (fast, <10 seconds)
crashlens simulate --output large.jsonl --count 100000

# Memory efficient (streams to disk)
crashlens simulate --output huge.jsonl --count 1000000
```

### Parallel Generation

**Generate multiple datasets in parallel**:

```bash
# Bash parallel
for scenario in normal retry-loop model-overkill; do
  crashlens simulate --output "test-${scenario}.jsonl" \
    --scenario "$scenario" \
    --count 1000 &
done
wait

# PowerShell parallel
$scenarios = @('normal', 'retry-loop', 'model-overkill')
$scenarios | ForEach-Object -Parallel {
  crashlens simulate --output "test-$_.jsonl" `
    --scenario $_ `
    --count 1000
} -ThrottleLimit 3
```

---

## Troubleshooting

### Issue: File Already Exists

**Problem**: Error when output file exists

**Solution**:
```bash
# Use --force to overwrite
crashlens simulate --output test.jsonl --force

# Or delete first
rm test.jsonl
crashlens simulate --output test.jsonl
```

### Issue: Inconsistent Results

**Problem**: Results differ between runs

**Solution**:
```bash
# Use --seed for consistent output
crashlens simulate --output test.jsonl --seed 42
```

### Issue: Not Enough Violations

**Problem**: Generated data doesn't trigger policies

**Solution**:
```bash
# Use specific scenario
crashlens simulate --output test.jsonl --scenario retry-loop

# Increase error rate
crashlens simulate --output test.jsonl --error-rate 0.8
```

### Issue: Too Many Violations

**Problem**: All traces violate policies

**Solution**:
```bash
# Use normal scenario
crashlens simulate --output test.jsonl --scenario normal

# Lower error rate
crashlens simulate --output test.jsonl --error-rate 0.1
```

---

## Command Reference

### All Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` | Path | Required | Path to write JSONL file |
| `--count` | Int | 100 | Number of traces to generate |
| `--scenario` | Choice | `normal` | Scenario: `normal`, `retry-loop`, `model-overkill`, `slow`, `mixed-errors`, `fallback-storm` |
| `--models` | String | Common models | Comma-separated model names |
| `--error-rate` | Float | 0.2 | Error probability (0.0-1.0) |
| `--seed` | Int | None | Random seed for reproducibility |
| `--force` | Flag | False | Overwrite existing file |
| `--open` | Flag | False | Run guard after generation |

### Scenario Types

| Scenario | Pattern | Best For |
|----------|---------|----------|
| `normal` | Balanced mix | Baseline testing |
| `retry-loop` | Excessive retries | Retry policies |
| `model-overkill` | Expensive models | Cost policies |
| `slow` | High latency | Performance policies |
| `mixed-errors` | Various errors | Error handling |
| `fallback-storm` | Cascading failures | Fallback policies |

---

## See Also

- **[Guard Command](./guard-command.md)**: Policy enforcement
- **[Scan Command](./scan-command.md)**: Analysis of generated data
- **[Init Command](./init-command.md)**: Setup policies
- **[CLI Reference](../CLI_COMMAND_REFERENCE.md)**: All commands

---

**Quick Start**: `crashlens simulate --output test.jsonl --scenario retry-loop --count 500 --open`
