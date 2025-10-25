#!/usr/bin/env python3
"""
Promote Rule Severity Helper

Usage:
    python scripts/promote-rule.py <rule_id> <new_severity> [--rules-file .crashlens/rules.yaml]

Example:
    python scripts/promote-rule.py RL001 error
    python scripts/promote-rule.py RL002 fatal --rules-file policies/custom.yaml

This script safely promotes a rule's severity from warn -> error -> fatal.
It validates the new severity and preserves all other rule properties.
"""

import sys
from pathlib import Path
from typing import Optional

import click
import yaml


@click.command()
@click.argument("rule_id", type=str)
@click.argument("new_severity", type=click.Choice(["warn", "error", "fatal"]))
@click.option(
    "--rules-file",
    type=click.Path(exists=True, path_type=Path),
    default=".crashlens/rules.yaml",
    help="Path to rules.yaml file (default: .crashlens/rules.yaml)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would change without modifying the file",
)
def promote_rule(
    rule_id: str, new_severity: str, rules_file: Path, dry_run: bool
) -> None:
    """Promote a rule's severity level
    
    Safely updates the severity of a specific rule in rules.yaml.
    Use --dry-run to preview changes before applying.
    
    Args:
        rule_id: ID of the rule to promote (e.g., RL001)
        new_severity: New severity level (warn, error, or fatal)
        rules_file: Path to rules.yaml
        dry_run: Preview changes without modifying file
    """
    # Load rules file
    try:
        with open(rules_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        click.echo(
            click.style(f"❌ Rules file not found: {rules_file}", fg="red"), err=True
        )
        sys.exit(1)
    except yaml.YAMLError as e:
        click.echo(
            click.style(f"❌ Invalid YAML in {rules_file}: {e}", fg="red"), err=True
        )
        sys.exit(1)
    
    if not data or "rules" not in data:
        click.echo(
            click.style(f"❌ No 'rules' key found in {rules_file}", fg="red"), err=True
        )
        sys.exit(1)
    
    # Find the rule
    rule_found = False
    old_severity: Optional[str] = None
    
    for rule in data["rules"]:
        if rule.get("id") == rule_id:
            rule_found = True
            old_severity = rule.get("severity", "warn")
            
            if old_severity == new_severity:
                click.echo(
                    click.style(
                        f"ℹ️  Rule {rule_id} already has severity '{new_severity}'",
                        fg="yellow",
                    )
                )
                sys.exit(0)
            
            # Update severity
            if dry_run:
                click.echo(
                    click.style(
                        f"🔍 DRY RUN: Would change rule {rule_id} "
                        f"from '{old_severity}' -> '{new_severity}'",
                        fg="cyan",
                    )
                )
                click.echo(f"\nRule preview:")
                click.echo(f"  id: {rule['id']}")
                click.echo(f"  description: {rule.get('description', 'N/A')}")
                click.echo(f"  action: {rule.get('action')}")
                click.echo(click.style(f"  severity: {new_severity}", fg="green"))
            else:
                rule["severity"] = new_severity
                click.echo(
                    click.style(
                        f"✅ Promoted rule {rule_id}: "
                        f"'{old_severity}' -> '{new_severity}'",
                        fg="green",
                    )
                )
            break
    
    if not rule_found:
        click.echo(
            click.style(
                f"❌ Rule ID '{rule_id}' not found in {rules_file}", fg="red"
            ),
            err=True,
        )
        click.echo("\nAvailable rule IDs:")
        for rule in data["rules"]:
            click.echo(f"  - {rule.get('id')} (severity: {rule.get('severity', 'warn')})")
        sys.exit(1)
    
    # Write back to file (unless dry-run)
    if not dry_run:
        try:
            with open(rules_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
            click.echo(f"📝 Updated {rules_file}")
        except Exception as e:
            click.echo(
                click.style(f"❌ Failed to write {rules_file}: {e}", fg="red"),
                err=True,
            )
            sys.exit(1)


if __name__ == "__main__":
    promote_rule()
