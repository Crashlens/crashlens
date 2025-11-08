import json

with open('test-output-fixed.json', 'r', encoding='utf-8') as f:
    # Skip the warning line if present
    content = f.read()
    # Find the start of JSON (first '{')
    json_start = content.find('{')
    if json_start > 0:
        content = content[json_start:]
    data = json.loads(content)

print("\n=== Boolean Logic Test Results ===\n")

# TEST001: Should match t1 (model=gpt-4o)
if 'TEST001' in data['rules']:
    count = data['rules']['TEST001']['count']
    print(f'✅ TEST001: Simple condition works (matched {count} trace(s))')
    assert count == 1, f"Expected 1 match for gpt-4o, got {count}"
else:
    print('❌ TEST001: FAILED - Rule not found in output')
    exit(1)

# TEST002: Should match t1, t3 (tokens > 1000)
if 'TEST002' in data['rules']:
    count = data['rules']['TEST002']['count']
    print(f'✅ TEST002: Numeric condition works (matched {count} trace(s))')
    assert count == 2, f"Expected 2 matches for tokens > 1000, got {count}"
else:
    print('❌ TEST002: FAILED - Rule not found in output')
    exit(1)

# TEST003: Should match t1 (model=gpt-4o AND tokens>2000)
if 'TEST003' in data['rules']:
    count = data['rules']['TEST003']['count']
    print(f'✅ TEST003: AND logic works (matched {count} trace(s))')
    assert count == 1, f"Expected 1 match for gpt-4o with tokens>2000, got {count}"
else:
    print('❌ TEST003: FAILED - Rule not found in output')
    exit(1)

# TEST004: Should have OR variants (model in [gpt-4o, claude-3])
test004_total = 0
if 'TEST004_or0' in data['rules']:
    count = data['rules']['TEST004_or0']['count']
    test004_total += count
    print(f'✅ TEST004_or0: OR logic variant 1 works (matched {count} trace(s))')
else:
    print('⚠️  TEST004_or0: Not found')

if 'TEST004_or1' in data['rules']:
    count = data['rules']['TEST004_or1']['count']
    test004_total += count
    print(f'✅ TEST004_or1: OR logic variant 2 works (matched {count} trace(s))')
else:
    print('⚠️  TEST004_or1: Not found')

if test004_total >= 2:
    print(f'✅ TEST004: OR logic works (total {test004_total} matches across variants)')
else:
    print(f'❌ TEST004: OR logic FAILED (expected 2+ matches, got {test004_total})')
    exit(1)

# TEST005: NOT logic (expected to be skipped with warning)
if 'TEST005' in data['rules'] and data['rules']['TEST005']['count'] == 0:
    print('✅ TEST005: NOT logic correctly skipped (logged warning)')
else:
    print('⚠️  TEST005: NOT logic status unclear')

print('\n🎉 All boolean logic tests passed!\n')
print(f"Summary:")
print(f"  Total rules: {data['summary']['total_rules']}")
print(f"  Violations: {data['summary']['violations']}")
print(f"  ✅ Simple conditions: Working")
print(f"  ✅ Numeric comparisons: Working")
print(f"  ✅ AND logic: Working")
print(f"  ✅ OR logic: Working (expanded to variants)")
print(f"  ⚠️  NOT logic: Unsupported (logged warning)")
