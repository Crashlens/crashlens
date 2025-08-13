# 🔗 CrashLens Webhook Integration Guide

This guide shows how to run CrashLens with webhook notifications for Slack, Discord, Teams, or any webhook service.

## 🛠️ Setup Instructions

### Step 1: Get Your Webhook URL

#### For Slack:
1. Go to [https://api.slack.com/apps](https://api.slack.com/apps)
2. Create new app → "From scratch"
3. Go to "Incoming Webhooks" → Turn ON
4. "Add New Webhook to Workspace" → Choose channel
5. Copy webhook URL (looks like `https://hooks.slack.com/services/T.../B.../...`)

#### For Discord:
1. Go to your Discord server settings
2. Integrations → Webhooks → New Webhook
3. Choose channel and copy webhook URL

#### For Microsoft Teams:
1. Go to your Teams channel
2. ... → Connectors → Incoming Webhook
3. Configure and copy webhook URL

### Step 2: Set Environment Variable

#### Windows PowerShell:
```powershell
# For current session
$env:CRASHLENS_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
$env:PYTHONIOENCODING = "utf-8"

# Permanently 
setx CRASHLENS_WEBHOOK_URL "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
setx PYTHONIOENCODING "utf-8"
```

#### Linux/Mac:
```bash
export CRASHLENS_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
export PYTHONIOENCODING="utf-8"

# Add to ~/.bashrc or ~/.zshrc for permanent
echo 'export CRASHLENS_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"' >> ~/.bashrc
```

### Step 3: Use the Webhook Script

The `crashlens_webhook.py` script is ready to use! Here's how:

## 📋 Usage Examples

### Basic Scans with Webhook:
```powershell
# Demo mode
python crashlens_webhook.py scan --demo

# Scan specific file
python crashlens_webhook.py scan logs.jsonl

# Summary mode
python crashlens_webhook.py scan logs.jsonl --summary

# Different formats
python crashlens_webhook.py scan logs.jsonl --format markdown
```

### Policy Checks with Webhook:
```powershell
# Specific template
python crashlens_webhook.py policy-check logs.jsonl --policy-template retry-loop-prevention

# All templates
python crashlens_webhook.py policy-check logs.jsonl --policy-template all

# With failure on violations
python crashlens_webhook.py policy-check logs.jsonl --policy-template all --fail-on-violations
```

### Generate and Analyze:
```powershell
# Generate test data, then analyze with webhook
python -m crashlens simulate --output new-test.jsonl --count 100 --scenario model-overkill
python crashlens_webhook.py scan new-test.jsonl --summary
```

## 🎯 What Gets Sent to Webhook

The webhook receives a Slack-compatible message with:

- ✅ Analysis status (Success/Error/Warning)
- 📊 Key metrics (traces analyzed, total cost)
- ⏰ Timestamp
- 📄 Full CrashLens output (truncated to 800 characters)

### Example Webhook Message:
```json
{
  "text": "✅ CrashLens Analysis Complete",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*CrashLens Token Waste Analysis*\n🔍 Status: Success\n📊 Traces Analyzed: 13\n💰 Total Cost: $0.10\n⏰ Run Time: 2025-08-14 03:58:50"
      }
    },
    {
      "type": "divider"
    },
    {
      "type": "section", 
      "text": {
        "type": "mrkdwn",
        "text": "```[CrashLens output here]```"
      }
    }
  ]
}
```

## 🔧 Advanced Usage

### Batch Processing:
```powershell
# Process multiple files
$files = Get-ChildItem *.jsonl
foreach ($file in $files) {
    python crashlens_webhook.py scan $file.Name --summary
}
```

### Scheduled Runs:
```powershell
# Windows Task Scheduler or cron job
python crashlens_webhook.py scan daily-logs.jsonl --policy-template all --fail-on-violations
```

### CI/CD Integration:
```yaml
# GitHub Actions example
- name: Run CrashLens with Webhook
  run: |
    python crashlens_webhook.py policy-check logs/*.jsonl --policy-template all
  env:
    CRASHLENS_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
    PYTHONIOENCODING: utf-8
```

## 🚨 Troubleshooting

### Common Issues:

1. **"CRASHLENS_WEBHOOK_URL not set"**
   - Set the environment variable as shown above

2. **"Failed to send webhook notification"**
   - Check webhook URL is correct
   - Test manually: `curl -X POST -H 'Content-Type: application/json' -d '{"text":"test"}' YOUR_WEBHOOK_URL`

3. **Encoding errors**
   - Always set `PYTHONIOENCODING=utf-8`
   - Use PowerShell (not CMD) on Windows

4. **Webhook not received**
   - Check if webhook service is working
   - Verify channel permissions
   - Check firewall/network settings

### Test Your Setup:
```powershell
# Quick test
python crashlens_webhook.py scan --demo
```

If you see "✅ Webhook notification sent successfully", everything is working!

## 🎉 You're Ready!

Now you can run CrashLens and automatically get results in your Slack/Discord/Teams channels. Perfect for:

- 🏢 Team notifications
- 📊 Daily cost reports 
- 🚨 Policy violation alerts
- 📈 Automated monitoring

---

*The webhook script supports all CrashLens commands and automatically formats results for easy sharing!*
