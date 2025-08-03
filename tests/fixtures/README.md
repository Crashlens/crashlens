# CrashLens CI Test Fixtures
# Comprehensive test logs for policy validation

## Test Fixture 1: Policy Violations
test-policy-violations.jsonl - Contains various policy violations for testing CI integration
- retry_loop_detection: retry_count > 3
- high_cost_request: cost > 0.5
- overkill_expensive_model: expensive model + low tokens
- excessive_tokens: total_tokens > 5000

## Test Fixture 2: Clean Logs  
test-clean-logs.jsonl - Contains well-optimized logs that should pass all policies
- Efficient model usage
- Reasonable costs
- Appropriate token counts

## Test Fixture 3: Premium Feature Tests
test-premium-features.jsonl - Tests premium-only rules
- Cross-request pattern detection
- Advanced fallback analysis

## Test Fixture 4: Edge Cases
test-edge-cases.jsonl - Edge cases and boundary conditions
- Zero costs
- Missing fields
- Malformed entries

These fixtures are used in CI to ensure policy engine reliability.
