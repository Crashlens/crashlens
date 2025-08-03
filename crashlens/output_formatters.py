"""
Enhanced output formatters for CrashLens CI integration.
Provides clean, truncated output perfect for CI environments.
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class CIOutputFormatter:
    """CI-optimized output formatter with artifact export support."""
    
    @staticmethod
    def format_github_summary(
        detections: List[Dict[str, Any]], 
        policy_violations: Optional[List[Any]] = None,
        traces: Optional[Dict[str, Any]] = None,
        max_lines: int = 50
    ) -> str:
        """
        Format results for GitHub Actions with clean, truncated output.
        
        Args:
            detections: List of detection results
            policy_violations: List of policy violations
            traces: Trace data for context
            max_lines: Maximum lines to output (prevents CI log overflow)
            
        Returns:
            Formatted GitHub-compatible output
        """
        lines = []
        
        # Header
        lines.append("# 🔍 CrashLens Analysis Report")
        lines.append("")
        
        # Policy Violations Section
        if policy_violations:
            lines.append("## 🚨 Policy Violations")
            lines.append(f"Found {len(policy_violations)} violation(s):")
            lines.append("")
            
            for i, violation in enumerate(policy_violations[:10]):  # Limit to first 10
                severity_emoji = {
                    'low': '🟡',
                    'medium': '🟠', 
                    'high': '🔴',
                    'critical': '⚫'
                }.get(violation.severity.value if hasattr(violation, 'severity') else 'medium', '🟠')
                
                lines.append(f"{severity_emoji} **{violation.rule_id}** (Line {violation.line_number})")
                lines.append(f"   {violation.reason}")
                lines.append(f"   💡 {violation.suggestion}")
                lines.append("")
                
            if len(policy_violations) > 10:
                lines.append(f"... and {len(policy_violations) - 10} more violations")
                lines.append("")
        else:
            lines.append("## ✅ Policy Compliance")
            lines.append("No policy violations found")
            lines.append("")
        
        # Waste Pattern Detection Section
        if detections:
            lines.append("## 💸 Waste Pattern Detection")
            lines.append(f"Found {len(detections)} pattern(s):")
            lines.append("")
            
            for detection in detections[:5]:  # Limit to first 5
                waste_cost = detection.get('waste_cost', 0)
                lines.append(f"🔹 **{detection.get('type', 'Unknown')}**")
                lines.append(f"   Cost Impact: ${waste_cost:.4f}")
                lines.append(f"   {detection.get('description', 'No description')}")
                lines.append("")
                
            if len(detections) > 5:
                lines.append(f"... and {len(detections) - 5} more patterns")
                lines.append("")
        else:
            lines.append("## 🎉 Waste Pattern Detection")
            lines.append("No waste patterns detected")
            lines.append("")
        
        # Summary Footer
        lines.append("---")
        lines.append("📊 **CrashLens** - Protecting your LLM budget since 2024")
        
        # Truncate if too long
        if len(lines) > max_lines:
            lines = lines[:max_lines-2]
            lines.append("...")
            lines.append("*(Output truncated for CI readability)*")
        
        return "\n".join(lines)
    
    @staticmethod
    def export_json_artifact(
        detections: List[Dict[str, Any]], 
        policy_violations: Optional[List[Any]] = None,
        output_file: Path = Path("crashlens-report.json")
    ) -> None:
        """
        Export comprehensive results as JSON artifact for CI systems.
        
        Args:
            detections: List of detection results
            policy_violations: List of policy violations  
            output_file: Path to write JSON report
        """
        report = {
            "timestamp": "2024-01-01T00:00:00Z",  # Would use datetime.utcnow()
            "summary": {
                "total_detections": len(detections),
                "total_policy_violations": len(policy_violations) if policy_violations else 0,
                "has_critical_issues": False
            },
            "policy_violations": [],
            "waste_patterns": [],
            "recommendations": []
        }
        
        # Process policy violations
        if policy_violations:
            for violation in policy_violations:
                report["policy_violations"].append({
                    "rule_id": violation.rule_id,
                    "line_number": violation.line_number,
                    "severity": violation.severity.value if hasattr(violation, 'severity') else 'medium',
                    "action": violation.action.value if hasattr(violation, 'action') else 'warn',
                    "reason": violation.reason,
                    "suggestion": violation.suggestion
                })
                
                if hasattr(violation, 'action') and violation.action.value in ['fail', 'block']:
                    report["summary"]["has_critical_issues"] = True
        
        # Process waste patterns
        for detection in detections:
            report["waste_patterns"].append({
                "type": detection.get('type'),
                "severity": detection.get('severity'),
                "description": detection.get('description'),
                "waste_cost": detection.get('waste_cost', 0),
                "trace_id": detection.get('trace_id')
            })
        
        # Generate recommendations
        if policy_violations:
            report["recommendations"].append(
                "Fix policy violations before merging to ensure compliance"
            )
        
        if detections:
            total_waste = sum(d.get('waste_cost', 0) for d in detections)
            if total_waste > 0.01:
                report["recommendations"].append(
                    f"Optimize patterns to save ${total_waste:.4f} in LLM costs"
                )
        
        if not policy_violations and not detections:
            report["recommendations"].append(
                "Great job! Your LLM usage looks efficient and compliant."
            )
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
    
    @staticmethod
    def format_progress_indicator(current: int, total: int, operation: str = "Processing") -> str:
        """
        Format a progress indicator for CI environments.
        
        Args:
            current: Current progress count
            total: Total items to process
            operation: Description of the operation
            
        Returns:
            Formatted progress string
        """
        if total == 0:
            return f"⏳ {operation}..."
        
        percentage = int((current / total) * 100)
        progress_bar = "█" * (percentage // 10) + "░" * (10 - percentage // 10)
        
        return f"⏳ {operation}: [{progress_bar}] {percentage}% ({current}/{total})"
    
    @staticmethod
    def format_summary_table(
        policy_violations: int = 0,
        waste_patterns: int = 0,
        total_cost_impact: float = 0.0,
        compliance_rate: float = 100.0
    ) -> str:
        """
        Format a summary table for CI output.
        
        Returns:
            Formatted markdown table
        """
        return f"""
| Metric | Value |
|--------|-------|
| Policy Violations | {policy_violations} |
| Waste Patterns | {waste_patterns} |
| Cost Impact | ${total_cost_impact:.4f} |
| Compliance Rate | {compliance_rate:.1f}% |
"""


# Backwards compatibility
GitHubOutputFormatter = CIOutputFormatter
