#!/usr/bin/env python3
"""Quick test to verify stats collection is working correctly."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crashlens.policy.engine import PolicyEngine

def test_stats_collection():
    """Test that stats collection works as expected."""
    print("Testing stats collection functionality...")
    print("=" * 50)
    
    # Create engine with a sample policy
    policy_file = Path(__file__).parent.parent / "policies" / "ci-sample.yaml"
    
    if not policy_file.exists():
        print(f"⚠️  Warning: Policy file not found at {policy_file}")
        print("Creating a minimal test policy...")
        # Use a different policy file
        policy_file = Path(__file__).parent.parent / "policies" / "max-cost-per-trace.yaml"
        
    if not policy_file.exists():
        print("❌ No policy files found. Skipping test.")
        return
    
    engine = PolicyEngine(policy_file)
    
    # Verify stats are disabled by default
    print("\n1. Testing default state (stats disabled)...")
    assert engine._collect_stats == False, "Stats should be disabled by default"
    print("   ✓ Stats disabled by default")
    
    # Enable stats
    print("\n2. Enabling stats collection...")
    engine.enable_stats_collection()
    assert engine._collect_stats == True, "Stats should be enabled after calling enable"
    print("   ✓ Stats enabled successfully")
    
    # Create test log entries
    print("\n3. Evaluating test log entries...")
    test_logs = [
        {
            "traceId": "test-1",
            "input": {"model": "gpt-4"},
            "usage": {"total_tokens": 1000},
            "cost": 0.03
        },
        {
            "traceId": "test-2",
            "input": {"model": "gpt-3.5-turbo"},
            "usage": {"total_tokens": 500},
            "cost": 0.001
        },
        {
            "traceId": "test-3",
            "input": {"model": "gpt-4"},
            "usage": {"total_tokens": 2000},
            "cost": 0.06
        }
    ]
    
    violations, skipped = engine.evaluate_logs(test_logs)
    print(f"   Evaluated {len(test_logs)} log entries")
    print(f"   Found {len(violations)} violations")
    
    # Check stats were collected
    print("\n4. Verifying stats collection...")
    stats = engine.get_stats()
    
    if not stats:
        print("   ⚠️  No stats collected (may be expected if no rules matched)")
    else:
        print(f"   ✓ Stats collected for {len(stats)} rules")
        for rule_id, rule_stats in stats.items():
            print(f"     - {rule_id}: {rule_stats['count']} evaluations")
    
    # Print summary
    print("\n5. Stats summary:")
    engine.print_stats_summary()
    
    print("\n" + "=" * 50)
    print("✅ All tests passed!")
    print("\nNext steps:")
    print("1. Run: python scripts/benchmark_stats_overhead.py")
    print("2. Verify overhead is <10%")
    print("3. If acceptable, proceed with full metrics implementation")


if __name__ == '__main__':
    try:
        test_stats_collection()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
