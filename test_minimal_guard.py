#!/usr/bin/env python3
"""Minimal test to debug guard"""

import json
from pathlib import Path
from click.testing import CliRunner
from crashlens.cli import cli

def test_guard_minimal(tmp_path):
    """Minimal reproduction of guard test"""
    # Create log
    logs = tmp_path / "logs.jsonl"
    logs.write_text(json.dumps({
        "traceId": "trace-1",
        "startTime": "2025-01-01T10:00:00Z",
        "input": {"model": "gpt-4o", "prompt": "test"},
        "usage": {"prompt_tokens": 3000, "completion_tokens": 150, "total_tokens": 3150},
        "cost": 0.30
    }), encoding="utf-8")
    
    # Create rules
    rules = tmp_path / "rules.yaml"
    rules.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      usage.prompt_tokens:
        ">": 2000
    action: fail_ci
    severity: fatal
""", encoding="utf-8")
    
    # Run guard
    runner = CliRunner()
    result = runner.invoke(cli, [
        "guard",
        str(logs),
        "--rules", str(rules),
        "--output", "json"
    ])
    
    print("Exit code:", result.exit_code)
    print("Output:", result.output)
    print("Exception:", result.exception)
    if result.exception:
        import traceback
        traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        test_guard_minimal(Path(tmpdir))
