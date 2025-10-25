#!/usr/bin/env python3
"""
CrashLens Guard - CI-Friendly Policy Enforcement
Parses rules.yaml, evaluates JSONL logs, respects suppressions/severity threshold/privacy flags.
Emits json/markdown/text reports and exits nonzero on violations for CI integration.
"""

import html
import json
import os
import re
import sys
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import click
import yaml
from jsonschema import ValidationError, validate

# PII detection patterns
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"\+?\d[\d\-\s]{7,}\d")

# Severity ranking for threshold comparison
SEVERITY_RANK = {"warn": 1, "error": 2, "fatal": 3}


def generate_run_id() -> str:
    """Generate unique run ID for artifact tracking (timestamp + git hash)"""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback if git is unavailable or not a git repo
        git_hash = "nogit"
    return f"{timestamp}-{git_hash}"


def get_max_examples() -> int:
    """Get max examples limit from environment (allows runtime configuration)"""
    return int(os.getenv("CRASHLENS_MAX_EXAMPLES", "5"))


# JSON Schema for rules.yaml validation (fail-fast on malformed config)
RULES_SCHEMA = {
    "type": "object",
    "properties": {
        "rules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "description": {"type": "string"},
                    "if": {"type": "object"},
                    "action": {"type": "string", "enum": ["fail_ci", "error", "warn"]},
                    "severity": {"type": "string", "enum": ["warn", "error", "fatal"]},
                },
                "required": ["id", "if", "action"],
            },
        }
    },
    "required": ["rules"],
}


@dataclass
class Rule:
    """Represents a single guard rule with conditions and actions"""
    id: str
    description: str
    cond: Dict[str, Any]
    action: str
    severity: str


def load_rules(path: str) -> List[Rule]:
    """Load and validate rules from YAML file
    
    Args:
        path: Path to rules.yaml file
        
    Returns:
        List of validated Rule objects
        
    Raises:
        click.ClickException: If rules file is invalid
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError:
        raise click.ClickException(f"Rules file not found: {path}")
    except yaml.YAMLError as e:
        raise click.ClickException(f"Invalid YAML in rules file: {e}")
    
    # Strict schema validation (fail-fast on malformed rules)
    try:
        validate(instance=raw, schema=RULES_SCHEMA)
    except ValidationError as e:
        raise click.ClickException(f"Invalid rules.yaml schema: {e.message}")
    
    if not raw or "rules" not in raw:
        raise click.ClickException("rules.yaml missing 'rules' key")
    
    # Check for duplicate rule IDs
    rule_ids = [r.get("id") for r in raw["rules"]]
    duplicates = [rid for rid in rule_ids if rule_ids.count(rid) > 1]
    if duplicates:
        raise click.ClickException(
            f"Duplicate rule IDs found: {', '.join(set(duplicates))}"
        )
    
    rules = []
    for r in raw["rules"]:
        # Validate required fields (schema already validates, but keep for clarity)
        if "id" not in r:
            raise click.ClickException(f"Rule missing required field 'id': {r}")
        if "if" not in r:
            raise click.ClickException(f"Rule {r.get('id')} missing required field 'if'")
        if "action" not in r:
            raise click.ClickException(f"Rule {r.get('id')} missing required field 'action'")
        
        # Validate action
        if r["action"] not in ["fail_ci", "error", "warn"]:
            raise click.ClickException(
                f"Rule {r['id']} has invalid action '{r['action']}'. "
                f"Must be one of: fail_ci, error, warn"
            )
        
        # Default severity to 'warn' for safety (teams can promote later)
        severity = r.get("severity", "warn")
        if severity not in SEVERITY_RANK:
            raise click.ClickException(
                f"Rule {r['id']} has invalid severity '{severity}'. "
                f"Must be one of: warn, error, fatal"
            )
        
        rules.append(Rule(
            id=r["id"],
            description=r.get("description", ""),
            cond=r["if"],
            action=r["action"],
            severity=severity
        ))
    
    return rules


def load_jsonl(path: str):
    """Generator that yields parsed JSON objects from JSONL file (fail-safe)
    
    Skips malformed lines and logs warnings to stderr. Tracks skipped line count
    as a global variable that can be accessed after iteration.
    
    Args:
        path: Path to JSONL log file
        
    Yields:
        Dict containing log entry data
        
    Raises:
        click.ClickException: If file cannot be read
    """
    global _jsonl_skipped_lines
    _jsonl_skipped_lines = 0
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as e:
                    # Fail-safe: skip malformed line and warn
                    _jsonl_skipped_lines += 1
                    content_snippet = line[:80] + "..." if len(line) > 80 else line
                    click.echo(
                        f"⚠️  Warning: Skipping malformed JSON at line {line_num}: {e}",
                        err=True
                    )
                    click.echo(f"   Content: {content_snippet}", err=True)
    except FileNotFoundError:
        raise click.ClickException(f"Log file not found: {path}")


# Global variable to track skipped lines (set by load_jsonl)
_jsonl_skipped_lines = 0


class PIIDetector:
    """Pluggable PII detection and redaction interface
    
    This class provides an extensible interface for PII detection.
    Override detect() and redact() methods to customize behavior.
    """
    
    def __init__(self):
        """Initialize detector with default regex patterns"""
        self.email_pattern = EMAIL_RE
        self.phone_pattern = PHONE_RE
    
    def detect(self, text: str) -> bool:
        """Check if text contains PII
        
        Args:
            text: Input text to check
            
        Returns:
            True if PII detected, False otherwise
        """
        if not text:
            return False
        return bool(self.email_pattern.search(text) or self.phone_pattern.search(text))
    
    def redact(self, text: str) -> str:
        """Redact PII from text
        
        Args:
            text: Input text to redact
            
        Returns:
            Text with PII replaced by [REDACTED_*] placeholders
        """
        if not text:
            return ""
        output = self.email_pattern.sub("[REDACTED_EMAIL]", text)
        output = self.phone_pattern.sub("[REDACTED_PHONE]", output)
        return output


# Global PII detector instance (can be replaced with custom implementation)
_pii_detector = PIIDetector()


def redact_text(s: str, strip_pii: bool) -> str:
    """Redact PII from text if strip_pii is enabled
    
    Args:
        s: Input text
        strip_pii: Whether to strip PII (emails, phones)
        
    Returns:
        Redacted text
    """
    if s is None:
        return ""
    if strip_pii:
        return _pii_detector.redact(s)
    return s


def evaluate_condition(cond: Dict[str, Any], entry: Dict[str, Any]) -> bool:
    """Evaluate a single condition (atomic or composite) against a log entry
    
    Supports boolean composition:
    - "and": List of conditions (all must be true)
    - "or": List of conditions (at least one must be true)
    - "not": Single condition (negates result)
    
    Atomic conditions:
    - if_model: exact string match on model field
    - if_tokens_gt: token count greater than threshold
    - if_retry_count_gt: retry count greater than threshold
    - if_fallback_triggered: boolean match on fallback_triggered
    - if_prompt_contains_pii: detects emails/phones in prompt
    - if_cost_usd_gt: cost greater than threshold
    - if_response_time_gt: response time (ms) greater than threshold
    - if_error_rate_gt: error rate (%) greater than threshold
    
    Args:
        cond: Condition dictionary (atomic or composite)
        entry: Log entry to evaluate
        
    Returns:
        True if condition matches, False otherwise
        
    Examples:
        # Simple atomic condition
        {"if_model": "gpt-4o"}
        
        # OR composition
        {"or": [{"if_model": "gpt-4o"}, {"if_model": "claude-3"}]}
        
        # NOT composition
        {"not": {"if_model": "gpt-3.5-turbo"}}
        
        # Nested composition
        {"and": [
            {"if_cost_usd_gt": 0.10},
            {"or": [{"if_model": "gpt-4o"}, {"if_retry_count_gt": 2}]}
        ]}
    """
    # Handle boolean composition
    if "and" in cond:
        conditions = cond["and"]
        if not isinstance(conditions, list):
            return False
        return all(evaluate_condition(sub_cond, entry) for sub_cond in conditions)
    
    if "or" in cond:
        conditions = cond["or"]
        if not isinstance(conditions, list):
            return False
        return any(evaluate_condition(sub_cond, entry) for sub_cond in conditions)
    
    if "not" in cond:
        sub_cond = cond["not"]
        if not isinstance(sub_cond, dict):
            return False
        return not evaluate_condition(sub_cond, entry)
    
    # Handle atomic conditions (backward compatibility)
    if "if_model" in cond:
        if entry.get("model") != cond["if_model"]:
            return False
    
    if "if_tokens_gt" in cond:
        if int(entry.get("tokens", 0)) <= int(cond["if_tokens_gt"]):
            return False
    
    if "if_retry_count_gt" in cond:
        if int(entry.get("retry_count", 0)) <= int(cond["if_retry_count_gt"]):
            return False
    
    if "if_fallback_triggered" in cond:
        val = bool(entry.get("fallback_triggered", False))
        if val != bool(cond["if_fallback_triggered"]):
            return False
    
    if "if_prompt_contains_pii" in cond:
        prompt = entry.get("prompt", "")
        has_pii = _pii_detector.detect(prompt)
        if has_pii != bool(cond["if_prompt_contains_pii"]):
            return False
    
    if "if_cost_usd_gt" in cond:
        if float(entry.get("cost_usd", 0.0)) <= float(cond["if_cost_usd_gt"]):
            return False
    
    if "if_response_time_gt" in cond:
        # Response time in milliseconds
        response_time_ms = float(entry.get("response_time_ms", 0.0))
        if response_time_ms <= float(cond["if_response_time_gt"]):
            return False
    
    if "if_error_rate_gt" in cond:
        # Error rate as percentage (0-100)
        error_rate = float(entry.get("error_rate", 0.0))
        if error_rate <= float(cond["if_error_rate_gt"]):
            return False
    
    return True


def eval_condition(cond: Dict[str, Any], entry: Dict[str, Any]) -> bool:
    """Evaluate rule conditions against a log entry (backward compatibility wrapper)
    
    This function maintains backward compatibility with existing code.
    All conditions within a rule are implicitly AND-ed together when using
    the flat dictionary format.
    
    For boolean composition (and/or/not), use evaluate_condition() directly
    or nest conditions under "and", "or", "not" keys.
    
    Args:
        cond: Dictionary of condition key-value pairs
        entry: Log entry to evaluate
        
    Returns:
        True if all conditions match, False otherwise
    """
    return evaluate_condition(cond, entry)


def format_json_report(report: Dict[str, Any]) -> str:
    """Format report as JSON
    
    Args:
        report: Report data structure
        
    Returns:
        Pretty-printed JSON string
    """
    return json.dumps(report, indent=2)


def format_markdown_report(report: Dict[str, Any], logfile: str) -> str:
    """Format report as Markdown
    
    Args:
        report: Report data structure
        logfile: Path to log file that was scanned
        
    Returns:
        Markdown-formatted report string
    """
    lines = ["# CrashLens Guard Report", ""]
    lines.append(f"- **Scanned**: `{logfile}`")
    lines.append(f"- **Rules Checked**: {len(report['rules'])}")
    lines.append(f"- **Violations Found**: {report['summary']['violations']}")
    lines.append("")
    
    if report['summary']['violations'] == 0:
        lines.append("✅ **No violations detected**")
        lines.append("")
        return "\n".join(lines)
    
    lines.append("## Violations by Rule")
    lines.append("")
    
    for rid, meta in report["rules"].items():
        if meta["count"] == 0:
            continue
            
        lines.append(f"### {rid} — `{meta['severity']}` severity")
        lines.append("")
        lines.append(f"**Description**: {meta['description']}")
        lines.append("")
        lines.append(f"**Violation Count**: {meta['count']}")
        lines.append("")
        
        if meta['examples']:
            lines.append("**Example Violations**:")
            lines.append("")
            for i, ex in enumerate(meta['examples'][:3], 1):
                lines.append(f"{i}. **Timestamp**: {ex.get('timestamp', 'N/A')}")
                lines.append(f"   - **Model**: `{ex.get('model', 'N/A')}`")
                lines.append(f"   - **Tokens**: {ex.get('tokens', 'N/A')}")
                lines.append(f"   - **Retry Count**: {ex.get('retry_count', 'N/A')}")
                lines.append(f"   - **Fallback**: {ex.get('fallback_triggered', 'N/A')}")
                lines.append(f"   - **Endpoint**: `{ex.get('endpoint', 'N/A')}`")
                if ex.get('prompt'):
                    prompt_preview = ex['prompt'][:80]
                    if len(ex['prompt']) > 80:
                        prompt_preview += "..."
                    lines.append(f"   - **Prompt**: {prompt_preview}")
                lines.append("")
        
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


def format_html_report(report: Dict[str, Any], logfile: str) -> str:
    """Format report as HTML with Bootstrap styling
    
    Args:
        report: Report data structure
        logfile: Path to log file that was scanned
        
    Returns:
        HTML report string with inline styles for email compatibility
    """
    # Color mapping for severity levels
    severity_colors = {
        'critical': '#dc3545',  # Red
        'high': '#fd7e14',      # Orange
        'medium': '#ffc107',    # Yellow
        'low': '#6c757d'        # Gray
    }
    
    # Start HTML with inline styles
    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '    <title>CrashLens Guard Report</title>',
        '    <style>',
        '        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 20px; background-color: #f8f9fa; }',
        '        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }',
        '        h1 { color: #212529; border-bottom: 3px solid #0d6efd; padding-bottom: 10px; }',
        '        .summary { background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }',
        '        .summary-item { display: inline-block; margin-right: 30px; }',
        '        .summary-label { font-weight: 600; color: #495057; }',
        '        .violation-card { border-left: 4px solid #dee2e6; padding: 15px; margin: 15px 0; background: #f8f9fa; border-radius: 4px; }',
        '        .violation-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }',
        '        .rule-id { font-weight: 700; font-size: 1.1em; color: #212529; }',
        '        .severity-badge { padding: 5px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 600; color: white; }',
        '        .description { color: #6c757d; margin: 10px 0; }',
        '        .count { font-size: 1.2em; font-weight: 600; color: #dc3545; }',
        '        .examples { margin-top: 15px; }',
        '        .example-item { background: white; padding: 12px; margin: 8px 0; border-radius: 4px; border: 1px solid #dee2e6; }',
        '        .example-row { margin: 5px 0; }',
        '        .example-label { font-weight: 600; color: #495057; min-width: 120px; display: inline-block; }',
        '        .example-value { color: #212529; }',
        '        code { background: #f1f3f5; padding: 2px 6px; border-radius: 3px; font-family: "Courier New", monospace; }',
        '        .no-violations { text-align: center; padding: 40px; color: #28a745; font-size: 1.3em; }',
        '        .success-icon { font-size: 3em; }',
        '    </style>',
        '</head>',
        '<body>',
        '    <div class="container">',
        '        <h1>🛡️ CrashLens Guard Report</h1>',
        '        <div class="summary">',
        f'            <div class="summary-item"><span class="summary-label">Scanned:</span> <code>{logfile}</code></div>',
        f'            <div class="summary-item"><span class="summary-label">Rules Checked:</span> {len(report["rules"])}</div>',
        f'            <div class="summary-item"><span class="summary-label">Violations Found:</span> <span class="count">{report["summary"]["violations"]}</span></div>',
        '        </div>',
    ]
    
    # No violations case
    if report['summary']['violations'] == 0:
        html_parts.extend([
            '        <div class="no-violations">',
            '            <div class="success-icon">✅</div>',
            '            <div>No violations detected - All policies passed!</div>',
            '        </div>',
        ])
    else:
        # Add violation cards
        for rid, meta in report["rules"].items():
            if meta["count"] == 0:
                continue
            
            severity = meta['severity'].lower()
            color = severity_colors.get(severity, '#6c757d')
            
            html_parts.extend([
                f'        <div class="violation-card" style="border-left-color: {color};">',
                '            <div class="violation-header">',
                f'                <span class="rule-id">{html.escape(rid)}</span>',
                f'                <span class="severity-badge" style="background-color: {color};">{html.escape(severity.upper())}</span>',
                '            </div>',
                f'            <div class="description">{html.escape(meta["description"])}</div>',
                f'            <div><span class="summary-label">Violation Count:</span> <span class="count">{meta["count"]}</span></div>',
            ])
            
            # Add examples if available
            if meta['examples']:
                html_parts.append('            <div class="examples">')
                html_parts.append('                <div class="summary-label">Example Violations:</div>')
                
                for i, ex in enumerate(meta['examples'][:3], 1):
                    html_parts.append('                <div class="example-item">')
                    html_parts.append(f'                    <div class="example-row"><span class="example-label">Example #{i}</span></div>')
                    html_parts.append(f'                    <div class="example-row"><span class="example-label">Timestamp:</span> <span class="example-value">{html.escape(str(ex.get("timestamp", "N/A")))}</span></div>')
                    html_parts.append(f'                    <div class="example-row"><span class="example-label">Model:</span> <code>{html.escape(str(ex.get("model", "N/A")))}</code></div>')
                    html_parts.append(f'                    <div class="example-row"><span class="example-label">Tokens:</span> <span class="example-value">{html.escape(str(ex.get("tokens", "N/A")))}</span></div>')
                    html_parts.append(f'                    <div class="example-row"><span class="example-label">Retry Count:</span> <span class="example-value">{html.escape(str(ex.get("retry_count", "N/A")))}</span></div>')
                    html_parts.append(f'                    <div class="example-row"><span class="example-label">Fallback:</span> <span class="example-value">{html.escape(str(ex.get("fallback_triggered", "N/A")))}</span></div>')
                    html_parts.append(f'                    <div class="example-row"><span class="example-label">Endpoint:</span> <code>{html.escape(str(ex.get("endpoint", "N/A")))}</code></div>')
                    
                    if ex.get('prompt'):
                        prompt_preview = ex['prompt'][:80]
                        if len(ex['prompt']) > 80:
                            prompt_preview += "..."
                        html_parts.append(f'                    <div class="example-row"><span class="example-label">Prompt:</span> <span class="example-value">{html.escape(prompt_preview)}</span></div>')
                    
                    html_parts.append('                </div>')
                
                html_parts.append('            </div>')
            
            html_parts.append('        </div>')
    
    # Close HTML
    html_parts.extend([
        '    </div>',
        '</body>',
        '</html>'
    ])
    
    return "\n".join(html_parts)


def format_text_report(report: Dict[str, Any], logfile: str) -> str:
    """Format report as plain text
    
    Args:
        report: Report data structure
        logfile: Path to log file that was scanned
        
    Returns:
        Plain text report string
    """
    lines = ["=" * 60]
    lines.append("CrashLens Guard Report")
    lines.append("=" * 60)
    lines.append(f"Scanned: {logfile}")
    lines.append(f"Rules Checked: {len(report['rules'])}")
    lines.append(f"Violations Found: {report['summary']['violations']}")
    lines.append("=" * 60)
    lines.append("")
    
    if report['summary']['violations'] == 0:
        lines.append("✅ No violations detected")
        lines.append("")
        return "\n".join(lines)
    
    for rid, meta in report["rules"].items():
        if meta["count"] == 0:
            continue
        
        lines.append(f"Rule: {rid} [{meta['severity'].upper()}]")
        lines.append(f"Description: {meta['description']}")
        lines.append(f"Violation Count: {meta['count']}")
        
        if meta['examples']:
            lines.append("Examples:")
            for ex in meta['examples'][:2]:
                timestamp = ex.get('timestamp', 'N/A')
                model = ex.get('model', 'N/A')
                tokens = ex.get('tokens', 'N/A')
                prompt = ex.get('prompt', '')
                prompt_preview = prompt[:60] if prompt else ''
                lines.append(f"  - {timestamp} | {model} | tokens={tokens} | prompt={prompt_preview}")
        
        lines.append("-" * 60)
        lines.append("")
    
    return "\n".join(lines)


@click.command("guard")
@click.argument("logfile", type=click.Path(exists=True))
@click.option("--rules", type=click.Path(exists=True), required=True,
              help="Path to rules.yaml file")
@click.option("--suppress", "-s", multiple=True,
              help="Rule IDs to suppress (repeatable or comma-separated, e.g., 'RL001' or 'RL001,RL002')")
@click.option("--severity", type=click.Choice(["warn", "error", "fatal"]), default="error",
              help="Minimum severity threshold for failing (default: error)")
@click.option("--output", type=click.Choice(["json", "md", "text", "html"]), default="text",
              help="Output format (default: text)")
@click.option("--no-content", is_flag=True,
              help="Redact content examples from report")
@click.option("--strip-pii", is_flag=True,
              help="Strip emails/phones from prompts in examples")
@click.option("--fail-on-violations", is_flag=True,
              help="Exit with code 1 when violations meet severity threshold")
@click.option("--dry-run", is_flag=True,
              help="Validate rules without failing CI (exit code always 0)")
@click.option("--summary-only", is_flag=True,
              help="Output condensed one-line-per-rule summary")
@click.option("--baseline-logs", type=click.Path(exists=True),
              help="Historical logs for dynamic P95/P99 baseline comparison")
@click.option("--baseline-deviation", type=float, default=0.50,
              help="Deviation threshold for baseline alerts (default: 0.50 = 50%)")
@click.option("--cost-cap", type=float,
              help="Maximum allowed total cost in USD (fails CI if exceeded)")
def guard(logfile, rules, suppress, severity, output, no_content, strip_pii, fail_on_violations, dry_run, summary_only, baseline_logs, baseline_deviation, cost_cap):
    """Guard against policy violations in JSONL logs
    
    Loads rules from YAML, evaluates log entries, and generates reports.
    Designed for CI integration with configurable exit codes.
    
    Example:
    
        crashlens guard logs.jsonl --rules .crashlens/rules.yaml --fail-on-violations
    
    Exit Codes:
    
        0 - No violations or only violations below severity threshold
        
        1 - Violations found that meet or exceed severity threshold
            (only when --fail-on-violations is set)
    """
    # Load rules from YAML
    try:
        ruleset = load_rules(rules)
    except click.ClickException:
        raise
    
    # Handle suppressions - support both repeatable and comma-separated formats
    suppress_set = set()
    for item in (suppress or []):
        if ',' in item:
            # Parse comma-separated: "RL001,RL002,RL003"
            suppress_set.update(s.strip() for s in item.split(',') if s.strip())
        else:
            # Single item: "RL001"
            suppress_set.add(item)
    
    # Initialize results structure
    results = {
        r.id: {
            "rule": r,
            "count": 0,
            "examples": []
        } 
        for r in ruleset if r.id not in suppress_set
    }
    
    # Evaluate each log entry against all rules
    # Also collect metrics for performance threshold checks
    all_logs = []
    try:
        for entry in load_jsonl(logfile):
            all_logs.append(entry)  # Store for performance threshold checks
            
            for r in ruleset:
                if r.id in suppress_set:
                    continue
                
                if eval_condition(r.cond, entry):
                    results[r.id]["count"] += 1
                    
                    # Collect example (unless no-content flag is set)
                    # Limit to get_max_examples() to prevent OOM on large logs
                    max_examples = get_max_examples()
                    if not no_content and len(results[r.id]["examples"]) < max_examples:
                        example = {
                            "timestamp": entry.get("timestamp"),
                            "model": entry.get("model"),
                            "tokens": entry.get("tokens"),
                            "retry_count": entry.get("retry_count"),
                            "fallback_triggered": entry.get("fallback_triggered"),
                            "endpoint": entry.get("endpoint"),
                            "prompt": redact_text(entry.get("prompt", ""), strip_pii)
                        }
                        results[r.id]["examples"].append(example)
    except click.ClickException:
        raise
    
    # Performance threshold checks (env var configured)
    slow_threshold = int(os.getenv("SLOW_RESPONSE_THRESHOLD_MS", "3000"))
    expensive_threshold = float(os.getenv("EXPENSIVE_REQUEST_THRESHOLD", "0.05"))
    error_rate_threshold = float(os.getenv("ERROR_RATE_THRESHOLD", "0.20"))
    
    # Dynamic baseline comparison (if baseline logs provided)
    baseline_violations = []
    if baseline_logs:
        try:
            from .performance_baseline import load_baseline_from_file
            from pathlib import Path
            
            baseline_calc = load_baseline_from_file(Path(baseline_logs))
            has_violations, violations = baseline_calc.compare_to_baseline(
                all_logs, 
                deviation_threshold=baseline_deviation
            )
            
            if has_violations:
                for violation in violations:
                    baseline_violations.append({
                        "id": f"baseline_{violation['metric']}",
                        "name": f"Baseline: {violation['metric'].upper().replace('_', ' ')}",
                        "severity": "fatal",
                        "description": violation['description'],
                        "count": 1,
                        "examples": []
                    })
        except Exception as e:
            click.echo(f"⚠️  Warning: Could not load baseline: {e}", err=True)
    
    # Cost cap check (if specified)
    cost_cap_violations = []
    total_cost = 0.0
    if cost_cap is not None:
        # Calculate total cost from all logs
        for entry in all_logs:
            total_cost += entry.get("cost_usd", 0.0)
        
        if total_cost > cost_cap:
            cost_cap_violations.append({
                "id": "cost_cap_exceeded",
                "name": "Budget: Cost Cap Exceeded",
                "severity": "fatal",
                "description": f"Total cost ${total_cost:.4f} exceeds cap ${cost_cap:.4f}",
                "count": 1,
                "examples": [],
                "total_cost": total_cost,
                "cost_cap": cost_cap,
                "overspend": total_cost - cost_cap
            })
    
    if all_logs:
        # Calculate metrics
        max_latency = max((log.get("response_time_ms", 0) for log in all_logs), default=0)
        max_cost = max((log.get("cost_usd", 0.0) for log in all_logs), default=0.0)
        error_count = sum(1 for log in all_logs if log.get("error", False))
        error_rate = error_count / len(all_logs) if all_logs else 0.0
        
        # Create synthetic rules for threshold violations
        # These are treated as fatal severity rules
        synthetic_violations = []
        
        if max_latency > slow_threshold:
            synthetic_violations.append({
                "id": "perf_latency_threshold",
                "name": "Performance: Latency Threshold",
                "severity": "fatal",
                "description": f"Max latency {max_latency}ms exceeds threshold {slow_threshold}ms",
                "count": 1,
                "examples": []
            })
        
        if max_cost > expensive_threshold:
            synthetic_violations.append({
                "id": "perf_cost_threshold",
                "name": "Performance: Cost Threshold",
                "severity": "fatal",
                "description": f"Max cost ${max_cost:.4f} exceeds threshold ${expensive_threshold:.4f}",
                "count": 1,
                "examples": []
            })
        
        if error_rate > error_rate_threshold:
            synthetic_violations.append({
                "id": "perf_error_rate_threshold",
                "name": "Performance: Error Rate Threshold",
                "severity": "fatal",
                "description": f"Error rate {error_rate:.2%} exceeds threshold {error_rate_threshold:.2%}",
                "count": 1,
                "examples": []
            })
        
        # Add baseline violations
        synthetic_violations.extend(baseline_violations)
        
        # Add cost cap violations
        synthetic_violations.extend(cost_cap_violations)
        
        # Add synthetic violations to results
        for syn_viol in synthetic_violations:
            # Create a mock rule object
            @dataclass
            class SyntheticRule:
                id: str
                name: str
                description: str
                severity: str
                cond: Dict[str, Any]
                action: str
            
            results[syn_viol["id"]] = {
                "rule": SyntheticRule(
                    id=syn_viol["id"],
                    name=syn_viol["name"],
                    description=syn_viol["description"],
                    severity=syn_viol["severity"],
                    cond={},
                    action="fail_ci"
                ),
                "count": syn_viol["count"],
                "examples": syn_viol["examples"]
            }
    
    # Determine highest severity level hit
    highest_hit = 0
    for rid, meta in results.items():
        if meta["count"] > 0:
            rank = SEVERITY_RANK.get(meta["rule"].severity, 2)
            if rank > highest_hit:
                highest_hit = rank
    
    # Get threshold rank
    threshold_rank = SEVERITY_RANK.get(severity, 2)
    
    # Build report structure
    report = {
        "summary": {
            "total_rules": len(results),
            "violations": sum(1 for m in results.values() if m["count"] > 0),
            "skipped_lines": _jsonl_skipped_lines,  # Track malformed lines
            "total_cost": total_cost if cost_cap is not None else None,
            "cost_cap": cost_cap if cost_cap is not None else None,
            "cost_cap_exceeded": total_cost > cost_cap if cost_cap is not None else False
        },
        "rules": {
            rid: {
                "count": meta["count"],
                "severity": meta["rule"].severity,
                "description": meta["rule"].description,
                "examples": meta["examples"]  # Show all collected examples (respects MAX_EXAMPLES)
            }
            for rid, meta in results.items()
        }
    }
    
    # Print skipped lines summary to stderr
    if _jsonl_skipped_lines > 0:
        click.echo("", err=True)
        click.echo(
            f"⚠️  Summary: Skipped {_jsonl_skipped_lines} malformed line(s) during parsing",
            err=True
        )
    
    # Print cost cap warning if exceeded
    if cost_cap is not None:
        if total_cost > cost_cap:
            overspend = total_cost - cost_cap
            click.echo("", err=True)
            click.echo(f"💰 COST CAP EXCEEDED: ${total_cost:.4f} / ${cost_cap:.4f} (over by ${overspend:.4f})", err=True)
        else:
            remaining = cost_cap - total_cost
            click.echo("", err=True)
            click.echo(f"💰 Cost Cap: ${total_cost:.4f} / ${cost_cap:.4f} (${remaining:.4f} remaining)", err=True)
    
    # Format and output report (stdout)
    if summary_only:
        # Condensed one-line-per-rule output
        click.echo("Rule ID | Violations | Severity")
        click.echo("-" * 40)
        for rid, meta in report["rules"].items():
            if meta["count"] > 0:  # Only show rules with violations
                click.echo(f"{rid:15} | {meta['count']:10} | {meta['severity']:8}")
    elif output == "json":
        click.echo(format_json_report(report))
    elif output == "md":
        click.echo(format_markdown_report(report, logfile))
    elif output == "html":
        click.echo(format_html_report(report, logfile))
    else:  # text
        click.echo(format_text_report(report, logfile))
    
    # Write JSON artifact for auditability (guard-<RUN_ID>.json)
    # Done after stdout output to avoid contaminating piped JSON
    run_id = os.getenv("CRASHLENS_RUN_ID") or generate_run_id()
    artifact_path = f"guard-{run_id}.json"
    try:
        with open(artifact_path, "w") as f:
            json.dump(report, f, indent=2)
        click.echo(f"📋 Artifact written: {artifact_path}", err=True)
    except IOError as e:
        click.echo(f"⚠️  Warning: Could not write artifact to {artifact_path}: {e}", err=True)
    
    # Determine exit code
    should_fail = fail_on_violations and highest_hit >= threshold_rank
    
    # Dry-run mode overrides exit code
    if dry_run:
        should_fail = False
    
    # Always output status to stderr to keep stdout clean for JSON/structured output
    if dry_run and report['summary']['violations'] > 0:
        click.echo("", err=True)
        click.echo("🔍 Guard (dry-run): Violations found but not failing CI", err=True)
    elif should_fail:
        click.echo("", err=True)
        click.echo("❌ Guard: Failing due to policy violations", err=True)
        sys.exit(1)
    else:
        if report['summary']['violations'] > 0:
            click.echo("", err=True)
            click.echo("⚠️  Guard: Violations found (not failing)", err=True)
        else:
            click.echo("", err=True)
            click.echo("✅ Guard: No violations detected", err=True)
        sys.exit(0)
