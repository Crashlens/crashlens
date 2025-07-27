🚨 **CrashLens Token Waste Report** 🚨
📊 Analysis Date: 2025-07-28 02:15:43
🔍 Traces Analyzed: 156
💰 Total AI Spend: $1.18
💸 Potential Savings: $0.92

❓ **Overkill Model** | 73 traces | $0.77 wasted | Fix: optimize usage
   🎯 **Wasted tokens**: 18,812
   🔗 **Traces** (68): trace_overkill_01, trace_norm_02, trace_fallback_success_01, trace_overkill_02, trace_overkill_03, +63 more
   📄 **Samples**: "What is 2+2?...", "Draft a comprehensive business..."

📢 **Fallback Failure** | 7 traces | $0.08 wasted | Fix: remove redundant fallbacks
   🎯 **Wasted tokens**: 1,330
   🔗 **Traces** (7): trace_fallback_success_01, trace_fallback_success_02, trace_fallback_success_03, trace_fallback_success_04, trace_fallback_success_05, +2 more

⚡ **Fallback Storm** | 5 traces | $0.07 wasted | Fix: optimize model selection
   🎯 **Wasted tokens**: 1,877
   🔗 **Traces** (5): trace_fallback_failure_01, trace_fallback_failure_02, trace_fallback_failure_03, trace_fallback_failure_04, trace_fallback_failure_05
   📄 **Samples**: "Write a Python script to analy...", "Create a function in Go to rev..."

🔄 **Retry Loop** | 2 traces | $0.0001 wasted | Fix: exponential backoff
   🎯 **Wasted tokens**: 128
   🔗 **Traces** (2): trace_retry_loop_07, trace_retry_loop_10
   📄 **Samples**: "What is the current time in To...", "What is the capital of India?..."


💡 Top 3 Expensive Traces: 1. trace_norm_76 → gpt-4 → $0.09 | 2. trace_norm_65 → gpt-4 → $0.07 | 3. trace_norm_38 → gpt-4 → $0.06
📊 **Model Breakdown**: gpt-4: $1.16 (98%) | gpt-3.5-turbo: $0.02 (2%)
