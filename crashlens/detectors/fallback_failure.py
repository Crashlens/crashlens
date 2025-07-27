"""
Fallback Failure Detector
Detects redundant fallback calls to expensive models after successful cheaper model calls
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class FallbackFailureDetector:
    """Detects unnecessary fallback calls to expensive models after successful cheaper calls"""
    
    def __init__(self, time_window_seconds: int = 300):
        self.time_window = timedelta(seconds=time_window_seconds)
        
        # Define model tiers (cheaper to more expensive)
        self.cheaper_models = {
            'gpt-3.5-turbo', 'gpt-3.5-turbo-16k', 'claude-3-haiku', 'claude-instant-1'
        }
        
        self.expensive_models = {
            'gpt-4', 'gpt-4-32k', 'gpt-4-turbo', 'claude-3-opus', 'claude-3-sonnet', 
            'claude-2.1', 'claude-2.0'
        }
    
    def detect(self, traces: Dict[str, List[Dict[str, Any]]], model_pricing: Optional[Dict[str, Any]] = None, already_flagged_ids: Optional[set] = None) -> List[Dict[str, Any]]:
        """Detect fallback failures across all traces"""
        detections = []
        if already_flagged_ids is None:
            already_flagged_ids = set()
        
        for trace_id, records in traces.items():
            # Skip if trace is already flagged by RetryLoopDetector
            if trace_id in already_flagged_ids:
                continue
            
            # Ensure trace has ≥2 LLM spans
            if len(records) < 2:
                continue
                
            # Sort records by timestamp
            sorted_records = sorted(records, key=lambda r: r.get('startTime', ''))
            
            # Look for fallback failure patterns
            fallback_failures = self._find_fallback_failures(sorted_records, model_pricing)
            
            for failure in fallback_failures:
                failure['trace_id'] = trace_id
                detections.append(failure)
        
        return [d for d in detections if d is not None]
    
    def _find_fallback_failures(self, records: List[Dict[str, Any]], model_pricing: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Find fallback failure patterns in sorted records"""
        failures: List[Dict[str, Any]] = []
        
        for i in range(len(records) - 1):
            first_record = records[i]
            second_record = records[i + 1]
            
            # Check if this is a fallback failure pattern
            if self._is_fallback_failure(first_record, second_record):
                failure = self._create_failure_detection(first_record, second_record, model_pricing)
                if failure is not None:
                    failures.append(failure)
        
        return [f for f in failures if f is not None]
    
    def _is_fallback_failure(self, first_record: Dict[str, Any], second_record: Dict[str, Any]) -> bool:
        """Check if two records represent a fallback failure pattern"""
        # Extract key fields
        first_model = first_record.get('model') or first_record.get('input', {}).get('model', '')
        second_model = second_record.get('model') or second_record.get('input', {}).get('model', '')
        first_prompt = first_record.get('prompt', '')
        second_prompt = second_record.get('prompt', '')
        first_time = first_record.get('startTime', '')
        second_time = second_record.get('startTime', '')

        # Check if models are in different tiers (cheaper → expensive)
        if not (self._is_cheaper_model(first_model) and self._is_expensive_model(second_model)):
            return False

        # Check if first call succeeded (has output, not error)
        if not self._first_call_succeeded(first_record):
            return False

        # Check if second call used the same prompt (exact string match)
        if not self._are_prompts_identical(first_prompt, second_prompt):
            return False

        # Enforce time window ≤ 5 minutes (default 300s)
        if not self._are_within_time_window(first_time, second_time):
            return False

        return True
    
    def _is_cheaper_model(self, model: str) -> bool:
        """Check if model is in the cheaper tier (supports versioned names)"""
        for cheaper in self.cheaper_models:
            if model and model.startswith(cheaper):
                return True
        return False

    def _is_expensive_model(self, model: str) -> bool:
        """Check if model is in the expensive tier (supports versioned names)"""
        for expensive in self.expensive_models:
            if model and model.startswith(expensive):
                return True
        return False
    
    def _first_call_succeeded(self, record: Dict[str, Any]) -> bool:
        """Check if the first call succeeded (has output, not error)"""
        # Check if there's any output/completion tokens
        completion_tokens = record.get('usage', {}).get('completion_tokens', 0)
        if completion_tokens > 0:
            return True
        
        # Check if there's a direct completion field
        if record.get('completion') or record.get('output'):
            return True
            
        # Check if metadata indicates success (no fallback attempted)
        metadata = record.get('metadata', {})
        return not metadata.get('fallback_attempted', False)
    
    def _are_prompts_identical(self, prompt1: str, prompt2: str) -> bool:
        """Check if two prompts are exactly the same using strict equality"""
        if not prompt1 or not prompt2:
            return False
        
        # Use exact string matching with stripped whitespace
        return prompt1.strip() == prompt2.strip()
    
    def _are_within_time_window(self, time1: str, time2: str) -> bool:
        """Check if two timestamps are within the time window"""
        try:
            dt1 = datetime.fromisoformat(time1.replace('Z', '+00:00'))
            dt2 = datetime.fromisoformat(time2.replace('Z', '+00:00'))
            time_diff = abs((dt2 - dt1).total_seconds())
            return time_diff <= self.time_window.total_seconds()
        except (ValueError, TypeError):
            return False
    
    def _create_failure_detection(self, first_record: Dict[str, Any], second_record: Dict[str, Any], model_pricing: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Create a fallback failure detection object"""
        first_model = first_record.get('model') or first_record.get('input', {}).get('model', '')
        second_model = second_record.get('model') or second_record.get('input', {}).get('model', '')
        first_prompt = first_record.get('prompt', '')
        second_prompt = second_record.get('prompt', '')
        
        # Calculate waste metrics
        # Handle both flattened (from parser) and nested (original) structures
        if 'usage' in second_record:
            usage = second_record.get('usage', {})
            fallback_prompt_tokens = usage.get('prompt_tokens', 0)
            fallback_completion_tokens = usage.get('completion_tokens', 0)
        else:
            fallback_prompt_tokens = second_record.get('prompt_tokens', 0)
            fallback_completion_tokens = second_record.get('completion_tokens', 0)
        
        fallback_tokens = fallback_prompt_tokens + fallback_completion_tokens
        
        # Calculate cost if pricing is available
        fallback_cost = 0.0
        if model_pricing and second_model in model_pricing:
            model_config = model_pricing[second_model]
            # Handle both per_1k and per_1m pricing formats
            input_cost_per_1k = model_config.get('input_cost_per_1k', 0)
            output_cost_per_1k = model_config.get('output_cost_per_1k', 0)
            input_cost_per_1m = model_config.get('input_cost_per_1m', 0)
            output_cost_per_1m = model_config.get('output_cost_per_1m', 0)
            
            # Use per_1k if available, otherwise convert from per_1m
            if input_cost_per_1k > 0:
                input_cost = input_cost_per_1k / 1000
            else:
                input_cost = input_cost_per_1m / 1000000
                
            if output_cost_per_1k > 0:
                output_cost = output_cost_per_1k / 1000
            else:
                output_cost = output_cost_per_1m / 1000000
            
            fallback_cost = (fallback_prompt_tokens * input_cost) + (fallback_completion_tokens * output_cost)
        
        # Get timestamps
        first_time = first_record.get('startTime', '')
        second_time = second_record.get('startTime', '')
        
        # Calculate time difference
        time_diff = "unknown"
        try:
            dt1 = datetime.fromisoformat(first_time.replace('Z', '+00:00'))
            dt2 = datetime.fromisoformat(second_time.replace('Z', '+00:00'))
            time_diff = f"{abs((dt2 - dt1).total_seconds()):.1f} seconds"
        except (ValueError, TypeError):
            pass
        
        return {
            'type': 'fallback_failure',
            'detection_method': 'exact_match',
            'severity': 'high' if fallback_cost > 0.01 else 'medium',
            'description': f"Unnecessary fallback from {first_model} to {second_model}",
            'model_tiers': f"{first_model} → {second_model}",
            'waste_tokens': fallback_tokens,
            'waste_cost': fallback_cost,
            'primary_model': first_model,
            'fallback_model': second_model,
            'primary_prompt': first_prompt[:200] + '...' if len(first_prompt) > 200 else first_prompt,
            'fallback_prompt': second_prompt[:200] + '...' if len(second_prompt) > 200 else second_prompt,
            'time_between_calls': time_diff,
            'primary_tokens': (
                first_record.get('prompt_tokens', 0) + 
                first_record.get('completion_tokens', 0)
            ),
            'fallback_tokens': fallback_tokens,
            'records': [first_record, second_record]
        }