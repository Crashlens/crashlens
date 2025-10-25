# CrashLens Report Command - Cost Digest & Week-over-Week Tracking

## Overview

`crashlens report` generates cost digest summaries from JSONL logs, providing quick aggregate statistics by model and endpoint. It's designed for weekly team digests, Slack notifications, and email reports with week-over-week cost tracking.

## Quick Start

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

## Features

- **Cost aggregation**: Total spend, tokens, retries, fallbacks
- **Model breakdown**: Per-model cost and usage statistics
- **Endpoint analysis**: Cost distribution across API endpoints
- **Week-over-week delta**: Automatic trend indicators (↑↓→) with percentage change
- **Multiple outputs**: Markdown, plain text, or Slack Block Kit JSON
- **Email delivery**: SMTP support with HTML formatting
- **Slack integration**: Direct webhook posting

## Command Syntax

```bash
crashlens report LOGFILE [OPTIONS]
```

### Arguments

- `LOGFILE`: Path to JSONL log file containing cost data

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` | choice | `md` | Output format: `slack`, `md`, `text` |
| `--webhook-url` | string | - | Slack webhook URL for posting reports |
| `--email` | string | - | Email address to send report to (requires SMTP config) |
| `--previous-logs` | path | - | Previous period logs for week-over-week comparison |

### Exit Codes

- `0`: Report generated successfully
- `1`: Error reading log file or sending notification
- `2`: Missing required parameter (e.g., nonexistent file)

## Log Format

Report expects JSONL files where each line is a JSON object with cost fields:

```json
{
  "model": "gpt-4o",
  "tokens": 2500,
  "cost_usd": 0.25,
  "endpoint": "/api/generate",
  "retry_count": 0,
  "fallback_triggered": false
}
```

**Required fields**: None (graceful defaults for missing fields)

**Recognized fields**:
- `model`: Model name (defaults to "unknown")
- `tokens`: Token count (defaults to 0)
- `cost_usd`: Cost in USD (defaults to 0.0)
- `endpoint`: API endpoint (defaults to "unknown")
- `retry_count`: Number of retries (defaults to 0)
- `fallback_triggered`: Whether fallback was used (defaults to false)

## Output Formats

### 1. Markdown (`--output md`)

**Example**:
```markdown
# 📊 CrashLens Cost Digest

**Log File**: `logs.jsonl`
**Total Spend**: $1.33 (↑ $1.33, +100.0%)
**Total Tokens**: 7,900
**Retries**: 3
**Fallbacks**: 1

### 📈 Week-over-Week Comparison

- **Previous Period**: $0.00
- **Current Period**: $1.33
- **Change**: ↑ $1.33 (+100.0%)

## 💰 Cost by Model

- **gpt-4o**: $1.30 (3 requests, 7,000 tokens)
- **gpt-3.5-turbo**: $0.03 (3 requests, 900 tokens)

## 🔗 Cost by Endpoint

- **/api/generate**: $1.31 (5 requests)
- **/api/stream**: $0.02 (1 requests)
```

**Best for**: Internal documentation, README updates, wiki pages

### 2. Plain Text (`--output text`)

**Example**:
```
============================================================
CrashLens Cost Digest
============================================================
Log File: logs.jsonl
Total Spend: $1.33 (↑ $1.33, +100.0%)
Total Tokens: 7,900
Retries: 3
Fallbacks: 1

Week-over-Week Comparison:
  Previous: $0.00
  Current: $1.33
  Change: ↑ $1.33 (+100.0%)

Cost by Model:
  gpt-4o: $1.30 (3 requests)
  gpt-3.5-turbo: $0.03 (3 requests)

Cost by Endpoint:
  /api/generate: $1.31 (5 requests)
  /api/stream: $0.02 (1 requests)
```

**Best for**: Terminal output, log files, email bodies (plaintext)

### 3. Slack Block Kit (`--output slack`)

**Example**:
```json
{
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "📊 CrashLens Cost Digest"
      }
    },
    {
      "type": "section",
      "fields": [
        {
          "type": "mrkdwn",
          "text": "*Total Spend:*\n$1.33\n↑ $1.33 (+100.0%)"
        },
        {
          "type": "mrkdwn",
          "text": "*Total Tokens:*\n7,900"
        },
        {
          "type": "mrkdwn",
          "text": "*Retries:*\n3"
        },
        {
          "type": "mrkdwn",
          "text": "*Fallbacks:*\n1"
        }
      ]
    },
    {
      "type": "divider"
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*💰 Top Models by Cost:*"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "• *gpt-4o*: $1.30 (3 requests)"
      }
    }
  ]
}
```

**Best for**: Slack webhook integrations, team notifications

## Week-over-Week Comparison

### Basic Usage

Compare current period against previous period by providing both log files:

```bash
crashlens report current.jsonl --previous-logs previous.jsonl
```

### Trend Indicators

| Icon | Meaning | Calculation |
|------|---------|-------------|
| ↑ | Increase | Current cost > Previous cost |
| ↓ | Decrease | Current cost < Previous cost |
| → | No change | Current cost = Previous cost |

### Delta Calculation

```
Delta ($) = Current Cost - Previous Cost
Delta (%) = (Delta $ / Previous Cost) × 100
```

**Special cases**:
- Previous cost = $0, Current cost > $0: Shows +100%
- Previous cost = $0, Current cost = $0: Shows no delta
- Previous cost > $0, Current cost = $0: Shows -100%

### Example Output Snippets

**Increase (50%)**:
```
Total Spend: $150.00 (↑ $50.00, +50.0%)
```

**Decrease (33%)**:
```
Total Spend: $100.00 (↓ $50.00, -33.3%)
```

**No change**:
```
Total Spend: $100.00 (→ $0.00, +0.0%)
```

## SMTP Email Delivery

### Configuration

Set environment variables for SMTP credentials:

```bash
export SMTP_SERVER=smtp.gmail.com      # Default
export SMTP_PORT=587                   # Default
export SMTP_USER=your-email@example.com
export SMTP_PASSWORD=your-app-password
export SMTP_FROM=noreply@example.com   # Optional (defaults to SMTP_USER)
```

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

### Email Format

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

## Slack Integration

### Webhook Setup

1. Create incoming webhook in Slack:
   - Go to: https://api.slack.com/messaging/webhooks
   - Select workspace and channel
   - Copy webhook URL

2. Store webhook URL securely:
   ```bash
   export SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   ```

### Usage

**Without delta**:
```bash
crashlens report logs.jsonl \
  --output slack \
  --webhook-url $SLACK_WEBHOOK
```

**With week-over-week delta**:
```bash
crashlens report current.jsonl \
  --previous-logs previous.jsonl \
  --output slack \
  --webhook-url $SLACK_WEBHOOK
```

### Success Output

```
✅ Report sent to Slack successfully
```

### Error Output

**Invalid webhook URL**:
```
❌ Failed to send to Slack: 404
```

**Network error**:
```
❌ Error sending to Slack: Connection timeout
```

**Missing requests library**:
```
❌ requests library not installed. Install with: pip install requests
```

## Usage Examples

### Example 1: Weekly Team Digest (Email)

```bash
#!/bin/bash
# weekly-digest.sh

# Configuration
CURRENT_LOGS="logs/week-$(date +%V).jsonl"
PREVIOUS_LOGS="logs/week-$(date -d '7 days ago' +%V).jsonl"
TEAM_EMAIL="eng-team@company.com"

# SMTP credentials from environment (set in CI/CD secrets)
export SMTP_USER=$SMTP_USERNAME
export SMTP_PASSWORD=$SMTP_APP_PASSWORD

# Generate and send report
crashlens report "$CURRENT_LOGS" \
  --previous-logs "$PREVIOUS_LOGS" \
  --output md \
  --email "$TEAM_EMAIL"
```

### Example 2: Daily Slack Notification

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

### Example 3: Month-over-Month Comparison

```bash
#!/bin/bash
# monthly-report.sh

CURRENT_MONTH=$(date +%Y-%m)
PREVIOUS_MONTH=$(date -d '1 month ago' +%Y-%m)

crashlens report "logs/${CURRENT_MONTH}.jsonl" \
  --previous-logs "logs/${PREVIOUS_MONTH}.jsonl" \
  --output md > "reports/${CURRENT_MONTH}.md"

echo "Report saved to reports/${CURRENT_MONTH}.md"
```

### Example 4: CI/CD Pipeline Integration

```yaml
# .github/workflows/weekly-digest.yml
name: Weekly Cost Digest

on:
  schedule:
    - cron: '0 9 * * MON'  # Every Monday at 9 AM UTC

jobs:
  digest:
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
      
      - name: Send digest to Slack
        env:
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK_URL }}
        run: |
          crashlens report current-week.jsonl \
            --previous-logs previous-week.jsonl \
            --output slack \
            --webhook-url $SLACK_WEBHOOK
      
      - name: Archive logs
        run: mv current-week.jsonl previous-week.jsonl
```

## Best Practices

### 1. Consistent Log Retention

Store logs with predictable naming patterns:

```
logs/
  2025-W01.jsonl  # Week 1
  2025-W02.jsonl  # Week 2
  2025-01.jsonl   # January
  2025-02.jsonl   # February
```

### 2. Automated Scheduling

Use cron jobs or CI/CD schedules for consistent reporting:

```cron
# Weekly digest every Monday at 9 AM
0 9 * * 1 /path/to/weekly-digest.sh

# Daily slack update at 10 AM
0 10 * * * /path/to/daily-slack.sh
```

### 3. Secure Credential Management

**Never** hardcode credentials in scripts:

```bash
# ❌ Bad
export SMTP_PASSWORD=mypassword123

# ✅ Good - Use CI/CD secrets
export SMTP_PASSWORD=${{ secrets.SMTP_APP_PASSWORD }}

# ✅ Good - Use password manager
export SMTP_PASSWORD=$(pass show smtp/crashlens)
```

### 4. Graceful Degradation

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

### 5. Multi-Channel Notifications

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

## Troubleshooting

### Issue: No data in report (all $0.00)

**Cause**: Log entries missing `cost_usd` field or field is null

**Solution**: Ensure logs include cost data:
```json
{"model": "gpt-4o", "cost_usd": 0.05, "tokens": 1000}
```

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

### Issue: Week-over-week shows +100% when it shouldn't

**Cause**: Previous logs file is empty or has $0.00 total

**Explanation**: When previous cost is $0, any increase shows as +100% (expected behavior)

**Solution**: Ensure previous logs contain actual cost data

## FAQ

**Q: Can I send to multiple emails?**  
A: Not directly. Use a distribution list/alias instead, or call the command multiple times with different `--email` values.

**Q: Can I customize the email subject line?**  
A: Not currently. The subject is fixed as "📊 CrashLens Cost Digest Report". Feature request welcomed!

**Q: Does `--previous-logs` work with Slack output?**  
A: Yes! The delta is shown inline in the "Total Spend" field of the Slack message.

**Q: Can I compare more than 2 time periods?**  
A: Not directly. You can generate multiple reports and compare manually.

**Q: Is STARTTLS required for SMTP?**  
A: Yes, CrashLens uses STARTTLS for secure connections. Plain SMTP (port 25) is not supported.

**Q: Can I use this with self-hosted SMTP servers?**  
A: Yes, set `SMTP_SERVER` and `SMTP_PORT` to your server's values.

**Q: Does this work without internet access?**  
A: Yes, for basic reports. Slack webhooks and SMTP email require internet.

---

**See also**:
- [Guard Command Documentation](./GUARD.md) - Policy enforcement
- [User Manual](./USER_MANUAL.md) - Complete CrashLens guide
- [Command Reference](./COMMAND-REFERENCE.md) - All CLI commands
