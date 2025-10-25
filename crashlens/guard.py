#!/usr/bin/env python3
"""
CrashLens Guard - CI-Friendly Policy Enforcement
Parses rules.yaml, evaluates JSONL logs, respects suppressions/severity threshold/privacy flags.
Emits json/markdown/text reports and exits nonzero on violations for CI integration.
"""

import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import click
import yaml
from jsonschema import ValidationError, validate

# PII detection patterns
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"\+?\d[\d\-\s]{7,}\d")

# Severity ranking for threshold comparison
SEVERITY_RANK = {"warn": 1, "error": 2, "fatal": 3}


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
    """Generator that yields parsed JSON objects from JSONL file
    
    Args:
        path: Path to JSONL log file
        
    Yields:
        Dict containing log entry data
        
    Raises:
        click.ClickException: If file cannot be read or contains invalid JSON
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as e:
                    raise click.ClickException(
                        f"Invalid JSON at line {line_num} in {path}: {e}"
                    )
    except FileNotFoundError:
        raise click.ClickException(f"Log file not found: {path}")


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


def eval_condition(cond: Dict[str, Any], entry: Dict[str, Any]) -> bool:
    """Evaluate rule conditions against a log entry
    
    Supported conditions:
    - if_model: exact string match on model field
    - if_tokens_gt: token count greater than threshold
    - if_retry_count_gt: retry count greater than threshold
    - if_fallback_triggered: boolean match on fallback_triggered
    - if_prompt_contains_pii: detects emails/phones in prompt
    - if_cost_usd_gt: cost greater than threshold
    
    All conditions within a rule are AND-ed together.
    
    Args:
        cond: Dictionary of condition key-value pairs
        entry: Log entry to evaluate
        
    Returns:
        True if all conditions match, False otherwise
    """
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
    
    return True


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
              help="Rule IDs to suppress (repeatable)")
@click.option("--severity", type=click.Choice(["warn", "error", "fatal"]), default="error",
              help="Minimum severity threshold for failing (default: error)")
@click.option("--output", type=click.Choice(["json", "md", "text"]), default="text",
              help="Output format (default: text)")
@click.option("--no-content", is_flag=True,
              help="Redact content examples from report")
@click.option("--strip-pii", is_flag=True,
              help="Strip emails/phones from prompts in examples")
@click.option("--fail-on-violations", is_flag=True,
              help="Exit with code 1 when violations meet severity threshold")
def guard(logfile, rules, suppress, severity, output, no_content, strip_pii, fail_on_violations):
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
    
    # Handle suppressions
    suppress = set(suppress or [])
    
    # Initialize results structure
    results = {
        r.id: {
            "rule": r,
            "count": 0,
            "examples": []
        } 
        for r in ruleset if r.id not in suppress
    }
    
    # Evaluate each log entry against all rules
    try:
        for entry in load_jsonl(logfile):
            for r in ruleset:
                if r.id in suppress:
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
            "violations": sum(1 for m in results.values() if m["count"] > 0)
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
    
    # Format and output report
    if output == "json":
        click.echo(format_json_report(report))
    elif output == "md":
        click.echo(format_markdown_report(report, logfile))
    else:  # text
        click.echo(format_text_report(report, logfile))
    
    # Determine exit code
    should_fail = fail_on_violations and highest_hit >= threshold_rank
    
    # Always output status to stderr to keep stdout clean for JSON/structured output
    if should_fail:
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
