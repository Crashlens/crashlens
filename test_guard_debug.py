#!/usr/bin/env python3
"""Debug script to test guard processing"""

import json
from pathlib import Path
from crashlens.guard_adapter import GuardPolicyEngineAdapter

# Use the existing test files
test_log = Path("test_simple.jsonl")
test_rules = Path("test_simple_rules.yaml")

print("Test log exists:", test_log.exists())
print("Test rules exists:", test_rules.exists())
print()

# Test adapter with verbose=True to see what's happening
adapter = GuardPolicyEngineAdapter(
    rules_yaml_path=test_rules,
    detector_mode="none",
    verbose=True  # Enable verbose logging
)

print("Adapter initialized:", adapter.is_enabled())
print()

violations, metrics = adapter.process_logs([test_log])

print(f"\nMetrics: {metrics}")
print(f"Violations: {len(violations)}")
for rule_id, viols in violations.items():
    print(f"  {rule_id}: {len(viols)} violations")
    for v in viols:
        print(f"    - Line {v.line_number}: {v.reason}")
