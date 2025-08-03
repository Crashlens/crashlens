🔒 CrashLens runs 100% locally. No data leaves your system.

# CrashLens Token Waste Report

**Analysis Date:** 2025-08-04 01:06:43  

**Traces Analyzed:** 12  


## Summary

| Metric | Value |
|--------|-------|
| Total AI Spend | $0.09 |
| Total Potential Savings | $0.0000 |
| Wasted Tokens | 0 |
| Issues Found | 3 |
| Traces Analyzed | 12 |

## Unknown (3 issues)

| Metric | Value |
|--------|-------|
| Total Waste Cost | $0.0000 |
| Total Waste Tokens | 0 |

**Trace IDs**:
`demo_fallback_05, demo_norm_03, demo_norm_04`

**Issue**: 3 traces flagged by Unknown


## Top Expensive Traces

| Rank | Trace ID | Model | Cost |
|------|----------|-------|------|
| 1 | demo_norm_03 | gpt-4 | $0.03 |
| 2 | demo_norm_04 | gpt-4 | $0.02 |
| 3 | demo_fallback_05 | gpt-3.5-turbo | $0.02 |

## Cost by Model

| Model | Cost | Percentage |
|-------|------|------------|
| gpt-4 | $0.09 | 99% |
| gpt-3.5-turbo | $0.0012 | 1% |

## Next Steps

- Run `crashlens --detailed` for grouped JSON reports
- Review trace patterns to optimize model routing
- Implement suggested fixes to reduce token waste
