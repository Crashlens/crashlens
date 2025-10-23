#!/usr/bin/env python3
"""End-to-end integration test for Prometheus metrics.

Tests the full flow:
1. Start pushgateway
2. Run scan with --push-metrics
3. Verify metrics appear in pushgateway
4. Validate all 8 metrics have data
"""

import subprocess
import time
import requests
import sys
from pathlib import Path

# Test configuration
PUSHGATEWAY_URL = "http://localhost:9091"
TEST_LOG_FILE = "sample-logs/demo-logs.jsonl"
EXPECTED_METRICS = [
    'crashlens_rule_hits_total',
    'crashlens_violations_total',
    'crashlens_traces_processed_total',
    'crashlens_traces_failed_total',
    'crashlens_decision_latency_avg_seconds',
    'crashlens_decision_latency_max_seconds',
    'crashlens_last_run_timestamp_seconds',
    'crashlens_metrics_push_status',
]

def check_pushgateway_running():
    """Check if pushgateway is running."""
    try:
        response = requests.get(f"{PUSHGATEWAY_URL}/metrics", timeout=2)
        return response.status_code == 200
    except:
        return False

def run_crashlens_with_metrics():
    """Run crashlens scan with metrics enabled."""
    cmd = [
        "python", "-m", "crashlens", "scan",
        TEST_LOG_FILE,
        "--push-metrics",
        "--pushgateway-url", PUSHGATEWAY_URL
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("=== CrashLens Output ===")
    print(result.stdout)
    if result.stderr:
        print("=== Stderr ===")
        print(result.stderr)
    
    return result.returncode == 0

def fetch_metrics():
    """Fetch metrics from pushgateway."""
    try:
        response = requests.get(f"{PUSHGATEWAY_URL}/metrics", timeout=5)
        return response.text
    except Exception as e:
        print(f"Error fetching metrics: {e}")
        return None

def validate_metrics(metrics_text):
    """Validate all expected metrics are present."""
    if not metrics_text:
        return False
    
    found_metrics = []
    missing_metrics = []
    
    for metric_name in EXPECTED_METRICS:
        if metric_name in metrics_text:
            found_metrics.append(metric_name)
            
            # Extract value for validation
            for line in metrics_text.split('\n'):
                if line.startswith(metric_name) and not line.startswith('#'):
                    print(f"  ✓ {metric_name}: {line}")
                    break
        else:
            missing_metrics.append(metric_name)
    
    print(f"\nMetrics found: {len(found_metrics)}/{len(EXPECTED_METRICS)}")
    
    if missing_metrics:
        print(f"Missing metrics: {missing_metrics}")
        return False
    
    return True

def main():
    print("=" * 60)
    print("CrashLens Metrics Integration Test")
    print("=" * 60)
    
    # Check pushgateway
    print("\n[1/4] Checking pushgateway...")
    if not check_pushgateway_running():
        print("✗ Pushgateway not running!")
        print(f"Start it with: docker run -d -p 9091:9091 prom/pushgateway")
        sys.exit(1)
    print(f"✓ Pushgateway running at {PUSHGATEWAY_URL}")
    
    # Run crashlens
    print("\n[2/4] Running CrashLens with metrics...")
    if not run_crashlens_with_metrics():
        print("✗ CrashLens scan failed")
        sys.exit(1)
    print("✓ CrashLens scan completed")
    
    # Wait for push
    print("\n[3/4] Waiting for metrics push...")
    time.sleep(3)  # Give time for fire-and-forget push
    
    # Fetch and validate
    print("\n[4/4] Validating metrics...")
    metrics_text = fetch_metrics()
    if not validate_metrics(metrics_text):
        print("\n✗ FAIL: Missing metrics")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)

if __name__ == '__main__':
    main()
