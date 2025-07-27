"""
Fallback Storm Detector - OSS v0.1 Minimal Implementation
Detects chaotic model switching and cost spikes within traces
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class FallbackStormDetector:
    """Detects fallback storms according to OSS v0.1 minimal checklist"""
    
    def __init__(self, min_calls: int = 3, min_models: int = 2, max_trace_window_minutes: int = 3):
        """
        Initialize detector with OSS v0.1 minimal configuration
        
        Args:
            min_calls: Minimum calls required to trigger detection (default: 3)
            min_models: Minimum distinct models required (default: 2) 
            max_trace_window_minutes: Maximum time window for trace (default: 3 minutes)
        """
        self.min_calls = min_calls
        self.min_models = min_models
        self.max_trace_window = timedelta(minutes=max_trace_window_minutes)
    
    def detect(self, traces: Dict[str, List[Dict[str, Any]]], model_pricing: Optional[Dict[str, Any]] = None, already_flagged_ids: Optional[set] = None) -> List[Dict[str, Any]]:
        """
        Detect fallback storms according to OSS v0.1 minimal checklist
        
        Args:
            traces: Dictionary of trace_id -> list of records
            model_pricing: Optional pricing configuration
            already_flagged_ids: Set of trace IDs already flagged by RetryLoopDetector
            
        Returns:
            List of detection results
        """
        detections = []
        if already_flagged_ids is None:
            already_flagged_ids = set()
        
        for trace_id, records in traces.items():
            # ⚠️ SUPPRESSION: Skip if already flagged by RetryLoopDetector
            if trace_id in already_flagged_ids:
                continue
            
            detection = self._check_storm_pattern(trace_id, records, model_pricing)
            if detection:
                detections.append(detection)
        
        return detections
    
    def _check_storm_pattern(self, trace_id: str, records: List[Dict[str, Any]], model_pricing: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Check if trace matches fallback storm pattern according to checklist"""
        
        # 🔍 CHECKLIST 1: Same trace_id (already grouped)
        # 🔍 CHECKLIST 2: 3 or more total calls in the trace
        if len(records) < self.min_calls:
            return None
        
        # Sort records by time
        sorted_records = sorted(records, key=lambda r: r.get('startTime', ''))
        
        # 🔍 CHECKLIST 4: All calls occurred within 3 minutes
        if not self._within_time_window(sorted_records):
            return None
        
        # 🔍 CHECKLIST 3: 2 or more distinct models used
        models_used = []
        for r in sorted_records:
            model = r.get('model') or r.get('input', {}).get('model')
            if model:
                models_used.append(model.lower())
        unique_models = list(dict.fromkeys(models_used))  # Preserve order, remove duplicates
        
        if len(unique_models) < self.min_models:
            return None
        
        # Calculate estimated waste
        estimated_waste = self._calculate_estimated_waste(sorted_records, model_pricing)
        
        # Calculate total tokens used in the storm
        total_tokens = 0
        for record in sorted_records:
            # Handle both flattened (from parser) and nested (original) structures
            if 'usage' in record:
                usage = record.get('usage', {})
                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)
            else:
                prompt_tokens = record.get('prompt_tokens', 0)
                completion_tokens = record.get('completion_tokens', 0)
            total_tokens += prompt_tokens + completion_tokens
        
        # 🖨️ CLI OUTPUT FORMAT: Return detection according to specification
        return {
            'type': 'fallback_storm',
            'detector': 'fallback_storm',
            'trace_id': trace_id,
            'severity': 'high' if len(sorted_records) > 5 else 'medium',
            'description': f"Fallback storm: {len(unique_models)} models used in {len(sorted_records)} calls",
            'models_used': unique_models,
            'num_calls': len(sorted_records),
            'estimated_waste_usd': estimated_waste,
            'waste_cost': estimated_waste,
            'waste_tokens': total_tokens,
            'suppressed_by': None,
            'time_span': self._get_time_span_seconds(sorted_records),
            'sample_prompt': sorted_records[0].get('prompt', '')[:100] + '...' if len(sorted_records[0].get('prompt', '')) > 100 else sorted_records[0].get('prompt', '')
        }
    
    def _within_time_window(self, records: List[Dict[str, Any]]) -> bool:
        """Check if all calls occurred within the time window"""
        if len(records) < 2:
            return True
        
        try:
            timestamps = []
            for record in records:
                ts_str = record.get('startTime', '')
                if ts_str:
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    timestamps.append(ts)
            
            if len(timestamps) < 2:
                return True
            
            time_span = max(timestamps) - min(timestamps)
            return time_span <= self.max_trace_window
            
        except (ValueError, TypeError):
            return False
    
    def _calculate_estimated_waste(self, records: List[Dict[str, Any]], model_pricing: Optional[Dict[str, Any]]) -> float:
        """Calculate estimated waste (simple sum of model costs)"""
        total_cost = 0.0
        
        for record in records:
            # Use existing cost if available
            if 'cost' in record and record['cost'] is not None:
                total_cost += float(record['cost'])
                continue
            
            # Calculate from pricing if available
            if model_pricing:
                model = record.get('model', '')
                model_config = model_pricing.get(model, {})
                if model_config:
                    input_tokens = record.get('usage', {}).get('prompt_tokens', 0)
                    output_tokens = record.get('usage', {}).get('completion_tokens', 0)
                    
                    input_cost = (input_tokens / 1000) * model_config.get('input_cost_per_1k', 0)
                    output_cost = (output_tokens / 1000) * model_config.get('output_cost_per_1k', 0)
                    total_cost += input_cost + output_cost
        
        return round(total_cost, 6)
    
    def _get_time_span_seconds(self, records: List[Dict[str, Any]]) -> float:
        """Get time span of records in seconds"""
        if len(records) < 2:
            return 0.0
        
        try:
            timestamps = []
            for record in records:
                ts_str = record.get('startTime', '')
                if ts_str:
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    timestamps.append(ts)
            
            if len(timestamps) < 2:
                return 0.0
            
            span = max(timestamps) - min(timestamps)
            return round(span.total_seconds(), 2)
            
        except (ValueError, TypeError):
            return 0.0 