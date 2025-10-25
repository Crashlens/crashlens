# E2E Integration Test - Setup Guide

## Overview

The E2E integration test (`tests/integration/test_integration_e2e.py`) is the **ultimate verification** that proves the entire Prometheus integration works end-to-end with a real Pushgateway.

## What It Tests

1. **Real Docker Container** - Spins up `prom/pushgateway` container
2. **Real CLI Execution** - Runs `crashlens scan` as a subprocess
3. **Real Metrics Push** - Pushes metrics to the running Pushgateway
4. **Real Verification** - Queries Pushgateway to verify metrics are present

## Prerequisites

### 1. Docker Desktop Must Be Running

**Windows:**
- Install Docker Desktop from https://www.docker.com/products/docker-desktop
- Start Docker Desktop (look for whale icon in system tray)
- Verify with: `docker version` (should show both client and server)

**macOS:**
- Install Docker Desktop
- Start Docker Desktop (menubar icon)
- Verify with: `docker version`

**Linux:**
- Install Docker Engine: `sudo apt-get install docker.io`
- Start Docker: `sudo systemctl start docker`
- Verify with: `docker version`

### 2. Port 9091 Must Be Available

The test uses port 9091 for Pushgateway. Make sure nothing else is using it:

```bash
# Windows PowerShell
Test-NetConnection -ComputerName localhost -Port 9091

# Linux/macOS
lsof -i :9091
```

### 3. Internet Connection (First Run Only)

The test needs to pull the `prom/pushgateway` Docker image on first run (~50MB download).

## Running the Test

### Option 1: Run via pytest (Recommended)

```bash
# Enable integration tests
$env:TEST_PROMETHEUS_INTEGRATION="true"  # Windows PowerShell
# OR
export TEST_PROMETHEUS_INTEGRATION=true  # Linux/macOS

# Run the E2E test
poetry run pytest tests/integration/test_integration_e2e.py -v -s
```

### Option 2: Run directly

```bash
# The test file can be run directly
poetry run python tests/integration/test_integration_e2e.py
```

## Expected Output

```
================================================================================
             E2E TEST: Running CrashLens CLI with Real Pushgateway
================================================================================

📦 Pulling prom/pushgateway image...
🚀 Starting Pushgateway container on port 9091...
✓ Container started: a1b2c3d4e5f6
⏳ Waiting for Pushgateway to be ready...
✓ Pushgateway ready at http://localhost:9091

📝 Environment:
  PROMETHEUS_PUSHGATEWAY_URL: http://localhost:9091
  PROMETHEUS_PUSH_JOB_NAME: crashlens_e2e_test
  Log file: /tmp/pytest-xyz/test-logs.jsonl

🚀 Running CrashLens CLI...

📊 CrashLens Output:
Exit Code: 0

STDOUT:
...

✓ PASS: CrashLens CLI executed successfully (exit code 0)

🔍 Fetching metrics from Pushgateway...
✓ PASS: Pushgateway responded (200 OK)
  Metrics size: 2458 bytes
✓ PASS: CrashLens job found in Pushgateway
✓ PASS: Found metric 'crashlens_run_success'
      Value: crashlens_run_success{job="crashlens_e2e_test"} 1.0
✓ PASS: Found metric 'crashlens_traces_processed_total'
      Value: crashlens_traces_processed_total{job="crashlens_e2e_test"} 6.0
✓ PASS: Found metric 'crashlens_detections_total'
✓ PASS: Found metric 'crashlens_last_run_timestamp_seconds'

📈 Sample metrics from Pushgateway:
================================================================================
  crashlens_run_success{job="crashlens_e2e_test"} 1.0
  crashlens_traces_processed_total{job="crashlens_e2e_test"} 6.0
  crashlens_detections_total{detector="retry_loop",job="crashlens_e2e_test"} 1.0
  crashlens_last_run_timestamp_seconds{job="crashlens_e2e_test",status="success"} 1729875234.0
================================================================================

✓ PASS: Found 4/4 core metrics
✓ PASS: Found non-zero metric value: 1.0

================================================================================
🎉 E2E TEST PASSED: All assertions successful!
================================================================================

✅ Verified:
  1. CrashLens CLI executed successfully
  2. Metrics pushed to real Pushgateway container
  3. Job name correctly set
  4. Core metrics present (4 found)
  5. Metric values are non-zero (data is being recorded)

🏆 This proves the ENTIRE Prometheus integration works end-to-end!

🧹 Stopping container a1b2c3d4e5f6...
✓ Container stopped
```

## Troubleshooting

### Error: "Docker is not available"

**Solution:** Start Docker Desktop
- Windows: Open Docker Desktop from Start menu
- macOS: Open Docker Desktop from Applications
- Linux: `sudo systemctl start docker`

Then verify: `docker version` (should show both client AND server)

### Error: "Port 9091 is not available"

**Solution:** Kill the process using port 9091
```bash
# Windows PowerShell
Get-Process -Id (Get-NetTCPConnection -LocalPort 9091).OwningProcess | Stop-Process

# Linux/macOS
kill $(lsof -t -i:9091)
```

### Error: "Failed to pull image"

**Solution:** Check internet connection and Docker Hub access
```bash
# Test Docker Hub connectivity
docker pull hello-world
```

### Error: "Container did not start"

**Solution:** Check Docker logs
```bash
# See recent Docker logs
docker logs $(docker ps -a -q --latest)

# Check Docker daemon status
docker info
```

### Test Hangs on "Waiting for Pushgateway to be ready..."

**Solution:** 
1. Check if Pushgateway container is running: `docker ps`
2. Check if port is mapped correctly: `docker port <container_id>`
3. Try accessing manually: `curl http://localhost:9091/metrics`

## Manual Verification (Without Test)

If you want to manually verify the integration:

### Step 1: Start Pushgateway

```bash
docker run -d -p 9091:9091 --name pushgateway prom/pushgateway
```

### Step 2: Run CrashLens with metrics enabled

```bash
export PROMETHEUS_PUSHGATEWAY_URL=http://localhost:9091
export PROMETHEUS_PUSH_JOB_NAME=crashlens_manual_test
export PROMETHEUS_PUSH_ON_EXIT=true

poetry run crashlens scan sample-logs/demo-logs.jsonl
```

### Step 3: Verify metrics

```bash
# View all metrics
curl http://localhost:9091/metrics | grep crashlens

# Should show lines like:
# crashlens_run_success{job="crashlens_manual_test"} 1.0
# crashlens_traces_processed_total{job="crashlens_manual_test"} 10.0
```

### Step 4: Cleanup

```bash
docker stop pushgateway
docker rm pushgateway
```

## CI/CD Integration

To run this test in CI/CD:

### GitHub Actions

```yaml
- name: Start Docker
  run: sudo systemctl start docker

- name: Run E2E Integration Test
  env:
    TEST_PROMETHEUS_INTEGRATION: true
  run: |
    poetry install --extras metrics
    poetry run pytest tests/integration/test_integration_e2e.py -v
```

### GitLab CI

```yaml
integration-e2e:
  services:
    - docker:dind
  variables:
    TEST_PROMETHEUS_INTEGRATION: "true"
  script:
    - poetry install --extras metrics
    - poetry run pytest tests/integration/test_integration_e2e.py -v
```

## Why This Test Matters

This is the **ultimate proof** that your Prometheus integration works because:

1. **Real Infrastructure** - Uses actual Docker container, not mocks
2. **Real CLI** - Runs crashlens as a subprocess, exactly as users would
3. **Real Network** - Pushes metrics over HTTP to real Pushgateway
4. **Real Verification** - Queries Pushgateway API to verify data
5. **Real Cleanup** - Automatically tears down container

**This is the test you show to investors, stakeholders, and users to prove the feature works end-to-end in a production-like environment.**

## Success Criteria

- ✅ Docker container starts successfully
- ✅ CrashLens CLI exits with code 0
- ✅ Metrics are pushed to Pushgateway
- ✅ All core metrics are present
- ✅ Metric values are non-zero
- ✅ Container is cleaned up automatically

---

**Last Updated:** October 25, 2025
**CrashLens Version:** 2.9.20
