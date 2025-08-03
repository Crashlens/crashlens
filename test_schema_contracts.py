#!/usr/bin/env python3

from crashlens.parsers.langfuse import LangfuseParser, InvalidTraceError
import json

print("=== Testing Schema Contract Functionality ===")

# Test data with various scenarios
test_data_valid = '{"traceId": "trace1", "input": {"model": "gpt-4"}, "usage": {"prompt_tokens": 100, "completion_tokens": 50}}'
test_data_missing_required = '{"input": {"model": "gpt-4"}, "usage": {"prompt_tokens": 100, "completion_tokens": 50}}'
test_data_missing_optional = '{"traceId": "trace2", "input": {}, "usage": {}}'
test_data_unknown_fields = '{"traceId": "trace3", "input": {"model": "gpt-4"}, "usage": {"prompt_tokens": 100}, "custom_field": "value", "nested": {"unknown": "data"}}'

print("\n1. Testing valid record with v1 schema:")
parser = LangfuseParser(verbose=True, fail_fast=False)
result = parser.parse_string(test_data_valid)
print(f"Parsed {len(result)} traces successfully")

print("\n2. Testing missing required field (traceId):")
try:
    parser_strict = LangfuseParser(verbose=True, fail_fast=True)
    result = parser_strict.parse_string(test_data_missing_required)
except Exception as e:
    print(f"Expected error: {e}")

print("\n3. Testing lenient mode with missing required field:")
parser_lenient = LangfuseParser(verbose=True, fail_fast=False)
result = parser_lenient.parse_string(test_data_missing_required)
print(f"Lenient mode parsed {len(result)} traces")

print("\n4. Testing missing optional fields (warnings):")
result = parser_lenient.parse_string(test_data_missing_optional)
print(f"Parsed {len(result)} traces with warnings")

print("\n5. Testing unknown fields detection:")
result = parser_lenient.parse_string(test_data_unknown_fields)
print(f"Parsed {len(result)} traces, unknown fields logged")

print("\n6. Testing schema contract management:")
print(f"Available schema versions: {parser.get_available_schema_versions()}")

# Add a custom v2 schema
parser.add_schema_contract(
    version="v2",
    required_fields=["traceId", "userId"],
    warn_fields=["model", "cost"],
    all_known_fields={"traceId", "userId", "model", "cost", "timestamp"}
)
print(f"After adding v2: {parser.get_available_schema_versions()}")

print("\n7. Testing v2 schema validation:")
test_data_v2 = '{"traceId": "trace4", "userId": "user123", "model": "gpt-4", "cost": 0.01}'
# Note: This would need _normalize_v2 method implementation to actually use v2 schema
result = parser.parse_string(test_data_v2)  # Still uses v1 for now
print(f"Parsed {len(result)} traces with v2 schema contract defined")

print("\n=== Schema Contract Test Complete ===")
