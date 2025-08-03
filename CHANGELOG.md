# Changelog

All notable changes to CrashLens will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2025-08-04 🔥 **MAJOR RELEASE: Policy-Only Architecture**

### 🚀 **BREAKING CHANGES**
- **Complete CLI rewrite** - New command structure with `crashlens scan`, `crashlens validate-policy`, `crashlens info`
- **Legacy detector removal** - All hardcoded Python detector classes eliminated
- **YAML-first enforcement** - 100% policy-driven detection system
- **New CLI flags** - Updated command syntax and options

### ✅ **Added**
- **🔧 YAML Policy Engine** - Complete policy-driven detection system
- **📋 Policy Validation** - `crashlens validate-policy` command for YAML syntax checking
- **📊 Enhanced Info Command** - Detailed log file statistics with model and cost analysis
- **🔐 License Integration** - Premium feature gating through license system
- **🎯 Dry Run Mode** - `--dry-run` flag for testing without generating reports
- **📄 Multiple Output Formats** - JSON, Markdown, Slack, Summary formats
- **⚡ Flexible Field Matching** - Support for nested fields like `input.model`, `usage.prompt_tokens`
- **🧠 Smart Model Detection** - Enhanced parsing for different log formats
- **🔍 Verbose Logging** - `--verbose` flag for detailed execution information

### 🗑️ **Removed (Legacy Code Elimination)**
- **Deleted**: `fallback_failure.py` - replaced by YAML rule `fallback_failure_expensive`
- **Deleted**: `fallback_storm.py` - replaced by YAML rule `fallback_storm_detection`  
- **Deleted**: `overkill_model_detector.py` - replaced by YAML rule `overkill_expensive_model`
- **Deleted**: `retry_loops.py` - replaced by YAML rule `retry_loop_detection`
- **Deleted**: `retry_fallback_detector.py` - replaced by YAML rules
- **Deleted**: `SuppressionEngine` class - replaced by `PolicySuppressionEngine`
- **Deleted**: `DETECTOR_PRIORITY` constants and legacy suppression logic
- **Deleted**: All detector imports and instantiation code from CLI

### 🔄 **Changed**
- **CLI Commands**: `crashlens policy-check` → `crashlens scan --policy`
- **Output Flags**: `--output-format` → `--format`
- **Configuration**: All detection rules now in `modern-policy.yaml`
- **Architecture**: Detector classes → Policy Engine (single point of enforcement)
- **Error Handling**: Enhanced error messages with actionable suggestions
- **Performance**: Single policy evaluation pass vs multiple detector runs

### 📋 **Policy Rule Coverage**
- **Cost Control**: `high_cost_request`, `overkill_expensive_model`, `excessive_tokens`
- **Security**: `unauthorized_model_usage`, `dev_expensive_model_block`  
- **Reliability**: `retry_loop_detection`, `fallback_failure_expensive`
- **Premium Features**: `premium_cost_analysis`, `model_efficiency_analysis`, `cross_request_patterns`, `fallback_storm_detection`

### 🧪 **Validation & Testing**
- ✅ Policy validation with 10 comprehensive rules
- ✅ Detection testing with demo logs (3 violations found)
- ✅ All output formats working correctly
- ✅ License gating for premium features
- ✅ Zero Python syntax errors

### 📚 **Documentation Updates**
- Updated all CLI examples in README files
- Fixed GitHub workflow commands  
- Updated troubleshooting guides
- Added policy configuration examples

---

## [2.0.0] - 2025-01-04 **Policy Engine Introduction**

### Added
- **YAML Policy Engine** - Initial implementation of policy-driven detection
- **License System** - Premium feature gating and validation
- **Modern Policy Configuration** - YAML-based rule definitions
- **Enhanced CLI** - Improved command structure and options

### Changed
- **Detection Architecture** - Hybrid approach with both detectors and policies
- **Configuration Management** - YAML-first policy definitions

---

## [1.0.0] - 2024-01-15 **Legacy Detector System**

### Added
- **GitHub Action for automated log validation** in CI/CD pipelines
- **Schema contract validation** for Langfuse log formats (v1 and v2)
- **Contract check CLI flag** (`--contract-check`) for early validation
- **JSON output support** (`--output json`) for automation and tooling
- **Contract info command** (`--contract-info`) to see schema requirements
- **Comprehensive error reporting** with line numbers and specific violations
- **Multi-file glob pattern support** for validating multiple log files
- **Schema version awareness** with backward compatibility
- **Production-grade error handling** and logging
- **PII scrubbing utilities** for sensitive data protection

### Changed
- **Rewritten LangfuseParser** for production robustness and extensibility
- **Enhanced CLI interface** with clearer commands and better UX
- **Improved error messages** with actionable guidance for fixing violations
- **Optimized performance** for handling large log files efficiently

### Technical Details
- **Python 3.10+ support** with modern type hints and async capabilities
- **Click-based CLI** with comprehensive help and validation
- **Structured logging** with configurable levels and formatters
- **Schema validation engine** with version-aware contract checking
- **GitHub Actions integration** with proper inputs, outputs, and branding

### Documentation
- **Comprehensive README** with quick start and advanced examples
- **GitHub Action documentation** with real-world use cases
- **API reference** for all CLI commands and options
- **Troubleshooting guide** for common issues and solutions
- **Contributing guidelines** for community participation

### Testing
- **Comprehensive test suite** with valid and invalid log samples
- **CI/CD validation** with automated contract checking
- **Edge case handling** for malformed files and missing data
- **Performance testing** with large log file scenarios

### Examples
- **Sample log files** demonstrating valid and invalid formats
- **GitHub workflow examples** for different team setups
- **Integration patterns** with Slack notifications and budget enforcement
- **Local development setup** for testing before deployment

---

## [0.9.0] - 2024-01-10 (Pre-release)

### Added
- Initial implementation of contract validation system
- Basic CLI interface for log scanning
- Langfuse parser with schema awareness
- Core detection engines for common issues

### Internal
- Project structure and development environment setup
- Initial test framework and sample data
- Documentation framework and README structure

---

## Future Releases

### Planned for v3.1.0
- **Enhanced Policy Syntax** - More advanced matching operators and conditions
- **Policy Templates** - Pre-built policy sets for common use cases  
- **Cross-Trace Analysis** - Advanced pattern detection across multiple traces
- **Performance Optimizations** - Faster processing for large log files
- **Integration Improvements** - Better Slack, Teams, and webhook support

### Planned for v3.2.0
- **OpenAI Log Format Support** - Native support for OpenAI API logs
- **Custom Field Definitions** - User-defined field mappings and transformations
- **Policy Inheritance** - Hierarchical policy configurations
- **Real-time Monitoring** - Live log stream analysis

### Under Consideration
- **VS Code Extension** - IDE integration for policy development
- **Web Dashboard** - GUI for policy management and violation analysis
- **Machine Learning Insights** - AI-powered policy recommendations
- **Multi-cloud Deployment** - Kubernetes, Docker, and cloud-native support

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:
- How to report bugs and request features
- Development setup and testing procedures
- Code style guidelines and review process
- Release coordination and version management

## Support

- **GitHub Issues**: [Report bugs and request features](https://github.com/crashlens/crashlens/issues)
- **Discussions**: [Community help and questions](https://github.com/crashlens/crashlens/discussions)
- **Documentation**: [Complete user guide and API reference](https://github.com/crashlens/crashlens/blob/main/README.md)
- **Email**: [Direct support for enterprise users](mailto:support@crashlens.dev)
