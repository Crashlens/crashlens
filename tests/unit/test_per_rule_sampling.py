"""
Unit tests for per-rule sampling functionality.

Tests the per-rule sampling feature that allows different sampling rates
for different policy rules in high-cardinality environments.

Uses mocks to test without requiring prometheus-client installed.
"""

import random
import sys
from unittest.mock import MagicMock, patch

import pytest


class TestPerRuleSampling:
    """Test per-rule sampling feature."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use deterministic random seed for reproducible tests
        random.seed(42)
        
        # Sample per-rule rates
        self.per_rule_rates = {
            "high_frequency_rule": 0.01,  # 1% sampling
            "medium_frequency_rule": 0.1,  # 10% sampling
            "critical_rule": 1.0,  # 100% sampling (always record)
            "disabled_rule": 0.0,  # 0% sampling (never record)
        }
        
        # Mock prometheus_client
        self.mock_prom = MagicMock()
        self.mock_counter = MagicMock()
        self.mock_gauge = MagicMock()
        
        self.mock_prom.Counter.return_value = self.mock_counter
        self.mock_prom.Gauge.return_value = self.mock_gauge
        
        # Patch modules for all tests
        self.patcher = patch.dict(sys.modules, {'prometheus_client': self.mock_prom})
        self.patcher.start()
        
        # Patch all the module-level flags and classes
        self.flag_patcher = patch('crashlens.observability.metrics._prometheus_available', True)
        self.counter_patcher = patch('crashlens.observability.metrics._Counter', self.mock_prom.Counter)
        self.gauge_patcher = patch('crashlens.observability.metrics._Gauge', self.mock_prom.Gauge)
        
        self.flag_patcher.start()
        self.counter_patcher.start()
        self.gauge_patcher.start()
    
    def teardown_method(self):
        """Tear down test fixtures."""
        self.patcher.stop()
        self.flag_patcher.stop()
        self.counter_patcher.stop()
        self.gauge_patcher.stop()

    def test_get_sample_rate_with_per_rule_override(self):
        """Test _get_sample_rate returns per-rule rate when available."""
        from crashlens.observability.metrics import CrashLensMetrics
        
        metrics = CrashLensMetrics(
            max_rules=100,
            sample_rate=0.5,  # Global rate
            per_rule_rates=self.per_rule_rates
        )
        
        # Should return per-rule rates
        assert metrics._get_sample_rate("high_frequency_rule") == 0.01
        assert metrics._get_sample_rate("medium_frequency_rule") == 0.1
        assert metrics._get_sample_rate("critical_rule") == 1.0
        assert metrics._get_sample_rate("disabled_rule") == 0.0

    def test_get_sample_rate_fallback_to_global(self):
        """Test _get_sample_rate falls back to global rate when rule not in per_rule_rates."""
        from crashlens.observability.metrics import CrashLensMetrics
        
        metrics = CrashLensMetrics(
            max_rules=100,
            sample_rate=0.5,  # Global rate
            per_rule_rates=self.per_rule_rates
        )
        
        # Rule not in per_rule_rates should use global rate
        assert metrics._get_sample_rate("unknown_rule") == 0.5
        assert metrics._get_sample_rate("another_rule") == 0.5

    def test_get_sample_rate_without_per_rule_rates(self):
        """Test _get_sample_rate works when per_rule_rates is None."""
        from crashlens.observability.metrics import CrashLensMetrics
        
        metrics = CrashLensMetrics(
            max_rules=100,
            sample_rate=0.3,  # Global rate
            per_rule_rates=None  # No per-rule overrides
        )
        
        # All rules should use global rate
        assert metrics._get_sample_rate("any_rule") == 0.3
        assert metrics._get_sample_rate("another_rule") == 0.3

    def test_empty_per_rule_rates_dict(self):
        """Test that empty per_rule_rates dict works (all rules use global rate)."""
        from crashlens.observability.metrics import CrashLensMetrics
        
        metrics = CrashLensMetrics(
            max_rules=100,
            sample_rate=0.3,
            per_rule_rates={}  # Empty dict
        )
        
        # All rules should fall back to global rate
        assert metrics._get_sample_rate("rule1") == 0.3
        assert metrics._get_sample_rate("rule2") == 0.3

    def test_backwards_compatibility_without_per_rule_rates(self):
        """Test that metrics work without per_rule_rates (backwards compatible)."""
        from crashlens.observability.metrics import CrashLensMetrics
        
        metrics = CrashLensMetrics(
            max_rules=100,
            sample_rate=0.2  # Global rate only
        )
        
        # Should work fine with just global rate
        assert metrics._per_rule_rates == {}
        assert metrics._get_sample_rate("any_rule") == 0.2

    def test_per_rule_rate_precedence_over_global(self):
        """Test that per-rule rates take precedence over global rate."""
        from crashlens.observability.metrics import CrashLensMetrics
        
        metrics = CrashLensMetrics(
            max_rules=100,
            sample_rate=0.5,  # Global rate 50%
            per_rule_rates={
                "override_low": 0.01,  # Override to 1%
                "override_high": 1.0,  # Override to 100%
            }
        )
        
        # Per-rule rates should override global
        assert metrics._get_sample_rate("override_low") == 0.01
        assert metrics._get_sample_rate("override_high") == 1.0
        
        # Non-overridden rules should use global
        assert metrics._get_sample_rate("normal_rule") == 0.5

    def test_per_rule_sampling_uses_correct_rate(self):
        """Test that record_rule_hit uses the correct sampling rate per rule."""
        with patch('crashlens.observability.metrics.random.random') as mock_random:
            from crashlens.observability.metrics import CrashLensMetrics
            
            # Set up mock to return specific values
            mock_random.side_effect = [0.005, 0.5, 0.99]  # First passes 0.01, second fails 0.1, third fails 0.5
            
            metrics = CrashLensMetrics(
                max_rules=100,
                sample_rate=0.5,
                per_rule_rates={
                    "rare_rule": 0.01,
                    "normal_rule": 0.1,
                }
            )
            
            # Record hits
            metrics.record_rule_hit("rare_rule", "low", "scan")  # Should pass (0.005 < 0.01)
            metrics.record_rule_hit("normal_rule", "medium", "scan")  # Should fail (0.5 >= 0.1)
            metrics.record_rule_hit("unknown_rule", "high", "scan")  # Should fail (0.99 >= 0.5 global)
            
            # Verify random was called 3 times
            assert mock_random.call_count == 3


class TestPerRuleSamplingIntegration:
    """Integration tests with initialize_metrics() public API."""

    def test_initialize_metrics_with_per_rule_rates(self):
        """Test that initialize_metrics accepts and uses per_rule_rates."""
        mock_prom = MagicMock()
        mock_prom.Counter.return_value = MagicMock()
        mock_prom.Gauge.return_value = MagicMock()
        
        with patch.dict(sys.modules, {'prometheus_client': mock_prom}):
            from crashlens.observability import initialize_metrics, get_metrics
            
            # Initialize with per-rule rates
            per_rule_rates = {
                "expensive_rule": 0.05,
                "critical_rule": 1.0,
            }
            
            initialize_metrics(
                enabled=True,
                max_rules=100,
                sample_rate=0.2,
                per_rule_rates=per_rule_rates
            )
            
            # Get metrics instance
            metrics = get_metrics()
            assert metrics is not None
            
            # Check that per-rule rates are applied
            assert metrics._get_sample_rate("expensive_rule") == 0.05
            assert metrics._get_sample_rate("critical_rule") == 1.0
            assert metrics._get_sample_rate("unknown_rule") == 0.2  # Falls back to global

    def test_initialize_metrics_without_per_rule_rates(self):
        """Test that initialize_metrics works without per_rule_rates (backwards compatible)."""
        mock_prom = MagicMock()
        mock_prom.Counter.return_value = MagicMock()
        mock_prom.Gauge.return_value = MagicMock()
        
        with patch.dict(sys.modules, {'prometheus_client': mock_prom}):
            from crashlens.observability import initialize_metrics, get_metrics
            
            # Initialize without per_rule_rates
            initialize_metrics(
                enabled=True,
                max_rules=100,
                sample_rate=0.3
            )
            
            # Should work fine
            metrics = get_metrics()
            assert metrics is not None
            assert metrics._get_sample_rate("any_rule") == 0.3
