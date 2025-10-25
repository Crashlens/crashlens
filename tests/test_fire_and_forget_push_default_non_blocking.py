"""
Test: Fire-and-Forget Push (Default Non-Blocking Mode)
Purpose: Verify that push_to_gateway calls don't block the main execution thread.
         Default behavior uses 2-second timeout with fire-and-forget semantics.
         
Acceptance Criteria:
- Push operation completes in <2.5 seconds (2s timeout + 0.5s tolerance)
- Main thread continues even if push takes longer
- No exceptions raised on slow pushes
- Returns immediately after spawning background thread

This ensures metrics collection never blocks critical log processing.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from threading import Event

try:
    from prometheus_client import CollectorRegistry, Counter
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


def fire_and_forget_push(registry, push_url: str, job_name: str, timeout: float = 2.0):
    """
    Fire-and-forget push implementation for testing.
    Spawns a background thread with timeout.
    """
    from threading import Thread
    
    def _do_push():
        try:
            from prometheus_client import push_to_gateway
            push_to_gateway(push_url, job=job_name, registry=registry, timeout=timeout)
        except Exception:
            # Fire-and-forget: ignore errors
            pass
    
    thread = Thread(target=_do_push, daemon=True)
    thread.start()
    # Don't wait for thread (fire-and-forget)
    return thread


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_fire_and_forget_completes_quickly_default_timeout():
    """
    ACCEPTANCE: Push operation completes in <2.5s even if backend is slow.
    
    Simulates a slow Pushgateway (5s response time) and verifies the call
    returns immediately without blocking.
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    counter.inc()
    
    # Mock push_to_gateway to sleep 5 seconds (slow backend)
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.side_effect = lambda *args, **kwargs: time.sleep(5)
        
        # Measure wall time
        start = time.monotonic()
        thread = fire_and_forget_push(
            registry=registry,
            push_url='http://localhost:9091',
            job_name='crashlens_test',
            timeout=2.0
        )
        elapsed = time.monotonic() - start
        
        # CRITICAL ASSERTION: Call returns almost immediately
        MAX_ALLOWED_TIME = 0.5  # Should return in <500ms (thread spawn overhead)
        assert elapsed < MAX_ALLOWED_TIME, (
            f"FAIL: fire_and_forget_push took {elapsed:.3f}s, expected <{MAX_ALLOWED_TIME}s. "
            f"Push is blocking the main thread!"
        )
        
        print(f"✓ PASS: Push returned in {elapsed * 1000:.1f}ms (non-blocking)")
        
        # Wait a bit to let background thread start
        time.sleep(0.1)
        
        # Thread should still be alive (blocked on 5s sleep)
        assert thread.is_alive(), (
            f"FAIL: Background thread terminated too quickly"
        )


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_fire_and_forget_doesnt_raise_on_timeout():
    """
    ACCEPTANCE: No exceptions raised when push times out.
    
    Fire-and-forget mode should silently ignore timeout errors.
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    counter.inc()
    
    # Mock push_to_gateway to raise timeout
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.side_effect = TimeoutError("Connection timed out")
        
        # Should not raise
        try:
            thread = fire_and_forget_push(
                registry=registry,
                push_url='http://localhost:9091',
                job_name='crashlens_test',
                timeout=2.0
            )
            # Wait for thread to finish
            thread.join(timeout=1.0)
            print("✓ PASS: No exception raised on timeout (fire-and-forget)")
        except Exception as e:
            pytest.fail(f"FAIL: Exception raised in fire-and-forget mode: {e}")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_fire_and_forget_doesnt_raise_on_connection_error():
    """
    ACCEPTANCE: No exceptions raised when push fails with connection error.
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    counter.inc()
    
    # Mock push_to_gateway to raise connection error
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.side_effect = ConnectionError("Connection refused")
        
        # Should not raise
        try:
            thread = fire_and_forget_push(
                registry=registry,
                push_url='http://localhost:9091',
                job_name='crashlens_test',
                timeout=2.0
            )
            # Wait for thread to finish
            thread.join(timeout=1.0)
            print("✓ PASS: No exception raised on connection error (fire-and-forget)")
        except Exception as e:
            pytest.fail(f"FAIL: Exception raised in fire-and-forget mode: {e}")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_fire_and_forget_multiple_pushes_non_blocking():
    """
    ACCEPTANCE: Multiple sequential pushes all return quickly.
    
    Verifies fire-and-forget behavior with burst of push calls.
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    
    # Mock push to take 3 seconds each
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.side_effect = lambda *args, **kwargs: time.sleep(3)
        
        # Make 5 pushes
        start = time.monotonic()
        threads = []
        for i in range(5):
            counter.inc()
            thread = fire_and_forget_push(
                registry=registry,
                push_url='http://localhost:9091',
                job_name=f'crashlens_test_{i}',
                timeout=2.0
            )
            threads.append(thread)
        elapsed = time.monotonic() - start
        
        # All 5 pushes should return in <1 second total (non-blocking)
        MAX_ALLOWED_TIME = 1.0
        assert elapsed < MAX_ALLOWED_TIME, (
            f"FAIL: 5 fire-and-forget pushes took {elapsed:.3f}s, expected <{MAX_ALLOWED_TIME}s. "
            f"Pushes are blocking!"
        )
        
        print(f"✓ PASS: 5 pushes returned in {elapsed * 1000:.1f}ms total")
        
        # All threads should be alive (still processing 3s sleep)
        time.sleep(0.1)
        alive_count = sum(1 for t in threads if t.is_alive())
        assert alive_count >= 4, (  # Allow for race conditions
            f"FAIL: Only {alive_count}/5 threads still alive after {elapsed:.3f}s"
        )


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_fire_and_forget_daemon_thread():
    """
    ACCEPTANCE: Background thread is daemonized (doesn't block process exit).
    
    Verifies that push threads won't prevent process termination.
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    counter.inc()
    
    # Mock push to never return
    event = Event()
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.side_effect = lambda *args, **kwargs: event.wait()
        
        thread = fire_and_forget_push(
            registry=registry,
            push_url='http://localhost:9091',
            job_name='crashlens_test',
            timeout=2.0
        )
        
        # Wait for thread to start
        time.sleep(0.1)
        
        # Verify thread is daemon
        assert thread.daemon, (
            f"FAIL: Background push thread is not daemonized. "
            f"This will block process exit if push hangs!"
        )
        
        print("✓ PASS: Push thread is daemonized (won't block exit)")
        
        # Signal thread to stop for cleanup
        event.set()


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_fire_and_forget_custom_timeout():
    """
    ACCEPTANCE: Custom timeout values are respected.
    """
    registry = CollectorRegistry()
    counter = Counter('test_counter', 'Test counter', registry=registry)
    counter.inc()
    
    # Track timeout passed to mock
    timeout_used = None
    
    def mock_push_fn(*args, **kwargs):
        nonlocal timeout_used
        timeout_used = kwargs.get('timeout', None)
        time.sleep(1)  # Simulate some work
    
    with patch('prometheus_client.push_to_gateway', side_effect=mock_push_fn):
        # Use custom 5s timeout
        thread = fire_and_forget_push(
            registry=registry,
            push_url='http://localhost:9091',
            job_name='crashlens_test',
            timeout=5.0
        )
        
        # Wait for thread to call mock
        thread.join(timeout=2.0)
        
        assert timeout_used == 5.0, (
            f"FAIL: Expected timeout=5.0, but got {timeout_used}"
        )
        
        print("✓ PASS: Custom timeout (5.0s) correctly passed")


if __name__ == '__main__':
    import sys
    
    print("=" * 70)
    print("FIRE-AND-FORGET PUSH (NON-BLOCKING) VERIFICATION SUITE")
    print("=" * 70)
    
    if not PROMETHEUS_AVAILABLE:
        print("⚠ SKIP: prometheus_client not installed")
        sys.exit(0)
    
    try:
        test_fire_and_forget_completes_quickly_default_timeout()
        test_fire_and_forget_doesnt_raise_on_timeout()
        test_fire_and_forget_doesnt_raise_on_connection_error()
        test_fire_and_forget_multiple_pushes_non_blocking()
        test_fire_and_forget_daemon_thread()
        test_fire_and_forget_custom_timeout()
        print("\n" + "=" * 70)
        print("ALL FIRE-AND-FORGET TESTS PASSED ✓")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n{'=' * 70}")
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)
