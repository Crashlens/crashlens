"""
Test: Lazy Import Verification
Purpose: Verify that importing CrashLens core modules does NOT import prometheus_client
         unless metrics are explicitly enabled via environment variable.
         
Acceptance Criteria:
- prometheus_client must NOT be in sys.modules after initial import
- prometheus_client MUST be in sys.modules when CRASHLENS_ENABLE_METRICS=1 is set

This ensures zero-dependency operation when metrics are disabled.
"""

import sys
import os
import importlib
import pytest


def test_lazy_import_prometheus_client_not_loaded_by_default():
    """
    ACCEPTANCE: prometheus_client is NOT in sys.modules after importing crashlens.
    
    This verifies the lazy loading requirement: users without prometheus_client
    installed can still use CrashLens CLI for all non-metrics features.
    """
    # Remove prometheus_client and crashlens modules if already loaded
    modules_to_remove = [
        mod for mod in sys.modules.keys() 
        if mod.startswith('prometheus_client') or mod.startswith('crashlens')
    ]
    for mod in modules_to_remove:
        del sys.modules[mod]
    
    # Ensure metrics are disabled
    env_backup = os.environ.get('CRASHLENS_ENABLE_METRICS')
    if 'CRASHLENS_ENABLE_METRICS' in os.environ:
        del os.environ['CRASHLENS_ENABLE_METRICS']
    
    try:
        # Import crashlens core modules
        import crashlens
        import crashlens.cli
        
        # CRITICAL ASSERTION: prometheus_client should NOT be loaded
        prometheus_modules = [
            mod for mod in sys.modules.keys() 
            if mod.startswith('prometheus_client')
        ]
        
        assert len(prometheus_modules) == 0, (
            f"FAIL: prometheus_client was imported during lazy load test. "
            f"Found modules: {prometheus_modules}. "
            f"This violates the zero-dependency requirement for metrics-disabled mode."
        )
        
        print("✓ PASS: prometheus_client not loaded when metrics disabled")
        
    finally:
        # Restore environment
        if env_backup is not None:
            os.environ['CRASHLENS_ENABLE_METRICS'] = env_backup


def test_lazy_import_prometheus_client_loaded_when_enabled():
    """
    ACCEPTANCE: prometheus_client IS in sys.modules when metrics are initialized.
    
    This verifies that metrics infrastructure loads correctly when requested.
    """
    # Clean slate
    modules_to_remove = [
        mod for mod in sys.modules.keys() 
        if mod.startswith('prometheus_client') or mod.startswith('crashlens.observability')
    ]
    for mod in modules_to_remove:
        del sys.modules[mod]
    
    # Enable metrics
    os.environ['CRASHLENS_ENABLE_METRICS'] = '1'
    
    try:
        # Import observability module and INITIALIZE metrics (this triggers prometheus import)
        try:
            from crashlens.observability import initialize_metrics
            
            # Actually initialize metrics - this is what triggers prometheus_client import
            metrics = initialize_metrics(enabled=True)
            
            # CRITICAL ASSERTION: prometheus_client SHOULD be loaded now
            prometheus_modules = [
                mod for mod in sys.modules.keys() 
                if mod.startswith('prometheus_client')
            ]
            
            assert len(prometheus_modules) > 0, (
                f"FAIL: prometheus_client was NOT imported when metrics enabled. "
                f"Expected prometheus_client.* modules in sys.modules. "
                f"This means lazy loading is broken or metrics are not working."
            )
            
            # Also verify metrics instance was created
            assert metrics is not None, (
                f"FAIL: initialize_metrics returned None when enabled=True"
            )
            
            print(f"✓ PASS: prometheus_client loaded when metrics enabled ({len(prometheus_modules)} modules)")
            
        except ImportError as e:
            # If prometheus_client is not installed, that's OK for this test
            # (we're testing lazy loading, not installation)
            if 'prometheus_client' in str(e):
                pytest.skip("prometheus_client not installed (expected in dev environment)")
            else:
                raise
    
    finally:
        # Cleanup
        if 'CRASHLENS_ENABLE_METRICS' in os.environ:
            del os.environ['CRASHLENS_ENABLE_METRICS']


def test_lazy_import_startup_time_overhead():
    """
    ACCEPTANCE: Import time for crashlens.cli must be <500ms even when
                prometheus_client is installed (but not enabled).
    
    This verifies the performance requirement from the reports.
    """
    import time
    
    # Remove modules
    modules_to_remove = [
        mod for mod in sys.modules.keys() 
        if mod.startswith('crashlens')
    ]
    for mod in modules_to_remove:
        del sys.modules[mod]
    
    # Disable metrics
    env_backup = os.environ.get('CRASHLENS_ENABLE_METRICS')
    if 'CRASHLENS_ENABLE_METRICS' in os.environ:
        del os.environ['CRASHLENS_ENABLE_METRICS']
    
    try:
        start = time.monotonic()
        import crashlens.cli
        elapsed = time.monotonic() - start
        
        # 500ms threshold from research reports
        MAX_IMPORT_TIME_S = 0.5
        
        assert elapsed < MAX_IMPORT_TIME_S, (
            f"FAIL: Import time {elapsed:.3f}s exceeds {MAX_IMPORT_TIME_S}s threshold. "
            f"This violates the <500ms startup requirement for CLI responsiveness."
        )
        
        print(f"✓ PASS: Import time {elapsed*1000:.1f}ms < {MAX_IMPORT_TIME_S*1000}ms")
        
    finally:
        if env_backup is not None:
            os.environ['CRASHLENS_ENABLE_METRICS'] = env_backup


if __name__ == '__main__':
    # Allow running directly for quick verification
    print("=" * 70)
    print("LAZY IMPORT VERIFICATION SUITE")
    print("=" * 70)
    
    try:
        test_lazy_import_prometheus_client_not_loaded_by_default()
        test_lazy_import_prometheus_client_loaded_when_enabled()
        test_lazy_import_startup_time_overhead()
        print("\n" + "=" * 70)
        print("ALL LAZY IMPORT TESTS PASSED ✓")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n{'=' * 70}")
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)
