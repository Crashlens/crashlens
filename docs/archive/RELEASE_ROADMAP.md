# CrashLens Release Roadmap - Unified Engine Rollout

## Current Status (November 8, 2025)

**Latest Commit:** `4d5ff0f` - Step 9 complete  
**Version:** Pre-release (v2.9.21 → v3.0.0 pending)  
**Unified Engine:** ✅ Implemented, ❌ Not deployed

### Steps 0-9 Complete
- ✅ Step 0-2: Rule translator, shared ingestion, baseline injection
- ✅ Step 3-4: Detector driver, guard adapter integration
- ✅ Step 5-6: Backwards compatibility, environment variable control
- ✅ Step 7: CLI alias with deprecation warnings
- ✅ Step 8: Performance benchmarks (unified 14.1% faster!)
- ✅ Step 9: Integration tests + canary workflow

**Result:** Production-ready unified engine with feature flag `CRASHLENS_USE_UNIFIED_ENGINE` (default OFF)

---

## Release Timeline

### v3.0.0 - Initial Release (Target: November 2025)
**Status:** Ready to tag  
**Goal:** Deploy unified engine with feature flag, default OFF

**Changes:**
- Add unified PolicyEngine with `GuardPolicyEngineAdapter`
- Feature flag: `CRASHLENS_USE_UNIFIED_ENGINE=0` (default, legacy mode)
- Enable unified: `CRASHLENS_USE_UNIFIED_ENGINE=1`
- Performance: 14.1% faster than legacy
- Parity: 100% match across all 5 policy templates

**Deployment:**
```bash
git tag -a v3.0.0 -m "feat: Unified engine with feature flag (default OFF)"
git push origin v3.0.0
poetry build
poetry publish
```

**Monitoring:**
- Enable Prometheus metrics collection
- Track: `crashlens_engine_type{type="legacy"|"unified"}`
- Track: Error rates, latency (p50/p95/p99), memory usage
- Alert on parity violations (>1% deviation)

**Timeline:** 4-8 weeks of monitoring before v3.1.0

---

### v3.1.0 - Canary Rollout (Target: January 2026)
**Status:** Pending v3.0.0 production data  
**Goal:** Gradual rollout, unified as default

**Prerequisites:**
- ✅ v3.0.0 deployed for 4-8 weeks
- ✅ Telemetry shows <0.1% error rate increase
- ✅ Parity gates passing in production (±1% violations)
- ✅ No critical rollback incidents
- ✅ Performance within thresholds (≤+15% time, ≤+25% memory)

**Canary Stages:**
1. **Week 1-2:** 10% traffic to unified (`CRASHLENS_USE_UNIFIED_ENGINE=1`)
2. **Week 3-4:** 25% traffic to unified
3. **Week 5-6:** 50% traffic to unified
4. **Week 7-8:** 100% traffic to unified

**Rollout Command:**
```bash
# Push to canary branch to trigger .github/workflows/canary.yml
git checkout -b internal/canary
git push origin internal/canary
```

**Rollback Trigger:**
- Error rate >0.5% higher than baseline
- Parity violations >1% difference
- Critical bug reports
- Memory usage >25% higher than legacy

**Rollback Command:**
```bash
# Emergency: Disable unified globally
kubectl set env deployment/crashlens CRASHLENS_USE_UNIFIED_ENGINE=0

# Or revert release
git revert v3.1.0
git tag -a v3.1.1 -m "hotfix: Revert to legacy engine"
```

**Changes:**
- Change default: `CRASHLENS_USE_UNIFIED_ENGINE=1`
- Legacy still available: `CRASHLENS_USE_UNIFIED_ENGINE=0`
- Update documentation: Unified is now standard
- Add migration guide for users on legacy

**Timeline:** 8-12 weeks before v3.2.0

---

### v3.2.0 - Deprecation Warnings (Target: March-April 2026)
**Status:** Pending v3.1.0 validation  
**Goal:** Announce legacy deprecation, collect usage data

**Prerequisites:**
- ✅ v3.1.0 deployed for 8-12 weeks
- ✅ Unified engine usage >90% in production
- ✅ Legacy usage <10% (tracked via telemetry)
- ✅ Zero critical rollback incidents since v3.1.0
- ✅ User feedback positive or neutral

**Changes:**
- Add deprecation warning when `CRASHLENS_USE_UNIFIED_ENGINE=0`:
  ```
  ⚠️  DEPRECATION WARNING: Legacy engine will be removed in v4.0.0
      The unified engine is now stable and recommended.
      
      To silence this warning:
        export CRASHLENS_USE_UNIFIED_ENGINE=1
      
      For issues, report at: https://github.com/crashlens/crashlens/issues
  ```
- Track legacy usage via telemetry: `crashlens_legacy_usage_count`
- Send user survey to legacy users (opt-in)
- Document migration path in UPGRADE_GUIDE.md

**Telemetry Target:**
- Goal: Legacy usage <5% by v4.0.0
- If >5% at 3 months, extend deprecation timeline

**Timeline:** 12-24 weeks before v4.0.0 (depends on legacy usage drop)

---

### v4.0.0 - Legacy Removal (Target: June-September 2026)
**Status:** Pending v3.2.0 telemetry  
**Goal:** Remove legacy code, breaking change

**Prerequisites (Step 10 Conditions):**
- ✅ v3.2.0 deployed for 12-24 weeks
- ✅ Telemetry shows legacy usage <5%
- ✅ No unresolved rollback incidents since v3.1.0
- ✅ 2+ production releases with unified as default (v3.1.0, v3.2.0)
- ✅ User communication campaign complete (3+ months notice)

**Step 10 Actions:**
1. **Remove legacy code:**
   - Delete `crashlens/guard.py` legacy evaluator
   - Delete `CRASHLENS_USE_UNIFIED_ENGINE` feature flag
   - Remove legacy-specific tests

2. **Update CLI:**
   - `crashlens guard` always uses unified engine (no flag check)
   - Remove environment variable handling

3. **Final docs cleanup:**
   - Archive migration guides
   - Update README to remove feature flag mentions
   - Create UPGRADE_v3_to_v4.md guide

4. **Breaking changes announcement:**
   - CHANGELOG.md entry (major version)
   - GitHub release notes
   - Email to users (if opt-in list available)

**Rollback Plan:**
```bash
# Tag created before removal
git tag -a v3.9.9 -m "Last version with legacy support"

# If issues in v4.0.0
git revert <v4.0.0-commit-range>
git tag -a v4.0.1 -m "hotfix: Restore legacy engine temporarily"
```

**Tests:**
- Full test suite (177+ tests)
- Integration tests (5/5 templates)
- Benchmark regression tests
- Documentation validation

**Timeline:** This is Step 10, earliest June 2026 (7-8 months from now)

---

## Telemetry Gates (Enforced Throughout)

### Parity Gates
- ✅ Violation counts: ±1% tolerance
- ✅ Severity buckets: ≤1 level difference
- ✅ Critical severity: Zero false negatives vs legacy
- ❌ **Fail Condition:** Auto-rollback if violated

### Performance Gates
- ✅ Wall time: Unified ≤ Legacy +15%
- ✅ RSS memory: Unified ≤ Legacy +25%
- ✅ P95 latency: Unified ≤ Legacy +20%
- ❌ **Fail Condition:** Disable unified engine, investigate

### Reliability Gates
- ✅ Error rate: <0.1% increase from baseline
- ✅ Crash rate: Zero crashes from unified engine
- ✅ Rollback incidents: Zero unresolved
- ❌ **Fail Condition:** Immediate rollback

---

## Emergency Rollback Procedures

### Immediate (< 5 minutes)
```bash
# Environment variable (no code change)
export CRASHLENS_USE_UNIFIED_ENGINE=0

# Or Kubernetes
kubectl set env deployment/crashlens CRASHLENS_USE_UNIFIED_ENGINE=0
kubectl rollout restart deployment/crashlens
```

### Fast (< 30 minutes)
```bash
# Revert release
git revert <problematic-commit>
poetry build
poetry publish  # Publish v3.x.y+1 with revert
```

### Full (< 2 hours)
```bash
# Restore previous release tag
git checkout v3.0.0  # Last known good version
git tag -a v3.x.y -m "hotfix: Rollback to v3.0.0"
poetry build
poetry publish
```

---

## Risk Assessment

### Low Risk (v3.0.0 → v3.1.0)
- Feature flag allows instant rollback
- Canary workflow validates before full rollout
- Parity tests ensure functional equivalence
- Performance benchmarks show improvement

**Mitigation:** Gradual rollout, real-time monitoring, instant rollback capability

### Medium Risk (v3.1.0 → v3.2.0)
- Deprecation warnings may annoy users
- Some users may resist migration
- Legacy usage telemetry required

**Mitigation:** Clear communication, extended timeline if needed, opt-out support

### High Risk (v3.2.0 → v4.0.0)
- Breaking change (legacy code removed)
- Users on <5% legacy could break
- Rollback requires full release revert

**Mitigation:** 
- Strict prerequisite checks (see v4.0.0 section)
- Final user survey before removal
- Create LTS branch (v3.x) for legacy users if needed
- Document rollback extensively

---

## Decision Criteria for Step 10

**Step 10 MAY proceed ONLY IF:**
1. ✅ 2+ production releases with unified as default (v3.1.0, v3.2.0)
2. ✅ Telemetry shows legacy usage <5% for 3+ months
3. ✅ Zero critical rollback incidents since v3.1.0
4. ✅ Parity gates passing for 6+ months continuously
5. ✅ Performance gates passing for 6+ months continuously
6. ✅ User communication complete (3+ months notice)
7. ✅ LTS branch created (v3.x-lts) for legacy support (if needed)

**If ANY condition fails:** Extend timeline, do NOT remove legacy code.

---

## Current Recommendation (November 2025)

**DO NOT EXECUTE STEP 10.** Instead:

1. **Tag v3.0.0** (this week)
2. **Deploy to production** (default: unified OFF)
3. **Monitor for 4-8 weeks** (collect telemetry)
4. **Canary rollout v3.1.0** (January 2026)
5. **Monitor for 8-12 weeks** (validate stability)
6. **Deprecation v3.2.0** (March-April 2026)
7. **Monitor for 12-24 weeks** (track legacy usage drop)
8. **THEN consider Step 10** (June-September 2026)

**Earliest Step 10 Date:** June 2026 (7-8 months from now)

---

## Stakeholder Sign-Off Required

Before v4.0.0 (Step 10):
- [ ] Engineering: Parity gates passed for 6+ months
- [ ] Product: User feedback positive, <5% legacy usage
- [ ] Support: Zero unresolved rollback incidents
- [ ] Security: No vulnerabilities in unified engine
- [ ] Documentation: Migration guides complete

---

**Last Updated:** November 8, 2025  
**Next Review:** v3.0.0 post-deployment (December 2025)
