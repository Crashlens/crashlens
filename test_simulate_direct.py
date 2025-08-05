#!/usr/bin/env python3
"""
Test CrashLens simulation directly (no requests dependency)
"""

import json
import os
from pathlib import Path

def mock_generate_simulation_report(violations, log_file):
    """Mock version of generate_simulation_report"""
    print(f"🎯 SIMULATION MODE: Policy violations for {log_file}")
    print("=" * 50)
    
    # Group violations by severity
    critical = [v for v in violations if v.get('severity') == 'critical']
    medium = [v for v in violations if v.get('severity') == 'medium']
    low = [v for v in violations if v.get('severity') in ['low', 'warning']]
    
    print(f"📊 Violation Summary:")
    print(f"   🔴 Critical: {len(critical)} violations")
    print(f"   🟡 Medium:   {len(medium)} violations") 
    print(f"   🟢 Low:      {len(low)} violations")
    print(f"   📋 Total:    {len(violations)} violations")
    
    if violations:
        print(f"\n🔍 Sample violations:")
        for i, violation in enumerate(violations[:3]):
            rule_id = violation.get('rule_id', 'unknown')
            severity = violation.get('severity', 'unknown')
            description = violation.get('description', 'No description')
            print(f"   {i+1}. [{severity.upper()}] {rule_id}")
            print(f"      {description}")
    
    print(f"\n✅ SIMULATION COMPLETE - No changes made to production")
    return violations

def test_simulate_feature():
    """Test the simulation logic"""
    print("🧪 Testing CrashLens --simulate feature")
    print("=" * 40)
    
    # Mock violation data (what might come from policy engine)
    mock_violations = [
        {
            "rule_id": "retry_limit_exceeded",
            "severity": "medium",
            "description": "Request exceeded maximum retry count (3 retries found)",
            "trace_id": "trace_123",
            "suggestion": "Implement exponential backoff"
        },
        {
            "rule_id": "expensive_model_simple_task", 
            "severity": "medium",
            "description": "GPT-4 used for simple 20-token prompt",
            "trace_id": "trace_456",
            "suggestion": "Consider gpt-3.5-turbo for simple tasks"
        },
        {
            "rule_id": "high_cost_request_block",
            "severity": "critical", 
            "description": "Request cost $0.15 exceeds limit ($0.10)",
            "trace_id": "trace_789",
            "suggestion": "Use cheaper model or optimize prompt"
        }
    ]
    
    # Test simulation report generation
    mock_generate_simulation_report(mock_violations, "test-logs.jsonl")
    
    print(f"\n🎯 Simulation Benefits:")
    print(f"   ✓ Safe policy testing without production impact")
    print(f"   ✓ Validate rule effectiveness before enforcement")
    print(f"   ✓ Estimate violation rates and cost impacts")
    print(f"   ✓ Preview enforcement actions and suggestions")

if __name__ == "__main__":
    test_simulate_feature()
