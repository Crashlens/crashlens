#!/usr/bin/env python3
"""
CrashLens CLI - YAML Policy-Only Version
Scans Langfuse-style JSONL logs using YAML-driven policy rules only.

Version: 3.0.0 (Policy-Only)
"""

import click
import sys
import yaml
import tempfile
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any

# Version information
__version__ = "3.0.0"
__build_date__ = "2025-01-04"

from .parsers.langfuse import LangfuseParser
from .reporters.slack_formatter import SlackFormatter
from .reporters.markdown_formatter import MarkdownFormatter
from .reporters.summary_formatter import SummaryFormatter
from .policy.engine import PolicyEngine, PolicyAction
from .utils.slack_webhook import SlackWebhookSender, group_violations_by_rule
from .license_checker import get_license_checker, load_license_key
from .utils.roi_calculator import generate_roi_report


def load_policy_config(policy_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load YAML policy configuration"""
    if not policy_path:
        # Try default policy locations
        default_paths = [
            Path.cwd() / "modern-policy.yaml",
            Path.cwd() / "policy.yaml", 
            Path(__file__).parent / "config" / "modern-policy.yaml"
        ]
        
        for path in default_paths:
            if path.exists():
                policy_path = path
                break
        else:
            raise FileNotFoundError("No policy configuration found. Create a modern-policy.yaml file.")
    
    with open(policy_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_pricing_config(pricing_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load pricing configuration"""
    if not pricing_path:
        pricing_path = Path(__file__).parent / "config" / "pricing.yaml"
    
    if pricing_path.exists():
        with open(pricing_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    # Default pricing fallback
    return {
        "models": {
            "gpt-4": {"input_cost_per_token": 0.00003, "output_cost_per_token": 0.00006},
            "gpt-3.5-turbo": {"input_cost_per_token": 0.0000015, "output_cost_per_token": 0.000002},
            "claude-3-opus": {"input_cost_per_token": 0.000015, "output_cost_per_token": 0.000075},
            "claude-3-haiku": {"input_cost_per_token": 0.00000025, "output_cost_per_token": 0.00000125}
        }
    }


@click.group()
@click.version_option(__version__, message="CrashLens CLI v%(version)s (Policy-Only)")
def cli():
    """🔍 CrashLens - YAML Policy-Driven Token Waste Detection"""
    pass


@cli.command()
@click.argument('log_file', type=click.Path(exists=True, path_type=Path))
@click.option('--policy', '-p', type=click.Path(exists=True, path_type=Path), 
              help='Path to YAML policy configuration file')
@click.option('--license-key', type=str, help='License key for premium features')
@click.option('--format', 'output_format', type=click.Choice(['markdown', 'slack', 'summary', 'json']), 
              default='markdown', help='Output format')
@click.option('--summary-only', is_flag=True, 
              help='Generate summary-only report without individual violation details')
@click.option('--output', '-o', type=click.Path(path_type=Path), 
              help='Output file path (default: report.md)')
@click.option('--slack-webhook', type=str, help='Slack webhook URL for notifications')
@click.option('--slack-channel', default='#ai-cost-monitoring', 
              help='Slack channel for notifications')
@click.option('--dry-run', is_flag=True, help='Show what would be detected without creating reports')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
def scan(log_file: Path, policy: Optional[Path], license_key: Optional[str], 
         output_format: str, summary_only: bool, output: Optional[Path], 
         slack_webhook: Optional[str], slack_channel: str, dry_run: bool, verbose: bool):
    """
    🚀 Scan log file for policy violations using YAML rules
    
    Analyzes Langfuse-format JSONL logs and detects issues based on YAML policy rules.
    All detection logic is policy-driven - no hardcoded detectors.
    """
    
    try:
        # Load configurations
        policy_config = load_policy_config(policy)
        pricing_config = load_pricing_config()
        
        if verbose:
            click.echo(f"📋 Loaded policy with {len(policy_config.get('rules', []))} rules")
            click.echo(f"💰 Loaded pricing for {len(pricing_config.get('models', {}))} models")
        
        # Initialize license checker
        if license_key:
            license_checker = get_license_checker()
            # Apply the license key if provided
            license_checker.license_key = license_key
        else:
            # Try to load from default locations
            license_checker = load_license_key()
        
        # Parse log file
        parser = LangfuseParser()
        traces_dict = parser.parse_file(log_file)
        
        if not traces_dict:
            click.echo("⚠️  No traces found in log file", err=True)
            return
        
        # Flatten traces into log entries for policy engine
        log_entries = []
        for trace_id, trace_logs in traces_dict.items():
            for log_entry in trace_logs:
                # Ensure trace_id is included in the log entry
                if 'trace_id' not in log_entry:
                    log_entry['trace_id'] = trace_id
                log_entries.append(log_entry)
        
        if verbose:
            click.echo(f"📊 Parsed {len(traces_dict)} traces with {len(log_entries)} log entries from {log_file}")
        
        # Initialize policy engine
        # Create a temporary policy file if needed
        if policy:
            policy_engine = PolicyEngine(policy)
        else:
            # Create temporary policy file from loaded config
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as tmp_file:
                yaml.dump(policy_config, tmp_file, default_flow_style=False)
                tmp_policy_path = Path(tmp_file.name)
            
            try:
                policy_engine = PolicyEngine(tmp_policy_path)
            finally:
                # Clean up temporary file
                os.unlink(tmp_policy_path)        # Run policy evaluation
        all_violations, skipped_rules = policy_engine.evaluate_logs(log_entries)
        
        if verbose:
            click.echo(f"🔍 Found {len(all_violations)} total violations")
            if skipped_rules:
                click.echo(f"⏭️  Skipped {len(skipped_rules)} license-gated rules")
        
        # Handle dry run
        if dry_run:
            click.echo("🔍 DRY RUN - Violations that would be reported:")
            for violation in all_violations:
                severity_emoji = {
                    'critical': '🚨',
                    'high': '⚠️',
                    'medium': '⚡',
                    'low': 'ℹ️'
                }.get(violation.severity.value.lower(), '•')
                
                click.echo(f"{severity_emoji} {violation.rule_id}: {violation.reason}")
            
            click.echo(f"\n📊 Total: {len(all_violations)} violations")
            return
        
        # Convert violations to legacy format for formatters
        detections_for_formatters = []
        for violation in all_violations:
            detection = {
                "rule_id": violation.rule_id,
                "reason": violation.reason,
                "suggestion": violation.suggestion,
                "severity": violation.severity.value,
                "action": violation.action.value,
                "trace_id": violation.log_entry.get('trace_id'),
                "line_number": violation.line_number,
                **violation.log_entry  # Include all log entry data
            }
            detections_for_formatters.append(detection)
        
        # Generate output
        if output_format == 'markdown':
            formatter = MarkdownFormatter()
            content = formatter.format(detections_for_formatters, traces_dict, 
                                     pricing_config.get('models', {}), summary_only)
            
            output_path = output or Path.cwd() / "report.md"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            click.echo(f"📝 Markdown report written to {output_path}")
        
        elif output_format == 'slack':
            formatter = SlackFormatter()
            content = formatter.format(detections_for_formatters, traces_dict, 
                                     pricing_config.get('models', {}), summary_only)
            
            if slack_webhook:
                # Note: SlackWebhookSender might need to be updated for policy violations
                click.echo(f"📢 Slack integration needs to be updated for policy violations")
            else:
                output_path = output or Path.cwd() / "slack_report.json"
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                click.echo(f"📱 Slack format report written to {output_path}")
        
        elif output_format == 'summary':
            formatter = SummaryFormatter()
            content = formatter.format(traces_dict, pricing_config.get('models', {}), 
                                     True, detections_for_formatters)  # summary_only=True, detections=violations
            
            output_path = output or Path.cwd() / "summary.md"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            click.echo(f"📊 Summary report written to {output_path}")
        
        elif output_format == 'json':
            import json
            
            # Convert violations to JSON-serializable format
            violations_data = []
            for v in all_violations:
                violations_data.append({
                    "rule_id": v.rule_id,
                    "line_number": v.line_number,
                    "reason": v.reason,
                    "severity": v.severity.value,
                    "action": v.action.value,
                    "suggestion": v.suggestion,
                    "log_entry": v.log_entry
                })
            
            json_data = {
                "scan_timestamp": datetime.now().isoformat(),
                "log_file": str(log_file),
                "total_traces": len(traces_dict),
                "total_log_entries": len(log_entries),
                "total_violations": len(all_violations),
                "violations": violations_data
            }
            
            output_path = output or Path.cwd() / "violations.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2)
            
            click.echo(f"📄 JSON report written to {output_path}")
        
        # Print summary
        if all_violations:
            click.echo(f"\n🔍 Scan complete: {len(all_violations)} violations found")
            
            # Count by severity
            severity_counts = {}
            for violation in all_violations:
                severity = violation.severity.value
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            for severity, count in severity_counts.items():
                emoji = {
                    'critical': '🚨',
                    'high': '⚠️', 
                    'medium': '⚡',
                    'low': 'ℹ️'
                }.get(severity.lower(), '•')
                click.echo(f"  {emoji} {severity}: {count}")
        else:
            click.echo("✅ No policy violations found")
    
    except Exception as e:
        click.echo(f"❌ Error during scan: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('--policy', '-p', type=click.Path(exists=True, path_type=Path), 
              help='Path to YAML policy configuration file')
def validate_policy(policy: Optional[Path]):
    """
    ✅ Validate YAML policy configuration
    
    Checks policy syntax, rule definitions, and configuration validity.
    """
    
    try:
        policy_config = load_policy_config(policy)
        
        # Basic validation
        if 'rules' not in policy_config:
            click.echo("❌ Policy must contain 'rules' section", err=True)
            sys.exit(1)
        
        rules = policy_config['rules']
        if not isinstance(rules, list) or len(rules) == 0:
            click.echo("❌ Policy 'rules' must be a non-empty list", err=True)
            sys.exit(1)
        
        # Validate each rule
        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                click.echo(f"❌ Rule {i+1} must be a dictionary", err=True)
                sys.exit(1)
            
            required_fields = ['id', 'description', 'match', 'action', 'severity']
            for field in required_fields:
                if field not in rule:
                    click.echo(f"❌ Rule {i+1} missing required field: {field}", err=True)
                    sys.exit(1)
        
        click.echo(f"✅ Policy validation passed")
        click.echo(f"📋 Found {len(rules)} valid rules")
        
        # Show rule summary
        for rule in rules:
            requires_license = rule.get('requires_license', False)
            license_indicator = "🔐" if requires_license else "🆓"
            click.echo(f"  {license_indicator} {rule['id']}: {rule['description']}")
    
    except Exception as e:
        click.echo(f"❌ Policy validation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('log_file', type=click.Path(exists=True, path_type=Path))
def info(log_file: Path):
    """
    ℹ️  Show information about a log file
    
    Displays basic statistics about traces, models, and costs without running detection.
    """
    
    try:
        # Parse log file
        parser = LangfuseParser()
        traces_dict = parser.parse_file(log_file)
        
        if not traces_dict:
            click.echo("⚠️  No traces found in log file", err=True)
            return
        
        # Calculate statistics
        total_traces = len(traces_dict)
        models_used = set()
        total_cost = 0.0
        total_tokens = 0
        total_log_entries = 0
        
        for trace_id, trace_logs in traces_dict.items():
            total_log_entries += len(trace_logs)
            for log_entry in trace_logs:
                # Check for model in different locations
                model = None
                if 'model' in log_entry and log_entry['model']:
                    model = log_entry['model']
                elif 'input' in log_entry and isinstance(log_entry['input'], dict) and 'model' in log_entry['input']:
                    model = log_entry['input']['model']
                
                if model:
                    models_used.add(model)
                    
                if 'cost' in log_entry and log_entry['cost']:
                    total_cost += log_entry['cost']
                if 'usage' in log_entry and log_entry['usage']:
                    usage = log_entry['usage']
                    if isinstance(usage, dict) and 'total_tokens' in usage:
                        total_tokens += usage['total_tokens']
        
        # Display info
        click.echo(f"📊 Log File Information: {log_file}")
        click.echo(f"📈 Total Traces: {total_traces}")
        click.echo(f"📄 Total Log Entries: {total_log_entries}")
        click.echo(f"🤖 Models Used: {', '.join(sorted(models_used)) if models_used else 'Unknown'}")
        click.echo(f"💰 Total Cost: ${total_cost:.4f}")
        click.echo(f"🔤 Total Tokens: {total_tokens:,}")
        
        if total_traces > 0:
            click.echo(f"📊 Average Cost per Trace: ${total_cost/total_traces:.4f}")
            click.echo(f"📊 Average Tokens per Trace: {total_tokens//total_traces:,}")
    
    except Exception as e:
        click.echo(f"❌ Error reading log file: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
