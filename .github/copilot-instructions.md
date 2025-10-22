# CrashLens - AI Coding Agent Instructions

## 🎯 Project Overview

**CrashLens** is a privacy-first AI token waste detection CLI tool that analyzes Langfuse JSONL logs to identify and prevent costly patterns in LLM API usage. It runs 100% locally with no data egress.

**Core Mission**: Detect retry loops, fallback storms, model overkill, and fallback failures before they burn through your AI budget.

**Tech Stack**: Python 3.12+, Poetry, Click CLI framework, pytest

**Entry Point**: `crashlens/cli.py` (2687 lines) → `@click.group()` decorator pattern

---

## 🏗️ Architecture Overview

### Pipeline Pattern (Chain of Responsibility)
```
User Command (Click CLI)
    ↓
Input Source (file/stdin/clipboard/Langfuse API/Helicone API)
    ↓
LangfuseParser (JSONL → normalized traces grouped by traceId)
    ↓
Detector Pipeline (4 parallel detectors with priority-based suppression)
    ├─ RetryLoopDetector (exact string matching, exponential backoff detection)
    ├─ FallbackStormDetector (cascade detection within time windows)
    ├─ OverkillModelDetector (model vs. task suitability scoring)
    └─ FallbackFailureDetector (failed fallback chain detection)
    ↓
Policy Engine (optional YAML rule evaluation)
    ├─ PolicyRule.evaluate() per log entry (hot loop)
    └─ Constant-memory stats collection (conditional, <10% overhead)
    ↓
Formatters (multiple output formats)
    ├─ MarkdownFormatter (readable reports)
    ├─ JSONFormatter (detailed output by category)
    └─ SlackFormatter (Slack block kit messages)
    ↓
Output (file/stdout/Slack webhook)
```

### Module Organization
```
crashlens/
├── cli.py                          # Main entry point, all Click commands
├── parsers/langfuse.py            # JSONL parsing with schema validation
├── detectors/                     # Waste pattern detection
│   ├── retry_loops.py             # Exact string matching, exponential backoff
│   ├── fallback_storm.py          # Cascade detection in time windows
│   ├── overkill_model_detector.py # Model suitability scoring
│   └── fallback_failure.py        # Failed fallback chain detection
├── policy/                        # Rule evaluation system
│   ├── engine.py                  # PolicyEngine with hot loop instrumentation
│   └── templates/                 # Reusable YAML policy templates
├── formatters/                    # Output rendering
│   ├── markdown_formatter.py      # Human-readable Markdown
│   ├── json_formatter.py          # Structured JSON with category breakdown
│   └── slack_formatter.py         # Slack Block Kit messages
├── pii/                           # Privacy-first PII removal
│   ├── sanitizer.py               # Email, phone, SSN scrubbing
│   └── patterns.py                # PII regex patterns
├── config/                        # YAML config schemas
└── utils/                         # Shared utilities
```

---

## 🔑 Key Conventions

### 1. Click CLI Pattern
**Always use decorators for commands:**
```python
@click.command()
@click.option('--format', type=click.Choice(['slack', 'markdown', 'json']), default='slack')
@click.option('--config', type=click.Path(exists=True, path_type=Path), help="Custom config")
@click.argument('logfile', type=click.Path(exists=True, path_type=Path), required=False)
def scan(logfile: Optional[Path], format: str, config: Optional[Path]) -> None:
    """Scan logs for token waste patterns."""
    # Implementation
```

**Error handling convention:**
```python
if error_condition:
    click.echo(click.style(f"❌ Error: {message}", fg="red"), err=True)
    sys.exit(1)
```

### 2. Detector Interface
**All detectors must implement:**
```python
class MyDetector:
    def __init__(self, threshold: int, time_window_minutes: int):
        """Configure detection parameters."""
        pass
    
    def detect(
        self,
        traces: Dict[str, List[Dict[str, Any]]],  # traceId -> list of records
        model_pricing: Optional[Dict[str, Any]] = None,
        already_flagged_ids: Optional[set] = None,  # For suppression
    ) -> List[Dict[str, Any]]:
        """
        Returns list of detection dicts with structure:
        {
            'trace_id': str,
            'detector': str,  # Human-readable name
            'waste_cost': float,
            'waste_tokens': int,
            'severity': 'high' | 'medium' | 'low',
            'description': str,
            'suggestion': str,
            'records': List[Dict[str, Any]],  # Relevant log entries
            # Detector-specific fields...
        }
        """
        detections = []
        # Detection logic
        return detections
```

**Suppression Pattern** (avoid double-counting):
```python
if trace_id in already_flagged_ids:
    continue  # Higher-priority detector already claimed this trace
```

### 3. Policy YAML Format
**Standard structure:**
```yaml
version: 1
global:
  max_violations_per_rule: 100  # Circuit breaker

rules:
  - id: excessive_retries
    description: "Block traces with >3 retries"
    match:
      retry_count: ">3"                      # Operators: >, >=, <, <=, ==, in:[...], regex:...
      metadata.fallback_attempted: true
      usage.prompt_tokens: ">= 1"
    action: fail                             # fail | warn | block
    severity: critical                       # critical | high | medium | low
    suggestion: "Implement exponential backoff and circuit breaker"
```

**Dot notation** for nested fields: `usage.prompt_tokens`, `metadata.team`, `error.code`

**AND logic** within each `match` block (all conditions must be true)

### 4. Constant-Memory Principles
**CRITICAL for production metrics:**
- Use `defaultdict` with fixed structure (no unbounded lists)
- Aggregate stats per rule/detector (not per trace)
- Boolean flags for conditional instrumentation (zero overhead when disabled)

**Example from PolicyEngine:**
```python
# Initialize with fixed structure
self._rule_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {
    'total_time': 0.0,
    'call_count': 0,
    'avg_time': 0.0,
    'max_time': 0.0
})

# Conditional timing (only if enabled)
if self._collect_stats:
    start = time.perf_counter()
    violation = rule.evaluate(log_entry, line_number)
    elapsed = time.perf_counter() - start
    self._rule_stats[rule_id]['total_time'] += elapsed
    self._rule_stats[rule_id]['call_count'] += 1
else:
    violation = rule.evaluate(log_entry, line_number)
```

### 5. JSONL Parsing Conventions
**Schema validation with LangfuseParser:**
```python
parser = LangfuseParser(verbose=False, fail_fast=False, default_schema="v1")
traces = parser.parse_file(Path("logs.jsonl"))
# Returns: Dict[str, List[Dict[str, Any]]]  (traceId -> records)
```

**Required fields (v1 schema):**
- `traceId` (mandatory)
- `model`, `prompt_tokens`, `completion_tokens` (warn if missing)

**Known fields** (all others trigger warnings for schema drift detection):
- Core: `traceId`, `startTime`, `endTime`, `level`, `name`, `cost`
- Usage: `prompt_tokens`, `completion_tokens`
- Metadata: `metadata.fallback_attempted`, `metadata.route`, `metadata.team`

### 6. Testing Patterns
**Use Click's CliRunner for CLI tests:**
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

**pytest conventions:**
- Test files: `tests/test_*.py`
- Test classes: `class Test<Feature>:`
- Test methods: `def test_<behavior>(self):`
- Fixtures in `setup_method()` / `teardown_method()`

---

## 🔄 Critical Workflows

### Development Setup
```bash
# Install dependencies
poetry install

# Activate virtualenv (automatic with poetry run)
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

### Running the CLI
```bash
# Demo mode (built-in sample data)
poetry run crashlens scan --demo

# Scan local file
poetry run crashlens scan sample-logs/demo-logs.jsonl --format markdown

# Policy check
poetry run crashlens policy-check logs.jsonl --policy-file policies/retry-loop-detector.yaml

# Fetch from Langfuse API
poetry run crashlens scan --from-langfuse --hours-back 24 --limit 1000

# PII removal
poetry run crashlens pii-remove logs.jsonl --output clean-logs.jsonl
```

### CI/CD Integration
**GitHub Actions (`.github/workflows/ci.yml`):**
- Triggers: `push` to `main` or `develop` branches only (PR triggers removed)
- Jobs: `lint` (black/flake8/isort), `type-check` (mypy), `test` (pytest matrix: 3.10/3.11/3.12 on ubuntu/windows/macos)
- Poetry caching: `.venv` cached by `poetry.lock` hash

**Schema contract validation (`.github/workflows/schema-contract-check.yml`):**
- Triggers: `push` with path filters, `workflow_dispatch`
- Validates Langfuse JSONL schema against known field contracts

### Debugging Tips
**Enable verbose logging:**
```python
parser = LangfuseParser(verbose=True, fail_fast=True)
```

**Check parser errors:**
```bash
crashlens scan logs.jsonl 2>&1 | grep "WARNING\|ERROR"
```

**Test single detector:**
```python
detector = RetryLoopDetector(max_retries=3, time_window_minutes=5)
detections = detector.detect(traces, model_pricing, already_flagged_ids=set())
```

---

## 🔌 Integration Points

### 1. Langfuse API Integration
**Client:** `crashlens/langfuse_client.py`
```python
# Fetch traces from Langfuse
traces = fetch_langfuse_traces(hours_back=24, limit=1000)
# Returns: List[Dict[str, Any]] (raw Langfuse trace objects)
```

### 2. Slack Webhooks
**Formatter:** `crashlens/formatters/slack_formatter.py`
```python
# Send report to Slack
slack_formatter = SlackFormatter()
blocks = slack_formatter.format(detections, traces, summary_only=False)
# POST to webhook URL
```

**Slack command:**
```bash
crashlens slack notify --webhook-url $SLACK_WEBHOOK --report report.md
```

### 3. Policy Templates
**Built-in templates** (in `crashlens/policy/templates/`):
- `retry-loop-prevention`: Detect excessive retries
- `model-overkill-detection`: Flag expensive models on simple tasks
- `fallback-chain-monitoring`: Track fallback patterns
- `all`: Combined policy set

**Usage:**
```bash
crashlens scan logs.jsonl --policy-template retry-loop-prevention
```

**Custom policies:**
```bash
crashlens scan logs.jsonl --policy-file my-policy.yaml
```

### 4. Cost Tracking (Model Pricing)
**Config file:** `custom-pricing.yaml`
```yaml
models:
  gpt-4:
    prompt_token_cost: 0.00003
    completion_token_cost: 0.00006
  gpt-3.5-turbo:
    prompt_token_cost: 0.0000015
    completion_token_cost: 0.000002
```

**Usage:**
```bash
crashlens scan logs.jsonl --config custom-pricing.yaml
```

---

## 🎯 Common Tasks

### Adding a New Detector
1. **Create detector file** in `crashlens/detectors/my_detector.py`:
   ```python
   class MyDetector:
       def __init__(self, threshold: int):
           self.threshold = threshold
       
       def detect(self, traces, model_pricing=None, already_flagged_ids=None):
           detections = []
           for trace_id, records in traces.items():
               if trace_id in already_flagged_ids:
                   continue
               # Detection logic
               if condition:
                   detections.append({
                       'trace_id': trace_id,
                       'detector': 'My Detector',
                       'waste_cost': cost,
                       'waste_tokens': tokens,
                       'severity': 'high',
                       'description': '...',
                       'suggestion': '...',
                       'records': records
                   })
           return detections
   ```

2. **Import in `cli.py`**:
   ```python
   from .detectors.my_detector import MyDetector
   ```

3. **Add to detector pipeline** in `scan()` command:
   ```python
   detectors = [
       retry_loop_detector,
       fallback_storm_detector,
       overkill_model_detector,
       MyDetector(threshold=10),  # Add here
   ]
   ```

4. **Test with pytest**:
   ```python
   def test_my_detector():
       detector = MyDetector(threshold=10)
       traces = {'trace1': [{'model': 'gpt-4', ...}]}
       detections = detector.detect(traces)
       assert len(detections) > 0
   ```

### Adding a New CLI Command
1. **Define command** in `crashlens/cli.py`:
   ```python
   @cli.command()
   @click.option('--option', type=str, help="Description")
   @click.argument('arg', type=click.Path(exists=True, path_type=Path))
   def mycommand(option: str, arg: Path) -> None:
       """Command description."""
       # Implementation
   ```

2. **Register with CLI group**:
   ```python
   cli.add_command(mycommand)
   ```

3. **Test with CliRunner**:
   ```python
   def test_mycommand():
       runner = CliRunner()
       result = runner.invoke(mycommand, ['--option', 'value', 'arg'])
       assert result.exit_code == 0
   ```

### Adding a Policy Template
1. **Create YAML file** in `crashlens/policy/templates/my-policy.yaml`:
   ```yaml
   version: 1
   rules:
     - id: my_rule
       description: "Detect pattern X"
       match:
         field: "condition"
       action: warn
       severity: medium
       suggestion: "Do this instead"
   ```

2. **Reference in CLI**:
   ```bash
   crashlens scan logs.jsonl --policy-template my-policy
   ```

### Instrumenting Hot Loops (Metrics)
**Follow constant-memory principles:**
```python
# Add flag to __init__
self._collect_stats = False
self._stats = defaultdict(lambda: {'count': 0, 'time': 0.0})

# Method to enable
def enable_stats_collection(self):
    self._collect_stats = True

# Conditional instrumentation
if self._collect_stats:
    start = time.perf_counter()
    result = expensive_operation()
    self._stats['operation']['time'] += time.perf_counter() - start
    self._stats['operation']['count'] += 1
else:
    result = expensive_operation()
```

**Benchmark overhead:**
```python
# scripts/benchmark_stats_overhead.py
# Run with/without stats, ensure <10% overhead
```

---

## 🚨 Important Constraints

### Memory Management
- **NEVER use unbounded lists** in hot loops (e.g., storing all rule timings)
- **Use fixed-structure defaultdicts** for aggregation
- **Profile memory** with `memory_profiler` for large log files (1M+ traces)

### Privacy-First Design
- **All analysis runs locally** (no API calls to external services except user-configured Langfuse/Helicone)
- **PII scrubbing** available via `crashlens pii-remove`
- **Summary-only mode** suppresses trace IDs for safe internal sharing

### Performance Constraints
- **Hot loop:** `PolicyEngine.evaluate_log_entry()` → `rule.evaluate()`
- **Target:** <10% overhead for stats collection (measured with `perf_counter`)
- **Fail-fast mode:** Stop on first policy violation per trace (avoid noise)

### Code Quality Standards
- **Type hints** on all functions (enforced by mypy)
- **Black formatting** (line length 88)
- **Flake8 linting** (E203, W503 ignored)
- **isort** for import sorting
- **pytest** for all new features (aim for >80% coverage)

---

## 📚 Reference Documentation

### Key Files to Read First
1. `crashlens/cli.py` (2687 lines) - Main CLI entry point
2. `crashlens/policy/engine.py` (320 lines) - Policy evaluation hot loop
3. `crashlens/parsers/langfuse.py` (564 lines) - JSONL parsing with schema validation
4. `docs/architecture-flow.md` - Sequence diagrams for scan/policy-check flows
5. `docs/COMMAND-REFERENCE.md` - Complete CLI command documentation

### External Dependencies
- **Click 8.2.1+**: CLI framework (decorators, options, arguments)
- **PyYAML 6.0.2+**: Config/policy YAML parsing
- **Jinja2 3.1.6+**: Policy template rendering
- **orjson 3.10.18+**: Fast JSON parsing (JSONL performance)
- **Rich 14.0.0+**: Terminal output formatting
- **prometheus-client 0.23.1+**: Metrics collection (Phase 1)

### Schema Contracts
- **Langfuse v1 schema** (required field: `traceId`)
- **Detection output schema** (see Detector Interface section)
- **Policy YAML schema** (see Policy YAML Format section)

---

## 🧩 Design Decisions Rationale

### Why Click over argparse?
- Cleaner decorator syntax
- Automatic help generation
- Built-in testing support (CliRunner)
- Better nested command groups

### Why JSONL over JSON?
- Streaming processing (handle large log files)
- Line-by-line error recovery (one bad line doesn't break entire file)
- Standard format for Langfuse exports

### Why exact string matching (not embeddings)?
- Privacy: No external API calls
- Speed: No embedding computation overhead
- Simplicity: Easy to debug and explain
- Accuracy: Deterministic matching (no false positives from similarity thresholds)

### Why priority-based suppression?
- Avoid double-counting waste (e.g., retry loop + fallback storm on same trace)
- Higher-priority detectors claim traces first
- Provides cleaner, non-duplicative reports

### Why constant-memory stats?
- Production-safe (no OOM risk on large log files)
- <10% overhead target (acceptable for monitoring)
- Fixed aggregation keys (rule ID, detector name, not trace ID)

---

## 🤝 Contributing Guidelines

### Before Making Changes
1. **Read relevant documentation** in `docs/` (especially `architecture-flow.md`)
2. **Check existing tests** to understand expected behavior
3. **Run full test suite** (`poetry run pytest tests/`)
4. **Lint and format** (`black`, `isort`, `flake8`, `mypy`)

### When Adding Features
1. **Write tests first** (TDD approach preferred)
2. **Update documentation** (`docs/COMMAND-REFERENCE.md`, this file)
3. **Add type hints** (required for mypy)
4. **Benchmark performance** if touching hot loops
5. **Update CHANGELOG** with user-facing changes

### Pull Request Checklist
- [ ] All tests pass (`poetry run pytest tests/`)
- [ ] Type checking passes (`poetry run mypy crashlens/`)
- [ ] Code formatted (`poetry run black crashlens/ tests/`)
- [ ] Imports sorted (`poetry run isort crashlens/ tests/`)
- [ ] Linting clean (`poetry run flake8 crashlens/ tests/`)
- [ ] Documentation updated (if applicable)
- [ ] Benchmark results included (if performance-critical)

---

## 🔮 Future Roadmap

### Phase 1: Prometheus Metrics Integration
- Add prometheus-client instrumentation
- Expose `/metrics` endpoint (optional HTTP server)
- Aggregate by detector type, rule ID, severity
- Grafana dashboard templates

### Phase 2: Advanced Detectors
- Semantic drift detection (prompt changes over time)
- Context window overflow detection
- Streaming response inefficiency detection

### Phase 3: CI/CD Enhancements
- GitHub Actions integration (policy-check in CI)
- Cost budget enforcement (fail builds on overspend)
- Slack notifications for policy violations

---

**Last Updated:** 2025-01-XX (update when making significant changes)
**Maintained By:** CrashLens Core Team
