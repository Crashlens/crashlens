# Config Precedence Guide

## 🎯 Overview

CrashLens uses a **strict precedence order** for configuration sources to ensure predictable behavior across environments. Understanding this order is critical for production deployments, CI/CD pipelines, and troubleshooting.

---

## 📊 Precedence Order

**Highest to Lowest Priority:**

```
1. CLI Flags           (--metrics-sample-rate 0.5)
2. Environment Variables (CRASHLENS_METRICS_SAMPLE_RATE=0.5)
3. YAML Config File    (metrics.yaml)
4. Hardcoded Defaults  (defined in code)
```

**Rule**: The highest-priority source that provides a value wins. If a value is not set at a higher level, the system falls back to the next level.

---

##  Config Sources Explained

### 1. CLI Flags (Highest Priority)

CLI flags override ALL other sources. Use for:
- **One-off testing**: `crashlens scan logs.jsonl --metrics-sample-rate 0.01`
- **Emergency overrides**: Disable metrics immediately without changing config
- **Ad-hoc adjustments**: Test different sampling rates without modifying files

**Example**:
```bash
# Override YAML and env vars with CLI flag
crashlens scan logs.jsonl \
  --push-metrics \
  --metrics-sample-rate 0.1 \
  --metrics-max-rules 1000
```

**Common CLI Flags**:
| Flag | Env Var | Default | Description |
|------|---------|---------|-------------|
| `--push-metrics` | `CRASHLENS_PUSH_METRICS` | `false` | Enable Pushgateway push mode |
| `--metrics-http` | `CRASHLENS_METRICS_HTTP` | `false` | Enable HTTP server mode |
| `--metrics-sample-rate` | `CRASHLENS_METRICS_SAMPLE_RATE` | `1.0` | Global sampling rate (0.0-1.0) |
| `--metrics-max-rules` | `CRASHLENS_METRICS_MAX_RULES` | `500` | Cardinality cap (max unique rules) |
| `--pushgateway-url` | `CRASHLENS_PUSHGATEWAY_URL` | `http://localhost:9091` | Pushgateway endpoint |
| `--metrics-job` | `CRASHLENS_METRICS_JOB` | `crashlens_scan` | Prometheus job name |
| `--metrics-port` | `CRASHLENS_METRICS_PORT` | `9090` | HTTP server port |
| `--metrics-addr` | `CRASHLENS_METRICS_ADDR` | `127.0.0.1` | HTTP server bind address |
| `--metrics-auth-user` | `CRASHLENS_METRICS_AUTH_USER` | `None` | HTTP Basic Auth username |
| `--metrics-auth-pass` | `CRASHLENS_METRICS_AUTH_PASS` | `None` | HTTP Basic Auth password |

---

### 2. Environment Variables

Environment variables override YAML config and defaults. Use for:
- **CI/CD pipelines**: Set via GitHub Actions secrets, GitLab CI vars
- **Container deployments**: Configure via Docker/Kubernetes env vars
- **Secrets management**: Inject credentials without hardcoding

**Example**:
```bash
# Set environment variables
export CRASHLENS_PUSH_METRICS=true
export CRASHLENS_METRICS_SAMPLE_RATE=0.1
export CRASHLENS_PUSHGATEWAY_URL=http://prometheus:9091

# Run without CLI flags (uses env vars)
crashlens scan logs.jsonl
```

**Environment Variable Naming Convention**:
- Prefix: `CRASHLENS_`
- All caps: `METRICS_SAMPLE_RATE`
- Underscores: `METRICS_MAX_RULES`

**Special Environment Variables**:
| Env Var | Purpose | Values |
|---------|---------|--------|
| `CRASHLENS_DISABLE_METRICS` | **Kill switch** - disables metrics entirely | `true` / `false` |
| `CRASHLENS_ALLOW_HTTP_METRICS` | **Security gate** - required for HTTP mode | `true` / `false` |
| `CRASHLENS_METRICS_CONFIG` | **Config file path** - override search locations | `/path/to/config.yaml` |

---

### 3. YAML Config File

YAML config provides persistent, version-controlled settings. Use for:
- **Team defaults**: Commit to repository for consistency
- **Environment-specific config**: Dev vs. staging vs. production
- **Complex per-rule sampling**: Define many rule overrides

**Config File Search Locations** (checked in order):
1. `--metrics-config <path>` (CLI flag)
2. `$CRASHLENS_METRICS_CONFIG` (env var)
3. `./.crashlens/metrics.yaml` (project directory)
4. `~/.crashlens/metrics.yaml` (user home)
5. `/etc/crashlens/metrics.yaml` (system-wide, Unix-like)

**Example Config** (`metrics.yaml`):
```yaml
metrics:
  enabled: true
  
  sampling:
    rate: 0.1  # 10% global sampling
    per_rule:
      # High-frequency rules: lower sampling
      rate_limit_violation: 0.01  # 1%
      prompt_too_long: 0.01       # 1%
      
      # Critical violations: full sampling
      security_breach: 1.0        # 100%
      cost_overrun: 1.0           # 100%
  
  pushgateway:
    url: http://prometheus:9091
    job: crashlens-production
    timeout: 10
  
  http_server:
    enabled: false
    port: 9090
    addr: 127.0.0.1
```

---

### 4. Hardcoded Defaults (Lowest Priority)

Built-in defaults ensure sane fallback behavior. Use when:
- No configuration provided at all
- Quick local testing
- Bootstrapping new environments

**Default Values**:
```python
metrics.enabled = False
sampling.rate = 1.0  # 100% sampling
sampling.per_rule = {}  # No overrides
pushgateway.url = "http://localhost:9091"
pushgateway.job = "crashlens_scan"
http_server.port = 9090
http_server.addr = "127.0.0.1"
```

---

## 🧪 Precedence Examples

### Example 1: CLI Overrides Everything

**Setup**:
```bash
# YAML config
cat > metrics.yaml <<EOF
metrics:
  sampling:
    rate: 0.5
EOF

# Environment variable
export CRASHLENS_METRICS_SAMPLE_RATE=0.3

# CLI flag
crashlens scan logs.jsonl --metrics-sample-rate 0.9
```

**Result**: Sampling rate = **0.9** (CLI wins)

---

### Example 2: Env Overrides YAML

**Setup**:
```bash
# YAML config
cat > metrics.yaml <<EOF
metrics:
  sampling:
    rate: 0.5
EOF

# Environment variable
export CRASHLENS_METRICS_SAMPLE_RATE=0.3

# No CLI flag
crashlens scan logs.jsonl
```

**Result**: Sampling rate = **0.3** (ENV wins)

---

### Example 3: YAML Overrides Defaults

**Setup**:
```bash
# YAML config
cat > metrics.yaml <<EOF
metrics:
  sampling:
    rate: 0.5
EOF

# No CLI flag, no env var
crashlens scan logs.jsonl
```

**Result**: Sampling rate = **0.5** (YAML wins)

---

### Example 4: Defaults Only

**Setup**:
```bash
# No YAML, no CLI, no env vars
crashlens scan logs.jsonl
```

**Result**: Sampling rate = **1.0** (default)

---

### Example 5: Kill Switch Overrides Everything

**Setup**:
```bash
# YAML config
cat > metrics.yaml <<EOF
metrics:
  enabled: true
  sampling:
    rate: 1.0
EOF

# Kill switch
export CRASHLENS_DISABLE_METRICS=true

# CLI flag
crashlens scan logs.jsonl --push-metrics
```

**Result**: Metrics **DISABLED** (kill switch wins)

**Critical**: The kill switch (`CRASHLENS_DISABLE_METRICS=true`) takes precedence over ALL other config, including CLI flags.

---

## 🚨 Error Handling & Validation

### Schema Validation

All config values are validated using **Pydantic schemas**:

| Field | Type | Range | Validation |
|-------|------|-------|------------|
| `sampling.rate` | `float` | `0.0-1.0` | Must be between 0 and 1 |
| `per_rule.*` | `float` | `0.0-1.0` | Each rule rate validated |
| `http_server.port` | `int` | `1024-65535` | Unprivileged ports only |
| `pushgateway.timeout` | `int` | `1-60` | Reasonable timeout range |
| `enabled` | `bool` | `true/false` | Must be boolean |

### Error Scenarios

#### 1. Invalid YAML Syntax

**Input**:
```yaml
metrics:
  enabled: true
  sampling:
    rate: [invalid
    indentation error
```

**Behavior**:
- ❌ Config load **FAILS**
- 📝 Error **LOGGED** to stderr: `Invalid YAML syntax at line X, column Y`
- 🔄 Fallback to **next config source** (env vars → defaults)
- 🚫 Process does **NOT crash** (graceful degradation)

**Log Output**:
```
ERROR: Invalid YAML syntax in .crashlens/metrics.yaml at line 4, column 10:
  mapping values are not allowed here
  
Hint: Check YAML indentation and syntax. Use a YAML validator like yamllint.

Falling back to environment variables and defaults...
```

---

#### 2. Type Mismatch

**Input**:
```yaml
metrics:
  sampling:
    rate: "not_a_number"
```

**Behavior**:
- ❌ Validation **FAILS**
- 📝 Error **LOGGED**: `Field 'rate' must be float, got str`
- 🔄 Fallback to **next source**

**Log Output**:
```
ERROR: Configuration validation failed in metrics.yaml:
  • sampling.rate: Input should be a valid number, got 'not_a_number'
  
Hint: Check field types. 'rate' must be a float between 0.0 and 1.0.

Falling back to environment variables and defaults...
```

---

#### 3. Out of Range Value

**Input**:
```yaml
metrics:
  sampling:
    rate: 2.5
```

**Behavior**:
- ❌ Validation **FAILS**
- 📝 Error **LOGGED**: `Rate 2.5 exceeds maximum 1.0`
- 🔄 Fallback to **next source**

**Log Output**:
```
ERROR: Configuration validation failed in metrics.yaml:
  • sampling.rate: Input should be less than or equal to 1.0
  
Hint: Sampling rate must be between 0.0 (0%) and 1.0 (100%).

Falling back to environment variables and defaults...
```

---

#### 4. Missing Required Field (None - All Fields Optional)

**Input**:
```yaml
metrics:
  enabled: true
```

**Behavior**:
- ✅ Config **VALID** (missing fields use defaults)
- 📝 Info **LOGGED**: `Using default sampling rate: 1.0`

**Log Output**:
```
INFO: Config loaded successfully from metrics.yaml
INFO: Using default sampling rate: 1.0 (not specified in config)
```

---

## 🛠️ Validation Commands

### Validate Config File

```bash
# Validate before using
crashlens validate-metrics-config metrics.yaml

# Verbose output
crashlens validate-metrics-config metrics.yaml --verbose
```

**Output (Valid)**:
```
✓ Config file is valid: metrics.yaml

Configuration summary:
  Enabled: true
  Global Sampling: 10.0%
  Per-Rule Overrides: 2 rules
    • expensive: 1.0%
    • rare: 100.0%
  Pushgateway URL: http://prometheus:9091
```

**Output (Invalid)**:
```
✗ Config file is invalid: metrics.yaml

Validation error:
  • sampling.rate: Input should be less than or equal to 1.0

Fix the errors above and try again.
```

---

### Show Effective Config

```bash
# Show final merged config (after precedence resolution)
crashlens show-metrics-config

# With custom config file
crashlens show-metrics-config --config metrics.yaml

# With environment variables
export CRASHLENS_METRICS_SAMPLE_RATE=0.1
crashlens show-metrics-config
```

**Output**:
```
Effective Metrics Configuration:
  
  Source Precedence:
    CLI Flags:        (none)
    Environment Vars: CRASHLENS_METRICS_SAMPLE_RATE=0.1
    Config File:      ./.crashlens/metrics.yaml
    Defaults:         (built-in)
  
  Final Configuration:
    Enabled: true
    Global Sampling: 10.0% (from ENV)
    Per-Rule Overrides: 2 rules (from YAML)
      • expensive: 1.0%
      • rare: 100.0%
    Pushgateway URL: http://prometheus:9091 (from YAML)
```

---

## 🐛 Troubleshooting

### Problem: "Config not found"

**Symptom**:
```
No config file found in standard locations.
Using default configuration.
```

**Solution**:
1. **Check search paths**:
   ```bash
   # Project directory
   ls -la ./.crashlens/metrics.yaml
   
   # User home
   ls -la ~/.crashlens/metrics.yaml
   ```

2. **Specify explicit path**:
   ```bash
   crashlens scan logs.jsonl --metrics-config /path/to/config.yaml
   ```

3. **Use environment variable**:
   ```bash
   export CRASHLENS_METRICS_CONFIG=/path/to/config.yaml
   crashlens scan logs.jsonl
   ```

---

### Problem: "Wrong value being used"

**Symptom**: Config value doesn't match what you set.

**Solution**:
1. **Check precedence order**:
   ```bash
   # Show effective config
   crashlens show-metrics-config
   ```

2. **Look for higher-priority sources**:
   ```bash
   # Check environment variables
   env | grep CRASHLENS
   
   # Check if kill switch is active
   echo $CRASHLENS_DISABLE_METRICS
   ```

3. **Verify CLI flags**:
   ```bash
   # Use explicit flags to override
   crashlens scan logs.jsonl --metrics-sample-rate 0.5
   ```

---

### Problem: "Config validation fails"

**Symptom**:
```
Configuration validation failed in metrics.yaml:
  • sampling.rate: Input should be less than or equal to 1.0
```

**Solution**:
1. **Check value ranges**:
   - Sampling rate: `0.0-1.0`
   - HTTP port: `1024-65535`
   - Timeout: `1-60`

2. **Check types**:
   ```yaml
   # ✗ Wrong
   sampling:
     rate: "0.5"  # String
   
   # ✓ Correct
   sampling:
     rate: 0.5    # Float
   ```

3. **Validate before using**:
   ```bash
   crashlens validate-metrics-config metrics.yaml
   ```

---

### Problem: "Metrics not working"

**Symptom**: Metrics not being collected or pushed.

**Solution**:
1. **Check kill switch**:
   ```bash
   echo $CRASHLENS_DISABLE_METRICS
   # Should be empty or "false"
   ```

2. **Check enabled flag**:
   ```yaml
   metrics:
     enabled: true  # Must be true
   ```

3. **Verify mode is enabled**:
   ```bash
   # For push mode
   crashlens scan logs.jsonl --push-metrics
   
   # For HTTP mode
   export CRASHLENS_ALLOW_HTTP_METRICS=true
   crashlens scan logs.jsonl --metrics-http
   ```

---

## 📋 Best Practices

### 1. Use YAML for Persistent Config

```bash
# Commit to repository
cat > .crashlens/metrics.yaml <<EOF
metrics:
  enabled: true
  sampling:
    rate: 0.1
    per_rule:
      expensive: 0.01
EOF

git add .crashlens/metrics.yaml
git commit -m "Add CrashLens metrics config"
```

### 2. Use Env Vars for Secrets

```bash
# Never commit credentials
export CRASHLENS_PUSHGATEWAY_URL=http://prometheus:9091
export CRASHLENS_METRICS_AUTH_USER=admin
export CRASHLENS_METRICS_AUTH_PASS=secret123

# Use secrets management
export CRASHLENS_METRICS_AUTH_PASS=$(vault read -field=password secret/crashlens)
```

### 3. Use CLI Flags for Ad-Hoc Testing

```bash
# Test with different sampling rates
crashlens scan logs.jsonl --metrics-sample-rate 0.01
crashlens scan logs.jsonl --metrics-sample-rate 0.1
crashlens scan logs.jsonl --metrics-sample-rate 1.0
```

### 4. Always Validate Config Changes

```bash
# Before committing
crashlens validate-metrics-config .crashlens/metrics.yaml

# Before deploying
crashlens show-metrics-config --config production-config.yaml
```

### 5. Document Environment-Specific Config

```bash
# development.yaml
metrics:
  enabled: true
  sampling:
    rate: 1.0  # Full sampling in dev

# production.yaml
metrics:
  enabled: true
  sampling:
    rate: 0.1  # 10% sampling in prod
```

---

## 📚 Reference

### Config File Examples

See `examples/` directory:
- `examples/metrics-minimal.yaml` - Minimal config
- `examples/metrics-per-rule.yaml` - Per-rule sampling
- `examples/metrics-full.yaml` - All options

### Related Documentation

- [OBSERVABILITY_REPORT.md](../OBSERVABILITY_REPORT.md) - Metrics system overview
- [HTTP_SERVER_SECURITY.md](./HTTP_SERVER_SECURITY.md) - HTTP mode security
- [COMMAND-REFERENCE.md](./COMMAND-REFERENCE.md) - CLI flag documentation

### Testing

- Unit tests: `tests/unit/test_config_precedence.py`
- Integration tests: `scripts/test-config-precedence.py`

---

## 🆘 Support

If you encounter config issues:
1. Run validation: `crashlens validate-metrics-config`
2. Check effective config: `crashlens show-metrics-config`
3. Review logs for error messages
4. See [GitHub Issues](https://github.com/Crashlens/crashlens/issues)

**Remember**: All config errors are **logged**, never silent. If you see unexpected behavior, check the logs!
