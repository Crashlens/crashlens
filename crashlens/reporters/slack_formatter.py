"""
Slack-style Formatter
Formats detection results in emoji-rich text format for stdout
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from ..utils.pii_scrubber import PIIScrubber


class SlackFormatter:
    """Formats detections in Slack-style emoji text"""
    
    def __init__(self):
        self.severity_emojis = {
            'high': '🔴',
            'medium': '🟡', 
            'low': '🟢'
        }
        
        self.type_emojis = {
            'retry_loop': '🔄',
            'gpt4_short': '💎',
            'expensive_model_short': '💎',
            'fallback_storm': '⚡',
            'fallback_failure': '📢'
        }
        
        self.pii_scrubber = PIIScrubber()
    
    def format(self, detections: List[Dict[str, Any]], traces: Dict[str, List[Dict[str, Any]]], model_pricing: Optional[Dict[str, Any]] = None, summary_only: bool = False) -> str:
        """Format detections in Slack-style output"""
        if not detections:
            return "🔒 CrashLens runs 100% locally. No data leaves your system.\n✅ No token waste patterns detected! Your GPT usage looks efficient."
        
        output = []
        output.append("🔒 CrashLens runs 100% locally. No data leaves your system.")
        if summary_only:
            output.append("📝 Summary-only mode: Prompts, sample inputs, and trace IDs are suppressed for safe internal sharing.")
        output.append("🚨 **CrashLens Token Waste Report**")
        output.append("=" * 50)
        
        # Add analysis metadata
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output.append(f"📅 **Analysis Date**: {current_time}")
        output.append(f"🔍 **Traces Analyzed**: {len(traces):,}")
        output.append("")
        
        # Scrub PII from detections
        scrubbed_detections = [self.pii_scrubber.scrub_detection(detection) for detection in detections]
        
        # Aggregate detections by type
        aggregated = self._aggregate_detections(scrubbed_detections)
        
        # Summary stats
        total_waste_cost = sum(d.get('waste_cost', 0) for d in scrubbed_detections)
        total_waste_tokens = sum(d.get('waste_tokens', 0) for d in scrubbed_detections)
        total_ai_spend = self._calculate_total_ai_spend(traces, model_pricing)
        
        # Sanity check: savings shouldn't exceed total spend
        total_waste_cost = min(total_waste_cost, total_ai_spend)
        
        # Format spend amount appropriately
        if total_ai_spend >= 0.01:
            spend_str = f"${total_ai_spend:.2f}"
        else:
            spend_str = f"${total_ai_spend:.4f}"
        
        output.append(f"🧾 **Total AI Spend**: {spend_str}")
        output.append(f"💰 **Total Potential Savings**: ${total_waste_cost:.4f}")
        output.append(f"🎯 **Wasted Tokens**: {total_waste_tokens:,}")
        output.append(f"📊 **Issues Found**: {len(scrubbed_detections)}")
        output.append("")
        
        # Add top expensive traces and cost breakdown (if we have real costs)
        if total_ai_spend > 0:
            self._add_cost_breakdown(output, traces, summary_only)
            output.append("")
        
        # Format aggregated detections
        for det_type, group_data in aggregated.items():
            type_emoji = self.type_emojis.get(det_type, '❓')
            type_name = det_type.replace('_', ' ').title()
            
            output.append(f"{type_emoji} **{type_name}** ({group_data['count']} issues)")
            output.append(self._format_aggregated_detection(group_data, summary_only))
            output.append("")
        
        # Monthly projection
        if total_waste_cost > 0:
            monthly_projection = total_waste_cost * 30  # Rough estimate
            output.append(f"📈 **Monthly Projection**: ${monthly_projection:.2f} potential savings")
        
        return "\n".join(output)
    
    def _add_cost_breakdown(self, output: List[str], traces: Dict[str, List[Dict[str, Any]]], summary_only: bool):
        """Add top expensive traces and cost by model sections"""
        from collections import defaultdict
        
        # Calculate cost breakdown by model
        model_costs = defaultdict(float)
        trace_costs = {}
        
        for trace_id, records in traces.items():
            trace_cost = 0.0
            for record in records:
                cost = record.get('cost', 0.0)
                model = record.get('input', {}).get('model', record.get('model', 'unknown'))
                
                trace_cost += cost
                model_costs[model] += cost
            
            if trace_cost > 0:
                trace_costs[trace_id] = trace_cost
        
        # Top expensive traces
        if trace_costs:
            output.append("🔍 **Top Expensive Traces**:")
            sorted_traces = sorted(trace_costs.items(), key=lambda x: x[1], reverse=True)[:3]
            for i, (trace_id, cost) in enumerate(sorted_traces, 1):
                cost_str = f"${cost:.2f}" if cost >= 0.01 else f"${cost:.4f}"
                if summary_only:
                    output.append(f"  {i}. trace_*** → {cost_str}")
                else:
                    # Extract model from first record of this trace
                    first_record = traces[trace_id][0] if traces[trace_id] else {}
                    model = first_record.get('input', {}).get('model', first_record.get('model', 'unknown'))
                    output.append(f"  {i}. {trace_id} → {model} → {cost_str}")
        
        # Cost by model
        if model_costs:
            total_cost = sum(model_costs.values())
            output.append("")
            output.append("📊 **Cost by Model**:")
            sorted_models = sorted(model_costs.items(), key=lambda x: x[1], reverse=True)
            for model, cost in sorted_models:
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                cost_str = f"${cost:.2f}" if cost >= 0.01 else f"${cost:.4f}"
                output.append(f"  • {model}: {cost_str} ({percentage:.0f}%)")
    
    def _aggregate_detections(self, detections: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Aggregate detections by type and model"""
        aggregated = {}
        
        for detection in detections:
            det_type = detection['type']
            model_used = detection.get('model_used', 'unknown')
            suggested_model = detection.get('suggested_model', 'unknown')
            
            # Only aggregate 'expensive_model_short' for expensive model waste
            if det_type == 'expensive_model_short':
                key = f"{det_type}_{model_used}_{suggested_model}"
            else:
                key = det_type
            
            if key not in aggregated:
                aggregated[key] = {
                    'type': det_type,
                    'count': 0,
                    'total_waste_cost': 0.0,
                    'total_waste_tokens': 0,
                    'sample_prompts': [],
                    'model_used': model_used,
                    'suggested_model': suggested_model,
                    'severity': detection.get('severity', 'medium'),
                    'detections': []
                }
            
            group = aggregated[key]
            group['count'] += 1
            group['total_waste_cost'] += detection.get('waste_cost', 0)
            group['total_waste_tokens'] += detection.get('waste_tokens', 0)
            group['detections'].append(detection)
            
            # Collect sample prompts (up to 3 unique ones)
            sample_prompt = detection.get('sample_prompt', '')
            if sample_prompt and sample_prompt not in group['sample_prompts'] and len(group['sample_prompts']) < 3:
                group['sample_prompts'].append(sample_prompt)
        
        return aggregated
    
    def _format_aggregated_detection(self, group_data: Dict[str, Any], summary_only: bool = False) -> str:
        """Format an aggregated detection group"""
        lines = []
        
        # Main description
        if group_data['type'] == 'expensive_model_short':
            model_used = group_data['model_used'].upper()
            suggested_model = group_data['suggested_model']
            lines.append(f"  • {group_data['count']} traces used {model_used} instead of {suggested_model}")
        elif group_data['type'] == 'retry_loop':
            lines.append(f"  • {group_data['count']} traces with excessive retries")
        elif group_data['type'] == 'fallback_storm':
            lines.append(f"  • {group_data['count']} traces with model fallback storms")
        elif group_data['type'] == 'fallback_failure':
            lines.append(f"  • {group_data['count']} traces with unnecessary fallback calls")
        else:
            lines.append(f"  • {group_data['count']} traces affected")
        
        # Cost and token info
        if group_data['total_waste_cost'] > 0:
            lines.append(f"  • Est. waste: ${group_data['total_waste_cost']:.4f}")
        
        if group_data['total_waste_tokens'] > 0:
            lines.append(f"  • Wasted tokens: {group_data['total_waste_tokens']:,}")
        
        # Sample prompts (suppress in summary_only)
        if group_data['sample_prompts'] and not summary_only:
            lines.append(f"  • Sample prompts: {', '.join(f'\"{p[:30]}...\"' for p in group_data['sample_prompts'])}")
        
        # Suggested fix
        if group_data['type'] == 'expensive_model_short':
            lines.append(f"  • Suggested fix: route short prompts to {group_data['suggested_model']}")
        elif group_data['type'] == 'retry_loop':
            lines.append("  • Suggested fix: implement exponential backoff and circuit breakers")
        elif group_data['type'] == 'fallback_storm':
            lines.append("  • Suggested fix: optimize model selection logic")
        elif group_data['type'] == 'fallback_failure':
            lines.append("  • Suggested fix: remove redundant fallback calls after successful cheaper model calls")
        
        return "\n".join(lines)
    
    def _format_detection(self, detection: Dict[str, Any], severity_emoji: str, summary_only: bool = False) -> str:
        """Format a single detection (kept for backward compatibility)"""
        lines = []
        
        # Main description
        lines.append(f"  {severity_emoji} {detection['description']}")
        
        # Cost and token info
        if detection.get('waste_cost', 0) > 0:
            lines.append(f"     💰 Waste: ${detection['waste_cost']:.4f}")
        
        if detection.get('waste_tokens', 0) > 0:
            lines.append(f"     🎯 Tokens: {detection['waste_tokens']:,}")
        
        # Type-specific details
        if detection['type'] == 'retry_loop':
            lines.append(f"     🔄 Retries: {detection.get('retry_count', 0)}")
            lines.append(f"     ⏱️  Time: {detection.get('time_span', 'unknown')}")
        
        elif detection['type'] in ['gpt4_short', 'expensive_model_short']:
            lines.append(f"     📝 Prompt length: {detection.get('prompt_length', 0)} tokens")
            lines.append(f"     🤖 Model: {detection.get('model_used', 'unknown')}")
            lines.append(f"     💡 Suggested: {detection.get('suggested_model', 'gpt-3.5-turbo')}")
        
        elif detection['type'] == 'fallback_storm':
            lines.append(f"     ⚡ Fallbacks: {detection.get('fallback_count', 0)}")
            models = detection.get('models_sequence', [])
            if models:
                lines.append(f"     🔄 Models: {' → '.join(models)}")
            lines.append(f"     ⏱️  Time: {detection.get('time_span', 'unknown')}")
        
        elif detection['type'] == 'fallback_failure':
            lines.append(f"     📢 Primary: {detection.get('primary_model', 'unknown')} → Fallback: {detection.get('fallback_model', 'unknown')}")
            lines.append(f"     💰 Waste: ${detection.get('waste_cost', 0):.4f}")
            lines.append(f"     ⏱️  Time between: {detection.get('time_between_calls', 'unknown')}")
            if not summary_only:
                lines.append(f"     📝 Primary prompt: {detection.get('primary_prompt', '')[:50]}...")
        
        # Sample prompt (suppress in summary_only)
        if detection.get('sample_prompt') and not summary_only:
            lines.append(f"     📄 Sample: {detection['sample_prompt']}")
        
        # Trace ID (suppress in summary_only)
        if not summary_only:
            lines.append(f"     🔗 Trace: {detection.get('trace_id', 'unknown')}")
        
        return "\n".join(lines) 

    def _calculate_total_ai_spend(self, traces: Dict[str, List[Dict[str, Any]]], model_pricing: Optional[Dict[str, Any]] = None) -> float:
        """Calculate the total cost of all traces using existing cost field or pricing config"""
        total = 0.0
        for records in traces.values():
            for record in records:
                # First try to use existing cost field
                if 'cost' in record and record['cost'] is not None:
                    total += record['cost']
                    continue
                
                # Fallback to calculating from pricing config
                if model_pricing:
                    model = record.get('model', record.get('input', {}).get('model', 'gpt-3.5-turbo'))
                    
                    # Get tokens from various possible locations
                    usage = record.get('usage', {})
                    input_tokens = (record.get('prompt_tokens') or 
                                   usage.get('prompt_tokens') or 0)
                    output_tokens = (record.get('completion_tokens') or 
                                    usage.get('completion_tokens') or 0)
                    
                    model_config = model_pricing.get(model, {})
                    if model_config:
                        input_cost = (input_tokens / 1000) * model_config.get('input_cost_per_1k', 0)
                        output_cost = (output_tokens / 1000) * model_config.get('output_cost_per_1k', 0)
                        total += input_cost + output_cost
        return total 