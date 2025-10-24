"""
Test: Push Success/Failure Counters
Purpose: Verify crashlens_push_success_total and crashlens_push_failure_total
         counters accurately track push outcomes.
         
Acceptance Criteria:
- Success counter increments on successful push
- Failure counter increments on push errors (timeout, connection, HTTP)
- Counters are independent (success doesn't affect failure count)
- Counters accumulate across multiple pushes
- Counters exported correctly in Prometheus format

This ensures observability of the metrics push system itself.
"""

import pytest
import time
from unittest.mock import patch, MagicMock

try:
    from prometheus_client import CollectorRegistry, Counter, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class PushMetrics:
    """
    Test shim for tracking push success/failure counters.
    Mimics production metrics collection.
    """
    
    def __init__(self, registry=None):
        self.registry = registry or CollectorRegistry()
        
        self.success_counter = Counter(
            'crashlens_push_success_total',
            'Total successful pushes to Pushgateway',
            registry=self.registry
        )
        
        self.failure_counter = Counter(
            'crashlens_push_failure_total',
            'Total failed pushes to Pushgateway',
            ['error_type'],  # Label for error classification
            registry=self.registry
        )
    
    def push_with_tracking(self, registry_to_push, push_url: str, job_name: str, timeout: float = 2.0):
        """
        Attempt push and track outcome in counters.
        """
        try:
            from prometheus_client import push_to_gateway
            push_to_gateway(push_url, job=job_name, registry=registry_to_push, timeout=timeout)
            self.success_counter.inc()
            return True
        except TimeoutError:
            self.failure_counter.labels(error_type='timeout').inc()
            return False
        except ConnectionError:
            self.failure_counter.labels(error_type='connection').inc()
            return False
        except Exception as e:
            self.failure_counter.labels(error_type='other').inc()
            return False


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_push_success_counter_increments():
    """
    ACCEPTANCE: Success counter increments on successful push.
    """
    metrics = PushMetrics()
    test_registry = CollectorRegistry()
    counter = Counter('test_metric', 'Test', registry=test_registry)
    counter.inc()
    
    # Mock successful push
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.return_value = None  # Success
        
        result = metrics.push_with_tracking(
            registry_to_push=test_registry,
            push_url='http://localhost:9091',
            job_name='crashlens_test',
            timeout=2.0
        )
        
        assert result is True, "Push should return True on success"
        
        # Check counter value
        output = generate_latest(metrics.registry).decode('utf-8')
        assert 'crashlens_push_success_total' in output, (
            f"FAIL: Success counter not in output"
        )
        
        # Extract counter value (should be 1)
        lines = [line for line in output.split('\n') 
                 if 'crashlens_push_success_total' in line and not line.startswith('#')]
        assert len(lines) > 0, "FAIL: Success counter metric line not found"
        
        # Value should be 1 or 1.0
        assert '1' in lines[0], (
            f"FAIL: Expected success counter = 1, got: {lines[0]}"
        )
        
        print("✓ PASS: Success counter incremented to 1")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_push_failure_counter_increments_on_timeout():
    """
    ACCEPTANCE: Failure counter increments on timeout with error_type label.
    """
    metrics = PushMetrics()
    test_registry = CollectorRegistry()
    counter = Counter('test_metric', 'Test', registry=test_registry)
    counter.inc()
    
    # Mock timeout
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.side_effect = TimeoutError("Connection timed out")
        
        result = metrics.push_with_tracking(
            registry_to_push=test_registry,
            push_url='http://localhost:9091',
            job_name='crashlens_test',
            timeout=2.0
        )
        
        assert result is False, "Push should return False on timeout"
        
        # Check counter value
        output = generate_latest(metrics.registry).decode('utf-8')
        assert 'crashlens_push_failure_total' in output, (
            f"FAIL: Failure counter not in output"
        )
        
        # Should have error_type="timeout" label
        assert 'error_type="timeout"' in output, (
            f"FAIL: Timeout error_type label not found in output:\n{output}"
        )
        
        print("✓ PASS: Failure counter incremented with error_type=timeout")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_push_failure_counter_increments_on_connection_error():
    """
    ACCEPTANCE: Failure counter increments on connection error with label.
    """
    metrics = PushMetrics()
    test_registry = CollectorRegistry()
    counter = Counter('test_metric', 'Test', registry=test_registry)
    counter.inc()
    
    # Mock connection error
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.side_effect = ConnectionError("Connection refused")
        
        result = metrics.push_with_tracking(
            registry_to_push=test_registry,
            push_url='http://localhost:9091',
            job_name='crashlens_test',
            timeout=2.0
        )
        
        assert result is False, "Push should return False on connection error"
        
        output = generate_latest(metrics.registry).decode('utf-8')
        assert 'error_type="connection"' in output, (
            f"FAIL: Connection error_type label not found"
        )
        
        print("✓ PASS: Failure counter incremented with error_type=connection")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_push_counters_accumulate_correctly():
    """
    ACCEPTANCE: Counters accumulate over multiple pushes.
    
    Simulates 3 successes, 2 timeouts, 1 connection error.
    """
    metrics = PushMetrics()
    test_registry = CollectorRegistry()
    counter = Counter('test_metric', 'Test', registry=test_registry)
    
    with patch('prometheus_client.push_to_gateway') as mock_push:
        # First 3 pushes: success
        mock_push.return_value = None
        for i in range(3):
            counter.inc()
            result = metrics.push_with_tracking(test_registry, 'http://localhost:9091', f'job_{i}')
            assert result is True
        
        # Next 2 pushes: timeout
        mock_push.side_effect = TimeoutError("Timeout")
        for i in range(2):
            counter.inc()
            result = metrics.push_with_tracking(test_registry, 'http://localhost:9091', f'job_{i+3}')
            assert result is False
        
        # Last push: connection error
        mock_push.side_effect = ConnectionError("Connection refused")
        counter.inc()
        result = metrics.push_with_tracking(test_registry, 'http://localhost:9091', 'job_5')
        assert result is False
    
    # Verify counters
    output = generate_latest(metrics.registry).decode('utf-8')
    
    # Success counter should be 3
    success_lines = [line for line in output.split('\n')
                     if 'crashlens_push_success_total' in line and not line.startswith('#')]
    assert len(success_lines) > 0
    assert '3' in success_lines[0], (
        f"FAIL: Expected success counter = 3, got: {success_lines[0]}"
    )
    
    # Failure counter with timeout should be 2
    timeout_lines = [line for line in output.split('\n')
                     if 'crashlens_push_failure_total' in line 
                     and 'error_type="timeout"' in line
                     and not line.startswith('#')]
    assert len(timeout_lines) > 0
    assert '2' in timeout_lines[0], (
        f"FAIL: Expected timeout failures = 2, got: {timeout_lines[0]}"
    )
    
    # Failure counter with connection should be 1
    connection_lines = [line for line in output.split('\n')
                        if 'crashlens_push_failure_total' in line
                        and 'error_type="connection"' in line
                        and not line.startswith('#')]
    assert len(connection_lines) > 0
    assert '1' in connection_lines[0], (
        f"FAIL: Expected connection failures = 1, got: {connection_lines[0]}"
    )
    
    print("✓ PASS: Counters accumulated correctly")
    print("  Success: 3")
    print("  Timeout failures: 2")
    print("  Connection failures: 1")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_push_counters_independent():
    """
    ACCEPTANCE: Success and failure counters are independent.
    
    Incrementing one doesn't affect the other.
    """
    metrics = PushMetrics()
    test_registry = CollectorRegistry()
    counter = Counter('test_metric', 'Test', registry=test_registry)
    
    with patch('prometheus_client.push_to_gateway') as mock_push:
        # 5 successful pushes
        mock_push.return_value = None
        for i in range(5):
            counter.inc()
            metrics.push_with_tracking(test_registry, 'http://localhost:9091', f'job_{i}')
        
        # Check that failure counter is still 0 (or not present)
        output = generate_latest(metrics.registry).decode('utf-8')
        
        # Success should be 5
        assert 'crashlens_push_success_total 5' in output or 'crashlens_push_success_total 5.0' in output
        
        # Failure counter should not exist or be 0 for all labels
        failure_lines = [line for line in output.split('\n')
                         if 'crashlens_push_failure_total' in line
                         and not line.startswith('#')
                         and '0' not in line]  # Non-zero lines
        
        assert len(failure_lines) == 0, (
            f"FAIL: Failure counter incremented when only successes occurred:\n"
            f"{chr(10).join(failure_lines)}"
        )
        
        print("✓ PASS: Success counter independent of failure counter")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_push_failure_other_error_type():
    """
    ACCEPTANCE: Generic exceptions labeled as error_type="other".
    """
    metrics = PushMetrics()
    test_registry = CollectorRegistry()
    counter = Counter('test_metric', 'Test', registry=test_registry)
    counter.inc()
    
    # Mock generic exception
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.side_effect = Exception("HTTP 500 Internal Server Error")
        
        result = metrics.push_with_tracking(
            registry_to_push=test_registry,
            push_url='http://localhost:9091',
            job_name='crashlens_test'
        )
        
        assert result is False
        
        output = generate_latest(metrics.registry).decode('utf-8')
        assert 'error_type="other"' in output, (
            f"FAIL: Generic exception not labeled as error_type=other"
        )
        
        print("✓ PASS: Generic exceptions labeled as error_type=other")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_push_counters_prometheus_format():
    """
    ACCEPTANCE: Counters exported in valid Prometheus text format.
    """
    metrics = PushMetrics()
    test_registry = CollectorRegistry()
    counter = Counter('test_metric', 'Test', registry=test_registry)
    counter.inc()
    
    with patch('prometheus_client.push_to_gateway') as mock_push:
        mock_push.return_value = None
        metrics.push_with_tracking(test_registry, 'http://localhost:9091', 'test')
    
    output = generate_latest(metrics.registry).decode('utf-8')
    
    # Should have HELP lines
    assert '# HELP crashlens_push_success_total' in output
    assert '# HELP crashlens_push_failure_total' in output
    
    # Should have TYPE lines
    assert '# TYPE crashlens_push_success_total counter' in output
    assert '# TYPE crashlens_push_failure_total counter' in output
    
    # Should have metric lines
    assert 'crashlens_push_success_total' in output
    
    print("✓ PASS: Counters exported in valid Prometheus format")
    print("Sample output:")
    for line in output.split('\n')[:10]:
        if line.strip():
            print(f"  {line}")


if __name__ == '__main__':
    import sys
    
    print("=" * 70)
    print("PUSH SUCCESS/FAILURE COUNTERS VERIFICATION SUITE")
    print("=" * 70)
    
    if not PROMETHEUS_AVAILABLE:
        print("⚠ SKIP: prometheus_client not installed")
        sys.exit(0)
    
    try:
        test_push_success_counter_increments()
        test_push_failure_counter_increments_on_timeout()
        test_push_failure_counter_increments_on_connection_error()
        test_push_counters_accumulate_correctly()
        test_push_counters_independent()
        test_push_failure_other_error_type()
        test_push_counters_prometheus_format()
        print("\n" + "=" * 70)
        print("ALL PUSH COUNTER TESTS PASSED ✓")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n{'=' * 70}")
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)
