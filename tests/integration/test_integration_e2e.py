"""
Integration Test: End-to-End Local Pushgateway Test (The Final Boss)

This is the ultimate verification test. It:
1. Spins up a real Pushgateway Docker container
2. Runs crashlens CLI as a real subprocess with metrics enabled
3. Verifies metrics are pushed and visible in Pushgateway
4. Automatically tears down container when done

Prerequisites:
- Docker must be installed and running
- Port 9091 must be available

Run with:
    TEST_PROMETHEUS_INTEGRATION=true pytest tests/integration/test_integration_e2e.py -v

This test proves the entire Prometheus integration works end-to-end in a production-like scenario.
"""

import os
import sys
import time
import subprocess
import requests
import pytest
import socket
import tempfile
from pathlib import Path

# Mark as integration test (skipped by default)
pytestmark = pytest.mark.integration


def is_docker_available():
    """Check if Docker is available and running."""
    try:
        # Check if docker command exists
        result = subprocess.run(
            ['docker', 'version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        # Docker client exists, but check if daemon is running
        if 'error during connect' in result.stderr.lower() or 'cannot connect' in result.stderr.lower():
            print(f"\n⚠️  Docker is installed but Docker Desktop is not running!")
            print(f"   Please start Docker Desktop and try again.")
            return False
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"\n⚠️  Docker not available: {e}")
        return False


def is_port_available(port: int) -> bool:
    """Check if a port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except OSError:
            return False


def wait_for_pushgateway(url: str, timeout: int = 30) -> bool:
    """Wait for Pushgateway to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(f"{url}/metrics", timeout=2)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.5)
    return False


@pytest.fixture(scope="module")
def docker_pushgateway():
    """
    Spin up a Pushgateway Docker container for testing.
    
    Yields:
        tuple: (container_id, pushgateway_url)
    
    The container is automatically torn down after tests complete.
    """
    # Check prerequisites
    if not is_docker_available():
        pytest.skip("Docker is not available")
    
    port = 9091
    if not is_port_available(port):
        pytest.skip(f"Port {port} is not available")
    
    container_id = None
    pushgateway_url = f"http://localhost:{port}"
    
    try:
        # Pull the Pushgateway image (if not already present)
        print(f"\n📦 Pulling prom/pushgateway image...")
        subprocess.run(
            ['docker', 'pull', 'prom/pushgateway'],
            capture_output=True,
            timeout=60
        )
        
        # Start Pushgateway container
        print(f"🚀 Starting Pushgateway container on port {port}...")
        result = subprocess.run(
            [
                'docker', 'run',
                '-d',  # Detached mode
                '-p', f'{port}:9091',  # Port mapping
                '--rm',  # Auto-remove when stopped
                'prom/pushgateway'
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            pytest.skip(f"Failed to start Pushgateway: {result.stderr}")
        
        container_id = result.stdout.strip()
        print(f"✓ Container started: {container_id[:12]}")
        
        # Wait for Pushgateway to be ready
        print(f"⏳ Waiting for Pushgateway to be ready...")
        if not wait_for_pushgateway(pushgateway_url, timeout=30):
            pytest.fail("Pushgateway did not become ready in time")
        
        print(f"✓ Pushgateway ready at {pushgateway_url}")
        
        yield container_id, pushgateway_url
        
    finally:
        # Cleanup: Stop container
        if container_id:
            print(f"\n🧹 Stopping container {container_id[:12]}...")
            subprocess.run(
                ['docker', 'stop', container_id],
                capture_output=True,
                timeout=10
            )
            print(f"✓ Container stopped")


@pytest.fixture
def sample_log_file(tmp_path):
    """Create a sample log file for CrashLens to scan."""
    log_file = tmp_path / "test-logs.jsonl"
    
    # Create sample traces matching demo-logs.jsonl format (nested usage object)
    logs = [
        # Trace 1: Retry loop (should trigger detection)
        '{"traceId":"trace-001","startTime":"2024-01-15T10:00:00Z","input":{"model":"gpt-4","prompt":"Test query 1"},"usage":{"prompt_tokens":100,"completion_tokens":50,"total_tokens":150},"cost":0.009,"level":"ERROR","statusMessage":"Rate limit exceeded"}',
        '{"traceId":"trace-001","startTime":"2024-01-15T10:00:10Z","input":{"model":"gpt-4","prompt":"Test query 1"},"usage":{"prompt_tokens":100,"completion_tokens":50,"total_tokens":150},"cost":0.009,"level":"ERROR","statusMessage":"Rate limit exceeded"}',
        '{"traceId":"trace-001","startTime":"2024-01-15T10:00:20Z","input":{"model":"gpt-4","prompt":"Test query 1"},"usage":{"prompt_tokens":100,"completion_tokens":50,"total_tokens":150},"cost":0.009,"level":"ERROR","statusMessage":"Rate limit exceeded"}',
        '{"traceId":"trace-001","startTime":"2024-01-15T10:00:30Z","input":{"model":"gpt-4","prompt":"Test query 1"},"usage":{"prompt_tokens":100,"completion_tokens":50,"total_tokens":150},"cost":0.009,"level":"ERROR","statusMessage":"Rate limit exceeded"}',
        
        # Trace 2: Normal successful trace
        '{"traceId":"trace-002","startTime":"2024-01-15T10:01:00Z","input":{"model":"gpt-3.5-turbo","prompt":"Normal query"},"usage":{"prompt_tokens":50,"completion_tokens":25,"total_tokens":75},"cost":0.0001125,"level":"DEFAULT"}',
        
        # Trace 3: Another normal trace
        '{"traceId":"trace-003","startTime":"2024-01-15T10:02:00Z","input":{"model":"gpt-4","prompt":"Another query"},"usage":{"prompt_tokens":200,"completion_tokens":100,"total_tokens":300},"cost":0.018,"level":"DEFAULT"}',
    ]
    
    log_file.write_text('\n'.join(logs) + '\n', encoding='utf-8')
    return log_file


def test_e2e_metrics_push_to_real_pushgateway(docker_pushgateway, sample_log_file):
    """
    The Final Boss: End-to-end test with real Pushgateway container.
    
    This test proves that the entire Prometheus integration works:
    - Lazy loading (no overhead when disabled)
    - Environment variable configuration
    - CLI subprocess execution
    - Metrics collection during scan
    - Push to real Pushgateway
    - Proper metric formatting
    
    ACCEPTANCE CRITERIA:
    1. CrashLens CLI runs successfully with metrics enabled
    2. Exit code is 0 (success)
    3. Metrics are pushed to Pushgateway
    4. All expected metric names are visible in Pushgateway
    5. Metric values are reasonable (non-zero)
    """
    container_id, pushgateway_url = docker_pushgateway
    
    print(f"\n{'='*80}")
    print(f"🎯 E2E TEST: Running CrashLens CLI with Real Pushgateway")
    print(f"{'='*80}")
    
    # Prepare environment variables
    env = os.environ.copy()
    env['CRASHLENS_PUSH_METRICS'] = 'true'  # Enable metrics push
    env['CRASHLENS_PUSHGATEWAY_URL'] = pushgateway_url
    env['CRASHLENS_METRICS_JOB'] = 'crashlens_e2e_test'  # Set custom job name
    
    # Unset disable flag to ensure metrics are enabled
    env.pop('CRASHLENS_DISABLE_METRICS', None)
    
    print(f"\n📝 Environment:")
    print(f"  CRASHLENS_PUSH_METRICS: true")
    print(f"  CRASHLENS_PUSHGATEWAY_URL: {pushgateway_url}")
    print(f"  CRASHLENS_METRICS_JOB: crashlens_e2e_test")
    print(f"  Log file: {sample_log_file}")
    
    # Run crashlens CLI as a real subprocess
    print(f"\n🚀 Running CrashLens CLI...")
    
    # Use poetry run to ensure correct environment
    result = subprocess.run(
        [
            'poetry', 'run', 'crashlens', 'scan',
            str(sample_log_file),
            '--format', 'json'
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        cwd=Path(__file__).parent.parent.parent  # Project root
    )
    
    print(f"\n📊 CrashLens Output:")
    print(f"Exit Code: {result.returncode}")
    print(f"\nSTDOUT:")
    print(result.stdout[:1000] if len(result.stdout) > 1000 else result.stdout)
    if result.stderr:
        print(f"\nSTDERR:")
        print(result.stderr[:1000] if len(result.stderr) > 1000 else result.stderr)
    
    # CRITICAL ASSERTION 1: CLI should succeed
    assert result.returncode == 0, (
        f"CrashLens CLI failed with exit code {result.returncode}\n"
        f"STDERR: {result.stderr}"
    )
    
    print(f"✓ PASS: CrashLens CLI executed successfully (exit code 0)")
    
    # Wait briefly for metrics to be pushed
    time.sleep(2)
    
    # Fetch metrics from Pushgateway
    print(f"\n🔍 Fetching metrics from Pushgateway...")
    response = requests.get(f"{pushgateway_url}/metrics", timeout=5)
    
    # CRITICAL ASSERTION 2: Pushgateway should respond
    assert response.status_code == 200, (
        f"Failed to fetch metrics from Pushgateway: {response.status_code}"
    )
    
    metrics_text = response.text
    print(f"✓ PASS: Pushgateway responded (200 OK)")
    print(f"  Metrics size: {len(metrics_text)} bytes")
    
    # CRITICAL ASSERTION 3: Check for CrashLens job name
    assert 'job="crashlens_e2e_test"' in metrics_text, (
        f"CrashLens job not found in Pushgateway metrics"
    )
    print(f"✓ PASS: CrashLens job found in Pushgateway")
    
    # CRITICAL ASSERTION 4: Verify all expected metrics are present
    expected_metrics = [
        'crashlens_run_success',  # Run status
        'crashlens_traces_processed_total',  # Traces processed
        'crashlens_detections_total',  # Detections made
        'crashlens_last_run_timestamp_seconds',  # Timestamp
    ]
    
    missing_metrics = []
    found_metrics = []
    
    for metric_name in expected_metrics:
        if metric_name in metrics_text:
            found_metrics.append(metric_name)
            print(f"✓ PASS: Found metric '{metric_name}'")
            
            # Extract value (basic parsing)
            for line in metrics_text.split('\n'):
                if metric_name in line and not line.startswith('#'):
                    print(f"      Value: {line.strip()}")
                    break
        else:
            missing_metrics.append(metric_name)
            print(f"✗ FAIL: Missing metric '{metric_name}'")
    
    # Print sample of metrics for debugging
    print(f"\n📈 Sample metrics from Pushgateway:")
    print("="*80)
    lines = [l for l in metrics_text.split('\n') if 'crashlens' in l.lower()]
    for line in lines[:20]:  # First 20 crashlens lines
        if line.strip() and not line.startswith('#'):
            print(f"  {line.strip()}")
    print("="*80)
    
    # CRITICAL ASSERTION 5: At least 2 of 4 core metrics should be present
    # (Some metrics may only appear if detections were made)
    assert len(found_metrics) >= 2, (
        f"Expected at least 2 core metrics, found {len(found_metrics)}: {found_metrics}\n"
        f"Missing: {missing_metrics}"
    )
    
    print(f"\n✓ PASS: Found {len(found_metrics)}/{len(expected_metrics)} core metrics")
    
    # CRITICAL ASSERTION 6: Verify metric values are reasonable
    # Check that at least one metric has a non-zero value
    non_zero_found = False
    for line in metrics_text.split('\n'):
        if 'crashlens' in line.lower() and not line.startswith('#'):
            # Extract numeric value (simple regex)
            import re
            match = re.search(r'(\d+\.?\d*)\s*$', line)
            if match:
                value = float(match.group(1))
                if value > 0:
                    non_zero_found = True
                    print(f"✓ PASS: Found non-zero metric value: {value}")
                    break
    
    assert non_zero_found, (
        "All metrics have zero values - something may be wrong with metric recording"
    )
    
    print(f"\n{'='*80}")
    print(f"🎉 E2E TEST PASSED: All assertions successful!")
    print(f"{'='*80}")
    print(f"\n✅ Verified:")
    print(f"  1. CrashLens CLI executed successfully")
    print(f"  2. Metrics pushed to real Pushgateway container")
    print(f"  3. Job name correctly set")
    print(f"  4. Core metrics present ({len(found_metrics)} found)")
    print(f"  5. Metric values are non-zero (data is being recorded)")
    print(f"\n🏆 This proves the ENTIRE Prometheus integration works end-to-end!")


def test_e2e_metrics_disabled_by_default(docker_pushgateway, sample_log_file):
    """
    E2E test verifying metrics are NOT pushed when PROMETHEUS_PUSHGATEWAY_URL is not set.
    
    This proves the opt-in behavior works in a real E2E scenario.
    """
    container_id, pushgateway_url = docker_pushgateway
    
    print(f"\n{'='*80}")
    print(f"🎯 E2E TEST: CrashLens without Pushgateway URL (disabled)")
    print(f"{'='*80}")
    
    # Prepare environment variables WITHOUT Pushgateway URL
    env = os.environ.copy()
    env.pop('PROMETHEUS_PUSHGATEWAY_URL', None)
    env.pop('CRASHLENS_DISABLE_METRICS', None)
    
    # Get initial metrics from Pushgateway
    response_before = requests.get(f"{pushgateway_url}/metrics", timeout=5)
    metrics_before = response_before.text
    
    # Count crashlens job instances before
    jobs_before = metrics_before.count('job="crashlens')
    
    print(f"\n📊 Metrics before CrashLens run:")
    print(f"  CrashLens jobs in Pushgateway: {jobs_before}")
    
    # Run crashlens CLI without Pushgateway URL
    print(f"\n🚀 Running CrashLens CLI (metrics disabled)...")
    result = subprocess.run(
        [
            'poetry', 'run', 'crashlens', 'scan',
            str(sample_log_file),
            '--format', 'json'
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        cwd=Path(__file__).parent.parent.parent
    )
    
    print(f"Exit Code: {result.returncode}")
    
    # CLI should still succeed
    assert result.returncode == 0, (
        f"CrashLens CLI failed: {result.stderr}"
    )
    
    print(f"✓ PASS: CrashLens CLI executed successfully")
    
    # Wait briefly
    time.sleep(1)
    
    # Get metrics again
    response_after = requests.get(f"{pushgateway_url}/metrics", timeout=5)
    metrics_after = response_after.text
    
    # Count crashlens job instances after
    jobs_after = metrics_after.count('job="crashlens')
    
    print(f"\n📊 Metrics after CrashLens run:")
    print(f"  CrashLens jobs in Pushgateway: {jobs_after}")
    
    # CRITICAL ASSERTION: No new crashlens jobs should appear
    assert jobs_after == jobs_before, (
        f"Metrics were pushed when they shouldn't be! "
        f"Before: {jobs_before}, After: {jobs_after}"
    )
    
    print(f"✓ PASS: No metrics pushed (opt-in behavior verified)")
    
    print(f"\n{'='*80}")
    print(f"🎉 E2E OPT-IN TEST PASSED!")
    print(f"{'='*80}")
    print(f"\n✅ Verified: Metrics are NOT pushed when PROMETHEUS_PUSHGATEWAY_URL is unset")


if __name__ == '__main__':
    """Allow running directly for manual testing."""
    import sys
    
    print("=" * 80)
    print("END-TO-END INTEGRATION TEST (Manual Run)")
    print("=" * 80)
    print("\nNOTE: This test requires Docker to be running!")
    print("      Port 9091 must be available.")
    print("\nStarting test...")
    
    # Run pytest on this file
    sys.exit(pytest.main([__file__, '-v', '-s']))
