#!/usr/bin/env python3
"""
CrashLens Cost Savings Report Generator
Generates ROI reports showing cost savings potential per policy rule
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CostSavingsReport:
    """Cost savings analysis for policy violations"""
    rule_id: str
    violation_count: int
    current_cost: float
    potential_savings: float
    efficiency_improvement: float
    suggested_actions: List[str]

class ROICalculator:
    """Calculate return on investment for policy enforcement"""
    
    def __init__(self, pricing_config: Dict[str, Any]):
        self.pricing_config = pricing_config
        
    def calculate_savings_by_rule(self, violations: List[Dict], log_entries: List[Dict]) -> List[CostSavingsReport]:
        """Calculate potential cost savings for each policy rule"""
        savings_by_rule = {}
        
        for violation in violations:
            rule_id = violation.get('rule_id', 'unknown')
            log_entry = violation.get('log_entry', {})
            
            if rule_id not in savings_by_rule:
                savings_by_rule[rule_id] = {
                    'violations': [],
                    'current_cost': 0.0,
                    'potential_savings': 0.0
                }
            
            savings_by_rule[rule_id]['violations'].append(violation)
            savings_by_rule[rule_id]['current_cost'] += log_entry.get('cost', 0.0)
            
            # Calculate potential savings based on rule type
            savings = self._calculate_rule_savings(rule_id, log_entry)
            savings_by_rule[rule_id]['potential_savings'] += savings
        
        # Convert to report objects
        reports = []
        for rule_id, data in savings_by_rule.items():
            efficiency_improvement = 0.0
            if data['current_cost'] > 0:
                efficiency_improvement = (data['potential_savings'] / data['current_cost']) * 100
                
            report = CostSavingsReport(
                rule_id=rule_id,
                violation_count=len(data['violations']),
                current_cost=data['current_cost'],
                potential_savings=data['potential_savings'],
                efficiency_improvement=efficiency_improvement,
                suggested_actions=self._get_suggested_actions(rule_id)
            )
            reports.append(report)
        
        return sorted(reports, key=lambda x: x.potential_savings, reverse=True)
    
    def _calculate_rule_savings(self, rule_id: str, log_entry: Dict) -> float:
        """Calculate potential savings for a specific rule violation"""
        if rule_id == 'retry_loop_detection':
            # Assume 70% of retries could be avoided with better logic
            retry_count = log_entry.get('retry_count', 0)
            cost_per_request = log_entry.get('cost', 0.0)
            return cost_per_request * retry_count * 0.7
            
        elif rule_id == 'overkill_expensive_model':
            # Savings from using cheaper model (e.g., gpt-3.5-turbo vs gpt-4)
            current_cost = log_entry.get('cost', 0.0)
            model = log_entry.get('model', '')
            if 'gpt-4' in model.lower():
                return current_cost * 0.85  # 85% savings switching to gpt-3.5-turbo
            elif 'claude-3-opus' in model.lower():
                return current_cost * 0.80  # 80% savings switching to cheaper claude
            
        elif rule_id == 'high_cost_request':
            # Assume 30% cost reduction through optimization
            return log_entry.get('cost', 0.0) * 0.3
            
        elif rule_id == 'excessive_tokens':
            # Assume 40% token reduction through better prompts
            return log_entry.get('cost', 0.0) * 0.4
            
        return 0.0
    
    def _get_suggested_actions(self, rule_id: str) -> List[str]:
        """Get actionable suggestions for each rule type"""
        suggestions = {
            'retry_loop_detection': [
                'Implement exponential backoff',
                'Add circuit breaker pattern',
                'Review error handling logic',
                'Set maximum retry limits'
            ],
            'overkill_expensive_model': [
                'Use gpt-3.5-turbo for simple tasks',
                'Implement model routing logic',
                'Add complexity detection',
                'Create task classification system'
            ],
            'high_cost_request': [
                'Optimize prompt length',
                'Use more efficient models',
                'Implement request caching',
                'Review model selection criteria'
            ],
            'excessive_tokens': [
                'Break large requests into chunks',
                'Use summarization techniques',
                'Implement token budgets',
                'Optimize prompt engineering'
            ]
        }
        return suggestions.get(rule_id, ['Review and optimize usage patterns'])

def generate_roi_report(log_file: Path, policy_file: Path, output_format: str = 'markdown') -> str:
    """Generate a comprehensive ROI report"""
    from ..policy.engine import PolicyEngine
    import json
    
    try:
        # Load policy and logs
        engine = PolicyEngine(policy_file)
        
        log_entries = []
        with open(log_file, 'r') as f:
            for line in f:
                if line.strip():
                    log_entries.append(json.loads(line))
        
        # Evaluate violations
        violations, _ = engine.evaluate_logs(log_entries)
        
        # Calculate ROI
        calculator = ROICalculator({})
        savings_reports = calculator.calculate_savings_by_rule(
            [{'rule_id': v.rule_id, 'log_entry': v.log_entry} for v in violations],
            log_entries
        )
        
        # Generate report
        if output_format == 'json':
            return json.dumps([
                {
                    'rule_id': r.rule_id,
                    'violation_count': r.violation_count,
                    'current_cost': r.current_cost,
                    'potential_savings': r.potential_savings,
                    'efficiency_improvement': r.efficiency_improvement,
                    'suggested_actions': r.suggested_actions
                }
                for r in savings_reports
            ], indent=2)
        else:
            return _format_markdown_roi_report(savings_reports, log_entries)
            
    except Exception as e:
        return f"Error generating ROI report: {e}"

def _format_markdown_roi_report(savings_reports: List[CostSavingsReport], log_entries: List[Dict]) -> str:
    """Format ROI report as Markdown"""
    total_current_cost = sum(r.current_cost for r in savings_reports)
    total_potential_savings = sum(r.potential_savings for r in savings_reports)
    
    markdown_report = f"""# 💰 CrashLens ROI Analysis Report
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## 📊 Executive Summary
- **Total Current Cost**: ${total_current_cost:.4f}
- **Potential Savings**: ${total_potential_savings:.4f} 
- **ROI Percentage**: {(total_potential_savings/total_current_cost*100):.1f}% if implemented
- **Log Entries Analyzed**: {len(log_entries)}

## 🎯 Cost Savings by Policy Rule

"""
    
    for savings_report in savings_reports:
        markdown_report += f"""### {savings_report.rule_id}
- **Violations Found**: {savings_report.violation_count}
- **Current Cost**: ${savings_report.current_cost:.4f}
- **Potential Savings**: ${savings_report.potential_savings:.4f}
- **Efficiency Improvement**: {savings_report.efficiency_improvement:.1f}%

**Recommended Actions:**
"""
        for action in savings_report.suggested_actions:
            markdown_report += f"- {action}\n"
        markdown_report += "\n"
    
    markdown_report += """## 🚀 Implementation Priority
Rules are ordered by potential savings impact. Focus on the top rules first for maximum ROI.

## 📈 Next Steps
1. Implement fixes for high-impact rules
2. Monitor cost reduction over time  
3. Run periodic ROI analysis to track improvements
4. Consider upgrading to CrashLens Pro for advanced patterns
"""
    
    return markdown_report

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python roi_calculator.py <log_file> <policy_file> [output_format]")
        sys.exit(1)
    
    log_file = Path(sys.argv[1])
    policy_file = Path(sys.argv[2])
    output_format = sys.argv[3] if len(sys.argv) > 3 else 'markdown'
    
    report = generate_roi_report(log_file, policy_file, output_format)
    print(report)
