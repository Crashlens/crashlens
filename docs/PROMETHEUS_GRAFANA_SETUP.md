# 📊 Prometheus & Grafana Setup Guide

**Complete guide to setting up CrashLens observability stack on macOS and Windows**

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Setup (Docker)](#quick-setup-docker)
3. [Manual Setup (No Docker)](#manual-setup-no-docker)
4. [Configuration](#configuration)
5. [Importing CrashLens Dashboards](#importing-crashlens-dashboards)
6. [Testing the Setup](#testing-the-setup)
7. [Troubleshooting](#troubleshooting)
8. [Production Deployment](#production-deployment)

---

## Prerequisites

### Required Software

**Docker (Recommended Method):**
- **macOS:** [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)
- **Windows:** [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)

**OR Manual Installation:**
- Prometheus 2.40+
- Pushgateway 1.5+
- Grafana 9.0+

### System Requirements

- **RAM:** 2GB minimum, 4GB recommended
- **Disk Space:** 5GB minimum
- **Ports:** 9090 (Prometheus), 9091 (Pushgateway), 3000 (Grafana)

---

## Quick Setup (Docker)

### Option 1: Docker Compose (Easiest)

**Step 1: Create `docker-compose.yml`**

Create this file in your project root:

```yaml
version: '3.8'

services:
  pushgateway:
    image: prom/pushgateway:latest
    container_name: crashlens_pushgateway
    ports:
      - "9091:9091"
    restart: unless-stopped
    networks:
      - crashlens

  prometheus:
    image: prom/prometheus:latest
    container_name: crashlens_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    restart: unless-stopped
    networks:
      - crashlens
    depends_on:
      - pushgateway

  grafana:
    image: grafana/grafana-oss:latest
    container_name: crashlens_grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./dashboards:/etc/grafana/provisioning/dashboards
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: unless-stopped
    networks:
      - crashlens
    depends_on:
      - prometheus

networks:
  crashlens:
    driver: bridge

volumes:
  prometheus_data:
  grafana_data:
```

**Step 2: Create `prometheus.yml`**

Create this file in your project root:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'crashlens-monitor'

scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['pushgateway:9091']
    scrape_interval: 15s
```

**Step 3: Start All Services**

**macOS:**
```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Windows (PowerShell):**
```powershell
# Start services ( make sure that the docker desktop is running )
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Step 4: Verify Services**

**macOS:**
```bash
# Check Pushgateway
curl http://localhost:9091/metrics

# Check Prometheus
open http://localhost:9090

# Check Grafana
open http://localhost:3000
```

**Windows (PowerShell):**
```powershell
# Check Pushgateway
Invoke-WebRequest http://localhost:9091/metrics

# Check Prometheus
Start-Process http://localhost:9090

# Check Grafana
Start-Process http://localhost:3000
```

---

### Option 2: Individual Docker Containers

If you prefer running containers individually:

#### Start Pushgateway

**macOS:**
```bash
docker run -d \
  --name crashlens_pushgateway \
  -p 9091:9091 \
  --restart unless-stopped \
  prom/pushgateway
```

**Windows (PowerShell):**
```powershell
docker run -d `
  --name crashlens_pushgateway `
  -p 9091:9091 `
  --restart unless-stopped `
  prom/pushgateway
```

#### Start Prometheus

**macOS:**
```bash
# Create prometheus.yml first (see above)

docker run -d \
  --name crashlens_prometheus \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  --restart unless-stopped \
  prom/prometheus
```

**Windows (PowerShell):**
```powershell
# Create prometheus.yml first (see above)

docker run -d `
  --name crashlens_prometheus `
  -p 9090:9090 `
  -v ${PWD}/prometheus.yml:/etc/prometheus/prometheus.yml `
  --restart unless-stopped `
  prom/prometheus
```

**Note for Windows:** Use `host.docker.internal:9091` in `prometheus.yml` instead of `pushgateway:9091` if not using Docker Compose.

#### Start Grafana

**macOS:**
```bash
docker run -d \
  --name crashlens_grafana \
  -p 3000:3000 \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" \
  --restart unless-stopped \
  grafana/grafana-oss
```

**Windows (PowerShell):**
```powershell
docker run -d `
  --name crashlens_grafana `
  -p 3000:3000 `
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" `
  --restart unless-stopped `
  grafana/grafana-oss
```

---

## Manual Setup (No Docker)

### macOS Installation

#### Install via Homebrew

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Prometheus, Pushgateway, and Grafana
brew install prometheus
brew install pushgateway
brew install grafana
```

#### Configure Services

**1. Configure Prometheus:**

Edit `/usr/local/etc/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['localhost:9091']
```

**2. Start Services:**

```bash
# Start Pushgateway
brew services start pushgateway

# Start Prometheus
brew services start prometheus

# Start Grafana
brew services start grafana
```

**3. Verify Services:**

```bash
# Check status
brew services list | grep -E "(prometheus|pushgateway|grafana)"

# Test endpoints
curl http://localhost:9091/metrics
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health
```

---

### Windows Installation

#### Install via Chocolatey

**1. Install Chocolatey (if not already installed):**

Open PowerShell as Administrator:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

**2. Install Services:**

```powershell
# Install Prometheus
choco install prometheus -y

# Install Pushgateway (manual download required)
# Download from: https://prometheus.io/download/#pushgateway

# Install Grafana
choco install grafana -y
```

#### Manual Installation (Alternative)

**1. Download Binaries:**

- **Prometheus:** https://prometheus.io/download/#prometheus
- **Pushgateway:** https://prometheus.io/download/#pushgateway
- **Grafana:** https://grafana.com/grafana/download?platform=windows

**2. Extract and Configure:**

```powershell
# Create installation directory
New-Item -Path "C:\CrashLens\observability" -ItemType Directory -Force

# Extract downloaded archives to:
# C:\CrashLens\observability\prometheus
# C:\CrashLens\observability\pushgateway
# C:\CrashLens\observability\grafana
```

**3. Create `prometheus.yml`:**

Create file at `C:\CrashLens\observability\prometheus\prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['localhost:9091']
```

**4. Start Services:**

Open 3 separate PowerShell windows:

**Window 1 - Pushgateway:**
```powershell
cd C:\CrashLens\observability\pushgateway
.\pushgateway.exe
```

**Window 2 - Prometheus:**
```powershell
cd C:\CrashLens\observability\prometheus
.\prometheus.exe --config.file=prometheus.yml
```

**Window 3 - Grafana:**
```powershell
cd C:\CrashLens\observability\grafana\bin
.\grafana-server.exe
```

**5. Install as Windows Services (Optional):**

```powershell
# Install NSSM (Non-Sucking Service Manager)
choco install nssm -y

# Create services
nssm install CrashLensPushgateway "C:\CrashLens\observability\pushgateway\pushgateway.exe"
nssm install CrashLensPrometheus "C:\CrashLens\observability\prometheus\prometheus.exe" "--config.file=C:\CrashLens\observability\prometheus\prometheus.yml"
nssm install CrashLensGrafana "C:\CrashLens\observability\grafana\bin\grafana-server.exe"

# Start services
Start-Service CrashLensPushgateway
Start-Service CrashLensPrometheus
Start-Service CrashLensGrafana
```

---

## Configuration

### Prometheus Configuration Details

**Basic `prometheus.yml`:**

```yaml
global:
  scrape_interval: 15s          # How often to scrape targets
  evaluation_interval: 15s       # How often to evaluate rules
  external_labels:
    monitor: 'crashlens-monitor'
    environment: 'production'    # Add your environment

# Alertmanager configuration (optional)
alerting:
  alertmanagers:
    - static_configs:
        - targets: []

# Load rules once and periodically evaluate them
rule_files:
  # - "alert_rules.yml"

# Scrape configurations
scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true           # Preserve job/instance labels from pushgateway
    static_configs:
      - targets: ['pushgateway:9091']  # Docker Compose
      # - targets: ['localhost:9091']    # Manual installation
    scrape_interval: 15s
    scrape_timeout: 10s
```

### Grafana Configuration

**Default Admin Credentials:**
- **Username:** `admin`
- **Password:** `admin` (you'll be prompted to change on first login)

**Environment Variables:**

**macOS:**
```bash
export GF_SECURITY_ADMIN_PASSWORD=your_secure_password
export GF_USERS_ALLOW_SIGN_UP=false
export GF_AUTH_ANONYMOUS_ENABLED=false
```

**Windows (PowerShell):**
```powershell
$env:GF_SECURITY_ADMIN_PASSWORD = "your_secure_password"
$env:GF_USERS_ALLOW_SIGN_UP = "false"
$env:GF_AUTH_ANONYMOUS_ENABLED = "false"
```

---

## Importing CrashLens Dashboards

### Step 1: Add Prometheus Data Source

1. **Open Grafana** at http://localhost:3000
2. **Login** with admin/admin
3. **Navigate to:** Configuration → Data Sources → Add data source
4. **Select:** Prometheus
5. **Configure:**
   - **Name:** `CrashLens Prometheus`
   - **URL:** 
     - Docker: `http://prometheus:9090`
     - Manual: `http://localhost:9090`
   - **Access:** Server (default)
6. **Click:** Save & Test

### Step 2: Import CrashLens Dashboard

**Method 1: Import JSON File**

1. **Navigate to:** Create (+) → Import
2. **Click:** Upload JSON file
3. **Select:** `dashboards/crashlens-policy-enforcement.json`
4. **Select Data Source:** CrashLens Prometheus
5. **Click:** Import

**Method 2: Import via Dashboard ID (if published)**

1. **Navigate to:** Create (+) → Import
2. **Enter Dashboard ID:** (if available on Grafana.com)
3. **Click:** Load
4. **Select Data Source:** CrashLens Prometheus
5. **Click:** Import

### Step 3: Configure Alert Rules (Optional)

Import alert rules from `dashboards/crashlens-alert-rules.yml`:

**macOS:**
```bash
# Copy alert rules to Prometheus config directory
cp dashboards/crashlens-alert-rules.yml /usr/local/etc/prometheus/

# Update prometheus.yml to include rules
# Add under rule_files:
#   - "crashlens-alert-rules.yml"

# Restart Prometheus
brew services restart prometheus
```

**Windows (PowerShell):**
```powershell
# Copy alert rules
Copy-Item dashboards/crashlens-alert-rules.yml C:\CrashLens\observability\prometheus\

# Update prometheus.yml to include rules
# Add under rule_files:
#   - "crashlens-alert-rules.yml"

# Restart Prometheus
Restart-Service CrashLensPrometheus
```

---

## Testing the Setup

### Step 1: Push Test Metrics from CrashLens

**macOS:**
```bash
# Scan with demo data and push metrics
crashlens scan --demo \
  --push-metrics \
  --pushgateway-url http://localhost:9091 \
  --metrics-job crashlens_test

# Or scan real logs
crashlens scan sample-logs/demo-logs.jsonl \
  --push-metrics \
  --pushgateway-url http://localhost:9091 \
  --metrics-job crashlens-production
```

**Windows (PowerShell):**
```powershell
# Scan with demo data and push metrics
crashlens scan --demo `
  --push-metrics `
  --pushgateway-url http://localhost:9091 `
  --metrics-job crashlens_test

# Or scan real logs
crashlens scan sample-logs/demo-logs.jsonl `
  --push-metrics `
  --pushgateway-url http://localhost:9091 `
  --metrics-job crashlens-production
```

### Step 2: Verify Metrics in Pushgateway

**macOS:**
```bash
# View all metrics
curl http://localhost:9091/metrics | grep crashlens

# Open in browser
open http://localhost:9091
```

**Windows (PowerShell):**
```powershell
# View all metrics
Invoke-WebRequest http://localhost:9091/metrics | Select-String "crashlens"

# Open in browser
Start-Process http://localhost:9091
```

### Step 3: Query Metrics in Prometheus

1. **Open Prometheus:** http://localhost:9090
2. **Navigate to:** Graph tab
3. **Try these queries:**

```promql
# Total policy violations
sum(crashlens_policy_rule_violations_total)

# Violations by severity
sum by (severity) (crashlens_policy_rule_violations_total)

# Most violated rules (top 5)
topk(5, crashlens_policy_rule_hits_total)

# Processing success rate
rate(crashlens_trace_processing_total{status="success"}[5m])

# Rule evaluation latency (95th percentile)
histogram_quantile(0.95, rate(crashlens_policy_rule_evaluation_seconds_bucket[5m]))
```

### Step 4: View Dashboard in Grafana

1. **Open Grafana:** http://localhost:3000
2. **Navigate to:** Dashboards → Browse
3. **Select:** CrashLens Policy Enforcement
4. **Verify panels show data**

---

## Troubleshooting

### Common Issues

#### 1. Metrics Not Appearing in Pushgateway

**Problem:** No metrics visible after running `crashlens scan --push-metrics`

**Solutions:**

**macOS:**
```bash
# Check if Pushgateway is running
curl http://localhost:9091/-/healthy

# Check CrashLens logs for errors
crashlens scan --demo --push-metrics --pushgateway-url http://localhost:9091 --metrics-job test 2>&1 | grep -i error

# Verify prometheus-client is installed
python -c "from prometheus_client import Counter; print('✓ Installed')"
```

**Windows (PowerShell):**
```powershell
# Check if Pushgateway is running
Invoke-WebRequest http://localhost:9091/-/healthy

# Check CrashLens logs for errors
crashlens scan --demo --push-metrics --pushgateway-url http://localhost:9091 --metrics-job test 2>&1 | Select-String -Pattern "error" -CaseSensitive:$false

# Verify prometheus-client is installed
python -c "from prometheus_client import Counter; print('✓ Installed')"
```

**Fix:**
```bash
# Install metrics support
pip install crashlens[metrics]
```

---

#### 2. Prometheus Not Scraping Pushgateway

**Problem:** Pushgateway has metrics but Prometheus doesn't show them

**Solutions:**

**Check Prometheus Targets:**

**macOS:**
```bash
# Open targets page
open http://localhost:9090/targets

# Check Prometheus logs
docker logs crashlens_prometheus
# OR
tail -f /usr/local/var/log/prometheus.log
```

**Windows (PowerShell):**
```powershell
# Open targets page
Start-Process http://localhost:9090/targets

# Check Prometheus logs
docker logs crashlens_prometheus
# OR
Get-Content C:\CrashLens\observability\prometheus\prometheus.log -Tail 50 -Wait
```

**Fix prometheus.yml for Docker:**
```yaml
scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['pushgateway:9091']  # Docker Compose
      # - targets: ['host.docker.internal:9091']  # Docker individual containers on Windows/Mac
```

**Fix prometheus.yml for Manual Installation:**
```yaml
scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['localhost:9091']
```

**Restart Prometheus:**

**macOS:**
```bash
# Docker
docker restart crashlens_prometheus

# Homebrew
brew services restart prometheus
```

**Windows (PowerShell):**
```powershell
# Docker
docker restart crashlens_prometheus

# Windows Service
Restart-Service CrashLensPrometheus
```

---

#### 3. Grafana Can't Connect to Prometheus

**Problem:** "Bad Gateway" or "Connection refused" errors

**Solutions:**

**Docker Compose:** Use `http://prometheus:9090`

**Docker Individual Containers (Windows/Mac):** Use `http://host.docker.internal:9090`

**Manual Installation:** Use `http://localhost:9090`

**Test connection:**

**macOS:**
```bash
# From Grafana container
docker exec -it crashlens_grafana sh
curl http://prometheus:9090/-/healthy

# From host
curl http://localhost:9090/-/healthy
```

**Windows (PowerShell):**
```powershell
# From Grafana container
docker exec -it crashlens_grafana sh
curl http://prometheus:9090/-/healthy

# From host
Invoke-WebRequest http://localhost:9090/-/healthy
```

---

#### 4. Port Already in Use

**Problem:** "Port 9090 is already allocated" or similar

**Solutions:**

**macOS:**
```bash
# Find process using port
lsof -i :9090
lsof -i :9091
lsof -i :3000

# Kill process
kill -9 <PID>

# Or stop conflicting Docker containers
docker stop $(docker ps -a -q --filter "publish=9090")
```

**Windows (PowerShell):**
```powershell
# Find process using port
Get-NetTCPConnection -LocalPort 9090
Get-NetTCPConnection -LocalPort 9091
Get-NetTCPConnection -LocalPort 3000

# Kill process
Stop-Process -Id <PID> -Force

# Or stop conflicting Docker containers
docker ps -a | Select-String "9090" | ForEach-Object { docker stop $_.ToString().Split()[0] }
```

---

#### 5. Dashboard Shows "No Data"

**Problem:** Dashboard loads but panels show "No data"

**Solutions:**

1. **Check time range** (top-right corner) - set to "Last 15 minutes"
2. **Generate fresh metrics:**

**macOS:**
```bash
crashlens scan --demo --push-metrics --pushgateway-url http://localhost:9091 --metrics-job test
```

**Windows (PowerShell):**
```powershell
crashlens scan --demo --push-metrics --pushgateway-url http://localhost:9091 --metrics-job test
```

3. **Verify query in Explore:**
   - Grafana → Explore → Select "CrashLens Prometheus"
   - Try: `crashlens_policy_rule_violations_total`

4. **Check panel queries match your metrics**

---

#### 6. CrashLens Command Not Found

**Problem:** `crashlens: command not found`

**Solutions:**

**macOS:**
```bash
# Activate Poetry environment
cd /path/to/crashlens
poetry shell

# Or use poetry run
poetry run crashlens scan --demo

# Or ensure CrashLens is in PATH
which crashlens
pip show crashlens
```

**Windows (PowerShell):**
```powershell
# Activate Poetry environment
cd C:\Users\LawLight\OneDrive\Desktop\crashlens
poetry shell

# Or use poetry run
poetry run crashlens scan --demo

# Or ensure CrashLens is in PATH
Get-Command crashlens
pip show crashlens
```

---

## Production Deployment

### Security Considerations

1. **Change default passwords:**

```yaml
# In docker-compose.yml
environment:
  - GF_SECURITY_ADMIN_PASSWORD=your_secure_password_here
```

2. **Enable authentication for Prometheus:**

Add to `prometheus.yml`:
```yaml
global:
  external_labels:
    environment: 'production'

# Enable basic auth
basic_auth:
  username: prometheus
  password: your_secure_password
```

3. **Use HTTPS with reverse proxy (Nginx/Traefik):**

**Example Nginx config:**
```nginx
server {
    listen 443 ssl;
    server_name grafana.yourdomain.com;

    ssl_certificate /etc/ssl/certs/grafana.crt;
    ssl_certificate_key /etc/ssl/private/grafana.key;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### High Availability Setup

For production, consider:

1. **Prometheus clustering** (Thanos/Cortex)
2. **Grafana clustering** (shared database)
3. **Load balancing** for Pushgateway
4. **Persistent storage** for metrics

### Backup Strategy

**macOS:**
```bash
# Backup Prometheus data
tar -czf prometheus-backup-$(date +%Y%m%d).tar.gz /usr/local/var/prometheus/data

# Backup Grafana data
tar -czf grafana-backup-$(date +%Y%m%d).tar.gz /usr/local/var/lib/grafana
```

**Windows (PowerShell):**
```powershell
# Backup Prometheus data
Compress-Archive -Path "C:\CrashLens\observability\prometheus\data" -DestinationPath "prometheus-backup-$(Get-Date -Format 'yyyyMMdd').zip"

# Backup Grafana data
Compress-Archive -Path "C:\CrashLens\observability\grafana\data" -DestinationPath "grafana-backup-$(Get-Date -Format 'yyyyMMdd').zip"
```

### Monitoring the Monitors

Set up health checks:

**macOS:**
```bash
# Create health check script
cat > healthcheck.sh << 'EOF'
#!/bin/bash
curl -f http://localhost:9090/-/healthy || exit 1
curl -f http://localhost:9091/-/healthy || exit 1
curl -f http://localhost:3000/api/health || exit 1
EOF

chmod +x healthcheck.sh

# Run via cron every 5 minutes
# crontab -e
# */5 * * * * /path/to/healthcheck.sh || /path/to/alert-script.sh
```

**Windows (PowerShell):**
```powershell
# Create health check script
@"
`$endpoints = @(
    "http://localhost:9090/-/healthy",
    "http://localhost:9091/-/healthy",
    "http://localhost:3000/api/health"
)

foreach (`$endpoint in `$endpoints) {
    try {
        Invoke-WebRequest `$endpoint -UseBasicParsing | Out-Null
    } catch {
        Write-Error "Health check failed for `$endpoint"
        # Send alert (email, Slack, etc.)
    }
}
"@ | Out-File -FilePath C:\CrashLens\scripts\healthcheck.ps1

# Schedule via Task Scheduler (every 5 minutes)
```

---

## Quick Reference

### Service URLs

| Service | URL | Default Port |
|---------|-----|--------------|
| **Pushgateway** | http://localhost:9091 | 9091 |
| **Prometheus** | http://localhost:9090 | 9090 |
| **Grafana** | http://localhost:3000 | 3000 |

### Common Commands

#### Start/Stop Services

**Docker Compose:**
```bash
# macOS/Windows
docker-compose up -d        # Start
docker-compose down         # Stop
docker-compose restart      # Restart
docker-compose logs -f      # View logs
```

**macOS (Homebrew):**
```bash
brew services start prometheus
brew services stop prometheus
brew services restart prometheus
```

**Windows (Services):**
```powershell
Start-Service CrashLensPrometheus
Stop-Service CrashLensPrometheus
Restart-Service CrashLensPrometheus
```

#### Push Metrics

**macOS:**
```bash
crashlens scan logs.jsonl \
  --push-metrics \
  --pushgateway-url http://localhost:9091 \
  --metrics-job production
```

**Windows:**
```powershell
crashlens scan logs.jsonl `
  --push-metrics `
  --pushgateway-url http://localhost:9091 `
  --metrics-job production
```

---

## Additional Resources

- **[CrashLens Observability Guide](OBSERVABILITY.md)** - Metrics reference and best practices
- **[Grafana Setup Guide](GRAFANA_SETUP.md)** - Advanced dashboard configuration
- **[Prometheus Documentation](https://prometheus.io/docs/)** - Official Prometheus docs
- **[Grafana Documentation](https://grafana.com/docs/)** - Official Grafana docs
- **[CrashLens Dashboards](../dashboards/)** - Pre-built dashboard JSON files

---

**Version:** 1.0  
**Last Updated:** October 27, 2025  
**Maintained By:** CrashLens Team  
**Status:** Production Ready
