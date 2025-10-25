#!/usr/bin/env python3
"""
Promote rule severity in CrashLens YAML policy files.

This script provides a command-line utility to promote rule severities
in YAML policy files. Promotion follows the order: warn → error → fatal

Usage:
    python scripts/promote_rule.py rules.yaml RULE_ID
    python scripts/promote_rule.py rules.yaml RULE_ID --dry-run
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click
import yaml


# Severity promotion ladder
SEVERITY_ORDER = ['warn', 'error', 'fatal']
SEVERITY_ALIASES = {
    'warning': 'warn',
    'err': 'error',
    'critical': 'fatal'
}


def normalize_severity(severity: str) -> str:
    """
    Normalize severity to canonical form.

    Args:
        severity: Severity level (warn/warning/error/err/fatal/critical)

    Returns:
        Canonical severity level (warn/error/fatal)

    Examples:
        >>> normalize_severity('warning')
        'warn'
        >>> normalize_severity('critical')
        'fatal'
    """
    severity_lower = severity.lower()
    return SEVERITY_ALIASES.get(severity_lower, severity_lower)


def get_next_severity(current: str) -> Optional[str]:
    """
    Get the next severity level in promotion order.

    Args:
        current: Current severity level

    Returns:
        Next severity level or None if already at highest (fatal)

    Examples:
        >>> get_next_severity('warn')
        'error'
        >>> get_next_severity('error')
        'fatal'
        >>> get_next_severity('fatal')
        None
    """
    normalized = normalize_severity(current)
    try:
        current_index = SEVERITY_ORDER.index(normalized)
        if current_index < len(SEVERITY_ORDER) - 1:
            return SEVERITY_ORDER[current_index + 1]
        return None  # Already at highest severity
    except ValueError:
        raise ValueError(f"Unknown severity level: {current}")


def load_rules_file(rules_path: Path) -> Dict[str, Any]:
    """
    Load and parse YAML rules file.

    Args:
        rules_path: Path to rules YAML file

    Returns:
        Parsed YAML content as dictionary

    Raises:
        FileNotFoundError: If rules file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    if not rules_path.exists():
        raise FileNotFoundError(f"Rules file not found: {rules_path}")

    with rules_path.open('r', encoding='utf-8') as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in {rules_path}: {e}")


def save_rules_file(rules_path: Path, rules: Dict[str, Any]) -> None:
    """
    Save rules dictionary to YAML file.

    Args:
        rules_path: Path to rules YAML file
        rules: Rules dictionary to save

    Raises:
        IOError: If file cannot be written
    """
    with rules_path.open('w', encoding='utf-8') as f:
        yaml.safe_dump(
            rules,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            indent=2
        )


def find_and_promote_rule(
    rules: Dict[str, Any],
    rule_id: str,
    dry_run: bool = False
) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Find rule by ID and promote its severity.

    Args:
        rules: Parsed rules dictionary
        rule_id: Rule ID to promote
        dry_run: If True, don't modify the dictionary

    Returns:
        Tuple of (success, old_severity, new_severity)
        - success: True if rule found and promotable
        - old_severity: Current severity (None if not found)
        - new_severity: New severity (None if already max or not found)

    Examples:
        >>> rules = {'rules': [{'id': 'TEST001', 'severity': 'warn'}]}
        >>> find_and_promote_rule(rules, 'TEST001', dry_run=True)
        (True, 'warn', 'error')
    """
    if 'rules' not in rules or not isinstance(rules['rules'], list):
        return False, None, None

    for rule in rules['rules']:
        if not isinstance(rule, dict):
            continue

        if rule.get('id') == rule_id:
            current_severity = rule.get('severity')
            if not current_severity:
                return False, None, None

            new_severity = get_next_severity(current_severity)
            if new_severity is None:
                # Already at maximum severity
                return False, current_severity, None

            if not dry_run:
                rule['severity'] = new_severity

            return True, current_severity, new_severity

    # Rule not found
    return False, None, None


@click.command()
@click.argument(
    'rules_file',
    type=click.Path(exists=True, path_type=Path)
)
@click.argument('rule_id')
@click.option(
    '--dry-run',
    is_flag=True,
    help='Preview changes without modifying the file'
)
def promote_rule(
    rules_file: Path,
    rule_id: str,
    dry_run: bool
) -> None:
    """
    Promote rule severity in YAML policy file.

    Promotion order: warn → error → fatal

    Examples:
        \b
        # Promote rule TEST001 in rules.yaml
        python scripts/promote_rule.py rules.yaml TEST001

        \b
        # Preview promotion without modifying file
        python scripts/promote_rule.py rules.yaml TEST001 --dry-run

    RULES_FILE: Path to YAML rules file
    RULE_ID: ID of the rule to promote
    """
    try:
        # Load rules
        click.echo(f"📂 Loading {rules_file}...")
        rules = load_rules_file(rules_file)

        # Attempt promotion
        success, old_severity, new_severity = find_and_promote_rule(
            rules,
            rule_id,
            dry_run=dry_run
        )

        if not success:
            if old_severity is None:
                # Rule not found
                click.echo(
                    click.style(
                        f"❌ Rule '{rule_id}' not found in {rules_file}",
                        fg='red'
                    ),
                    err=True
                )
                sys.exit(1)
            elif new_severity is None:
                # Already at max severity
                click.echo(
                    click.style(
                        f"⚠️  Rule '{rule_id}' already at maximum severity: {old_severity}",
                        fg='yellow'
                    )
                )
                sys.exit(0)

        # Report changes
        if dry_run:
            click.echo(
                click.style(
                    f"🔍 [DRY RUN] Would promote '{rule_id}': {old_severity} → {new_severity}",
                    fg='cyan'
                )
            )
            click.echo("   (No changes made)")
        else:
            # Save modified rules
            save_rules_file(rules_file, rules)
            click.echo(
                click.style(
                    f"✅ Promoted '{rule_id}': {old_severity} → {new_severity}",
                    fg='green'
                )
            )
            click.echo(f"   Updated: {rules_file}")

    except FileNotFoundError as e:
        click.echo(click.style(f"❌ {e}", fg='red'), err=True)
        sys.exit(1)
    except yaml.YAMLError as e:
        click.echo(click.style(f"❌ YAML Error: {e}", fg='red'), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"❌ Unexpected error: {e}", fg='red'), err=True)
        sys.exit(1)


if __name__ == '__main__':
    promote_rule()
