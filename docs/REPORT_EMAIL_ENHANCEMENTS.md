# CrashLens Report Command - Enhanced Email Features

## Overview

The `crashlens report` command has been enhanced with SMTP configuration file support and HTML attachment capabilities, making it easier to send automated cost digest reports with rich formatting and detailed policy violation reports.

## Features

### 1. SMTP Configuration File Support

Instead of managing SMTP credentials solely through environment variables, you can now store them in a `.crashlens/smtp.yaml` configuration file.

**Benefits:**
- Centralized credential management
- Team-wide shared configuration (with environment-specific overrides)
- Easier CI/CD integration
- Support for optional settings (TLS, timeout)

#### Configuration Precedence

CrashLens uses the following precedence for SMTP configuration (highest to lowest):

1. **Environment Variables** (highest priority)
   - `SMTP_SERVER`: SMTP server hostname
   - `SMTP_PORT`: SMTP server port (converted to integer)
   - `SMTP_USER`: SMTP username
   - `SMTP_PASSWORD`: SMTP password
   - `SMTP_FROM`: From address for emails

2. **YAML Configuration File**
   - Loaded from `.crashlens/smtp.yaml` in current directory or up to 5 parent directories
   - See example below

3. **No defaults** - all required fields must be provided via env vars or YAML

#### Creating an SMTP Configuration File

Generate an example configuration:

```bash
crashlens config smtp-example
```

This creates `.crashlens/smtp.yaml`:

```yaml
# CrashLens SMTP Configuration
# Environment variables override these values:
#   $SMTP_SERVER overrides server
#   $SMTP_PORT overrides port
#   $SMTP_USER overrides user
#   $SMTP_PASSWORD overrides password
#   $SMTP_FROM overrides from

server: smtp.gmail.com
port: 587
user: alerts@example.com
password: your-app-specific-password
from: CrashLens Alerts <alerts@example.com>
use_tls: true
timeout: 30
```

**Required Fields:**
- `server`: SMTP server hostname
- `port`: SMTP server port (integer)
- `user`: SMTP authentication username
- `password`: SMTP authentication password
- `from`: Email "From" address

**Optional Fields:**
- `use_tls`: Enable TLS (default: `true`)
- `timeout`: Connection timeout in seconds (default: `30`)

#### Environment Variable Override

Override specific settings without editing the YAML file:

```bash
# Use production SMTP server but keep other settings from YAML
export SMTP_SERVER=smtp.prod.example.com
export SMTP_FROM="Production Alerts <prod-alerts@example.com>"

crashlens report logs.jsonl --email team@example.com
```

This is useful for:
- **CI/CD pipelines**: Store credentials in secrets manager, reference in YAML
- **Multi-environment setups**: Use staging SMTP in dev, production SMTP in prod
- **Sensitive data**: Keep passwords out of version control

#### Gmail App Passwords

If using Gmail, create an app-specific password:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable 2-Step Verification
3. Navigate to "App passwords"
4. Generate a new app password for "Mail"
5. Use this 16-character password in `SMTP_PASSWORD`

#### Testing SMTP Configuration

Verify your configuration:

```bash
# Send test report
crashlens report sample-logs/demo-logs.jsonl --email your-email@example.com
```

If configuration is invalid, you'll see:

```
❌ Email sending requires SMTP configuration

💡 Configure SMTP in one of two ways:

1️⃣  Environment Variables:
   export SMTP_SERVER=smtp.gmail.com
   export SMTP_PORT=587
   export SMTP_USER=your-email@example.com
   export SMTP_PASSWORD=your-app-password
   export SMTP_FROM=noreply@example.com

2️⃣  YAML Configuration File (.crashlens/smtp.yaml):
   Run: crashlens config smtp-example
   Then edit: .crashlens/smtp.yaml
```

---

### 2. HTML Email Attachments

Attach detailed HTML policy violation reports to your cost digest emails using the `--attach-html` flag.

#### Use Case

Combine `crashlens guard` HTML output with `crashlens report` for comprehensive monitoring:

1. **Run guard** to generate policy violations report as HTML
2. **Send email** with cost digest + HTML attachment

#### Workflow Example

```bash
# Step 1: Run guard with HTML output
crashlens guard logs.jsonl \
  --policy-file policies/production.yaml \
  --format html \
  --output guard-$(date +%Y%m%d).html

# Step 2: Send report with HTML attachment
crashlens report logs.jsonl \
  --email team@example.com \
  --attach-html guard-$(date +%Y%m%d).html
```

**Output:**
```
✅ Guard completed (found 3 violations, 0 suppressed)
📄 Report saved: guard-20240115.html
✅ Report sent via email to team@example.com (with attachment: guard-20240115.html)
```

#### Automated CI/CD Example

GitHub Actions workflow:

```yaml
name: Weekly Cost Monitoring

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9 AM UTC

jobs:
  cost-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Fetch logs from Langfuse
        run: |
          crashlens fetch-langfuse --hours-back 168 > weekly-logs.jsonl
        env:
          LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
          LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
      
      - name: Run policy check (generate HTML)
        run: |
          crashlens guard weekly-logs.jsonl \
            --policy-file policies/weekly-budget.yaml \
            --format html \
            --output guard-weekly.html
        continue-on-error: true  # Don't fail if violations found
      
      - name: Send weekly report with violations
        run: |
          crashlens report weekly-logs.jsonl \
            --email ${{ secrets.TEAM_EMAIL }} \
            --attach-html guard-weekly.html
        env:
          SMTP_SERVER: smtp.gmail.com
          SMTP_PORT: 587
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
          SMTP_FROM: "CrashLens Weekly <${{ secrets.SMTP_USER }}>"
```

#### Email Structure

When using `--attach-html`, the email contains:

1. **Email Body** (multipart/alternative):
   - Plain text version (for basic email clients)
   - HTML version (for rich rendering)

2. **Attachment** (multipart/mixed):
   - Attached HTML file with proper `Content-Disposition: attachment`
   - Filename preserved (e.g., `guard-20240115.html`)
   - Content-Type: `text/html`

#### Attachment File Requirements

- **Must exist**: Click validates file existence before running command
- **Must be readable**: If file cannot be read, a warning is shown but email still sends
- **Recommended naming**: `guard-<RUN_ID>.html` or `guard-<DATE>.html` for clarity

#### Error Handling

**File not found:**
```bash
crashlens report logs.jsonl --email team@example.com --attach-html missing.html
```
```
Error: Invalid value for '--attach-html': Path 'missing.html' does not exist.
```

**File cannot be read (permission issue):**
```bash
chmod 000 guard-12345.html
crashlens report logs.jsonl --email team@example.com --attach-html guard-12345.html
```
```
⚠️  Warning: Could not attach HTML file: Permission denied
✅ Report sent via email to team@example.com
```

The email will still send, but without the attachment.

---

## Command Reference

### `crashlens report`

Generate cost digest report from JSONL logs.

**Syntax:**
```bash
crashlens report LOGFILE [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` | `[slack\|md\|text]` | `md` | Output format for the report |
| `--webhook-url` | `TEXT` | - | Slack webhook URL for sending reports |
| `--email` | `TEXT` | - | Email address to send report to (requires SMTP configuration) |
| `--attach-html` | `PATH` | - | Path to HTML file to attach (e.g., guard-<RUN_ID>.html) |
| `--previous-logs` | `PATH` | - | Previous period logs for week-over-week comparison |

**Examples:**

Generate markdown report:
```bash
crashlens report logs.jsonl
```

Send to email with YAML config:
```bash
crashlens report logs.jsonl --email team@example.com
```

Send with environment variables:
```bash
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=alerts@example.com
export SMTP_PASSWORD=app-specific-password
export SMTP_FROM="CrashLens Alerts <alerts@example.com>"

crashlens report logs.jsonl --email team@example.com
```

Attach HTML guard report:
```bash
crashlens report logs.jsonl \
  --email team@example.com \
  --attach-html guard-12345.html
```

Week-over-week comparison:
```bash
crashlens report current-week.jsonl \
  --previous-logs last-week.jsonl \
  --email team@example.com
```

### `crashlens config smtp-example`

Generate example SMTP configuration file.

**Syntax:**
```bash
crashlens config smtp-example [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` | `PATH` | `.crashlens/smtp.yaml` | Output path for example config |

**Examples:**

Create default config:
```bash
crashlens config smtp-example
```

Create custom location:
```bash
crashlens config smtp-example --output config/smtp.yaml
```

---

## Security Best Practices

### 1. Protect SMTP Passwords

**DO:**
- ✅ Use app-specific passwords (not your main email password)
- ✅ Store passwords in secrets managers (GitHub Secrets, AWS Secrets Manager, etc.)
- ✅ Use environment variables in CI/CD pipelines
- ✅ Add `.crashlens/smtp.yaml` to `.gitignore` if it contains credentials

**DON'T:**
- ❌ Commit SMTP passwords to version control
- ❌ Use your main email account password
- ❌ Share SMTP credentials in plaintext (Slack, email, etc.)
- ❌ Log SMTP passwords in CI/CD output

### 2. YAML Configuration Security

If storing credentials in YAML:

```bash
# Restrict file permissions (Unix/Linux)
chmod 600 .crashlens/smtp.yaml

# Or use environment variable override
cat <<EOF > .crashlens/smtp.yaml
server: smtp.gmail.com
port: 587
user: alerts@example.com
password: $SMTP_PASSWORD  # Will be overridden by env var
from: CrashLens Alerts <alerts@example.com>
EOF
```

### 3. Masked Output

CrashLens automatically masks passwords in logs:

```python
from crashlens.config.smtp_config import load_smtp_config

config = load_smtp_config()
print(config.get_masked_dict())
# Output: {'server': 'smtp.gmail.com', 'password': '***', ...}
```

---

## Troubleshooting

### SMTP Authentication Failed

**Error:**
```
❌ SMTP authentication failed. Check SMTP_USER and SMTP_PASSWORD
```

**Solutions:**
1. Verify credentials are correct
2. Use app-specific password (not main account password)
3. Check if 2FA is enabled (requires app password)
4. Ensure SMTP user matches from address domain

### TLS/SSL Connection Issues

**Error:**
```
❌ SMTP error: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**Solutions:**
1. Update Python certificates: `pip install --upgrade certifi`
2. Try different port (587 for STARTTLS, 465 for SSL)
3. Disable TLS as last resort (not recommended):
   ```yaml
   use_tls: false
   ```

### Configuration Not Found

**Error:**
```
❌ Email sending requires SMTP configuration
```

**Solutions:**
1. Create `.crashlens/smtp.yaml`: `crashlens config smtp-example`
2. Or set environment variables: `export SMTP_SERVER=...`
3. Verify file is in current directory or up to 5 parent directories
4. Check file permissions (must be readable)

### Attachment Too Large

Some email providers limit attachment size (typically 10-25MB):

**Solutions:**
1. Compress HTML file: `gzip guard-12345.html`
2. Use Slack webhook instead: `crashlens slack notify --report-file guard-12345.html`
3. Upload to cloud storage and include link in email body

---

## See Also

- [GUARD.md](./GUARD.md) - Policy enforcement and HTML report generation
- [SLACK_INTEGRATION.md](./SLACK_INTEGRATION.md) - Slack webhook integration
- [CONFIG_PRECEDENCE.md](./CONFIG_PRECEDENCE.md) - Configuration priority rules
- [USER_MANUAL.md](./USER_MANUAL.md) - Complete command reference
