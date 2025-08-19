# 🚨 CrashLens Policy Violations Report
📊 **Analysis Date:** 2025-08-19T19:23:23.408377Z

## Summary
- **Traces Analyzed:** 1
- **Policy Violations:** 2
  (Critical: 1 | High: 1)
- **Estimated Spend:** $1.31
- **Potential Savings:** $0.51

## Top Rules (by count)
1) **trace_cost_hard_limit** — 1 violations — severity=critical — est. cost: $0.60
2) **trace_cost_warning_limit** — 1 violations — severity=high — est. cost: $0.25

## Cost by Model
- **gpt-4**: $1.32 (100%)

## Detectors (Essentials Only)
- ✅ No major detector patterns found

## Next Actions
- Tighten YAML policy (retry caps, model routing thresholds)
- Enable CI fail on critical/high violations
- Re-run with `--detailed` and inspect `policy-violations-detailed.json`
- Review trace patterns to optimize model routing
- Implement suggested fixes to reduce policy violations
