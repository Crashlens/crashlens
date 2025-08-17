#!/usr/bin/env python3
"""
Policy Report JSON Writer
Generates detailed JSON reports for policy violations with trace grouping
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from collections import defaultdict
from ..policy.engine import PolicyViolation
from ..utils.pii_scrubber import PIIScrubber


class PolicyReportJSON:
    """Generates detailed JSON reports for policy violations"""
    
    def __init__(self, violations: List[PolicyViolation], log_entries: List[Dict[str, Any]], 
                 strip_pii: bool = False, no_content: bool = False):
        self.violations = violations
        self.log_entries = log_entries
        self.strip_pii = strip_pii
        self.no_content = no_content
        self.pii_scrubber = PIIScrubber() if strip_pii else None
        
    def generate_report(self, output_path: Path) -> None:
        """Generate and write the detailed JSON report"""
        
        # Build the detailed report structure
        report = self._build_detailed_report()
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    
    def _build_detailed_report(self) -> Dict[str, Any]:
        """Build the complete detailed report structure"""
        
        # Calculate summary
        summary = self._calculate_summary()
        
        # Group violations by rule
        violations_by_rule = self._group_violations_by_rule()
        
        return {
            "summary": summary,
            "violations_by_rule": violations_by_rule
        }
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary statistics"""
        
        # Count by severity
        by_severity = defaultdict(int)
        for violation in self.violations:
            by_severity[violation.severity.value] += 1
        
        # Calculate costs
        total_spend = sum((entry.get('cost') or 0.0) for entry in self.log_entries)
        violation_cost = sum((v.log_entry.get('cost') or 0.0) for v in self.violations)
        
        # Count unique traces
        total_traces = len(set(entry.get('traceId') or entry.get('trace_id', 'unknown') for entry in self.log_entries))
        
        return {
            "total_traces": total_traces,
            "total_violations": len(self.violations),
            "by_severity": dict(by_severity),
            "estimated_spend_usd": round(total_spend, 2),
            "estimated_savings_usd": round(violation_cost * 0.6, 2),  # 60% savings estimate
            "generated_at": datetime.utcnow().isoformat() + 'Z'
        }
    
    def _group_violations_by_rule(self) -> List[Dict[str, Any]]:
        """Group violations by rule and then by trace within each rule"""
        
        # Group by rule_id first
        by_rule = defaultdict(list)
        for violation in self.violations:
            by_rule[violation.rule_id].append(violation)
        
        result = []
        
        for rule_id, rule_violations in by_rule.items():
            # Get rule metadata from first violation
            first_violation = rule_violations[0]
            rule_severity = first_violation.severity.value
            rule_cost = sum((v.log_entry.get('cost') or 0.0) for v in rule_violations)
            
            # Group violations by trace_id within this rule
            traces = self._group_rule_violations_by_trace(rule_violations)
            
            rule_entry = {
                "rule_id": rule_id,
                "severity": rule_severity,
                "count": len(rule_violations),
                "estimated_cost_usd": round(rule_cost, 2),
                "traces": traces
            }
            
            result.append(rule_entry)
        
        # Sort by violation count (descending)
        result.sort(key=lambda x: x["count"], reverse=True)
        
        return result
    
    def _group_rule_violations_by_trace(self, rule_violations: List[PolicyViolation]) -> List[Dict[str, Any]]:
        """Group violations by trace and detect retry/fallback patterns"""
        
        # Group by trace_id
        by_trace = defaultdict(list)
        for violation in rule_violations:
            trace_id = violation.log_entry.get('traceId') or violation.log_entry.get('trace_id', 'unknown')
            by_trace[trace_id].append(violation)
        
        traces = []
        
        for trace_id, trace_violations in by_trace.items():
            # Sort violations by timestamp if available, handling None values
            trace_violations.sort(key=lambda v: v.log_entry.get('startTime') or v.log_entry.get('timestamp') or '')
            
            # Build trace entry
            trace_entry = self._build_trace_entry(trace_id, trace_violations)
            traces.append(trace_entry)
        
        # Sort traces by cost (descending), handling None values
        traces.sort(key=lambda x: x.get("cost_usd") or 0.0, reverse=True)
        
        return traces
    
    def _build_trace_entry(self, trace_id: str, trace_violations: List[PolicyViolation]) -> Dict[str, Any]:
        """Build a trace entry with retry/fallback grouping"""
        
        # Get the primary log entry (first violation's entry)
        primary_entry = trace_violations[0].log_entry
        
        # Extract basic trace info
        trace_entry = {
            "trace_id": trace_id,
            "model": primary_entry.get('input', {}).get('model') or primary_entry.get('model', 'unknown'),
            "cost_usd": round(primary_entry.get('cost') or 0.0, 4),
            "prompt_tokens": primary_entry.get('usage', {}).get('prompt_tokens') or primary_entry.get('input_tokens', 0),
            "completion_tokens": primary_entry.get('usage', {}).get('completion_tokens') or primary_entry.get('output_tokens', 0),
        }
        
        # Detect and group retries
        retry_group = self._detect_retry_pattern(trace_violations)
        if retry_group:
            trace_entry["retry_group"] = retry_group
        
        # Detect fallback chain
        fallback_chain = self._detect_fallback_pattern(trace_violations)
        if fallback_chain:
            trace_entry["fallback_chain"] = fallback_chain
        
        # Add redaction info
        trace_entry["redactions"] = {
            "content_removed": self.no_content,
            "pii_removed": self.strip_pii
        }
        
        # Add violation details
        trace_entry["violations"] = []
        for violation in trace_violations:
            violation_entry = {
                "reason": violation.reason,
                "suggestion": violation.suggestion,
                "action": violation.action.value,
                "line_number": violation.line_number
            }
            
            # Add sanitized content if allowed
            if not self.no_content:
                log_entry = violation.log_entry.copy()
                
                # Apply PII scrubbing if enabled
                if self.strip_pii and self.pii_scrubber:
                    log_entry = self.pii_scrubber.scrub_record(log_entry)
                
                # Add relevant fields
                if 'input' in log_entry:
                    violation_entry['input'] = log_entry['input']
                if 'output' in log_entry:
                    violation_entry['output'] = log_entry['output']
            
            trace_entry["violations"].append(violation_entry)
        
        return trace_entry
    
    def _detect_retry_pattern(self, trace_violations: List[PolicyViolation]) -> Optional[List[Dict[str, Any]]]:
        """Detect retry patterns in trace violations"""
        
        if len(trace_violations) < 2:
            return None
        
        # Look for multiple entries with similar inputs/timestamps
        retry_group = []
        
        for i, violation in enumerate(trace_violations):
            entry = violation.log_entry
            
            retry_attempt = {
                "attempt": i,
                "timestamp": entry.get('timestamp', ''),
                "status": "success" if entry.get('error') is None else "error"
            }
            
            if entry.get('error'):
                retry_attempt["error_code"] = str(entry.get('error', 'unknown'))
            
            # Estimate backoff time from timestamp differences
            if i > 0 and 'timestamp' in entry:
                prev_entry = trace_violations[i-1].log_entry
                if 'timestamp' in prev_entry:
                    # Simple timestamp diff calculation (would need proper parsing in real implementation)
                    retry_attempt["backoff_ms"] = 1000 * (i + 1)  # Placeholder calculation
            else:
                retry_attempt["backoff_ms"] = 0
            
            retry_group.append(retry_attempt)
        
        return retry_group if len(retry_group) > 1 else None
    
    def _detect_fallback_pattern(self, trace_violations: List[PolicyViolation]) -> Optional[List[str]]:
        """Detect fallback chains in trace violations"""
        
        # Extract models used in sequence
        models = []
        for violation in trace_violations:
            model = violation.log_entry.get('model', 'unknown')
            if model not in models:
                models.append(model)
        
        # Return if there's a model progression (fallback)
        return models if len(models) > 1 else None
