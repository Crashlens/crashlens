#!/usr/bin/env python3
"""
Extended tests for --suppress flag enhancements
Tests comma-separated format and mixed usage patterns
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from crashlens.guard import guard


def extract_json_from_output(output: str) -> dict:
    """Extract JSON from output that may contain other text"""
    # Click's CliRunner combines stdout and stderr
    # Find the JSON object (starts with { and ends with })
    start_idx = output.find('{')
    if start_idx == -1:
        raise ValueError(f"No JSON object found in output: {output}")
    
    # Find matching closing brace
    brace_count = 0
    for i in range(start_idx, len(output)):
        if output[i] == '{':
            brace_count += 1
        elif output[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                json_text = output[start_idx:i+1]
                return json.loads(json_text)
    
    raise ValueError(f"No valid JSON found in output: {output}")


class TestSuppressCommaSeparated:
    """Test comma-separated rule suppression"""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @pytest.fixture
    def setup_files(self, tmp_path):
        """Create test logs and rules"""
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "2025-10-25T10:00:00Z",
            "model": "gpt-4o",
            "tokens": 3000,
            "retry_count": 5,
            "fallback_triggered": True,
            "prompt": "test prompt",
            "cost_usd": 0.30,
            "endpoint": "/api/chat"
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
    action: fail_ci
    severity: error
  - id: RL003
    description: "Fallback triggered"
    if:
      if_fallback_triggered: true
    action: warn
    severity: warn
""", encoding="utf-8")
        
        return logs, rules
    
    def test_suppress_comma_separated_single(self, runner, setup_files):
        """Single rule suppressed via comma-separated format (edge case)"""
        logs, rules = setup_files
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--suppress", "RL001",
            "--output", "json"
        ])
        
        assert result.exit_code == 0
        output = extract_json_from_output(result.output)
        
        # RL001 should be suppressed (not in results)
        assert 'RL001' not in output['rules']
        
        # RL002 and RL003 should still be detected
        assert output['rules']['RL002']['count'] == 1
        assert output['rules']['RL003']['count'] == 1
    
    def test_suppress_comma_separated_multiple(self, runner, setup_files):
        """Multiple rules suppressed in single comma-separated flag"""
        logs, rules = setup_files
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--suppress", "RL001,RL002",
            "--output", "json"
        ])
        
        assert result.exit_code == 0
        output = extract_json_from_output(result.output)
        
        # RL001 and RL002 should be suppressed
        assert 'RL001' not in output['rules']
        assert 'RL002' not in output['rules']
        
        # Only RL003 should be detected
        assert output['rules']['RL003']['count'] == 1
    
    def test_suppress_comma_separated_all_rules(self, runner, setup_files, monkeypatch):
        """All rules suppressed via comma-separated format"""
        logs, rules = setup_files
        
        # Disable performance thresholds for this test
        monkeypatch.setenv("EXPENSIVE_REQUEST_THRESHOLD", "9999.99")
        monkeypatch.setenv("SLOW_RESPONSE_THRESHOLD_MS", "999999")
        monkeypatch.setenv("ERROR_RATE_THRESHOLD", "1.0")
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--suppress", "RL001,RL002,RL003",
            "--output", "json"
        ])
        
        assert result.exit_code == 0
        output = extract_json_from_output(result.output)
        
        # No rules should be in results
        assert len(output['rules']) == 0
        assert output['summary']['violations'] == 0
    
    def test_suppress_with_spaces(self, runner, setup_files):
        """Comma-separated with spaces should be trimmed"""
        logs, rules = setup_files
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--suppress", "RL001, RL002",  # Note spaces
            "--output", "json"
        ])
        
        assert result.exit_code == 0
        output = extract_json_from_output(result.output)
        
        # Both should be suppressed despite spaces
        assert 'RL001' not in output['rules']
        assert 'RL002' not in output['rules']
        assert output['rules']['RL003']['count'] == 1
    
    def test_suppress_mixed_format(self, runner, setup_files, monkeypatch):
        """Mix repeatable and comma-separated formats"""
        logs, rules = setup_files
        
        # Disable performance thresholds for this test
        monkeypatch.setenv("EXPENSIVE_REQUEST_THRESHOLD", "9999.99")
        monkeypatch.setenv("SLOW_RESPONSE_THRESHOLD_MS", "999999")
        monkeypatch.setenv("ERROR_RATE_THRESHOLD", "1.0")
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--suppress", "RL001",
            "--suppress", "RL002,RL003",
            "--output", "json"
        ])
        
        assert result.exit_code == 0
        output = extract_json_from_output(result.output)
        
        # All three rules should be suppressed
        assert 'RL001' not in output['rules']
        assert 'RL002' not in output['rules']
        assert 'RL003' not in output['rules']
        assert output['summary']['violations'] == 0
    
    def test_suppress_invalid_rule_ids_ignored(self, runner, setup_files):
        """Invalid rule IDs are silently ignored"""
        logs, rules = setup_files
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--suppress", "NONEXISTENT,RL001,FAKE",
            "--output", "json"
        ])
        
        # Should not crash
        assert result.exit_code == 0
        output = extract_json_from_output(result.output)
        
        # RL001 suppressed, invalid IDs ignored
        assert 'RL001' not in output['rules']
        assert output['rules']['RL002']['count'] == 1
        assert output['rules']['RL003']['count'] == 1
    
    def test_suppress_empty_strings_handled(self, runner, setup_files):
        """Empty strings in comma-separated list are ignored"""
        logs, rules = setup_files
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--suppress", "RL001,,RL002,",  # Extra commas
            "--output", "json"
        ])
        
        assert result.exit_code == 0
        output = extract_json_from_output(result.output)
        
        # Should handle gracefully
        assert 'RL001' not in output['rules']
        assert 'RL002' not in output['rules']
        assert output['rules']['RL003']['count'] == 1
    
    def test_suppress_case_sensitive(self, runner, setup_files):
        """Rule ID matching is case-sensitive"""
        logs, rules = setup_files
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--suppress", "rl001",  # lowercase (should not match RL001)
            "--output", "json"
        ])
        
        assert result.exit_code == 0
        output = extract_json_from_output(result.output)
        
        # RL001 should NOT be suppressed (case mismatch)
        assert output['rules']['RL001']['count'] == 1
    
    def test_suppress_no_violations_when_all_suppressed(self, runner, setup_files):
        """Summary shows 0 violations when all rules suppressed"""
        logs, rules = setup_files
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--suppress", "RL001,RL002,RL003",
            "--output", "text"
        ])
        
        assert result.exit_code == 0
        assert "No violations detected" in result.output or "0" in result.output
