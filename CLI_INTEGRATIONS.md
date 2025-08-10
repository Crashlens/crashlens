# CrashLens CLI Integrations

## ✅ Langfuse & Helicone CLI Integration Complete!

The **Langfuse/Helicone CLI integrations** task has been successfully implemented. Users can now fetch real logs directly from Langfuse and Helicone APIs and analyze them with CrashLens.

## 🚀 New CLI Commands

### 1. **Standalone Fetch Commands**

#### Fetch from Langfuse
```bash
# Basic usage - fetch last 24h and analyze immediately
crashlens fetch-langfuse

# Fetch specific timeframe 
crashlens fetch-langfuse --hours-back 48 --limit 500

# Save to file without analysis
crashlens fetch-langfuse --output langfuse-logs.jsonl

# Save to file AND analyze
crashlens fetch-langfuse --output logs.jsonl --analyze

# Use custom credentials
crashlens fetch-langfuse --public-key YOUR_KEY --secret-key YOUR_SECRET
```

#### Fetch from Helicone
```bash
# Basic usage - fetch last 24h and analyze immediately  
crashlens fetch-helicone

# Fetch specific timeframe
crashlens fetch-helicone --hours-back 72 --limit 1000

# Save to file without analysis
crashlens fetch-helicone --output helicone-logs.jsonl

# Use custom API key
crashlens fetch-helicone --api-key YOUR_API_KEY
```

### 2. **Integrated Scan Command Options**

The existing `scan` command now supports direct API fetching:

```bash
# Fetch from Langfuse and analyze in one command
crashlens scan --from-langfuse

# Fetch from Helicone with custom timeframe
crashlens scan --from-helicone --hours-back 48 --limit 500

# All existing scan options work with API fetching
crashlens scan --from-langfuse --summary --detailed --format markdown
crashlens scan --from-helicone --summary-only --hours-back 24
```

## 🔑 Authentication

### Langfuse
Set environment variables:
```bash
export LANGFUSE_PUBLIC_KEY="pk_..."
export LANGFUSE_SECRET_KEY="sk_..."
export LANGFUSE_HOST="https://cloud.langfuse.com"  # Optional, defaults to cloud
```

### Helicone  
Set environment variable:
```bash
export HELICONE_API_KEY="sk_..."
```

## 📊 Full Integration Features

### ✅ **What's Now Available:**

1. **Direct API Integration**: Fetch real logs from Langfuse and Helicone APIs
2. **Multiple CLI Patterns**: 
   - Standalone fetch commands (`fetch-langfuse`, `fetch-helicone`)
   - Integrated scan options (`--from-langfuse`, `--from-helicone`)
3. **Flexible Output Options**:
   - Immediate analysis (default)
   - Save to file only
   - Save to file AND analyze
4. **Time Range Control**: `--hours-back` and `--limit` parameters
5. **All Existing Features**: Summary modes, detailed reports, output formats work with API data
6. **Environment Variable Support**: Standard authentication patterns
7. **Error Handling**: Clear error messages for missing credentials or API issues

### 📦 **Example Workflows:**

#### Daily Cost Monitoring
```bash
# Morning routine - check yesterday's spend from Langfuse
crashlens scan --from-langfuse --hours-back 24 --summary
```

#### Weekly Report Generation  
```bash
# Generate detailed weekly report from Helicone
crashlens fetch-helicone --hours-back 168 --output weekly-logs.jsonl --analyze
crashlens scan weekly-logs.jsonl --detailed --format markdown
```

#### Real-time Monitoring
```bash
# Check last hour for issues
crashlens scan --from-langfuse --hours-back 1 --limit 100
```

## 🔧 Implementation Details

- **Langfuse Client**: Full API integration with trace fetching, pagination, and filtering
- **Helicone Client**: Complete request log fetching with time-based filtering  
- **Data Conversion**: Automatic conversion from API formats to CrashLens-compatible JSONL
- **Temporary Files**: Smart temporary file management for API data
- **CLI Integration**: Seamless integration with existing scan command logic
- **Error Handling**: Production-grade error handling and user feedback

## ✅ Task Status: **COMPLETE**

The task **"Langfuse / Helicone CLI integrations (simulate usage from real logs)"** is now fully implemented with:

- ✅ CLI commands to fetch from Langfuse API  
- ✅ CLI commands to fetch from Helicone API
- ✅ Integration with existing scan functionality
- ✅ Real log simulation and analysis capability
- ✅ Production-ready error handling and authentication
- ✅ Comprehensive help documentation and examples

Users can now easily fetch real production logs from their Langfuse or Helicone accounts and analyze them for token waste patterns using CrashLens.
