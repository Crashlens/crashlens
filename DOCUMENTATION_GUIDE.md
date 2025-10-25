# 📖 Documentation Guide

**CrashLens Documentation Map** - Find exactly what you need

---

## 🎯 I want to...

### Start Using CrashLens
→ **[QUICK_START.md](QUICK_START.md)** - Get running in 5 minutes  
→ **[docs/QUICKSTART.md](docs/QUICKSTART.md)** - Detailed installation guide  
→ **[docs/COMMAND-REFERENCE.md](docs/COMMAND-REFERENCE.md)** - All CLI commands

### Enable Metrics & Monitoring (NEW in v2.0)
→ **[PHASE_2_SUMMARY.md](PHASE_2_SUMMARY.md)** - Quick overview  
→ **[docs/OBSERVABILITY.md](docs/OBSERVABILITY.md)** - Complete metrics guide  
→ **[docs/GRAFANA_SETUP.md](docs/GRAFANA_SETUP.md)** - Dashboard setup  
→ **[dashboards/](dashboards/)** - Pre-built Grafana dashboards

### Write Custom Policies
→ **[docs/POLICY_GUIDE.md](docs/POLICY_GUIDE.md)** - Policy writing guide  
→ **[examples/policies/](examples/policies/)** - Example policies  
→ **[policies/](policies/)** - Built-in policy templates

### Integrate with CI/CD
→ **[examples/ci-workflows/](examples/ci-workflows/)** - GitHub Actions examples  
→ **[docs/NON-INTERACTIVE-GUIDE.md](docs/NON-INTERACTIVE-GUIDE.md)** - Automation guide

### Integrate with Slack
→ **[docs/SLACK_INTEGRATION.md](docs/SLACK_INTEGRATION.md)** - Slack webhook setup

### Remove PII from Logs
→ **[docs/PII_REMOVAL_GUIDE.md](docs/PII_REMOVAL_GUIDE.md)** - Privacy protection guide

### Understand Test Coverage
→ **[tests/TEST_DOCUMENTATION.md](tests/TEST_DOCUMENTATION.md)** - All 26 tests explained  
→ **[docs/PHASE_2_COMPLETE_REPORT.md](docs/PHASE_2_COMPLETE_REPORT.md)** - Test results & benchmarks

### Contribute to Development
→ **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines  
→ **[docs/PHASE_2_COMPLETE_REPORT.md](docs/PHASE_2_COMPLETE_REPORT.md)** - Technical architecture  
→ **[docs/architecture-flow.md](docs/architecture-flow.md)** - System design

### Troubleshoot Issues
→ **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Common problems & solutions  
→ **[docs/WINDOWS_SETUP.md](docs/WINDOWS_SETUP.md)** - Windows-specific issues

---

## 📂 Documentation Structure

```
crashlens/
├── README.md                          # Project overview
├── QUICK_START.md                     # 5-minute getting started
├── PHASE_2_SUMMARY.md                 # 🆕 Metrics integration overview
├── CONTRIBUTING.md                    # How to contribute
├── SECURITY.md                        # Security policy
├── CHANGELOG.md                       # Version history
│
├── docs/                              # 📖 Comprehensive documentation
│   ├── QUICKSTART.md                  # Detailed installation
│   ├── COMMAND-REFERENCE.md           # All CLI commands
│   ├── OBSERVABILITY.md               # 🆕 Prometheus metrics guide
│   ├── GRAFANA_SETUP.md               # 🆕 Dashboard configuration
│   ├── HTTP_SERVER_SECURITY.md        # 🆕 Security hardening
│   ├── PHASE_2_COMPLETE_REPORT.md     # 🆕 Full technical report
│   ├── SLACK_INTEGRATION.md           # Slack webhooks
│   ├── PII_REMOVAL_GUIDE.md           # Privacy protection
│   ├── POLICY_GUIDE.md                # Custom policy writing
│   ├── NON-INTERACTIVE-GUIDE.md       # CI/CD automation
│   ├── architecture-flow.md           # System architecture
│   ├── TROUBLESHOOTING.md             # Problem solving
│   ├── WINDOWS_SETUP.md               # Windows PATH setup
│   └── INDEX.md                       # Documentation index
│
├── tests/
│   └── TEST_DOCUMENTATION.md          # 🆕 All 26 tests explained
│
├── examples/                          # 💡 Working examples
│   ├── config/                        # Configuration examples
│   ├── policies/                      # Policy examples
│   ├── ci-workflows/                  # GitHub Actions workflows
│   └── custom_reports/                # Custom report templates
│
├── dashboards/                        # 📊 Grafana dashboards
│   ├── crashlens-policy-enforcement.json
│   ├── crashlens-alert-rules.yml
│   └── QUICK_REFERENCE.md
│
├── policies/                          # 📋 Built-in policy templates
│   ├── retry-loop-detector.yaml
│   ├── fallback-chain-detector.yaml
│   └── max-cost-per-trace.yaml
│
└── archive/                           # 🗄️ Historical documents
    └── phase-2-development-logs/      # Development notes (archived)
```

---

## 🆕 What's New in v2.0 (Phase 2)

**Prometheus Metrics Integration** - Production-ready observability

### New Features
- ✅ Prometheus metrics collection (8 metrics)
- ✅ Pushgateway integration (fire-and-forget push)
- ✅ HTTP metrics server (alternative mode)
- ✅ Grafana dashboard templates
- ✅ Cardinality protection (prevent metrics explosion)
- ✅ Lazy loading (zero overhead when disabled)

### New Documentation
- **[PHASE_2_SUMMARY.md](PHASE_2_SUMMARY.md)** - Quick overview
- **[docs/OBSERVABILITY.md](docs/OBSERVABILITY.md)** - Complete guide
- **[docs/GRAFANA_SETUP.md](docs/GRAFANA_SETUP.md)** - Dashboard setup
- **[docs/PHASE_2_COMPLETE_REPORT.md](docs/PHASE_2_COMPLETE_REPORT.md)** - Technical details
- **[tests/TEST_DOCUMENTATION.md](tests/TEST_DOCUMENTATION.md)** - 26 tests explained

### Test Coverage
- 26 tests total (100% passing)
- 6 critical verification tests
- Real Docker E2E integration test
- 87% code coverage

**See**: [PHASE_2_SUMMARY.md](PHASE_2_SUMMARY.md) for details

---

## 📊 Quick Reference Tables

### By User Type

| User Type | Start Here |
|-----------|----------|
| **First-time user** | [QUICK_START.md](QUICK_START.md) |
| **DevOps engineer** | [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md) |
| **Security analyst** | [docs/PII_REMOVAL_GUIDE.md](docs/PII_REMOVAL_GUIDE.md) |
| **Policy author** | [docs/POLICY_GUIDE.md](docs/POLICY_GUIDE.md) |
| **Developer** | [docs/PHASE_2_COMPLETE_REPORT.md](docs/PHASE_2_COMPLETE_REPORT.md) |
| **QA/Tester** | [tests/TEST_DOCUMENTATION.md](tests/TEST_DOCUMENTATION.md) |

### By Use Case

| Use Case | Documentation |
|----------|---------------|
| Scan logs for token waste | [QUICK_START.md](QUICK_START.md) |
| Monitor AI costs | [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md) |
| Create Grafana dashboards | [docs/GRAFANA_SETUP.md](docs/GRAFANA_SETUP.md) |
| Send alerts to Slack | [docs/SLACK_INTEGRATION.md](docs/SLACK_INTEGRATION.md) |
| Enforce cost policies in CI | [examples/ci-workflows/](examples/ci-workflows/) |
| Remove PII from logs | [docs/PII_REMOVAL_GUIDE.md](docs/PII_REMOVAL_GUIDE.md) |
| Write custom detection rules | [docs/POLICY_GUIDE.md](docs/POLICY_GUIDE.md) |
| Troubleshoot errors | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |

---

## 🔗 External Resources

### Community
- **GitHub**: [Crashlens/crashlens](https://github.com/Crashlens/crashlens)
- **Issues**: [Report bugs or request features](https://github.com/Crashlens/crashlens/issues)
- **Discussions**: [Community Q&A](https://github.com/Crashlens/crashlens/discussions)

### Related Tools
- **Langfuse**: [langfuse.com](https://langfuse.com) - LLM observability platform
- **Prometheus**: [prometheus.io](https://prometheus.io) - Monitoring system
- **Grafana**: [grafana.com](https://grafana.com) - Visualization platform
- **Pushgateway**: [Prometheus Pushgateway](https://github.com/prometheus/pushgateway)

---

## ❓ Can't Find What You Need?

1. **Search** - Use GitHub search or `Ctrl+F` in documents
2. **Check examples** - [examples/](examples/) has working code
3. **Read tests** - [tests/TEST_DOCUMENTATION.md](tests/TEST_DOCUMENTATION.md) explains behavior
4. **Ask community** - [GitHub Discussions](https://github.com/Crashlens/crashlens/discussions)
5. **Report issue** - [GitHub Issues](https://github.com/Crashlens/crashlens/issues)

---

**Last Updated**: 2025-01-24  
**Version**: 2.0.0  
**Documentation Status**: ✅ Complete
