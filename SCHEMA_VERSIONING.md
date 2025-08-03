# Schema Contract Management

CrashLens now supports version-aware parsing with schema contract validation to ensure robust handling of evolving Langfuse log formats.

## Features

### 🏗️ Version-Aware CLI

Use the `--log-format` flag to specify the Langfuse schema version:

```bash
# Use Langfuse v1 schema (default)
crashlens scan logs.jsonl --log-format langfuse-v1

# Use Langfuse v2 schema (when available)
crashlens scan logs.jsonl --log-format langfuse-v2

# Error handling for unsupported formats
crashlens scan logs.jsonl --log-format unknown-format
# Output: ❌ Error: Unsupported log format: unknown-format
```

### 🔍 Schema Contract Validation

The parser automatically validates logs against defined schema contracts:

```python
from crashlens.parsers.langfuse import LangfuseParser

# Create version-aware parser
parser = LangfuseParser(default_schema="v1", verbose=True)

# Parser will validate against v1 contract:
# - Required fields: ["traceId"]
# - Optional fields: ["model", "prompt_tokens", "completion_tokens"]
# - Known fields: All fields in the v1 schema specification
```

### 🧪 Contract Break Detection

Automated tests detect schema changes that could break parsing:

```bash
# Run schema contract tests
python tests/test_schema_contracts.py

# Tests verify:
# ✅ Required fields are present
# ✅ Field types are correct
# ✅ Nested structures are valid
# ✅ Contract break scenarios are detected
```

## Schema Evolution Support

### Adding New Schema Versions

```python
# Add a new schema version programmatically
parser.add_schema_contract(
    version="v2",
    required_fields=["traceId", "userId"],
    warn_fields=["model", "cost"],
    all_known_fields={"traceId", "userId", "model", "cost", "timestamp"}
)

# Validate the new contract
if parser.validate_schema_contract("v2"):
    print("v2 schema is valid!")
```

### Backwards Compatibility

- Parser automatically falls back to v1 for unknown schema versions
- Existing logs continue to work without modification
- Warnings are logged for unsupported schema versions

## Testing Schema Contracts

### Test Fixtures

Place test log files in `tests/fixtures/`:

```
tests/
├── fixtures/
│   ├── langfuse_latest_log.json      # Single log for basic testing
│   └── langfuse_latest_logs.jsonl    # Multiple logs for comprehensive testing
└── test_schema_contracts.py          # Contract validation tests
```

### Contract Tests

The test suite validates:

1. **Required Fields**: Must be present for parsing to succeed
2. **Field Types**: Critical fields have expected data types
3. **Nested Structures**: Complex objects follow expected patterns
4. **Schema Evolution**: New fields are detected and logged
5. **Break Detection**: Missing or changed fields trigger failures

### Example Test Output

```
🧪 Running Schema Contract Break Detection Tests
============================================================
Testing single log contract fields...
✅ Single log contract validation passed
Testing all logs contract validation...
✅ All 3 logs passed contract validation
Testing critical field types...
✅ Critical field types validation passed
Testing schema evolution detection...
ℹ️  No new fields detected - schema is stable
✅ Schema evolution detection completed
Testing contract break detection...
✅ Correctly detected contract break: Required field 'traceId' missing from log
✅ Correctly detected type change: traceId must be string
============================================================
🎉 All schema contract tests passed!
```

## Usage Examples

### CLI with Version Specification

```bash
# Standard usage with v1 schema
crashlens scan demo-logs.jsonl --log-format langfuse-v1

# Future v2 usage
crashlens scan new-logs.jsonl --log-format langfuse-v2

# Demo with specific schema
crashlens scan --demo --log-format langfuse-v1
```

### Programmatic Usage

```python
from crashlens.parsers.langfuse import LangfuseParser

# Create parser with specific schema version
parser = LangfuseParser(
    default_schema="v1",
    verbose=True,
    fail_fast=False
)

# Parse logs with schema validation
traces = parser.parse_file("logs.jsonl")

# Check available schema versions
print(f"Available schemas: {parser.get_available_schema_versions()}")

# Validate schema contracts
for version in parser.get_available_schema_versions():
    is_valid = parser.validate_schema_contract(version)
    print(f"Schema {version}: {'✅ Valid' if is_valid else '❌ Invalid'}")
```

## Benefits

1. **Future-Proof**: Easy addition of new schema versions without breaking changes
2. **Robust Validation**: Automatic detection of schema contract violations
3. **Clear Error Messages**: Detailed feedback when schema validation fails
4. **Backwards Compatibility**: Existing workflows continue to work unchanged
5. **Test Coverage**: Comprehensive validation of schema assumptions

This schema contract system ensures CrashLens can evolve with Langfuse's data format changes while maintaining reliability and providing clear feedback when issues occur.
