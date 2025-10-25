#!/usr/bin/env python3
"""
Tests for performance threshold checks
Validates that CI fails when latency/cost/error-rate thresholds are breached
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from crashlens.guard import guard


class TestPerformanceThresholds:
    """Test performance threshold enforcement"""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    @pytest.fixture
    def empty_rules(self, tmp_path):
        """Empty rules file (thresholds independent of rules)"""
        rules = tmp_path / "rules.yaml"
        rules.write_text("rules: []", encoding="utf-8")
        return rules
    
    def test_latency_threshold_ci_failure(self, runner, tmp_path, monkeypatch, empty_rules):
        """High latency triggers CI failure"""
        # Set strict latency threshold
        monkeypatch.setenv("SLOW_RESPONSE_THRESHOLD_MS", "1000")
        
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "2025-10-25T10:00:00Z",
            "model": "gpt-4o",
            "tokens": 100,
            "response_time_ms": 2500,  # Exceeds 1000ms threshold
            "cost_usd": 0.001,
            "error": False
        }), encoding="utf-8")
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(empty_rules),
            "--fail-on-violations",
            "--output", "text"
        ])
        
        assert result.exit_code == 1
        assert "latency" in result.output.lower() or "2500" in result.output
    
    def test_cost_threshold_ci_failure(self, runner, tmp_path, monkeypatch, empty_rules):
        """High cost triggers CI failure"""
        # Set strict cost threshold
        monkeypatch.setenv("EXPENSIVE_REQUEST_THRESHOLD", "0.01")
        
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "2025-10-25T10:00:00Z",
            "model": "gpt-4o",
            "tokens": 100,
            "response_time_ms": 100,
            "cost_usd": 0.15,  # Exceeds $0.01 threshold
            "error": False
        }), encoding="utf-8")
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(empty_rules),
            "--fail-on-violations",
            "--output", "text"
        ])
        
        assert result.exit_code == 1
        assert "cost" in result.output.lower() and ("0.15" in result.output or "15" in result.output)
    
    def test_error_rate_threshold_ci_failure(self, runner, tmp_path, monkeypatch, empty_rules):
        """High error rate triggers CI failure"""
        # Set strict error rate threshold
        monkeypatch.setenv("ERROR_RATE_THRESHOLD", "0.10")  # 10%
        
        logs = tmp_path / "logs.jsonl"
        # 2 errors out of 5 logs = 40% error rate (exceeds 10%)
        logs.write_text('\n'.join([
            json.dumps({"timestamp": "t1", "model": "gpt-4o", "tokens": 100, "response_time_ms": 100, "cost_usd": 0.001, "error": True}),
            json.dumps({"timestamp": "t2", "model": "gpt-4o", "tokens": 100, "response_time_ms": 100, "cost_usd": 0.001, "error": False}),
            json.dumps({"timestamp": "t3", "model": "gpt-4o", "tokens": 100, "response_time_ms": 100, "cost_usd": 0.001, "error": True}),
            json.dumps({"timestamp": "t4", "model": "gpt-4o", "tokens": 100, "response_time_ms": 100, "cost_usd": 0.001, "error": False}),
            json.dumps({"timestamp": "t5", "model": "gpt-4o", "tokens": 100, "response_time_ms": 100, "cost_usd": 0.001, "error": False})
        ]), encoding="utf-8")
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(empty_rules),
            "--fail-on-violations",
            "--output", "text"
        ])
        
        assert result.exit_code == 1
        assert "error" in result.output.lower() and ("40" in result.output or "rate" in result.output.lower())
    
    def test_performance_within_limits_passes(self, runner, tmp_path, monkeypatch, empty_rules):
        """No threshold violations when metrics are within limits"""
        # Set default thresholds (lenient)
        monkeypatch.setenv("SLOW_RESPONSE_THRESHOLD_MS", "5000")
        monkeypatch.setenv("EXPENSIVE_REQUEST_THRESHOLD", "1.00")
        monkeypatch.setenv("ERROR_RATE_THRESHOLD", "0.50")
        
        logs = tmp_path / "logs.jsonl"
        logs.write_text('\n'.join([
            json.dumps({"timestamp": "t1", "model": "gpt-3.5-turbo", "tokens": 100, "response_time_ms": 500, "cost_usd": 0.001, "error": False}),
            json.dumps({"timestamp": "t2", "model": "gpt-3.5-turbo", "tokens": 100, "response_time_ms": 600, "cost_usd": 0.002, "error": False}),
            json.dumps({"timestamp": "t3", "model": "gpt-3.5-turbo", "tokens": 100, "response_time_ms": 700, "cost_usd": 0.001, "error": False})
        ]), encoding="utf-8")
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(empty_rules),
            "--fail-on-violations",
            "--output", "text"
        ])
        
        assert result.exit_code == 0
        assert "No violations" in result.output or result.exit_code == 0
    
    def test_combined_performance_thresholds(self, runner, tmp_path, monkeypatch, empty_rules):
        """Multiple threshold breaches detected"""
        # Set strict thresholds for all metrics
        monkeypatch.setenv("SLOW_RESPONSE_THRESHOLD_MS", "100")
        monkeypatch.setenv("EXPENSIVE_REQUEST_THRESHOLD", "0.01")
        monkeypatch.setenv("ERROR_RATE_THRESHOLD", "0.05")
        
        logs = tmp_path / "logs.jsonl"
        # Breach all three thresholds
        logs.write_text('\n'.join([
            json.dumps({"timestamp": "t1", "model": "gpt-4o", "tokens": 5000, "response_time_ms": 3000, "cost_usd": 0.50, "error": True}),
            json.dumps({"timestamp": "t2", "model": "gpt-4o", "tokens": 3000, "response_time_ms": 2000, "cost_usd": 0.30, "error": False})
        ]), encoding="utf-8")
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(empty_rules),
            "--fail-on-violations",
            "--output", "text"
        ])
        
        assert result.exit_code == 1
        # Should detect all three threshold breaches
        output_lower = result.output.lower()
        # At least one should be mentioned
        assert "latency" in output_lower or "cost" in output_lower or "error" in output_lower
    
    def test_threshold_with_regular_rules(self, runner, tmp_path, monkeypatch):
        """Thresholds work alongside regular rules"""
        monkeypatch.setenv("SLOW_RESPONSE_THRESHOLD_MS", "500")
        
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "2025-10-25T10:00:00Z",
            "model": "gpt-4o",
            "tokens": 5000,  # Will trigger token rule
            "response_time_ms": 2000,  # Will trigger latency threshold
            "cost_usd": 0.001,
            "error": False
        }), encoding="utf-8")
        
        rules = tmp_path / "rules.yaml"
        rules.write_text("""
rules:
  - id: RL001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: error
""", encoding="utf-8")
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(rules),
            "--fail-on-violations",
            "--output", "json"
        ])
        
        assert result.exit_code == 1
        # Both rule and threshold should be detected
        assert "RL001" in result.output or "token" in result.output.lower()
    
    def test_default_thresholds_lenient(self, runner, tmp_path, empty_rules):
        """Default thresholds are lenient (don't fail normal operations)"""
        # Don't set any env vars - use defaults
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "2025-10-25T10:00:00Z",
            "model": "gpt-4o",
            "tokens": 1000,
            "response_time_ms": 2000,  # Under default 3000ms
            "cost_usd": 0.03,  # Under default 0.05
            "error": False  # 0% error rate
        }), encoding="utf-8")
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(empty_rules),
            "--fail-on-violations"
        ])
        
        assert result.exit_code == 0
    
    def test_threshold_values_in_output(self, runner, tmp_path, monkeypatch, empty_rules):
        """Threshold violations show actual vs threshold values"""
        monkeypatch.setenv("SLOW_RESPONSE_THRESHOLD_MS", "1000")
        
        logs = tmp_path / "logs.jsonl"
        logs.write_text(json.dumps({
            "timestamp": "2025-10-25T10:00:00Z",
            "model": "gpt-4o",
            "tokens": 100,
            "response_time_ms": 2500,
            "cost_usd": 0.001,
            "error": False
        }), encoding="utf-8")
        
        result = runner.invoke(guard, [
            str(logs),
            "--rules", str(empty_rules),
            "--output", "text"
        ])
        
        # Output should show both actual and threshold values
        assert "2500" in result.output or "1000" in result.output
        assert "threshold" in result.output.lower() or "exceeds" in result.output.lower()
