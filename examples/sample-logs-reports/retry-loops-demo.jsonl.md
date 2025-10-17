🚨 *CrashLens Token Waste Report* 🚨
📊 *Analysis Date:* 2025-10-18 02:57:38

📋 *Report Summary:*
• 💰 *Total AI Spend:* $0.01
• 🔥 *Potential Savings:* $0.01
• 🎯 *Wasted Tokens:* 1,639
• ⚠️ *Issues Found:* 3
• 📈 *Traces Analyzed:* 3

🔄 *Retry Loop* • 3 traces • $0.01 wasted
   💡 *Fix:* exponential backoff
   🎯 *Wasted tokens:* 1,639
   🔗 *Traces (3):* `retry_f908e1b6, retry_fd054f72, retry_6c0ab209`


🏆 *Top Expensive Traces:*
• #1 → `retry_6c0ab209` → gpt-4o → $0.0051
• #2 → `retry_fd054f72` → gpt-4o → $0.0031
• #3 → `retry_f908e1b6` → gpt-4o → $0.0025

🤖 *Cost by Model:*
• gpt-4o → $0.01 (100%)

💡 *Next Steps:*
• Run `crashlens --detailed` for grouped JSON reports
• Review trace patterns to optimize model routing
• Implement suggested fixes to reduce token waste
