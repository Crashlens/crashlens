# Changelog

All notable changes to CrashLens will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-15

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

### Planned for v1.1.0
- **OpenAI log format support** - Contract validation for OpenAI API logs
- **Custom schema definitions** - User-defined contract requirements
- **Batch processing improvements** - Faster validation for large datasets
- **Integration with popular MLOps platforms** - MLflow, Weights & Biases support

### Planned for v1.2.0
- **Real-time log streaming validation** - Live contract checking
- **Advanced reporting dashboard** - Web UI for validation results
- **Team management features** - Multi-user access and permissions
- **Enterprise security compliance** - SOC2, GDPR, HIPAA support

### Under Consideration
- **VS Code extension** - IDE integration for developer workflows
- **Webhook integrations** - Real-time notifications and triggers
- **Machine learning insights** - Predictive quality scoring
- **Multi-cloud deployment** - AWS, GCP, Azure native integrations

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
