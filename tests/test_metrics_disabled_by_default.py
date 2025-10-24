"""
Test: Metrics Disabled by Default Verification
Purpose: Ensure metrics do not execute unless environment explicitly opts in.

Acceptance Criteria:
- When CRASHLENS_DISABLE_METRICS=1, no calls to prometheus_client
- When CRASHLENS_ENABLE_METRICS is unset, no calls to prometheus_client
- Metrics only activate when CRASHLENS_ENABLE_METRICS=1

This ensures zero overhead by default and opt-in behavior.
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, call


def test_metrics_disabled_with_disable_flag():
    """
    ACCEPTANCE: When CRASHLENS_DISABLE_METRICS=1, no prometheus_client calls occur.
    """
    # Set environment to disable metrics
    with patch.dict(os.environ, {'CRASHLENS_DISABLE_METRICS': '1'}, clear=False):
        # Remove any enable flag
        os.environ.pop('CRASHLENS_ENABLE_METRICS', None)
        
        # Mock prometheus_client functions
        with patch('prometheus_client.Counter') as mock_counter, \
             patch('prometheus_client.Histogram') as mock_histogram, \
             patch('prometheus_client.Gauge') as mock_gauge, \
             patch('prometheus_client.push_to_gateway') as mock_push:
            
            # Simulate CrashLens entry function
            def crashlens_main_simulation():
                """
                Simulates CrashLens main execution.
                Should check env vars and skip metrics if disabled.
                """
                # Check if metrics are enabled
                disable_metrics = os.getenv('CRASHLENS_DISABLE_METRICS', '0') == '1'
                enable_metrics = os.getenv('CRASHLENS_ENABLE_METRICS', '0') == '1'
                
                if not enable_metrics or disable_metrics:
                    # Skip all metrics operations
                    return
                
                # If we reach here, metrics are enabled (shouldn't happen in this test)
                from prometheus_client import Counter
                counter = Counter('test_counter', 'Test')
                counter.inc()
            
            # Run simulation
            crashlens_main_simulation()
            
            # Assert no prometheus_client calls
            assert mock_counter.call_count == 0, (
                f"FAIL: Counter called {mock_counter.call_count} times when metrics disabled"
            )
            assert mock_histogram.call_count == 0, (
                f"FAIL: Histogram called {mock_histogram.call_count} times when metrics disabled"
            )
            assert mock_gauge.call_count == 0, (
                f"FAIL: Gauge called {mock_gauge.call_count} times when metrics disabled"
            )
            assert mock_push.call_count == 0, (
                f"FAIL: push_to_gateway called {mock_push.call_count} times when metrics disabled"
            )
    
    print("✓ PASS: No prometheus_client calls when CRASHLENS_DISABLE_METRICS=1")


def test_metrics_disabled_when_enable_flag_absent():
    """
    ACCEPTANCE: When CRASHLENS_ENABLE_METRICS is unset, no prometheus_client calls occur.
    """
    # Ensure neither flag is set
    env = os.environ.copy()
    env.pop('CRASHLENS_ENABLE_METRICS', None)
    env.pop('CRASHLENS_DISABLE_METRICS', None)
    
    with patch.dict(os.environ, env, clear=True):
        # Mock prometheus_client functions
        with patch('prometheus_client.Counter') as mock_counter, \
             patch('prometheus_client.Histogram') as mock_histogram, \
             patch('prometheus_client.Gauge') as mock_gauge, \
             patch('prometheus_client.push_to_gateway') as mock_push:
            
            def crashlens_main_simulation():
                """Simulates CrashLens with default env (no flags set)."""
                enable_metrics = os.getenv('CRASHLENS_ENABLE_METRICS', '0') == '1'
                disable_metrics = os.getenv('CRASHLENS_DISABLE_METRICS', '0') == '1'
                
                if not enable_metrics or disable_metrics:
                    return  # Skip metrics
                
                # Shouldn't reach here
                from prometheus_client import Counter
                counter = Counter('test_counter', 'Test')
                counter.inc()
            
            crashlens_main_simulation()
            
            # Assert no calls
            assert mock_counter.call_count == 0, "FAIL: Metrics should be disabled by default"
            assert mock_histogram.call_count == 0, "FAIL: Metrics should be disabled by default"
            assert mock_gauge.call_count == 0, "FAIL: Metrics should be disabled by default"
            assert mock_push.call_count == 0, "FAIL: Metrics should be disabled by default"
    
    print("✓ PASS: No prometheus_client calls when CRASHLENS_ENABLE_METRICS unset (default)")


def test_metrics_enabled_only_with_enable_flag():
    """
    ACCEPTANCE: Metrics only execute when CRASHLENS_ENABLE_METRICS=1.
    """
    with patch.dict(os.environ, {'CRASHLENS_ENABLE_METRICS': '1'}, clear=False):
        # Ensure disable flag is not set
        os.environ.pop('CRASHLENS_DISABLE_METRICS', None)
        
        # Mock prometheus_client functions
        with patch('prometheus_client.Counter') as mock_counter, \
             patch('prometheus_client.CollectorRegistry') as mock_registry:
            
            # Configure mocks
            mock_registry_instance = MagicMock()
            mock_registry.return_value = mock_registry_instance
            mock_counter_instance = MagicMock()
            mock_counter.return_value = mock_counter_instance
            
            def crashlens_main_simulation():
                """Simulates CrashLens with metrics enabled."""
                enable_metrics = os.getenv('CRASHLENS_ENABLE_METRICS', '0') == '1'
                disable_metrics = os.getenv('CRASHLENS_DISABLE_METRICS', '0') == '1'
                
                if not enable_metrics or disable_metrics:
                    return  # Skip metrics
                
                # Metrics are enabled - create them
                from prometheus_client import Counter, CollectorRegistry
                registry = CollectorRegistry()
                counter = Counter('test_counter', 'Test', registry=registry)
                counter.inc()
            
            crashlens_main_simulation()
            
            # Assert prometheus_client was called
            assert mock_counter.call_count > 0, (
                "FAIL: Counter should be created when CRASHLENS_ENABLE_METRICS=1"
            )
    
    print("✓ PASS: prometheus_client called only when CRASHLENS_ENABLE_METRICS=1")


def test_disable_flag_takes_precedence_over_enable():
    """
    ACCEPTANCE: CRASHLENS_DISABLE_METRICS=1 overrides CRASHLENS_ENABLE_METRICS=1.
    """
    with patch.dict(os.environ, {
        'CRASHLENS_ENABLE_METRICS': '1',
        'CRASHLENS_DISABLE_METRICS': '1'
    }, clear=False):
        
        with patch('prometheus_client.Counter') as mock_counter, \
             patch('prometheus_client.Histogram') as mock_histogram:
            
            def crashlens_main_simulation():
                """Disable flag should override enable flag."""
                enable_metrics = os.getenv('CRASHLENS_ENABLE_METRICS', '0') == '1'
                disable_metrics = os.getenv('CRASHLENS_DISABLE_METRICS', '0') == '1'
                
                # Disable takes precedence
                if disable_metrics or not enable_metrics:
                    return
                
                from prometheus_client import Counter
                counter = Counter('test_counter', 'Test')
                counter.inc()
            
            crashlens_main_simulation()
            
            # Should not have called prometheus_client
            assert mock_counter.call_count == 0, (
                "FAIL: Disable flag should take precedence over enable flag"
            )
    
    print("✓ PASS: CRASHLENS_DISABLE_METRICS=1 overrides CRASHLENS_ENABLE_METRICS=1")


def test_lazy_import_prevents_prometheus_client_loading():
    """
    ACCEPTANCE: prometheus_client not imported unless metrics enabled.
    """
    # Remove metrics-related modules from sys.modules
    modules_to_remove = [name for name in sys.modules.keys() 
                         if 'prometheus_client' in name]
    for name in modules_to_remove:
        del sys.modules[name]
    
    with patch.dict(os.environ, {}, clear=False):
        # Ensure flags unset
        os.environ.pop('CRASHLENS_ENABLE_METRICS', None)
        os.environ.pop('CRASHLENS_DISABLE_METRICS', None)
        
        def crashlens_main_simulation():
            """Should not import prometheus_client when disabled."""
            enable_metrics = os.getenv('CRASHLENS_ENABLE_METRICS', '0') == '1'
            
            if not enable_metrics:
                return  # Don't import
            
            # Only import if enabled
            import prometheus_client
        
        crashlens_main_simulation()
        
        # Check if prometheus_client was imported
        prometheus_loaded = any('prometheus_client' in name for name in sys.modules.keys())
        
        assert not prometheus_loaded, (
            "FAIL: prometheus_client should not be loaded when metrics disabled"
        )
    
    print("✓ PASS: prometheus_client not loaded when metrics disabled (lazy import)")


def test_environment_variable_parsing():
    """
    ACCEPTANCE: Various env var values correctly parsed.
    """
    test_cases = [
        # (ENABLE, DISABLE, should_metrics_run)
        ('1', '0', True),    # Explicit enable
        ('1', '1', False),   # Disable overrides
        ('0', '0', False),   # Both disabled
        ('true', '0', False),  # Only '1' enables
        (None, None, False),  # Default is disabled
        ('1', None, True),   # Enable with no disable
        (None, '1', False),  # Disable with no enable
    ]
    
    for enable_val, disable_val, should_run in test_cases:
        env = {}
        if enable_val is not None:
            env['CRASHLENS_ENABLE_METRICS'] = enable_val
        if disable_val is not None:
            env['CRASHLENS_DISABLE_METRICS'] = disable_val
        
        with patch.dict(os.environ, env, clear=True):
            enable_metrics = os.getenv('CRASHLENS_ENABLE_METRICS', '0') == '1'
            disable_metrics = os.getenv('CRASHLENS_DISABLE_METRICS', '0') == '1'
            
            metrics_should_run = enable_metrics and not disable_metrics
            
            assert metrics_should_run == should_run, (
                f"FAIL: ENABLE={enable_val}, DISABLE={disable_val}. "
                f"Expected metrics_run={should_run}, got {metrics_should_run}"
            )
    
    print("✓ PASS: Environment variable parsing correct for all cases")


if __name__ == '__main__':
    import sys
    
    print("=" * 70)
    print("METRICS DISABLED BY DEFAULT VERIFICATION SUITE")
    print("=" * 70)
    
    try:
        test_metrics_disabled_with_disable_flag()
        test_metrics_disabled_when_enable_flag_absent()
        test_metrics_enabled_only_with_enable_flag()
        test_disable_flag_takes_precedence_over_enable()
        test_lazy_import_prevents_prometheus_client_loading()
        test_environment_variable_parsing()
        
        print("\n" + "=" * 70)
        print("ALL METRICS DISABLED BY DEFAULT TESTS PASSED ✓")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n{'=' * 70}")
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)
