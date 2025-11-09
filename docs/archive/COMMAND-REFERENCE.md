# 📚 CrashLens Command Reference

Complete reference for all CrashLens CLI commands with descriptions, options, and examples.

> **⚠️ Deprecation Notice**: The `guard` command is deprecated as of v3.0.0 and will be removed in v3.1.0. It currently works as an alias for `guard` with a deprecation warning. See [MIGRATION.md](../MIGRATION.md) for migration details.

## 🎯 Core Commands

### `crashlens scan` - Token Waste Analysis
**Purpose**: Analyze logs for token waste patterns with production-grade suppression logic

```bash
crashlens scan [OPTIONS] [LOGFILE]
```

**Key Features:**
- Detects retry loops, fallback failures, model overkill, and fallback storms
- Production-grade suppression prevents duplicate alerts
- Multiple output formats (Slack, Markdown, JSON)
- Real-time cost analysis and optimization suggestions

**Input Sources:**
- File: `crashlens scan logs.jsonl`
- Demo data: `crashlens scan --demo`
- Standard input: `cat logs.jsonl | crashlens scan --stdin`
- Clipboard: `crashlens scan --paste`
- Langfuse API: `crashlens scan --from-langfuse`
- Helicone API: `crashlens scan --from-helicone`

**Output Options:**
| Option | Description | Example |
|--------|-------------|---------|
| `-f, --format` | Output format: slack, markdown, json | `--format json` |
| `--summary` | Cost summary with breakdown | `crashlens scan --summary` |
| `--summary-only` | Summary without trace IDs | `crashlens scan --summary-only` |
| `--detailed` | Generate detailed JSON reports by category | `crashlens scan --detailed` |
| `--detailed-dir` | Custom directory for detailed reports | `--detailed-dir my_reports` |

**Configuration Options:**
| Option | Description | Example |
|--------|-------------|---------|
| `-c, --config` | Custom pricing config file | `--config my-pricing.yaml` |
| `--policy-template` | Use built-in policy templates | `--policy-template all` |
| `--policy-file` | Use custom policy file | `--policy-file my-policy.yaml` |

**API Integration Options:**
| Option | Description | Default |
|--------|-------------|---------|
| `--from-langfuse` | Fetch traces from Langfuse API | N/A |
| `--from-helicone` | Fetch requests from Helicone API | N/A |
| `--hours-back` | Hours back to fetch | 24 |
| `--limit` | Max traces/requests to fetch | 1000 |

**Examples:**
```bash
# Basic analysis
crashlens scan logs.jsonl

# Cost summary with detailed reports
crashlens scan logs.jsonl --summary --detailed --format markdown

# Live API analysis
crashlens scan --from-langfuse --hours-back 48 --limit 500

# Policy enforcement
crashlens scan logs.jsonl --policy-template all --format json
```

---

### `crashlens guard` - Policy Validation
**Purpose**: Check logs against policy rules without running full waste detection

```bash
crashlens guard [OPTIONS] LOGFILE
```

**Key Features:**
- Fast policy validation for CI/CD pipelines
- Configurable severity thresholds
- Exit codes for automation (fail on violations)
- No waste pattern analysis overhead

**Options:**
| Option | Description | Example |
|--------|-------------|---------|
| `--policy-template` | Built-in policy templates | `--policy-template retry-loop-prevention` |
| `--policy-file` | Custom policy file | `--policy-file my-policy.yaml` |
| `--fail-on-violations` | Exit with error code if violations found | `--fail-on-violations` |
| `--severity-threshold` | Minimum severity: low, medium, high, critical | `--severity-threshold high` |

**Examples:**
```bash
# Check against specific policy
crashlens guard logs.jsonl --policy-template retry-loop-prevention

# Check all policies with strict enforcement
crashlens guard logs.jsonl --policy-template all --fail-on-violations

# Custom severity filtering
crashlens guard logs.jsonl --policy-file custom.yaml --severity-threshold high
```

**Exit Codes:**
- `0`: No violations or violations below threshold
- `1`: Violations found (when using `--fail-on-violations`)

---

### `crashlens guard` - ⚠️ DEPRECATED
**Status**: Deprecated as of v3.0.0, will be removed in v3.1.0

```bash
crashlens guard [OPTIONS] LOGFILE  # Shows deprecation warning
```

**Deprecation Notice:**
- The `guard` command is now an alias for `guard`
- All functionality is identical to `guard`
- A deprecation warning is displayed on every invocation
- Use `guard` instead for new workflows

**Migration:**
```bash
# Old (deprecated)
crashlens guard logs.jsonl --policy-template all

# New (recommended)
crashlens guard logs.jsonl --policy-template all
```

**See Also:** [MIGRATION.md](../MIGRATION.md) for complete migration guide

---

### `crashlens init` - Setup Wizard
**Purpose**: Initialize CrashLens configuration and GitHub Actions workflow

```bash
crashlens init [OPTIONS]
```

**Key Features:**
- Interactive setup wizard or non-interactive automation
- Generates `.crashlens/config.yaml` configuration
- Creates GitHub Actions workflow for CI/CD
- Environment variable support for automation

**Options:**
| Option | Description | Use Case |
|--------|-------------|----------|
| `--non-interactive` | Use environment variables instead of prompts | CI/CD pipelines |
| `--dry-run-workflow` | Print workflow YAML to stdout | Preview before creation |

**Environment Variables (Non-Interactive Mode):**
| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `CRASHLENS_TEMPLATES` | Policy templates to use | `"retry-loop-prevention"` | `"all"` |
| `CRASHLENS_SEVERITY` | Minimum severity threshold | `"medium"` | `"high"` |
| `CRASHLENS_FAIL_ON_VIOLATIONS` | Exit with error on violations | `"false"` | `"true"` |
| `CRASHLENS_LOGS_SOURCE` | Default log source path | `"logs/"` | `".llm_logs/"` |
| `CRASHLENS_OUTPUT_FORMAT` | Report output format | `"markdown"` | `"slack"` |
| `CRASHLENS_CREATE_WORKFLOW` | Generate GitHub Actions workflow | `"true"` | `"false"` |

**Examples:**
```bash
# Interactive setup
crashlens init

# Non-interactive setup for CI/CD
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="medium"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
crashlens init --non-interactive

# Preview workflow without creating
crashlens init --dry-run-workflow
```

**PowerShell (Windows):**
```powershell
$env:CRASHLENS_TEMPLATES = "all"
$env:CRASHLENS_SEVERITY = "medium"
$env:CRASHLENS_FAIL_ON_VIOLATIONS = "true"
crashlens init --non-interactive
```

---

## 🔗 Data Integration Commands

### `crashlens fetch-langfuse` - Langfuse Integration
**Purpose**: Fetch traces from Langfuse API and optionally analyze them

```bash
crashlens fetch-langfuse [OPTIONS]
```

**Key Features:**
- Direct integration with Langfuse API
- Automatic analysis or save to file
- Configurable time range and limits
- Environment variable support for credentials

**Options:**
| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--hours-back` | Hours back to fetch traces | 24 | `--hours-back 48` |
| `--limit` | Maximum number of traces to fetch | 1000 | `--limit 500` |
| `-o, --output` | Save to file instead of analyzing | N/A | `--output traces.jsonl` |
| `--analyze` | Analyze fetched traces immediately | Automatic if no output | `--analyze` |
| `--public-key` | Langfuse public key | `LANGFUSE_PUBLIC_KEY` env var | - |
| `--secret-key` | Langfuse secret key | `LANGFUSE_SECRET_KEY` env var | - |
| `--base-url` | Langfuse base URL | `LANGFUSE_HOST` env var | - |

**Examples:**
```bash
# Fetch and analyze last 24 hours
crashlens fetch-langfuse

# Fetch last 48 hours and save to file
crashlens fetch-langfuse --hours-back 48 --output recent-traces.jsonl

# Fetch limited traces and analyze
crashlens fetch-langfuse --limit 500 --analyze
```

**Environment Setup:**
```bash
export LANGFUSE_PUBLIC_KEY="pk_..."
export LANGFUSE_SECRET_KEY="sk_..."
export LANGFUSE_HOST="https://cloud.langfuse.com"
```

---

### `crashlens fetch-helicone` - Helicone Integration
**Purpose**: Fetch requests from Helicone API and optionally analyze them

```bash
crashlens fetch-helicone [OPTIONS]
```

**Key Features:**
- Direct integration with Helicone API
- Automatic analysis or save to file
- Configurable time range and limits
- Environment variable support for API key

**Options:**
| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--hours-back` | Hours back to fetch requests | 24 | `--hours-back 48` |
| `--limit` | Maximum number of requests to fetch | 1000 | `--limit 500` |
| `-o, --output` | Save to file instead of analyzing | N/A | `--output requests.jsonl` |
| `--analyze` | Analyze fetched requests immediately | Automatic if no output | `--analyze` |
| `--api-key` | Helicone API key | `HELICONE_API_KEY` env var | - |
| `--base-url` | Helicone base URL | Production endpoint | - |

**Examples:**
```bash
# Fetch and analyze last 24 hours
crashlens fetch-helicone

# Fetch last 48 hours and save to file
crashlens fetch-helicone --hours-back 48 --output recent-requests.jsonl

# Fetch limited requests and analyze
crashlens fetch-helicone --limit 500 --analyze
```

**Environment Setup:**
```bash
export HELICONE_API_KEY="sk-helicone-..."
```

---

## 🧪 Testing & Development Commands

### `crashlens simulate` - Test Data Generation
**Purpose**: Generate realistic Langfuse-style .jsonl traces for testing

```bash
crashlens simulate [OPTIONS]
```

**Key Features:**
- Generates realistic test data with configurable scenarios
- Multiple scenario types for testing different policies
- Deterministic output with seed support
- Automatic policy checking integration

**Options:**
| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--output` | Path to write .jsonl file | Required | `--output test.jsonl` |
| `--count` | Number of traces to generate | 100 | `--count 500` |
| `--scenario` | Scenario type to generate | normal | `--scenario retry-loop` |
| `--models` | Comma-separated list of model names | Common OpenAI models | `--models gpt-4,gpt-3.5-turbo` |
| `--error-rate` | Probability of generating error traces | 0.2 | `--error-rate 0.3` |
| `--seed` | Random seed for deterministic output | Random | `--seed 42` |
| `--force` | Overwrite existing output file | False | `--force` |
| `--open` | Run guard on generated file | False | `--open` |

**Scenario Types:**
- `normal`: Typical API usage patterns
- `retry-loop`: Generates retry loop patterns for testing
- `model-overkill`: Creates model overkill scenarios
- `slow`: Simulates slow response patterns
- `mixed-errors`: Mixed error conditions

**Examples:**
```bash
# Generate test data for retry loop testing
crashlens simulate --output retry-test.jsonl --count 500 --scenario retry-loop

# Generate mixed scenarios with high error rate
crashlens simulate --output mixed.jsonl --scenario mixed-errors --error-rate 0.3 --open

# Deterministic output for CI/CD testing
crashlens simulate --output deterministic.jsonl --seed 42 --force
```

---

### `crashlens list-policy-templates` - Template Discovery
**Purpose**: List all available built-in policy templates

```bash
crashlens list-policy-templates
```

**Key Features:**
- Shows all available policy templates
- Includes descriptions and use cases
- No options required

**Example:**
```bash
crashlens list-policy-templates
```

**Sample Output:**
```
Available Policy Templates:
1. retry-loop-prevention: Prevents excessive retry loops
2. model-overkill-detection: Detects expensive models for simple tasks
3. budget-protection: Enforces cost limits and thresholds
4. all: All available templates combined
```

---

## 🎛️ Global Options

All commands support these global options:

| Option | Description |
|--------|-------------|
| `--version` | Show CrashLens version and exit |
| `--help` | Show help message and exit |

---

## 🔄 Command Combinations & Workflows

### CI/CD Pipeline Setup
```bash
# 1. Setup (run once)
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="medium"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
crashlens init --non-interactive

# 2. Policy checking in CI
crashlens guard logs.jsonl --policy-template all --fail-on-violations
```

### Development Workflow
```bash
# 1. Generate test data
crashlens simulate --output test-data.jsonl --count 1000 --scenario mixed-errors

# 2. Test policies
crashlens guard test-data.jsonl --policy-template all

# 3. Full analysis
crashlens scan test-data.jsonl --detailed --summary
```

### Production Monitoring
```bash
# 1. Fetch live data
crashlens fetch-langfuse --hours-back 24 --output daily-traces.jsonl

# 2. Analyze for issues
crashlens scan daily-traces.jsonl --policy-template all --format slack --detailed

# 3. Generate reports
crashlens scan daily-traces.jsonl --summary-only --format json > daily-report.json
```

---

## ❌ Error Codes

| Exit Code | Description | Commands |
|-----------|-------------|----------|
| `0` | Success, no issues found | All commands |
| `1` | Policy violations found | `guard` with `--fail-on-violations` |
| `2` | Command line argument error | All commands |
| `3` | File not found or read error | Commands requiring input files |
| `4` | Configuration error | `init`, commands with config files |
| `5` | API connection error | `fetch-langfuse`, `fetch-helicone` |

---

## 📝 File Outputs

### Reports Generated
- `report.md`: Main analysis report (scan command)
- `.crashlens/config.yaml`: Configuration file (init command)
- `.github/workflows/crashlens.yml`: GitHub Actions workflow (init command)
- `detailed_output/*.json`: Detailed category reports (scan with --detailed)

### Log File Requirements
- **Format**: JSONL (one JSON object per line)
- **Required fields**: `traceId`, `input.model`, `input.prompt`, `usage.completion_tokens`
- **Optional fields**: `cost`, `startTime`, `name`, etc.

---

## 🔗 Environment Variables Reference

See [docs/NON-INTERACTIVE-GUIDE.md](NON-INTERACTIVE-GUIDE.md) for complete environment variable documentation.

---

## 📚 Additional Resources

- **Complete Setup Guide**: [docs/NON-INTERACTIVE-GUIDE.md](NON-INTERACTIVE-GUIDE.md)
- **Quick Reference**: [docs/NON-INTERACTIVE-QUICK-REFERENCE.md](NON-INTERACTIVE-QUICK-REFERENCE.md)
- **User Manual**: [USER_MANUAL.md](../USER_MANUAL.md)
- **Main Documentation**: [README.md](../README.md)
