# 📚 CrashLens Documentation Index - Complete Guide

**Version:** 2.10.1  
**Last Updated:** 2025-11-09  
**Purpose:** Comprehensive index of all CrashLens documentation with descriptions

This document provides a complete overview of all documentation files in the `docs/` folder, organized by category with brief descriptions to help you find exactly what you need.

---

## 🎯 Quick Navigation

| I Need To... | Go To |
|-------------|--------|
| **Understand what CrashLens is** | [WHAT_IS_CRASHLENS.md](#what_is_crashlensmd) |
| **Get started quickly** | [QUICKSTART.md](#quickstartmd) |
| **Learn all CLI commands** | [CLI_COMMAND_REFERENCE.md](#cli_command_referencemd) |
| **Set up policy enforcement** | [GUARD.md](#guardmd) |
| **Monitor with Prometheus** | [OBSERVABILITY.md](#observabilitymd) |
| **Integrate with CI/CD** | [NON-INTERACTIVE-GUIDE.md](#non-interactive-guidemd) |
| **Remove PII from logs** | [PII_REMOVAL_GUIDE.md](#pii_removal_guidemd) |
| **Understand detector algorithms** | [../crashlens/detectors/detectors.md](#detectors-documentation) |

---

## 📖 Documentation Files by Category

### 🚀 Getting Started (New Users Start Here)

#### **WHAT_IS_CRASHLENS.md**
- **Size:** 1,671 lines
- **Purpose:** Complete conceptual guide to understanding CrashLens
- **Contents:**
  - Core problem & solution (token waste detection)
  - Key features overview
  - Architecture & how it works
  - Detection capabilities (4 detectors explained)
  - Policy enforcement system
  - Input sources (Langfuse, Helicone, OpenAI, local files)
  - Output & reporting formats
  - Privacy & security model
  - Integration options
  - Use cases (development, CI/CD, production monitoring)
  - Technical stack
- **Best For:** Understanding the "why" and "what" of CrashLens
- **Read Time:** 25-30 minutes

#### **QUICKSTART.md**
- **Purpose:** Quick reference for common tasks
- **Contents:**
  - Installation instructions
  - Basic usage examples
  - Common commands cheat sheet
  - Quick troubleshooting
- **Best For:** Getting up and running in 5 minutes
- **Read Time:** 5-10 minutes

#### **USER_MANUAL.md**
- **Size:** 1,378 lines
- **Purpose:** Comprehensive step-by-step user guide
- **Contents:**
  - Complete setup instructions
  - All features explained with examples
  - GitHub Actions workflow integration
  - Policy configuration guide
  - Troubleshooting section
  - Best practices
- **Best For:** In-depth learning of all CrashLens features
- **Read Time:** 30-40 minutes

#### **INDEX.md**
- **Size:** 133 lines
- **Purpose:** Original documentation index (now superseded by this file)
- **Contents:**
  - Quick navigation links
  - Documentation organized by category
  - Getting started section
- **Best For:** Quick reference (older version)
- **Read Time:** 2-3 minutes

---

### 🔧 Command Reference

#### **CLI_COMMAND_REFERENCE.md** ⭐ NEW
- **Size:** 1,016 lines
- **Purpose:** Complete CLI command documentation
- **Contents:**
  - All 13 commands documented (scan, guard, report, simulate, etc.)
  - 90+ options with types, defaults, descriptions
  - 50+ usage examples
  - 25+ environment variables
  - 4 complete workflows (dev, CI/CD, production, privacy)
  - Common patterns and tips
  - Quick reference cheat sheet
- **Best For:** Looking up specific command syntax and options
- **Read Time:** Reference (search as needed)

#### **COMMAND-REFERENCE.md**
- **Purpose:** Earlier command documentation (older version)
- **Contents:**
  - CLI command overview
  - Basic usage examples
- **Best For:** Quick command lookup (older version, use CLI_COMMAND_REFERENCE.md instead)
- **Read Time:** 10-15 minutes

---

### 🛡️ Policy Enforcement & Guard

#### **GUARD.md** ⭐ ESSENTIAL
- **Size:** 842 lines
- **Purpose:** Complete guide to CI-friendly policy enforcement
- **Contents:**
  - Guard command overview and philosophy
  - YAML rule syntax (match conditions, actions, severity)
  - Boolean logic (AND/OR/NOT operators)
  - CI/CD integration examples
  - Policy templates (retry-loop, cost limits, model restrictions)
  - Advanced patterns (regex, nested fields, thresholds)
  - Exit codes and error handling
  - Privacy-safe reporting (--no-content, --strip-pii)
- **Best For:** Setting up automated policy checks in CI/CD
- **Read Time:** 20-25 minutes

#### **GUARD_IMPLEMENTATION_SUMMARY.md**
- **Purpose:** Technical summary of Guard implementation
- **Contents:**
  - Implementation details
  - Architecture decisions
  - Testing approach
- **Best For:** Developers working on Guard internals
- **Read Time:** 10-15 minutes

#### **GUARD_FUNCTIONALITY.md**
- **Purpose:** Guard functionality overview
- **Contents:**
  - Feature descriptions
  - Use cases
  - Examples
- **Best For:** Understanding Guard capabilities
- **Read Time:** 10-15 minutes

---

### 📊 Observability & Monitoring

#### **OBSERVABILITY.md** ⭐ PRODUCTION
- **Size:** 1,390 lines
- **Purpose:** Comprehensive Prometheus metrics guide
- **Contents:**
  - Prometheus installation and setup
  - 8 metrics definitions (counters, histograms, gauges)
  - Grafana dashboard setup (3 dashboards with 20+ panels)
  - PromQL query examples
  - Performance benchmarks (< 2s overhead)
  - Production deployment best practices
  - Cardinality protection (max 500 rules)
  - Alerting rules (PagerDuty, Slack integration)
  - Troubleshooting guide
- **Best For:** Production monitoring setup
- **Read Time:** 30-35 minutes

#### **PROMETHEUS_GRAFANA_SETUP.md**
- **Purpose:** Installation guide for Prometheus & Grafana
- **Contents:**
  - macOS installation (Homebrew)
  - Windows installation
  - Docker Compose setup
  - Configuration examples
- **Best For:** First-time setup of monitoring stack
- **Read Time:** 15-20 minutes

#### **GRAFANA_SETUP.md**
- **Purpose:** Grafana-specific setup guide
- **Contents:**
  - Dashboard import instructions
  - Panel configuration
  - Data source setup
- **Best For:** Grafana dashboard configuration
- **Read Time:** 10-15 minutes

#### **DASHBOARD_IMPLEMENTATION_COMPLETE.md**
- **Purpose:** Dashboard implementation technical details
- **Contents:**
  - Dashboard JSON structure
  - Panel specifications
  - Implementation notes
- **Best For:** Developers working on dashboards
- **Read Time:** 10-15 minutes

#### **DASHBOARD_LAYOUT_MAP.md**
- **Purpose:** Dashboard layout reference
- **Contents:**
  - Visual layout descriptions
  - Panel positioning
  - Design decisions
- **Best For:** Understanding dashboard organization
- **Read Time:** 5-10 minutes

#### **HTTP_SERVER_SECURITY.md**
- **Purpose:** Security guide for HTTP metrics server
- **Contents:**
  - Security considerations
  - Authentication options
  - Network configuration
- **Best For:** Securing metrics endpoints
- **Read Time:** 10-15 minutes

---

### 🔍 Detectors & Algorithms

#### **../crashlens/detectors/detectors.md** ⭐ TECHNICAL DEEP DIVE
- **Size:** 1,248 lines
- **Purpose:** Complete technical documentation for all 4 detectors
- **Contents:**
  - Detailed algorithmic logic for each detector (with code snippets)
  - Precise cost calculation formulas (step-by-step breakdowns)
  - Time/space complexity analysis (O(n), O(n²), etc.)
  - Edge case handling explanations
  - Real-world detection examples (JSON input/output)
  - Production accuracy metrics (96-99% accuracy rates)
  - Suppression system architecture
  - Configuration reference with YAML examples
  - Troubleshooting guide
  - Best practices for threshold tuning
- **Detectors Covered:**
  1. **RetryLoopDetector** (Priority 1) - Exact string matching + temporal analysis
  2. **FallbackStormDetector** (Priority 2) - Model switching cascade detection
  3. **FallbackFailureDetector** (Priority 3) - Tier violation detection (cheap→expensive)
  4. **OverkillModelDetector** (Priority 4) - Task complexity heuristics
- **Best For:** Understanding how waste detection algorithms work
- **Read Time:** 40-50 minutes

---

### 🔐 Privacy & Security

#### **PII_REMOVAL_GUIDE.md**
- **Purpose:** Guide to removing sensitive data from logs
- **Contents:**
  - PII detection patterns (email, SSN, phone, credit cards)
  - pii-remove and pii-clean commands
  - Regex patterns reference
  - Custom pattern configuration
  - Verification examples
- **Best For:** Sanitizing logs before sharing
- **Read Time:** 15-20 minutes

#### **../SECURITY.md**
- **Purpose:** Security policy and vulnerability reporting
- **Contents:**
  - Supported versions
  - Reporting vulnerabilities
  - Security best practices
- **Best For:** Understanding security commitment
- **Read Time:** 5 minutes

---

### 📥 Input Sources & Data Handling

#### **FILE_HANDLING_MANUAL.md**
- **Purpose:** Complete guide to input sources
- **Contents:**
  - Local file inputs (.jsonl)
  - stdin streaming
  - Clipboard input
  - Langfuse API integration
  - Helicone API integration
  - OpenAI format conversion
  - Batch processing
- **Best For:** Understanding all ways to provide logs to CrashLens
- **Read Time:** 20-25 minutes

#### **LOG_SETUP.md**
- **Purpose:** Log configuration and format requirements
- **Contents:**
  - Required fields (traceId, model, tokens)
  - Optional fields (metadata, cost)
  - JSONL format specification
  - Schema validation
  - Example logs
- **Best For:** Preparing logs for CrashLens analysis
- **Read Time:** 10-15 minutes

#### **CONFIG_PRECEDENCE.md**
- **Purpose:** Configuration priority and override behavior
- **Contents:**
  - CLI flags > env vars > config files > defaults
  - Configuration loading order
  - Override examples
- **Best For:** Understanding how CrashLens resolves configuration
- **Read Time:** 5-10 minutes

---

### 🔗 Integrations

#### **SLACK_INTEGRATION.md**
- **Purpose:** Slack webhook setup and notifications
- **Contents:**
  - Webhook URL setup
  - Message formatting (Slack Block Kit)
  - slack notify command examples
  - Custom templates
  - Error handling
- **Best For:** Sending CrashLens reports to Slack
- **Read Time:** 10-15 minutes

#### **NON-INTERACTIVE-GUIDE.md**
- **Purpose:** CI/CD integration guide
- **Contents:**
  - GitHub Actions workflows
  - Exit code handling
  - Non-interactive mode flags
  - Environment variable configuration
  - Example workflows (.github/workflows/)
- **Best For:** Integrating CrashLens into CI/CD pipelines
- **Read Time:** 15-20 minutes

#### **REPORT_COMMAND.md**
- **Purpose:** Report generation guide
- **Contents:**
  - report command usage
  - Email report generation
  - SMTP configuration
  - Report formats (markdown, JSON, HTML)
- **Best For:** Generating and sending cost digest reports
- **Read Time:** 10-15 minutes

#### **REPORT_EMAIL_ENHANCEMENTS.md**
- **Purpose:** Email reporting enhancements
- **Contents:**
  - HTML email templates
  - Advanced SMTP configuration
  - Attachment handling
- **Best For:** Advanced email reporting features
- **Read Time:** 10-15 minutes

---

### 🏗️ Architecture & Development

#### **architecture-flow.md**
- **Purpose:** System architecture and flow diagrams
- **Contents:**
  - Sequence diagrams (scan, guard, report flows)
  - Component interactions
  - Data flow visualization
  - Pipeline pattern explanation
- **Best For:** Understanding CrashLens internal architecture
- **Read Time:** 15-20 minutes

#### **../CONTRIBUTING.md**
- **Purpose:** Development setup and contribution guidelines
- **Contents:**
  - Development environment setup (Poetry)
  - Code style conventions
  - Testing requirements
  - Pull request process
  - Commit message format
- **Best For:** Contributors and developers
- **Read Time:** 10-15 minutes

#### **DEVELOPMENT_RETROSPECTIVE_100_COMMITS.md**
- **Purpose:** Development history retrospective
- **Contents:**
  - Key milestones
  - Lessons learned
  - Technical decisions
- **Best For:** Understanding project evolution
- **Read Time:** 10-15 minutes

---

### 📦 Implementation & Enhancement Summaries

#### **ENHANCEMENT_STEPS_SUMMARY.md**
- **Purpose:** Summary of enhancement phases
- **Contents:**
  - Feature additions
  - Implementation timeline
  - Status updates
- **Best For:** Tracking feature development
- **Read Time:** 10-15 minutes

#### **STEPS_0_TO_9_COMPLETE_DOCUMENTATION.md**
- **Purpose:** Documentation of development steps 0-9
- **Contents:**
  - Phase-by-phase implementation details
  - Testing results
  - Validation reports
- **Best For:** Understanding development process
- **Read Time:** 20-30 minutes

#### **STEP_2_INGESTION_SUMMARY.md**
- **Purpose:** Log ingestion implementation summary
- **Contents:**
  - Parser design
  - Schema validation
  - Performance optimization
- **Best For:** Understanding log parsing
- **Read Time:** 10-15 minutes

#### **STEP_3_DETECTOR_DRIVER_SUMMARY.md**
- **Purpose:** Detector pipeline implementation
- **Contents:**
  - Detector execution flow
  - Priority system
  - Suppression logic
- **Best For:** Understanding detector orchestration
- **Read Time:** 10-15 minutes

#### **STEP_4_GUARD_POLICYENGINE_ADAPTER_SUMMARY.md**
- **Purpose:** Guard and PolicyEngine integration
- **Contents:**
  - PolicyEngine design
  - Guard command implementation
  - Adapter pattern
- **Best For:** Understanding policy enforcement internals
- **Read Time:** 10-15 minutes

#### **STEP_4_PHASE_2_GUARD_INTEGRATION_COMPLETE.md**
- **Purpose:** Phase 2 Guard integration completion
- **Contents:**
  - Advanced Guard features
  - Integration testing
  - Production readiness
- **Best For:** Guard integration details
- **Read Time:** 10-15 minutes

#### **STEP_5_WRITERS_CONSOLIDATION_COMPLETE.md**
- **Purpose:** Output formatter consolidation
- **Contents:**
  - Formatter design
  - Output formats (markdown, JSON, Slack)
  - Writer abstraction
- **Best For:** Understanding output generation
- **Read Time:** 10-15 minutes

#### **STEP_6_BASELINE_INJECTION_COMPLETE.md**
- **Purpose:** Baseline metrics implementation
- **Contents:**
  - Baseline calculation
  - Performance metrics
  - Injection strategy
- **Best For:** Understanding baseline feature
- **Read Time:** 10-15 minutes

#### **STEP_7_CLI_ALIAS_COMPLETE.md**
- **Purpose:** CLI alias implementation
- **Contents:**
  - Command aliases
  - Shorthand syntax
  - Backward compatibility
- **Best For:** Understanding CLI design
- **Read Time:** 5-10 minutes

#### **STEP_8_BENCHMARKS_COMPLETE.md**
- **Purpose:** Benchmark implementation
- **Contents:**
  - Performance benchmarks
  - Memory profiling
  - Optimization results
- **Best For:** Understanding performance characteristics
- **Read Time:** 10-15 minutes

#### **STEP_9_INTEGRATION_COMPLETE.md**
- **Purpose:** Integration testing completion
- **Contents:**
  - End-to-end tests
  - Integration scenarios
  - Validation results
- **Best For:** Understanding test coverage
- **Read Time:** 10-15 minutes

#### **STEP_10_CLEANUP_PLAN.md**
- **Purpose:** Code cleanup and refactoring plan
- **Contents:**
  - Technical debt identification
  - Refactoring tasks
  - Cleanup priorities
- **Best For:** Understanding code quality improvements
- **Read Time:** 10-15 minutes

#### **STEP_10_COMPLEXITY_ANALYSIS.md**
- **Purpose:** Code complexity analysis
- **Contents:**
  - Cyclomatic complexity metrics
  - Hotspot identification
  - Simplification recommendations
- **Best For:** Understanding code complexity
- **Read Time:** 10-15 minutes

---

### ✅ Validation & Testing

#### **PRE_PRODUCTION_VALIDATION_REPORT.md**
- **Purpose:** Pre-production validation results
- **Contents:**
  - Test execution results
  - Bug fixes
  - Production readiness checklist
- **Best For:** Understanding production readiness
- **Read Time:** 15-20 minutes

#### **VALIDATION_EXECUTIVE_SUMMARY.md**
- **Purpose:** Executive summary of validation efforts
- **Contents:**
  - High-level test results
  - Key metrics
  - Risk assessment
- **Best For:** Management/stakeholder overview
- **Read Time:** 5-10 minutes

#### **VALIDATION_QUICK_REFERENCE.md**
- **Purpose:** Quick reference for validation results
- **Contents:**
  - Test pass/fail summary
  - Known issues
  - Workarounds
- **Best For:** Quick validation status check
- **Read Time:** 5 minutes

#### **FINAL_VALIDATION_K_N.md**
- **Purpose:** Final K-N validation report
- **Contents:**
  - Final test results
  - Edge case validation
  - Sign-off criteria
- **Best For:** Final production approval
- **Read Time:** 10-15 minutes

#### **TEST_FAILURE_FIXES_SESSION_REPORT.md**
- **Purpose:** Test failure debugging session report
- **Contents:**
  - Failed test analysis
  - Root cause identification
  - Fix implementations
- **Best For:** Understanding test failure resolution
- **Read Time:** 10-15 minutes

---

### 🐛 Bug Fixes & Critical Issues

#### **CRITICAL_BUG_FIXES.md**
- **Purpose:** Critical bug fixes documentation
- **Contents:**
  - Bug descriptions
  - Impact analysis
  - Fix implementations
  - Regression prevention
- **Best For:** Understanding critical bug history
- **Read Time:** 10-15 minutes

#### **BOOLEAN_LOGIC_IMPLEMENTATION.md**
- **Purpose:** Boolean logic implementation in policy engine
- **Contents:**
  - AND/OR/NOT operators
  - Evaluation algorithm
  - Test cases
- **Best For:** Understanding policy logic implementation
- **Read Time:** 10-15 minutes

---

### 🚀 Release & Roadmap

#### **RELEASE_ROADMAP.md**
- **Purpose:** Product release roadmap
- **Contents:**
  - Planned features
  - Release timeline
  - Version milestones
- **Best For:** Understanding future plans
- **Read Time:** 10-15 minutes

#### **V1_0_LAUNCH_CHECKLIST_FINAL.md**
- **Purpose:** v1.0 launch checklist
- **Contents:**
  - Pre-launch tasks
  - Documentation requirements
  - Testing completion
  - Marketing materials
- **Best For:** v1.0 release preparation
- **Read Time:** 10-15 minutes

#### **../CHANGELOG.md**
- **Purpose:** Version history and release notes
- **Contents:**
  - All versions with changes
  - Breaking changes
  - Bug fixes and features
- **Best For:** Understanding version differences
- **Read Time:** Reference (search by version)

---

### 📁 Archive

#### **archive/** (directory)
- **Purpose:** Historical documentation and deprecated files
- **Contents:**
  - Old versions of documentation
  - Deprecated guides
  - Legacy implementation notes
- **Best For:** Historical reference only
- **Access:** Browse directory for specific needs

---

## 🎓 Learning Paths

### Path 1: New User (First-Time Setup)
1. [WHAT_IS_CRASHLENS.md](#what_is_crashlensmd) (30 min)
2. [QUICKSTART.md](#quickstartmd) (10 min)
3. [CLI_COMMAND_REFERENCE.md](#cli_command_referencemd) (reference)
4. Try it: `crashlens scan --demo`

**Total Time:** ~45 minutes

---

### Path 2: CI/CD Integration
1. [NON-INTERACTIVE-GUIDE.md](#non-interactive-guidemd) (15 min)
2. [GUARD.md](#guardmd) (25 min)
3. [FILE_HANDLING_MANUAL.md](#file_handling_manualmd) (20 min)
4. Set up: GitHub Actions workflow

**Total Time:** ~1 hour

---

### Path 3: Production Monitoring
1. [OBSERVABILITY.md](#observabilitymd) (35 min)
2. [PROMETHEUS_GRAFANA_SETUP.md](#prometheus_grafana_setupmd) (20 min)
3. [GRAFANA_SETUP.md](#grafana_setupmd) (15 min)
4. [HTTP_SERVER_SECURITY.md](#http_server_securitymd) (10 min)
5. Deploy: Prometheus + Grafana + CrashLens metrics

**Total Time:** ~1.5 hours

---

### Path 4: Advanced Policy Engineering
1. [GUARD.md](#guardmd) (25 min)
2. [USER_MANUAL.md](#user_manualmd) - Policy section (30 min)
3. [BOOLEAN_LOGIC_IMPLEMENTATION.md](#boolean_logic_implementationmd) (10 min)
4. Create: Custom policy YAML

**Total Time:** ~1 hour

---

### Path 5: Understanding Detectors (Technical Deep Dive)
1. [../crashlens/detectors/detectors.md](#detectors-documentation) (50 min)
2. [WHAT_IS_CRASHLENS.md](#what_is_crashlensmd) - Detection section (10 min)
3. [architecture-flow.md](#architecture-flowmd) (20 min)
4. Review: Detector source code

**Total Time:** ~1.5 hours

---

### Path 6: Privacy & Compliance
1. [PII_REMOVAL_GUIDE.md](#pii_removal_guidemd) (20 min)
2. [../SECURITY.md](#securitymd) (5 min)
3. [WHAT_IS_CRASHLENS.md](#what_is_crashlensmd) - Privacy section (5 min)
4. [HTTP_SERVER_SECURITY.md](#http_server_securitymd) (10 min)
5. Configure: PII removal + secure metrics

**Total Time:** ~40 minutes

---

### Path 7: Contributing/Development
1. [../CONTRIBUTING.md](#contributingmd) (15 min)
2. [architecture-flow.md](#architecture-flowmd) (20 min)
3. [DEVELOPMENT_RETROSPECTIVE_100_COMMITS.md](#development_retrospective_100_commitsmd) (10 min)
4. Review: Implementation summaries (STEP_*.md)
5. Set up: Development environment

**Total Time:** ~1-2 hours

---

## 📊 Documentation Statistics

| Category | Files | Total Lines | Estimated Read Time |
|----------|-------|-------------|---------------------|
| **Getting Started** | 4 | ~3,200 | 1-1.5 hours |
| **Command Reference** | 2 | ~1,100 | Reference |
| **Policy & Guard** | 3 | ~1,000 | 45-60 minutes |
| **Observability** | 5 | ~1,600 | 1-1.5 hours |
| **Detectors** | 1 | 1,248 | 50 minutes |
| **Privacy & Security** | 2 | ~300 | 30 minutes |
| **Input/Data** | 3 | ~500 | 45 minutes |
| **Integrations** | 4 | ~600 | 45-60 minutes |
| **Architecture** | 3 | ~400 | 45 minutes |
| **Implementation** | 12 | ~2,000 | 2-3 hours |
| **Validation** | 5 | ~800 | 1-1.5 hours |
| **Bug Fixes** | 2 | ~300 | 30 minutes |
| **Release** | 3 | ~400 | 30 minutes |

**Total:** 49 files | ~13,448 lines | ~10-12 hours (full read)

---

## 🔍 Finding What You Need

### By Task

| Task | Primary Document | Supporting Documents |
|------|-----------------|---------------------|
| **Install CrashLens** | QUICKSTART.md | USER_MANUAL.md |
| **Run first scan** | QUICKSTART.md | CLI_COMMAND_REFERENCE.md |
| **Set up CI/CD** | NON-INTERACTIVE-GUIDE.md | GUARD.md |
| **Create policies** | GUARD.md | USER_MANUAL.md |
| **Monitor production** | OBSERVABILITY.md | PROMETHEUS_GRAFANA_SETUP.md |
| **Remove PII** | PII_REMOVAL_GUIDE.md | FILE_HANDLING_MANUAL.md |
| **Send to Slack** | SLACK_INTEGRATION.md | REPORT_COMMAND.md |
| **Understand detectors** | detectors.md | WHAT_IS_CRASHLENS.md |
| **Configure inputs** | FILE_HANDLING_MANUAL.md | LOG_SETUP.md |
| **Troubleshoot** | USER_MANUAL.md | CLI_COMMAND_REFERENCE.md |

### By Role

| Role | Recommended Reading |
|------|---------------------|
| **Developer** | QUICKSTART.md, CLI_COMMAND_REFERENCE.md, detectors.md |
| **DevOps/SRE** | OBSERVABILITY.md, PROMETHEUS_GRAFANA_SETUP.md, NON-INTERACTIVE-GUIDE.md |
| **Security** | PII_REMOVAL_GUIDE.md, SECURITY.md, HTTP_SERVER_SECURITY.md |
| **Data Scientist** | WHAT_IS_CRASHLENS.md, detectors.md, FILE_HANDLING_MANUAL.md |
| **Engineering Manager** | WHAT_IS_CRASHLENS.md, OBSERVABILITY.md, RELEASE_ROADMAP.md |
| **Contributor** | CONTRIBUTING.md, architecture-flow.md, STEP_*.md |

---

## 🆘 Getting Help

### In-Document Search

Most documentation files have:
- **Table of Contents** (ToC) at the top
- **Section headers** for easy navigation
- **Code examples** with syntax highlighting
- **Tips & warnings** for common pitfalls

### External Resources

- **GitHub Issues:** https://github.com/Crashlens/crashlens/issues
- **Discussions:** https://github.com/Crashlens/crashlens/discussions
- **Contributing:** See CONTRIBUTING.md
- **Security:** See SECURITY.md

### Quick Reference Commands

```bash
# Get help on any command
crashlens --help
crashlens scan --help
crashlens guard --help

# Demo mode (no logs required)
crashlens scan --demo

# Generate test data
crashlens simulate --output test-logs.jsonl --count 100

# Validate configuration
crashlens validate-metrics-config metrics-config.yaml
```

---

## 📝 Documentation Maintenance

This index is manually maintained. When adding new documentation:

1. Add the file to the appropriate category section
2. Include file size (lines) if substantial (>100 lines)
3. Write a clear purpose statement
4. List key contents (3-5 bullet points)
5. Specify "Best For" use case
6. Estimate read time
7. Update statistics section
8. Update learning paths if relevant

**Last Full Audit:** 2025-11-09  
**Next Scheduled Review:** 2025-12-01

---

## 🎯 Version Notes

### What's New in 2.10.1 Documentation

- ✨ **NEW:** CLI_COMMAND_REFERENCE.md (1,016 lines) - Complete command reference
- ✨ **NEW:** detectors.md enhanced (379→1,248 lines) - Comprehensive detector algorithms
- ✨ **ENHANCED:** OBSERVABILITY.md - Production-grade Prometheus integration
- ✨ **ENHANCED:** GUARD.md - Boolean logic and advanced policies
- 📚 **ORGANIZED:** All 49 documentation files indexed and categorized

### Upcoming Documentation (Roadmap)

- [ ] Video tutorials for key workflows
- [ ] Interactive examples (Jupyter notebooks)
- [ ] API documentation (if API endpoints added)
- [ ] Multi-language support (translations)
- [ ] Community cookbook (user-contributed recipes)

---

**Happy CrashLens-ing! 🚀**

For questions or suggestions about this documentation index, please open an issue on GitHub.
