"""
Overkill Model Detector - Enhanced v1.2
Detects inefficient use of expensive models for short/simple prompts according to official checklist.
Supports configurable thresholds, cost estimation, and routing suggestions.
"""

import re
import json
from typing import Dict, List, Any, Optional


class OverkillModelDetector:
    """Detects overkill usage of expensive models for short/simple tasks"""
    
    def __init__(self, 
                 max_prompt_tokens: int = 20, 
                 max_prompt_chars: int = 150,
                 expensive_models: Optional[List[str]] = None,
                 simple_task_keywords: Optional[List[str]] = None,
                 comment_tags: Optional[List[str]] = None):
        """
        Initialize the Enhanced Overkill Model Detector
        
        Args:
            max_prompt_tokens: Maximum tokens for short prompt detection (configurable)
            max_prompt_chars: Maximum characters for very short prompt detection
            expensive_models: List of models to check for overkill (configurable)
            simple_task_keywords: Keywords indicating simple tasks
            comment_tags: Optional comment tags to check for (#low_priority)
        """
        self.max_prompt_tokens = max_prompt_tokens
        self.max_prompt_chars = max_prompt_chars
        
        # 🧠 2. Configurable expensive models list
        self.expensive_models = expensive_models or [
            "gpt-4", "gpt-4-1106-preview", "gpt-4-turbo", "gpt-4-32k", "gpt-4o",
            "claude-2", "claude-2.1", "claude-3-opus", "claude-3-sonnet"
        ]
        
        # 🧠 2. Configurable simple task keywords
        self.simple_task_keywords = simple_task_keywords or [
            "summarize", "fix grammar", "translate", "explain", "what is", 
            "hello", "hi", "thanks", "thank you", "yes", "no", "ok"
        ]
        
        # 🧠 2. Optional comment tag matching
        self.comment_tags = comment_tags or ["#low_priority", "#simple", "#quick"]
        
        # Routing suggestions for cost optimization
        self.routing_suggestions = {
            "gpt-4": "gpt-3.5-turbo",
            "gpt-4-32k": "gpt-3.5-turbo",
            "gpt-4-turbo": "gpt-3.5-turbo",
            "claude-3-opus": "claude-3-haiku",
            "claude-3-sonnet": "claude-3-haiku",
            "claude-2.1": "claude-instant-1"
        }
    
    def detect(self, traces: Dict[str, List[Dict[str, Any]]], model_pricing: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Detect overkill model usage with enhanced cost estimation and routing suggestions
        
        Args:
            traces: Dictionary of trace_id -> list of records
            model_pricing: Pricing configuration for cost estimation
            
        Returns:
            List of detection results with cost estimates and routing suggestions
        """
        detections = []
        
        for trace_id, records in traces.items():
            for record in records:
                detection = self._check_overkill_pattern(trace_id, record, model_pricing)
                if detection:
                    detections.append(detection)
        
        return detections
    
    def _check_overkill_pattern(self, trace_id: str, record: Dict[str, Any], model_pricing: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Check if a single record represents overkill model usage"""
        
        # ✅ CHECKLIST: Span uses expensive model - handle both field formats
        model = record.get('model', '') or record.get('input', {}).get('model', '')
        model = model.lower()
        if not self._is_expensive_model(model):
            return None
        
        # ✅ CHECKLIST: Span succeeded (returned output, not error)
        if not self._span_succeeded(record):
            return None
        
        # Extract prompt from various possible locations
        prompt = (record.get('prompt', '') or 
                 record.get('input', {}).get('prompt', '') or
                 self._extract_prompt_from_messages(record.get('input', {}).get('messages', [])))
        
        # ✅ CHECKLIST: Check if prompt is short
        prompt_tokens = self._estimate_tokens(prompt)
        if prompt_tokens > self.max_prompt_tokens:
            return None
        
        # ✅ CHECKLIST: Check if task looks simple via heuristics
        simple_reason = self._check_simple_task_heuristics(prompt)
        if not simple_reason:
            return None
        
        # ⚠️ SUPPRESSION LOGIC: Do not flag complex formats
        if self._has_complex_format(prompt):
            return None
        
        # 📈 4. Calculate estimated cost with accurate pricing
        estimated_cost = self._calculate_estimated_cost(record, model_pricing)
        suggested_model = self.routing_suggestions.get(model, "gpt-3.5-turbo")
        potential_savings = self._calculate_potential_savings(record, model, suggested_model, model_pricing)
        
        # Calculate total tokens used
        # Handle both flattened (from parser) and nested (original) structures
        if 'usage' in record:
            usage = record.get('usage', {})
            prompt_tokens_actual = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
        else:
            prompt_tokens_actual = record.get('prompt_tokens', 0)
            completion_tokens = record.get('completion_tokens', 0)
        total_tokens = prompt_tokens_actual + completion_tokens
        
        # 💡 CLI OUTPUT: Return enhanced detection metadata with cost and routing info
        return {
            'type': 'overkill_model',
            'trace_id': trace_id,
            'severity': 'medium',
            'model': model,
            'prompt_tokens': prompt_tokens,
            'prompt_length': len(prompt),
            'reason': simple_reason,
            'estimated_cost_usd': estimated_cost,
            'suggested_model': suggested_model,
            'potential_savings_usd': potential_savings,
            'prompt_preview': prompt[:50] + "..." if len(prompt) > 50 else prompt,
            'overkill_detected': True,
            'description': f"Overkill: {model} used for simple task ({simple_reason})",
            'waste_cost': estimated_cost * 0.7,  # Assume 70% could be saved with cheaper model
            'waste_tokens': total_tokens,
            'sample_prompt': prompt[:100] + '...' if len(prompt) > 100 else prompt
        }
    
    def _is_expensive_model(self, model: str) -> bool:
        """Check if model is considered expensive for overkill detection"""
        model_lower = model.lower()
        return any(expensive in model_lower for expensive in self.expensive_models)
    
    def _span_succeeded(self, record: Dict[str, Any]) -> bool:
        """Check if span succeeded (returned output, not error)"""
        # Check for completion tokens
        completion_tokens = record.get('usage', {}).get('completion_tokens', 0)
        if completion_tokens > 0:
            return True
        
        # Check for direct output fields
        if record.get('completion') or record.get('output'):
            return True
        
        # Check if there's no error indicated
        if not record.get('error') and not record.get('failed', False):
            return True
        
        return False
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count using simple word splitting (approximation)"""
        if not text:
            return 0
        # Simple approximation: ~0.75 tokens per word
        word_count = len(text.split())
        return max(1, int(word_count * 0.75))
    
    def _check_simple_task_heuristics(self, prompt: str) -> Optional[str]:
        """
        Check if task looks simple via heuristics
        Returns reason string if simple, None if complex
        """
        prompt_lower = prompt.lower().strip()
        
        # ✅ CHECKLIST: Prompt starts with simple keywords
        for keyword in self.simple_task_keywords:
            if prompt_lower.startswith(keyword):
                return f"prompt starts with '{keyword}'"
        
        # ✅ CHECKLIST: Prompt length very short
        if len(prompt) < self.max_prompt_chars:
            return f"prompt too short ({len(prompt)} chars)"
        
        # Additional heuristics for simple tasks
        simple_patterns = [
            (r'^(what is|what are)', "simple question"),
            (r'^(how to)', "simple how-to"),
            (r'^(define|definition)', "simple definition"),
            (r'^(list|show me)', "simple listing"),
        ]
        
        for pattern, reason in simple_patterns:
            if re.match(pattern, prompt_lower):
                return reason
        
        return None
    
    def _has_complex_format(self, prompt: str) -> bool:
        """Check if prompt contains complex formats that should not be flagged"""
        # ⚠️ SUPPRESSION: Complex JSON-like structures
        if re.search(r'\{"task":|"context":|"instructions":', prompt):
            return True
        
        # ⚠️ SUPPRESSION: Multi-line structured prompts
        if prompt.count('\n') > 3:
            return True
        
        # ⚠️ SUPPRESSION: Code-like content
        if re.search(r'```|def |class |import |function', prompt):
            return True
        
        return False
    
    def _extract_prompt_from_messages(self, messages: List[Dict[str, Any]]) -> str:
        """Extract prompt text from messages array"""
        if not messages:
            return ""
        
        # Extract user messages
        user_messages = [msg.get('content', '') for msg in messages if msg.get('role') == 'user']
        return ' '.join(user_messages)
    
    def _calculate_potential_savings(self, record: Dict[str, Any], current_model: str, suggested_model: str, model_pricing: Optional[Dict[str, Any]]) -> float:
        """Calculate potential savings by switching to suggested model"""
        if not model_pricing:
            return 0.0
            
        # Get current cost
        current_cost = self._calculate_estimated_cost(record, model_pricing)
        
        # Calculate cost with suggested model
        suggested_record = record.copy()
        suggested_record['model'] = suggested_model
        suggested_cost = self._calculate_estimated_cost(suggested_record, model_pricing)
        
        return max(0.0, current_cost - suggested_cost)
    
    def _calculate_estimated_cost(self, record: Dict[str, Any], model_pricing: Optional[Dict[str, Any]]) -> float:
        """📈 4. Calculate estimated cost with accurate pricing (updated for 1M token normalization)"""
        # Use existing cost if available
        if 'cost' in record and record['cost'] is not None:
            return float(record['cost'])
        
        # Extract model from record (handle both formats)
        model = record.get('model', '') or record.get('input', {}).get('model', '')
        
        # Extract usage tokens
        usage = record.get('usage', {})
        input_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0)
        
        # Calculate from pricing if available - handle both direct models dict and full config
        if model_pricing:
            # Handle both formats: direct models dict or full config with models section
            models_config = model_pricing if 'input_cost_per_1m' in model_pricing.get(model, {}) else model_pricing.get('models', {})
            model_config = models_config.get(model, {})
            
            if model_config:
                # Updated for 1M token normalization
                input_cost = (input_tokens / 1000000) * model_config.get('input_cost_per_1m', 0)
                output_cost = (output_tokens / 1000000) * model_config.get('output_cost_per_1m', 0)
                return input_cost + output_cost
        
        # Fallback estimation for common models (updated pricing)
        model = model.lower()
        
        # Updated fallback costs per 1M tokens
        if 'gpt-4' in model:
            return (input_tokens * 30.0 + output_tokens * 60.0) / 1000000
        elif 'claude-3-opus' in model:
            return (input_tokens * 15.0 + output_tokens * 75.0) / 1000000
        elif 'gpt-3.5-turbo' in model:
            return (input_tokens * 1.5 + output_tokens * 2.0) / 1000000
        
        return 0.0

def detect_expensive_model_waste(
    traces: Dict[str, List[Dict[str, Any]]],
    prompt_token_threshold: int = 50,
    completion_token_threshold: int = 100,
    min_tokens_for_gpt4: int = 100,
    model_pricing: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Detects wasteful use of expensive models for short/simple prompts.
    Only flags 'expensive_model_short' and recommends a cheaper model if appropriate.
    Handles both single-model and multi-model traces.
    """
    expensive_models = {
        'gpt-4': 'gpt-3.5-turbo',
        'gpt-4-32k': 'gpt-3.5-turbo-16k',
        'gpt-4-turbo': 'gpt-3.5-turbo',
        'claude-3-opus': 'claude-3-sonnet',
        'claude-3-sonnet': 'claude-3-haiku',
        'claude-2.1': 'claude-3-haiku',
        'claude-2.0': 'claude-3-haiku'
    }
    detections = []
    for trace_id, records in traces.items():
        for record in records:
            model = record.get('model', '').lower()
            prompt = record.get('prompt', '')
            if model in expensive_models:
                prompt_tokens = record.get('prompt_tokens', len(prompt.split()))
                if prompt_tokens < min_tokens_for_gpt4:
                    current_cost = _calculate_record_cost(record, model_pricing)
                    suggested_model = expensive_models[model]
                    cheaper_cost = _calculate_cost_with_model(record, suggested_model, model_pricing)
                    potential_savings = max(0.0, current_cost - cheaper_cost)
                    detections.append({
                        'type': 'expensive_model_short',
                        'trace_id': trace_id,
                        'severity': 'medium',
                        'description': f"{model.upper()} used for short prompt ({prompt_tokens} tokens)",
                        'waste_tokens': record.get('completion_tokens', 0),
                        'waste_cost': potential_savings,
                        'prompt_length': prompt_tokens,
                        'model_used': model,
                        'suggested_model': suggested_model,
                        'sample_prompt': prompt[:100] + '...' if len(prompt) > 100 else prompt,
                        'records': [record]
                    })
    return [d for d in detections if d is not None]

def _calculate_record_cost(record: Dict[str, Any], model_pricing: Optional[Dict[str, Any]]) -> float:
    if not model_pricing:
        return record.get('cost', 0.0)
    model = record.get('model', 'gpt-3.5-turbo')
    input_tokens = record.get('prompt_tokens', 0)
    output_tokens = record.get('completion_tokens', 0)
    if 'cost' in record and record['cost'] is not None:
        return record['cost']
    model_config = model_pricing.get(model, {})
    if model_config:
        input_cost = (input_tokens / 1000) * model_config.get('input_cost_per_1k', 0)
        output_cost = (output_tokens / 1000) * model_config.get('output_cost_per_1k', 0)
        return input_cost + output_cost
    return 0.0

def _calculate_cost_with_model(record: Dict[str, Any], new_model: str, model_pricing: Optional[Dict[str, Any]]) -> float:
    if not model_pricing:
        return 0.0
    input_tokens = record.get('prompt_tokens', 0)
    output_tokens = record.get('completion_tokens', 0)
    model_config = model_pricing.get(new_model, {})
    if model_config:
        input_cost = (input_tokens / 1000) * model_config.get('input_cost_per_1k', 0)
        output_cost = (output_tokens / 1000) * model_config.get('output_cost_per_1k', 0)
        return input_cost + output_cost
    return 0.0

# Example usage:
# issues = detect_expensive_model_waste(traces, model_pricing=...) 