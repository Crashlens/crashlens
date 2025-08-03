#!/bin/bash

# CrashLens Daily Cost Violation Alert Script
# This script runs daily to check for policy violations and send Slack alerts

# Configuration
PROJECT_DIR="/path/to/your/crashlens/project"
LOG_FILE="/var/log/crashlens-alerts.log"
POLICY_FILE="policy.yaml"
LOGS_DIR="logs"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-https://hooks.slack.com/services/YOUR/WEBHOOK/URL}"

# Daily log file (adjust path as needed)
DAILY_LOG="${LOGS_DIR}/$(date +%Y-%m-%d).jsonl"
FALLBACK_LOG="${LOGS_DIR}/latest.jsonl"

# Function to log with timestamp
log_with_timestamp() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

# Change to project directory
cd "$PROJECT_DIR" || {
    log_with_timestamp "ERROR: Failed to change to project directory: $PROJECT_DIR"
    exit 1
}

# Check if policy file exists
if [ ! -f "$POLICY_FILE" ]; then
    log_with_timestamp "ERROR: Policy file not found: $POLICY_FILE"
    exit 1
fi

# Determine which log file to use
if [ -f "$DAILY_LOG" ]; then
    LOG_TO_SCAN="$DAILY_LOG"
    log_with_timestamp "INFO: Using daily log file: $DAILY_LOG"
elif [ -f "$FALLBACK_LOG" ]; then
    LOG_TO_SCAN="$FALLBACK_LOG"
    log_with_timestamp "INFO: Daily log not found, using fallback: $FALLBACK_LOG"
else
    log_with_timestamp "ERROR: No log files found. Checked: $DAILY_LOG, $FALLBACK_LOG"
    exit 1
fi

# Check if log file has content
if [ ! -s "$LOG_TO_SCAN" ]; then
    log_with_timestamp "INFO: Log file is empty, skipping scan: $LOG_TO_SCAN"
    exit 0
fi

log_with_timestamp "INFO: Starting CrashLens scan with Slack webhook"

# Run CrashLens with Slack webhook
# Using summary mode for daily alerts (recommended)
if crashlens scan "$LOG_TO_SCAN" \
    --policy "$POLICY_FILE" \
    --summary \
    --slack-webhook "$SLACK_WEBHOOK_URL" >> "$LOG_FILE" 2>&1; then
    
    log_with_timestamp "INFO: CrashLens scan completed successfully"
else
    exit_code=$?
    log_with_timestamp "ERROR: CrashLens scan failed with exit code: $exit_code"
    
    # Optional: Send error notification to Slack
    if command -v curl >/dev/null 2>&1; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"❌ CrashLens daily scan failed with exit code $exit_code. Check logs for details.\"}" \
            "$SLACK_WEBHOOK_URL" >/dev/null 2>&1
    fi
    
    exit $exit_code
fi

log_with_timestamp "INFO: Daily alert script completed"
