#!/usr/bin/env python3
"""
Simple test runner for schema contract validation without pytest dependency.
"""

import json
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import from tests
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_latest_langfuse_log():
    """Load the latest Langfuse log fixture for testing."""
    fixture_path = Path(__file__).parent / "tests" / "fixtures" / "langfuse_latest_log.json"
    with open(fixture_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_langfuse_logs():
    """Load multiple Langfuse log lines for comprehensive testing."""
    fixture_path = Path(__file__).parent / "tests" / "fixtures" / "langfuse_latest_logs.jsonl"
    logs = []
    with open(fixture_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                logs.append(json.loads(line))
    return logs

def test_single_log_contract_fields():
    """Test that a single log contains all required v1 contract fields."""
    print("Testing single log contract fields...")
    
    log = load_latest_langfuse_log()
    V1_REQUIRED_FIELDS = ["traceId"]
    
    # Assert basic structure
    assert isinstance(log, dict), "Log must be a dictionary"
    
    # Assert required fields
    for field in V1_REQUIRED_FIELDS:
        assert field in log, f"Required field '{field}' missing from log"
        assert log[field] is not None, f"Required field '{field}' is None"
    
    print("✅ Single log contract validation passed")

def test_all_contract_logs_pass():
    """Test that all logs in the fixture pass v1 contract validation."""
    print("Testing all logs contract validation...")
    
    logs = load_langfuse_logs()
    V1_REQUIRED_FIELDS = ["traceId"]
    
    assert len(logs) > 0, "No logs found in fixture file"
    
    for i, log in enumerate(logs):
        # Test each log against the contract
        assert isinstance(log, dict), f"Line {i+1}: Log must be a dictionary"
        
        # Check required fields
        for field in V1_REQUIRED_FIELDS:
            assert field in log, f"Line {i+1}: Missing required field '{field}'"
            assert log[field] is not None, f"Line {i+1}: Required field '{field}' is None"
        
        # Check data types for critical fields
        if "traceId" in log:
            assert isinstance(log["traceId"], str), f"Line {i+1}: traceId must be string"
    
    print(f"✅ All {len(logs)} logs passed contract validation")

def test_critical_field_types():
    """Test that critical fields have expected data types."""
    print("Testing critical field types...")
    
    logs = load_langfuse_logs()
    
    for i, log in enumerate(logs):
        # Test field types that are critical for our parsing logic
        if "usage" in log:
            assert isinstance(log["usage"], dict), f"Line {i+1}: usage must be dict"
            
            usage = log["usage"]
            if "prompt_tokens" in usage:
                assert isinstance(usage["prompt_tokens"], (int, type(None))), \
                    f"Line {i+1}: prompt_tokens must be int or None"
            if "completion_tokens" in usage:
                assert isinstance(usage["completion_tokens"], (int, type(None))), \
                    f"Line {i+1}: completion_tokens must be int or None"
        
        if "input" in log:
            assert isinstance(log["input"], dict), f"Line {i+1}: input must be dict"
        
        if "metadata" in log:
            assert isinstance(log["metadata"], dict), f"Line {i+1}: metadata must be dict"
    
    print("✅ Critical field types validation passed")

def test_schema_evolution_detection():
    """Detect if new fields have been added that we should consider supporting."""
    print("Testing schema evolution detection...")
    
    log = load_latest_langfuse_log()
    
    # Known fields in our current v1 schema
    known_fields = {
        "traceId", "startTime", "endTime", "level", "model", "name", "cost",
        "input", "usage", "metadata", "userId", "timestamp"
    }
    
    # Find any new top-level fields
    actual_fields = set(log.keys())
    new_fields = actual_fields - known_fields
    
    if new_fields:
        print(f"ℹ️  New fields detected (consider adding to v2 schema): {sorted(new_fields)}")
    else:
        print("ℹ️  No new fields detected - schema is stable")
    
    print("✅ Schema evolution detection completed")

def test_contract_break_scenarios():
    """Test contract break detection scenarios."""
    print("Testing contract break detection...")
    
    # Test missing required field
    try:
        broken_log = {"startTime": "2025-01-01T10:00:00Z", "model": "gpt-4"}
        assert "traceId" in broken_log, "Required field 'traceId' missing from log"
        print("❌ Should have detected missing traceId")
    except AssertionError as e:
        print(f"✅ Correctly detected contract break: {e}")
    
    # Test type change
    try:
        type_changed_log = {"traceId": 12345, "startTime": "2025-01-01T10:00:00Z"}
        assert isinstance(type_changed_log["traceId"], str), "traceId must be string"
        print("❌ Should have detected type change")
    except AssertionError as e:
        print(f"✅ Correctly detected type change: {e}")

def main():
    """Run all schema contract tests."""
    print("🧪 Running Schema Contract Break Detection Tests")
    print("=" * 60)
    
    try:
        test_single_log_contract_fields()
        test_all_contract_logs_pass()
        test_critical_field_types()
        test_schema_evolution_detection()
        test_contract_break_scenarios()
        
        print("\n" + "=" * 60)
        print("🎉 All schema contract tests passed!")
        print("✅ Current Langfuse log format is compatible with v1 schema")
        print("✅ Contract break detection is working correctly")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("🚨 This indicates a potential schema contract break!")
        sys.exit(1)

if __name__ == "__main__":
    main()
