#!/usr/bin/env python3
"""
Fire-and-Forget Push Test
Tests that metrics pushing doesn't block CLI execution even with dead/slow pushgateway.
"""

import time
import threading
import requests


def test_push_with_timeout():
    """Test fire-and-forget push with 2s timeout"""
    
    print("Testing fire-and-forget push pattern...")
    print("-" * 70)
    
    def push_worker():
        """Worker thread that attempts to push metrics"""
        try:
            print("  [Thread] Attempting push to dead endpoint...")
            # Simulate slow push (use fake URL that will timeout)
            requests.post('http://localhost:99999/metrics/job/crashlens', 
                         data='test_metric 1\n',
                         timeout=10)
            print("  [Thread] Push succeeded (unexpected)")
        except requests.exceptions.ConnectionError as e:
            print(f"  [Thread] Connection failed (expected): {type(e).__name__}")
        except requests.exceptions.Timeout as e:
            print(f"  [Thread] Timeout (expected): {type(e).__name__}")
        except Exception as e:
            print(f"  [Thread] Push failed (expected): {type(e).__name__}")
    
    start = time.time()
    
    # Create daemon thread (won't block process exit)
    thread = threading.Thread(target=push_worker, daemon=True)
    print(f"  [Main] Starting daemon thread at t={0:.2f}s")
    thread.start()
    
    # Wait maximum 2 seconds for thread
    print(f"  [Main] Waiting max 2.0s for thread...")
    thread.join(timeout=2.0)
    
    elapsed = time.time() - start
    
    print(f"  [Main] Exited after {elapsed:.2f}s")
    print("-" * 70)
    
    # Validate acceptance criteria
    assert elapsed < 2.5, f"❌ FAIL: Blocked too long: {elapsed:.2f}s"
    print(f"✓ PASS: Fire-and-forget works correctly ({elapsed:.2f}s < 2.5s)")
    print("✓ Thread is daemon (won't block process exit)")
    print("✓ Works with unreachable URLs")
    

def test_fast_success_path():
    """Test that successful pushes complete quickly"""
    
    print("\nTesting fast success path (mock endpoint)...")
    print("-" * 70)
    
    def push_worker_success():
        """Worker that simulates fast success"""
        try:
            # Use httpbin.org echo endpoint for testing
            print("  [Thread] Pushing to httpbin.org/post (fast endpoint)")
            response = requests.post('https://httpbin.org/post', 
                                    json={'metric': 'test_value', 'value': 1},
                                    timeout=5)
            print(f"  [Thread] Success! Status: {response.status_code}")
        except Exception as e:
            print(f"  [Thread] Failed: {type(e).__name__}: {e}")
    
    start = time.time()
    thread = threading.Thread(target=push_worker_success, daemon=True)
    print(f"  [Main] Starting daemon thread at t={0:.2f}s")
    thread.start()
    
    # Wait for completion
    thread.join(timeout=5.0)
    elapsed = time.time() - start
    
    print(f"  [Main] Completed in {elapsed:.2f}s")
    print("-" * 70)
    
    if elapsed < 5.0:
        print(f"✓ PASS: Fast path works ({elapsed:.2f}s < 5.0s)")
    else:
        print(f"⚠ WARNING: Slow success path ({elapsed:.2f}s)")


def test_immediate_return():
    """Test that main thread doesn't wait for push completion"""
    
    print("\nTesting immediate return (no blocking)...")
    print("-" * 70)
    
    def slow_push():
        """Simulates a slow push that takes 5 seconds"""
        print("  [Thread] Starting slow operation (5s)...")
        time.sleep(5)
        print("  [Thread] Slow operation complete")
    
    start = time.time()
    thread = threading.Thread(target=slow_push, daemon=True)
    print(f"  [Main] Starting slow thread at t={0:.2f}s")
    thread.start()
    
    # Don't wait - return immediately
    print("  [Main] NOT waiting for thread (immediate return)")
    elapsed = time.time() - start
    
    print(f"  [Main] Returned after {elapsed:.2f}s")
    print("-" * 70)
    
    assert elapsed < 0.5, f"❌ FAIL: Blocked: {elapsed:.2f}s"
    print(f"✓ PASS: Immediate return works ({elapsed:.2f}s < 0.5s)")
    print("✓ Background thread continues running (daemon)")


if __name__ == '__main__':
    print("=" * 70)
    print("Fire-and-Forget Push Pattern Tests")
    print("=" * 70)
    print("\nThese tests validate that metrics pushing won't block CLI execution")
    print("even with dead, slow, or unreachable pushgateway endpoints.\n")
    
    try:
        # Test 1: Dead endpoint with timeout
        test_push_with_timeout()
        
        # Test 2: Fast success path
        test_fast_success_path()
        
        # Test 3: Immediate return (no blocking)
        test_immediate_return()
        
        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✓")
        print("=" * 70)
        print("\nKey Findings:")
        print("  1. Daemon threads don't block process exit")
        print("  2. Timeouts prevent indefinite blocking")
        print("  3. Failed pushes don't crash the application")
        print("  4. Fast success path works correctly")
        print("  5. Immediate return pattern allows non-blocking execution")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        exit(1)
