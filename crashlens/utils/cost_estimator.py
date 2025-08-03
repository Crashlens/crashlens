"""
Cost estimation utilities for CrashLens
Calculates token-based costs for different LLM models
"""

from typing import Optional


def estimate_cost(input_tokens: int, output_tokens: int, model_name: str) -> float:
    """
    Estimate cost based on token usage and model name
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens  
        model_name: Name of the model (e.g., 'gpt-4', 'gpt-3.5-turbo')
        
    Returns:
        Estimated cost in INR (₹)
    """
    # Fixed rates in INR per 1K tokens
    MODEL_RATES = {
        'gpt-4': {
            'input': 0.03,   # ₹0.03 per 1K input tokens
            'output': 0.06   # ₹0.06 per 1K output tokens
        },
        'gpt-4-32k': {
            'input': 0.06,
            'output': 0.12
        },
        'gpt-3.5-turbo': {
            'input': 0.006,  # ₹0.006 per 1K input tokens
            'output': 0.012  # ₹0.012 per 1K output tokens
        },
        'gpt-3.5-turbo-16k': {
            'input': 0.012,
            'output': 0.024
        }
    }
    
    # Normalize model name
    model_key = model_name.lower()
    if model_key not in MODEL_RATES:
        # Default to GPT-3.5 rates for unknown models
        model_key = 'gpt-3.5-turbo'
    
    rates = MODEL_RATES[model_key]
    
    # Calculate cost
    input_cost = (input_tokens / 1000) * rates['input']
    output_cost = (output_tokens / 1000) * rates['output']
    
    return input_cost + output_cost


def format_cost(cost: float) -> str:
    """Format cost in INR with appropriate precision"""
    if cost >= 1:
        return f"₹{cost:.2f}"
    elif cost >= 0.01:
        return f"₹{cost:.3f}"
    else:
        return f"₹{cost:.4f}"
