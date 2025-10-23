# HTTP Server Security Model

## Overview

CrashLens HTTP server mode exposes Prometheus metrics via HTTP for scraping. This document outlines security considerations and best practices.

---

## Security Principles

### 1. Localhost-Only Default
**Default bind address:** `127.0.0.1`

**Rationale:**
- Prevents accidental internet exposure
- Limits attack surface to local machine
- Forces explicit opt-in for network exposure

**To expose on network:** Must explicitly set `--metrics-addr 0.0.0.0` (discouraged)

---

### 2. Explicit Opt-In Required
**Environment variable:** `CRASHLENS_ALLOW_HTTP_METRICS=true`

**Rationale:**
- Prevents accidental enablement
- Forces user acknowledgment of security implications
- Provides audit trail (environment variable set)

**If not set:** CLI will error with security warning

---

### 3. Mutual Exclusivity
**Cannot use both:** `--push-metrics` AND `--metrics-http`

**Rationale:**
- Clear operational mode
- Prevents resource conflicts
- Simpler error handling

**Enforcement:** CLI validation before server start

---

### 4. Port Range Restriction
**Allowed ports:** 1024-65535

**Rationale:**
- Ports <1024 require root/admin privileges
- Prevents privilege escalation risks
- Standard unprivileged port range

**Default port:** 9090 (Prometheus standard)

---

### 5. Read-Only Metrics
**No write operations:** Server only exposes GET endpoints

**Rationale:**
- Prevents remote code execution
- Limits to monitoring use case
- Reduces attack surface

**Endpoints:**
- `GET /metrics` - Prometheus metrics (read-only)
- `GET /health` - Health check (read-only)
- All other methods: 405 Method Not Allowed

---

## Threat Model

### Threats Considered

1. **Unauthorized Metric Access**
   - **Risk:** Metrics may contain sensitive trace information
   - **Mitigation:** Localhost-only default, explicit opt-in
   - **Status:** ✅ Mitigated

2. **Denial of Service**
   - **Risk:** Excessive requests could slow scan performance
   - **Mitigation:** Daemon thread (doesn't block CLI), rate limiting (future)
   - **Status:** ⚠️ Partially mitigated (no rate limiting yet)

3. **Information Disclosure**
   - **Risk:** Metrics reveal internal policy rules, violation counts
   - **Mitigation:** Localhost-only, network isolation
   - **Status:** ✅ Mitigated (if using localhost)

4. **Accidental Internet Exposure**
   - **Risk:** User binds to 0.0.0.0 and exposes to internet
   - **Mitigation:** Audit banner, security warnings, documentation
   - **Status:** ⚠️ User responsibility

5. **Port Conflicts**
   - **Risk:** Port already in use causes bind failure
   - **Mitigation:** Port availability check, fallback to port+1/+2
   - **Status:** ✅ Mitigated

---

## Security Checklist

### Before Enabling HTTP Server:

- [ ] Understand metrics may contain trace IDs and rule names
- [ ] Verify `--metrics-addr` is `127.0.0.1` (default)
- [ ] Confirm firewall blocks external access to metrics port
- [ ] Review audit banner output for server URL
- [ ] Set `CRASHLENS_ALLOW_HTTP_METRICS=true` explicitly
- [ ] Do NOT expose to internet without reverse proxy + auth

---

## Safe Exposure Patterns

### ✅ SAFE: Local Prometheus Scraping
```yaml
# prometheus.yml
scrape_configs:
  - job_name: crashlens
    static_configs:
      - targets: ['localhost:9090']
```

**Why safe:** All traffic stays on localhost

---

### ✅ SAFE: Kubernetes Pod with Service Mesh
```yaml
# Kubernetes pod with Istio/Linkerd
apiVersion: v1
kind: Pod
metadata:
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "9090"
spec:
  containers:
    - name: crashlens
      env:
        - name: CRASHLENS_ALLOW_HTTP_METRICS
          value: "true"
        - name: CRASHLENS_METRICS_ADDR
          value: "0.0.0.0"  # OK: Pod network isolated
```

**Why safe:** Pod network isolated by service mesh

---

### ⚠️ RISKY: Docker Bind to Host
```bash
# RISKY: Exposes to host network
docker run --network host \
  -e CRASHLENS_ALLOW_HTTP_METRICS=true \
  crashlens scan logs.jsonl --metrics-http
```

**Risk:** Exposed on all host interfaces  
**Mitigation:** Use bridge network instead

---

### ❌ UNSAFE: Bind to 0.0.0.0 on Public Server
```bash
# NEVER DO THIS
export CRASHLENS_ALLOW_HTTP_METRICS=true
crashlens scan logs.jsonl \
  --metrics-http \
  --metrics-addr 0.0.0.0  # ❌ EXPOSED TO INTERNET
```

**Risk:** Metrics exposed to entire internet  
**Consequence:** Information disclosure, DoS attacks

---

## Recommended Architecture

### Option 1: Reverse Proxy with Authentication
```
[CrashLens] → [Nginx/Caddy + Basic Auth] → [Prometheus]
  127.0.0.1        Adds authentication        Scrapes
```

**Nginx config:**
```nginx
location /metrics {
    proxy_pass http://localhost:9090/metrics;
    auth_basic "Metrics";
    auth_basic_user_file /etc/nginx/.htpasswd;
}
```

---

### Option 2: VPN/Private Network Only
```
[CrashLens] → [Private Network] → [Prometheus]
  0.0.0.0        10.0.0.0/8         Scrapes
```

**Required:** Network isolation via VPN, private subnet

---

### Option 3: Mutual TLS (Future)
```
[CrashLens] → [mTLS] → [Prometheus]
  Cert required   Client cert validation
```

**Status:** Not yet implemented (future enhancement)

---

## Audit Banner

When HTTP server starts, this banner is printed to **stderr**:

```
⚠️  WARNING: Metrics HTTP server enabled
   Endpoint: http://127.0.0.1:9090/metrics
   Security: Ensure this is not exposed to the internet
   To disable: Remove --metrics-http flag
```

**Purpose:**
- Clear visibility of server status
- Reminds user of security implications
- Provides quick disable instructions

**Visibility:** Always shown (cannot be suppressed)

---

## Future Enhancements

### Planned (Not Yet Implemented):

1. **Authentication:**
   - Basic auth support
   - Bearer token authentication
   - API key validation

2. **Rate Limiting:**
   - Requests per second limit
   - Circuit breaker on excessive load

3. **TLS Support:**
   - HTTPS endpoint
   - Certificate validation
   - Mutual TLS

4. **IP Allowlist:**
   - Restrict scraping to known IPs
   - CIDR range support

5. **Audit Logging:**
   - Log all scrape requests
   - Track source IPs
   - Alert on unusual patterns

---

## Compliance Considerations

### GDPR
- **Concern:** Metrics may contain trace IDs linked to user data
- **Mitigation:** Use `--summary-only` mode, enable PII removal
- **Recommendation:** Audit metrics for PII before exposing

### SOC 2
- **Concern:** Metrics access should be logged and controlled
- **Mitigation:** Audit banner, localhost default
- **Recommendation:** Use reverse proxy with logging

### HIPAA
- **Concern:** Healthcare data in logs → metrics
- **Mitigation:** PII removal, network isolation
- **Recommendation:** Keep metrics localhost-only

---

## Emergency Response

### If Metrics Are Accidentally Exposed:

1. **Immediate action:**
   ```bash
   # Kill the scan process
   Ctrl+C
   
   # Or set kill switch
   export CRASHLENS_DISABLE_METRICS=true
   ```

2. **Verify exposure:**
   ```bash
   # Check listening ports
   netstat -tuln | grep 9090
   
   # Test external access
   curl http://YOUR_PUBLIC_IP:9090/metrics
   ```

3. **Rotate secrets:**
   - If metrics contained API keys → rotate them
   - If trace IDs exposed → assess data sensitivity
   - Update firewall rules

4. **Incident report:**
   - Document what was exposed
   - Duration of exposure
   - Affected traces/rules

---

## FAQ

### Q: Why require environment variable AND CLI flag?
**A:** Defense in depth. Prevents accidental enablement from scripts copying flags without understanding implications.

### Q: Can I disable the audit banner?
**A:** No. It's intentionally non-suppressible for security visibility.

### Q: Is HTTP mode less secure than Push mode?
**A:** Different threat models:
- **Push:** Credentials sent to Pushgateway (credential leak risk)
- **HTTP:** Server exposed on network (exposure risk)
- Both require careful configuration

### Q: Should I use HTTP or Push mode?
**A:**
- **Push:** For CI/CD, ephemeral processes, Lambda functions
- **HTTP:** For long-running processes, Kubernetes, persistent servers

### Q: Can Prometheus scrape through firewall?
**A:** Only if firewall allows inbound on metrics port. Recommended: Use Prometheus federation or push mode instead.

---

## Summary

**Default posture:** Secure (localhost-only, explicit opt-in)  
**Production readiness:** Safe with proper network isolation  
**Recommended use:** Local development, internal networks only  
**Not recommended:** Public internet exposure without reverse proxy + auth  

**When in doubt:** Use Push mode instead (credential-based, no inbound ports).

---

**Last Updated:** October 23, 2025  
**Version:** HTTP Server Mode v1.0  
**Maintainer:** CrashLens Core Team
