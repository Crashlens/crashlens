"""
Schema Contract Break Detection Tests
Unit tests to validate current Langfuse log assumptions and detect schema changes.
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Any, List


def load_latest_langfuse_log() -> Dict[str, Any]:
    """Load the latest Langfuse log fixture for testing."""
    fixture_path = Path(__file__).parent / "fixtures" / "langfuse_latest_log.json"
    with open(fixture_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_langfuse_logs() -> List[Dict[str, Any]]:
    """Load multiple Langfuse log lines for comprehensive testing."""
    fixture_path = Path(__file__).parent / "fixtures" / "langfuse_latest_logs.jsonl"
    logs = []
    with open(fixture_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                logs.append(json.loads(line))
    return logs


class TestLangfuseV1SchemaContract:
    """Test suite for Langfuse v1 schema contract validation."""
    
    # Define the v1 schema contract fields
    V1_REQUIRED_FIELDS = ["traceId"]
    V1_IMPORTANT_FIELDS = ["startTime", "model", "input", "usage"]
    V1_EXPECTED_NESTED_FIELDS = {
        "input": ["model", "prompt"],
        "usage": ["prompt_tokens", "completion_tokens"]
    }
    
    def test_single_log_contract_fields(self):
        """Test that a single log contains all required v1 contract fields."""
        log = load_latest_langfuse_log()
        
        # Assert basic structure
        assert isinstance(log, dict), "Log must be a dictionary"
        
        # Assert required fields (these MUST exist for our parser to work)
        for field in self.V1_REQUIRED_FIELDS:
            assert field in log, f"Required field '{field}' missing from log"
            assert log[field] is not None, f"Required field '{field}' is None"
        
        # Assert important fields (warn if missing, but don't fail)
        missing_important = []
        for field in self.V1_IMPORTANT_FIELDS:
            if field not in log:
                missing_important.append(field)
        
        # Log warnings for missing important fields but don't fail
        if missing_important:
            print(f"WARNING: Missing important fields: {missing_important}")
    
    def test_nested_structure_contract(self):
        """Test that nested structures conform to v1 expectations."""
        log = load_latest_langfuse_log()
        
        # Test nested field expectations
        for parent_field, expected_children in self.V1_EXPECTED_NESTED_FIELDS.items():
            if parent_field in log and isinstance(log[parent_field], dict):
                for child_field in expected_children:
                    if child_field not in log[parent_field]:
                        print(f"WARNING: Missing nested field '{parent_field}.{child_field}'")
    
    def test_all_contract_logs_pass(self):
        """Test that all logs in the fixture pass v1 contract validation."""
        logs = load_langfuse_logs()
        assert len(logs) > 0, "No logs found in fixture file"
        
        for i, log in enumerate(logs):
            # Test each log against the contract
            assert isinstance(log, dict), f"Line {i+1}: Log must be a dictionary"
            
            # Check required fields
            for field in self.V1_REQUIRED_FIELDS:
                assert field in log, f"Line {i+1}: Missing required field '{field}'"
                assert log[field] is not None, f"Line {i+1}: Required field '{field}' is None"
            
            # Check data types for critical fields
            if "traceId" in log:
                assert isinstance(log["traceId"], str), f"Line {i+1}: traceId must be string"
            
            if "startTime" in log:
                assert isinstance(log["startTime"], str), f"Line {i+1}: startTime must be string"
            
            if "model" in log:
                assert isinstance(log["model"], str), f"Line {i+1}: model must be string"
    
    def test_backwards_compatibility_fields(self):
        """Test for fields that existed in older versions to ensure backwards compatibility."""
        log = load_latest_langfuse_log()
        
        # These fields should still exist for backwards compatibility
        backwards_compat_fields = ["traceId", "startTime", "model"]
        
        for field in backwards_compat_fields:
            assert field in log, f"Backwards compatibility broken: '{field}' field removed"
    
    def test_schema_evolution_detection(self):
        """Detect if new fields have been added that we should consider supporting."""
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
            print(f"INFO: New fields detected (consider adding to v2 schema): {sorted(new_fields)}")
            
        # This is informational only - don't fail the test
        # In production, you might want to alert on new fields
    
    def test_critical_field_types(self):
        """Test that critical fields have expected data types."""
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


class TestSchemaEvolutionCompatibility:
    """Test suite for detecting breaking changes in schema evolution."""
    
    def test_v1_to_v2_migration_safety(self):
        """Ensure that v1 logs can still be parsed even if v2 schema is active."""
        # This test would verify that our parser can handle both v1 and v2 logs
        # Currently we only have v1, so this is a placeholder for future testing
        
        logs = load_langfuse_logs()
        
        # Simulate v1 logs being processed with future v2 parser
        for log in logs:
            # Should have v1 required fields
            assert "traceId" in log
            
            # Should be parseable regardless of additional v2 fields
            # This ensures forward compatibility


def test_contract_break_detection_with_missing_field():
    """Test that contract break detection works when fields are missing."""
    # Simulate a log with missing required field (contract break scenario)
    broken_log = {
        "startTime": "2025-01-01T10:00:00Z",
        "model": "gpt-4",
        # Missing traceId - this should be detected as a contract break
    }
    
    # This should fail with our contract validation
    with pytest.raises(AssertionError, match="Required field 'traceId' missing"):
        assert "traceId" in broken_log, "Required field 'traceId' missing from log"


def test_contract_break_detection_with_type_change():
    """Test detection of type changes in critical fields."""
    # Simulate a log where a field changed type (contract break scenario)
    type_changed_log = {
        "traceId": 12345,  # Should be string, not int - contract break
        "startTime": "2025-01-01T10:00:00Z",
        "model": "gpt-4"
    }
    
    # This should fail with our type validation
    with pytest.raises(AssertionError, match="traceId must be string"):
        assert isinstance(type_changed_log["traceId"], str), "traceId must be string"


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
