"""
Guard-PolicyEngine Integration Adapter

This module provides the integration layer between crashlens guard's legacy
rule evaluation and the unified PolicyEngine.

The unified engine is always enabled in v1.0+.
"""

import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from crashlens.utils.feature_flags import is_unified_enabled
from crashlens.utils.rule_translator import RuleTranslator
from crashlens.policy.engine import PolicyEngine, PolicyViolation
from crashlens.io.ingest import LogIterator
from crashlens.detectors.driver import DetectorDriver, DetectorMode


class GuardPolicyEngineAdapter:
    """
    Adapter that integrates PolicyEngine into guard while maintaining
    backwards compatibility with legacy rule format.
    
    Unified Engine Behavior:
    - Uses LogIterator for streaming
    - Translates rules.yaml to PolicyEngine format
    - Optionally runs DetectorDriver for inline detection
    - Uses PolicyEngine for rule evaluation
    """
    
    def __init__(
        self,
        rules_yaml_path: Path,
        detector_mode: DetectorMode = "none",
        detector_config: Optional[Dict[str, Any]] = None,
        suppress_ids: Optional[set] = None,
        verbose: bool = False,
    ):
        """Initialize adapter.
        
        Args:
            rules_yaml_path: Path to rules.yaml file
            detector_mode: Detector mode ('none', 'precomputed', 'inline')
            detector_config: Configuration for inline detectors
            suppress_ids: Set of rule IDs to suppress
            verbose: Enable verbose logging
        """
        self.rules_yaml_path = rules_yaml_path
        self.detector_mode = detector_mode
        self.detector_config = detector_config or {}
        self.suppress_ids = suppress_ids or set()
        self.verbose = verbose
        
        # Unified engine is always enabled
        self.use_unified = True
        
        if self.verbose:
            print("🔧 Unified engine enabled")
        
        # Load guard's rules.yaml and convert to PolicyEngine format
        # Guard rules.yaml format is simpler than guard format
        # We need to convert it directly
        with open(self.rules_yaml_path, 'r') as f:
            import yaml
            guard_rules = yaml.safe_load(f)
        
        policy_rules = self._convert_guard_rules_to_policy_format(guard_rules.get('rules', []))
        
        # Create temporary policy file for PolicyEngine
        policy_dict = {
            "version": 1,
            "rules": policy_rules
        }
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(policy_dict, f)
            temp_policy_path = Path(f.name)
        
        try:
            self.policy_engine = PolicyEngine(policy_file=temp_policy_path)
        finally:
            # Clean up temp file
            temp_policy_path.unlink(missing_ok=True)
        
        # Initialize detector driver if needed
        if detector_mode != "none":
            self.detector_driver = DetectorDriver(
                mode=detector_mode,
                detector_config=detector_config,
                verbose=verbose,
            )
        else:
            self.detector_driver = None
        
        if self.verbose:
            print(f"   Loaded {len(policy_rules)} rules")
            print(f"   Detector mode: {detector_mode}")
    
    def _convert_guard_rules_to_policy_format(self, guard_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert guard rules.yaml format to PolicyEngine format.
        
        Guard format:
            {
                "id": "TEST001",
                "description": "...",
                "if": {"field": {">": value}},
                "action": "error",
                "severity": "error"
            }
        
        Supports boolean logic:
            {
                "if": {
                    "and": [{"field1": value1}, {"field2": value2}]  # All must match
                    "or": [{"field1": value1}, {"field2": value2}]   # At least one must match
                    "not": {"field": value}                          # Inverts condition
                }
            }
        
        PolicyEngine format:
            {
                "id": "TEST001",
                "description": "...",
                "match": {"field": ">value"},  # Operator prefix format
                "action": "fail",  # fail/warn/block
                "severity": "high",  # low/medium/high/critical
                "suggestion": "..."
            }
        """
        policy_rules = []
        
        # Action mapping: guard -> guard
        action_map = {
            "error": "fail",
            "warn": "warn",
            "fail_ci": "fail",
        }
        
        # Severity mapping: guard -> guard
        severity_map = {
            "warn": "low",
            "error": "medium",
            "fatal": "critical",
        }
        
        for guard_rule in guard_rules:
            if_block = guard_rule.get("if", {})
            
            # Handle boolean logic by expanding into multiple rules
            expanded_rules = self._expand_boolean_logic(
                rule_id=guard_rule["id"],
                description=guard_rule.get("description", ""),
                if_block=if_block,
                action=action_map.get(guard_rule.get("action", "error"), "fail"),
                severity=severity_map.get(guard_rule.get("severity", "error"), "medium"),
                suggestion=guard_rule.get("suggestion", "Review this violation")
            )
            
            policy_rules.extend(expanded_rules)
        
        return policy_rules
    
    def _expand_boolean_logic(
        self,
        rule_id: str,
        description: str,
        if_block: Dict[str, Any],
        action: str,
        severity: str,
        suggestion: str
    ) -> List[Dict[str, Any]]:
        """Expand boolean logic (AND/OR/NOT) into multiple PolicyEngine rules.
        
        Since PolicyEngine only supports flat AND logic in match blocks,
        we need to expand OR and NOT into separate rules.
        
        Args:
            rule_id: Base rule ID
            description: Rule description
            if_block: The "if" conditions (may contain and/or/not)
            action: Policy action
            severity: Policy severity
            suggestion: Suggestion text
            
        Returns:
            List of policy rules (may be multiple for OR logic)
        """
        # Check for boolean operators
        if "and" in if_block:
            # AND: Flatten all conditions into single match block
            return [self._create_policy_rule(
                rule_id=rule_id,
                description=description,
                conditions=self._flatten_and_conditions(if_block["and"]),
                action=action,
                severity=severity,
                suggestion=suggestion
            )]
        
        elif "or" in if_block:
            # OR: Create separate rule for each condition
            # We'll use the same rule ID but add suffix for tracking
            or_conditions = if_block["or"]
            rules = []
            for idx, condition in enumerate(or_conditions):
                rules.append(self._create_policy_rule(
                    rule_id=f"{rule_id}_or{idx}" if len(or_conditions) > 1 else rule_id,
                    description=f"{description} (variant {idx+1})" if len(or_conditions) > 1 else description,
                    conditions=self._convert_conditions(condition),
                    action=action,
                    severity=severity,
                    suggestion=suggestion
                ))
            return rules
        
        elif "not" in if_block:
            # NOT: Invert the conditions using != operator or negative logic
            not_condition = if_block["not"]
            inverted = self._invert_conditions(not_condition)
            
            if inverted:
                return [self._create_policy_rule(
                    rule_id=rule_id,
                    description=description,
                    conditions=inverted,
                    action=action,
                    severity=severity,
                    suggestion=suggestion
                )]
            else:
                print(f"⚠️  Warning: Rule {rule_id} uses 'not' logic that cannot be inverted. Skipping.")
                return []
        
        else:
            # Simple conditions (no boolean logic)
            return [self._create_policy_rule(
                rule_id=rule_id,
                description=description,
                conditions=self._convert_conditions(if_block),
                action=action,
                severity=severity,
                suggestion=suggestion
            )]
    
    def _flatten_and_conditions(self, and_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Flatten a list of AND conditions into a single match block."""
        flattened = {}
        for condition in and_list:
            flattened.update(self._convert_conditions(condition))
        return flattened
    
    def _invert_conditions(self, conditions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Invert conditions for NOT logic.
        
        Converts conditions to their negation:
        - Direct equality: field: "value" → field: "!=value"
        - Operators: {">": 5} → {"<=": 5}, {"==": true} → {"==": false}
        
        Args:
            conditions: Conditions to invert
            
        Returns:
            Inverted conditions dict, or None if inversion is not possible
        """
        inverted = {}
        
        for field, condition in conditions.items():
            if isinstance(condition, dict):
                # Handle operator conditions
                for op, value in condition.items():
                    # Invert the operator
                    inverse_op = self._invert_operator(op)
                    if inverse_op is None:
                        return None  # Cannot invert
                    
                    if isinstance(value, bool):
                        # For booleans, invert the value instead of operator
                        if op == "==":
                            inverted[field] = not value
                        else:
                            return None  # Cannot invert non-equality boolean ops
                    elif inverse_op == "!=":
                        # Use != operator directly
                        inverted[field] = f"{inverse_op}{value}"
                    elif inverse_op == "regex":
                        # Cannot invert regex
                        return None
                    else:
                        # Inverted numeric operator
                        inverted[field] = f"{inverse_op}{value}"
            else:
                # Direct equality - use != operator
                if isinstance(condition, bool):
                    inverted[field] = not condition
                else:
                    inverted[field] = f"!={condition}"
        
        return inverted
    
    def _invert_operator(self, op: str) -> Optional[str]:
        """Invert a comparison operator.
        
        Args:
            op: Operator to invert (e.g., ">", "==")
            
        Returns:
            Inverted operator, or None if cannot be inverted
        """
        operator_inversions = {
            ">": "<=",
            ">=": "<",
            "<": ">=",
            "<=": ">",
            "==": "!=",
            "!=": "==",
        }
        return operator_inversions.get(op)
    
    def _convert_conditions(self, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Convert guard condition format to PolicyEngine match format.
        
        Args:
            conditions: Guard conditions (may be nested)
            
        Returns:
            Flat dictionary for PolicyEngine match block
        """
        match_conditions = {}
        
        for field, condition in conditions.items():
            if isinstance(condition, dict):
                # Handle operator conditions like {">": 3} or {"==": true}
                for op, value in condition.items():
                    # Special handling for boolean comparisons
                    if isinstance(value, bool):
                        # For booleans, pass the value directly (not as string)
                        if op == "==":
                            match_conditions[field] = value
                        else:
                            # Other operators with booleans - convert to string
                            match_conditions[field] = f"{op}{value}"
                    elif op == "regex":
                        # Regex operator needs space after colon
                        match_conditions[field] = f"{op}: {value}"
                    else:
                        # Standard operators (>, <, >=, etc.)
                        match_conditions[field] = f"{op}{value}"
            else:
                # Direct equality
                match_conditions[field] = condition
        
        return match_conditions
    
    def _create_policy_rule(
        self,
        rule_id: str,
        description: str,
        conditions: Dict[str, Any],
        action: str,
        severity: str,
        suggestion: str
    ) -> Dict[str, Any]:
        """Create a PolicyEngine rule dictionary.
        
        Args:
            rule_id: Unique rule identifier
            description: Human-readable description
            conditions: Match conditions (already converted to PolicyEngine format)
            action: Policy action (fail/warn/block)
            severity: Severity level (low/medium/high/critical)
            suggestion: Suggestion text
            
        Returns:
            PolicyEngine rule dictionary
        """
        return {
            "id": rule_id,
            "description": description,
            "match": conditions,
            "action": action,
            "severity": severity,
            "suggestion": suggestion,
        }
    
    def is_enabled(self) -> bool:
        """Check if unified engine is enabled."""
        return self.use_unified
    
    def process_logs(
        self,
        log_paths: List[Path],
        model_pricing: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, List[PolicyViolation]], Dict[str, Any]]:
        """Process logs using unified engine.
        
        Args:
            log_paths: List of log file paths to process
            model_pricing: Optional model pricing data for cost calculations
        
        Returns:
            Tuple of:
            - violations_by_rule: Dict[rule_id, List[PolicyViolation]]
            - metrics: Dict with processing metrics
        """
        if not self.use_unified or self.policy_engine is None:
            # Return empty results - guard will use legacy path
            return {}, {}
        
        violations_by_rule: Dict[str, List[PolicyViolation]] = {}
        total_records = 0
        total_batches = 0
        detector_time_ms = 0.0
        
        for log_path in log_paths:
            if self.verbose:
                print(f"📖 Processing {log_path.name} with unified engine...")
            
            # Use LogIterator for streaming
            iterator = LogIterator(
                log_path,
                langfuse_schema=False,  # Guard doesn't require Langfuse validation
                verbose=self.verbose,
            )
            
            for batch in iterator:
                total_batches += 1
                
                # Run detectors if enabled
                if self.detector_driver:
                    enriched_batch = self.detector_driver.run_detectors_on_batch(
                        batch,
                        model_pricing=model_pricing,
                    )
                    detector_metrics = self.detector_driver.get_metrics()
                    detector_time_ms += detector_metrics.detector_time_ms
                else:
                    enriched_batch = batch
                
                # Evaluate with PolicyEngine
                for entry in enriched_batch:
                    total_records += 1
                    violations, skipped_rules = self.policy_engine.evaluate_log_entry(
                        entry,
                        line_number=total_records,
                    )
                    
                    for violation in violations:
                        # Skip suppressed rules
                        if violation.rule_id in self.suppress_ids:
                            continue
                        
                        if violation.rule_id not in violations_by_rule:
                            violations_by_rule[violation.rule_id] = []
                        violations_by_rule[violation.rule_id].append(violation)
        
        # Compile metrics
        metrics = {
            "total_records": total_records,
            "total_batches": total_batches,
            "detector_time_ms": detector_time_ms,
            "used_unified_engine": True,
        }
        
        if self.verbose:
            print(f"✅ Processed {total_records} records in {total_batches} batches")
            if detector_time_ms > 0:
                print(f"   Detector time: {detector_time_ms:.2f}ms")
        
        return violations_by_rule, metrics
    
    def convert_violations_to_legacy_format(
        self,
        violations_by_rule: Dict[str, List[PolicyViolation]],
        strip_pii: bool = False,
        no_content: bool = False,
        max_examples: int = 5,
    ) -> Dict[str, Dict[str, Any]]:
        """Convert PolicyEngine violations to legacy guard results format.
        
        Args:
            violations_by_rule: Violations grouped by rule ID
            strip_pii: Whether to strip PII from examples
            no_content: Whether to exclude content examples
            max_examples: Maximum examples per rule
        
        Returns:
            Dict in legacy format: {rule_id: {"count": int, "examples": [], "severity": str}}
        """
        from crashlens.guard import redact_text  # Import from guard for PII stripping
        
        legacy_results = {}
        
        for rule_id, violations in violations_by_rule.items():
            # Map PolicySeverity to legacy severity strings
            severity_map = {
                "LOW": "warn",
                "MEDIUM": "error",
                "HIGH": "error",
                "CRITICAL": "fatal",
            }
            
            # Get severity from first violation
            policy_severity = violations[0].severity.name if violations else "MEDIUM"
            legacy_severity = severity_map.get(policy_severity, "error")
            
            examples = []
            if not no_content:
                for violation in violations[:max_examples]:
                    entry = violation.log_entry
                    # Extract prompt from either flat format or Langfuse nested format
                    prompt = entry.get("prompt") or entry.get("input", {}).get("prompt", "")
                    example = {
                        "timestamp": entry.get("timestamp") or entry.get("startTime"),
                        "model": entry.get("model") or entry.get("input", {}).get("model"),
                        "tokens": entry.get("tokens") or entry.get("usage", {}).get("prompt_tokens", 0),
                        "retry_count": entry.get("retry_count") or entry.get("metadata", {}).get("retry_count"),
                        "fallback_triggered": entry.get("fallback_triggered") or entry.get("metadata", {}).get("fallback_triggered"),
                        "endpoint": entry.get("endpoint") or entry.get("metadata", {}).get("endpoint"),
                        "prompt": redact_text(prompt, strip_pii),
                        "reason": violation.reason,
                    }
                    examples.append(example)
            
            legacy_results[rule_id] = {
                "count": len(violations),
                "examples": examples,
                "severity": legacy_severity,
                "description": violations[0].reason if violations else "",
                "suggestion": violations[0].suggestion if violations else "",
            }
        
        return legacy_results


def should_use_unified_engine() -> bool:
    """Check if unified engine should be used.
    
    Returns:
        Always True (unified engine is always enabled in v1.0+)
    """
    return True
