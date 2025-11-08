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
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import yaml
from jsonschema import ValidationError, validate

# Import config resolution for .crashlens/config.yaml fallback
from crashlens.config import resolve_variables_in_obj

# Import streaming reader for large file support
from crashlens.io.stream_reader import stream_jsonl

# Import unified engine adapter (Step 4 Phase 2)
# Only used when CRASHLENS_USE_UNIFIED_ENGINE=1
from crashlens.guard_adapter import GuardPolicyEngineAdapter

# PII detection patterns
EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
# Phone: more restrictive - require + prefix or longer sequences to avoid SSN/date matches
PHONE_RE = re.compile(r"(\+\d[\d\-\s]{8,}|(?<!\d)\d{3}[\-\s]\d{3}[\-\s]\d{4}(?!\d))")
# SSN: exactly XXX-XX-XXXX format (US Social Security Number)
SSN_RE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
# Credit card: 16 digits with optional spaces/dashes between 4-digit groups
CREDIT_CARD_RE = re.compile(r"(?<!\d)(\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4})(?!\d)")

# Severity ranking for threshold comparison
SEVERITY_RANK = {"warn": 1, "error": 2, "fatal": 3}

# Streaming threshold (file size in bytes, default: 10 MB)
# Use environment variable CRASHLENS_STREAM_THRESHOLD to customize
STREAM_THRESHOLD_BYTES = int(os.getenv("CRASHLENS_STREAM_THRESHOLD", str(10 * 1024 * 1024)))
STREAM_BATCH_SIZE = int(os.getenv("CRASHLENS_STREAM_BATCH_SIZE", "5000"))

# Feature flag for unified engine (Step 4 Phase 2)
# Set CRASHLENS_USE_UNIFIED_ENGINE=1 to enable GuardPolicyEngineAdapter
# Note: Check at runtime in guard() function, not at module load time


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
            cond=resolve_variables_in_obj(r["if"]),  # Resolve variables from env/.crashlens/config.yaml
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


def find_rules_path(provided: Optional[str] = None) -> Optional[str]:
    """
    Find rules.yaml path, either from provided path or autodiscovery.
    
    If provided path is given, returns it if it exists.
    Otherwise, searches in standard locations:
    1. .crashlens/rules.yaml (project-specific)
    2. .github/crashlens/rules.yaml (GitHub Actions convention)
    3. rules.yaml (root directory)
    
    Args:
        provided: Optional path to rules file
        
    Returns:
        Path to rules file, or None if not found
    """
    if provided:
        return provided if os.path.exists(provided) else None
    
    search_paths = [
        ".crashlens/rules.yaml",
        ".github/crashlens/rules.yaml",
        "rules.yaml"
    ]
    
    for path in search_paths:
        if os.path.exists(path):
            return path
    
    return None


def autodiscover_rules() -> Optional[str]:
    """
    Autodiscover rules.yaml in standard locations.
    
    DEPRECATED: Use find_rules_path() instead.
    
    Search order:
    1. .crashlens/rules.yaml (project-specific)
    2. .github/crashlens/rules.yaml (GitHub Actions convention)
    3. rules.yaml (root directory)
    
    Returns:
        Path to discovered rules file, or None if not found
    """
    return find_rules_path()


def resolve_log_sources(logfile_arg: Optional[str] = None) -> List[Path]:
    """
    Resolve log sources from argument, accepting file, directory, glob, or stdin.
    
    Supports:
    - Single file: logs.jsonl
    - Directory: logs/ (finds all *.jsonl files)
    - Glob pattern: logs/*.jsonl
    - Stdin: - or None (reads from stdin)
    
    Args:
        logfile_arg: Path argument (file/dir/glob) or '-' for stdin, or None
        
    Returns:
        List of Path objects to process, or [Path('-')] for stdin
        
    Raises:
        click.ClickException: If no valid log sources found
    """
    from pathlib import Path as PathLib
    import glob as glob_module
    
    # Handle stdin
    if logfile_arg is None or logfile_arg == '-':
        return [PathLib('-')]
    
    logfile_path = PathLib(logfile_arg)
    
    # Handle directory
    if logfile_path.is_dir():
        jsonl_files = sorted(logfile_path.glob('*.jsonl'))
        if not jsonl_files:
            raise click.ClickException(f"No *.jsonl files found in directory: {logfile_arg}")
        return jsonl_files
    
    # Handle glob pattern (has wildcard characters)
    if '*' in logfile_arg or '?' in logfile_arg or '[' in logfile_arg:
        matches = sorted([PathLib(p) for p in glob_module.glob(logfile_arg)])
        if not matches:
            raise click.ClickException(f"No files match glob pattern: {logfile_arg}")
        return matches
    
    # Handle single file
    if logfile_path.is_file():
        return [logfile_path]
    
    raise click.ClickException(f"Log source not found: {logfile_arg}")


def interpolate_variables(value: Any) -> Any:
    """
    Interpolate environment variables in string values.
    
    Supports both $VAR and ${VAR} syntax. Non-string values are returned unchanged.
    
    Args:
        value: Value to interpolate (can be string, dict, list, or other)
        
    Returns:
        Value with variables interpolated
        
    Examples:
        >>> os.environ['TEAM'] = 'platform'
        >>> interpolate_variables('team=$TEAM')
        'team=platform'
        >>> interpolate_variables('${THRESHOLD}')
        '100' (if THRESHOLD=100)
    """
    if isinstance(value, str):
        # Replace ${VAR} format
        import re
        def replace_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))  # Keep original if not found
        
        value = re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}', replace_var, value)
        
        # Replace $VAR format (word boundary required)
        value = re.sub(r'\$([A-Za-z_][A-Za-z0-9_]*)\b', replace_var, value)
        
        return value
    elif isinstance(value, dict):
        return {k: interpolate_variables(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [interpolate_variables(item) for item in value]
    else:
        return value


class PIIDetector:
    """Pluggable PII detection and redaction interface
    
    This class provides an extensible interface for PII detection.
    Override detect() and redact() methods to customize behavior.
    
    Supports:
    - Email addresses
    - Phone numbers (US and international)
    - Social Security Numbers (SSN)
    - Credit card numbers
    """
    
    def __init__(self):
        """Initialize detector with default regex patterns"""
        self.email_pattern = EMAIL_RE
        self.phone_pattern = PHONE_RE
        self.ssn_pattern = SSN_RE
        self.credit_card_pattern = CREDIT_CARD_RE
    
    def detect(self, text: str) -> bool:
        """Check if text contains PII
        
        Args:
            text: Input text to check
            
        Returns:
            True if PII detected, False otherwise
        """
        if not text:
            return False
        return bool(
            self.email_pattern.search(text) or 
            self.phone_pattern.search(text) or
            self.ssn_pattern.search(text) or
            self.credit_card_pattern.search(text)
        )
    
    def redact(self, text: str) -> str:
        """Redact PII from text
        
        Args:
            text: Input text to redact
            
        Returns:
            Text with PII replaced by [REDACTED_*] placeholders
        """
        if not text:
            return ""
        # Redact in order: email, SSN, credit card, then phone
        # (SSN and CC first to avoid phone regex overlapping)
        output = self.email_pattern.sub("[REDACTED_EMAIL]", text)
        output = self.ssn_pattern.sub("[REDACTED_SSN]", output)
        output = self.credit_card_pattern.sub("[REDACTED_CREDIT_CARD]", output)
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
    - "and" / "all_of": List of conditions (all must be true)
    - "or" / "any_of": List of conditions (at least one must be true)
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
        
        # OR composition (both syntaxes supported)
        {"or": [{"if_model": "gpt-4o"}, {"if_model": "claude-3"}]}
        {"any_of": [{"if_model": "gpt-4o"}, {"if_model": "claude-3"}]}
        
        # AND composition (both syntaxes supported)
        {"and": [{"if_cost_usd_gt": 0.10}, {"if_model": "gpt-4o"}]}
        {"all_of": [{"if_cost_usd_gt": 0.10}, {"if_model": "gpt-4o"}]}
        
        # NOT composition
        {"not": {"if_model": "gpt-3.5-turbo"}}
        
        # Nested composition
        {"all_of": [
            {"if_cost_usd_gt": 0.10},
            {"any_of": [{"if_model": "gpt-4o"}, {"if_retry_count_gt": 2}]}
        ]}
    """
    # Handle boolean composition (support both syntaxes)
    if "and" in cond or "all_of" in cond:
        conditions = cond.get("and") or cond.get("all_of")
        if not isinstance(conditions, list):
            return False
        return all(evaluate_condition(sub_cond, entry) for sub_cond in conditions)
    
    if "or" in cond or "any_of" in cond:
        conditions = cond.get("or") or cond.get("any_of")
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


def format_html_report(report: Dict[str, Any], logfile: str, summary_only: bool = False) -> str:
    """Format report as HTML with Bootstrap styling
    
    Args:
        report: Report data structure
        logfile: Path to log file that was scanned
        summary_only: If True, omit content examples
        
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
            
            # Add examples if available and not summary_only
            if meta['examples'] and not summary_only:
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
@click.argument("logfile", type=click.Path(), required=False, default=None)
@click.option("--rules", type=click.Path(exists=True), required=False,
              help="Path to rules.yaml file (auto-discovers if not specified)")
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
@click.option("--report-path", type=click.Path(), default="crashlens-report.json",
              help="Path to write structured JSON report (default: crashlens-report.json)")
@click.option("--annotation-hook", type=str,
              help="Command to run after report is written (receives report path as argument)")
def guard(logfile, rules, suppress, severity, output, no_content, strip_pii, fail_on_violations, dry_run, summary_only, baseline_logs, baseline_deviation, cost_cap, report_path, annotation_hook):
    """Guard against policy violations in JSONL logs
    
    Loads rules from YAML, evaluates log entries, and generates reports.
    Designed for CI integration with configurable exit codes and GitHub annotation hooks.
    
    Supports multiple input sources:
    - Single file: crashlens guard logs.jsonl
    - Directory: crashlens guard logs/ (processes all *.jsonl files)
    - Glob pattern: crashlens guard "logs/*.jsonl"
    - Stdin: crashlens guard - < logs.jsonl OR cat logs.jsonl | crashlens guard
    
    Example:
    
        # Basic usage with violations failing CI
        crashlens guard logs.jsonl --rules .crashlens/rules.yaml --fail-on-violations
        
        # Process directory of logs
        crashlens guard logs/ --fail-on-violations
        
        # Process with glob pattern
        crashlens guard "sample-logs/*.jsonl" --fail-on-violations
        
        # Read from stdin
        cat logs.jsonl | crashlens guard --fail-on-violations
        
        # Write report and trigger GitHub Checks annotations
        crashlens guard logs.jsonl --rules rules.yaml \\
            --report-path crashlens-report.json \\
            --annotation-hook "python tools/post_crashlens_annotations.py crashlens-report.json $GITHUB_SHA"
        
        # Dry-run mode (never fails CI, useful for testing)
        crashlens guard logs.jsonl --rules rules.yaml --dry-run
    
    Exit Codes:
    
        0 - No violations, violations below severity threshold, or --dry-run mode
        
        1 - Violations found that meet or exceed severity threshold
            (only when --fail-on-violations is set and NOT in --dry-run mode)
    """
    # ============================================================
    # Step 7: Deprecation Notice for guard command
    # ============================================================
    # Show deprecation warning unless unified engine is already enabled
    # or CRASHLENS_QUIET is set (to avoid noise in CI)
    if not os.getenv('CRASHLENS_USE_UNIFIED_ENGINE') and not os.getenv('CRASHLENS_QUIET'):
        click.echo("", err=True)
        click.echo("⚠️  DEPRECATION NOTICE: The 'guard' command is being phased out.", err=True)
        click.echo("   Please migrate to 'guard' for the unified engine experience.", err=True)
        click.echo("", err=True)
        click.echo("   Migration: crashlens guard <your-args>", err=True)
        click.echo("", err=True)
        click.echo("   To enable unified engine with 'guard':", err=True)
        click.echo("     export CRASHLENS_USE_UNIFIED_ENGINE=1", err=True)
        click.echo("", err=True)
        click.echo("   To silence this warning:", err=True)
        click.echo("     export CRASHLENS_QUIET=1", err=True)
        click.echo("", err=True)
    
    # Resolve log sources (file, directory, glob, or stdin)
    try:
        log_sources = resolve_log_sources(logfile)
    except click.ClickException:
        raise
    
    # Autodiscover rules if not specified
    rules = find_rules_path(rules)
    if rules is None:
        raise click.ClickException(
            "No rules file found. Specify --rules or create rules.yaml in:\n"
            "  - .crashlens/rules.yaml\n"
            "  - .github/crashlens/rules.yaml\n"
            "  - rules.yaml"
        )
    
    # Show autodiscovery message if rules were found automatically
    if not logfile or logfile == '-':
        click.echo(f"📋 Using rules: {rules}", err=True)
    else:
        click.echo(f"📋 Processing {len(log_sources)} log source(s) with rules: {rules}", err=True)
    
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
    
    # ============================================================
    # STEP 4 PHASE 2: Unified Engine Integration
    # ============================================================
    # If CRASHLENS_USE_UNIFIED_ENGINE=1, use GuardPolicyEngineAdapter
    # instead of legacy evaluation loop
    # Check at runtime (not at module load time) to support test environment variables
    # ============================================================
    use_unified_engine = os.getenv("CRASHLENS_USE_UNIFIED_ENGINE", "0") == "1"
    
    if use_unified_engine:
        click.echo("🔧 Using unified PolicyEngine (CRASHLENS_USE_UNIFIED_ENGINE=1)", err=True)
        
        try:
            # Initialize adapter with rules and configuration
            # Use Path from pathlib (imported at top of file)
            from pathlib import Path as PathType
            adapter = GuardPolicyEngineAdapter(
                rules_yaml_path=PathType(rules),
                detector_mode="none",  # Start with no detection, can be upgraded later
                suppress_ids=suppress_set,
                verbose=False
            )
            
            # Process all log sources through unified pipeline
            violations_by_rule, metrics = adapter.process_logs(
                log_paths=log_sources,
                model_pricing=None  # Can be added in future phases
            )
            
            # Convert PolicyEngine violations back to legacy guard format
            results = adapter.convert_violations_to_legacy_format(
                violations_by_rule=violations_by_rule,
                strip_pii=strip_pii,
                no_content=no_content,
                max_examples=get_max_examples()
            )
            
            # Enrich results with rule objects for compatibility with downstream code
            # The adapter doesn't have access to Rule objects, so we add them here
            for rule_id in results:
                # Find matching rule from ruleset
                matching_rule = next((r for r in ruleset if r.id == rule_id), None)
                if matching_rule:
                    results[rule_id]["rule"] = matching_rule
                else:
                    # Create a mock rule if not found (shouldn't happen)
                    @dataclass
                    class MockRule:
                        id: str
                        description: str
                        severity: str
                        cond: Dict[str, Any]
                        action: str
                    
                    results[rule_id]["rule"] = MockRule(
                        id=rule_id,
                        description=results[rule_id].get("description", ""),
                        severity=results[rule_id].get("severity", "error"),
                        cond={},
                        action="error"
                    )
            
            # Initialize all rules that had no violations (for reporting consistency)
            for rule in ruleset:
                if rule.id not in results and rule.id not in suppress_set:
                    results[rule.id] = {
                        "rule": rule,
                        "count": 0,
                        "examples": []
                    }
            
            # Initialize all_logs for downstream metrics (empty for now in unified path)
            # Future: adapter should expose logs for performance checks
            all_logs = []
            
            click.echo(f"✅ Unified engine processed {metrics.get('total_records', 0)} records in {metrics.get('total_batches', 0)} batches", err=True)
            
        except Exception as e:
            click.echo(f"❌ Error in unified engine: {e}", err=True)
            import traceback
            traceback.print_exc()
            raise click.ClickException(f"Unified engine failed: {e}")
    
    else:
        # ============================================================
        # LEGACY CODE PATH (original guard evaluation)
        # ============================================================
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
        
        from pathlib import Path as PathLib  # Avoid conflict with click.Path
        
        try:
            # Process each log source
            for source_path in log_sources:
                # Handle stdin
                if str(source_path) == '-':
                    click.echo("📖 Reading from stdin...", err=True)
                    stdin_stream = click.get_text_stream('stdin')
                    try:
                        for line in stdin_stream:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                entry = json.loads(line)
                            except json.JSONDecodeError:
                                continue  # Skip malformed lines
                            
                            all_logs.append(entry)
                            
                            for r in ruleset:
                                if r.id in suppress_set:
                                    continue
                                
                                if eval_condition(r.cond, entry):
                                    results[r.id]["count"] += 1
                                    
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
                    except (EOFError, KeyboardInterrupt):
                        pass  # Graceful termination for stdin
                    continue
                
                # Handle regular files
                file_size_bytes = source_path.stat().st_size
                use_streaming = file_size_bytes > STREAM_THRESHOLD_BYTES
                
                if use_streaming:
                    file_size_mb = file_size_bytes / (1024 * 1024)
                    click.echo(f"📊 Processing {source_path.name} ({file_size_mb:.2f} MB) in streaming mode (batch_size={STREAM_BATCH_SIZE})", err=True)
                    
                    # Streaming mode for large files
                    for batch in stream_jsonl(source_path, batch_size=STREAM_BATCH_SIZE, skip_malformed=True, verbose=False):
                        for entry in batch:
                            all_logs.append(entry)
                            
                            for r in ruleset:
                                if r.id in suppress_set:
                                    continue
                                
                                if eval_condition(r.cond, entry):
                                    results[r.id]["count"] += 1
                                    
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
                else:
                    # Original line-by-line mode for small files
                    for entry in load_jsonl(str(source_path)):
                        all_logs.append(entry)
                        
                        for r in ruleset:
                            if r.id in suppress_set:
                                continue
                            
                            if eval_condition(r.cond, entry):
                                results[r.id]["count"] += 1
                                
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
            
            # Use new generate_synthetic_violations method (Step 6)
            synthetic_violations = baseline_calc.generate_synthetic_violations(
                all_logs,
                deviation_threshold=baseline_deviation
            )
            
            # Add synthetic violations to baseline_violations list
            baseline_violations.extend(synthetic_violations)
            
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
        click.echo(format_html_report(report, logfile, summary_only))
    else:  # text
        click.echo(format_text_report(report, logfile))
    
    # Write JSON report to specified path (for auditability and annotation hooks)
    # Done after stdout output to avoid contaminating piped JSON
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        click.echo(f"📋 Report written: {report_path}", err=True)
    except IOError as e:
        click.echo(f"⚠️  Warning: Could not write report to {report_path}: {e}", err=True)
    
    # Run annotation hook if provided (e.g., GitHub Checks API posting)
    if annotation_hook:
        try:
            # Substitute {report_path} placeholder if present
            hook_cmd = annotation_hook.replace("{report_path}", report_path)
            
            click.echo(f"🔗 Running annotation hook: {hook_cmd}", err=True)
            result = subprocess.run(
                hook_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout for external hooks
            )
            
            if result.returncode == 0:
                click.echo("✅ Annotation hook completed successfully", err=True)
                if result.stdout:
                    click.echo(result.stdout, err=True)
            else:
                click.echo(f"⚠️  Annotation hook failed with exit code {result.returncode}", err=True)
                if result.stderr:
                    click.echo(result.stderr, err=True)
        except subprocess.TimeoutExpired:
            click.echo("⚠️  Annotation hook timed out after 60 seconds", err=True)
        except Exception as e:
            click.echo(f"⚠️  Error running annotation hook: {e}", err=True)
    
    # Determine exit code based on violations and cost cap
    should_fail = False
    
    # Check policy violations
    if fail_on_violations and highest_hit >= threshold_rank:
        should_fail = True
    
    # Check cost cap (if specified)
    if cost_cap is not None and total_cost > cost_cap:
        should_fail = True
    
    # Dry-run mode ALWAYS overrides exit code (never fails)
    if dry_run:
        should_fail = False
    
    # Always output status to stderr to keep stdout clean for JSON/structured output
    if dry_run and (report['summary']['violations'] > 0 or (cost_cap and total_cost > cost_cap)):
        click.echo("", err=True)
        click.echo("🔍 Guard (dry-run): Issues found but not failing CI", err=True)
    elif should_fail:
        click.echo("", err=True)
        if cost_cap and total_cost > cost_cap:
            click.echo("❌ Guard: Failing due to cost cap violation", err=True)
        else:
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
