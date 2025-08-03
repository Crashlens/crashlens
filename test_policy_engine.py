#!/usr/bin/env python3
"""
Simple integration test for the policy engine.
Tests the scenario: retry_count=3 GPT-4 log triggers a violation.
"""

import tempfile
import yaml
from pathlib import Path
import sys
import os

# Add the parent directory to the path so we can import crashlens
sys.path.insert(0, str(Path(__file__).parent.parent))

from crashlens.policy.engine import PolicyEngine

def test_gpt4_retry_violation():
    """Test that a GPT-4 log with retry_count=3 triggers a violation."""
    
    # Create policy file
    policy_data = {
        'rules': [
            {
                'id': 'no-gpt4-in-retries',
                'match': {
                    'model': 'gpt-4',
                    'retry_count': '>2'
                },
                'action': 'fail',
                'severity': 'high',
                'suggestion': 'Use GPT-3.5-turbo for retries or reduce fallback steps'
            }
        ]
    }
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(policy_data, f)
        policy_file = Path(f.name)
    
    try:
        # Load policy engine
        engine = PolicyEngine(policy_file)
        print(f"✅ Loaded policy with {len(engine.rules)} rules")
        
        # Test log entry that should violate the rule
        violating_log = {
            "id": "trace-abc123",
            "model": "gpt-4",
            "retry_count": 3,
            "timestamp": "2025-01-01T12:00:00Z",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150
            }
        }
        
        # Evaluate
        violations = engine.evaluate_log_entry(violating_log, line_number=1)
        
        # Verify violation occurred
        assert len(violations) == 1, f"Expected 1 violation, got {len(violations)}"
        
        violation = violations[0]
        print(f"✅ Violation detected:")
        print(f"   Rule ID: {violation.rule_id}")
        print(f"   Reason: {violation.reason}")
        print(f"   Action: {violation.action.value}")
        print(f"   Severity: {violation.severity.value}")
        print(f"   Suggestion: {violation.suggestion}")
        
        # Test non-violating log
        good_log = {
            "id": "trace-def456", 
            "model": "gpt-3.5-turbo",  # Different model
            "retry_count": 3,
            "timestamp": "2025-01-01T12:01:00Z"
        }
        
        good_violations = engine.evaluate_log_entry(good_log)
        assert len(good_violations) == 0, "Expected no violations for GPT-3.5 log"
        print("✅ No violation for GPT-3.5-turbo log (as expected)")
        
        print(f"\n🎉 Policy engine test passed! The retry_count=3 GPT-4 log correctly triggered a violation.")
        
    finally:
        # Clean up
        policy_file.unlink()

if __name__ == "__main__":
    test_gpt4_retry_violation()
