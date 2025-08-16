# 🎯 CrashLens Working Commands Summary

## ✅ Fully Working Commands

### 1. `crashlens scan` - Core Analysis Engine
**Status**: ✅ **WORKING** - Primary analysis command
- **Purpose**: Analyze logs for token waste patterns
- **Input Sources**: File, stdin, clipboard, demo, Langfuse API, Helicone API
- **Output Formats**: Slack, Markdown, JSON
- **Key Features**: Waste detection, cost analysis, detailed reports
- **Example**: `crashlens scan logs.jsonl --format markdown --detailed`

### 2. `crashlens policy-check` - Policy Validation
**Status**: ✅ **WORKING** - Fast policy validation
- **Purpose**: Check logs against policy rules without full analysis
- **Key Features**: CI/CD integration, severity filtering, exit codes
- **Templates**: 10 built-in policy templates available
- **Example**: `crashlens policy-check logs.jsonl --policy-template all --fail-on-violations`

### 3. `crashlens init` - Setup Wizard
**Status**: ✅ **WORKING** - Configuration and CI/CD setup
- **Purpose**: Initialize CrashLens configuration and GitHub Actions
- **Modes**: Interactive wizard or non-interactive (environment variables)
- **Outputs**: `.crashlens/config.yaml`, `.github/workflows/crashlens.yml`
- **Example**: `crashlens init --non-interactive` (with env vars)

### 4. `crashlens simulate` - Test Data Generator
**Status**: ✅ **WORKING** - Perfect for testing and development
- **Purpose**: Generate realistic test data for policy testing
- **Scenarios**: normal, retry-loop, model-overkill, slow, mixed-errors
- **Features**: Configurable count, models, error rates, deterministic seeds
- **Example**: `crashlens simulate --output test.jsonl --count 500 --scenario retry-loop`

### 5. `crashlens list-policy-templates` - Template Discovery
**Status**: ✅ **WORKING** - Lists available policy templates
- **Purpose**: Show all built-in policy templates with descriptions
- **Output**: 10 policy templates with savings estimates
- **Example**: `crashlens list-policy-templates`

### 6. `crashlens fetch-langfuse` - Langfuse Integration
**Status**: ✅ **WORKING** - Direct API integration
- **Purpose**: Fetch traces from Langfuse API and analyze
- **Features**: Configurable time range, limits, save to file
- **Auth**: Environment variables (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY)
- **Example**: `crashlens fetch-langfuse --hours-back 48 --limit 500`

### 7. `crashlens fetch-helicone` - Helicone Integration
**Status**: ✅ **WORKING** - Direct API integration
- **Purpose**: Fetch requests from Helicone API and analyze
- **Features**: Configurable time range, limits, save to file
- **Auth**: Environment variable (HELICONE_API_KEY)
- **Example**: `crashlens fetch-helicone --hours-back 24 --analyze`

---

## 🚀 Command Usage Statistics

### Primary Commands (Most Used)
1. **`crashlens scan`** - Main analysis engine, most comprehensive
2. **`crashlens policy-check`** - Fast validation for CI/CD pipelines
3. **`crashlens init`** - One-time setup for projects

### Development Commands
1. **`crashlens simulate`** - Essential for testing without production logs
2. **`crashlens list-policy-templates`** - Policy discovery and planning

### Integration Commands
1. **`crashlens fetch-langfuse`** - For Langfuse users
2. **`crashlens fetch-helicone`** - For Helicone users

---

## 🎯 Command Categories by Use Case

### 🏗️ Project Setup
```bash
# Initialize project configuration
crashlens init

# List available policies for setup
crashlens list-policy-templates
```

### 🧪 Development & Testing
```bash
# Generate test data
crashlens simulate --output test.jsonl --count 1000 --scenario mixed-errors

# Quick policy validation
crashlens policy-check test.jsonl --policy-template all

# Full analysis with detailed reports
crashlens scan test.jsonl --detailed --summary
```

### 🔍 Production Analysis
```bash
# Comprehensive analysis
crashlens scan production-logs.jsonl --format slack --detailed

# Policy compliance check
crashlens policy-check production-logs.jsonl --policy-template budget-protection --fail-on-violations

# Live API analysis
crashlens fetch-langfuse --hours-back 24 --analyze
```

### 🤖 CI/CD Integration
```bash
# Non-interactive setup
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
crashlens init --non-interactive

# Automated policy checking
crashlens policy-check logs.jsonl --policy-template all --severity-threshold high --fail-on-violations
```

---

## 📊 Feature Matrix

| Command | Analysis | Policy Check | Cost Calc | API Fetch | Test Data | CI/CD Ready |
|---------|----------|--------------|-----------|-----------|-----------|-------------|
| `scan` | ✅ Full | ✅ Integrated | ✅ Yes | ✅ Lang/Heli | ❌ No | ✅ Yes |
| `policy-check` | ❌ No | ✅ Primary | ❌ No | ❌ No | ❌ No | ✅ Yes |
| `init` | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ✅ Primary |
| `simulate` | ❌ No | ❌ No | ❌ No | ❌ No | ✅ Primary | ✅ Yes |
| `list-policy-templates` | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ✅ Yes |
| `fetch-langfuse` | ✅ Auto | ❌ No | ❌ No | ✅ Primary | ❌ No | ✅ Yes |
| `fetch-helicone` | ✅ Auto | ❌ No | ❌ No | ✅ Primary | ❌ No | ✅ Yes |

---

## 🎨 Output Formats & Files

### Reports Generated
| Command | File Output | Format Options |
|---------|-------------|----------------|
| `scan` | `report.md` | slack, markdown, json |
| `scan --detailed` | `detailed_output/*.json` | JSON by category |
| `init` | `.crashlens/config.yaml` | YAML config |
| `init` | `.github/workflows/crashlens.yml` | GitHub Actions |
| `simulate` | Custom `.jsonl` file | JSONL traces |

### Log File Requirements
- **Format**: JSONL (one JSON object per line)
- **Required Fields**: `traceId`, `input.model`, `input.prompt`, `usage.completion_tokens`
- **Optional Fields**: `cost`, `startTime`, `name`, metadata

---

## 🔑 Environment Variables

### Authentication
```bash
# Langfuse
export LANGFUSE_PUBLIC_KEY="pk_..."
export LANGFUSE_SECRET_KEY="sk_..."
export LANGFUSE_HOST="https://cloud.langfuse.com"

# Helicone
export HELICONE_API_KEY="sk-helicone-..."
```

### Configuration (Non-Interactive Mode)
```bash
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="medium"
export CRASHLENS_FAIL_ON_VIOLATIONS="true"
export CRASHLENS_LOGS_SOURCE="logs/"
export CRASHLENS_OUTPUT_FORMAT="markdown"
export CRASHLENS_CREATE_WORKFLOW="true"
```

---

## ⚡ Quick Command Examples

### Most Common Workflows
```bash
# Setup project
crashlens init

# Generate test data and validate
crashlens simulate --output test.jsonl --count 100 --scenario retry-loop
crashlens policy-check test.jsonl --policy-template retry-loop-prevention

# Analyze production logs
crashlens scan production.jsonl --format slack --detailed

# CI/CD policy check
crashlens policy-check logs.jsonl --policy-template all --fail-on-violations
```

### Advanced Usage
```bash
# Comprehensive analysis with all features
crashlens scan logs.jsonl --policy-template all --format json --detailed --summary

# Live API monitoring
crashlens fetch-langfuse --hours-back 24 | crashlens scan --stdin --format slack

# Deterministic testing
crashlens simulate --output tests.jsonl --seed 42 --scenario mixed-errors --force
```

---

## 📈 Success Metrics

All commands are **production-ready** and successfully:
- ✅ Handle malformed input gracefully
- ✅ Provide helpful error messages
- ✅ Support multiple output formats
- ✅ Work cross-platform (Windows, macOS, Linux)
- ✅ Integrate with CI/CD pipelines
- ✅ Provide comprehensive help documentation
- ✅ Support both interactive and non-interactive modes

---

## 📚 Documentation Links

- **Complete Command Reference**: [docs/COMMAND-REFERENCE.md](COMMAND-REFERENCE.md)
- **Non-Interactive Guide**: [docs/NON-INTERACTIVE-GUIDE.md](NON-INTERACTIVE-GUIDE.md)
- **Quick Reference**: [docs/NON-INTERACTIVE-QUICK-REFERENCE.md](NON-INTERACTIVE-QUICK-REFERENCE.md)
- **User Manual**: [USER_MANUAL.md](../USER_MANUAL.md)
- **Main Documentation**: [README.md](../README.md)
