# Migration Safety and Teardown Plan

## Overview

This document describes the safety mechanisms and rollback procedures for the gradual merge of `crashlens policy-check` into `crashlens guard`.

## Feature Flag

The migration is controlled by the environment variable:
```bash
CRASHLENS_USE_UNIFIED_ENGINE=1  # Enable unified engine
CRASHLENS_USE_UNIFIED_ENGINE=0  # Use legacy behavior (default)
```

CLI override:
```bash
crashlens guard --use-unified-engine  # Force new engine
crashlens guard --no-unified-engine   # Force old engine
```

## Migration Phases

### Phase 1: Preparation (Commits 000-002)
- Add feature flags
- Add rule translator
- Add shared ingestion layer
- **Safety**: No behavior changes, default is legacy mode

### Phase 2: Integration (Commits 003-005)
- Integrate PolicyEngine into guard
- Add detector enrichment hooks
- Unify reporting layer
- **Safety**: Feature-flagged, parallel testing

### Phase 3: Deprecation (Commits 006-007)
- Mark policy-check as deprecated
- Redirect policy-check to guard
- **Safety**: Only after parity gates pass

### Phase 4: Removal (Commit 008)
- Remove old policy-check code
- Remove legacy guard evaluator
- **Safety**: After 2 release cycles of deprecation

## Parity Gates

Before proceeding to Phase 3, the following must pass:

1. **Functional Parity**: All integration tests pass with both engines
2. **Performance Parity**: Unified engine ≤ 10% slower than legacy
3. **Memory Parity**: Unified engine memory usage ≤ 20% higher
4. **Output Parity**: Reports are structurally equivalent

## Rollback Procedures

### Immediate Rollback
If any gate fails during development:
```bash
git revert <commit-hash>
poetry run pytest tests/
```

### Production Rollback
If issues are discovered in production:
```bash
# Option 1: Environment variable
export CRASHLENS_USE_UNIFIED_ENGINE=0

# Option 2: CLI flag
crashlens guard --no-unified-engine

# Option 3: Code rollback
git revert <range>
poetry install
```

## Testing Strategy

### Unit Tests
- Each commit includes unit tests for new functionality
- Tests run in both legacy and unified modes

### Integration Tests
- End-to-end tests for complete workflows
- Comparison tests verify output equivalence

### Performance Tests
- Benchmark large file processing (1M+ lines)
- Memory profiling with memory_profiler
- Regression detection with statistical thresholds

## Monitoring

Track these metrics during rollout:
- Error rate by engine type
- Processing latency (p50, p95, p99)
- Memory consumption
- User-reported issues

## Communication

### Deprecation Notice
```
Warning: The 'policy-check' command is deprecated and will be removed in v3.0.0.
Please use 'crashlens guard' instead. For equivalent behavior, use:
  crashlens guard LOGFILE --policy-file POLICY.yaml
See docs/MIGRATION_GUIDE.md for details.
```

### Changelog Entry
```
### Deprecated
- `crashlens policy-check` command (use `crashlens guard` instead)

### Added
- Unified policy engine in `crashlens guard`
- Support for policy templates in guard
- Backwards-compatible rule translation

### Changed
- Guard now supports PolicyEngine features (operators, dot notation)
- Improved schema validation with optional Langfuse parser
```

## Success Criteria

Migration is considered complete when:
1. All parity gates pass for 2 consecutive releases
2. No critical bugs reported for unified engine
3. Documentation fully updated
4. User migration guide published
5. At least 80% of users migrated (telemetry permitting)

## Emergency Contacts

If critical issues arise:
1. Disable unified engine globally (env var)
2. File GitHub issue with `critical` label
3. Notify maintainers via Slack/Discord
4. Prepare hotfix release with revert

## Audit Trail

All decisions and gate results must be documented in:
- `docs/migration_log.md` - Chronological log
- GitHub Issues - Tracking individual concerns
- PR comments - Technical discussion
