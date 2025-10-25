#!/usr/bin/env python3
"""
Tests for crashlens guard command
"""

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from crashlens.cli import cli
from crashlens.guard import (
    load_rules,
    load_jsonl,
    eval_condition,
    redact_text,
    SEVERITY_RANK,
)


def extract_json_from_output(output: str) -> dict:
    """Extract JSON from CLI output that may contain status messages
    
    The guard command outputs JSON followed by status messages.
    This function finds the JSON block and parses it.
    """
    # Find the last closing brace which should be the end of the JSON
    last_brace = output.rfind('}')
    if last_brace == -1:
        raise ValueError("No JSON found in output")
    
    # Extract just the JSON part
    json_str = output[:last_brace + 1]
    return json.loads(json_str)


class TestGuardCLI:
    """Test suite for guard CLI command"""

    def setup_method(self):
        """Setup test fixtures"""
        self.runner = CliRunner()

    def test_guard_basic_no_violations(self, tmp_path):
        """Test guard with clean logs (no violations)"""
        # Create sample logs with no violations
        logs = tmp_path / "logs.jsonl"
        logs.write_text('\n'.join([
            json.dumps({
                "timestamp": "t1",
                "model": "gpt-3.5-turbo",
                "tokens": 100,
                "retry_count": 0,
                "fallback_triggered": False,
                "prompt": "simple query",
                "cost_usd": 0.01,
                "endpoint": "/api"
            }),
            json.dumps({
                "timestamp": "t2",
                "model": "gpt-3.5-turbo",
                "tokens": 200,
                "retry_count": 1,
                "fallback_triggered": False,
                "prompt": "another query",
                "cost_usd": 0.02,
                "endpoint": "/api"
            })
        ]), encoding="utf-8")
        
        # Create rules
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
""", encoding="utf-8")
        
        # Run guard
        result = self.runner.invoke(cli, [
            "guard",
            str(logs),
            "--rules", str(rules),
            "--output", "json"
        ])
        
        assert result.exit_code == 0
        output = extract_json_from_output(result.output)
        assert output['summary']['violations'] == 0

    def test_guard_with_violations(self, tmp_path):
        """Test guard detecting violations"""
        # Create sample logs with violations
        logs = tmp_path / "logs.jsonl"
        logs.write_text('\n'.join([
            json.dumps({
                "timestamp": "t1",
                "model": "gpt-4o",
                "tokens": 2500,
                "retry_count": 0,
                "fallback_triggered": False,
                "prompt": "joe@example.com",
                "cost_usd": 0.25,
                "endpoint": "/api"
            }),
            json.dumps({
                "timestamp": "t2",
                "model": "gpt-3.5-turbo",
                "tokens": 100,
                "retry_count": 3,
                "fallback_triggered": False,
                "prompt": "ok",
                "cost_usd": 0.01,
                "endpoint": "/api"
            })
        ]), encoding="utf-8")
        
        # Create rules
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
  - id: RL002
    description: "Many retries"
    if:
      if_retry_count_gt: 2
    action: warn
    severity: warn
""", encoding="utf-8")
        
        # Run without fail-on-violations
        result = self.runner.invoke(cli, [
            "guard",
            str(logs),
            "--rules", str(rules),
            "--output", "json"
        ])
        
        assert result.exit_code == 0
        output = extract_json_from_output(result.output)
        assert output['summary']['violations'] == 2
        assert output['rules']['RL001']['count'] == 1
        assert output['rules']['RL002']['count'] == 1

    def test_guard_fail_on_violations(self, tmp_path):
        """Test guard with --fail-on-violations flag"""
        # Create logs with high severity violations
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "t1",
            "model": "gpt-4o",
            "tokens": 3000,
            "retry_count": 0,
            "fallback_triggered": False,
            "prompt": "test",
            "cost_usd": 0.30,
            "endpoint": "/api"
        }), encoding="utf-8")
        
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
""", encoding="utf-8")
        
        # Run with fail-on-violations
        result = self.runner.invoke(cli, [
            "guard",
            str(logs),
            "--rules", str(rules),
            "--fail-on-violations"
        ])
        
        assert result.exit_code == 1

    def test_guard_suppression(self, tmp_path):
        """Test guard with rule suppression"""
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "t1",
            "model": "gpt-4o",
            "tokens": 3000,
            "retry_count": 5,
            "fallback_triggered": False,
            "prompt": "test",
            "cost_usd": 0.30,
            "endpoint": "/api"
        }), encoding="utf-8")
        
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
  - id: RL002
    description: "Many retries"
    if:
      if_retry_count_gt: 2
    action: error
    severity: error
""", encoding="utf-8")
        
        # Suppress RL001
        result = self.runner.invoke(cli, [
            "guard",
            str(logs),
            "--rules", str(rules),
            "--suppress", "RL001",
            "--output", "json"
        ])
        
        assert result.exit_code == 0
        output = extract_json_from_output(result.output)
        assert 'RL001' not in output['rules']
        assert output['rules']['RL002']['count'] == 1

    def test_guard_severity_threshold(self, tmp_path):
        """Test guard with severity threshold"""
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "t1",
            "model": "gpt-3.5-turbo",
            "tokens": 100,
            "retry_count": 0,
            "fallback_triggered": True,
            "prompt": "test",
            "cost_usd": 0.01,
            "endpoint": "/api"
        }), encoding="utf-8")
        
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "Fallback triggered"
    if:
      if_fallback_triggered: true
    action: warn
    severity: warn
""", encoding="utf-8")
        
        # Should not fail with warn severity when threshold is error
        result = self.runner.invoke(cli, [
            "guard",
            str(logs),
            "--rules", str(rules),
            "--severity", "error",
            "--fail-on-violations"
        ])
        
        assert result.exit_code == 0
        
        # Should not fail with warn threshold even with fail-on-violations
        result = self.runner.invoke(cli, [
            "guard",
            str(logs),
            "--rules", str(rules),
            "--severity", "warn",
            "--fail-on-violations"
        ])
        
        assert result.exit_code == 1

    def test_guard_pii_stripping(self, tmp_path):
        """Test guard with PII stripping"""
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "t1",
            "model": "gpt-3.5-turbo",
            "tokens": 100,
            "retry_count": 0,
            "fallback_triggered": False,
            "prompt": "Contact joe@example.com or call +1-555-1234",
            "cost_usd": 0.01,
            "endpoint": "/api"
        }), encoding="utf-8")
        
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "PII in prompt"
    if:
      if_prompt_contains_pii: true
    action: error
    severity: error
""", encoding="utf-8")
        
        # Run with PII stripping
        result = self.runner.invoke(cli, [
            "guard",
            str(logs),
            "--rules", str(rules),
            "--strip-pii",
            "--output", "json"
        ])
        
        assert result.exit_code == 0
        output = extract_json_from_output(result.output)
        assert output['rules']['RL001']['count'] == 1
        example_prompt = output['rules']['RL001']['examples'][0]['prompt']
        assert "[REDACTED_EMAIL]" in example_prompt
        assert "[REDACTED_PHONE]" in example_prompt

    def test_guard_no_content(self, tmp_path):
        """Test guard with --no-content flag"""
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "t1",
            "model": "gpt-4o",
            "tokens": 3000,
            "retry_count": 0,
            "fallback_triggered": False,
            "prompt": "sensitive data here",
            "cost_usd": 0.30,
            "endpoint": "/api"
        }), encoding="utf-8")
        
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
""", encoding="utf-8")
        
        # Run with no-content
        result = self.runner.invoke(cli, [
            "guard",
            str(logs),
            "--rules", str(rules),
            "--no-content",
            "--output", "json"
        ])
        
        assert result.exit_code == 0
        output = extract_json_from_output(result.output)
        assert output['rules']['RL001']['count'] == 1
        assert len(output['rules']['RL001']['examples']) == 0

    def test_guard_markdown_output(self, tmp_path):
        """Test guard with markdown output format"""
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "t1",
            "model": "gpt-4o",
            "tokens": 2500,
            "retry_count": 0,
            "fallback_triggered": False,
            "prompt": "test",
            "cost_usd": 0.25,
            "endpoint": "/api"
        }), encoding="utf-8")
        
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
""", encoding="utf-8")
        
        result = self.runner.invoke(cli, [
            "guard",
            str(logs),
            "--rules", str(rules),
            "--output", "md"
        ])
        
        assert result.exit_code == 0
        assert "# CrashLens Guard Report" in result.output
        assert "RL001" in result.output
        assert "High token usage" in result.output

    def test_guard_text_output(self, tmp_path):
        """Test guard with text output format"""
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "t1",
            "model": "gpt-4o",
            "tokens": 2500,
            "retry_count": 0,
            "fallback_triggered": False,
            "prompt": "test",
            "cost_usd": 0.25,
            "endpoint": "/api"
        }), encoding="utf-8")
        
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
""", encoding="utf-8")
        
        result = self.runner.invoke(cli, [
            "guard",
            str(logs),
            "--rules", str(rules),
            "--output", "text"
        ])
        
        assert result.exit_code == 0
        assert "CrashLens Guard Report" in result.output
        assert "RL001" in result.output


class TestGuardHelpers:
    """Test suite for guard helper functions"""

    def test_load_rules_valid(self, tmp_path):
        """Test loading valid rules"""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
rules:
  - id: TEST001
    description: "Test rule"
    if:
      if_tokens_gt: 1000
    action: warn
    severity: warn
""", encoding="utf-8")
        
        rules = load_rules(str(rules_file))
        assert len(rules) == 1
        assert rules[0].id == "TEST001"
        assert rules[0].severity == "warn"

    def test_load_rules_missing_file(self):
        """Test loading rules from non-existent file"""
        with pytest.raises(Exception) as exc_info:
            load_rules("/nonexistent/path.yaml")
        assert "not found" in str(exc_info.value)

    def test_load_rules_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML"""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("invalid: yaml: content:", encoding="utf-8")
        
        with pytest.raises(Exception) as exc_info:
            load_rules(str(rules_file))
        assert "Invalid YAML" in str(exc_info.value)

    def test_load_rules_missing_required_fields(self, tmp_path):
        """Test rules with missing required fields"""
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
rules:
  - description: "Missing id"
    if:
      if_tokens_gt: 1000
    action: warn
""", encoding="utf-8")
        
        with pytest.raises(Exception) as exc_info:
            load_rules(str(rules_file))
        # jsonschema validation message
        assert "'id' is a required property" in str(exc_info.value) or "missing required field 'id'" in str(exc_info.value)

    def test_eval_condition_model(self):
        """Test model condition evaluation"""
        cond = {"if_model": "gpt-4o"}
        
        assert eval_condition(cond, {"model": "gpt-4o"}) is True
        assert eval_condition(cond, {"model": "gpt-3.5-turbo"}) is False

    def test_eval_condition_tokens(self):
        """Test token threshold condition"""
        cond = {"if_tokens_gt": 1000}
        
        assert eval_condition(cond, {"tokens": 1500}) is True
        assert eval_condition(cond, {"tokens": 1000}) is False
        assert eval_condition(cond, {"tokens": 500}) is False

    def test_eval_condition_retry_count(self):
        """Test retry count condition"""
        cond = {"if_retry_count_gt": 2}
        
        assert eval_condition(cond, {"retry_count": 3}) is True
        assert eval_condition(cond, {"retry_count": 2}) is False
        assert eval_condition(cond, {"retry_count": 1}) is False

    def test_eval_condition_fallback(self):
        """Test fallback triggered condition"""
        cond = {"if_fallback_triggered": True}
        
        assert eval_condition(cond, {"fallback_triggered": True}) is True
        assert eval_condition(cond, {"fallback_triggered": False}) is False

    def test_eval_condition_pii(self):
        """Test PII detection condition"""
        cond = {"if_prompt_contains_pii": True}
        
        assert eval_condition(cond, {"prompt": "Contact joe@example.com"}) is True
        assert eval_condition(cond, {"prompt": "Call +1-555-1234"}) is True
        assert eval_condition(cond, {"prompt": "No PII here"}) is False

    def test_eval_condition_cost(self):
        """Test cost threshold condition"""
        cond = {"if_cost_usd_gt": 0.50}
        
        assert eval_condition(cond, {"cost_usd": 0.75}) is True
        assert eval_condition(cond, {"cost_usd": 0.50}) is False
        assert eval_condition(cond, {"cost_usd": 0.25}) is False

    def test_eval_condition_multiple(self):
        """Test multiple conditions (AND logic)"""
        cond = {
            "if_model": "gpt-4o",
            "if_tokens_gt": 1000,
            "if_retry_count_gt": 0
        }
        
        # All conditions met
        assert eval_condition(cond, {
            "model": "gpt-4o",
            "tokens": 2000,
            "retry_count": 1
        }) is True
        
        # One condition not met
        assert eval_condition(cond, {
            "model": "gpt-4o",
            "tokens": 500,  # Too low
            "retry_count": 1
        }) is False

    def test_redact_text_no_pii(self):
        """Test text redaction without PII flag"""
        text = "Email: joe@example.com Phone: +1-555-1234"
        assert redact_text(text, strip_pii=False) == text

    def test_redact_text_with_pii(self):
        """Test text redaction with PII flag"""
        text = "Email: joe@example.com Phone: +1-555-1234"
        redacted = redact_text(text, strip_pii=True)
        
        assert "[REDACTED_EMAIL]" in redacted
        assert "[REDACTED_PHONE]" in redacted
        assert "joe@example.com" not in redacted
        assert "+1-555-1234" not in redacted

    def test_severity_ranks(self):
        """Test severity ranking constants"""
        assert SEVERITY_RANK["warn"] < SEVERITY_RANK["error"]
        assert SEVERITY_RANK["error"] < SEVERITY_RANK["fatal"]


class TestGuardIntegration:
    """Integration tests using real fixtures"""

    def test_guard_with_fixture_logs(self):
        """Test guard with fixture combined-logs.jsonl"""
        runner = CliRunner()
        
        # Use project fixtures
        fixtures_dir = Path(__file__).parent.parent / "fixtures"
        logs_file = fixtures_dir / "combined-logs.jsonl"
        
        # Skip if fixtures don't exist
        if not logs_file.exists():
            pytest.skip("Fixture file not found")
        
        # Create temp rules
        with runner.isolated_filesystem():
            rules_file = Path("rules.yaml")
            rules_file.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
  - id: RL002
    description: "Many retries"
    if:
      if_retry_count_gt: 2
    action: error
    severity: error
  - id: RL003
    description: "Fallback triggered"
    if:
      if_fallback_triggered: true
    action: warn
    severity: warn
""", encoding="utf-8")
            
            result = runner.invoke(cli, [
                "guard",
                str(logs_file),
                "--rules", str(rules_file),
                "--output", "json"
            ])
            
            assert result.exit_code == 0
            output = extract_json_from_output(result.output)
            
            # Verify violations detected
            assert output['summary']['violations'] > 0
            assert output['rules']['RL001']['count'] >= 1  # High tokens
            assert output['rules']['RL002']['count'] >= 1  # Retries
            assert output['rules']['RL003']['count'] >= 1  # Fallback


class TestGuardEdgeCases:
    """Test suite for edge cases and error handling"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.runner = CliRunner()
    
    def test_malformed_rules_yaml(self, tmp_path):
        """Test that malformed YAML fails gracefully"""
        rules_file = tmp_path / "bad.yaml"
        rules_file.write_text("rules: [ invalid yaml {", encoding="utf-8")
        
        logs_file = tmp_path / "logs.jsonl"
        logs_file.write_text('{"model": "gpt-4", "tokens": 100}', encoding="utf-8")
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "guard", str(logs_file),
            "--rules", str(rules_file)
        ])
        
        assert result.exit_code == 1
        assert "Invalid YAML" in result.output
    
    def test_missing_required_rule_field(self, tmp_path):
        """Test that rules missing required fields fail validation"""
        rules_file = tmp_path / "incomplete.yaml"
        rules_file.write_text("""
rules:
  - id: TEST
    description: "Missing 'if' field"
    action: warn
""", encoding="utf-8")
        
        logs_file = tmp_path / "logs.jsonl"
        logs_file.write_text('{"model": "gpt-4"}', encoding="utf-8")
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "guard", str(logs_file),
            "--rules", str(rules_file)
        ])
        
        assert result.exit_code == 1
        assert "schema" in result.output.lower() or "required" in result.output.lower()
    
    def test_duplicate_rule_ids(self, tmp_path):
        """Test that duplicate rule IDs are detected"""
        rules_file = tmp_path / "duplicates.yaml"
        rules_file.write_text("""
rules:
  - id: DUPLICATE
    description: "First rule"
    if:
      if_tokens_gt: 100
    action: warn
  - id: DUPLICATE
    description: "Second rule with same ID"
    if:
      if_tokens_gt: 200
    action: error
""", encoding="utf-8")
        
        logs_file = tmp_path / "logs.jsonl"
        logs_file.write_text('{"model": "gpt-4", "tokens": 150}', encoding="utf-8")
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "guard", str(logs_file),
            "--rules", str(rules_file)
        ])
        
        assert result.exit_code == 1
        assert "Duplicate rule IDs" in result.output
    
    def test_truncated_jsonl_line(self, tmp_path):
        """Test fail-safe handling of truncated JSONL line"""
        logs_file = tmp_path / "truncated.jsonl"
        logs_file.write_text('{"model": "gpt-4", "tokens": 100}\n{"model": "gpt-3.5", "token', encoding="utf-8")
        
        rules_file = tmp_path / "rules.yaml"
        rules_file.write_text("""
rules:
  - id: TEST
    if:
      if_tokens_gt: 50
    action: warn
""", encoding="utf-8")
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "guard", str(logs_file),
            "--rules", str(rules_file)
        ])
        
        # Should succeed (fail-safe: skips bad line and continues)
        assert result.exit_code == 0
        # Should warn about skipped line
        assert "Skipping malformed JSON" in result.output or "Skipped 1 malformed line" in result.output
    
    def test_max_examples_limit(self, tmp_path):
        """Test that MAX_EXAMPLES limit is enforced"""
        import os
        os.environ["CRASHLENS_MAX_EXAMPLES"] = "2"
        
        try:
            # Create logs with many violations
            logs_file = tmp_path / "many.jsonl"
            entries = [
                '{"model": "gpt-4", "tokens": 5000, "retry_count": 0}\n' for _ in range(10)
            ]
            logs_file.write_text(''.join(entries), encoding="utf-8")
            
            rules_file = tmp_path / "rules.yaml"
            rules_file.write_text("""
rules:
  - id: HIGH_TOKENS
    if:
      if_tokens_gt: 1000
    action: warn
""", encoding="utf-8")
            
            runner = CliRunner()
            result = runner.invoke(cli, [
                "guard", str(logs_file),
                "--rules", str(rules_file),
                "--output", "json"
            ])
            
            assert result.exit_code == 0
            output = extract_json_from_output(result.output)
            
            # Should have 10 violations but only 2 examples
            assert output['rules']['HIGH_TOKENS']['count'] == 10
            assert len(output['rules']['HIGH_TOKENS']['examples']) <= 2
        finally:
            # Clean up env var
            os.environ.pop("CRASHLENS_MAX_EXAMPLES", None)
    
    def test_invalid_severity_in_rule(self, tmp_path):
        """Test that invalid severity values are caught"""
        rules_file = tmp_path / "bad_severity.yaml"
        rules_file.write_text("""
rules:
  - id: TEST
    if:
      if_tokens_gt: 100
    action: warn
    severity: critical
""", encoding="utf-8")
        
        logs_file = tmp_path / "logs.jsonl"
        logs_file.write_text('{"model": "gpt-4", "tokens": 200}', encoding="utf-8")
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "guard", str(logs_file),
            "--rules", str(rules_file)
        ])
        
        assert result.exit_code == 1
        assert "schema" in result.output.lower() or "severity" in result.output.lower()
    
    def test_empty_rules_file(self, tmp_path):
        """Test handling of empty rules file"""
        rules_file = tmp_path / "empty.yaml"
        rules_file.write_text("", encoding="utf-8")
        
        logs_file = tmp_path / "logs.jsonl"
        logs_file.write_text('{"model": "gpt-4", "tokens": 100}', encoding="utf-8")
        
        runner = CliRunner()
        result = runner.invoke(cli, [
            "guard", str(logs_file),
            "--rules", str(rules_file)
        ])
        
        assert result.exit_code == 1
        assert "rules" in result.output.lower()
    
    def test_pii_detector_pluggable(self):
        """Test that PIIDetector can be extended"""
        from crashlens.guard import PIIDetector, _pii_detector
        
        # Test default detector
        assert _pii_detector.detect("test@example.com") is True
        assert _pii_detector.detect("+1-555-1234") is True
        assert _pii_detector.detect("no pii here") is False
        
        # Test redaction
        redacted = _pii_detector.redact("Email: test@example.com, Phone: +1-555-1234")
        assert "[REDACTED_EMAIL]" in redacted
        assert "[REDACTED_PHONE]" in redacted
        assert "test@example.com" not in redacted
    
    def test_default_severity_is_warn(self, tmp_path):
        """Test that rules without explicit severity default to 'warn'"""
        rules_file = tmp_path / "no_severity.yaml"
        rules_file.write_text("""
rules:
  - id: TEST
    description: "No severity specified"
    if:
      if_tokens_gt: 100
    action: warn
""", encoding="utf-8")
        
        from crashlens.guard import load_rules
        rules = load_rules(str(rules_file))
        
        assert len(rules) == 1
        assert rules[0].severity == "warn"

