# 📚 CrashLens Documentation Index

Welcome to CrashLens documentation! This index will help you find the right guide for your needs.

## 🚀 Getting Started

**New to CrashLens?** Start here:

1. **[README.md](../README.md)** - Project overview, features, and installation
2. **[docs/QUICKSTART.md](QUICKSTART.md)** - Common commands and quick reference
3. **[docs/USER_MANUAL.md](USER_MANUAL.md)** - Complete step-by-step user guide

## 📖 User Guides

### Core Features
- **[WHAT_IS_CRASHLENS.md](WHAT_IS_CRASHLENS.md)** - Complete guide to understanding CrashLens (NEW!)
- **[QUICKSTART.md](QUICKSTART.md)** - Quick reference for common tasks
- **[COMMAND-REFERENCE.md](COMMAND-REFERENCE.md)** - Complete CLI command documentation
- **[USER_MANUAL.md](USER_MANUAL.md)** - Comprehensive usage guide with examples

### Data Sources & Input
- **[FILE_HANDLING_MANUAL.md](FILE_HANDLING_MANUAL.md)** - File inputs, stdin, clipboard, API sources
- **[LOG_SETUP.md](LOG_SETUP.md)** - Log configuration and format requirements

### Privacy & Security
- **[PII_REMOVAL_GUIDE.md](PII_REMOVAL_GUIDE.md)** - Remove sensitive data from logs
- **[../SECURITY.md](../SECURITY.md)** - Security policy and reporting

### Integrations
- **[SLACK_INTEGRATION.md](SLACK_INTEGRATION.md)** - Slack webhook setup and notifications
- **[PROMETHEUS_GRAFANA_SETUP.md](PROMETHEUS_GRAFANA_SETUP.md)** - Prometheus & Grafana installation guide (NEW!)
- **[OBSERVABILITY.md](OBSERVABILITY.md)** - Prometheus & Grafana monitoring setup

### CI/CD
- **[NON-INTERACTIVE-GUIDE.md](NON-INTERACTIVE-GUIDE.md)** - GitHub Actions and CI/CD integration

## 🔧 Developer Resources

**Contributing to CrashLens?**

- **[../CONTRIBUTING.md](../CONTRIBUTING.md)** - Development setup, conventions, and guidelines
- **[architecture-flow.md](architecture-flow.md)** - System architecture and flow diagrams
- **[../CHANGELOG.md](../CHANGELOG.md)** - Version history and release notes

## 📊 Advanced Topics

### Observability Stack
- **[PROMETHEUS_GRAFANA_SETUP.md](PROMETHEUS_GRAFANA_SETUP.md)** - Complete installation guide for macOS & Windows (NEW!)
- **[OBSERVABILITY.md](OBSERVABILITY.md)** - Complete Prometheus & Grafana guide
  - 8 metrics definitions
  - Dashboard setup
  - Alert rules
  - Per-rule sampling
  - HTTP server mode
- **[../OBSERVABILITY_REPORT.md](../OBSERVABILITY_REPORT.md)** - Implementation details and architecture decisions

## 🗂️ Documentation by Use Case

### I want to...

**Understand what CrashLens does and all its features**
→ Read [WHAT_IS_CRASHLENS.md](WHAT_IS_CRASHLENS.md) - comprehensive overview

**Analyze my AI usage logs**
→ Start with [QUICKSTART.md](QUICKSTART.md), then see [USER_MANUAL.md](USER_MANUAL.md)

**Set up automated checks in CI/CD**
→ Read [NON-INTERACTIVE-GUIDE.md](NON-INTERACTIVE-GUIDE.md)

**Remove PII from logs before sharing**
→ Follow [PII_REMOVAL_GUIDE.md](PII_REMOVAL_GUIDE.md)

**Send alerts to Slack**
→ Configure with [SLACK_INTEGRATION.md](SLACK_INTEGRATION.md)

**Monitor with Prometheus & Grafana**
→ Install using [PROMETHEUS_GRAFANA_SETUP.md](PROMETHEUS_GRAFANA_SETUP.md), configure with [OBSERVABILITY.md](OBSERVABILITY.md)

**Understand specific commands**
→ Check [COMMAND-REFERENCE.md](COMMAND-REFERENCE.md)

**Contribute code**
→ Read [../CONTRIBUTING.md](../CONTRIBUTING.md)

**Report a security issue**
→ See [../SECURITY.md](../SECURITY.md)

## 📁 Documentation Structure

```
crashlens/
├── README.md                    # Project overview & quick start
├── CHANGELOG.md                 # Version history
├── CONTRIBUTING.md              # Developer guide
├── SECURITY.md                  # Security policy
├── OBSERVABILITY_REPORT.md      # Observability implementation
├── PR_TEMPLATE.md               # Pull request template
│
└── docs/
    ├── INDEX.md                       # This file
    ├── QUICKSTART.md                  # Quick reference
    ├── COMMAND-REFERENCE.md           # CLI documentation
    ├── USER_MANUAL.md                 # Complete user guide
    ├── OBSERVABILITY.md               # Prometheus/Grafana
    ├── PII_REMOVAL_GUIDE.md           # Privacy features
    ├── SLACK_INTEGRATION.md           # Slack webhooks
    ├── FILE_HANDLING_MANUAL.md        # Input sources
    ├── NON-INTERACTIVE-GUIDE.md       # CI/CD integration
    ├── LOG_SETUP.md                   # Log configuration
    └── architecture-flow.md           # Architecture diagrams
```

## 🆘 Getting Help

**Can't find what you need?**

1. Check the [COMMAND-REFERENCE.md](COMMAND-REFERENCE.md) for detailed CLI documentation
2. Read the [USER_MANUAL.md](USER_MANUAL.md) for comprehensive examples
3. Look at `examples/` directory for sample configs and logs
4. Open an issue on GitHub for questions

## 📝 Documentation Maintenance

**For maintainers:**
- Keep this index updated when adding/removing documentation
- Follow the structure defined in [CONTRIBUTING.md](../CONTRIBUTING.md)
- Update [CHANGELOG.md](../CHANGELOG.md) for documentation changes

---

**Last Updated:** October 23, 2025  
**CrashLens Version:** 2.9.12+
