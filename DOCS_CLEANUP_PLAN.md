# CrashLens Documentation Cleanup & Reorganization Plan

**Status:** In Progress  
**Date:** 2025-11-09  
**Goal:** Clean, canonical, production-ready documentation structure

---

## ✅ Phase 1: Structure Setup (DONE)

- [x] Create `docs/internal/` directory
- [x] Create `docs/archive/` directory

---

## 📋 Phase 2: Keep & Polish (Canonical Docs)

These remain in `docs/` as the single source of truth:

### Core User Docs
- [ ] ✅ **WHAT_IS_CRASHLENS.md** - Trim to 600-800 words
- [ ] ✅ **QUICKSTART.md** - Ensure <5 min runnable
- [ ] ✅ **CLI_COMMAND_REFERENCE.md** - Keep as only CLI reference
- [ ] ✅ **GUARD.md** - Keep as canonical policy guide
- [ ] ✅ **OBSERVABILITY.md** - Keep as canonical Prometheus/Grafana guide
- [ ] ✅ **../crashlens/detectors/detectors.md** - Keep technical deep dive
- [ ] ✅ **PII_REMOVAL_GUIDE.md** - Keep (consider moving to privacy/)
- [ ] ✅ **SLACK_INTEGRATION.md** - Keep
- [ ] ✅ **NON-INTERACTIVE-GUIDE.md** - Keep (CI/CD integration)
- [ ] ✅ **architecture-flow.md** - Keep

### Project Meta
- [ ] ✅ **../CONTRIBUTING.md** - Keep, tighten for GitHub workflow
- [ ] ✅ **../SECURITY.md** - Keep
- [ ] ✅ **../CHANGELOG.md** - Keep
- [ ] ✅ **../README.md** - Keep (needs enhancement)
- [ ] ⚠️ **../LICENSE** - MISSING (need MIT or Apache-2.0)
- [ ] ⚠️ **../CODE_OF_CONDUCT.md** - MISSING (need to create)

---

## 🔀 Phase 3: Merge Operations

### 3.1 CLI References
- [ ] Merge `COMMAND-REFERENCE.md` → `CLI_COMMAND_REFERENCE.md`
- [ ] Delete `COMMAND-REFERENCE.md`

### 3.2 Guard Internals
- [ ] Merge `GUARD_IMPLEMENTATION_SUMMARY.md` + `GUARD_FUNCTIONALITY.md` → `docs/internal/guard-internals.md`
- [ ] Keep `GUARD.md` as user-facing (link to internals)

### 3.3 Observability & Dashboards
- [ ] Merge `PROMETHEUS_GRAFANA_SETUP.md` + `GRAFANA_SETUP.md` + `DASHBOARD_IMPLEMENTATION_COMPLETE.md` + `DASHBOARD_LAYOUT_MAP.md` → `OBSERVABILITY.md` (enhance existing)
- [ ] Create `docs/internal/dashboards.md` for JSON/panel internals
- [ ] Archive originals

### 3.4 Reporting
- [ ] Merge `REPORT_COMMAND.md` + `REPORT_EMAIL_ENHANCEMENTS.md` → `docs/reporting.md`

### 3.5 Inputs & Configuration
- [ ] Merge `FILE_HANDLING_MANUAL.md` + `LOG_SETUP.md` + `CONFIG_PRECEDENCE.md` → `docs/inputs-and-config.md`

### 3.6 Implementation History
- [ ] Merge all `STEP_*.md` files → `docs/internal/development-history.md`
- [ ] Merge `ENHANCEMENT_STEPS_SUMMARY.md` → development-history
- [ ] Merge `STEPS_0_TO_9_COMPLETE_DOCUMENTATION.md` → development-history
- [ ] Merge `DEVELOPMENT_RETROSPECTIVE_100_COMMITS.md` → development-history

---

## 🗄️ Phase 4: Archive/Move Operations

### Move to `docs/archive/`
- [ ] `INDEX.md` (superseded by DOCUMENTATION_INDEX.md)
- [ ] `COMMAND-REFERENCE.md` (after merge)
- [ ] All validation reports (already in subdirs)
- [ ] `V1_0_LAUNCH_CHECKLIST_FINAL.md`
- [ ] `RELEASE_ROADMAP.md` (create public high-level version)

### Move to `docs/internal/`
- [ ] All `STEP_*.md` files (after merge)
- [ ] `ENHANCEMENT_STEPS_SUMMARY.md`
- [ ] `STEPS_0_TO_9_COMPLETE_DOCUMENTATION.md`
- [ ] `DEVELOPMENT_RETROSPECTIVE_100_COMMITS.md`
- [ ] `BOOLEAN_LOGIC_IMPLEMENTATION.md` (or merge into GUARD.md)
- [ ] `DASHBOARD_IMPLEMENTATION_COMPLETE.md`
- [ ] `DASHBOARD_LAYOUT_MAP.md`
- [ ] `GUARD_IMPLEMENTATION_SUMMARY.md`
- [ ] `GUARD_FUNCTIONALITY.md`
- [ ] `HTTP_SERVER_SECURITY.md` (or keep if production-relevant)
- [ ] All `*_COMPLETE.md`, `*_SUMMARY.md`, `*_REPORT.md` implementation docs

---

## 📝 Phase 5: Content Housekeeping

### 5.1 README.md Enhancement
- [ ] Add 200-400 word elevator pitch
- [ ] Add 3 quick start commands
- [ ] Add badge row (build, version, license, downloads)
- [ ] Add GitHub Actions CI badge
- [ ] Add installation instructions
- [ ] Add links to Quickstart and CLI reference

### 5.2 WHAT_IS_CRASHLENS.md Trim
- [ ] Reduce to 600-800 words
- [ ] Focus: problem, solution, 3 key benefits
- [ ] Move architecture details to architecture-flow.md
- [ ] Move detection details to detectors.md

### 5.3 Create Missing Files
- [ ] `LICENSE` (MIT or Apache-2.0)
- [ ] `CODE_OF_CONDUCT.md` (Contributor Covenant)
- [ ] `.github/ISSUE_TEMPLATE/` (bug, feature request)
- [ ] `.github/PULL_REQUEST_TEMPLATE.md`

### 5.4 Standardize Front Matter
Add to each major doc:
- [ ] Table of Contents (ToC)
- [ ] TL;DR section
- [ ] "Who this doc is for" line
- [ ] Last updated date

---

## 🏗️ Phase 6: Documentation System

### 6.1 Choose Doc Generator
- [ ] Evaluate: MkDocs-Material vs Docusaurus
- [ ] Recommendation: **MkDocs-Material** (Python-native, simple)

### 6.2 Create Sidebar Structure
```yaml
nav:
  - Home: index.md
  - Overview: WHAT_IS_CRASHLENS.md
  - Quickstart: QUICKSTART.md
  - CLI Reference: CLI_COMMAND_REFERENCE.md
  - User Guides:
    - Guard & Policies: GUARD.md
    - Observability: OBSERVABILITY.md
    - Detectors: ../crashlens/detectors/detectors.md
    - Reporting: reporting.md
    - Inputs & Config: inputs-and-config.md
  - Integrations:
    - Slack: SLACK_INTEGRATION.md
    - CI/CD: NON-INTERACTIVE-GUIDE.md
  - Security:
    - PII Removal: PII_REMOVAL_GUIDE.md
    - Security Policy: ../SECURITY.md
  - Contributing:
    - Guide: ../CONTRIBUTING.md
    - Architecture: architecture-flow.md
  - Internal:
    - Guard Internals: internal/guard-internals.md
    - Dashboards: internal/dashboards.md
    - Dev History: internal/development-history.md
```

### 6.3 Docs CI
- [ ] Add `.github/workflows/docs.yml`
- [ ] Link checker (markdown-link-check)
- [ ] Spell checker (cspell or codespell)
- [ ] Verify no internal docs in main nav
- [ ] Build and deploy docs site

---

## 🔍 Phase 7: Security & Cleanup

### 7.1 Permissions Scrub
- [ ] Search for credentials in all docs
- [ ] Search for internal endpoints
- [ ] Search for PII
- [ ] Remove or redact sensitive info

### 7.2 Final Verification
- [ ] All links work (no 404s)
- [ ] All code examples run
- [ ] No duplicate content
- [ ] Consistent formatting
- [ ] Proper heading hierarchy

---

## 📊 Success Metrics

| Metric | Before | Target | After |
|--------|--------|--------|-------|
| Total doc files | 49 | 20-25 | TBD |
| Main docs/ files | 49 | 12-15 | TBD |
| Internal docs | 0 | 5-8 | TBD |
| Archived docs | 0 | 10-15 | TBD |
| Duplicate pages | ~10 | 0 | TBD |
| Avg read time | 30-40min | 10-15min | TBD |

---

## 🚀 Execution Order

1. **Phase 1** ✅ - Structure (DONE)
2. **Phase 3** - Merges (do first to consolidate)
3. **Phase 4** - Archives/moves (clean up)
4. **Phase 5** - Content polish (enhance kept docs)
5. **Phase 6** - Doc system (infrastructure)
6. **Phase 7** - Security & verify (final checks)
7. **Phase 2** - Polish pass (final review)

---

## 📝 Notes

- Keep all originals in git history (nothing truly deleted)
- Test all merged docs before archiving originals
- Update all internal links after moves
- Announce structure change in CHANGELOG
- Consider creating migration guide for users

**Status Tracking:**
- 🟢 Complete
- 🟡 In Progress
- 🔴 Blocked
- ⚪ Not Started

---

**Next Actions:**
1. Start Phase 3.1: Merge CLI references
2. Continue with other merges
3. Move to archives
4. Polish kept docs
5. Set up doc generator
