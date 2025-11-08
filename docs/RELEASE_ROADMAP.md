# CrashLens Release Roadmap

## Current Status (November 8, 2025)

**Version:** v1.0 (direct launch with unified engine only)

The original gradual rollout roadmap (v3.0 → v4.0 with feature flags) has been superseded. CrashLens is launching directly at v1.0 with the unified PolicyEngine as the only execution path.

## Why Direct Launch?

- **Pre-launch status**: Zero production users, no migration needed
- **Parity validated**: 100% functional equivalence achieved in testing
- **Performance validated**: Unified engine 14.1% faster than legacy prototype
- **Simpler codebase**: Single execution path, easier to maintain

## Archived Documentation

The original gradual rollout strategy (v3.0-v4.0 with `CRASHLENS_USE_UNIFIED_ENGINE` feature flag) has been archived at:

`docs/archive/RELEASE_ROADMAP.md`

This included:
- 4-phase canary rollout (10% → 50% → 100%)
- Feature flag controls and rollback procedures
- 8-week gradual migration timeline
- Kubernetes deployment configurations

Since CrashLens had no users at the time of this decision, the gradual rollout was unnecessary complexity.

## v1.0 Launch Plan

### Features
- Unified PolicyEngine (only execution path)
- YAML rule definitions with dot notation and operators
- Inline detector enrichment (retry loops, fallback storms, model overkill)
- Multi-format output (JSON, Markdown, Text)
- PII removal and content filtering
- Prometheus metrics and Grafana dashboards

### Deployment
```bash
poetry build
poetry publish
# No feature flags, no rollback complexity
```

### Monitoring
- Standard Prometheus metrics
- Grafana dashboard for policy violations
- Alert rules for critical violations

---

**Historical Note:** The gradual rollout plan was developed assuming production users existed. The decision to launch directly at v1.0 was made on 2025-11-08 during Step 10 (legacy code removal).

---

**Last Updated:** November 8, 2025  
**Next Review:** v3.0.0 post-deployment (December 2025)
