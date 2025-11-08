#!/usr/bin/env python3
from crashlens.policy.engine import PolicyMatcher

# Test metadata.retry_count matching
entry1 = {'metadata': {'retry_count': 5}}
value1 = PolicyMatcher._get_nested_value(entry1, 'metadata.retry_count')
print(f'Got retry_count value: {value1}, type: {type(value1)}')
result1 = PolicyMatcher.match_condition(value1, '>2')
print(f'retry_count=5 > 2: {result1}')
print()

# Test metadata.fallback_triggered matching
entry2 = {'metadata': {'fallback_triggered': True}}
value2 = PolicyMatcher._get_nested_value(entry2, 'metadata.fallback_triggered')
print(f'Got fallback_triggered value: {value2}, type: {type(value2)}')
result2 = PolicyMatcher.match_condition(value2, '==true')
print(f'fallback_triggered==true: {result2}')
result3 = PolicyMatcher.match_condition(value2, True)
print(f'fallback_triggered==True (boolean): {result3}')
print()

# Test input.prompt matching
entry3 = {'input': {'prompt': 'test@example.com'}}
value3 = PolicyMatcher._get_nested_value(entry3, 'input.prompt')
print(f'Got prompt value: {value3}')
result4 = PolicyMatcher.match_condition(value3, 'regex:@')
print(f'prompt regex @: {result4}')
