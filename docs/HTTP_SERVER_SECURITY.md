# HTTP Server Security Guide

## 🔒 Overview

CrashLens HTTP metrics server exposes Prometheus metrics via HTTP endpoints. This guide covers security requirements, threat model, and best practices.

## ⚠️ Security Model

### Default: Localhost-Only, No Authentication

```bash
# Safe default - binds to 127.0.0.1, accessible only from local machine
crashlens scan logs.jsonl --metrics-http
```

- **Binding**: 127.0.0.1 (localhost-only)
- **Authentication**: None required
- **Accessibility**: Only local processes can access metrics
- **Risk Level**: LOW (metrics not exposed to network)

### Network Binding: Authentication Required

```bash
# Expose on network - REQUIRES authentication
export CRASHLENS_METRICS_AUTH_USER="admin"
export CRASHLENS_METRICS_AUTH_PASS="secret123"
crashlens scan logs.jsonl --metrics-http --metrics-addr 0.0.0.0
```

- **Binding**: 0.0.0.0 (all interfaces), 192.168.x.x (LAN), etc.
- **Authentication**: HTTP Basic Auth (username/password)
- **TTY Check**: Interactive approval required (or --skip-tty-check)
- **Risk Level**: MEDIUM (credentials in transit unless using HTTPS)

## 🔐 Authentication

### Basic Authentication

HTTP Basic Auth protects metrics endpoint when binding to non-localhost.

#### Configuration

**Via Environment Variables** (recommended):
```bash
export CRASHLENS_METRICS_AUTH_USER="prometheus_user"
export CRASHLENS_METRICS_AUTH_PASS="strong_password_here"
crashlens scan logs.jsonl --metrics-http --metrics-addr 0.0.0.0
```

**Via CLI Flags**:
```bash
crashlens scan logs.jsonl --metrics-http \
  --metrics-addr 0.0.0.0 \
  --metrics-auth-user "prometheus_user" \
  --metrics-auth-pass "strong_password_here"
```

#### Prometheus Configuration

Configure Prometheus to use Basic Auth when scraping:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'crashlens'
    basic_auth:
      username: 'prometheus_user'
      password: 'strong_password_here'
    static_configs:
      - targets: ['crashlens-server:9090']
```

### Why Not OAuth/OIDC for OSS?

- **OAuth/OIDC**: Planned for enterprise version (Phase 3)
- **Current OSS**: Basic Auth provides reasonable security for internal networks
- **Rationale**: Prometheus built-in Basic Auth support, simplicity for self-hosted

## 🔍 TTY/Interactivity Check

Non-localhost binding triggers interactive approval check.

### Interactive Environment

```bash
crashlens scan logs.jsonl --metrics-http --metrics-addr 0.0.0.0
```

Output:
```
⚠️  WARNING: You are about to expose metrics on 0.0.0.0:9090
   This will be accessible from other machines on the network.
   Authentication is enabled. Credentials required for access.

Proceed? (yes/no): yes
```

### Non-Interactive Environment (CI/CD)

Use `--skip-tty-check` to bypass interactive approval:

```bash
# CI/CD pipeline - skip TTY check
crashlens scan logs.jsonl --metrics-http \
  --metrics-addr 0.0.0.0 \
  --skip-tty-check \
  --metrics-auth-user "$CI_METRICS_USER" \
  --metrics-auth-pass "$CI_METRICS_PASS"
```

**WARNING**: Only use `--skip-tty-check` in automated environments where you've verified:
1. Firewall rules restrict access
2. Strong credentials are configured
3. Network is trusted (VPN, internal network, etc.)

## 🎯 Endpoints

### `/metrics` - Prometheus Metrics

- **Method**: GET
- **Authentication**: Required for non-localhost
- **Content-Type**: `text/plain; version=0.0.4`
- **Response**: Prometheus exposition format

```bash
# Localhost - no auth
curl http://127.0.0.1:9090/metrics

# Non-localhost - Basic Auth required
curl -u admin:secret123 http://192.168.1.100:9090/metrics
```

### `/health` - Health Check

- **Method**: GET
- **Authentication**: NOT required (always accessible)
- **Content-Type**: `text/plain`
- **Response**: `OK\n`

```bash
# Health check - no auth required
curl http://192.168.1.100:9090/health
```

**Rationale**: Health checks often performed by load balancers/monitoring systems without credentials.

## 🛡️ Threat Model

### Threats Mitigated

| Threat | Mitigation | Residual Risk |
|--------|------------|---------------|
| Unauthorized metrics access (localhost) | Localhost-only binding by default | LOW - requires local access |
| Unauthorized metrics access (network) | Basic Auth + TTY approval | MEDIUM - credentials in transit |
| Accidental exposure | TTY interactive approval | LOW - user must explicitly approve |
| Credential leakage | Env vars (not CLI history) | MEDIUM - env vars visible in `ps` |
| Replay attacks | N/A (HTTP Basic Auth) | HIGH - no nonce/timestamp |

### Threats NOT Mitigated (OSS Version)

| Threat | Enterprise Solution |
|--------|---------------------|
| Man-in-the-middle (MITM) | HTTPS/TLS (reverse proxy) |
| Replay attacks | OAuth 2.0 + short-lived tokens |
| Credential brute-force | Rate limiting (reverse proxy) |
| Session hijacking | OIDC with refresh tokens |

## 🏢 Enterprise Security (Planned)

Phase 3 roadmap for enterprise customers:

### OAuth 2.0 / OIDC Integration

```yaml
# Enterprise config (future)
metrics:
  http:
    enabled: true
    bind: "0.0.0.0:9090"
    auth:
      provider: "oidc"
      issuer_url: "https://auth.example.com"
      client_id: "crashlens-metrics"
      scopes: ["openid", "profile", "metrics:read"]
```

### Mutual TLS (mTLS)

```yaml
# Enterprise config (future)
metrics:
  http:
    tls:
      enabled: true
      cert: "/etc/crashlens/tls/server.crt"
      key: "/etc/crashlens/tls/server.key"
      client_ca: "/etc/crashlens/tls/ca.crt"
```

## 📋 Best Practices

### 1. Localhost-Only for Single-Node

```bash
# Best: Keep it local
crashlens scan logs.jsonl --metrics-http
# Prometheus can scrape via localhost:9090
```

### 2. Use Reverse Proxy for Network Exposure

```nginx
# nginx.conf - terminate TLS at proxy
server {
    listen 443 ssl;
    server_name metrics.example.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:9090;
        proxy_set_header Authorization $http_authorization;
    }
}
```

Then run CrashLens on localhost:
```bash
crashlens scan logs.jsonl --metrics-http
# Prometheus scrapes via https://metrics.example.com (TLS + auth)
```

### 3. Firewall Rules for Direct Network Exposure

```bash
# Allow only Prometheus server IP
iptables -A INPUT -p tcp --dport 9090 -s 192.168.1.50 -j ACCEPT
iptables -A INPUT -p tcp --dport 9090 -j DROP
```

### 4. Rotate Credentials Regularly

```bash
# Use secrets management
export CRASHLENS_METRICS_AUTH_USER=$(vault read -field=user secret/crashlens/metrics)
export CRASHLENS_METRICS_AUTH_PASS=$(vault read -field=pass secret/crashlens/metrics)
```

### 5. Monitor for Unauthorized Access

Check logs for 401 responses:
```bash
# Check CrashLens metrics log
grep "401" /tmp/crashlens-metrics.log

# Check nginx access log
grep "401" /var/log/nginx/access.log | grep "/metrics"
```

## 🚨 Security Checklist

Before exposing metrics on network:

- [ ] Strong credentials configured (`CRASHLENS_METRICS_AUTH_USER` + `CRASHLENS_METRICS_AUTH_PASS`)
- [ ] TTY check passed or `--skip-tty-check` justified
- [ ] Firewall rules restrict access to trusted IPs
- [ ] Reverse proxy with TLS for external access (recommended)
- [ ] Credentials stored in secrets manager (not hardcoded)
- [ ] Monitoring for 401 responses enabled
- [ ] Incident response plan for credential leakage

## 🔧 Troubleshooting

### Error: "Authentication required for non-localhost binding"

**Cause**: Binding to non-localhost (0.0.0.0, 192.168.x.x, etc.) without credentials.

**Fix**:
```bash
export CRASHLENS_METRICS_AUTH_USER="user"
export CRASHLENS_METRICS_AUTH_PASS="pass"
crashlens scan logs.jsonl --metrics-http --metrics-addr 0.0.0.0
```

### Error: "TTY approval required"

**Cause**: Non-interactive environment (CI/CD) without `--skip-tty-check`.

**Fix**:
```bash
crashlens scan logs.jsonl --metrics-http \
  --metrics-addr 0.0.0.0 \
  --skip-tty-check
```

### 401 Unauthorized from Prometheus

**Cause**: Missing or incorrect `basic_auth` in Prometheus config.

**Fix**:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'crashlens'
    basic_auth:
      username: 'correct_user'
      password: 'correct_pass'
    static_configs:
      - targets: ['crashlens:9090']
```

## 📚 References

- [Prometheus Basic Auth](https://prometheus.io/docs/guides/basic-auth/)
- [HTTP Basic Authentication RFC 7617](https://datatracker.ietf.org/doc/html/rfc7617)
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [OAuth 2.0 RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749) (enterprise future)

## 🆘 Support

Security concerns? Contact: security@crashlens.dev

Found a vulnerability? See [SECURITY.md](../SECURITY.md) for responsible disclosure.
