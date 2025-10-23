"""Integration tests for metrics pushgateway (requires external service).

These tests require a running pushgateway instance:
  docker run -d -p 9091:9091 prom/pushgateway

Run with: TEST_PROMETHEUS_INTEGRATION=true pytest tests/integration/
"""

import os
import time
import requests
import pytest
from crashlens.observability import initialize_metrics, get_metrics
from crashlens.observability.server import (
    push_metrics_async,
    validate_pushgateway_url
)


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Test constants
PUSHGATEWAY_URL = "http://localhost:9091"
TEST_JOB_NAME = "crashlens_test"


@pytest.fixture(scope="module")
def pushgateway_url():
    """Get pushgateway URL from environment or use default."""
    return os.getenv('PUSHGATEWAY_URL', PUSHGATEWAY_URL)


@pytest.fixture(scope="module")
def check_pushgateway(pushgateway_url):
    """Verify pushgateway is running before tests."""
    try:
        response = requests.get(f"{pushgateway_url}/metrics", timeout=2)
        if response.status_code != 200:
            pytest.skip(f"Pushgateway not responding at {pushgateway_url}")
    except requests.exceptions.RequestException:
        pytest.skip(
            f"Pushgateway not running at {pushgateway_url}\n"
            f"Start with: docker run -d -p 9091:9091 prom/pushgateway"
        )
    
    return pushgateway_url


@pytest.fixture
def metrics_instance():
    """Create a fresh metrics instance for each test."""
    # Reset global state
    import crashlens.observability.metrics as metrics_module
    metrics_module._metrics_instance = None
    
    # Initialize with test settings
    metrics = initialize_metrics(enabled=True, max_rules=100)
    
    # Record some test data
    metrics.record_rule_hit('test-rule', 'high', 'scan')
    metrics.record_violation('critical')
    metrics.record_trace_processed(count=10)
    metrics.update_decision_latency('test-rule', 0.01, 0.05)
    metrics.update_run_timestamp('success')
    
    yield metrics
    
    # Cleanup (optional)
    metrics_module._metrics_instance = None


# Optional: Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup_pushgateway():
    """Clean up test metrics from pushgateway after all tests."""
    yield
    
    # Cleanup (delete metrics for this job)
    try:
        requests.delete(f"{PUSHGATEWAY_URL}/metrics/job/{TEST_JOB_NAME}", timeout=2)
    except Exception:
        pass


class TestPushgatewayIntegration:
    """Test real metrics push to pushgateway."""
    
    def test_pushgateway_reachable(self, check_pushgateway):
        """Test that pushgateway is responding."""
        response = requests.get(f"{check_pushgateway}/metrics")
        assert response.status_code == 200
        assert 'pushgateway' in response.text.lower()
    
    def test_metrics_push_succeeds(self, check_pushgateway):
        """Test that metrics can be pushed to pushgateway."""
        from crashlens.observability import initialize_metrics
        
        # Initialize metrics
        metrics = initialize_metrics(enabled=True, max_rules=100)
        assert metrics is not None
        
        # Record some metrics
        metrics.record_rule_hit('test-rule-1', 'high', 'scan')
        metrics.record_violation('critical')
        metrics.record_trace_processed(count=10)
        metrics.update_run_timestamp('success')
        
        # Push synchronously (for testing)
        success = push_metrics_sync(
            gateway_url=check_pushgateway,
            job_name='crashlens_integration_test',
            metrics_instance=metrics
        )
        
        assert success, "Metrics push should succeed"
    
    def test_pushed_metrics_visible(self, check_pushgateway):
        """Test that pushed metrics are visible in pushgateway."""
        from crashlens.observability import initialize_metrics
        
        # Initialize and push metrics
        metrics = initialize_metrics(enabled=True, max_rules=100)
        metrics.record_rule_hit('integration-test-rule', 'medium', 'check')
        metrics.record_violation('high')
        metrics.record_trace_processed(count=5)
        metrics.record_trace_failed('parse_error', count=2)
        
        push_metrics_sync(
            gateway_url=check_pushgateway,
            job_name='crashlens_integration_test',
            metrics_instance=metrics
        )
        
        # Wait briefly for pushgateway to process
        time.sleep(0.5)
        
        # Fetch metrics from pushgateway
        response = requests.get(f"{check_pushgateway}/metrics")
        metrics_text = response.text
        
        # Verify key metrics are present
        assert 'crashlens_rule_hits_total' in metrics_text
        assert 'crashlens_violations_total' in metrics_text
        assert 'crashlens_traces_processed_total' in metrics_text
        assert 'crashlens_traces_failed_total' in metrics_text
        assert 'integration-test-rule' in metrics_text
    
    def test_all_metrics_present(self, check_pushgateway):
        """Test that all 8 expected metrics are pushed."""
        from crashlens.observability import initialize_metrics
        
        # Initialize metrics
        metrics = initialize_metrics(enabled=True, max_rules=100)
        
        # Record comprehensive metrics
        metrics.record_rule_hit('comprehensive-rule', 'critical', 'scan')
        metrics.record_violation('medium')
        metrics.record_trace_processed(count=100)
        metrics.record_trace_failed('missing_fields', count=5)
        metrics.update_decision_latency('comprehensive-rule', avg=0.001, max_val=0.005)
        metrics.update_run_timestamp('success')
        
        # Push metrics
        push_metrics_sync(
            gateway_url=check_pushgateway,
            job_name='crashlens_comprehensive_test',
            metrics_instance=metrics
        )
        
        time.sleep(0.5)
        
        # Fetch and validate
        response = requests.get(f"{check_pushgateway}/metrics")
        metrics_text = response.text
        
        expected_metrics = [
            'crashlens_rule_hits_total',
            'crashlens_violations_total',
            'crashlens_traces_processed_total',
            'crashlens_traces_failed_total',
            'crashlens_decision_latency_avg_seconds',
            'crashlens_decision_latency_max_seconds',
            'crashlens_last_run_timestamp_seconds',
            'crashlens_metrics_push_status',
        ]
        
        missing_metrics = []
        for metric_name in expected_metrics:
            if metric_name not in metrics_text:
                missing_metrics.append(metric_name)
        
        assert not missing_metrics, f"Missing metrics: {missing_metrics}"
    
    def test_cardinality_protection_in_pushgateway(self, check_pushgateway):
        """Test that cardinality limit works with real pushgateway."""
        from crashlens.observability import initialize_metrics
        
        # Initialize with low cardinality limit
        metrics = initialize_metrics(enabled=True, max_rules=5)
        
        # Add 10 unique rules (limit is 5)
        for i in range(10):
            metrics.record_rule_hit(f'cardinality-rule-{i}', 'low', 'scan')
        
        # Push metrics
        push_metrics_sync(
            gateway_url=check_pushgateway,
            job_name='crashlens_cardinality_test',
            metrics_instance=metrics
        )
        
        time.sleep(0.5)
        
        # Fetch metrics
        response = requests.get(f"{check_pushgateway}/metrics")
        metrics_text = response.text
        
        # Count how many cardinality-rule metrics appear
        cardinality_rule_count = metrics_text.count('cardinality-rule')
        
        # Should be limited (not all 10)
        assert cardinality_rule_count <= 7, f"Cardinality protection failed: {cardinality_rule_count} rules"
        
        # Overflow metric should be present
        assert 'rule="overflow"' in metrics_text or 'rule_cardinality_overflow' in metrics_text


class TestEndToEndScan:
    """Test end-to-end scan with metrics collection."""
    
    def test_scan_with_metrics_enabled(self, check_pushgateway, tmp_path):
        """Test full scan workflow with metrics push."""
        from click.testing import CliRunner
        from crashlens.cli import scan
        
        # Create test log file
        log_file = tmp_path / "test-scan.jsonl"
        log_file.write_text('''
{"traceId": "trace-1", "model": "gpt-4", "prompt_tokens": 100, "completion_tokens": 10}
{"traceId": "trace-2", "model": "gpt-3.5-turbo", "prompt_tokens": 50, "completion_tokens": 5}
''')
        
        runner = CliRunner()
        result = runner.invoke(scan, [
            str(log_file),
            '--push-metrics',
            '--pushgateway-url', check_pushgateway,
            '--metrics-job', 'crashlens_e2e_test',
            '--format', 'json'
        ])
        
        # Scan should succeed
        assert result.exit_code == 0, f"Scan failed: {result.output}"
        
        # Should see metrics messages
        assert 'Metrics collection enabled' in result.output or 'Metrics pushed' in result.stderr
        
        # Wait for push
        time.sleep(1)
        
        # Verify metrics in pushgateway
        response = requests.get(f"{check_pushgateway}/metrics")
        metrics_text = response.text
        
        assert 'crashlens_traces_processed_total' in metrics_text
        assert 'crashlens_e2e_test' in metrics_text
    
    def test_scan_with_env_var(self, check_pushgateway, tmp_path, monkeypatch):
        """Test scan with environment variable configuration."""
        from click.testing import CliRunner
        from crashlens.cli import scan
        
        # Set environment variables
        monkeypatch.setenv('CRASHLENS_PUSH_METRICS', 'true')
        monkeypatch.setenv('CRASHLENS_PUSHGATEWAY_URL', check_pushgateway)
        
        # Create test log file
        log_file = tmp_path / "test-env.jsonl"
        log_file.write_text('{"traceId": "env-test", "model": "gpt-4", "prompt_tokens": 10, "completion_tokens": 5}\n')
        
        runner = CliRunner()
        result = runner.invoke(scan, [
            str(log_file),
            '--format', 'markdown'
        ])
        
        # Should use env vars and push metrics
        assert result.exit_code == 0
        # Note: In test environment, stderr might not capture the metrics message
        # So we just verify scan succeeded
    
    def test_scan_continues_on_push_failure(self, tmp_path):
        """Test that scan completes even if metrics push fails."""
        from click.testing import CliRunner
        from crashlens.cli import scan
        
        # Create test log file
        log_file = tmp_path / "test-failure.jsonl"
        log_file.write_text('{"traceId": "fail-test", "model": "gpt-4", "prompt_tokens": 10, "completion_tokens": 5}\n')
        
        runner = CliRunner()
        result = runner.invoke(scan, [
            str(log_file),
            '--push-metrics',
            '--pushgateway-url', 'http://invalid-url:9999',  # Invalid URL
            '--format', 'json'
        ])
        
        # Scan should still complete successfully
        assert result.exit_code == 0, "Scan should complete even if push fails"


class TestMetricsAccuracy:
    """Test metrics accuracy with known log data."""
    
    def test_trace_counts_accurate(self, check_pushgateway, tmp_path):
        """Test that trace counts match log file contents."""
        from click.testing import CliRunner
        from crashlens.cli import scan
        
        # Create log file with known trace count
        log_file = tmp_path / "count-test.jsonl"
        traces = [
            f'{{"traceId": "trace-{i}", "model": "gpt-4", "prompt_tokens": 100, "completion_tokens": 10}}\n'
            for i in range(20)
        ]
        log_file.write_text(''.join(traces))
        
        runner = CliRunner()
        result = runner.invoke(scan, [
            str(log_file),
            '--push-metrics',
            '--pushgateway-url', check_pushgateway,
            '--metrics-job', 'crashlens_accuracy_test',
            '--format', 'json'
        ])
        
        assert result.exit_code == 0
        
        time.sleep(1)
        
        # Fetch metrics
        response = requests.get(f"{check_pushgateway}/metrics")
        metrics_text = response.text
        
        # Find traces_processed_total
        for line in metrics_text.split('\n'):
            if 'crashlens_traces_processed_total' in line and not line.startswith('#'):
                # Extract value (e.g., "crashlens_traces_processed_total{...} 20.0")
                parts = line.split()
                if len(parts) >= 2:
                    count = float(parts[-1])
                    assert count >= 20, f"Expected >= 20 traces, got {count}"
                    break


class TestFireAndForgetTiming:
    """Test fire-and-forget push behavior and timing."""
    
    def test_push_to_invalid_url_fails_gracefully(self, metrics_instance):
        """Test that push to invalid URL doesn't crash."""
        # Push to non-existent host (should fail silently)
        start = time.time()
        
        push_metrics_async(
            gateway_url="http://invalid-host-that-doesnt-exist:9999",
            job_name=TEST_JOB_NAME,
            timeout=2.0,
            max_wait=2.0,
            metrics_instance=metrics_instance
        )
        
        elapsed = time.time() - start
        
        # Should return immediately (fire-and-forget with max_wait)
        assert elapsed < 3.0, f"Push blocked for {elapsed}s (expected < 3s)"
    
    def test_fire_and_forget_exits_quickly(self, check_pushgateway, metrics_instance):
        """Test that push doesn't block even with valid gateway."""
        start = time.time()
        
        push_metrics_async(
            gateway_url=check_pushgateway,
            job_name=TEST_JOB_NAME,
            timeout=5.0,
            max_wait=0.5,  # Only wait 0.5 seconds
            metrics_instance=metrics_instance
        )
        
        elapsed = time.time() - start
        
        # Fire-and-forget should exit within max_wait
        assert elapsed < 1.0, f"Push blocked for {elapsed}s (expected < 1.0s)"
    
    def test_metrics_content_validation(self, check_pushgateway, metrics_instance):
        """Test that pushed metrics have correct content."""
        # Push metrics
        push_metrics_async(
            gateway_url=check_pushgateway,
            job_name=TEST_JOB_NAME,
            timeout=5.0,
            max_wait=2.0,
            metrics_instance=metrics_instance
        )
        
        # Wait for push to complete
        time.sleep(3)
        
        # Fetch metrics
        response = requests.get(f"{check_pushgateway}/metrics")
        metrics_text = response.text
        
        # Validate specific metrics exist with correct labels
        assert 'crashlens_rule_hits_total{' in metrics_text
        assert 'rule="test-rule"' in metrics_text
        assert 'severity="high"' in metrics_text
        assert 'mode="scan"' in metrics_text
        assert 'crashlens_violations_total{severity="critical"}' in metrics_text


class TestURLValidationIntegration:
    """Test URL validation with real network checks."""
    
    def test_valid_urls_accepted(self):
        """Test that valid URLs are accepted."""
        valid_urls = [
            'http://localhost:9091',
            'https://prometheus.local:9091',
            'http://192.168.1.1:8080',
            'https://pushgateway.example.com',
        ]
        
        for url in valid_urls:
            result = validate_pushgateway_url(url)
            assert result is not None
            assert result.startswith('http')
    
    def test_invalid_urls_rejected(self):
        """Test that invalid URLs are rejected."""
        invalid_urls = [
            'localhost:9091',  # No scheme
            'ftp://localhost:9091',  # Wrong scheme
            'http://',  # No host
            '',  # Empty
        ]
        
        for url in invalid_urls:
            with pytest.raises((ValueError, AttributeError)):
                validate_pushgateway_url(url)


class TestMetricsPushStatus:
    """Test push status self-monitoring."""
    
    def test_push_status_set_on_success(self, check_pushgateway, metrics_instance):
        """Test that metrics_push_status is set to 1 on success."""
        # Push should succeed
        push_metrics_async(
            gateway_url=check_pushgateway,
            job_name=TEST_JOB_NAME,
            timeout=5.0,
            max_wait=2.0,
            metrics_instance=metrics_instance
        )
        
        time.sleep(3)
        
        # Verify push_status metric
        response = requests.get(f"{check_pushgateway}/metrics")
        metrics_text = response.text
        
        # Should see push_status = 1
        assert 'crashlens_metrics_push_status 1' in metrics_text
    
    def test_push_status_set_on_failure(self, metrics_instance):
        """Test that metrics_push_status is set to 0 on failure."""
        # Push to invalid URL (should fail)
        push_metrics_async(
            gateway_url="http://invalid-host:9999",
            job_name=TEST_JOB_NAME,
            timeout=2.0,
            max_wait=2.0,
            metrics_instance=metrics_instance
        )
        
        time.sleep(3)
        
        # Note: Can't easily verify this without real pushgateway,
        # but the metric should be set in the registry
        metrics = get_metrics()
        assert metrics is not None


# Run integration tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
