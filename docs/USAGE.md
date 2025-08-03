# 📚 Usage Guide for Langfuse Schema Validation

This guide provides detailed instructions for using the Langfuse schema validation template repository.

## 🎯 Overview

The schema validation system automatically checks your Langfuse logs against predefined contracts to ensure:
- **Data Integrity**: Required fields are present
- **Type Safety**: Fields have correct data types
- **Schema Compliance**: Logs conform to expected structure
- **Future Compatibility**: Early detection of schema changes

## 🚀 Getting Started

### Prerequisites

- GitHub account
- Langfuse logs in JSON/JSONL format
- Basic understanding of GitHub Actions

### Setup Process

1. **Fork the Template Repository**
   ```bash
   # Visit: https://github.com/your-username/langfuse-schema-template
   # Click "Fork" button
   ```

2. **Clone Your Fork**
   ```bash
   git clone https://github.com/your-username/your-fork-name.git
   cd your-fork-name
   ```

3. **Add Your Log Files**
   ```bash
   # Replace sample logs with your data
   cp /path/to/your/langfuse-logs.jsonl logs/langfuse-latest.jsonl
   
   # Commit changes
   git add logs/langfuse-latest.jsonl
   git commit -m "Add Langfuse logs for validation"
   git push origin main
   ```

4. **Enable GitHub Actions**
   - Navigate to your repository's **Actions** tab
   - Click **"I understand my workflows, go ahead and enable them"**
   - The first validation will run automatically

## 🔧 Configuration

### Environment Variables

Configure validation behavior using repository variables:

#### Setting Variables
1. Go to **Settings → Secrets and variables → Actions**
2. Click **Variables** tab
3. Click **New repository variable**

#### Available Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `LOG_PATH` | Path to log file | `logs/langfuse-latest.jsonl` | `data/prod-logs.jsonl` |
| `SCHEMA_VERSION` | Schema version | `langfuse-v1` | `langfuse-v2` |

### Workflow Customization

Edit `.github/workflows/langfuse-schema-check.yml` to customize:

#### Multiple Log Files
```yaml
strategy:
  matrix:
    log-file:
      - logs/production.jsonl
      - logs/staging.jsonl
      - logs/development.jsonl
```

#### Custom Validation Steps
```yaml
- name: Custom Validation
  run: |
    echo "Running custom checks..."
    python scripts/validate-business-logic.py
```

#### Different Python Versions
```yaml
strategy:
  matrix:
    python-version: ['3.9', '3.10', '3.11', '3.12']
```

## 🧪 Manual Testing

### Local Validation

Test schema validation locally before pushing:

```bash
# Install CrashLens
pip install crashlens

# Validate your logs
crashlens scan logs/langfuse-latest.jsonl --log-format langfuse-v1 --verbose

# Test with different schema versions
crashlens scan logs/langfuse-latest.jsonl --log-format langfuse-v2
```

### Manual Workflow Dispatch

Trigger validation with custom parameters:

1. **Navigate to Actions**
   - Go to your repository
   - Click **Actions** tab
   - Select **Langfuse Schema Validation**

2. **Run Workflow**
   - Click **Run workflow** dropdown
   - Specify custom parameters:
     - **Log path**: Custom file path
     - **Schema version**: Specific version to test
   - Click **Run workflow**

## 📊 Understanding Results

### Success Indicators ✅

```
✅ SUCCESS: Schema validation passed for langfuse-v1
🎉 All Langfuse log entries conform to the schema contract
📊 No contract violations detected
```

**What this means:**
- All logs have required fields
- Field types are correct
- Schema contract is satisfied

### Failure Indicators ❌

```
❌ FAILURE: Schema validation failed for langfuse-v1
🚨 Contract violations detected in Langfuse logs
💡 Check the error messages above for details
```

**Common failure reasons:**
- Missing required fields (e.g., `traceId`)
- Incorrect field types
- Malformed JSON structure
- Empty or corrupted log files

### Workflow Status

| Badge | Status | Action Required |
|-------|--------|-----------------|
| ![Success](https://img.shields.io/badge/build-passing-brightgreen) | All validations passed | None |
| ![Failed](https://img.shields.io/badge/build-failing-red) | Contract violations detected | Fix log format |
| ![Pending](https://img.shields.io/badge/build-pending-yellow) | Validation in progress | Wait for completion |

## 🔍 Log Format Requirements

### Required Structure

**Single Log Entry (JSON)**:
```json
{
  "traceId": "trace_12345",
  "model": "gpt-4",
  "prompt_tokens": 150,
  "completion_tokens": 75
}
```

**Multiple Entries (JSONL)**:
```jsonl
{"traceId": "trace_1", "model": "gpt-4"}
{"traceId": "trace_2", "model": "gpt-3.5-turbo"}
{"traceId": "trace_3", "model": "claude-3"}
```

### Field Specifications

#### langfuse-v1 Schema

**Required Fields:**
- `traceId` (string): Unique trace identifier

**Optional Fields:**
- `model` (string): LLM model name
- `prompt_tokens` (integer): Input token count
- `completion_tokens` (integer): Output token count
- `cost` (number): API call cost
- `timestamp` (string): ISO 8601 timestamp
- `userId` (string): User identifier
- `input` (string): Input prompt
- `output` (string): Generated response
- `metadata` (object): Additional data

### Data Type Validation

| Field | Type | Validation |
|-------|------|------------|
| `traceId` | string | Non-empty, unique |
| `model` | string | Valid model name |
| `prompt_tokens` | integer | >= 0 |
| `completion_tokens` | integer | >= 0 |
| `cost` | number | >= 0.0 |
| `timestamp` | string | ISO 8601 format |

## 🛠️ Advanced Configuration

### Multi-Environment Setup

**Production Environment:**
```yaml
# .github/workflows/prod-validation.yml
env:
  LOG_PATH: 'logs/production/langfuse.jsonl'
  SCHEMA_VERSION: 'langfuse-v1'
```

**Staging Environment:**
```yaml
# .github/workflows/staging-validation.yml
env:
  LOG_PATH: 'logs/staging/langfuse.jsonl'
  SCHEMA_VERSION: 'langfuse-v2'
```

### Conditional Validation

Run validation only on specific conditions:

```yaml
# Only validate on main branch
if: github.ref == 'refs/heads/main'

# Only validate if log files changed
if: contains(github.event.head_commit.modified, 'logs/')

# Skip validation in drafts
if: github.event.pull_request.draft == false
```

### Custom Notification

Add Slack/Teams notifications:

```yaml
- name: Notify on Failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: "Langfuse schema validation failed!"
```

## 📈 Monitoring & Maintenance

### Regular Tasks

1. **Update Log Files** (Daily/Weekly)
   ```bash
   # Automated log collection
   curl -o logs/langfuse-latest.jsonl "https://your-api.com/logs/latest"
   ```

2. **Monitor Schema Changes** (Monthly)
   - Check Langfuse release notes
   - Test new schema versions
   - Update contracts as needed

3. **Review Validation History** (Monthly)
   - Check Actions tab for trends
   - Identify recurring issues
   - Optimize log collection

### Performance Optimization

**For Large Log Files:**
```yaml
# Process logs in chunks
- name: Split Large Logs
  run: |
    split -l 1000 logs/large-file.jsonl logs/chunk-
    for file in logs/chunk-*; do
      crashlens scan "$file" --log-format langfuse-v1
    done
```

**Caching Dependencies:**
```yaml
- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

## 🚨 Troubleshooting Guide

### Common Issues

#### Issue: "No such file or directory"
```bash
# Check file existence
ls -la logs/
# Verify file permissions
chmod 644 logs/langfuse-latest.jsonl
```

#### Issue: "Invalid JSON format"
```bash
# Validate JSON syntax
python -m json.tool logs/langfuse-latest.jsonl
# Check for common issues
grep -n "}" logs/langfuse-latest.jsonl | tail -5
```

#### Issue: "Schema contract violation"
```bash
# Identify missing fields
jq '.[] | keys' logs/langfuse-latest.jsonl | sort | uniq
# Check field types
jq '.[] | .traceId | type' logs/langfuse-latest.jsonl
```

### Debug Mode

Enable detailed logging:

```yaml
- name: Debug Validation
  run: |
    crashlens scan logs/langfuse-latest.jsonl \
      --log-format langfuse-v1 \
      --verbose \
      --debug
```

### Support Resources

1. **CrashLens Issues**: [GitHub Issues](https://github.com/crashlens/crashlens/issues)
2. **Langfuse Community**: [Discord/Slack channels]
3. **Template Issues**: [Template Repository Issues]

## 📚 Best Practices

### Log Management
- Keep log files under 100MB for faster processing
- Use JSONL format for streaming logs
- Implement log rotation for large datasets
- Add timestamps for chronological ordering

### Security
- Avoid committing sensitive data in logs
- Use secrets for API keys and tokens
- Implement PII scrubbing before validation
- Restrict repository access appropriately

### Performance
- Use matrix strategies for parallel validation
- Cache dependencies between runs
- Process logs in chunks for large files
- Optimize workflow triggers

This usage guide should help you effectively implement and maintain Langfuse schema validation in your projects. For additional help, refer to the troubleshooting section or open an issue in the repository.
