#!/usr/bin/env python3

from crashlens.parsers.langfuse import LangfuseParser
import json

# Test with sample data
test_data = '''{"traceId": "trace1", "startTime": "2025-01-01T10:00:00Z", "endTime": "2025-01-01T10:00:05Z", "input": {"model": "gpt-4"}, "usage": {"prompt_tokens": 100, "completion_tokens": 50}}
{"traceId": "trace1", "input": {"model": "gpt-4"}, "usage": {"prompt_tokens": 50, "completion_tokens": 25}}
{"traceId": "trace2", "input": {"model": "gpt-3.5-turbo"}, "usage": {"prompt_tokens": 200, "completion_tokens": 100}}'''

print("=== Testing Enhanced LangfuseParser ===")

# Test verbose mode
print("\n1. Testing with verbose=True, fail_fast=False:")
parser = LangfuseParser(verbose=True, fail_fast=False)
result = parser.parse_string(test_data)
print(f"Parsed {len(result)} traces")
print(f"Model costs: {parser.get_model_costs()}")

# Test trace summary
print("\n2. Testing trace summary:")
if "trace1" in result:
    summary = parser.get_trace_summary("trace1")
    print(f"Trace1 summary: {summary}")

# Test sorting
print("\n3. Testing sort by timestamp:")
parser.sort_by_timestamp()
print("Traces sorted by timestamp")

# Test fail_fast mode with bad data
print("\n4. Testing fail_fast mode:")
bad_data = '''{"traceId": "trace1", "input": {"model": "gpt-4"}}
{"invalid": "json"'''

parser_fail_fast = LangfuseParser(verbose=True, fail_fast=True)
try:
    parser_fail_fast.parse_string(bad_data)
except Exception as e:
    print(f"Expected error in fail_fast mode: {e}")

parser_lenient = LangfuseParser(verbose=True, fail_fast=False)
result_lenient = parser_lenient.parse_string(bad_data)
print(f"Lenient mode parsed {len(result_lenient)} traces from bad data")

print("\n=== Test Complete ===")
