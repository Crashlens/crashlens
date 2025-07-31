🚨 **CrashLens Token Waste Report** 🚨
📊 Analysis Date: 2025-07-31 15:24:48

| Metric | Value |
|--------|-------|
| Total AI Spend | $1.18 |
| Total Potential Savings | $0.82 |
| Wasted Tokens | 19,831 |
| Issues Found | 73 |
| Traces Analyzed | 156 |

❓ **Overkill Model** | 59 traces | $0.68 wasted | Fix: optimize usage
   🎯 **Wasted tokens**: 16,496
   🔗 **Traces** (57): trace_overkill_01, trace_norm_02, trace_overkill_02, trace_overkill_03, trace_norm_06, +52 more

📢 **Fallback Failure** | 7 traces | $0.08 wasted | Fix: remove redundant fallbacks
   🎯 **Wasted tokens**: 1,330
   🔗 **Traces** (7): trace_fallback_success_01, trace_fallback_success_02, trace_fallback_success_03, trace_fallback_success_04, trace_fallback_success_05, +2 more

⚡ **Fallback Storm** | 5 traces | $0.07 wasted | Fix: optimize model selection
   🎯 **Wasted tokens**: 1,877
   🔗 **Traces** (5): trace_fallback_failure_01, trace_fallback_failure_02, trace_fallback_failure_03, trace_fallback_failure_04, trace_fallback_failure_05

🔄 **Retry Loop** | 2 traces | $0.0001 wasted | Fix: exponential backoff
   🎯 **Wasted tokens**: 128
   🔗 **Traces** (2): trace_retry_loop_07, trace_retry_loop_10


## Top Expensive Traces

| Rank | Trace ID | Model | Cost |
|------|----------|-------|------|
| 1 | trace_norm_76 | gpt-4 | $0.09 |
| 2 | trace_norm_65 | gpt-4 | $0.07 |
| 3 | trace_norm_38 | gpt-4 | $0.06 |

## Cost by Model

| Model | Cost | Percentage |
|-------|------|------------|
| gpt-4 | $1.16 | 98% |
| gpt-3.5-turbo | $0.02 | 2% |
