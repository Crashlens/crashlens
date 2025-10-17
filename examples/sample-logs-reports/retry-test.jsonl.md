🚨 *CrashLens Token Waste Report* 🚨
📊 *Analysis Date:* 2025-10-18 02:57:43

📋 *Report Summary:*
• 💰 *Total AI Spend:* $859.52
• 🔥 *Potential Savings:* $859.52
• 🎯 *Wasted Tokens:* 24,555,498
• ⚠️ *Issues Found:* 187
• 📈 *Traces Analyzed:* 156

🔄 *Retry Loop* • 187 traces • $859.52 wasted
   💡 *Fix:* exponential backoff
   🎯 *Wasted tokens:* 24,555,498
   🔗 *Traces (156):* `trace_norm_01, trace_overkill_01, trace_norm_02, trace_retry_loop_01, trace_norm_03, +151 more`


🏆 *Top Expensive Traces:*
• #1 → `trace_norm_76` → gpt-4 → $65.78
• #2 → `trace_norm_65` → gpt-4 → $52.60
• #3 → `trace_norm_38` → gpt-4 → $44.10

🤖 *Cost by Model:*
• gpt-4 → $845.65 (98%)
• gpt-3.5-turbo → $13.87 (2%)

💡 *Next Steps:*
• Run `crashlens --detailed` for grouped JSON reports
• Review trace patterns to optimize model routing
• Implement suggested fixes to reduce token waste
