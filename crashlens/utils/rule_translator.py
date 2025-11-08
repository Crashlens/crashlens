"""
Rule translator for CrashLens guard/policy-check unification.

This module translates policy-check YAML rules into guard-compatible
rule structures, enabling seamless migration between the two formats.
"""

import sys
import json
import yaml
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


# Severity mapping: policy-check -> guard
SEVERITY_MAP = {
    'critical': 'fatal',
    'high': 'error',
    'medium': 'warn',
    'low': 'warn',
}

# Action mapping: policy-check -> guard
ACTION_MAP = {
    'block': 'fail_ci',
    'fail': 'error',
    'warn': 'warn',
}

# Supported operators in guard's condition evaluator
GUARD_SUPPORTED_OPERATORS = {
    '==', '!=', '>', '<', '>=', '<=',
    'in', 'not in', 'contains', 'startswith', 'endswith',
}


@dataclass
class TranslationWarning:
    """Warning generated during translation."""
    rule_id: str
    field: str
    message: str
    severity: str = 'warning'


@dataclass
class TranslationResult:
    """Result of translating a policy file to guard rules."""
    rules: List[Dict[str, Any]]
    warnings: List[TranslationWarning]
    errors: List[TranslationWarning]
    
    @property
    def success(self) -> bool:
        """Translation succeeded if no errors occurred."""
        return len(self.errors) == 0


class RuleTranslator:
    """Translates policy-check rules to guard rules."""
    
    def __init__(self, strict: bool = False):
        """Initialize translator.
        
        Args:
            strict: If True, treat warnings as errors and fail translation.
        """
        self.strict = strict
        self.warnings: List[TranslationWarning] = []
        self.errors: List[TranslationWarning] = []
    
    def translate_policy_file(self, policy_path: Path) -> TranslationResult:
        """Translate a policy-check YAML file to guard rules.
        
        Args:
            policy_path: Path to policy YAML file.
            
        Returns:
            TranslationResult with rules, warnings, and errors.
        """
        try:
            with open(policy_path, 'r', encoding='utf-8') as f:
                policy_data = yaml.safe_load(f)
        except Exception as e:
            self.errors.append(TranslationWarning(
                rule_id='<file>',
                field='',
                message=f"Failed to load YAML: {e}",
                severity='error'
            ))
            return TranslationResult([], self.warnings, self.errors)
        
        if not policy_data or 'rules' not in policy_data:
            self.errors.append(TranslationWarning(
                rule_id='<file>',
                field='rules',
                message="Policy file missing 'rules' key",
                severity='error'
            ))
            return TranslationResult([], self.warnings, self.errors)
        
        guard_rules = []
        for rule in policy_data['rules']:
            translated = self._translate_rule(rule)
            if translated:
                guard_rules.append(translated)
        
        # In strict mode, treat warnings as errors
        if self.strict and self.warnings:
            self.errors.extend(self.warnings)
            self.warnings = []
        
        return TranslationResult(guard_rules, self.warnings, self.errors)
    
    def _translate_rule(self, rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Translate a single policy rule to guard format.
        
        Args:
            rule: Policy rule dictionary.
            
        Returns:
            Guard-compatible rule dictionary, or None if translation fails.
        """
        # Validate required fields
        if 'id' not in rule:
            # Generate rule ID if missing
            rule_id = f"POL_{uuid.uuid4().hex[:8]}"
            self.warnings.append(TranslationWarning(
                rule_id=rule_id,
                field='id',
                message=f"Missing rule ID, generated: {rule_id}"
            ))
        else:
            rule_id = rule['id']
        
        if 'match' not in rule:
            self.errors.append(TranslationWarning(
                rule_id=rule_id,
                field='match',
                message="Rule missing required 'match' field",
                severity='error'
            ))
            return None
        
        # Translate severity
        severity = rule.get('severity', 'medium')
        if severity not in SEVERITY_MAP:
            self.warnings.append(TranslationWarning(
                rule_id=rule_id,
                field='severity',
                message=f"Unknown severity '{severity}', defaulting to 'warn'"
            ))
            guard_severity = 'warn'
        else:
            guard_severity = SEVERITY_MAP[severity]
        
        # Translate action
        action = rule.get('action', 'warn')
        if action not in ACTION_MAP:
            self.warnings.append(TranslationWarning(
                rule_id=rule_id,
                field='action',
                message=f"Unknown action '{action}', defaulting to 'warn'"
            ))
            guard_action = 'warn'
        else:
            guard_action = ACTION_MAP[action]
        
        # Translate conditions
        guard_conditions = self._translate_conditions(rule_id, rule['match'])
        if guard_conditions is None:
            return None
        
        return {
            'id': rule_id,
            'description': rule.get('description', ''),
            'if': guard_conditions,
            'action': guard_action,
            'severity': guard_severity,
        }
    
    def _translate_conditions(self, rule_id: str, match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Translate policy match conditions to guard 'if' conditions.
        
        Args:
            rule_id: Rule ID for error reporting.
            match: Policy match block.
            
        Returns:
            Guard-compatible conditions, or None if translation fails.
        """
        guard_conditions = {}
        
        for field, condition in match.items():
            # Handle boolean composition (and, or, not)
            if field in ['and', 'or', 'not', 'all_of', 'any_of']:
                # Guard supports these natively
                if field == 'all_of':
                    field = 'and'
                elif field == 'any_of':
                    field = 'or'
                
                if isinstance(condition, list):
                    guard_conditions[field] = [
                        self._translate_conditions(rule_id, c) 
                        for c in condition
                    ]
                elif isinstance(condition, dict):
                    guard_conditions[field] = self._translate_conditions(rule_id, condition)
                else:
                    self.errors.append(TranslationWarning(
                        rule_id=rule_id,
                        field=field,
                        message=f"Invalid {field} condition type",
                        severity='error'
                    ))
                    return None
                continue
            
            # Translate field-level conditions
            translated = self._translate_field_condition(rule_id, field, condition)
            if translated is None:
                return None
            
            guard_conditions.update(translated)
        
        return guard_conditions
    
    def _translate_field_condition(
        self, 
        rule_id: str, 
        field: str, 
        condition: Any
    ) -> Optional[Dict[str, Any]]:
        """Translate a single field condition.
        
        Args:
            rule_id: Rule ID for error reporting.
            field: Field name (may use dot notation).
            condition: Condition value or expression.
            
        Returns:
            Guard-compatible condition, or None if unsupported.
        """
        # Map common field names to guard equivalents
        field_map = {
            'retry_count': 'retry_count',
            'model': 'model',
            'tokens': 'tokens',
            'cost_usd': 'cost_usd',
            'fallback_triggered': 'fallback_triggered',
            'prompt': 'prompt',
            'response_time_ms': 'response_time_ms',
            'error_rate': 'error_rate',
        }
        
        guard_field = field_map.get(field, field)
        
        # Handle string conditions with operators
        if isinstance(condition, str):
            # Check for operator-based conditions
            for op in ['>=', '<=', '>', '<', '==', '!=', 'regex:', 'contains:', 'in:']:
                if condition.startswith(op):
                    operator = op.rstrip(':')
                    value = condition[len(op):].strip()
                    
                    # Check if operator is supported
                    if operator == 'regex':
                        self.warnings.append(TranslationWarning(
                            rule_id=rule_id,
                            field=field,
                            message=f"Regex operator not yet supported in guard, condition may not work"
                        ))
                        # Store as-is, guard will need to handle it
                        return {f'if_{guard_field}': condition}
                    
                    if operator not in GUARD_SUPPORTED_OPERATORS:
                        if self.strict:
                            self.errors.append(TranslationWarning(
                                rule_id=rule_id,
                                field=field,
                                message=f"Unsupported operator '{operator}' in strict mode",
                                severity='error'
                            ))
                            return None
                        else:
                            self.warnings.append(TranslationWarning(
                                rule_id=rule_id,
                                field=field,
                                message=f"Operator '{operator}' may not be fully supported"
                            ))
                    
                    # Convert to guard format
                    if operator in ['>', '<', '>=', '<=']:
                        return {f'if_{guard_field}_gt' if operator in ['>', '>='] else f'if_{guard_field}': condition}
                    else:
                        return {f'if_{guard_field}': condition}
            
            # Simple string match
            return {f'if_{guard_field}': condition}
        
        # Handle list conditions (in operator)
        elif isinstance(condition, list):
            return {f'if_{guard_field}': condition}
        
        # Handle boolean conditions
        elif isinstance(condition, bool):
            return {f'if_{guard_field}': condition}
        
        # Handle numeric conditions
        elif isinstance(condition, (int, float)):
            return {f'if_{guard_field}': condition}
        
        else:
            self.warnings.append(TranslationWarning(
                rule_id=rule_id,
                field=field,
                message=f"Unsupported condition type: {type(condition).__name__}"
            ))
            return {f'if_{guard_field}': condition}


def translate_file(
    input_path: Path, 
    output_path: Optional[Path] = None,
    strict: bool = False
) -> TranslationResult:
    """Translate a policy file to guard rules.
    
    Args:
        input_path: Path to input policy YAML.
        output_path: Optional path to write guard rules JSON.
        strict: If True, fail on warnings.
        
    Returns:
        TranslationResult with rules and diagnostics.
    """
    translator = RuleTranslator(strict=strict)
    result = translator.translate_policy_file(input_path)
    
    if output_path and result.success:
        output_data = {
            'rules': result.rules,
            'metadata': {
                'source': str(input_path),
                'translator_version': '1.0.0',
                'warnings_count': len(result.warnings),
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
    
    return result


def main():
    """CLI entry point for rule translator."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Translate policy-check rules to guard format')
    parser.add_argument('--input', required=True, help='Input policy YAML file')
    parser.add_argument('--output', help='Output guard rules JSON file')
    parser.add_argument('--strict-translate', action='store_true', 
                       help='Fail on unsupported operators')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None
    
    result = translate_file(input_path, output_path, strict=args.strict_translate)
    
    # Print warnings
    if result.warnings:
        print(f"\n⚠️  {len(result.warnings)} warning(s):", file=sys.stderr)
        for warning in result.warnings:
            print(f"  [{warning.rule_id}] {warning.field}: {warning.message}", file=sys.stderr)
    
    # Print errors
    if result.errors:
        print(f"\n❌ {len(result.errors)} error(s):", file=sys.stderr)
        for error in result.errors:
            print(f"  [{error.rule_id}] {error.field}: {error.message}", file=sys.stderr)
        sys.exit(2)
    
    # Print success
    if result.success:
        print(f"✅ Successfully translated {len(result.rules)} rule(s)")
        if output_path:
            print(f"📝 Output written to: {output_path}")
        else:
            print(json.dumps({'rules': result.rules}, indent=2))
        sys.exit(0)


if __name__ == '__main__':
    main()
