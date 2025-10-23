"""
Integration tests for HTTP Server metrics functionality.

These tests make REAL HTTP requests and start REAL servers.
They are marked with @pytest.mark.integration and skip by default.

To run these tests:
    export TEST_PROMETHEUS_INTEGRATION=true
    pytest tests/integration/test_http_server_integration.py -v -s

Requirements:
    - Available ports (9090-9095)
    - Network access to localhost
    - requests library installed
"""

import pytest
import time
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock
from crashlens.observability import initialize_metrics
from crashlens.observability.http_server import MetricsHTTPServer

# Skip all tests unless explicitly enabled
pytestmark = pytest.mark.skipif(
    os.getenv('TEST_PROMETHEUS_INTEGRATION') != 'true',
    reason="Integration tests disabled. Set TEST_PROMETHEUS_INTEGRATION=true to enable."
)


@pytest.fixture
def metrics_instance():
    """Create a real metrics instance for testing"""
    metrics = initialize_metrics(
        enabled=True,
        max_rules=100,
        sample_rate=1.0
    )
    
    # Add some test metrics (if enabled)
    if metrics:
        if hasattr(metrics, 'record_rule_hit'):
            metrics.record_rule_hit('test_rule', 'high', 'scan')
        if hasattr(metrics, 'record_violation'):
            metrics.record_violation('high')
    
    yield metrics


@pytest.fixture
def http_server(metrics_instance):
    """Create and start a real HTTP server"""
    # Use a high port to avoid conflicts
    server = MetricsHTTPServer(metrics_instance, '127.0.0.1', 9093)
    
    try:
        url = server.start()
        # Give server time to start
        time.sleep(0.5)
        yield server, url
    finally:
        server.stop()
        # Give server time to stop
        time.sleep(0.5)


class TestRealHTTPServer:
    """Integration tests with real HTTP server"""
    
    @pytest.mark.integration
    def test_real_server_starts_and_serves_metrics(self, http_server):
        """Server should start and serve metrics via HTTP"""
        server, url = http_server
        
        # Make real HTTP request
        response = requests.get(f"{url}/metrics", timeout=5)
        
        assert response.status_code == 200
        assert 'text/plain' in response.headers.get('Content-Type', '')
        
        # Check for Prometheus metrics format
        content = response.text
        assert '# HELP' in content or '# TYPE' in content or 'crashlens_' in content
        
        print(f"\n✓ Server responded with {len(content)} bytes")
    
    @pytest.mark.integration
    def test_prometheus_can_scrape_endpoint(self, http_server):
        """Prometheus should be able to scrape the metrics endpoint"""
        server, url = http_server
        
        # Simulate Prometheus scrape
        response = requests.get(
            f"{url}/metrics",
            headers={'Accept': 'text/plain'},
            timeout=5
        )
        
        assert response.status_code == 200
        
        # Parse metrics (basic validation)
        lines = response.text.split('\n')
        metric_lines = [line for line in lines if line and not line.startswith('#')]
        
        # Should have at least some metrics
        assert len(metric_lines) > 0, "No metrics found in response"
        
        # Check for CrashLens metrics
        crashlens_metrics = [line for line in lines if 'crashlens_' in line]
        assert len(crashlens_metrics) > 0, "No crashlens metrics found"
        
        print(f"\n✓ Found {len(metric_lines)} metric lines")
        print(f"✓ Found {len(crashlens_metrics)} crashlens metrics")
    
    @pytest.mark.integration
    def test_health_endpoint_responds(self, http_server):
        """Health endpoint should return 200 OK"""
        server, url = http_server
        
        response = requests.get(f"{url}/health", timeout=5)
        
        assert response.status_code == 200
        assert response.text.strip() == "OK"
        
        print("\n✓ Health endpoint OK")
    
    @pytest.mark.integration
    def test_server_handles_concurrent_requests(self, http_server):
        """Server should handle multiple concurrent requests"""
        server, url = http_server
        
        def make_request(request_id):
            """Make a single request"""
            try:
                response = requests.get(f"{url}/metrics", timeout=5)
                return request_id, response.status_code, len(response.text)
            except Exception as e:
                return request_id, None, str(e)
        
        # Make 10 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        # All requests should succeed
        successes = [r for r in results if r[1] == 200]
        assert len(successes) == 10, f"Only {len(successes)}/10 requests succeeded"
        
        # All should return content
        sizes = [r[2] for r in successes if isinstance(r[2], int)]
        assert all(size > 0 for size in sizes), "Some responses were empty"
        assert len(sizes) == 10, "Some responses returned errors"
        
        print(f"\n✓ All 10 concurrent requests succeeded")
        print(f"  Response sizes: min={min(sizes)}, max={max(sizes)}, avg={sum(sizes)//len(sizes)}")
    
    @pytest.mark.integration
    def test_server_returns_404_for_unknown_endpoint(self, http_server):
        """Server should return 404 for unknown endpoints"""
        server, url = http_server
        
        response = requests.get(f"{url}/unknown", timeout=5)
        
        assert response.status_code == 404
        assert '404' in response.text or 'Not Found' in response.text
        
        print("\n✓ 404 returned for unknown endpoint")
    
    @pytest.mark.integration
    def test_server_stops_cleanly(self, metrics_instance):
        """Server should stop cleanly without hanging"""
        # Create server
        server = MetricsHTTPServer(metrics_instance, '127.0.0.1', 9094)
        url = server.start()
        
        # Verify it's running
        response = requests.get(f"{url}/health", timeout=5)
        assert response.status_code == 200
        
        # Stop server
        start_time = time.time()
        server.stop()
        stop_time = time.time()
        
        # Should stop quickly (within 3 seconds)
        elapsed = stop_time - start_time
        assert elapsed < 3.0, f"Server took {elapsed:.2f}s to stop (expected <3s)"
        
        # Server should no longer respond
        with pytest.raises(requests.exceptions.ConnectionError):
            requests.get(f"{url}/health", timeout=1)
        
        print(f"\n✓ Server stopped cleanly in {elapsed:.2f}s")


class TestServerPortFallback:
    """Integration tests for port fallback logic"""
    
    @pytest.mark.integration
    def test_server_falls_back_to_next_port(self, metrics_instance):
        """Server should try port+1 if primary port is unavailable"""
        # Start first server on 9095
        server1 = MetricsHTTPServer(metrics_instance, '127.0.0.1', 9095)
        url1 = server1.start()
        assert '9095' in url1
        
        try:
            # Try to start second server on same port
            server2 = MetricsHTTPServer(metrics_instance, '127.0.0.1', 9095)
            url2 = server2.start()
            
            # Should have fallen back to 9096
            assert '9096' in url2
            
            # Both should be accessible
            response1 = requests.get(f"{url1}/health", timeout=5)
            response2 = requests.get(f"{url2}/health", timeout=5)
            
            assert response1.status_code == 200
            assert response2.status_code == 200
            
            print(f"\n✓ Server 1: {url1}")
            print(f"✓ Server 2: {url2} (fallback)")
            
            server2.stop()
        finally:
            server1.stop()


class TestMetricsContent:
    """Integration tests for metrics content validation"""
    
    @pytest.mark.integration
    def test_metrics_include_crashlens_specific_metrics(self, http_server):
        """Response should include CrashLens-specific metrics"""
        server, url = http_server
        
        response = requests.get(f"{url}/metrics", timeout=5)
        content = response.text
        
        # Check for specific CrashLens metrics
        expected_metrics = [
            'crashlens_rule_hits_total',
            'crashlens_violations_total',
            'crashlens_traces_processed_total',
        ]
        
        found_metrics = []
        for metric in expected_metrics:
            if metric in content:
                found_metrics.append(metric)
        
        assert len(found_metrics) >= 1, f"Expected at least 1 CrashLens metric, found {len(found_metrics)}"
        
        print(f"\n✓ Found {len(found_metrics)} CrashLens metrics:")
        for metric in found_metrics:
            print(f"  • {metric}")
    
    @pytest.mark.integration
    def test_metrics_format_is_valid_prometheus(self, http_server):
        """Metrics should be in valid Prometheus text format"""
        server, url = http_server
        
        response = requests.get(f"{url}/metrics", timeout=5)
        lines = response.text.split('\n')
        
        # Validate Prometheus format
        comment_lines = [l for l in lines if l.startswith('#')]
        metric_lines = [l for l in lines if l and not l.startswith('#')]
        
        # Should have comments (HELP and TYPE)
        assert len(comment_lines) > 0, "No comment lines found"
        
        # Should have metric data
        assert len(metric_lines) > 0, "No metric lines found"
        
        # Metric lines should have format: metric_name{labels} value
        for line in metric_lines[:5]:  # Check first 5
            if '{' in line:
                # Has labels
                assert '}' in line, f"Invalid label format: {line}"
                assert ' ' in line.split('}')[1], f"Missing value: {line}"
            else:
                # No labels
                parts = line.split()
                assert len(parts) >= 2, f"Invalid metric format: {line}"
        
        print(f"\n✓ Valid Prometheus format:")
        print(f"  • {len(comment_lines)} comment lines")
        print(f"  • {len(metric_lines)} metric lines")


if __name__ == '__main__':
    # Run with integration tests enabled
    os.environ['TEST_PROMETHEUS_INTEGRATION'] = 'true'
    pytest.main([__file__, '-v', '-s'])
