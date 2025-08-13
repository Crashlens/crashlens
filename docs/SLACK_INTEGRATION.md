# 🔔 Slack Integration Guide for CrashLens

This guide shows you how to integrate CrashLens with Slack to receive notifications about token waste and policy violations.

## 🚨 **Current State**

⚠️ **Important**: The `--slack-webhook` CLI parameter mentioned in some documentation **does not exist yet**. This guide shows you the working methods to integrate with Slack.

## 🛠️ **Integration Methods**

### **Method 1: GitHub Actions + Slack Action (Recommended)**

#### Step 1: Get Your Slack Webhook URL
1. Go to [Slack Apps](https://api.slack.com/apps)
2. Create a new app or select existing one
3. Go to "Incoming Webhooks" and activate them
4. Create a webhook for your channel
5. Copy the webhook URL (looks like: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX`)

#### Step 2: Add Webhook as GitHub Secret
1. In your GitHub repo, go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `SLACK_WEBHOOK_URL`
4. Value: Your webhook URL from Step 1
5. Click **Add secret**

#### Step 3: Update Your GitHub Workflow
Your workflow already has Slack integration added. Here's what it does:

```yaml
- name: Send Slack Notification
  if: always()  # Run even if previous steps fail
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
    custom_payload: |
      {
        "text": "🔍 CrashLens Analysis Complete",
        "blocks": [
          {
            "type": "section", 
            "text": {
              "type": "mrkdwn",
              "text": "*CrashLens Analysis Results*\\n• Repository: ${{ github.repository }}\\n• Branch: ${{ github.ref_name }}\\n• Status: ${{ job.status }}\\n• Run: <${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View Details>"
            }
          },
          {
            "type": "divider"
          },
          {
            "type": "context",
            "elements": [
              {
                "type": "mrkdwn", 
                "text": "📊 Check the artifacts for detailed analysis reports"
              }
            ]
          }
        ]
      }
```

### **Method 2: Custom Script with Python**

If you want more control, create a custom script:

#### Step 1: Create Slack Notification Script

```python
#!/usr/bin/env python3
"""
Custom Slack notifier for CrashLens results
"""

import os
import json
import requests
import sys
from pathlib import Path

def send_slack_notification(webhook_url: str, report_file: str):
    """Send CrashLens results to Slack"""
    
    # Read the report
    if not Path(report_file).exists():
        print(f"❌ Report file not found: {report_file}")
        return False
    
    with open(report_file, 'r') as f:
        report_content = f.read()
    
    # Extract key metrics (simple parsing)
    lines = report_content.split('\n')
    total_spend = "Unknown"
    potential_savings = "Unknown"
    
    for line in lines:
        if "Total AI Spend" in line:
            total_spend = line.split('**')[1] if '**' in line else line
        elif "Total Potential Savings" in line:
            potential_savings = line.split('**')[1] if '**' in line else line
    
    # Build Slack message
    payload = {
        "text": "🔍 CrashLens Analysis Complete",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*CrashLens Token Waste Analysis*\\n💰 Total Spend: {total_spend}\\n🎯 Potential Savings: {potential_savings}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{report_content[:1000]}{'...' if len(report_content) > 1000 else ''}```"
                }
            }
        ]
    }
    
    # Send to Slack
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Slack notification sent successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to send Slack notification: {e}")
        return False

if __name__ == "__main__":
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook_url:
        print("❌ SLACK_WEBHOOK_URL environment variable not set")
        sys.exit(1)
    
    report_file = sys.argv[1] if len(sys.argv) > 1 else "report.md"
    send_slack_notification(webhook_url, report_file)
```

#### Step 2: Use in Your Workflow

```yaml
- name: Run CrashLens Analysis
  run: |
    crashlens scan logs.jsonl --format markdown > crashlens-report.md
    
- name: Send to Slack
  run: |
    python slack_notifier.py crashlens-report.md
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### **Method 3: Manual Integration (Local)**

For local development or testing:

#### Step 1: Install requests
```bash
pip install requests
```

#### Step 2: Run CrashLens and Send to Slack
```bash
# Run analysis
crashlens scan logs.jsonl --format slack > report.txt

# Send to Slack (using curl)
curl -X POST -H 'Content-type: application/json' \
  --data "{'text':'$(cat report.txt)'}" \
  YOUR_WEBHOOK_URL
```

## 📋 **Webhook Secret Management**

### **For GitHub Actions:**
- Repository Secrets: `Settings` → `Secrets and variables` → `Actions`
- Add `SLACK_WEBHOOK_URL` as a secret

### **For Local Development:**
```bash
# Set environment variable
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Or use .env file (don't commit this!)
echo "SLACK_WEBHOOK_URL=https://hooks.slack.com/services/..." > .env
```

## 🎯 **Message Customization**

### **Basic Message:**
```json
{
  "text": "🔍 CrashLens found token waste worth $0.45"
}
```

### **Rich Block Message:**
```json
{
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Token Waste Alert*\\n💰 Potential savings: $0.45\\n🔍 Issues found: 12"
      }
    }
  ]
}
```

## 🔧 **Troubleshooting**

### **Common Issues:**

1. **"webhook_url not found"**
   - Check that `SLACK_WEBHOOK_URL` is set as a GitHub secret
   - Verify the secret name matches exactly

2. **"Message not delivered"**
   - Test your webhook URL manually with curl
   - Check if your Slack app has proper permissions

3. **"Invalid payload"**
   - Ensure JSON is properly formatted
   - Escape special characters in text

### **Testing Your Webhook:**
```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test from CrashLens"}' \
  YOUR_WEBHOOK_URL
```

## 🚀 **What's Next?**

The CrashLens CLI will eventually include native `--slack-webhook` support. Until then, these methods provide full Slack integration functionality.

---

💡 **Pro Tip**: Use the GitHub Actions method for automated notifications, and the Python script method for custom integrations.
