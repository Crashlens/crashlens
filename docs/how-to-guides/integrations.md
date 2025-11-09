# CrashLens Integrations Guide

This guide covers all integration methods for CrashLens, including Slack notifications, email reports, and third-party services.

---

## Table of Contents

1. [Slack Integration](#slack-integration)
2. [Email Reports (SMTP)](#email-reports-smtp)
3. [Report Command](#report-command)
4. [CI/CD Integration](#cicd-integration)
5. [Webhooks & Custom Scripts](#webhooks--custom-scripts)

---

## Slack Integration

### Overview

CrashLens can send notifications to Slack using webhooks. There are multiple integration methods depending on your use case.

### Method 1: GitHub Actions + Slack Action (Recommended)

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

### Method 2: Custom Script with Python

If you want more control, create a custom script:

#### Step 1: Create Slack Notification Script

Create `slack_notifier.py`:

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

### Method 3: Using Report Command with Slack Output

```bash
# Slack notification with week-over-week delta
crashlens report current-week.jsonl \
  --previous-logs last-week.jsonl \
  --output slack \
  --webhook-url $SLACK_WEBHOOK
```

### Webhook Secret Management

#### For GitHub Actions:
- Repository Secrets: `Settings` → `Secrets and variables` → `Actions`
- Add `SLACK_WEBHOOK_URL` as a secret

#### For Local Development:
```bash
# Set environment variable
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Or use .env file (don't commit this!)
echo "SLACK_WEBHOOK_URL=https://hooks.slack.com/services/..." > .env
```

### Message Customization

#### Basic Message:
```json
{
  "text": "🔍 CrashLens found token waste worth $0.45"
}
```

#### Rich Block Message:
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

### Troubleshooting Slack Integration

#### Common Issues:

**1. "webhook_url not found"**
- Check that `SLACK_WEBHOOK_URL` is set as a GitHub secret
- Verify the secret name matches exactly

**2. "Message not delivered"**
- Test your webhook URL manually with curl
- Check if your Slack app has proper permissions

**3. "Invalid payload"**
- Ensure JSON is properly formatted
- Escape special characters in text

#### Testing Your Webhook:
```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test from CrashLens"}' \
  YOUR_WEBHOOK_URL
```

---

## Email Reports (SMTP)

### Overview

CrashLens can send cost digest reports via email with HTML formatting and optional attachments.

### SMTP Configuration

#### Method 1: Environment Variables

Set environment variables for SMTP credentials:

```bash
export SMTP_SERVER=smtp.gmail.com      # Default
export SMTP_PORT=587                   # Default
export SMTP_USER=your-email@example.com
export SMTP_PASSWORD=your-app-password
export SMTP_FROM=noreply@example.com   # Optional (defaults to SMTP_USER)
```

#### Method 2: Configuration File (Recommended)

Create `.crashlens/smtp.yaml`:

```bash
crashlens config smtp-example
```

This creates:

```yaml
# CrashLens SMTP Configuration
# Environment variables override these values

server: smtp.gmail.com
port: 587
user: alerts@example.com
password: your-app-specific-password
from: CrashLens Alerts <alerts@example.com>
use_tls: true
timeout: 30
```

**Configuration Precedence** (highest to lowest):
1. Environment Variables (highest priority)
2. YAML Configuration File
3. No defaults - all required fields must be provided

### Gmail Setup

For Gmail accounts:

1. Enable 2-factor authentication in Google Account settings
2. Generate an App Password:
   - Go to: https://myaccount.google.com/apppasswords
   - Create app password for "Mail"
   - Use this password for `SMTP_PASSWORD`

**Example**:
```bash
export SMTP_USER=yourname@gmail.com
export SMTP_PASSWORD=abcd efgh ijkl mnop  # 16-char app password
crashlens report logs.jsonl --email team@company.com
```

### Office 365 / Outlook Setup

```bash
export SMTP_SERVER=smtp.office365.com
export SMTP_PORT=587
export SMTP_USER=yourname@company.com
export SMTP_PASSWORD=your-password
crashlens report logs.jsonl --email team@company.com
```

### HTML Email Features

Reports sent via `--email` include:

- **Subject**: "📊 CrashLens Cost Digest Report"
- **From**: Value of `SMTP_FROM` (or `SMTP_USER`)
- **To**: Email address provided via `--email` flag
- **Body**: Multipart MIME (plaintext + HTML)
  - **Plain text**: Readable in basic email clients
  - **HTML**: Bootstrap-styled formatting for modern clients

**HTML Email Features**:
- Responsive design (mobile-friendly)
- Color-coded sections
- Inline CSS for maximum compatibility
- Clean typography with system fonts

### Attaching HTML Reports

Attach detailed HTML policy violation reports to cost digest emails:

```bash
# Step 1: Run guard with HTML output
crashlens guard logs.jsonl \
  --policy-file policies/production.yaml \
  --format html \
  --output guard-$(date +%Y%m%d).html

# Step 2: Send report with HTML attachment
crashlens report logs.jsonl \
  --email team@example.com \
  --attach-html guard-$(date +%Y%m%d).html
```

**Output:**
```
✅ Guard completed (found 3 violations, 0 suppressed)
📄 Report saved: guard-20240115.html
✅ Report sent via email to team@example.com (with attachment: guard-20240115.html)
```

### Error Handling

**Missing credentials**:
```
❌ Email sending requires SMTP_USER and SMTP_PASSWORD environment variables

💡 Set environment variables:
   export SMTP_SERVER=smtp.gmail.com  # (default)
   export SMTP_PORT=587  # (default)
   export SMTP_USER=your-email@example.com
   export SMTP_PASSWORD=your-app-password
   export SMTP_FROM=noreply@example.com  # (optional)
```

**Authentication failure**:
```
❌ SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD
```

**Connection errors**:
```
❌ SMTP error: [Errno 61] Connection refused
```

---

## Report Command

### Overview

`crashlens report` generates cost digest summaries from JSONL logs with week-over-week tracking.

### Quick Start

```bash
# Basic markdown report
crashlens report logs.jsonl

# Slack notification with delta
crashlens report current-week.jsonl \
  --previous-logs last-week.jsonl \
  --output slack \
  --webhook-url $SLACK_WEBHOOK

# Email digest with HTML formatting
export SMTP_USER=your-email@example.com
export SMTP_PASSWORD=your-app-password
crashlens report logs.jsonl \
  --output md \
  --email team@example.com

# Week-over-week comparison
crashlens report week2.jsonl \
  --previous-logs week1.jsonl \
  --output text
```

### Command Syntax

```bash
crashlens report LOGFILE [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` | choice | `md` | Output format: `slack`, `md`, `text` |
| `--webhook-url` | string | - | Slack webhook URL for posting reports |
| `--email` | string | - | Email address to send report to (requires SMTP config) |
| `--previous-logs` | path | - | Previous period logs for week-over-week comparison |
| `--attach-html` | path | - | HTML file to attach to email (e.g., guard report) |

### Output Formats

#### 1. Markdown (`--output md`)

**Example**:
```markdown
# 📊 CrashLens Cost Digest

**Log File**: `logs.jsonl`
**Total Spend**: $1.33 (↑ $1.33, +100.0%)
**Total Tokens**: 7,900
**Retries**: 3
**Fallbacks**: 1

## 💰 Cost by Model

- **gpt-4o**: $1.30 (3 requests, 7,000 tokens)
- **gpt-3.5-turbo**: $0.03 (3 requests, 900 tokens)
```

#### 2. Plain Text (`--output text`)

**Example**:
```
============================================================
CrashLens Cost Digest
============================================================
Log File: logs.jsonl
Total Spend: $1.33 (↑ $1.33, +100.0%)
Total Tokens: 7,900
```

#### 3. Slack Block Kit (`--output slack`)

Sends formatted blocks to Slack webhook with cost breakdown and trends.

### Week-over-Week Comparison

Compare current period against previous period:

```bash
crashlens report current.jsonl --previous-logs previous.jsonl
```

**Trend Indicators:**

| Icon | Meaning | Calculation |
|------|---------|-------------|
| ↑ | Increase | Current cost > Previous cost |
| ↓ | Decrease | Current cost < Previous cost |
| → | No change | Current cost = Previous cost |

---

## CI/CD Integration

### GitHub Actions Example: Weekly Cost Monitoring

```yaml
name: Weekly Cost Monitoring

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9 AM UTC

jobs:
  cost-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install CrashLens
        run: pip install crashlens
      
      - name: Fetch logs from Langfuse
        run: |
          crashlens scan \
            --from-langfuse \
            --hours-back 168 \
            --limit 10000 \
            > current-week.jsonl
        env:
          LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
          LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
      
      - name: Run policy check (generate HTML)
        run: |
          crashlens guard current-week.jsonl \
            --policy-file policies/weekly-budget.yaml \
            --format html \
            --output guard-weekly.html
        continue-on-error: true
      
      - name: Send weekly report with violations
        run: |
          crashlens report current-week.jsonl \
            --email ${{ secrets.TEAM_EMAIL }} \
            --attach-html guard-weekly.html
        env:
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
      
      - name: Send Slack notification
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### GitLab CI Example

```yaml
cost-report:
  stage: report
  only:
    - schedules
  script:
    - pip install crashlens
    - crashlens report logs.jsonl --output md --email $TEAM_EMAIL
  variables:
    SMTP_USER: $SMTP_USERNAME
    SMTP_PASSWORD: $SMTP_APP_PASSWORD
```

---

## Webhooks & Custom Scripts

### Daily Slack Notification Script

Create `daily-slack.sh`:

```bash
#!/bin/bash
# daily-slack.sh

TODAY=$(date +%Y-%m-%d)
YESTERDAY=$(date -d '1 day ago' +%Y-%m-%d)

crashlens report "logs/${TODAY}.jsonl" \
  --previous-logs "logs/${YESTERDAY}.jsonl" \
  --output slack \
  --webhook-url $SLACK_WEBHOOK
```

### Monthly Email Report Script

Create `monthly-report.sh`:

```bash
#!/bin/bash
# monthly-report.sh

CURRENT_MONTH=$(date +%Y-%m)
PREVIOUS_MONTH=$(date -d '1 month ago' +%Y-%m)

crashlens report "logs/${CURRENT_MONTH}.jsonl" \
  --previous-logs "logs/${PREVIOUS_MONTH}.jsonl" \
  --output md \
  --email engineering@company.com
```

### Cron Job Setup

```cron
# Weekly digest every Monday at 9 AM
0 9 * * 1 /path/to/weekly-digest.sh

# Daily slack update at 10 AM
0 10 * * * /path/to/daily-slack.sh
```

---

## Best Practices

### 1. Secure Credential Management

**Never** hardcode credentials in scripts:

```bash
# ❌ Bad
export SMTP_PASSWORD=mypassword123

# ✅ Good - Use CI/CD secrets
export SMTP_PASSWORD=${{ secrets.SMTP_APP_PASSWORD }}

# ✅ Good - Use password manager
export SMTP_PASSWORD=$(pass show smtp/crashlens)
```

### 2. Graceful Degradation

Handle missing previous logs gracefully:

```bash
PREVIOUS_LOGS="logs/previous.jsonl"

if [ -f "$PREVIOUS_LOGS" ]; then
  crashlens report current.jsonl \
    --previous-logs "$PREVIOUS_LOGS"
else
  echo "⚠️  No previous logs found, skipping delta calculation"
  crashlens report current.jsonl
fi
```

### 3. Multi-Channel Notifications

Send reports to multiple channels:

```bash
# Generate report once
crashlens report current.jsonl \
  --previous-logs previous.jsonl \
  --output md > report.md

# Send to Slack
crashlens report current.jsonl \
  --previous-logs previous.jsonl \
  --output slack \
  --webhook-url $SLACK_WEBHOOK

# Send to email
crashlens report current.jsonl \
  --previous-logs previous.jsonl \
  --output md \
  --email team@company.com
```

### 4. Consistent Log Retention

Store logs with predictable naming patterns:

```
logs/
  2025-W01.jsonl  # Week 1
  2025-W02.jsonl  # Week 2
  2025-01.jsonl   # January
  2025-02.jsonl   # February
```

---

## Troubleshooting

### Issue: Email sending fails with authentication error

**Cause**: Invalid SMTP credentials or app password required

**Solutions**:
1. For Gmail: Use App Password (not regular password)
2. For Office 365: Enable "Authenticated SMTP"
3. Check firewall allows outbound port 587

### Issue: Slack webhook returns 404

**Cause**: Webhook URL is invalid or deactivated

**Solutions**:
1. Verify webhook URL is correct
2. Check webhook is still active in Slack settings
3. Regenerate webhook if necessary

### Issue: No data in report (all $0.00)

**Cause**: Log entries missing `cost_usd` field or field is null

**Solution**: Ensure logs include cost data:
```json
{"model": "gpt-4o", "cost_usd": 0.05, "tokens": 1000}
```

---

## FAQ

**Q: Can I send to multiple emails?**  
A: Not directly. Use a distribution list/alias instead, or call the command multiple times with different `--email` values.

**Q: Can I customize the email subject line?**  
A: Not currently. The subject is fixed as "📊 CrashLens Cost Digest Report". Feature request welcomed!

**Q: Does `--previous-logs` work with Slack output?**  
A: Yes! The delta is shown inline in the "Total Spend" field of the Slack message.

**Q: Is STARTTLS required for SMTP?**  
A: Yes, CrashLens uses STARTTLS for secure connections. Plain SMTP (port 25) is not supported.

**Q: Can I use this with self-hosted SMTP servers?**  
A: Yes, set `SMTP_SERVER` and `SMTP_PORT` to your server's values.

---

**See Also**:
- [CI/CD Integration Guide](./ci-cd-integration.md) - Detailed CI/CD patterns
- [Guard Documentation](./guard.md) - Policy enforcement
- [Observability Guide](./observability.md) - Metrics and monitoring
