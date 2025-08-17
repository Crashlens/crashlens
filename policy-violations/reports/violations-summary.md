# 🚨 CrashLens Policy Violations Report
📊 **Analysis Date:** 2025-08-17T10:42:49.825461Z

## Summary
- **Traces Analyzed:** 1
- **Policy Violations:** 2
  (Critical: 2)
- **Estimated Spend:** $0.02
- **Potential Savings:** $0.01

## Top Rules (by count)
1) **expensive_single_call** — 2 violations — severity=critical — est. cost: $0.02

## Cost by Model
- **gpt-4**: $0.02 (100%)

## Detectors (Essentials Only)
- ✅ No major detector patterns found

## Next Actions
- Tighten YAML policy (retry caps, model routing thresholds)
- Enable CI fail on critical/high violations
- Re-run with `--detailed` and inspect `policy-violations-detailed.json`
- Review trace patterns to optimize model routing
- Implement suggested fixes to reduce policy violations
