"""
Summary Formatter
Aggregates total costs by route, model, and team from traces
"""

from typing import Dict, List, Any
from datetime import datetime
from ..utils.pii_scrubber import PIIScrubber
from collections import defaultdict


class SummaryFormatter:
    """Formats cost summaries by route, model, and team"""
    
    def __init__(self):
        self.pii_scrubber = PIIScrubber()
    
    def format(self, traces: Dict[str, List[Dict[str, Any]]], model_pricing: Dict[str, Any], summary_only: bool = False, detections: List[Dict[str, Any]] = None) -> str:
        """Format cost summary from traces using compact FinOps format with waste analysis"""
        if not traces:
            return "🔒 CrashLens runs 100% locally. No data leaves your system.\nℹ️  No traces found for summary"
        
        # For summary-only mode, create ultra-concise 2-3 line report
        if summary_only:
            return self._format_summary_only(traces, model_pricing, detections)
        
        # Regular summary mode - detailed format
        output = []
        output.append("🔒 CrashLens runs 100% locally. No data leaves your system.")
        output.append("📝 Summary mode: Trace IDs are suppressed for safe internal sharing.")
        
        # Calculate totals first
        total_cost = 0.0
        total_tokens = 0
        model_costs = defaultdict(float)
        
        # Process all traces for totals
        for trace_id, records in traces.items():
            for record in records:
                cost = self._calculate_record_cost(record, model_pricing)
                total_cost += cost
                
                # Get tokens from multiple possible locations
                usage = record.get('usage', {})
                prompt_tokens = (usage.get('prompt_tokens', 0) or 
                               record.get('prompt_tokens', 0) or 0)
                completion_tokens = (usage.get('completion_tokens', 0) or 
                                   record.get('completion_tokens', 0) or 0)
                total_tokens += prompt_tokens + completion_tokens
                
                # Track model costs
                model = record.get('input', {}).get('model', record.get('model', 'unknown'))
                model_costs[model] += cost
        
        # Generate compact header (similar to Slack format)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cost_str = f"${total_cost:.4f}" if total_cost < 0.01 else f"${total_cost:.2f}"
        
        # Only show tokens if we have a meaningful count, otherwise suppress the field
        if total_tokens > 0:
            output.append(f"📊 CrashLens Summary – {timestamp} | Traces: {len(traces)} | Cost: {cost_str} | Tokens: {total_tokens:,}")
        else:
            output.append(f"📊 CrashLens Summary – {timestamp} | Traces: {len(traces)} | Cost: {cost_str}")
        output.append("")
        
        # Model breakdown - compact format
        if model_costs:
            sorted_models = sorted(model_costs.items(), key=lambda x: x[1], reverse=True)
            model_parts = []
            for model, cost in sorted_models:
                cost_str = f"${cost:.4f}" if cost < 0.01 else f"${cost:.2f}"
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                model_parts.append(f"{model}: {cost_str} ({percentage:.0f}%)")
            
            output.append(f"🤖 Model Breakdown: {' | '.join(model_parts)}")
        
        # Top expensive traces
        self._add_top_traces_summary(output, traces, summary_only)
        
        # Add waste analysis if detections are provided
        if detections:
            self._add_waste_analysis_summary(output, detections, summary_only)
        
        return "\n".join(output)

    def _format_summary_only(self, traces: Dict[str, List[Dict[str, Any]]], model_pricing: Dict[str, Any], detections: List[Dict[str, Any]] = None) -> str:
        """Create ultra-concise 2-3 line summary-only report"""
        # Calculate totals
        total_cost = 0.0
        total_waste_cost = 0.0
        total_issues = 0
        
        # Calculate total cost
        for trace_id, records in traces.items():
            for record in records:
                cost = self._calculate_record_cost(record, model_pricing)
                total_cost += cost
        
        # Calculate waste cost and issues
        if detections:
            total_waste_cost = sum(d.get('waste_cost', 0) for d in detections)
            total_issues = len(detections)
        
        # Format costs
        cost_str = f"${total_cost:.2f}" if total_cost >= 0.01 else f"${total_cost:.4f}"
        waste_str = f"${total_waste_cost:.2f}" if total_waste_cost >= 0.01 else f"${total_waste_cost:.4f}"
        
        # Create ultra-concise output (2-3 lines max)
        output = []
        
        # Line 1: Basic summary
        output.append(f"📊 {len(traces)} traces | {cost_str} total | {waste_str} waste")
        
        # Line 2: Issues breakdown (only if there are issues)
        if total_issues > 0:
            # Group by type for concise display
            issue_types = {}
            for detection in detections:
                detector_type = detection.get('type', 'unknown')
                if detector_type not in issue_types:
                    issue_types[detector_type] = 0
                issue_types[detector_type] += 1
            
            # Create compact issue summary
            issue_parts = []
            for issue_type, count in issue_types.items():
                if issue_type == 'retry_loop':
                    issue_parts.append(f"{count} retry")
                elif issue_type == 'fallback_storm':
                    issue_parts.append(f"{count} fallback")
                elif issue_type == 'fallback_failure':
                    issue_parts.append(f"{count} failure")
                elif issue_type == 'overkill_model':
                    issue_parts.append(f"{count} overkill")
                else:
                    issue_parts.append(f"{count} {issue_type}")
            
            output.append(f"🚨 {total_issues} issues: {', '.join(issue_parts)}")
        else:
            output.append("✅ No waste patterns detected")
        
        # Line 3: Savings potential (only if there's waste)
        if total_waste_cost > 0:
            savings_percentage = (total_waste_cost / total_cost * 100) if total_cost > 0 else 0
            output.append(f"💡 {savings_percentage:.0f}% potential savings")
        
        return "\n".join(output)

    def _add_top_traces_summary(self, output: List[str], traces: Dict[str, List[Dict[str, Any]]], summary_only: bool):
        """Add compact top traces section"""
        trace_costs = {}
        
        for trace_id, records in traces.items():
            trace_cost = sum(record.get('cost', 0.0) for record in records)
            if trace_cost > 0:
                trace_costs[trace_id] = trace_cost
        
        if trace_costs:
            # Show fewer traces for summary-only mode
            max_traces = 3 if summary_only else 5
            sorted_traces = sorted(trace_costs.items(), key=lambda x: x[1], reverse=True)[:max_traces]
            trace_lines = []
            
            for i, (trace_id, cost) in enumerate(sorted_traces, 1):
                cost_str = f"${cost:.4f}" if cost < 0.01 else f"${cost:.2f}"
                if summary_only:
                    # Summary-only: just costs, no trace IDs or models
                    trace_lines.append(f"#{i}: {cost_str}")
                else:
                    # Summary: show models but hide trace IDs
                    first_record = traces[trace_id][0] if traces[trace_id] else {}
                    model = first_record.get('input', {}).get('model', first_record.get('model', 'unknown'))
                    trace_lines.append(f"#{i}: {model} → {cost_str}")
            
            output.append("")
            output.append(f"🏆 Top {len(trace_lines)} Traces: " + " | ".join(trace_lines))
    
    def _calculate_record_cost(self, record: Dict[str, Any], model_pricing: Dict[str, Any]) -> float:
        """Calculate cost for a single record"""
        model = record.get('model', 'gpt-3.5-turbo')
        input_tokens = record.get('prompt_tokens', 0)
        output_tokens = record.get('completion_tokens', 0)
        
        # Use provided cost if available, otherwise calculate from pricing
        if 'cost' in record and record['cost'] is not None:
            return record['cost']
        
        # Calculate from pricing config
        model_config = model_pricing.get(model, {})
        if model_config:
            input_cost = (input_tokens / 1000) * model_config.get('input_cost_per_1k', 0)
            output_cost = (output_tokens / 1000) * model_config.get('output_cost_per_1k', 0)
            return input_cost + output_cost
        
        return 0.0

    def _add_waste_analysis_summary(self, output: List[str], detections: List[Dict[str, Any]], summary_only: bool):
        """Add concise waste analysis to summary"""
        if not detections:
            return
        
        # Group detections by type
        waste_by_type = {}
        for detection in detections:
            detector_type = detection.get('type', 'unknown')
            if detector_type not in waste_by_type:
                waste_by_type[detector_type] = {
                    'count': 0,
                    'total_cost': 0.0,
                    'total_tokens': 0
                }
            
            waste_by_type[detector_type]['count'] += 1
            waste_by_type[detector_type]['total_cost'] += detection.get('waste_cost', 0)
            waste_by_type[detector_type]['total_tokens'] += detection.get('waste_tokens', 0)
        
        # Add waste summary
        output.append("")
        output.append("🚨 Waste Analysis:")
        
        # Map detector types to display names
        display_names = {
            'retry_loop': '🔄 Retry Loops',
            'fallback_storm': '⚡ Fallback Storms', 
            'fallback_failure': '📢 Fallback Failures',
            'overkill_model': '❓ Overkill Models'
        }
        
        total_waste_cost = sum(d.get('waste_cost', 0) for d in detections)
        total_waste_tokens = sum(d.get('waste_tokens', 0) for d in detections)
        
        if total_waste_cost > 0:
            output.append(f"   💰 Total Waste: ${total_waste_cost:.4f}")
            output.append(f"   🎯 Wasted Tokens: {total_waste_tokens:,}")
            output.append("")
            
            # Show breakdown by type
            for detector_type, data in waste_by_type.items():
                if data['total_cost'] > 0:
                    display_name = display_names.get(detector_type, detector_type.title())
                    cost_str = f"${data['total_cost']:.4f}"
                    if summary_only:
                        output.append(f"   {display_name}: {data['count']} issues, {cost_str}")
                    else:
                        output.append(f"   {display_name}: {data['count']} issues, {cost_str}, {data['total_tokens']:,} tokens")
        else:
            output.append("   ✅ No waste patterns detected") 