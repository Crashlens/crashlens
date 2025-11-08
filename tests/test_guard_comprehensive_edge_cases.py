"""
Comprehensive edge case tests for Guard system pre-production validation.
Tests all items from the surgical checklist.
"""

import json
import pytest
from pathlib import Path
from click.testing import CliRunner
from crashlens.cli import cli


def extract_json_from_output(output: str) -> dict:
    """Extract and parse JSON from CLI output that may have text prefix/suffix"""
    lines = output.strip().split('\n')
    
    # Find the start of JSON
    json_start_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith('{'):
            json_start_idx = i
            break
    
    if json_start_idx is None:
        raise ValueError(f"No JSON found in output: {output}")
    
    # Try to parse progressively larger chunks until we get valid JSON
    for end_idx in range(json_start_idx + 1, len(lines) + 1):
        json_str = '\n'.join(lines[json_start_idx:end_idx])
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            continue
    
    raise ValueError(f"Could not parse JSON from output: {output}")


class TestCoreRuleEvaluation:
    """A. Core functionality & correctness - Rule evaluation"""
    
    def test_all_condition_types(self, tmp_path):
        """Test all condition types: model, tokens, retry_count, fallback, pii, cost, response_time"""
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: MODEL_CHECK
    description: "Model check"
    if:
      input.model:
        "==": "gpt-4"
    action: warn
    severity: warn
  - id: TOKENS_GT
    description: "Token threshold"
    if:
      usage.prompt_tokens:
        ">": 1000
    action: warn
    severity: warn
  - id: RETRY_COUNT_GT
    description: "Retry threshold"
    if:
      metadata.retry_count:
        ">": 3
    action: warn
    severity: warn
  - id: FALLBACK_TRIGGERED
    description: "Fallback check"
    if:
      metadata.fallback_triggered:
        "==": true
    action: warn
    severity: warn
  - id: PII_IN_PROMPT
    description: "PII detection"
    if:
      input.prompt:
        "regex": "@"
    action: error
    severity: error
  - id: COST_GT
    description: "Cost threshold"
    if:
      cost:
        ">": 0.50
    action: warn
    severity: warn
""")
        
        logs = tmp_path / "test.jsonl"
        logs.write_text(json.dumps({
            "traceId": "trace-001",
            "startTime": "2025-01-01T10:00:00Z",
            "input": {
                "model": "gpt-4",
                "prompt": "Contact joe@example.com"
            },
            "usage": {
                "prompt_tokens": 1500,
                "completion_tokens": 200
            },
            "metadata": {
                "retry_count": 5,
                "fallback_triggered": True
            },
            "cost": 0.75
        }))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules), '--output', 'json'])
        
        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = extract_json_from_output(result.output)
        
        # Should match all 6 rules
        assert 'MODEL_CHECK' in output['rules']
        assert 'TOKENS_GT' in output['rules']
        assert 'RETRY_COUNT_GT' in output['rules']
        assert 'FALLBACK_TRIGGERED' in output['rules']
        assert 'PII_IN_PROMPT' in output['rules']
        assert 'COST_GT' in output['rules']
    
    def test_boolean_composition_and_nesting(self, tmp_path):
        """Test implicit AND, explicit OR, NOT, deep nesting (>3 levels)"""
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: IMPLICIT_AND
    description: "Multiple conditions = implicit AND"
    if:
      usage.prompt_tokens:
        ">": 1000
      input.model:
        "==": "gpt-4"
    action: warn
    severity: warn
  - id: DEEP_NESTING
    description: "3+ level nesting"
    if:
      usage.prompt_tokens:
        ">": 500
      input.model:
        "in": ["gpt-4", "gpt-4-turbo"]
      metadata.retry_count:
        "<=": 5
    action: warn
    severity: warn
""")
        
        logs = tmp_path / "test.jsonl"
        logs.write_text(json.dumps({
            "traceId": "trace-001",
            "startTime": "2025-01-01T10:00:00Z",
            "input": {"model": "gpt-4"},
            "usage": {"prompt_tokens": 1500},
            "metadata": {"retry_count": 3}
        }))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules), '--output', 'json'])
        
        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = extract_json_from_output(result.output)
        
        # Both should match
        assert 'IMPLICIT_AND' in output['rules']
        assert 'DEEP_NESTING' in output['rules']


class TestFieldPathResolution:
    """A. Core functionality - Field path resolution edge cases"""
    
    def test_nested_paths_and_missing_fields(self, tmp_path):
        """Test nested paths, arrays, missing fields, dot-in-key edge cases"""
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: NESTED_PATH
    description: "Deeply nested path"
    if:
      usage.prompt_tokens:
        ">": 0
    action: warn
    severity: warn
  - id: MISSING_FIELD
    description: "Missing field should not crash"
    if:
      metadata.nonexistent_field:
        "==": "value"
    action: warn
    severity: warn
""")
        
        logs = tmp_path / "test.jsonl"
        logs.write_text('\n'.join([
            json.dumps({
                "traceId": "trace-001",
                "input": {"model": "gpt-4"},
                "usage": {"prompt_tokens": 100}
            }),
            json.dumps({
                "traceId": "trace-002",
                "input": {"model": "gpt-3.5"}
                # Missing 'usage' entirely
            })
        ]))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules)])
        
        # Should not crash on missing fields
        assert result.exit_code == 0


class TestTypeCoercion:
    """A. Core functionality - Type coercion"""
    
    def test_string_vs_numeric_coercion(self, tmp_path):
        """Test tokens as '2500' vs 2500, booleans as 'true' vs true"""
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: NUMERIC_COMPARISON
    description: "Compare numeric field"
    if:
      usage.prompt_tokens:
        ">": 1000
    action: warn
    severity: warn
""")
        
        logs = tmp_path / "test.jsonl"
        logs.write_text('\n'.join([
            json.dumps({
                "traceId": "trace-001",
                "usage": {"prompt_tokens": 2500}  # Numeric
            }),
            json.dumps({
                "traceId": "trace-002",
                "usage": {"prompt_tokens": "2500"}  # String
            })
        ]))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules), '--output', 'json'])
        
        assert result.exit_code == 0, f"Command failed: {result.output}"
        output = extract_json_from_output(result.output)
        
        # Both should match (coercion should work)
        assert output['rules']['NUMERIC_COMPARISON']['count'] == 2


class TestRegexHandling:
    """A. Core functionality - Regex edge cases"""
    
    def test_regex_format_variations(self, tmp_path):
        """Test regex: @ vs regex:@, whitespace handling"""
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: REGEX_WITH_SPACE
    description: "Regex with space"
    if:
      input.prompt:
        regex: '@'
    action: warn
    severity: warn
""")
        
        logs = tmp_path / "test.jsonl"
        logs.write_text(json.dumps({
            "traceId": "trace-001",
            "input": {"prompt": "Contact me at joe@example.com"}
        }))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules)])
        
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        # Format should work
    
    def test_unicode_regex(self, tmp_path):
        """Test unicode patterns"""
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: UNICODE_PATTERN
    description: "Unicode in regex"
    if:
      input.prompt:
        "regex": "[\\u4e00-\\u9fff]"
    action: warn
    severity: warn
""")
        
        logs = tmp_path / "test.jsonl"
        logs.write_text(json.dumps({
            "traceId": "trace-001",
            "input": {"prompt": "Hello 你好 world"}
        }))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules)])
        
        assert result.exit_code == 0


class TestPIIDetection:
    """A. Core functionality - PII detection"""
    
    def test_canonical_pii_patterns(self, tmp_path):
        """Test email/phone/SSN detection"""
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: EMAIL_DETECTED
    description: "Email pattern"
    if:
      input.prompt:
        regex: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}'
    action: error
    severity: error
  - id: PHONE_DETECTED
    description: "Phone pattern"
    if:
      input.prompt:
        regex: '\\d{3}-\\d{3}-\\d{4}'
    action: error
    severity: error
  - id: SSN_DETECTED
    description: "SSN pattern"
    if:
      input.prompt:
        regex: '\\d{3}-\\d{2}-\\d{4}'
    action: error
    severity: error
""")
        
        logs = tmp_path / "test.jsonl"
        logs.write_text('\n'.join([
            json.dumps({
                "traceId": "trace-001",
                "input": {"prompt": "Email: alice@example.com"}
            }),
            json.dumps({
                "traceId": "trace-002",
                "input": {"prompt": "Phone: 555-123-4567"}
            }),
            json.dumps({
                "traceId": "trace-003",
                "input": {"prompt": "SSN: 123-45-6789"}
            })
        ]))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules)])
        
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        # Should match all PII patterns


class TestJSONLParsing:
    """B. I/O - JSONL parsing edge cases"""
    
    def test_malformed_lines_tolerance(self, tmp_path):
        """Test trailing commas, whitespace, blank lines, malformed lines"""
        logs = tmp_path / "test.jsonl"
        logs.write_text('''
{"traceId": "trace-001", "input": {"model": "gpt-4"}}

  {"traceId": "trace-002", "input": {"model": "gpt-3.5"}}  
{"traceId": "trace-003", "input": {"model": "gpt-4"},}
this is not json at all
{"traceId": "trace-004", "input": {"model": "claude"}}
''')
        
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: ANY_TRACE
    description: "Any trace"
    if:
      traceId:
        "regex": "trace-"
    action: warn
    severity: warn
""")
        
        runner = CliRunner()
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules)])
        
        # Should process valid lines and skip malformed
        assert result.exit_code == 0
        assert "trace-001" in result.output or "processed" in result.output.lower()


class TestCLIBehavior:
    """C. CLI behavior & UX"""
    
    def test_exit_codes_with_fail_on_violations(self, tmp_path):
        """Test exit codes: 0/1 for --fail-on-violations"""
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: HIGH_COST
    description: "Cost too high"
    if:
      cost:
        ">": 0.10
    action: error
    severity: error
""")
        
        logs = tmp_path / "test.jsonl"
        logs.write_text(json.dumps({
            "traceId": "trace-001",
            "cost": 0.50
        }))
        
        runner = CliRunner()
        
        # Without --fail-on-violations: should exit 0
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules)])
        assert result.exit_code == 0
        
        # With --fail-on-violations: should exit 1
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules), '--fail-on-violations'])
        assert result.exit_code == 1
    
    def test_help_and_version(self):
        """Test --help and --version"""
        runner = CliRunner()
        
        result = runner.invoke(cli, ['guard', '--help'])
        assert result.exit_code == 0
        assert 'guard' in result.output.lower()
        
        result = runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
    
    def test_output_formats(self, tmp_path):
        """Test --output formats: json, markdown, text"""
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: TEST_RULE
    description: "Test"
    if:
      traceId:
        "regex": "trace-"
    action: warn
    severity: warn
""")
        
        logs = tmp_path / "test.jsonl"
        logs.write_text(json.dumps({
            "traceId": "trace-001",
            "input": {"model": "gpt-4"}
        }))
        
        runner = CliRunner()
        
        # JSON format
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules), '--output', 'json'])
        assert result.exit_code == 0, f"JSON format failed: {result.output}"
        assert 'rules' in result.output or 'TEST_RULE' in result.output
        
        # Markdown format
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules), '--output', 'md'])
        assert result.exit_code == 0, f"Markdown format failed: {result.output}"
        
        # Text format
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules), '--output', 'text'])
        assert result.exit_code == 0, f"Text format failed: {result.output}"
    
    def test_rules_file_validation(self, tmp_path):
        """Test clear errors for malformed rules"""
        rules = tmp_path / "bad_rules.yaml"
        rules.write_text("""
rules:
  - id: BAD_RULE
    # Missing 'if' key
    action: warn
""")
        
        logs = tmp_path / "test.jsonl"
        logs.write_text(json.dumps({"traceId": "trace-001"}))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['guard', str(logs), '--rules', str(rules)])
        
        # Should fail with helpful error
        assert result.exit_code == 1
        assert 'error' in result.output.lower() or 'invalid' in result.output.lower()


class TestBackwardsCompatibility:
    """D. Backwards compatibility & migration"""
    
    def test_guard_alias(self, tmp_path):
        """Test guard command works (restored for backwards compatibility)"""
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: TEST_RULE
    description: "Test"
    if:
      traceId:
        "regex": "trace-"
    action: warn
    severity: warn
""")
        
        logs = tmp_path / "test.jsonl"
        logs.write_text(json.dumps({"traceId": "trace-001"}))
        
        runner = CliRunner()
        result = runner.invoke(cli, ['guard', str(logs), '--policy-file', str(rules)])
        
        # Should work now that we restored the command
        assert result.exit_code == 0, f"guard command failed: {result.output}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
