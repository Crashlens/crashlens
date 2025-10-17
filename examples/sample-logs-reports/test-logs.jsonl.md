🚨 *CrashLens Token Waste Report* 🚨
📊 *Analysis Date:* 2025-10-18 02:57:51

📋 *Report Summary:*
• 💰 *Total AI Spend:* $0.10
• 🔥 *Potential Savings:* $0.09
• 🎯 *Wasted Tokens:* 4,272
• ⚠️ *Issues Found:* 18
• 📈 *Traces Analyzed:* 13

🔄 *Retry Loop* • 8 traces • $0.07 wasted
   💡 *Fix:* exponential backoff
   🎯 *Wasted tokens:* 3,190
   🔗 *Traces (8):* `retry_9442330b, retry_ef493f8c, retry_0e89d768, retry_954e978d, retry_cc755128, +3 more`

❓ *Overkill Model* • 10 traces • $0.02 wasted
   💡 *Fix:* optimize usage
   🎯 *Wasted tokens:* 1,082
   🔗 *Traces (4):* `retry_c484645d, retry_a23e16d4, retry_f3265906, retry_2b039e1b`


🏆 *Top Expensive Traces:*
• #1 → `retry_93ab39c6` → gpt-4 → $0.02
• #2 → `retry_cc755128` → gpt-4 → $0.02
• #3 → `retry_f3265906` → gpt-4 → $0.01

🤖 *Cost by Model:*
• gpt-4 → $0.07 (66%)
• gpt-4-turbo → $0.02 (24%)
• gpt-4o → $0.0095 (9%)

💡 *Next Steps:*
• Run `crashlens --detailed` for grouped JSON reports
• Review trace patterns to optimize model routing
• Implement suggested fixes to reduce token waste
