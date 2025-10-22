#!/usr/bin/env python3
"""Memory profiling script for PolicyEngine stats collection.

Tests memory usage with and without stats collection to ensure
overhead is minimal and scales with rules, not log entries.
"""

import sys
import yaml
import tempfile
from pathlib import Path
from memory_profiler import profile

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from crashlens.policy.engine import PolicyEngine


def create_policy_file(num_rules: int = 10):
    """Create a temporary policy file with specified number of rules."""
    rules = []
    for i in range(num_rules):
        rules.append({
            'id': f'rule_{i+1}',
            'description': f'Test rule {i+1}',
            'match': {
                'model': f'gpt-4' if i % 2 == 0 else f'gpt-3.5-turbo',
                'prompt_tokens': f'>{100 * (i+1)}'
            },
            'action': 'warn',
            'severity': 'medium',
            'suggestion': f'Optimize for rule {i+1}'
        })
    
    policy = {
        'version': 1,
        'global': {'max_violations_per_rule': 100},
        'rules': rules
    }
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8')
    yaml.dump(policy, temp_file)
    temp_file.close()
    return Path(temp_file.name)


def create_sample_logs(count: int = 10000):
    """Create sample log entries for testing."""
    logs = []
    for i in range(count):
        logs.append({
            'traceId': f'trace_{i}',
            'model': 'gpt-4' if i % 3 == 0 else 'gpt-3.5-turbo',
            'prompt_tokens': 500 + (i % 1000),
            'completion_tokens': 200,
            'cost': 0.001 * (i % 20),
            'metadata': {
                'fallback_attempted': i % 5 == 0
            },
            'retry_count': i % 5
        })
    return logs


@profile
def test_baseline_memory(num_logs: int, num_rules: int):
    """Test memory usage without stats collection."""
    policy_file = create_policy_file(num_rules)
    logs = create_sample_logs(num_logs)
    
    try:
        engine = PolicyEngine(policy_file)
        # Stats collection disabled by default
        violations, warnings = engine.evaluate_logs(logs)
        print(f"Baseline: {len(violations)} violations found")
    finally:
        policy_file.unlink(missing_ok=True)


@profile
def test_stats_memory(num_logs: int, num_rules: int):
    """Test memory usage with stats collection enabled."""
    policy_file = create_policy_file(num_rules)
    logs = create_sample_logs(num_logs)
    
    try:
        engine = PolicyEngine(policy_file)
        engine.enable_stats_collection()
        violations, warnings = engine.evaluate_logs(logs)
        print(f"With stats: {len(violations)} violations found")
        
        # Print stats summary
        stats = engine.get_stats()
        print(f"Collected stats for {len(stats)} rules")
        
    finally:
        policy_file.unlink(missing_ok=True)


if __name__ == '__main__':
    print("=" * 70)
    print("Memory Profiling: PolicyEngine Stats Collection")
    print("=" * 70)
    print("\nTest Configuration:")
    print("  - Log entries: 10,000")
    print("  - Policy rules: 10")
    print("  - Expected stats memory: ~400 bytes (5 floats × 8 bytes × 10 rules)")
    print("\n" + "=" * 70)
    
    print("\n[1/2] Profiling BASELINE (stats disabled)...")
    print("-" * 70)
    test_baseline_memory(num_logs=10000, num_rules=10)
    
    print("\n" + "=" * 70)
    print("[2/2] Profiling WITH STATS (stats enabled)...")
    print("-" * 70)
    test_stats_memory(num_logs=10000, num_rules=10)
    
    print("\n" + "=" * 70)
    print("ANALYSIS:")
    print("  - Check 'Increment' column for memory differences")
    print("  - Expected overhead: < 100MB (should be < 1MB)")
    print("  - Memory should scale with rules (10), not logs (10,000)")
    print("=" * 70)
