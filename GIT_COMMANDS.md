# Quick Git Commands for Commit

## Copy-Paste Commands (Windows PowerShell)

```powershell
# Step 1: Add all files
git add crashlens/observability/metrics.py
git add crashlens/observability/__init__.py
git add crashlens/policy/engine.py
git add crashlens/cli.py
git add tests/unit/test_metrics_mock.py
git add scripts/benchmark_100k_proper.py
git add .github/workflows/benchmark-metrics.yml
git add HOUR1-2_SAMPLING_COMPLETE.md
git add HOUR3_LINUX_BENCHMARK_SETUP.md
git add SALVAGE_OPERATION_PROGRESS.md
git add READY_TO_COMMIT.md
git add GIT_COMMANDS.md

# Step 2: Verify what's staged
git status

# Step 3: Commit with descriptive message
git commit -m "feat: implement metrics sampling to reduce overhead

- Add probabilistic sampling to CrashLensMetrics (--metrics-sample-rate)
- Remove max/min latency metrics (misleading with sampling)
- Add 8 unit tests for sampling functionality (all passing)
- Update benchmark script to test baseline + 100% + 10% sampling
- Add GitHub Actions workflow for Linux benchmark validation

Implementation complete:
- 36/36 unit tests passing
- Zero breaking changes
- 100% backward compatible (default sample_rate=1.0)
- Expected overhead reduction: 21.89% -> ~2.2%

Next: Trigger workflow for Linux validation"

# Step 4: Push to remote
git push origin feat/prometheus-metrics-mvp
```

## Alternative: One-Line Commands

```powershell
# Add all tracked and documentation files
git add crashlens/ tests/ scripts/ .github/ *.md

# Commit
git commit -m "feat: implement metrics sampling to reduce overhead"

# Push
git push origin feat/prometheus-metrics-mvp
```

## Verify Before Pushing

```powershell
# Check current branch
git branch

# Should show: * feat/prometheus-metrics-mvp

# Check staged files
git status

# Should show 11 files staged for commit

# Check commit message
git log -1

# Review changes (optional)
git diff --cached
```

## After Pushing

1. Go to: https://github.com/Crashlens/crashlens
2. Check that branch `feat/prometheus-metrics-mvp` has your commit
3. Navigate to: Actions tab
4. Find workflow: "Metrics Performance Benchmark"
5. Click "Run workflow" button

## Troubleshooting

**Issue: "fatal: not a git repository"**
```powershell
cd C:\Users\LawLight\OneDrive\Desktop\crashlens
git status
```

**Issue: "Updates were rejected"**
```powershell
# Pull latest changes first
git pull origin feat/prometheus-metrics-mvp
# Then push again
git push origin feat/prometheus-metrics-mvp
```

**Issue: Authentication failed**
```powershell
# Use GitHub CLI (if installed)
gh auth login

# Or use Personal Access Token
# Settings -> Developer settings -> Personal access tokens -> Generate new token
```

**Issue: Need to undo**
```powershell
# Unstage files
git reset HEAD

# Discard changes (CAREFUL!)
git checkout -- <file>
```

---

**Ready to commit? Run the commands above! 🚀**
