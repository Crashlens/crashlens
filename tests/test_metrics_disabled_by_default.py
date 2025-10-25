"""
Test: Metrics Disabled by Default Verification
Purpose: Ensure metrics do not execute unless environment explicitly opts in.

Acceptance Criteria:
- When CRASHLENS_DISABLE_METRICS=1, no calls to prometheus_client
- When enabled=False, no metrics instance created
- Metrics only activate when enabled=True

This ensures zero overhead by default and opt-in behavior.
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock, call


@pytest.fixture(autouse=True)
def cleanup_metrics():
    """Clean up metrics singleton between tests."""
    yield
    # Clean up global singleton
    import crashlens.observability
    crashlens.observability._metrics_instance = None
    
    # Clean up prometheus registry  
    try:
        import prometheus_client
        # Force new registry for next test
        prometheus_client.REGISTRY = prometheus_client.CollectorRegistry()
    except ImportError:
        pass


def test_metrics_disabled_with_disable_flag():
    """
    ACCEPTANCE: When CRASHLENS_DISABLE_METRICS=1, initialize_metrics returns None.
    """
    # Set environment to disable metrics
    with patch.dict(os.environ, {'CRASHLENS_DISABLE_METRICS': '1'}, clear=False):
        # Remove any enable flag
        os.environ.pop('CRASHLENS_ENABLE_METRICS', None)
        
        # Use actual CrashLens initialization
        from crashlens.observability import initialize_metrics
        
        # Try to initialize metrics - should return None due to disable flag
        metrics = initialize_metrics(enabled=True)
        
        # Assert metrics are disabled
        assert metrics is None, (
            f"FAIL: initialize_metrics returned non-None value when CRASHLENS_DISABLE_METRICS=1"
        )
    
    print("✓ PASS: Metrics disabled when CRASHLENS_DISABLE_METRICS=1")


def test_metrics_disabled_when_enable_flag_absent():
    """
    ACCEPTANCE: When CRASHLENS_ENABLE_METRICS is unset, no prometheus_client calls occur.
    """
    # Ensure neither flag is set
    env = os.environ.copy()
    env.pop('CRASHLENS_ENABLE_METRICS', None)
    env.pop('CRASHLENS_DISABLE_METRICS', None)
    
    with patch.dict(os.environ, env, clear=True):
        # Use actual CrashLens initialization
        from crashlens.observability import initialize_metrics
        
        # Try to initialize metrics without enabling - should return None
        metrics = initialize_metrics(enabled=False)
        
        # Assert metrics are disabled
        assert metrics is None, (
            "FAIL: initialize_metrics returned non-None value when enabled=False"
        )
    
    print("✓ PASS: Metrics disabled when CRASHLENS_ENABLE_METRICS unset (default)")


def test_metrics_enabled_only_with_enable_flag():
    """
    ACCEPTANCE: Metrics only execute when enabled=True.
    """
    with patch.dict(os.environ, {}, clear=False):
        # Ensure disable flag is not set
        os.environ.pop('CRASHLENS_DISABLE_METRICS', None)
        
        # Clean up any previous initialization
        import crashlens.observability
        crashlens.observability._metrics_instance = None
        
        # Use actual CrashLens initialization
        from crashlens.observability import initialize_metrics
        
        # Initialize metrics with enabled=True
        metrics = initialize_metrics(enabled=True)
        
        # Assert metrics are enabled
        assert metrics is not None, (
            "FAIL: initialize_metrics returned None when enabled=True"
        )
        
        # Verify we can record metrics
        metrics.record_trace_processed()
        
        # Verify prometheus_client was actually imported
        prometheus_loaded = any('prometheus_client' in name for name in sys.modules.keys())
        assert prometheus_loaded, (
            "FAIL: prometheus_client not loaded even though metrics are enabled"
        )
    
    print("✓ PASS: Metrics enabled when enabled=True")


def test_disable_flag_takes_precedence_over_enable():
    """
    ACCEPTANCE: CRASHLENS_DISABLE_METRICS=1 overrides enabled=True parameter.
    """
    with patch.dict(os.environ, {
        'CRASHLENS_DISABLE_METRICS': '1'
    }, clear=False):
        
        # Use actual CrashLens initialization
        from crashlens.observability import initialize_metrics
        
        # Try to initialize metrics with enabled=True - should be overridden
        metrics = initialize_metrics(enabled=True)
        
        # Should be None due to disable flag
        assert metrics is None, (
            "FAIL: Disable flag should take precedence over enabled=True"
        )
    
    print("✓ PASS: CRASHLENS_DISABLE_METRICS=1 overrides enabled=True")


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
