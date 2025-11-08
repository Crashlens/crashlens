"""
Tests for Baseline Injection (Step 6)

Validates that PerformanceBaseline.generate_synthetic_violations() creates
properly structured violation objects and integrates correctly with guard reporting.
"""

import json
import statistics
from pathlib import Path
from typing import Any, Dict, List

import pytest

from crashlens.performance_baseline import PerformanceBaseline, load_baseline_from_file


class TestSyntheticViolationGeneration:
    """Test generate_synthetic_violations() method"""
    
    @pytest.fixture
    def historical_logs_normal(self) -> List[Dict[str, Any]]:
        """Create historical logs with normal performance"""
        logs = []
        for i in range(100):
            logs.append({
                "timestamp": f"2025-01-0{1+(i//10):01d}T10:{i%60:02d}:00Z",
                "model": "gpt-4" if i % 2 == 0 else "gpt-3.5-turbo",
                "response_time_ms": 1000 + (i % 500),  # 1000-1500ms
                "cost_usd": 0.01 + (i % 10) * 0.001,  # $0.01-0.02
                "error": False,
            })
        return logs
    
    @pytest.fixture
    def current_logs_degraded(self) -> List[Dict[str, Any]]:
        """Create current logs with degraded performance (2x latency, 2x cost)"""
        logs = []
        for i in range(100):
            logs.append({
                "timestamp": f"2025-01-10T10:{i%60:02d}:00Z",
                "model": "gpt-4" if i % 2 == 0 else "gpt-3.5-turbo",
                "response_time_ms": 2000 + (i % 1000),  # 2000-3000ms (2x baseline)
                "cost_usd": 0.02 + (i % 10) * 0.002,  # $0.02-0.04 (2x baseline)
                "error": False,
            })
        return logs
    
    @pytest.fixture
    def current_logs_normal(self) -> List[Dict[str, Any]]:
        """Create current logs with normal performance matching baseline"""
        logs = []
        for i in range(100):
            logs.append({
                "timestamp": f"2025-01-10T10:{i%60:02d}:00Z",
                "model": "gpt-4",
                "response_time_ms": 1050 + (i % 100),  # Slight variation, within baseline
                "cost_usd": 0.011 + (i % 10) * 0.0005,
                "error": False,
            })
        return logs
    
    def test_no_violations_when_within_baseline(self, historical_logs_normal, current_logs_normal):
        """Should return empty list when current metrics are within baseline"""
        baseline = PerformanceBaseline(historical_logs_normal)
        violations = baseline.generate_synthetic_violations(
            current_logs_normal,
            deviation_threshold=0.50  # 50% threshold
        )
        
        assert violations == []
    
    def test_latency_violation_generated(self, historical_logs_normal, current_logs_degraded):
        """Should generate violation when latency exceeds baseline + threshold"""
        baseline = PerformanceBaseline(historical_logs_normal)
        violations = baseline.generate_synthetic_violations(
            current_logs_degraded,
            deviation_threshold=0.50  # 50% threshold
        )
        
        # Should have latency violations
        latency_violations = [v for v in violations if 'latency' in v['id']]
        assert len(latency_violations) > 0
        
        # Check violation structure
        v = latency_violations[0]
        assert v['id'].startswith('baseline_')
        assert v['severity'] == 'fatal'
        assert v['count'] == 1
        assert v['examples'] == []
        assert 'baseline_value' in v
        assert 'current_value' in v
        assert 'percent_increase' in v
        assert v['percent_increase'] > 50.0  # Should be >50% increase
    
    def test_cost_violation_generated(self, historical_logs_normal, current_logs_degraded):
        """Should generate violation when cost exceeds baseline + threshold"""
        baseline = PerformanceBaseline(historical_logs_normal)
        violations = baseline.generate_synthetic_violations(
            current_logs_degraded,
            deviation_threshold=0.50
        )
        
        # Should have cost violations
        cost_violations = [v for v in violations if 'cost' in v['id']]
        assert len(cost_violations) > 0
        
        v = cost_violations[0]
        assert 'baseline_cost' in v['id'] or 'cost_p' in v['id']
        assert v['severity'] == 'fatal'
    
    def test_multiple_violations_generated(self, historical_logs_normal, current_logs_degraded):
        """Should generate multiple violations when multiple metrics exceed baseline"""
        baseline = PerformanceBaseline(historical_logs_normal)
        violations = baseline.generate_synthetic_violations(
            current_logs_degraded,
            deviation_threshold=0.50
        )
        
        # Should have both latency and cost violations
        assert len(violations) >= 2
        
        violation_types = {v['id'] for v in violations}
        assert any('latency' in vid for vid in violation_types)
        assert any('cost' in vid for vid in violation_types)
    
    def test_violation_format_compatible_with_guard(self, historical_logs_normal, current_logs_degraded):
        """Violation structure should be compatible with guard report format"""
        baseline = PerformanceBaseline(historical_logs_normal)
        violations = baseline.generate_synthetic_violations(
            current_logs_degraded,
            deviation_threshold=0.50
        )
        
        assert len(violations) > 0
        
        # Check all required guard report fields
        required_fields = ['id', 'name', 'severity', 'description', 'count', 'examples']
        for v in violations:
            for field in required_fields:
                assert field in v, f"Missing field '{field}' in violation"
            
            # Check types
            assert isinstance(v['id'], str)
            assert isinstance(v['name'], str)
            assert isinstance(v['severity'], str)
            assert isinstance(v['description'], str)
            assert isinstance(v['count'], int)
            assert isinstance(v['examples'], list)
    
    def test_violation_description_includes_metrics(self, historical_logs_normal, current_logs_degraded):
        """Violation description should include baseline and current values"""
        baseline = PerformanceBaseline(historical_logs_normal)
        violations = baseline.generate_synthetic_violations(
            current_logs_degraded,
            deviation_threshold=0.50
        )
        
        assert len(violations) > 0
        
        # Check description contains metrics
        for v in violations:
            desc = v['description']
            assert 'baseline' in desc.lower() or 'above' in desc.lower()
            # Should contain numeric values
            assert any(char.isdigit() for char in desc)
    
    def test_custom_deviation_threshold(self, historical_logs_normal):
        """Should respect custom deviation threshold"""
        baseline = PerformanceBaseline(historical_logs_normal)
        
        # Create logs with 30% increase
        logs_30pct_increase = []
        for i in range(100):
            logs_30pct_increase.append({
                "response_time_ms": 1300 + (i % 200),  # 30% increase
                "cost_usd": 0.013 + (i % 10) * 0.0013,
                "error": False,
            })
        
        # Should violate with 20% threshold
        violations_20pct = baseline.generate_synthetic_violations(
            logs_30pct_increase, deviation_threshold=0.20
        )
        assert len(violations_20pct) > 0
        
        # Should NOT violate with 40% threshold
        violations_40pct = baseline.generate_synthetic_violations(
            logs_30pct_increase, deviation_threshold=0.40
        )
        assert len(violations_40pct) == 0
    
    def test_empty_current_logs(self, historical_logs_normal):
        """Should return empty list when current logs are empty"""
        baseline = PerformanceBaseline(historical_logs_normal)
        violations = baseline.generate_synthetic_violations([], deviation_threshold=0.50)
        
        assert violations == []
    
    def test_violation_includes_baseline_specific_fields(self, historical_logs_normal, current_logs_degraded):
        """Should include baseline-specific fields in addition to guard fields"""
        baseline = PerformanceBaseline(historical_logs_normal)
        violations = baseline.generate_synthetic_violations(
            current_logs_degraded,
            deviation_threshold=0.50
        )
        
        assert len(violations) > 0
        
        # Check baseline-specific fields
        v = violations[0]
        assert 'baseline_value' in v
        assert 'current_value' in v
        assert 'percent_increase' in v
        assert 'deviation_threshold' in v
        
        # Verify they are numeric
        assert isinstance(v['baseline_value'], (int, float))
        assert isinstance(v['current_value'], (int, float))
        assert isinstance(v['percent_increase'], (int, float))
        assert isinstance(v['deviation_threshold'], (int, float))


class TestBaselineIntegrationWithGuard:
    """Test integration with guard.py workflow"""
    
    @pytest.fixture
    def temp_historical_logs(self, tmp_path):
        """Create temporary historical logs file"""
        log_file = tmp_path / "historical.jsonl"
        logs = []
        for i in range(50):
            logs.append({
                "timestamp": f"2025-01-01T10:00:{i:02d}Z",
                "model": "gpt-4",
                "response_time_ms": 1000 + i * 10,
                "cost_usd": 0.01,
                "error": False,
            })
        
        with open(log_file, 'w') as f:
            for log in logs:
                f.write(json.dumps(log) + "\n")
        
        return log_file
    
    def test_load_baseline_from_file(self, temp_historical_logs):
        """Should load baseline from JSONL file"""
        baseline = load_baseline_from_file(temp_historical_logs)
        
        assert isinstance(baseline, PerformanceBaseline)
        assert len(baseline.historical_logs) == 50
    
    def test_load_baseline_nonexistent_file(self, tmp_path):
        """Should raise FileNotFoundError for missing file"""
        nonexistent = tmp_path / "nonexistent.jsonl"
        
        with pytest.raises(FileNotFoundError):
            load_baseline_from_file(nonexistent)
    
    def test_load_baseline_empty_file(self, tmp_path):
        """Should raise ValueError for empty file"""
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("")
        
        with pytest.raises(ValueError, match="empty"):
            load_baseline_from_file(empty_file)
    
    def test_synthetic_violations_can_be_added_to_results(self, temp_historical_logs):
        """Synthetic violations should integrate with guard results dict"""
        baseline = load_baseline_from_file(temp_historical_logs)
        
        # Create degraded logs
        current_logs = [
            {"response_time_ms": 2000, "cost_usd": 0.02, "error": False}
            for _ in range(50)
        ]
        
        violations = baseline.generate_synthetic_violations(
            current_logs, deviation_threshold=0.30
        )
        
        # Simulate adding to guard results
        guard_results = {
            "rule1": {"count": 1, "severity": "error", "examples": []},
        }
        
        # Add synthetic violations (as guard.py does)
        for v in violations:
            guard_results[v['id']] = {
                "count": v['count'],
                "severity": v['severity'],
                "description": v['description'],
                "examples": v['examples'],
            }
        
        # Should have original rule + baseline violations
        assert len(guard_results) > 1
        assert any('baseline_' in key for key in guard_results.keys())


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_single_log_entry(self):
        """Should handle single historical log entry gracefully"""
        # Note: statistics.quantiles() requires at least 2 data points
        # So baseline calculation will fail with single entry
        
        with pytest.raises(ValueError, match="Cannot calculate baselines|at least two"):
            baseline = PerformanceBaseline([
                {"response_time_ms": 1000, "cost_usd": 0.01, "error": False}
            ])
            baseline.calculate_baselines()
    
    def test_missing_fields_in_logs(self):
        """Should handle logs with missing performance fields"""
        baseline = PerformanceBaseline([
            {"timestamp": "2025-01-01T10:00:00Z", "model": "gpt-4"}
            # Missing response_time_ms, cost_usd
            for _ in range(10)
        ])
        
        current = [
            {"timestamp": "2025-01-10T10:00:00Z", "model": "gpt-4"}
            for _ in range(10)
        ]
        
        violations = baseline.generate_synthetic_violations(current, deviation_threshold=0.50)
        
        # Should not crash, return empty violations (no metrics to compare)
        assert violations == []
    
    def test_mixed_field_presence(self):
        """Should handle logs where some have metrics and some don't"""
        historical = [
            {"response_time_ms": 1000, "cost_usd": 0.01, "error": False}
            for _ in range(50)
        ]
        historical.extend([
            {"timestamp": "2025-01-01T10:00:00Z"}  # No metrics
            for _ in range(10)
        ])
        
        baseline = PerformanceBaseline(historical)
        
        current = [
            {"response_time_ms": 2000, "cost_usd": 0.02, "error": False}
            for _ in range(50)
        ]
        
        violations = baseline.generate_synthetic_violations(current, deviation_threshold=0.50)
        
        # Should still work with the logs that have metrics
        assert isinstance(violations, list)
    
    def test_zero_baseline_values(self):
        """Should handle zero baseline values gracefully"""
        baseline = PerformanceBaseline([
            {"response_time_ms": 0, "cost_usd": 0.0, "error": False}
            for _ in range(10)
        ])
        
        current = [
            {"response_time_ms": 1000, "cost_usd": 0.01, "error": False}
            for _ in range(10)
        ]
        
        violations = baseline.generate_synthetic_violations(current, deviation_threshold=0.50)
        
        # Should not crash (division by zero should be handled)
        assert isinstance(violations, list)
    
    def test_negative_deviation_threshold_fails(self):
        """Should handle negative deviation threshold"""
        baseline = PerformanceBaseline([
            {"response_time_ms": 1000, "cost_usd": 0.01, "error": False}
            for _ in range(10)
        ])
        
        current = [
            {"response_time_ms": 1000, "cost_usd": 0.01, "error": False}
            for _ in range(10)
        ]
        
        # Negative threshold should still work (everything will violate)
        violations = baseline.generate_synthetic_violations(current, deviation_threshold=-0.50)
        
        # Should work but likely generate violations
        assert isinstance(violations, list)


class TestBackwardsCompatibility:
    """Ensure changes maintain backwards compatibility"""
    
    def test_compare_to_baseline_still_works(self):
        """Old compare_to_baseline() method should still work"""
        historical = [
            {"response_time_ms": 1000 + i * 5, "cost_usd": 0.01, "error": False}
            for i in range(50)
        ]
        baseline = PerformanceBaseline(historical)
        
        current = [
            {"response_time_ms": 2000, "cost_usd": 0.02, "error": False}
            for _ in range(50)
        ]
        
        has_violations, violations = baseline.compare_to_baseline(
            current, deviation_threshold=0.50
        )
        
        assert isinstance(has_violations, bool)
        assert isinstance(violations, list)
    
    def test_get_baselines_still_works(self):
        """Baseline calculation methods should still work"""
        historical = [
            {"response_time_ms": 1000 + i * 10, "cost_usd": 0.01, "error": False}
            for i in range(50)
        ]
        baseline = PerformanceBaseline(historical)
        
        baselines = baseline.get_baselines()
        
        assert 'latency_p95' in baselines
        assert 'cost_p95' in baselines
        assert isinstance(baselines['latency_p95'], (int, float))
