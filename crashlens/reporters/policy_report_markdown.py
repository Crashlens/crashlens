#!/usr/bin/env python3
"""
Policy Report Markdown Writer
Generates concise Markdown reports for policy violations
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..policy.engine import PolicyViolation


class PolicyReportMarkdown:
    """Generates concise Markdown reports for policy violations"""
    
    def __init__(self, violations: List[PolicyViolation], log_entries: List[Dict[str, Any]], 
                 strip_pii: bool = False, no_content: bool = False):
        self.violations = violations
        self.log_entries = log_entries
        self.strip_pii = strip_pii
        self.no_content = no_content
        
    def generate_report(self, output_path: Path) -> None:
        """Generate and write the markdown report"""
        
        # Calculate summary metrics
        summary = self._calculate_summary()
        
        # Generate report content
        content = self._generate_markdown_content(summary)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate summary metrics from violations and log entries"""
        
        # Count by severity
        by_severity = {}
        for violation in self.violations:
            severity = violation.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # Count by rule
        by_rule = {}
        rule_costs = {}
        for violation in self.violations:
            rule_id = violation.rule_id
            by_rule[rule_id] = by_rule.get(rule_id, 0) + 1
            
            # Extract cost if available
            cost = violation.log_entry.get('cost', 0.0)
            if rule_id not in rule_costs:
                rule_costs[rule_id] = 0.0
            rule_costs[rule_id] += cost
        
        # Calculate total spend and potential savings
        total_spend = sum((entry.get('cost') or 0.0) for entry in self.log_entries)
        violation_cost = sum((v.log_entry.get('cost') or 0.0) for v in self.violations)
        
        # Count by model
        model_costs = {}
        for entry in self.log_entries:
            model = entry.get('model', 'unknown')
            cost = entry.get('cost') or 0.0
            model_costs[model] = model_costs.get(model, 0.0) + cost
        
        # Count traces affected by violations
        affected_traces = set()
        for violation in self.violations:
            trace_id = violation.log_entry.get('trace_id', 'unknown')
            affected_traces.add(trace_id)
        
        return {
            'total_traces': len(set(entry.get('trace_id', 'unknown') for entry in self.log_entries)),
            'total_violations': len(self.violations),
            'by_severity': by_severity,
            'by_rule': by_rule,
            'rule_costs': rule_costs,
            'total_spend': total_spend,
            'violation_cost': violation_cost,
            'potential_savings': violation_cost * 0.6,  # Estimate 60% savings potential
            'model_costs': model_costs,
            'affected_traces': len(affected_traces)
        }
    
    def _generate_markdown_content(self, summary: Dict[str, Any]) -> str:
        """Generate the markdown report content"""
        
        now = datetime.utcnow().isoformat() + 'Z'
        
        content = [
            "# 🚨 CrashLens Policy Violations Report",
            f"📊 **Analysis Date:** {now}",
            "",
            "## Summary",
            f"- **Traces Analyzed:** {summary['total_traces']}",
            f"- **Policy Violations:** {summary['total_violations']}"
        ]
        
        # Add severity breakdown
        if summary['by_severity']:
            severity_parts = []
            for severity in ['critical', 'high', 'medium', 'low']:
                if severity in summary['by_severity']:
                    count = summary['by_severity'][severity]
                    severity_parts.append(f"{severity.title()}: {count}")
            
            if severity_parts:
                content.append(f"  ({' | '.join(severity_parts)})")
        
        content.extend([
            f"- **Estimated Spend:** ${summary['total_spend']:.2f}",
            f"- **Potential Savings:** ${summary['potential_savings']:.2f}",
            ""
        ])
        
        # Top rules by count
        content.append("## Top Rules (by count)")
        sorted_rules = sorted(summary['by_rule'].items(), key=lambda x: x[1], reverse=True)
        
        for i, (rule_id, count) in enumerate(sorted_rules[:10], 1):
            # Get severity from first violation of this rule
            rule_severity = 'medium'
            for violation in self.violations:
                if violation.rule_id == rule_id:
                    rule_severity = violation.severity.value
                    break
            
            cost = summary['rule_costs'].get(rule_id, 0.0)
            content.append(f"{i}) **{rule_id}** — {count} violations — severity={rule_severity} — est. cost: ${cost:.2f}")
        
        content.append("")
        
        # Cost by model
        if summary['model_costs']:
            content.append("## Cost by Model")
            sorted_models = sorted(summary['model_costs'].items(), key=lambda x: x[1], reverse=True)
            total_cost = sum(summary['model_costs'].values())
            
            for model, cost in sorted_models:
                if total_cost > 0:
                    percentage = (cost / total_cost) * 100
                    content.append(f"- **{model}**: ${cost:.2f} ({percentage:.0f}%)")
                else:
                    content.append(f"- **{model}**: ${cost:.2f}")
            
            content.append("")
        
        # Detector patterns (simplified)
        content.extend([
            "## Detectors (Essentials Only)",
            self._generate_detector_summary(),
            "",
            "## Next Actions",
            "- Tighten YAML policy (retry caps, model routing thresholds)",
            "- Enable CI fail on critical/high violations", 
            "- Re-run with `--detailed` and inspect `policy-violations-detailed.json`",
            "- Review trace patterns to optimize model routing",
            "- Implement suggested fixes to reduce policy violations",
            ""
        ])
        
        return '\n'.join(content)
    
    def _generate_detector_summary(self) -> str:
        """Generate simplified detector summary"""
        
        # Group violations by common patterns
        retry_violations = [v for v in self.violations if 'retry' in v.rule_id.lower()]
        fallback_violations = [v for v in self.violations if 'fallback' in v.rule_id.lower()]
        model_violations = [v for v in self.violations if any(x in v.rule_id.lower() for x in ['gpt4', 'model', 'overkill'])]
        
        lines = []
        
        if retry_violations:
            cost = sum((v.log_entry.get('cost') or 0.0) for v in retry_violations)
            traces = len(set(v.log_entry.get('trace_id', 'unknown') for v in retry_violations))
            lines.append(f"- 🔄 **excessive_retries** — {traces} traces — est. waste ${cost:.2f}")
            lines.append("  Fix: cap retries to 2, add backoff, short-circuit on repeated 429/5xx")
        
        if fallback_violations:
            cost = sum((v.log_entry.get('cost') or 0.0) for v in fallback_violations)
            traces = len(set(v.log_entry.get('trace_id', 'unknown') for v in fallback_violations))
            lines.append(f"- ⚡ **fallback_alert** — {traces} traces — est. waste ${cost:.2f}")
            lines.append("  Fix: avoid escalation to GPT-4 for low-token prompts; add routing guards")
        
        if model_violations:
            cost = sum((v.log_entry.get('cost') or 0.0) for v in model_violations)
            traces = len(set(v.log_entry.get('trace_id', 'unknown') for v in model_violations))
            lines.append(f"- 🤖 **gpt4_for_simple_tasks** — {traces} traces — est. waste ${cost:.2f}")
            lines.append("  Fix: downgrade to gpt-4o-mini / gpt-3.5 for <50+50 tokens")
        
        if not lines:
            lines.append("- ✅ No major detector patterns found")
        
        return '\n'.join(lines)
