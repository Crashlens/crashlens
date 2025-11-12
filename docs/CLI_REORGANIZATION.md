# CLI Reorganization (Phase 3)

## Overview

This document describes the CLI command reorganization implemented to improve consistency, reduce duplication, and provide better command structure.

## Changes Summary

### 1. Removed Duplicate PII Commands

**Problem**: Both `pii-clean` and `pii-remove` commands existed with identical functionality.

**Solution**:
- ✅ **Primary Command**: `crashlens pii-remove` (clearer name)
- ⚠️ **Deprecated**: `crashlens pii-clean` (forwards to `pii-remove` with deprecation warning)
- 🔒 **Backward Compatible**: Old command still works but shows warning

**Migration Guide**:
```bash
# OLD (deprecated, will be removed in v2.0)
crashlens pii-clean logs.jsonl

# NEW (recommended)
crashlens pii-remove logs.jsonl
```

---

### 2. Created Schema Command Group

**Problem**: Schema-related commands (`list-schemas`, `detect-schema`) were top-level, inconsistent with other command groups.

**Solution**: Created `schema` command group with subcommands:

```bash
# NEW STRUCTURE (recommended)
crashlens schema list              # List supported log formats
crashlens schema detect LOGFILE    # Auto-detect log schema

# OLD STRUCTURE (deprecated)
crashlens list-schemas             # Shows deprecation warning
crashlens detect-schema LOGFILE    # Shows deprecation warning
```

**Features**:
- Grouped related schema operations
- Clear namespace for schema detection tools
- Legacy commands still work with deprecation warnings

**Migration Guide**:
```bash
# List all supported schemas
crashlens schema list
crashlens schema list --stable-only

# Auto-detect schema
crashlens schema detect logs.jsonl
crashlens schema detect logs.jsonl --sample-size 20
```

---

### 3. Consolidated Config Command Group

**Problem**: `validate-metrics-config` was top-level, but `config smtp-example` was already a subcommand of `config` group.

**Solution**: Moved all config operations under unified `config` group:

```bash
# NEW STRUCTURE (recommended)
crashlens config validate CONFIG_FILE              # Validate any config type
crashlens config validate metrics.yaml --type metrics
crashlens config validate policy.yaml --type policy
crashlens config validate smtp.yaml --type smtp
crashlens config smtp-example                      # Generate SMTP template

# OLD STRUCTURE (deprecated)
crashlens validate-metrics-config metrics.yaml     # Shows deprecation warning
```

**Features**:
- Unified config validation for all types (metrics, policy, SMTP)
- Consistent command hierarchy
- Extended validation beyond just metrics
- Legacy command still works with deprecation warning

**Migration Guide**:
```bash
# Validate metrics configuration
crashlens config validate metrics.yaml
crashlens config validate metrics.yaml --type metrics --verbose

# Validate policy configuration
crashlens config validate my-policy.yaml --type policy

# Validate SMTP configuration (future)
crashlens config validate smtp.yaml --type smtp

# Generate SMTP example (unchanged)
crashlens config smtp-example --output my-smtp.yaml
```

---

## Complete Command Structure

### Top-Level Commands
```bash
crashlens scan LOGFILE              # Detect token waste patterns
crashlens guard LOGFILE             # Policy enforcement
crashlens pii-remove LOGFILE        # Remove PII from logs
crashlens report LOGFILE            # Generate cost digest
crashlens init                      # Setup wizard
crashlens simulate                  # Generate test data
crashlens fetch-langfuse            # Fetch from Langfuse API
crashlens fetch-helicone            # Fetch from Helicone API
crashlens list-policy-templates     # List built-in policies
crashlens validate REPORT           # Validate report JSON
crashlens show-metrics-config       # Show current metrics config
```

### Command Groups

#### `config` - Configuration Management
```bash
crashlens config validate CONFIG_FILE [--type TYPE] [--verbose]
crashlens config smtp-example [--output PATH]
```

#### `schema` - Schema Detection
```bash
crashlens schema list [--stable-only]
crashlens schema detect LOGFILE [--sample-size N]
```

#### `reports` - Report Management
```bash
crashlens reports archive [--days N] [--base-dir PATH]
crashlens reports prune [--days N] [--base-dir PATH]
crashlens reports stats [--base-dir PATH]
crashlens reports readme [--base-dir PATH]
```

#### `slack` - Slack Integration
```bash
crashlens slack notify --webhook-url URL --report REPORT [--summary-only]
```

---

## Deprecated Commands (Backward Compatibility)

These commands still work but show deprecation warnings. They will be removed in CrashLens v2.0.

| Deprecated Command | Replacement | Status |
|--------------------|-------------|--------|
| `crashlens pii-clean` | `crashlens pii-remove` | Hidden from `--help` |
| `crashlens list-schemas` | `crashlens schema list` | Hidden from `--help` |
| `crashlens detect-schema` | `crashlens schema detect` | Hidden from `--help` |
| `crashlens validate-metrics-config` | `crashlens config validate --type metrics` | Hidden from `--help` |

**Deprecation Behavior**:
- Commands are marked with `hidden=True` (don't appear in `--help`)
- Show yellow warning message when executed
- Forward to new command implementation
- Exit with same behavior as new commands

---

## Testing

Comprehensive test suite in `tests/test_cli_reorganization.py`:

```bash
# Run CLI reorganization tests
poetry run pytest tests/test_cli_reorganization.py -v

# Test coverage:
# - 20 test cases covering all changes
# - Deprecation warnings verified
# - Command group structure validated
# - Backward compatibility confirmed
# - Help output consistency checked
```

**Test Results**: ✅ 20/20 tests passing

---

## Design Principles

### 1. Backward Compatibility
- **Zero Breaking Changes**: All old commands still work
- **Graceful Migration**: Deprecation warnings guide users to new commands
- **Hidden but Functional**: Deprecated commands hidden from `--help` but still execute

### 2. Consistent Hierarchy
- **Command Groups**: Related operations grouped together (`schema`, `config`, `reports`, `slack`)
- **Top-Level Simplicity**: Core operations remain top-level (`scan`, `guard`, `pii-remove`)
- **Predictable Structure**: Users can guess command structure

### 3. Clear Naming
- **Descriptive**: Command names clearly indicate their purpose
- **Concise**: No unnecessary verbosity
- **Consistent**: Similar operations use similar naming patterns

### 4. Future-Proof
- **Extensible Groups**: Easy to add new subcommands to existing groups
- **Deprecation Path**: Clear migration timeline (v2.0 removal)
- **Version Awareness**: Commands document their stability status

---

## Migration Timeline

### v1.x (Current)
- ✅ All new command structure available
- ✅ All old commands work with deprecation warnings
- ✅ Documentation updated

### v2.0 (Future)
- 🗑️ Remove deprecated commands entirely
- 🔒 New commands become required
- 📚 Update all examples and tutorials

---

## Examples

### Before (Old Structure)
```bash
# Inconsistent command hierarchy
crashlens list-schemas
crashlens detect-schema logs.jsonl
crashlens validate-metrics-config metrics.yaml
crashlens pii-clean logs.jsonl
```

### After (New Structure)
```bash
# Consistent, organized command hierarchy
crashlens schema list
crashlens schema detect logs.jsonl
crashlens config validate metrics.yaml
crashlens pii-remove logs.jsonl
```

---

## FAQ

### Q: Will my existing scripts break?
**A**: No. All old commands still work and will continue to work until v2.0.

### Q: How do I update my CI/CD pipelines?
**A**: Update commands to new structure to avoid deprecation warnings:
```bash
# Replace in your CI scripts
sed -i 's/list-schemas/schema list/g' .github/workflows/*.yml
sed -i 's/detect-schema/schema detect/g' .github/workflows/*.yml
sed -i 's/validate-metrics-config/config validate/g' .github/workflows/*.yml
sed -i 's/pii-clean/pii-remove/g' .github/workflows/*.yml
```

### Q: When will deprecated commands be removed?
**A**: CrashLens v2.0 (estimated 6+ months from now). You'll have plenty of time to migrate.

### Q: Can I suppress deprecation warnings?
**A**: Yes, redirect stderr:
```bash
crashlens pii-clean logs.jsonl 2>/dev/null  # Unix/Linux/macOS
crashlens pii-clean logs.jsonl 2>$null      # PowerShell
```

### Q: How do I check if my scripts use deprecated commands?
**A**: Run with deprecation warnings visible and grep for "WARNING":
```bash
crashlens pii-clean logs.jsonl 2>&1 | grep WARNING
```

---

## Related Documentation

- [Command Reference](COMMAND-REFERENCE.md) - Complete command documentation
- [User Manual](USER_MANUAL.md) - End-user guide
- [Development Guide](../CONTRIBUTING.md) - Contributing to CrashLens

---

**Last Updated**: 2025-01-12  
**Status**: ✅ Complete and Tested  
**Version**: CrashLens v1.x
