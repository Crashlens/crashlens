import yaml
import re
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum



class PolicyAction(Enum):
    """Actions that can be taken when a policy rule is violated."""
    WARN = "warn"
    FAIL = "fail" 
    BLOCK = "block"


class PolicySeverity(Enum):
    """Severity levels for policy violations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PolicyViolation:
    """Represents a policy rule violation."""
    rule_id: str
    reason: str
    suggestion: str
    severity: PolicySeverity
    action: PolicyAction
    log_entry: Dict[str, Any]
    line_number: Optional[int] = None


class PolicyMatcher:
    """Handles matching operations for policy rules."""
    
    OPERATORS = {
        'not in': lambda a, b: a not in b,
        '!=': lambda a, b: a != b,
        '==': lambda a, b: a == b,
        '>=': lambda a, b: a is not None and b is not None and float(a) >= float(b),
        '<=': lambda a, b: a is not None and b is not None and float(a) <= float(b),
        '>': lambda a, b: a is not None and b is not None and float(a) > float(b),
        '<': lambda a, b: a is not None and b is not None and float(a) < float(b),
        'in': lambda a, b: a in b,
        'regex': lambda a, b: bool(re.match(b, str(a))),
        'contains': lambda a, b: b in str(a),
        'startswith': lambda a, b: str(a).startswith(b),
        'endswith': lambda a, b: str(a).endswith(b)
    }
    
    @classmethod
    def match_condition(cls, log_value: Any, rule_value: Any) -> bool:
        """
        Match a log value against a rule condition.
        
        Args:
            log_value: Value from the log entry
            rule_value: Expected value or condition from the rule
            
        Returns:
            True if the condition matches, False otherwise
        """
        if isinstance(rule_value, str) and any(op in rule_value for op in cls.OPERATORS):
            # Handle operator-based conditions like ">2", "!=gpt-4"
            for op_str, op_func in cls.OPERATORS.items():
                if rule_value.startswith(op_str):
                    try:
                        expected = rule_value[len(op_str):].strip()
                        # Handle special operators
                        if op_str in ['not in']:
                            # Parse the list from the string format "not in:['item1', 'item2']"
                            if ':' in expected:
                                list_str = expected.split(':', 1)[1]
                                import ast
                                expected = ast.literal_eval(list_str)
                        return op_func(log_value, expected)
                    except (ValueError, TypeError, SyntaxError) as e:
                        logging.warning(f"Policy match error: {e}")
                        return False
            return False  # No matching operator found
        
        # Handle list conditions (for 'in' operator)
        elif isinstance(rule_value, list):
            return log_value in rule_value
            
        # Handle direct equality
        else:
            return log_value == rule_value
    
    @classmethod
    def evaluate_match_block(cls, log_entry: Dict[str, Any], match_conditions: Dict[str, Any]) -> bool:
        """
        Evaluate all conditions in a match block against a log entry.
        
        Args:
            log_entry: The log entry to check
            match_conditions: Dictionary of field->condition mappings
            
        Returns:
            True if all conditions match (AND logic), False otherwise
        """
        for field_path, expected_value in match_conditions.items():
            # Support nested field access with dot notation
            log_value = cls._get_nested_value(log_entry, field_path)
            
            if log_value is None:
                return False  # Field doesn't exist
                
            if not cls.match_condition(log_value, expected_value):
                return False
                
        return True  # All conditions matched
    
    @staticmethod
    def _get_nested_value(data: Dict[str, Any], field_path: str) -> Any:
        """Get value from nested dictionary using dot notation (e.g., 'usage.prompt_tokens')."""
        keys = field_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
                
        return value


@dataclass
class PolicyRule:
    """Represents a single policy rule."""
    id: str
    match: Dict[str, Any]
    action: PolicyAction
    severity: PolicySeverity
    suggestion: str
    description: Optional[str] = None
    
    def evaluate(self, log_entry: Dict[str, Any], line_number: Optional[int] = None) -> Optional[PolicyViolation]:
        """
        Evaluate this rule against a log entry.
        
        Args:
            log_entry: The log entry to check
            line_number: Optional line number for better error reporting
            
        Returns:
            PolicyViolation if rule is violated, None otherwise
        """
        if PolicyMatcher.evaluate_match_block(log_entry, self.match):
            # Build human-readable reason
            conditions = []
            for field, value in self.match.items():
                actual_value = PolicyMatcher._get_nested_value(log_entry, field)
                conditions.append(f"{field}={actual_value} (rule: {value})")
            
            reason = " AND ".join(conditions)
            
            return PolicyViolation(
                rule_id=self.id,
                reason=reason,
                suggestion=self.suggestion,
                severity=self.severity,
                action=self.action,
                log_entry=log_entry,
                line_number=line_number
            )
        
        return None


class PolicyEngine:
    """Main policy enforcement engine."""
    
    def __init__(self, policy_file: Optional[Path] = None):
        self.rules: List[PolicyRule] = []
        self.logger = logging.getLogger(__name__)
        
        if policy_file:
            self.load_policy(policy_file)
    
    def load_policy(self, policy_file: Path) -> None:
        """
        Load policy rules from a YAML file.
        
        Args:
            policy_file: Path to the YAML policy file
        """
        try:
            with open(policy_file, 'r', encoding='utf-8') as f:
                policy_data = yaml.safe_load(f)
                
            if 'rules' not in policy_data:
                raise ValueError("Policy file must contain a 'rules' section")
                
            self.rules = []
            for rule_data in policy_data['rules']:
                try:
                    rule = PolicyRule(
                        id=rule_data['id'],
                        match=rule_data['match'],
                        action=PolicyAction(rule_data['action']),
                        severity=PolicySeverity(rule_data['severity']),
                        suggestion=rule_data['suggestion'],
                        description=rule_data.get('description')
                    )
                    self.rules.append(rule)
                except (KeyError, ValueError) as e:
                    self.logger.error(f"Invalid rule '{rule_data.get('id', 'unknown')}': {e}")
                    
            self.logger.info(f"Loaded {len(self.rules)} policy rules from {policy_file}")
            
        except Exception as e:
            raise ValueError(f"Failed to load policy file {policy_file}: {e}")
    
    def evaluate_log_entry(self, log_entry: Dict[str, Any], line_number: Optional[int] = None) -> Tuple[List[PolicyViolation], List[str]]:
        """
        Evaluate a single log entry against all policy rules.
        
        Args:
            log_entry: The log entry to check
            line_number: Optional line number for better error reporting
            
        Returns:
            Tuple of (violations, skipped_rule_ids)
        """
        violations = []
        skipped_rules = []
        
        for rule in self.rules:
            # Evaluate rule normally
            violation = rule.evaluate(log_entry, line_number)
            if violation:
                violations.append(violation)
                
        return violations, skipped_rules
    
    def evaluate_logs(self, log_entries: List[Dict[str, Any]]) -> Tuple[List[PolicyViolation], List[str]]:
        """
        Evaluate multiple log entries against all policy rules.
        
        Args:
            log_entries: List of log entries to check
            
        Returns:
            Tuple of (all_violations, all_skipped_rule_ids)
        """
        all_violations = []
        all_skipped_rules = set()
        
        for line_number, log_entry in enumerate(log_entries, 1):
            violations, skipped_rules = self.evaluate_log_entry(log_entry, line_number)
            all_violations.extend(violations)
            all_skipped_rules.update(skipped_rules)
            
        return all_violations, list(all_skipped_rules)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of loaded policy rules."""
        return {
            'total_rules': len(self.rules),
            'active_rules': len(self.rules),
            'rules_by_severity': {
                severity.value: len([r for r in self.rules if r.severity == severity])
                for severity in PolicySeverity
            },
            'rules_by_action': {
                action.value: len([r for r in self.rules if r.action == action])
                for action in PolicyAction
            }
        }
