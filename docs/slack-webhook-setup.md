# Slack Webhook Integration for CrashLens

CrashLens now supports sending daily cost violation alerts to Slack channels via webhooks. This feature allows teams to stay informed about policy violations and take action on cost-related issues proactively.

## Setup

### 1. Create a Slack App and Webhook URL

1. Go to [Slack App Management](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "CrashLens Alerts") and select your workspace
4. Go to "Incoming Webhooks" in the sidebar
5. Toggle "Activate Incoming Webhooks" to On
6. Click "Add New Webhook to Workspace"
7. Select the channel where you want alerts sent
8. Copy the generated webhook URL (starts with `https://hooks.slack.com/services/...`)

### 2. Configure Policy Rules

Create a policy file (`.yaml`) defining cost violation rules:

```yaml
# policy.yaml
rules:
  - id: "expensive-model-usage"
    description: "Detect usage of expensive models"
    severity: "high"
    action: "warn"
    match:
      "input.model": "gpt-4"
    suggestion: "Consider using gpt-3.5-turbo for simpler tasks"
  
  - id: "high-token-consumption"
    description: "Detect excessive token usage"
    severity: "medium"
    action: "warn"
    match:
      "usage.total_tokens >": 5000
    suggestion: "Break down large prompts into smaller chunks"
    
  - id: "cost-threshold-exceeded"
    description: "High cost per request"
    severity: "critical"
    action: "block"
    match:
      "cost >": 0.50
    suggestion: "Review prompt efficiency and model selection"
```

## Usage

### Manual Testing

Test your webhook configuration:

```bash
# Test with a specific log file
crashlens scan logs.jsonl --policy policy.yaml --slack-webhook "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Test with summary mode (recommended for daily alerts)
crashlens scan logs.jsonl --policy policy.yaml --summary --slack-webhook "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### Daily Automated Alerts

Set up a cronjob for daily cost violation monitoring:

#### Linux/macOS Cron Example

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 9:00 AM
0 9 * * * cd /path/to/your/project && /usr/local/bin/crashlens scan logs/daily.jsonl --policy policy.yaml --summary --slack-webhook "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" >> /var/log/crashlens-alerts.log 2>&1
```

#### Windows Task Scheduler Example

Create a batch file `daily-crashlens-alert.bat`:

```batch
@echo off
cd /d "C:\path\to\your\project"
crashlens scan logs\daily.jsonl --policy policy.yaml --summary --slack-webhook "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

Then create a scheduled task:
1. Open Task Scheduler
2. Click "Create Basic Task"
3. Set trigger to "Daily" at your preferred time
4. Set action to run your batch file

#### Docker/Kubernetes Example

```yaml
# kubernetes-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: crashlens-daily-alert
spec:
  schedule: "0 9 * * *"  # Daily at 9:00 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: crashlens
            image: your-crashlens-image:latest
            command:
            - /bin/sh
            - -c
            - |
              crashlens scan /data/logs/daily.jsonl \
                --policy /config/policy.yaml \
                --summary \
                --slack-webhook "$SLACK_WEBHOOK_URL"
            env:
            - name: SLACK_WEBHOOK_URL
              valueFrom:
                secretKeyRef:
                  name: slack-webhook
                  key: url
            volumeMounts:
            - name: logs
              mountPath: /data/logs
            - name: config
              mountPath: /config
          volumes:
          - name: logs
            persistentVolumeClaim:
              claimName: logs-pvc
          - name: config
            configMap:
              name: crashlens-policy
          restartPolicy: OnFailure
```

## Message Format

Slack alerts use Block Kit formatting and include:

- **Header**: Number of violations and estimated cost waste
- **Rule Breakdown**: Violations grouped by rule ID with counts and costs
- **Suggestions**: Actionable recommendations for each rule
- **Footer**: Timestamp and command to fix violations

Example message:
```
⚠️ 15 cost policy violations found • Estimated waste: $2.34

high-cost-model-usage • 12x violations • $1.89
💡 Consider using gpt-3.5-turbo for simpler tasks

large-token-usage • 3x violations • $0.45
💡 Break down large prompts into smaller chunks

Run `crashlens scan` to fix violations • 2025-01-15 09:00:00
```

## Error Handling

CrashLens handles webhook failures gracefully:

- **Network errors**: Prints error message, continues execution
- **Invalid webhook URL**: Shows connection error
- **Slack API errors**: Displays HTTP status and response
- **No violations**: Skips sending alert (saves Slack API calls)

Example error output:
```
❌ Failed to send Slack alert: HTTPSConnectionPool(host='hooks.slack.com', port=443): Max retries exceeded
⚠️  Failed to send Slack alert (see error above)
```

## Best Practices

### 1. Use Summary Mode
Always use `--summary` for daily alerts as it provides cost breakdown and trace analysis without overwhelming detail.

### 2. Set Appropriate Thresholds
Configure policy rules with realistic thresholds for your usage patterns:
- Start with warning thresholds, then tighten based on results
- Use `action: "warn"` for initial monitoring
- Escalate to `action: "block"` for critical cost violations

### 3. Monitor Alert Frequency
- Test webhook with small log samples first
- Consider rate limiting in policy rules to avoid alert spam
- Use different channels for different severity levels

### 4. Secure Webhook URLs
- Store webhook URLs as environment variables or secrets
- Rotate webhook URLs periodically
- Restrict Slack app permissions to minimum required

### 5. Log Rotation
For automated setups, ensure log rotation to prevent disk space issues:

```bash
# Add to logrotate configuration
/var/log/crashlens-alerts.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
}
```

## Troubleshooting

### Webhook Not Working
1. Verify webhook URL is correct and active
2. Check network connectivity to Slack
3. Test with a simple curl command:
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test message"}' \
     YOUR_WEBHOOK_URL
   ```

### No Alerts Sent
1. Ensure policy violations are being detected (`--summary` shows violations)
2. Check if policy file is correctly formatted
3. Verify log files contain expected data format

### Too Many Alerts
1. Adjust policy thresholds to reduce noise
2. Use `action: "warn"` instead of `"block"` for less critical rules
3. Consider grouping rules or using time-based aggregation

For additional support, check the CrashLens documentation or create an issue on GitHub.
