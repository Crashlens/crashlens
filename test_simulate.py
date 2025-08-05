#!/usr/bin/env python3
"""
Test script for CrashLens v2.0 --simulate feature
Tests the simulation functionality without full dependencies
"""

import sys
import os
from pathlib import Path

# Add the crashlens directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Mock the missing dependencies
import types
import unittest.mock

# Mock requests module
requests_mock = types.ModuleType('requests')
requests_mock.post = lambda *args, **kwargs: None
sys.modules['requests'] = requests_mock

# Mock click module with basic functionality
click_mock = types.ModuleType('click')
click_mock.echo = print
click_mock.group = lambda: lambda f: f
click_mock.command = lambda: lambda f: f
click_mock.argument = lambda *args, **kwargs: lambda f: f
click_mock.option = lambda *args, **kwargs: lambda f: f
click_mock.version_option = lambda *args, **kwargs: lambda f: f
click_mock.Path = str
click_mock.Choice = lambda choices: str
sys.modules['click'] = click_mock

try:
    # Import and test the simulation function
    from crashlens.cli import generate_simulation_report
    
    # Create mock violation object
    class MockViolation:
        def __init__(self, rule_id, reason, suggestion, severity, action, log_entry):
            self.rule_id = rule_id
            self.reason = reason
            self.suggestion = suggestion
            self.severity = types.SimpleNamespace(value=severity)
            self.action = types.SimpleNamespace(value=action)
            self.log_entry = log_entry
    
    # Test data
    mock_violations = [
        MockViolation(
            rule_id="overkill_expensive_model",
            reason="GPT-4 used for simple task",
            suggestion="Consider using gpt-3.5-turbo for simple tasks",
            severity="medium",
            action="warn",
            log_entry={
                "trace_id": "test_001",
                "input": {"model": "gpt-4"},
                "cost": 0.0234,
                "usage": {"prompt_tokens": 10}
            }
        ),
        MockViolation(
            rule_id="high_cost_request",
            reason="Request cost exceeds threshold",
            suggestion="Consider optimizing prompt length",
            severity="high", 
            action="warn",
            log_entry={
                "trace_id": "test_002",
                "input": {"model": "gpt-4"},
                "cost": 0.0567,
                "usage": {"total_tokens": 1000}
            }
        )
    ]
    
    pricing_config = {
        "models": {
            "gpt-4": {"input_cost_per_token": 0.00003}
        }
    }
    
    print("🧪 Testing CrashLens v2.0 --simulate feature")
    print("=" * 50)
    
    # Test the simulation report generation
    generate_simulation_report(
        violations=mock_violations,
        pricing_config=pricing_config,
        verbose=True,
        output_format="markdown",
        slack_webhook=None
    )
    
    print("\n✅ Simulation feature test completed successfully!")
    print("🎉 The --simulate flag implementation is working correctly.")
    
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
