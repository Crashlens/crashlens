#!/usr/bin/env python3

from crashlens.parsers.langfuse import LangfuseParser, InvalidTraceError

print("=== Comprehensive Schema Contract Test ===")

# Test 1: Default v1 schema validation
print("\n1. Testing default v1 schema:")
parser = LangfuseParser(verbose=True)
print(f"Default schema: {parser.default_schema}")
print(f"Available versions: {parser.get_available_schema_versions()}")
print(f"v1 contract valid: {parser.validate_schema_contract('v1')}")

# Test 2: Adding and validating a v2 schema  
print("\n2. Adding custom v2 schema:")
parser.add_schema_contract(
    version="v2",
    required_fields=["traceId", "userId"],
    warn_fields=["model", "cost"],
    all_known_fields={"traceId", "userId", "model", "cost", "timestamp", "duration_sec"}
)
print(f"v2 contract valid: {parser.validate_schema_contract('v2')}")

# Test 3: Invalid schema contract
print("\n3. Testing invalid schema contract:")
parser.add_schema_contract(
    version="invalid",
    required_fields=["traceId", "nonexistent_field"],  # This field not in all_known_fields
    warn_fields=["model"],
    all_known_fields={"traceId", "model"}
)
print(f"Invalid contract valid: {parser.validate_schema_contract('invalid')}")

# Test 4: Parse with different schema versions
print("\n4. Testing parsing with different schema versions:")

# Create parser with v2 as default
parser_v2 = LangfuseParser(verbose=True, default_schema="v2")
parser_v2.add_schema_contract(
    version="v2", 
    required_fields=["traceId", "userId"],
    warn_fields=["model"],
    all_known_fields={"traceId", "userId", "model", "cost"}
)

# Data that satisfies v2 requirements
test_data_v2_valid = '{"traceId": "trace1", "userId": "user123", "model": "gpt-4"}'
# Data missing userId (required in v2)
test_data_v2_invalid = '{"traceId": "trace1", "model": "gpt-4"}'

print("Parsing valid v2 data:")
try:
    result = parser_v2.parse_string(test_data_v2_valid)
    print(f"Success: {len(result)} traces parsed")
except Exception as e:
    print(f"Error: {e}")

print("Parsing invalid v2 data (missing userId):")
try:
    result = parser_v2.parse_string(test_data_v2_invalid)
    print(f"Success: {len(result)} traces parsed")
except Exception as e:
    print(f"Error: {e}")

# Test 5: Unknown fields detection
print("\n5. Testing unknown field detection:")
test_data_unknown = '{"traceId": "trace1", "userId": "user123", "model": "gpt-4", "unknown_field": "value", "another_unknown": {"nested": "data"}}'
result = parser_v2.parse_string(test_data_unknown)
print(f"Parsed {len(result)} traces with unknown fields")

print("\n=== Schema Contract Test Complete ===")
