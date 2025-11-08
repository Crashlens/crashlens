"""
Integration tests for GuardPolicyEngineAdapter

Tests the feature-flagged integration between guard and PolicyEngine.
"""

import pytest
import os
import tempfile
from pathlib import Path
import yaml
import json

from crashlens.guard_adapter import (
    GuardPolicyEngineAdapter,
    should_use_unified_engine,
)


@pytest.fixture
def sample_rules_yaml(tmp_path):
    """Create a sample rules.yaml file."""
    rules_path = tmp_path / "rules.yaml"
    rules = {
        "rules": [
            {
                "id": "TEST001",
                "description": "Test rule for retry count",
                "if": {
                    "retry_count": {">": 3}
                },
                "action": "error",
                "severity": "error"
            },
            {
                "id": "TEST002",
                "description": "Test rule for expensive requests",
                "if": {
                    "cost_usd": {">": 0.10}
                },
                "action": "warn",
                "severity": "warn"
            },
        ]
    }
    
    with open(rules_path, 'w') as f:
        yaml.dump(rules, f)
    
    return rules_path


@pytest.fixture
def sample_logs_jsonl(tmp_path):
    """Create a sample JSONL log file."""
    log_path = tmp_path / "logs.jsonl"
    
    entries = [
        {
            "id": 1,
            "traceId": "trace-001",
            "model": "gpt-4",
            "retry_count": 2,
            "cost_usd": 0.05,
            "prompt": "Test prompt",
        },
        {
            "id": 2,
            "traceId": "trace-002",
            "model": "gpt-4",
            "retry_count": 5,  # Violates TEST001
            "cost_usd": 0.03,
            "prompt": "Test prompt 2",
        },
        {
            "id": 3,
            "traceId": "trace-003",
            "model": "gpt-4",
            "retry_count": 1,
            "cost_usd": 0.15,  # Violates TEST002
            "prompt": "Test prompt 3",
        },
    ]
    
    with open(log_path, 'w') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')
    
    return log_path


class TestFeatureFlag:
    """Test feature flag behavior."""
    
    def test_feature_flag_disabled_by_default(self, monkeypatch):
        """Test that unified engine is disabled by default."""
        monkeypatch.delenv("CRASHLENS_USE_UNIFIED_ENGINE", raising=False)
        assert not should_use_unified_engine()
    
    def test_feature_flag_enabled_with_env_var(self, monkeypatch):
        """Test that unified engine can be enabled via env var."""
        monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")
        assert should_use_unified_engine()
    
    def test_feature_flag_disabled_with_zero(self, monkeypatch):
        """Test that unified engine is disabled with 0."""
        monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "0")
        assert not should_use_unified_engine()


class TestAdapterInitialization:
    """Test adapter initialization."""
    
    def test_adapter_disabled_by_default(self, sample_rules_yaml, monkeypatch):
        """Test that adapter is disabled when feature flag is off."""
        monkeypatch.delenv("CRASHLENS_USE_UNIFIED_ENGINE", raising=False)
        
        adapter = GuardPolicyEngineAdapter(
            rules_yaml_path=sample_rules_yaml,
            detector_mode="none",
        )
        
        assert not adapter.is_enabled()
        assert adapter.policy_engine is None
        assert adapter.detector_driver is None
    
    def test_adapter_enabled_with_flag(self, sample_rules_yaml, monkeypatch):
        """Test that adapter is enabled when feature flag is on."""
        monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")
        
        adapter = GuardPolicyEngineAdapter(
            rules_yaml_path=sample_rules_yaml,
            detector_mode="none",
            verbose=True,
        )
        
        assert adapter.is_enabled()
        assert adapter.policy_engine is not None
        assert adapter.detector_driver is None  # mode=none
    
    def test_adapter_with_detector_driver(self, sample_rules_yaml, monkeypatch):
        """Test that detector driver is initialized in inline mode."""
        monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")
        
        adapter = GuardPolicyEngineAdapter(
            rules_yaml_path=sample_rules_yaml,
            detector_mode="inline",
            detector_config={"retry_loop": {"max_retries": 2}},
        )
        
        assert adapter.is_enabled()
        assert adapter.detector_driver is not None


class TestLogProcessing:
    """Test log processing with adapter."""
    
    def test_process_logs_disabled(self, sample_rules_yaml, sample_logs_jsonl, monkeypatch):
        """Test that processing returns empty when disabled."""
        monkeypatch.delenv("CRASHLENS_USE_UNIFIED_ENGINE", raising=False)
        
        adapter = GuardPolicyEngineAdapter(
            rules_yaml_path=sample_rules_yaml,
            detector_mode="none",
        )
        
        violations, metrics = adapter.process_logs([sample_logs_jsonl])
        
        assert violations == {}
        assert metrics == {}
    
    def test_process_logs_enabled(self, sample_rules_yaml, sample_logs_jsonl, monkeypatch):
        """Test that processing works when enabled."""
        monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")
        
        adapter = GuardPolicyEngineAdapter(
            rules_yaml_path=sample_rules_yaml,
            detector_mode="none",
            verbose=False,
        )
        
        violations, metrics = adapter.process_logs([sample_logs_jsonl])
        
        # Should have violations
        assert len(violations) > 0
        assert "TEST001" in violations or "TEST002" in violations
        
        # Should have metrics
        assert "total_records" in metrics
        assert metrics["total_records"] == 3
        assert metrics["used_unified_engine"] is True
    
    def test_suppression_works(self, sample_rules_yaml, sample_logs_jsonl, monkeypatch):
        """Test that rule suppression works."""
        monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")
        
        adapter = GuardPolicyEngineAdapter(
            rules_yaml_path=sample_rules_yaml,
            detector_mode="none",
            suppress_ids={"TEST001"},  # Suppress TEST001
        )
        
        violations, metrics = adapter.process_logs([sample_logs_jsonl])
        
        # TEST001 should be suppressed
        assert "TEST001" not in violations
        # TEST002 might still be present
    
    def test_multiple_files(self, sample_rules_yaml, tmp_path, monkeypatch):
        """Test processing multiple log files."""
        monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")
        
        # Create two log files
        log1 = tmp_path / "log1.jsonl"
        log2 = tmp_path / "log2.jsonl"
        
        with open(log1, 'w') as f:
            f.write(json.dumps({"id": 1, "traceId": "t1", "retry_count": 5}) + '\n')
        
        with open(log2, 'w') as f:
            f.write(json.dumps({"id": 2, "traceId": "t2", "retry_count": 6}) + '\n')
        
        adapter = GuardPolicyEngineAdapter(
            rules_yaml_path=sample_rules_yaml,
            detector_mode="none",
        )
        
        violations, metrics = adapter.process_logs([log1, log2])
        
        assert metrics["total_records"] == 2


class TestLegacyFormatConversion:
    """Test conversion from PolicyEngine format to legacy guard format."""
    
    def test_convert_violations_to_legacy(self, sample_rules_yaml, sample_logs_jsonl, monkeypatch):
        """Test conversion to legacy format."""
        monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")
        
        adapter = GuardPolicyEngineAdapter(
            rules_yaml_path=sample_rules_yaml,
            detector_mode="none",
        )
        
        violations, metrics = adapter.process_logs([sample_logs_jsonl])
        
        legacy_results = adapter.convert_violations_to_legacy_format(
            violations,
            strip_pii=False,
            no_content=False,
            max_examples=5,
        )
        
        # Check legacy format structure
        for rule_id, result in legacy_results.items():
            assert "count" in result
            assert "examples" in result
            assert "severity" in result
            assert result["severity"] in ["warn", "error", "fatal"]
            
            # Check examples structure
            for example in result["examples"]:
                assert "timestamp" in example or "model" in example
    
    def test_severity_mapping(self, sample_rules_yaml, sample_logs_jsonl, monkeypatch):
        """Test that PolicySeverity maps correctly to legacy severity."""
        monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")
        
        adapter = GuardPolicyEngineAdapter(
            rules_yaml_path=sample_rules_yaml,
            detector_mode="none",
        )
        
        violations, metrics = adapter.process_logs([sample_logs_jsonl])
        legacy_results = adapter.convert_violations_to_legacy_format(violations)
        
        # Verify severity values are in expected set
        for result in legacy_results.values():
            assert result["severity"] in ["warn", "error", "fatal"]
    
    def test_no_content_flag(self, sample_rules_yaml, sample_logs_jsonl, monkeypatch):
        """Test that no_content flag excludes examples."""
        monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")
        
        adapter = GuardPolicyEngineAdapter(
            rules_yaml_path=sample_rules_yaml,
            detector_mode="none",
        )
        
        violations, metrics = adapter.process_logs([sample_logs_jsonl])
        legacy_results = adapter.convert_violations_to_legacy_format(
            violations,
            no_content=True,
        )
        
        # Examples should be empty
        for result in legacy_results.values():
            assert result["examples"] == []
    
    def test_max_examples_limit(self, sample_rules_yaml, monkeypatch):
        """Test that max_examples limits examples."""
        monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")
        
        # Create log file with many violations
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for i in range(10):
                f.write(json.dumps({
                    "id": i,
                    "traceId": f"t{i}",
                    "retry_count": 5,  # Violates TEST001
                }) + '\n')
            log_path = Path(f.name)
        
        try:
            adapter = GuardPolicyEngineAdapter(
                rules_yaml_path=sample_rules_yaml,
                detector_mode="none",
            )
            
            violations, metrics = adapter.process_logs([log_path])
            legacy_results = adapter.convert_violations_to_legacy_format(
                violations,
                max_examples=3,
            )
            
            # Should have at most 3 examples
            for result in legacy_results.values():
                assert len(result["examples"]) <= 3
        finally:
            log_path.unlink()


class TestDetectorIntegration:
    """Test detector driver integration."""
    
    def test_inline_detection_enriches_logs(self, sample_rules_yaml, monkeypatch):
        """Test that inline detection enriches logs before evaluation."""
        monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")
        
        # Create logs with retry pattern
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for i in range(4):
                f.write(json.dumps({
                    "id": i,
                    "traceId": "trace-retry",
                    "startTime": f"2024-01-01T10:0{i}:00Z",
                    "model": "gpt-4",
                    "prompt": "Same prompt",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20},
                }) + '\n')
            log_path = Path(f.name)
        
        try:
            adapter = GuardPolicyEngineAdapter(
                rules_yaml_path=sample_rules_yaml,
                detector_mode="inline",
                detector_config={"retry_loop": {"max_retries": 2}},
                verbose=False,
            )
            
            violations, metrics = adapter.process_logs([log_path])
            
            # Check that detector metrics are present
            assert "detector_time_ms" in metrics
            # Detector should have run
            assert metrics["detector_time_ms"] >= 0
        finally:
            log_path.unlink()


class TestBackwardsCompatibility:
    """Test backwards compatibility when feature flag is off."""
    
    def test_disabled_has_no_side_effects(self, sample_rules_yaml, sample_logs_jsonl, monkeypatch):
        """Test that disabled adapter has no side effects."""
        monkeypatch.delenv("CRASHLENS_USE_UNIFIED_ENGINE", raising=False)
        
        adapter = GuardPolicyEngineAdapter(
            rules_yaml_path=sample_rules_yaml,
            detector_mode="inline",  # Even with inline mode
        )
        
        # Should initialize successfully
        assert not adapter.is_enabled()
        
        # Should return empty results
        violations, metrics = adapter.process_logs([sample_logs_jsonl])
        assert violations == {}
        assert metrics == {}
    
    def test_can_toggle_flag_at_runtime(self, sample_rules_yaml, sample_logs_jsonl, monkeypatch):
        """Test that feature flag can be toggled (for testing)."""
        # Start disabled
        monkeypatch.delenv("CRASHLENS_USE_UNIFIED_ENGINE", raising=False)
        
        adapter1 = GuardPolicyEngineAdapter(
            rules_yaml_path=sample_rules_yaml,
            detector_mode="none",
        )
        assert not adapter1.is_enabled()
        
        # Enable flag
        monkeypatch.setenv("CRASHLENS_USE_UNIFIED_ENGINE", "1")
        
        adapter2 = GuardPolicyEngineAdapter(
            rules_yaml_path=sample_rules_yaml,
            detector_mode="none",
        )
        assert adapter2.is_enabled()
