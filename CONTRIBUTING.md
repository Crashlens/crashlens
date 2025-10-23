# Contributing to CrashLens

Thank you for your interest in contributing to CrashLens! This guide will help you get started.

## 🚀 Quick Start for Developers

### Prerequisites
- Python 3.12+
- Poetry (package manager)
- Git

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/Crashlens/crashlens.git
cd crashlens

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run tests
poetry run pytest tests/

# Type checking
poetry run mypy crashlens/ --ignore-missing-imports

# Code formatting
poetry run black crashlens/ tests/
poetry run isort crashlens/ tests/
poetry run flake8 crashlens/ tests/ --max-line-length=88 --extend-ignore=E203,W503
```

## 📁 Project Structure

```
crashlens/
├── crashlens/              # Main package
│   ├── cli.py             # CLI entry point (Click commands)
│   ├── parsers/           # JSONL parsing with schema validation
│   ├── detectors/         # Waste pattern detectors
│   ├── policy/            # Policy engine and rules
│   ├── formatters/        # Output formatters (markdown, JSON, Slack)
│   ├── observability/     # Prometheus metrics (Phase 2)
│   ├── config/            # Configuration schemas
│   ├── pii/               # PII removal utilities
│   └── utils/             # Shared utilities
├── tests/                 # Test suite
├── docs/                  # Documentation
├── policies/              # Policy templates
├── dashboards/            # Grafana dashboards
├── examples/              # Usage examples
└── sample-logs/           # Test data
```

## 🎯 Key Development Workflows

### Running the CLI

```bash
# Demo mode (built-in sample data)
poetry run crashlens scan --demo

# Scan local file
poetry run crashlens scan sample-logs/demo-logs.jsonl --format markdown

# Policy check
poetry run crashlens policy-check logs.jsonl --policy-file policies/retry-loop-detector.yaml

# With metrics (requires Prometheus)
poetry run crashlens scan logs.jsonl --push-metrics --pushgateway-url http://localhost:9091
```

### Running Tests

```bash
# Run all tests
poetry run pytest tests/

# Run specific test file
poetry run pytest tests/test_retry_loops.py

# Run with coverage
poetry run pytest tests/ --cov=crashlens --cov-report=html

# Run only unit tests (skip integration)
poetry run pytest tests/ -m "not integration"

# Run with verbose output
poetry run pytest tests/ -v
```

### Code Quality

```bash
# Format code (auto-fix)
poetry run black crashlens/ tests/
poetry run isort crashlens/ tests/

# Lint code
poetry run flake8 crashlens/ tests/ --max-line-length=88 --extend-ignore=E203,W503

# Type checking
poetry run mypy crashlens/ --ignore-missing-imports

# Run all quality checks at once
poetry run black crashlens/ tests/ && \
poetry run isort crashlens/ tests/ && \
poetry run flake8 crashlens/ tests/ --max-line-length=88 --extend-ignore=E203,W503 && \
poetry run mypy crashlens/ --ignore-missing-imports
```

## 📝 Code Conventions

### Click CLI Pattern

All CLI commands use Click decorators:

```python
@click.command()
@click.option('--format', type=click.Choice(['slack', 'markdown', 'json']), default='slack')
@click.argument('logfile', type=click.Path(exists=True, path_type=Path), required=False)
def scan(logfile: Optional[Path], format: str) -> None:
    """Scan logs for token waste patterns."""
    if error_condition:
        click.echo(click.style(f"❌ Error: {message}", fg="red"), err=True)
        sys.exit(1)
```

### Detector Interface

All detectors must implement:

```python
class MyDetector:
    def __init__(self, threshold: int):
        """Configure detection parameters."""
        pass
    
    def detect(
        self,
        traces: Dict[str, List[Dict[str, Any]]],
        model_pricing: Optional[Dict[str, Any]] = None,
        already_flagged_ids: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        """
        Returns list of detection dicts with structure:
        {
            'trace_id': str,
            'detector': str,
            'waste_cost': float,
            'waste_tokens': int,
            'severity': 'high' | 'medium' | 'low',
            'description': str,
            'suggestion': str,
            'records': List[Dict[str, Any]],
        }
        """
        detections = []
        # Detection logic
        return detections
```

### Testing Patterns

```python
from click.testing import CliRunner

def test_scan_command():
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create test files
        result = runner.invoke(scan, ['logs.jsonl', '--format', 'json'])
        assert result.exit_code == 0
        assert "No token waste" in result.output
```

### Type Hints

All functions must have type hints:

```python
def parse_logs(file_path: Path, verbose: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    """Parse JSONL logs."""
    traces: Dict[str, List[Dict[str, Any]]] = {}
    return traces
```

### Constant-Memory Principles

For production metrics and hot loops:

```python
# ✅ Good: Fixed structure
self._stats = defaultdict(lambda: {'count': 0, 'time': 0.0})

# ❌ Bad: Unbounded lists
self._all_timings = []  # Will cause OOM on large logs
```

## 🎨 Adding New Features

### Adding a New Detector

1. Create detector file in `crashlens/detectors/my_detector.py`
2. Implement the detector interface
3. Import in `cli.py` and add to detector pipeline
4. Write tests in `tests/test_my_detector.py`
5. Update documentation

### Adding a New CLI Command

1. Define command in `crashlens/cli.py` with `@cli.command()`
2. Register with CLI group
3. Test with CliRunner
4. Update `docs/COMMAND-REFERENCE.md`

### Adding a Policy Template

1. Create YAML in `crashlens/policy/templates/my-policy.yaml`
2. Follow policy YAML format
3. Document in policy README
4. Add tests

## 🧪 Testing Guidelines

### Test Organization

- Test files: `tests/test_*.py`
- Test classes: `class Test<Feature>:`
- Test methods: `def test_<behavior>(self):`
- Fixtures in `conftest.py`

### Coverage Requirements

- Aim for >80% code coverage
- All new features must have tests
- All bug fixes must have regression tests

### Manual Testing

For features that need manual validation:

```bash
# Test with demo logs
poetry run crashlens scan sample-logs/demo-logs.jsonl

# Test with real Langfuse export
poetry run crashlens scan your-logs.jsonl --format json

# Test policy enforcement
poetry run crashlens policy-check logs.jsonl --policy-file policies/retry-loop-detector.yaml
```

## 📚 Documentation

### Required Documentation

When adding features, update:

1. **README.md** - If user-facing feature
2. **CHANGELOG.md** - All changes
3. **docs/COMMAND-REFERENCE.md** - New CLI commands
4. **docs/OBSERVABILITY.md** - Metrics changes
5. **Docstrings** - All public functions/classes

### Documentation Style

```python
def my_function(arg1: str, arg2: int = 10) -> bool:
    """
    Brief one-line description.
    
    More detailed description if needed, explaining what the function
    does, any side effects, and important considerations.
    
    Args:
        arg1: Description of first argument
        arg2: Description of second argument with default
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When input validation fails
        
    Example:
        >>> my_function("test", 5)
        True
    """
```

## 🔄 Git Workflow

### Branching Strategy

- `main` - Production-ready code
- `develop` - Integration branch (if used)
- `feature/your-feature-name` - Feature branches
- `fix/issue-description` - Bug fix branches

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add per-rule sampling to metrics
fix: handle missing trace IDs in parser
docs: update observability guide
test: add integration tests for HTTP server
refactor: simplify detector pipeline
perf: optimize policy rule evaluation
```

### Pull Request Process

1. Create feature branch from `main`
2. Make changes with tests
3. Run all quality checks locally
4. Push and create PR
5. Wait for CI to pass
6. Request review
7. Address feedback
8. Merge when approved

### Pull Request Checklist

- [ ] All tests pass (`poetry run pytest tests/`)
- [ ] Type checking passes (`poetry run mypy crashlens/`)
- [ ] Code formatted (`poetry run black`, `poetry run isort`)
- [ ] Linting clean (`poetry run flake8`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No breaking changes (or documented)

## 🐛 Reporting Issues

### Bug Reports

Include:
- CrashLens version (`crashlens --version`)
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/stack traces
- Sample logs (if applicable, anonymized)

### Feature Requests

Include:
- Use case description
- Expected behavior
- Example usage
- Benefits to other users

## 🎯 Performance Guidelines

### Hot Loop Optimization

For code in critical paths (policy evaluation, metrics collection):

- Target: <10% overhead
- Use `time.perf_counter()` for benchmarking
- Profile with `memory_profiler` for large files
- Avoid unbounded data structures
- Use constant-memory aggregation

### Benchmarking

```bash
# Run performance benchmarks
poetry run python scripts/benchmark_policy_engine.py

# Profile memory
poetry run python -m memory_profiler crashlens/cli.py scan large-logs.jsonl
```

## 🔐 Security

- Never commit secrets or API keys
- Use environment variables for sensitive data
- Validate all user inputs
- Follow principle of least privilege
- Report security issues privately to maintainers

## 📞 Getting Help

- **Documentation**: Check `docs/` directory
- **Examples**: See `examples/` directory
- **Issues**: GitHub Issues for bugs/features
- **Discussions**: GitHub Discussions for questions

## 🙏 Recognition

Contributors will be recognized in:
- Release notes
- GitHub contributors page
- Project README (for significant contributions)

Thank you for contributing to CrashLens! 🚀
