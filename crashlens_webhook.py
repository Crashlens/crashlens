#!/usr/bin/env python3
"""
CrashLens with Webhook Integration
Run CrashLens and send results to Slack/Discord/Teams webhook
"""

import subprocess
import requests
import json
import sys
import os
from pathlib import Path
from datetime import datetime

def send_webhook_notification(webhook_url: str, report_content: str, status: str = "success"):
    """Send CrashLens results to webhook"""
    
    # Parse the report for key metrics
    lines = report_content.split('\n')
    total_cost = "Unknown"
    traces_analyzed = "Unknown"
    
    for line in lines:
        if "Cost:" in line and "$" in line:
            # Extract cost from line like "📊 CrashLens Summary – 2025-08-14 03:44:46 | Traces: 13 | Cost: $0.10"
            parts = line.split("Cost:")
            if len(parts) > 1:
                cost_part = parts[1].strip().split("|")[0].strip()
                total_cost = cost_part
        elif "Traces:" in line:
            # Extract trace count
            parts = line.split("Traces:")
            if len(parts) > 1:
                trace_part = parts[1].strip().split("|")[0].strip()
                traces_analyzed = trace_part
    
    # Determine emoji based on status
    status_emoji = {
        "success": "✅",
        "error": "❌", 
        "warning": "⚠️"
    }.get(status, "ℹ️")
    
    # Create Slack-compatible payload
    payload = {
        "text": f"{status_emoji} CrashLens Analysis Complete",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*CrashLens Token Waste Analysis*\n🔍 Status: {status.title()}\n📊 Traces Analyzed: {traces_analyzed}\n💰 Total Cost: {total_cost}\n⏰ Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{report_content[:800]}{'...' if len(report_content) > 800 else ''}```"
                }
            }
        ]
    }
    
    # Send to webhook
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        print(f"✅ Webhook notification sent successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to send webhook notification: {e}")
        return False

def main():
    """Main function to run CrashLens with webhook integration"""
    
    # Get webhook URL from environment variable
    webhook_url = os.getenv('CRASHLENS_WEBHOOK_URL')
    if not webhook_url:
        print("❌ CRASHLENS_WEBHOOK_URL environment variable not set")
        print("💡 Set it with: export CRASHLENS_WEBHOOK_URL='https://hooks.slack.com/services/...'")
        sys.exit(1)
    
    # Get command line arguments (pass through to crashlens)
    if len(sys.argv) < 2:
        print("Usage: python crashlens_webhook.py <crashlens-command> [args...]")
        print("Example: python crashlens_webhook.py scan test-logs.jsonl --summary")
        print("Example: python crashlens_webhook.py policy-check logs.jsonl --policy-template all")
        sys.exit(1)
    
    # Build crashlens command
    crashlens_args = ['python', '-m', 'crashlens'] + sys.argv[1:]
    
    print(f"🔍 Running: {' '.join(crashlens_args)}")
    
    try:
        # Run crashlens and capture output
        result = subprocess.run(
            crashlens_args,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            encoding='utf-8',
            errors='replace'  # Replace problematic characters
        )
        
        # Get the output
        output = result.stdout
        if result.stderr:
            output += f"\n\nErrors:\n{result.stderr}"
        
        # Clean output for display (remove problematic unicode)
        clean_output = output.encode('ascii', 'replace').decode('ascii')
        print(clean_output)  # Print to console as well
        
        # Determine status
        status = "success" if result.returncode == 0 else "error"
        
        # Send webhook notification
        send_webhook_notification(webhook_url, clean_output, status)
        
        # Exit with same code as crashlens
        sys.exit(result.returncode)
        
    except subprocess.TimeoutExpired:
        error_msg = "❌ CrashLens command timed out after 5 minutes"
        print(error_msg)
        send_webhook_notification(webhook_url, error_msg, "error")
        sys.exit(1)
    except Exception as e:
        error_msg = f"❌ Error running CrashLens: {e}"
        print(error_msg)
        send_webhook_notification(webhook_url, error_msg, "error")
        sys.exit(1)

if __name__ == "__main__":
    main()
