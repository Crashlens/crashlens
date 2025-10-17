🚨 *CrashLens Token Waste Report* 🚨
📊 *Analysis Date:* 2025-10-18 02:57:53

📋 *Report Summary:*
• 💰 *Total AI Spend:* $0.0052
• 🔥 *Potential Savings:* $0.0052
• 🎯 *Wasted Tokens:* 883
• ⚠️ *Issues Found:* 2
• 📈 *Traces Analyzed:* 2

🔄 *Retry Loop* • 2 traces • $0.0052 wasted
   💡 *Fix:* exponential backoff
   🎯 *Wasted tokens:* 883
   🔗 *Traces (2):* `retry_f280c00c, retry_965b6dde`


🏆 *Top Expensive Traces:*
• #1 → `retry_f280c00c` → gpt-4o → $0.0031
• #2 → `retry_965b6dde` → gpt-4o → $0.0021

🤖 *Cost by Model:*
• gpt-4o → $0.0052 (100%)

💡 *Next Steps:*
• Run `crashlens --detailed` for grouped JSON reports
• Review trace patterns to optimize model routing
• Implement suggested fixes to reduce token waste
