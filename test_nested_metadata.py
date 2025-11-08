#!/usr/bin/env python3
import json
import yaml
from pathlib import Path
from crashlens.guard_adapter import GuardPolicyEngineAdapter

# Create test log with nested metadata
log_entry = {
    "traceId": "trace-1",
    "startTime": "2025-01-01T10:00:00Z",
    "input": {"model": "gpt-4o", "prompt": "test"},
    "usage": {"prompt_tokens": 3000, "completion_tokens": 150, "total_tokens": 3150},
    "cost": 0.30,
    "metadata": {"retry_count": 5, "fallback_triggered": False, "endpoint": "/api"}
}

log_file = Path("test_nested.jsonl")
with open(log_file, 'w') as f:
    json.dump(log_entry, f)

# Create guard rules
rules_content = """
rules:
  - id: RL002
    description: "Many retries"
    if:
      metadata.retry_count:
        ">": 2
    action: error
    severity: error
"""

rules_file = Path("test_nested_rules.yaml")
with open(rules_file, 'w') as f:
    f.write(rules_content)

# Test adapter
adapter = GuardPolicyEngineAdapter(
    rules_yaml_path=rules_file,
    detector_mode="none",
    verbose=True
)

print("Testing adapter with nested metadata...")
violations, metrics = adapter.process_logs([log_file])

print(f"\nMetrics: {metrics}")
print(f"Violations: {violations}")

# Check what the adapter converted the rules to
import tempfile
with open(adapter.rules_yaml_path, 'r') as f:
    guard_rules = yaml.safe_load(f)

policy_rules = adapter._convert_guard_rules_to_policy_format(guard_rules.get('rules', []))
print(f"\nConverted policy rules:")
for rule in policy_rules:
    print(f"  {rule['id']}: {rule['match']}")

# Clean up
log_file.unlink()
rules_file.unlink()
