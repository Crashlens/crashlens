"""
Test: Fire-and-Forget Push (Strict Mode - Blocking Failures)
Purpose: Verify that strict mode causes push failures to raise exceptions.
         When CRASHLENS_METRICS_STRICT=1, push errors should propagate.
         
Acceptance Criteria:
- TimeoutError raised when push times out in strict mode
- ConnectionError raised when push fails in strict mode
- Main thread blocked until push completes or fails
- Non-strict mode (default) doesn't raise exceptions

This ensures strict mode is available for CI/testing environments that require
hard failures on metrics push errors.
"""

import pytest
import time
import os
from unittest.mock import patch, MagicMock

try:
    from prometheus_client import CollectorRegistry, Counter
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


def strict_push(registry, push_url: str, job_name: str, timeout: float = 2.0, strict: bool = False):
    """
    Push implementation with strict mode option.
    
    - strict=False (default): Fire-and-forget, errors silenced
    - strict=True: Blocking call, errors raised
    """
    from prometheus_client import push_to_gateway
    
    if strict:
        # STRICT MODE: Blocking call, raise on errors
        push_to_gateway(push_url, job=job_name, registry=registry, timeout=timeout)
    else:
        # FIRE-AND-FORGET: Background thread, ignore errors
        from threading import Thread
        
        def _do_push():
            try:
                push_to_gateway(push_url, job=job_name, registry=registry, timeout=timeout)
            except Exception:
                pass  # Silently ignore
        
        thread = Thread(target=_do_push, daemon=True)
        thread.start()
        # Don't wait for completion


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_strict_mode_raises_on_timeout():
    """
    ACCEPTANCE: Strict mode raises TimeoutError when push times out.
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    counter.inc()
    
    # Mock push_to_gateway to raise timeout
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.side_effect = TimeoutError("Connection timed out after 2 seconds")
        
        # STRICT MODE: Should raise
        with pytest.raises(TimeoutError, match="timed out"):
            strict_push(
                registry=registry,
                push_url='http://localhost:9091',
                job_name='crashlens_test',
                timeout=2.0,
                strict=True
            )
        
        print("✓ PASS: Strict mode raised TimeoutError")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_strict_mode_raises_on_connection_error():
    """
    ACCEPTANCE: Strict mode raises ConnectionError when push fails.
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    counter.inc()
    
    # Mock push_to_gateway to raise connection error
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.side_effect = ConnectionError("Connection refused")
        
        # STRICT MODE: Should raise
        with pytest.raises(ConnectionError, match="refused"):
            strict_push(
                registry=registry,
                push_url='http://localhost:9091',
                job_name='crashlens_test',
                timeout=2.0,
                strict=True
            )
        
        print("✓ PASS: Strict mode raised ConnectionError")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_strict_mode_raises_on_http_error():
    """
    ACCEPTANCE: Strict mode raises on HTTP errors (4xx, 5xx).
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    counter.inc()
    
    # Mock push_to_gateway to raise HTTP 500
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.side_effect = Exception("HTTP 500 Internal Server Error")
        
        # STRICT MODE: Should raise
        with pytest.raises(Exception, match="500"):
            strict_push(
                registry=registry,
                push_url='http://localhost:9091',
                job_name='crashlens_test',
                timeout=2.0,
                strict=True
            )
        
        print("✓ PASS: Strict mode raised HTTP error")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_strict_mode_blocks_until_completion():
    """
    ACCEPTANCE: Strict mode blocks main thread until push completes.
    
    Verifies synchronous behavior vs fire-and-forget.
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    counter.inc()
    
    # Mock push to take 1 second
    def slow_push(*args, **kwargs):
        time.sleep(1.0)
    
    with patch('prometheus_client.push_to_gateway', side_effect=slow_push):
        # STRICT MODE: Should block for full 1 second
        start = time.monotonic()
        strict_push(
            registry=registry,
            push_url='http://localhost:9091',
            job_name='crashlens_test',
            timeout=5.0,
            strict=True
        )
        elapsed = time.monotonic() - start
        
        # Should take at least 1 second (blocking)
        assert elapsed >= 0.9, (  # Allow 100ms tolerance
            f"FAIL: Strict mode returned in {elapsed:.3f}s, expected >=1.0s. "
            f"Strict mode is not blocking!"
        )
        
        print(f"✓ PASS: Strict mode blocked for {elapsed:.3f}s (synchronous)")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_non_strict_mode_doesnt_raise():
    """
    ACCEPTANCE: Non-strict mode (default) silently ignores errors.
    
    Contrast with strict mode behavior.
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    counter.inc()
    
    # Mock push to raise timeout
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.side_effect = TimeoutError("Connection timed out")
        
        # NON-STRICT MODE: Should NOT raise
        try:
            strict_push(
                registry=registry,
                push_url='http://localhost:9091',
                job_name='crashlens_test',
                timeout=2.0,
                strict=False  # Fire-and-forget
            )
            # Wait a bit for background thread
            time.sleep(0.2)
            print("✓ PASS: Non-strict mode didn't raise on timeout")
        except Exception as e:
            pytest.fail(f"FAIL: Non-strict mode raised exception: {e}")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_non_strict_mode_returns_immediately():
    """
    ACCEPTANCE: Non-strict mode returns immediately (doesn't block).
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    counter.inc()
    
    # Mock push to take 3 seconds
    def slow_push(*args, **kwargs):
        time.sleep(3.0)
    
    with patch('prometheus_client.push_to_gateway', side_effect=slow_push):
        # NON-STRICT MODE: Should return in <500ms
        start = time.monotonic()
        strict_push(
            registry=registry,
            push_url='http://localhost:9091',
            job_name='crashlens_test',
            timeout=2.0,
            strict=False
        )
        elapsed = time.monotonic() - start
        
        MAX_ALLOWED = 0.5  # Should return almost instantly
        assert elapsed < MAX_ALLOWED, (
            f"FAIL: Non-strict mode took {elapsed:.3f}s, expected <{MAX_ALLOWED}s. "
            f"Fire-and-forget is blocking!"
        )
        
        print(f"✓ PASS: Non-strict mode returned in {elapsed * 1000:.1f}ms")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_strict_mode_env_var_detection():
    """
    ACCEPTANCE: CRASHLENS_METRICS_STRICT=1 enables strict mode.
    
    Simulates environment variable-based configuration.
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    counter.inc()
    
    # Read strict mode from env var
    strict_mode = os.getenv('CRASHLENS_METRICS_STRICT', '0') == '1'
    
    # Mock push to raise
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.side_effect = TimeoutError("Timeout")
        
        if strict_mode:
            # If env var set, should raise
            with pytest.raises(TimeoutError):
                strict_push(registry, 'http://localhost:9091', 'test', strict=True)
            print("✓ PASS: CRASHLENS_METRICS_STRICT=1 detected, strict mode active")
        else:
            # If env var not set, should not raise
            try:
                strict_push(registry, 'http://localhost:9091', 'test', strict=False)
                time.sleep(0.1)
                print("✓ PASS: CRASHLENS_METRICS_STRICT not set, fire-and-forget active")
            except TimeoutError:
                pytest.fail("FAIL: Fire-and-forget mode raised when env var not set")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_strict_mode_success_doesnt_raise():
    """
    ACCEPTANCE: Strict mode doesn't raise on successful push.
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    counter.inc()
    
    # Mock successful push
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.return_value = None  # Success
        
        # Should not raise
        try:
            strict_push(
                registry=registry,
                push_url='http://localhost:9091',
                job_name='crashlens_test',
                timeout=2.0,
                strict=True
            )
            print("✓ PASS: Strict mode successful push didn't raise")
        except Exception as e:
            pytest.fail(f"FAIL: Strict mode raised on success: {e}")


if __name__ == '__main__':
    import sys
    
    print("=" * 70)
    print("FIRE-AND-FORGET PUSH (STRICT MODE) VERIFICATION SUITE")
    print("=" * 70)
    
    if not PROMETHEUS_AVAILABLE:
        print("⚠ SKIP: prometheus_client not installed")
        sys.exit(0)
    
    try:
        test_strict_mode_raises_on_timeout()
        test_strict_mode_raises_on_connection_error()
        test_strict_mode_raises_on_http_error()
        test_strict_mode_blocks_until_completion()
        test_non_strict_mode_doesnt_raise()
        test_non_strict_mode_returns_immediately()
        test_strict_mode_env_var_detection()
        test_strict_mode_success_doesnt_raise()
        print("\n" + "=" * 70)
        print("ALL STRICT MODE TESTS PASSED ✓")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n{'=' * 70}")
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)
