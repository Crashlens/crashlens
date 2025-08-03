#!/bin/bash
# CrashLens Scheduled Policy Scan
# Cronjob-compatible script for automated policy enforcement

set -euo pipefail

# Configuration (customize these variables)
LOG_DIR="${LOG_DIR:-/app/logs}"
POLICY_FILE="${POLICY_FILE:-/app/config/policy.yaml}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/crashlens-reports}"
DAYS_TO_SCAN="${DAYS_TO_SCAN:-1}"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Generate timestamp for reports
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="$OUTPUT_DIR/crashlens_scan_$TIMESTAMP.md"

echo "🔍 Starting CrashLens scheduled scan..."
echo "📁 Log directory: $LOG_DIR"
echo "📋 Policy file: $POLICY_FILE"
echo "📊 Report file: $REPORT_FILE"

# Find log files modified in the last N days
LOG_FILES=$(find "$LOG_DIR" -name "*.jsonl" -type f -mtime -"$DAYS_TO_SCAN" | head -10)

if [ -z "$LOG_FILES" ]; then
    echo "⚠️  No recent log files found in $LOG_DIR"
    exit 0
fi

echo "📄 Found $(echo "$LOG_FILES" | wc -l) log files to scan"

# Run CrashLens scan
SCAN_COMMAND="crashlens scan"

# Add policy file if exists
if [ -f "$POLICY_FILE" ]; then
    SCAN_COMMAND="$SCAN_COMMAND --policy $POLICY_FILE"
fi

# Add Slack webhook if configured
if [ -n "$SLACK_WEBHOOK" ]; then
    SCAN_COMMAND="$SCAN_COMMAND --slack-webhook $SLACK_WEBHOOK"
fi

# Add output format
SCAN_COMMAND="$SCAN_COMMAND --format markdown --fail-on-policy"

# Process each log file
EXIT_CODE=0
TOTAL_VIOLATIONS=0

for LOG_FILE in $LOG_FILES; do
    echo "🔄 Scanning: $LOG_FILE"
    
    if $SCAN_COMMAND "$LOG_FILE" > "$REPORT_FILE.tmp" 2>&1; then
        echo "✅ $LOG_FILE: PASSED"
    else
        echo "❌ $LOG_FILE: VIOLATIONS FOUND"
        EXIT_CODE=1
        # Count violations (rough estimate)
        VIOLATIONS=$(grep -c "FAIL\|WARN" "$REPORT_FILE.tmp" || echo "0")
        TOTAL_VIOLATIONS=$((TOTAL_VIOLATIONS + VIOLATIONS))
    fi
    
    # Append to main report
    echo "## Scan Results for $LOG_FILE" >> "$REPORT_FILE"
    echo "**Scan Time:** $(date)" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    cat "$REPORT_FILE.tmp" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "---" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    
    rm -f "$REPORT_FILE.tmp"
done

# Generate summary
echo "## 📊 Scan Summary" >> "$REPORT_FILE"
echo "- **Files Scanned:** $(echo "$LOG_FILES" | wc -l)" >> "$REPORT_FILE"
echo "- **Total Violations:** $TOTAL_VIOLATIONS" >> "$REPORT_FILE"
echo "- **Scan Date:** $(date)" >> "$REPORT_FILE"
echo "- **Exit Code:** $EXIT_CODE" >> "$REPORT_FILE"

echo "📊 Scan complete!"
echo "📄 Report saved to: $REPORT_FILE"
echo "🔢 Total violations: $TOTAL_VIOLATIONS"
echo "🚪 Exit code: $EXIT_CODE"

# Cleanup old reports (keep last 30 days)
find "$OUTPUT_DIR" -name "crashlens_scan_*.md" -type f -mtime +30 -delete 2>/dev/null || true

exit $EXIT_CODE
