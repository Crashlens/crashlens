#!/usr/bin/env python3
"""
Tests for Dynamic Performance Baseline Calculation
"""

import pytest
from pathlib import Path

from crashlens.performance_baseline import PerformanceBaseline, load_baseline_from_file


class TestPerformanceBaseline:
    """Test dynamic baseline calculation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Historical logs (baseline period)
        self.historical_logs = [
            {"response_time_ms": 100, "cost_usd": 0.01, "error": False},
            {"response_time_ms": 150, "cost_usd": 0.015, "error": False},
            {"response_time_ms": 200, "cost_usd": 0.02, "error": False},
            {"response_time_ms": 250, "cost_usd": 0.025, "error": False},
            {"response_time_ms": 300, "cost_usd": 0.03, "error": False},
            {"response_time_ms": 350, "cost_usd": 0.035, "error": False},
            {"response_time_ms": 400, "cost_usd": 0.04, "error": False},
            {"response_time_ms": 450, "cost_usd": 0.045, "error": False},
            {"response_time_ms": 500, "cost_usd": 0.05, "error": False},
            {"response_time_ms": 550, "cost_usd": 0.055, "error": False},
            {"response_time_ms": 600, "cost_usd": 0.06, "error": False},
            {"response_time_ms": 650, "cost_usd": 0.065, "error": False},
            {"response_time_ms": 700, "cost_usd": 0.07, "error": False},
            {"response_time_ms": 750, "cost_usd": 0.075, "error": False},
            {"response_time_ms": 800, "cost_usd": 0.08, "error": False},
            {"response_time_ms": 850, "cost_usd": 0.085, "error": False},
            {"response_time_ms": 900, "cost_usd": 0.09, "error": False},
            {"response_time_ms": 950, "cost_usd": 0.095, "error": False},
            {"response_time_ms": 1000, "cost_usd": 0.10, "error": False},
            {"response_time_ms": 1050, "cost_usd": 0.105, "error": True},  # 1 error
        ]
        
        # Good current logs (within baseline)
        self.good_current_logs = [
            {"response_time_ms": 120, "cost_usd": 0.012, "error": False},
            {"response_time_ms": 180, "cost_usd": 0.018, "error": False},
            {"response_time_ms": 240, "cost_usd": 0.024, "error": False},
            {"response_time_ms": 300, "cost_usd": 0.030, "error": False},
            {"response_time_ms": 360, "cost_usd": 0.036, "error": False},
            {"response_time_ms": 420, "cost_usd": 0.042, "error": False},
            {"response_time_ms": 480, "cost_usd": 0.048, "error": False},
            {"response_time_ms": 540, "cost_usd": 0.054, "error": False},
            {"response_time_ms": 600, "cost_usd": 0.060, "error": False},
            {"response_time_ms": 660, "cost_usd": 0.066, "error": False},
            {"response_time_ms": 720, "cost_usd": 0.072, "error": False},
            {"response_time_ms": 780, "cost_usd": 0.078, "error": False},
            {"response_time_ms": 840, "cost_usd": 0.084, "error": False},
            {"response_time_ms": 900, "cost_usd": 0.090, "error": False},
            {"response_time_ms": 960, "cost_usd": 0.096, "error": False},
            {"response_time_ms": 1020, "cost_usd": 0.102, "error": False},
            {"response_time_ms": 1080, "cost_usd": 0.108, "error": False},
            {"response_time_ms": 1140, "cost_usd": 0.114, "error": False},
            {"response_time_ms": 1200, "cost_usd": 0.120, "error": False},
            {"response_time_ms": 1260, "cost_usd": 0.126, "error": False},
        ]
        
        # Bad current logs (exceeds baseline by >50%)
        self.bad_current_logs = [
            {"response_time_ms": 2000, "cost_usd": 0.20, "error": False},  # 2x baseline
            {"response_time_ms": 2100, "cost_usd": 0.21, "error": False},
            {"response_time_ms": 2200, "cost_usd": 0.22, "error": False},
            {"response_time_ms": 2300, "cost_usd": 0.23, "error": False},
            {"response_time_ms": 2400, "cost_usd": 0.24, "error": False},
            {"response_time_ms": 2500, "cost_usd": 0.25, "error": False},
            {"response_time_ms": 2600, "cost_usd": 0.26, "error": False},
            {"response_time_ms": 2700, "cost_usd": 0.27, "error": False},
            {"response_time_ms": 2800, "cost_usd": 0.28, "error": False},
            {"response_time_ms": 2900, "cost_usd": 0.29, "error": False},
            {"response_time_ms": 3000, "cost_usd": 0.30, "error": False},
            {"response_time_ms": 3100, "cost_usd": 0.31, "error": False},
            {"response_time_ms": 3200, "cost_usd": 0.32, "error": False},
            {"response_time_ms": 3300, "cost_usd": 0.33, "error": False},
            {"response_time_ms": 3400, "cost_usd": 0.34, "error": False},
            {"response_time_ms": 3500, "cost_usd": 0.35, "error": False},
            {"response_time_ms": 3600, "cost_usd": 0.36, "error": False},
            {"response_time_ms": 3700, "cost_usd": 0.37, "error": False},
            {"response_time_ms": 3800, "cost_usd": 0.38, "error": False},
            {"response_time_ms": 3900, "cost_usd": 0.39, "error": False},
        ]
    
    def test_calculate_baselines(self):
        """Calculate P95/P99 baselines from historical data"""
        baseline = PerformanceBaseline(self.historical_logs)
        baselines = baseline.calculate_baselines()
        
        # Check all metrics present
        assert 'latency_p95' in baselines
        assert 'latency_p99' in baselines
        assert 'cost_p95' in baselines
        assert 'cost_p99' in baselines
        assert 'error_rate' in baselines
        
        # Check reasonable values
        assert baselines['latency_p95'] > 0
        assert baselines['latency_p99'] > baselines['latency_p95']
        assert baselines['cost_p95'] > 0
        assert baselines['cost_p99'] > baselines['cost_p95']
        assert 0 <= baselines['error_rate'] <= 1
    
    def test_empty_logs_raises_error(self):
        """Empty historical logs raise ValueError"""
        baseline = PerformanceBaseline([])
        
        with pytest.raises(ValueError, match="empty historical logs"):
            baseline.calculate_baselines()
    
    def test_get_baselines_caches_result(self):
        """get_baselines() caches calculation"""
        baseline = PerformanceBaseline(self.historical_logs)
        
        # First call calculates
        baselines1 = baseline.get_baselines()
        
        # Second call uses cache
        baselines2 = baseline.get_baselines()
        
        # Should be same object
        assert baselines1 is baselines2
    
    def test_compare_good_logs_no_violations(self):
        """Logs within baseline don't trigger violations"""
        baseline = PerformanceBaseline(self.historical_logs)
        
        has_violations, violations = baseline.compare_to_baseline(
            self.good_current_logs,
            deviation_threshold=0.50  # 50% above baseline
        )
        
        # Should not have violations
        assert has_violations is False
        assert len(violations) == 0
    
    def test_compare_bad_logs_triggers_violations(self):
        """Logs exceeding baseline trigger violations"""
        baseline = PerformanceBaseline(self.historical_logs)
        
        has_violations, violations = baseline.compare_to_baseline(
            self.bad_current_logs,
            deviation_threshold=0.50  # 50% above baseline
        )
        
        # Should have violations
        assert has_violations is True
        assert len(violations) > 0
        
        # Check violation structure
        for violation in violations:
            assert 'metric' in violation
            assert 'baseline' in violation
            assert 'current' in violation
            assert 'deviation_threshold' in violation
            assert 'percent_increase' in violation
            assert 'description' in violation
    
    def test_deviation_threshold_30_percent(self):
        """Custom deviation threshold (30%)"""
        baseline = PerformanceBaseline(self.historical_logs)
        
        # Logs that are 40% above baseline
        moderate_logs = [
            {"response_time_ms": int(log["response_time_ms"] * 1.4), 
             "cost_usd": log["cost_usd"] * 1.4, 
             "error": False}
            for log in self.historical_logs
        ]
        
        # With 50% threshold, should pass
        has_violations_50, _ = baseline.compare_to_baseline(moderate_logs, 0.50)
        assert has_violations_50 is False
        
        # With 30% threshold, should fail
        has_violations_30, _ = baseline.compare_to_baseline(moderate_logs, 0.30)
        assert has_violations_30 is True
    
    def test_compare_empty_current_logs(self):
        """Empty current logs return no violations"""
        baseline = PerformanceBaseline(self.historical_logs)
        
        has_violations, violations = baseline.compare_to_baseline([])
        
        assert has_violations is False
        assert len(violations) == 0
    
    def test_get_summary_format(self):
        """get_summary() returns formatted string"""
        baseline = PerformanceBaseline(self.historical_logs)
        summary = baseline.get_summary()
        
        assert "Dynamic Performance Baselines" in summary
        assert "Historical samples:" in summary
        assert "Latency P95:" in summary
        assert "Latency P99:" in summary
        assert "Cost P95:" in summary
        assert "Cost P99:" in summary
        assert "Error Rate:" in summary
    
    def test_error_rate_violation(self):
        """High error rate triggers violation"""
        baseline = PerformanceBaseline(self.historical_logs)
        
        # Current logs with high error rate (50%)
        high_error_logs = [
            {"response_time_ms": 500, "cost_usd": 0.05, "error": i % 2 == 0}
            for i in range(20)
        ]
        
        has_violations, violations = baseline.compare_to_baseline(high_error_logs)
        
        # Should trigger error rate violation
        assert has_violations is True
        error_violations = [v for v in violations if v['metric'] == 'error_rate']
        assert len(error_violations) > 0
    
    def test_latency_ms_field_name(self):
        """Support latency_ms field name (alternative to response_time_ms)"""
        logs_with_latency = [
            {"latency_ms": 100, "cost_usd": 0.01, "error": False}
            for _ in range(20)
        ]
        
        baseline = PerformanceBaseline(logs_with_latency)
        baselines = baseline.calculate_baselines()
        
        assert baselines['latency_p95'] > 0
        assert baselines['latency_p99'] > 0
    
    def test_status_error_field(self):
        """Support status='error' field (alternative to error=True)"""
        logs_with_status = [
            {"response_time_ms": 100, "cost_usd": 0.01, "status": "error" if i % 5 == 0 else "success"}
            for i in range(20)
        ]
        
        baseline = PerformanceBaseline(logs_with_status)
        baselines = baseline.calculate_baselines()
        
        # Should detect errors via status field
        assert baselines['error_rate'] > 0


class TestLoadBaselineFromFile:
    """Test loading baselines from JSONL files"""
    
    def test_load_from_file(self, tmp_path):
        """Load baseline from JSONL file"""
        # Create test file
        log_file = tmp_path / "baseline.jsonl"
        log_file.write_text("""{"response_time_ms": 100, "cost_usd": 0.01, "error": false}
{"response_time_ms": 200, "cost_usd": 0.02, "error": false}
{"response_time_ms": 300, "cost_usd": 0.03, "error": false}
{"response_time_ms": 400, "cost_usd": 0.04, "error": false}
{"response_time_ms": 500, "cost_usd": 0.05, "error": false}
{"response_time_ms": 600, "cost_usd": 0.06, "error": false}
{"response_time_ms": 700, "cost_usd": 0.07, "error": false}
{"response_time_ms": 800, "cost_usd": 0.08, "error": false}
{"response_time_ms": 900, "cost_usd": 0.09, "error": false}
{"response_time_ms": 1000, "cost_usd": 0.10, "error": false}
{"response_time_ms": 1100, "cost_usd": 0.11, "error": false}
{"response_time_ms": 1200, "cost_usd": 0.12, "error": false}
{"response_time_ms": 1300, "cost_usd": 0.13, "error": false}
{"response_time_ms": 1400, "cost_usd": 0.14, "error": false}
{"response_time_ms": 1500, "cost_usd": 0.15, "error": false}
{"response_time_ms": 1600, "cost_usd": 0.16, "error": false}
{"response_time_ms": 1700, "cost_usd": 0.17, "error": false}
{"response_time_ms": 1800, "cost_usd": 0.18, "error": false}
{"response_time_ms": 1900, "cost_usd": 0.19, "error": false}
{"response_time_ms": 2000, "cost_usd": 0.20, "error": false}
""")
        
        baseline = load_baseline_from_file(log_file)
        
        # Should successfully load
        assert baseline is not None
        assert len(baseline.historical_logs) == 20
        
        # Can calculate baselines
        baselines = baseline.get_baselines()
        assert baselines['latency_p95'] > 0
    
    def test_load_nonexistent_file_raises_error(self):
        """Nonexistent file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            load_baseline_from_file(Path("/nonexistent/file.jsonl"))
    
    def test_load_empty_file_raises_error(self, tmp_path):
        """Empty file raises ValueError"""
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("")
        
        with pytest.raises(ValueError, match="empty"):
            load_baseline_from_file(empty_file)
