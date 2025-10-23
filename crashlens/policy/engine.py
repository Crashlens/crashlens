import yaml
import re
import logging
import time
from collections import defaultdict
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from crashlens.observability import get_metrics



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
        self.global_config: Dict[str, Any] = {}
        self.violation_counts: Dict[str, int] = {}
        self.traces_flagged: Set[str] = set()
        
        # Benchmark stats tracking (constant memory: ~5 floats per rule)
        self._collect_stats = False  # Flag to enable stats collection
        self._record_metrics = False  # Flag for metrics recording
        self._rule_stats = defaultdict(lambda: {
            'count': 0,
            'sum': 0.0,
            'max': 0.0,
            'min': float('inf')
        })
        
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
            
            # Load global configuration
            self.global_config = policy_data.get('global', {})
            max_violations_per_rule = self.global_config.get('max_violations_per_rule', 100)
            
            # Initialize violation counters
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
                    # Initialize violation counter for this rule
                    self.violation_counts[rule.id] = 0
                except (KeyError, ValueError) as e:
                    self.logger.error(f"Invalid rule '{rule_data.get('id', 'unknown')}': {e}")
                    
            self.logger.info(f"Loaded {len(self.rules)} policy rules from {policy_file}")
            self.logger.info(f"Global config: max_violations_per_rule={max_violations_per_rule}")
            
        except Exception as e:
            raise ValueError(f"Failed to load policy file {policy_file}: {e}")
    
    def enable_stats_collection(self):
        """Enable performance stats collection for benchmarking.
        
        This is used for performance testing only and will be replaced
        with full metrics implementation later.
        """
        self._collect_stats = True
    
    def enable_metrics_recording(self):
        """Enable Prometheus metrics recording.
        
        This should be called after initialize_metrics() in the CLI.
        Works alongside stats collection for latency tracking.
        """
        self._record_metrics = get_metrics() is not None
        if self._record_metrics:
            self.enable_stats_collection()  # Need stats for latency tracking
    
    def get_stats(self):
        """Get collected stats (for benchmark validation)."""
        return dict(self._rule_stats)
    
    def print_stats_summary(self):
        """Print stats summary for benchmark validation."""
        if not self._rule_stats:
            print("No stats collected (stats collection not enabled)")
            return
        
        print("\n=== Rule Evaluation Performance Stats ===")
        for rule_name, stats in sorted(self._rule_stats.items()):
            if stats['count'] > 0:
                avg = stats['sum'] / stats['count']
                print(f"{rule_name}:")
                print(f"  Count: {stats['count']}")
                print(f"  Avg:   {avg*1000:.3f}ms")
                print(f"  Min:   {stats['min']*1000:.3f}ms")
                print(f"  Max:   {stats['max']*1000:.3f}ms")
        print("=" * 40)
    
    def evaluate_log_entry(self, log_entry: Dict[str, Any], line_number: Optional[int] = None) -> Tuple[List[PolicyViolation], List[str]]:
        """
        Evaluate a single log entry against all policy rules with lazy evaluation.
        
        Args:
            log_entry: The log entry to check
            line_number: Optional line number for better error reporting
            
        Returns:
            Tuple of (violations, skipped_rule_ids)
        """
        violations = []
        skipped_rules = []
        
        # Get trace ID for early exit tracking
        trace_id = log_entry.get('traceId', f'line_{line_number}')
        
        # Check if this trace is already flagged (early exit)
        if trace_id in self.traces_flagged:
            self.logger.debug(f"Trace {trace_id} already flagged, skipping additional rule checks")
            return violations, skipped_rules
        
        max_violations_per_rule = self.global_config.get('max_violations_per_rule', 100)
        
        for rule in self.rules:
            # Check if rule has reached its violation limit
            if self.violation_counts[rule.id] >= max_violations_per_rule:
                skipped_rules.append(rule.id)
                continue
            
            # Benchmark timing collection (minimal overhead)
            if self._collect_stats:
                start_time = time.perf_counter()
            
            # Evaluate rule
            violation = rule.evaluate(log_entry, line_number)
            
            # Update stats after evaluation
            if self._collect_stats:
                elapsed = time.perf_counter() - start_time
                stats = self._rule_stats[rule.id]
                stats['count'] += 1
                stats['sum'] += elapsed
                if elapsed > stats['max']:
                    stats['max'] = elapsed
                if elapsed < stats['min']:
                    stats['min'] = elapsed
            
            # Record metrics if enabled
            if self._record_metrics and violation:
                metrics = get_metrics()
                if metrics:
                    severity = rule.severity.value
                    metrics.record_rule_hit(
                        rule_name=rule.id,
                        severity=severity,
                        mode='policy-check'
                    )
                    metrics.record_violation(severity=severity)
            
            if violation:
                violations.append(violation)
                self.violation_counts[rule.id] += 1
                
                # Mark trace as flagged for early exit on future evaluations
                self.traces_flagged.add(trace_id)
                
                # Early exit: once a trace is flagged, don't check remaining rules
                self.logger.debug(f"Trace {trace_id} flagged by rule {rule.id}, skipping remaining rules")
                break
                
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
    
    def flush_metrics(self):
        """Flush metrics at end of scan.
        
        Pushes latency stats to Prometheus gauges.
        Should be called after evaluate_logs() completes.
        """
        metrics = get_metrics()
        if not metrics or not self._rule_stats:
            return
        
        # Update latency gauges from stats
        for rule_name, stats in self._rule_stats.items():
            if stats['count'] > 0:
                avg_latency = stats['sum'] / stats['count']
                max_latency = stats['max']
                
                metrics.update_decision_latency(
                    rule_name=rule_name,
                    avg_seconds=avg_latency,
                    max_seconds=max_latency
                )
    
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
            },
            'violation_counts': self.violation_counts.copy(),
            'traces_flagged': len(self.traces_flagged),
            'max_violations_per_rule': self.global_config.get('max_violations_per_rule', 100)
        }
    
    def reset_counters(self) -> None:
        """Reset violation counters and flagged traces for reuse."""
        self.violation_counts = {rule.id: 0 for rule in self.rules}
        self.traces_flagged.clear()
        self.logger.debug("Reset violation counters and flagged traces")
