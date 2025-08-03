"""
Slack webhook utilities for CrashLens
Sends policy violation alerts to Slack channels
"""

import json
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

from .cost_estimator import format_cost


class SlackWebhookSender:
    """Handles sending Slack messages via webhooks"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send_policy_violations_alert(self, violations_by_rule: Dict[str, List[Dict]], total_cost: float) -> bool:
        """
        Send a formatted Slack alert for policy violations
        
        Args:
            violations_by_rule: Dict mapping rule_id to list of violations
            total_cost: Total estimated cost of violations
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            total_violations = sum(len(violations) for violations in violations_by_rule.values())
            
            if total_violations == 0:
                return True  # No violations, no need to send alert
            
            # Build Slack blocks
            blocks = self._build_violation_blocks(violations_by_rule, total_violations, total_cost)
            
            payload = {
                "blocks": blocks
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            response.raise_for_status()
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send Slack alert: {e}")
            return False
        except Exception as e:
            print(f"❌ Error preparing Slack message: {e}")
            return False
    
    def _build_violation_blocks(self, violations_by_rule: Dict[str, List[Dict]], total_violations: int, total_cost: float) -> List[Dict[str, Any]]:
        """Build Slack block kit formatted message"""
        blocks = []
        
        # Header block
        header_text = f"⚠️ {total_violations} cost policy violation{'s' if total_violations != 1 else ''} found"
        if total_cost > 0:
            header_text += f" • Estimated waste: {format_cost(total_cost)}"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{header_text}*"
            }
        })
        
        # Add divider
        blocks.append({"type": "divider"})
        
        # Violation details for each rule
        for rule_id, violations in violations_by_rule.items():
            rule_cost = sum(v.get('estimated_cost', 0) for v in violations)
            violation_count = len(violations)
            
            # Get suggestion from first violation
            suggestion = violations[0].get('suggestion', 'Review and optimize usage') if violations else ''
            
            rule_text = f"*{rule_id}* • {violation_count}x violations"
            if rule_cost > 0:
                rule_text += f" • {format_cost(rule_cost)}"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": rule_text
                }
            })
            
            if suggestion:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"💡 _{suggestion}_"
                        }
                    ]
                })
        
        # Footer
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Run `crashlens scan` to fix violations • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            ]
        })
        
        return blocks


def group_violations_by_rule(policy_violations) -> Dict[str, List[Dict]]:
    """
    Group policy violations by rule ID and calculate costs
    
    Args:
        policy_violations: List of PolicyViolation objects
        
    Returns:
        Dict mapping rule_id to list of violations with cost estimates
    """
    grouped = {}
    
    for violation in policy_violations:
        # Extract rule ID
        rule_id = violation.rule_id
        
        # Extract log entry for cost calculation
        log_entry = violation.log_entry if hasattr(violation, 'log_entry') else {}
        
        # Estimate cost from log entry
        estimated_cost = 0.0
        if log_entry:
            input_tokens = log_entry.get('usage', {}).get('prompt_tokens', 0) or 0
            output_tokens = log_entry.get('usage', {}).get('completion_tokens', 0) or 0
            model = log_entry.get('input', {}).get('model', 'gpt-3.5-turbo')
            
            if input_tokens or output_tokens:
                from .cost_estimator import estimate_cost
                estimated_cost = estimate_cost(input_tokens, output_tokens, model)
        
        # Create violation dict
        violation_dict = {
            'rule_id': rule_id,
            'reason': violation.reason,
            'suggestion': violation.suggestion,
            'severity': violation.severity.value if hasattr(violation.severity, 'value') else str(violation.severity),
            'action': violation.action.value if hasattr(violation.action, 'value') else str(violation.action),
            'estimated_cost': estimated_cost,
            'log_entry': log_entry
        }
        
        if rule_id not in grouped:
            grouped[rule_id] = []
        
        grouped[rule_id].append(violation_dict)
    
    return grouped
