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
        # Guard rules.yaml format is simpler than policy-check format
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
        else:
            self.policy_engine = None
            self.detector_driver = None
    
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
        
        # Action mapping: guard -> policy-check
        action_map = {
            "error": "fail",
            "warn": "warn",
            "fail_ci": "fail",
        }
        
        # Severity mapping: guard -> policy-check
        severity_map = {
            "warn": "low",
            "error": "medium",
            "fatal": "critical",
        }
        
        for guard_rule in guard_rules:
            # Convert "if" conditions to "match" format
            match_conditions = {}
            if_block = guard_rule.get("if", {})
            
            for field, condition in if_block.items():
                if isinstance(condition, dict):
                    # Handle operator conditions like {">": 3}
                    for op, value in condition.items():
                        match_conditions[field] = f"{op}{value}"
                else:
                    # Direct equality
                    match_conditions[field] = condition
            
            policy_rule = {
                "id": guard_rule["id"],
                "description": guard_rule.get("description", ""),
                "match": match_conditions,
                "action": action_map.get(guard_rule.get("action", "error"), "fail"),
                "severity": severity_map.get(guard_rule.get("severity", "error"), "medium"),
                "suggestion": guard_rule.get("suggestion", "Review this violation"),
            }
            
            policy_rules.append(policy_rule)
        
        return policy_rules
    
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
                    example = {
                        "timestamp": entry.get("timestamp") or entry.get("startTime"),
                        "model": entry.get("model"),
                        "tokens": entry.get("tokens") or entry.get("usage", {}).get("prompt_tokens", 0),
                        "retry_count": entry.get("retry_count"),
                        "fallback_triggered": entry.get("fallback_triggered"),
                        "endpoint": entry.get("endpoint"),
                        "prompt": redact_text(entry.get("prompt", ""), strip_pii),
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
