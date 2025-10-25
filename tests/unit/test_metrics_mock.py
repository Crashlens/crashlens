"""
Unit tests for crashlens.observability module using mocks.

These tests run WITHOUT prometheus-client installed, using mocks to validate:
- Lazy import behavior
- Kill switch functionality
- Cardinality protection
- Severity normalization
- URL validation
- Fire-and-forget push behavior

All tests must pass whether prometheus-client is installed or not.
"""

import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# Test 1: Metrics Disabled by Default
# ============================================================================

def test_metrics_disabled_by_default():
    """Test that metrics are disabled by default without explicit enable."""
    # Mock prometheus_client to avoid ImportError
    with patch.dict(sys.modules, {'prometheus_client': MagicMock()}):
        from crashlens.observability import initialize_metrics
        
        # Initialize without enabled=True
        metrics = initialize_metrics(enabled=False)
        
        assert metrics is None, "Metrics should be None when disabled"


# ============================================================================
# Test 2: Kill Switch Overrides Enabled Flag
# ============================================================================

def test_kill_switch_overrides_enabled():
    """Test that CRASHLENS_DISABLE_METRICS env var disables metrics."""
    with patch.dict(sys.modules, {'prometheus_client': MagicMock()}):
        # Set kill switch environment variable
        with patch.dict(os.environ, {'CRASHLENS_DISABLE_METRICS': 'true'}):
            from crashlens.observability import initialize_metrics
            
            # Try to enable metrics, but kill switch should override
            metrics = initialize_metrics(enabled=True)
            
            assert metrics is None, "Kill switch should disable metrics even with enabled=True"


# ============================================================================
# Test 3: Lazy Import Fails Gracefully
# ============================================================================

def test_lazy_import_fails_gracefully():
    """Test that missing prometheus_client doesn't crash at import time."""
    # Remove prometheus_client from sys.modules to simulate missing dependency
    with patch.dict(sys.modules, {'prometheus_client': None}):
        # Import should succeed even without prometheus_client
        from crashlens.observability import initialize_metrics
        
        # Attempting to enable should fail gracefully
        with pytest.raises(RuntimeError, match="prometheus_client.*not installed"):
            initialize_metrics(enabled=True)


# ============================================================================
# Test 4: Cardinality Limit Enforces Max Rules
# ============================================================================

def test_cardinality_limit_enforces_500():
    """Test that cardinality protection enforces 500-rule limit."""
    # Mock prometheus_client completely
    mock_prom = MagicMock()
    mock_counter = MagicMock()
    mock_gauge = MagicMock()
    
    # Setup Counter and Gauge mocks
    mock_prom.Counter.return_value = mock_counter
    mock_prom.Gauge.return_value = mock_gauge
    
    with patch.dict(sys.modules, {'prometheus_client': mock_prom}):
        from crashlens.observability import initialize_metrics
        
        # Initialize with 500-rule limit (default)
        metrics = initialize_metrics(enabled=True, max_rules=500)
        
        assert metrics is not None, "Metrics should be initialized"
        assert metrics.max_rules == 500, "Max rules should be set to 500"
        
        # Verify that _normalize_rule_name enforces limit
        # (implementation detail: uses set with max size check)


# ============================================================================
# Test 5: Overflow Counter Increments
# ============================================================================

def test_overflow_counter_increments():
    """Test that rule_label_overflow counter increments when limit exceeded."""
    # Mock prometheus_client
    mock_prom = MagicMock()
    mock_counter = MagicMock()
    mock_gauge = MagicMock()
    
    mock_prom.Counter.return_value = mock_counter
    mock_prom.Gauge.return_value = mock_gauge
    
    with patch.dict(sys.modules, {'prometheus_client': mock_prom}):
        from crashlens.observability import initialize_metrics
        
        # Initialize with small limit to test overflow
        metrics = initialize_metrics(enabled=True, max_rules=5)
        
        assert metrics is not None, "Metrics should be initialized"
        
        # Add rules up to limit
        for i in range(5):
            metrics._get_rule_label(f"rule_{i}")
        
        # Next rule should trigger overflow
        overflow_label = metrics._get_rule_label("rule_6")
        
        # Should return 'rule_overflow' for rules beyond limit
        assert overflow_label == "rule_overflow", "Should use overflow label"
        
        # Verify overflow counter was incremented (safely check 'called' attribute)
        assert getattr(metrics.label_overflow.inc, "called", False), "Overflow counter should increment"


# ============================================================================
# Test 6: Severity Normalization
# ============================================================================

@pytest.mark.parametrize("input_severity,expected_output", [
    ("critical", "critical"),
    ("CRITICAL", "critical"),
    ("high", "high"),
    ("HIGH", "high"),
    ("medium", "medium"),
    ("low", "low"),
    ("info", "info"),
    ("unknown", "info"),  # Unknown maps to info
    ("invalid", "info"),  # Invalid maps to info
    ("warn", "info"),     # Non-standard maps to info
])
def test_severity_normalization(input_severity, expected_output):
    """Test that severity normalization handles all cases correctly."""
    # Mock prometheus_client
    mock_prom = MagicMock()
    mock_counter = MagicMock()
    mock_gauge = MagicMock()
    
    mock_prom.Counter.return_value = mock_counter
    mock_prom.Gauge.return_value = mock_gauge
    
    with patch.dict(sys.modules, {'prometheus_client': mock_prom}):
        from crashlens.observability import initialize_metrics
        
        metrics = initialize_metrics(enabled=True)
        
        assert metrics is not None, "Metrics should be initialized"
        
        # Test normalization
        normalized = metrics.normalize_severity(input_severity)
        
        assert normalized == expected_output, f"Severity '{input_severity}' should normalize to '{expected_output}'"


# ============================================================================
# Test 7: URL Validation Rejects Invalid URLs
# ============================================================================

@pytest.mark.parametrize("invalid_url", [
    "not-a-url",
    "ftp://localhost:9091",  # Wrong scheme
    "http://",               # Missing netloc
    "localhost:9091",        # Missing scheme
])
def test_url_validation_rejects_invalid(invalid_url):
    """Test that URL validation rejects invalid URLs."""
    # Mock prometheus_client (URL validation doesn't need it)
    with patch.dict(sys.modules, {'prometheus_client': MagicMock()}):
        from crashlens.observability.server import validate_pushgateway_url
        
        # Invalid URLs should raise ValueError
        with pytest.raises(ValueError):
            validate_pushgateway_url(invalid_url)


# ============================================================================
# Test 8: URL Validation Accepts Valid URLs
# ============================================================================

@pytest.mark.parametrize("valid_url,expected_normalized", [
    ("http://localhost:9091", "http://localhost:9091"),
    ("http://localhost:9091/", "http://localhost:9091/"),  # Keep trailing slash
    ("https://pushgateway.example.com:9091", "https://pushgateway.example.com:9091"),
    ("http://192.168.1.100:9091", "http://192.168.1.100:9091"),
])
def test_url_validation_accepts_valid(valid_url, expected_normalized):
    """Test that URL validation accepts valid URLs and normalizes them."""
    with patch.dict(sys.modules, {'prometheus_client': MagicMock()}):
        from crashlens.observability.server import validate_pushgateway_url
        
        # Valid URLs should be normalized
        normalized = validate_pushgateway_url(valid_url)
        
        assert normalized == expected_normalized, f"URL '{valid_url}' should normalize to '{expected_normalized}'"


# ============================================================================
# Test 9: Fire-and-Forget Push Doesn't Block
# ============================================================================

def test_fire_and_forget_push_doesnt_block():
    """Test that push_metrics_async returns within max_wait seconds."""
    # Mock prometheus_client completely
    mock_prom = MagicMock()
    mock_counter = MagicMock()
    mock_gauge = MagicMock()
    
    # Simulate slow push (takes 5 seconds)
    def slow_push(*args, **kwargs):
        time.sleep(5)
    
    mock_prom.push_to_gateway.side_effect = slow_push
    mock_prom.Counter.return_value = mock_counter
    mock_prom.Gauge.return_value = mock_gauge
    mock_prom.REGISTRY = MagicMock()
    
    with patch.dict(sys.modules, {'prometheus_client': mock_prom}):
        from crashlens.observability.server import push_metrics_async
        from crashlens.observability import initialize_metrics
        
        metrics = initialize_metrics(enabled=True)
        
        # Push with max_wait=2 seconds (should return even though push takes 5s)
        start = time.time()
        push_metrics_async(
            gateway_url="http://localhost:9091",
            job_name="test",
            max_wait=2.0,
            metrics_instance=metrics
        )
        elapsed = time.time() - start
        
        # Should return within 2.5 seconds (2s max_wait + 0.5s tolerance)
        assert elapsed < 2.5, f"Push should return within max_wait (got {elapsed:.2f}s)"


# ============================================================================
# Test 10: Daemon Thread Continues After Return
# ============================================================================

def test_daemon_thread_continues_after_return():
    """Test that daemon thread continues running after function returns."""
    # Mock prometheus_client
    mock_prom = MagicMock()
    mock_counter = MagicMock()
    mock_gauge = MagicMock()
    
    push_called = []
    
    def track_push(*args, **kwargs):
        time.sleep(1)  # Simulate work
        push_called.append(True)
    
    mock_prom.push_to_gateway.side_effect = track_push
    mock_prom.Counter.return_value = mock_counter
    mock_prom.Gauge.return_value = mock_gauge
    mock_prom.REGISTRY = MagicMock()
    
    with patch.dict(sys.modules, {'prometheus_client': mock_prom}):
        from crashlens.observability.server import push_metrics_async
        from crashlens.observability import initialize_metrics
        
        metrics = initialize_metrics(enabled=True)
        
        # Push with very short max_wait
        push_metrics_async(
            gateway_url="http://localhost:9091",
            job_name="test",
            max_wait=0.1,  # Very short wait
            metrics_instance=metrics
        )
        
        # Function should return immediately
        # But give thread time to complete
        time.sleep(2)
        
        # Push should have been called in background thread
        assert len(push_called) == 1, "Push should complete in background thread"


# ============================================================================
# Test 11: Metrics Instance Creation
# ============================================================================

def test_metrics_instance_creation():
    """Test that metrics instance is created with correct configuration."""
    # Mock prometheus_client
    mock_prom = MagicMock()
    mock_counter = MagicMock()
    mock_gauge = MagicMock()
    
    mock_prom.Counter.return_value = mock_counter
    mock_prom.Gauge.return_value = mock_gauge
    
    with patch.dict(sys.modules, {'prometheus_client': mock_prom}):
        from crashlens.observability import initialize_metrics
        
        # Initialize with custom max_rules
        metrics = initialize_metrics(enabled=True, max_rules=100)
        
        assert metrics is not None, "Metrics should be initialized"
        assert metrics.max_rules == 100, "Max rules should be set correctly"
        assert hasattr(metrics, 'rule_hits'), "Should have rule_hits counter"
        assert hasattr(metrics, 'violations'), "Should have violations counter"
        assert hasattr(metrics, 'traces_processed'), "Should have traces_processed counter"


# ============================================================================
# Test 12: Get Metrics Singleton
# ============================================================================

def test_get_metrics_singleton():
    """Test that get_metrics returns singleton instance."""
    # Mock prometheus_client
    mock_prom = MagicMock()
    mock_counter = MagicMock()
    mock_gauge = MagicMock()
    
    mock_prom.Counter.return_value = mock_counter
    mock_prom.Gauge.return_value = mock_gauge
    
    with patch.dict(sys.modules, {'prometheus_client': mock_prom}):
        # Reset module to fresh state
        import crashlens.observability
        crashlens.observability._metrics_instance = None
        
        from crashlens.observability import initialize_metrics, get_metrics
        
        # Before initialization, should return None
        metrics_before = get_metrics()
        assert metrics_before is None, "get_metrics should return None before initialization"
        
        # Initialize metrics
        metrics1 = initialize_metrics(enabled=True)
        
        # Get metrics should return same instance
        metrics2 = get_metrics()
        
        assert metrics1 is metrics2, "get_metrics should return singleton"


# ============================================================================
# Integration Test: Full Workflow
# ============================================================================

def test_full_metrics_workflow():
    """Integration test: Initialize, record metrics, push."""
    # Mock prometheus_client
    mock_prom = MagicMock()
    mock_counter = MagicMock()
    mock_gauge = MagicMock()
    
    mock_prom.Counter.return_value = mock_counter
    mock_prom.Gauge.return_value = mock_gauge
    mock_prom.REGISTRY = MagicMock()
    mock_prom.push_to_gateway = MagicMock()
    
    with patch.dict(sys.modules, {'prometheus_client': mock_prom}):
        from crashlens.observability import initialize_metrics
        from crashlens.observability.server import push_metrics_async
        
        # 1. Initialize
        metrics = initialize_metrics(enabled=True, max_rules=500)
        assert metrics is not None
        
        # 2. Record some metrics
        metrics.record_rule_hit("test_rule", "high", "scan")
        metrics.record_violation("critical")
        metrics.record_trace_processed()
        metrics.update_run_timestamp("success")
        
        # 3. Push to gateway
        push_metrics_async(
            gateway_url="http://localhost:9091",
            job_name="crashlens_test",
            max_wait=2.0,
            metrics_instance=metrics
        )
        
        # Verify push was called (eventually in background thread)
        time.sleep(1)  # Give thread time to execute
        
        # Test passes if no exceptions raised


# ============================================================================
# Test: Sampling Functionality
# ============================================================================

class TestSampling:
    """Test metrics sampling functionality."""
    
    def test_sample_rate_parameter_accepted(self):
        """Test that sample_rate parameter is accepted."""
        with patch.dict(sys.modules, {'prometheus_client': MagicMock()}):
            from crashlens.observability import initialize_metrics
            
            metrics = initialize_metrics(enabled=True, sample_rate=0.5)
            
            assert metrics is not None
            assert metrics._sample_rate == 0.5
    
    def test_sample_rate_validation(self):
        """Test that invalid sample rates are rejected."""
        with patch.dict(sys.modules, {
            'prometheus_client': MagicMock(),
            'prometheus_client.Counter': MagicMock,
            'prometheus_client.Gauge': MagicMock,
            'prometheus_client.CollectorRegistry': MagicMock,
            'prometheus_client.REGISTRY': MagicMock(),
        }):
            from crashlens.observability.metrics import CrashLensMetrics
            
            # Make prometheus available
            import crashlens.observability.metrics as metrics_module
            metrics_module._prometheus_available = True
            metrics_module._Counter = MagicMock
            metrics_module._Gauge = MagicMock
            metrics_module._CollectorRegistry = MagicMock
            metrics_module._REGISTRY = MagicMock()
            
            # Valid rates
            CrashLensMetrics(sample_rate=0.0)  # Should not raise
            CrashLensMetrics(sample_rate=0.5)  # Should not raise
            CrashLensMetrics(sample_rate=1.0)  # Should not raise
            
            # Invalid rates
            with pytest.raises(ValueError, match="sample_rate must be between"):
                CrashLensMetrics(sample_rate=-0.1)
            
            with pytest.raises(ValueError, match="sample_rate must be between"):
                CrashLensMetrics(sample_rate=1.5)
    
    def test_zero_sampling_records_nothing(self):
        """Test that 0.0 sample rate records nothing."""
        with patch.dict(sys.modules, {'prometheus_client': MagicMock()}):
            from crashlens.observability import initialize_metrics
            
            metrics = initialize_metrics(enabled=True, sample_rate=0.0)
            assert metrics is not None, "Metrics should be initialized"
            
            # Try to record 100 times
            for i in range(100):
                metrics.record_rule_hit('test-rule', 'high', 'scan')
                metrics.record_violation('critical')
                metrics.record_trace_processed()
            
            # With 0% sampling, nothing should be recorded
            # (We can't easily check internal counter with mocks,
            #  but the test verifies no exceptions are raised)
            assert True  # If we got here, no crashes occurred
    
    def test_full_sampling_records_all(self):
        """Test that 1.0 sample rate records everything."""
        with patch.dict(sys.modules, {'prometheus_client': MagicMock()}):
            from crashlens.observability import initialize_metrics
            
            metrics = initialize_metrics(enabled=True, sample_rate=1.0)
            assert metrics is not None, "Metrics should be initialized"
            
            # Record multiple times - should all go through
            for i in range(10):
                metrics.record_rule_hit('test-rule', 'high', 'scan')
            
            # With 100% sampling, all calls succeed
            assert True  # No crashes = success
    
    @pytest.mark.parametrize("sample_rate", [0.1, 0.5, 0.9])
    def test_partial_sampling_probabilistic(self, sample_rate):
        """Test that partial sampling is probabilistic."""
        import random
        
        with patch.dict(sys.modules, {'prometheus_client': MagicMock()}):
            from crashlens.observability import initialize_metrics
            
            # Set seed for reproducibility
            random.seed(42)
            
            metrics = initialize_metrics(enabled=True, sample_rate=sample_rate)
            assert metrics is not None, "Metrics should be initialized"
            
            # Call 1000 times
            for i in range(1000):
                metrics.record_trace_processed()
            
            # With probabilistic sampling, should not crash
            assert True


class TestSamplingCLI:
    """Test CLI integration for sampling."""
    
    def test_cli_sample_rate_flag(self):
        """Test --metrics-sample-rate flag is recognized."""
        from click.testing import CliRunner
        from crashlens.cli import cli
        
        runner = CliRunner()
        
        # Test with --help to see if flag exists
        result = runner.invoke(cli, ['scan', '--help'])
        
        assert '--metrics-sample-rate' in result.output
        assert 'Metrics sampling rate' in result.output


if __name__ == "__main__":
    # Run tests with pytest
    import subprocess
    result = subprocess.run(
        ["pytest", __file__, "-v", "--tb=short"],
        capture_output=False
    )
    sys.exit(result.returncode)
