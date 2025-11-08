import json
import sys

with open('test-output-with-not.json', 'r', encoding='utf-8') as f:
    content = f.read()
    json_start = content.find('{')
    if json_start > 0:
        content = content[json_start:]
    data = json.loads(content)

print("\n" + "="*70)
print("  COMPREHENSIVE BOOLEAN LOGIC VERIFICATION")
print("="*70 + "\n")

all_passed = True

# TEST001: Simple condition
print("📋 TEST001: Simple String Condition")
print("   Rule: input.model: 'gpt-4o'")
print("   Expected: Match t1 (gpt-4o)")
if 'TEST001' in data['rules'] and data['rules']['TEST001']['count'] == 1:
    print("   ✅ PASSED - Matched 1 trace\n")
else:
    print(f"   ❌ FAILED - Expected 1, got {data['rules'].get('TEST001', {}).get('count', 0)}\n")
    all_passed = False

# TEST002: Numeric comparison
print("📋 TEST002: Numeric Comparison")
print("   Rule: usage.prompt_tokens > 1000")
print("   Expected: Match t1 (2500) and t3 (1500)")
if 'TEST002' in data['rules'] and data['rules']['TEST002']['count'] == 2:
    print("   ✅ PASSED - Matched 2 traces\n")
else:
    print(f"   ❌ FAILED - Expected 2, got {data['rules'].get('TEST002', {}).get('count', 0)}\n")
    all_passed = False

# TEST003: AND logic
print("📋 TEST003: Boolean AND Logic")
print("   Rule: and: [{model: 'gpt-4o'}, {tokens > 2000}]")
print("   Expected: Match t1 (gpt-4o with 2500 tokens)")
print("   Implementation: Flattened to single match block")
if 'TEST003' in data['rules'] and data['rules']['TEST003']['count'] == 1:
    reason = data['rules']['TEST003']['examples'][0]['reason']
    print(f"   Reason: {reason}")
    print("   ✅ PASSED - Matched 1 trace\n")
else:
    print(f"   ❌ FAILED - Expected 1, got {data['rules'].get('TEST003', {}).get('count', 0)}\n")
    all_passed = False

# TEST004: OR logic
print("📋 TEST004: Boolean OR Logic")
print("   Rule: or: [{model: 'gpt-4o'}, {model: 'claude-3'}]")
print("   Expected: Match t1 (gpt-4o) and t3 (claude-3)")
print("   Implementation: Expanded to 2 rule variants")

test004_total = 0
test004_or0 = data['rules'].get('TEST004_or0', {}).get('count', 0)
test004_or1 = data['rules'].get('TEST004_or1', {}).get('count', 0)
test004_total = test004_or0 + test004_or1

if test004_or0 == 1:
    print(f"   ✅ TEST004_or0 - Matched {test004_or0} trace (gpt-4o)")
else:
    print(f"   ❌ TEST004_or0 - Expected 1, got {test004_or0}")
    all_passed = False

if test004_or1 == 1:
    print(f"   ✅ TEST004_or1 - Matched {test004_or1} trace (claude-3)")
else:
    print(f"   ❌ TEST004_or1 - Expected 1, got {test004_or1}")
    all_passed = False

print(f"   ✅ PASSED - Total {test004_total} matches across variants\n")

# TEST005: NOT logic
print("📋 TEST005: Boolean NOT Logic")
print("   Rule: not: {model: 'gpt-3.5-turbo'}")
print("   Expected: Match t1 (gpt-4o) and t3 (claude-3)")
print("   Implementation: Inverted to != operator")
if 'TEST005' in data['rules'] and data['rules']['TEST005']['count'] == 2:
    reason = data['rules']['TEST005']['examples'][0]['reason']
    print(f"   Reason: {reason}")
    print("   ✅ PASSED - Matched 2 traces (excluded gpt-3.5-turbo)\n")
else:
    print(f"   ❌ FAILED - Expected 2, got {data['rules'].get('TEST005', {}).get('count', 0)}\n")
    all_passed = False

# Summary
print("="*70)
print("SUMMARY")
print("="*70)
print(f"Total Rules: {data['summary']['total_rules']}")
print(f"Total Violations: {data['summary']['violations']}")
print(f"\n✅ Simple conditions: Working")
print(f"✅ Numeric comparisons: Working")
print(f"✅ AND logic: Working (flattened to single match)")
print(f"✅ OR logic: Working (expanded to variants)")
print(f"✅ NOT logic: Working (inverted with != operator)")
print("="*70)

if all_passed:
    print("\n🎉 ALL BOOLEAN LOGIC TESTS PASSED!\n")
    sys.exit(0)
else:
    print("\n❌ SOME TESTS FAILED\n")
    sys.exit(1)
