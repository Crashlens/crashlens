# Migration Safety and Teardown Plan

## Overview

This document describes the safety mechanisms and rollback procedures for the gradual merge of `crashlens policy-check` into `crashlens guard`.

## Feature Flag

The migration is controlled by the environment variable:
```bash
CRASHLENS_USE_UNIFIED_ENGINE=1  # Enable unified engine
CRASHLENS_USE_UNIFIED_ENGINE=0  # Use legacy behavior (default)
```
# Migration Teardown — Completed

This migration has been completed. The legacy feature flag `CRASHLENS_USE_UNIFIED_ENGINE` has been removed and the unified engine is now the single execution path.

The original, detailed migration plan has been archived for historical reference at:

`docs/archive/migration_teardown.md`

Summary of changes:

- Unified engine is the only supported execution path.
- CLI flags and environment variables for toggling engines removed.
- Tests and CI referencing the legacy flag were updated or removed.

For historical rollback procedures, parity gate results, and the full migration rationale, consult the archived document.

Archived on: 2025-11-08
