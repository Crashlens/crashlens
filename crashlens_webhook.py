#!/usr/bin/env python3
"""
CrashLens with Webhook Integration
Run CrashLens and send results to Slack/Discord/Teams webhook

This script automatically enforces Slack format output for webhook compatibility.
All reports sent to webhook will be in Slack-formatted style, not Markdown.
"""

import subprocess
import requests
import json
import sys
import os
from pathlib import Path
from datetime import datetime

def send_webhook_notification(webhook_url: str, report_content: str, status: str = "success"):
    """Send CrashLens results to webhook - expects Slack-formatted content"""
    
    # Parse the report for key metrics from Slack-formatted output
    lines = report_content.split('\n')
    total_cost = "Unknown"
    traces_analyzed = "Unknown"
    potential_savings = "Unknown"
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # Look for Slack-formatted cost indicators
        if ("cost:" in line_lower or "total" in line_lower) and ("$" in line or "₹" in line):
            # Extract cost from various formats
            import re
            cost_match = re.search(r'[\$₹€£¥]?[\d,]+\.?\d*', line)
            if cost_match:
                total_cost = cost_match.group()
                
        elif "traces" in line_lower and ("analyzed" in line_lower or ":" in line):
            # Extract trace count
            import re
            trace_match = re.search(r'\d+', line)
            if trace_match:
                traces_analyzed = trace_match.group()
                
        elif "savings" in line_lower or "waste" in line_lower:
            # Extract potential savings
            import re
            savings_match = re.search(r'[\$₹€£¥]?[\d,]+\.?\d*', line)
            if savings_match:
                potential_savings = savings_match.group()
    
    # Determine emoji based on status
    status_emoji = {
        "success": "✅",
        "error": "❌", 
        "warning": "⚠️"
    }.get(status, "ℹ️")
    
    # Create enhanced Slack payload with better structure
    payload = {
        "text": f"{status_emoji} CrashLens Analysis Complete",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🔍 CrashLens Token Waste Analysis*\n📊 *Traces Analyzed:* {traces_analyzed}\n💰 *Total Cost:* {total_cost}\n🎯 *Potential Savings:* {potential_savings}\n⏰ *Analysis Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📋 Full Report (Slack Format):*\n```{report_content[:1500]}{'...' if len(report_content) > 1500 else ''}```"
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
    
    # Build crashlens command - force Slack format for webhook integration
    crashlens_args = ['python', '-m', 'crashlens'] + sys.argv[1:]
    
    # Force Slack format by modifying the arguments
    if '--format' not in ' '.join(sys.argv[1:]) and '-f' not in ' '.join(sys.argv[1:]):
        # Insert --format slack after the command but before other options
        if len(sys.argv) > 2:  # Has command + arguments
            crashlens_args = ['python', '-m', 'crashlens', sys.argv[1], '--format', 'slack'] + sys.argv[2:]
        else:  # Just has command
            crashlens_args = ['python', '-m', 'crashlens'] + sys.argv[1:] + ['--format', 'slack']
    
    print(f"🔍 Running: {' '.join(crashlens_args)}")
    print("📡 Webhook mode: Enforcing Slack format output")
    
    try:
        # Set environment variables to handle Unicode properly
        env = os.environ.copy()
        env['PYTHONUTF8'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        
        # Run crashlens and capture output
        result = subprocess.run(
            crashlens_args,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            encoding='utf-8',
            errors='replace',  # Replace problematic characters
            env=env
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
