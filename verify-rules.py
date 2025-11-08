import json

with open('test-output.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("\n=== Rule Evaluation Test Results ===\n")

# TEST001: Should match t1 (model=gpt-4o)
if 'TEST001' in data['rules']:
    count = data['rules']['TEST001']['count']
    print(f'✅ TEST001: Simple condition works (matched {count} trace(s))')
    assert count >= 1, "Expected at least 1 match for gpt-4o"
else:
    print('❌ TEST001: FAILED - Rule not found in output')
    exit(1)

# TEST002: Should match t1, t3 (tokens > 1000)
if 'TEST002' in data['rules']:
    count = data['rules']['TEST002']['count']
    print(f'✅ TEST002: Numeric condition works (matched {count} trace(s))')
    assert count >= 2, "Expected at least 2 matches for tokens > 1000"
else:
    print('❌ TEST002: FAILED - Rule not found in output')
    exit(1)

# TEST003: Should match t1 (model=gpt-4o AND tokens>2000)
if 'TEST003' in data['rules']:
    count = data['rules']['TEST003']['count']
    print(f'✅ TEST003: AND logic works (matched {count} trace(s))')
    assert count >= 1, "Expected at least 1 match for gpt-4o with tokens>2000"
else:
    print('❌ TEST003: FAILED - Rule not found in output')
    exit(1)

# TEST004: Should match t1, t3 (model in [gpt-4o, claude-3])
if 'TEST004' in data['rules']:
    count = data['rules']['TEST004']['count']
    print(f'✅ TEST004: OR logic works (matched {count} trace(s))')
    assert count >= 2, "Expected at least 2 matches for gpt-4o or claude-3"
else:
    print('❌ TEST004: FAILED - Rule not found in output')
    exit(1)

# TEST005: Should match t1, t3 (NOT gpt-3.5-turbo)
if 'TEST005' in data['rules']:
    count = data['rules']['TEST005']['count']
    print(f'✅ TEST005: NOT logic works (matched {count} trace(s))')
    assert count >= 2, "Expected at least 2 matches (excluding gpt-3.5-turbo)"
else:
    print('❌ TEST005: FAILED - Rule not found in output')
    exit(1)

print('\n✅ All rule evaluation tests passed!\n')
print(f"Summary: {data['summary']['total_rules']} rules, {data['summary']['total_violations']} violations")
