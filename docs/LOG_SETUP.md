# 📁 CrashLens Log Setup Guide

CrashLens analyzes your LLM usage logs to detect token waste, retry loops, and cost optimization opportunities. This guide explains how to set up proper logging for analysis.

## 🎯 Quick Setup

**Place your JSONL log files in one of these locations:**
- `.llm_logs/` (recommended)
- `logs/`
- Any directory with `*.jsonl` files

## 📋 Required Log Format

Each line in your JSONL file should contain LLM API call data:

```json
{
  "trace_id": "abc123",
  "model": "gpt-4", 
  "usage": {"total_tokens": 1500, "prompt_tokens": 100, "completion_tokens": 1400},
  "cost": 0.03,
  "timestamp": "2025-01-15T10:30:00Z",
  "status": "success"
}
```

### Required Fields
- `model`: Model name (e.g., "gpt-4", "gpt-3.5-turbo", "claude-3")
- `usage.total_tokens`: Total tokens used in the request

### Optional But Recommended Fields
- `cost` or `totalCost`: Cost of the API call in USD
- `trace_id`: Unique identifier for the request
- `timestamp` or `startTime`/`endTime`: When the request occurred
- `status` or `level`: Success/error status
- `usage.prompt_tokens`, `usage.completion_tokens`: Breakdown of token usage

## 🔧 Platform-Specific Setup

### LangFuse Integration

**Export from LangFuse Dashboard:**
1. Go to your LangFuse project dashboard
2. Navigate to "Traces" section
3. Export traces as JSONL format
4. Save to `.llm_logs/langfuse-traces.jsonl`

**Using LangFuse API:**
```bash
mkdir -p .llm_logs
curl -X GET "https://cloud.langfuse.com/api/public/traces" \
  -H "Authorization: Bearer YOUR_LANGFUSE_SECRET_KEY" \
  -H "Content-Type: application/json" \
  > .llm_logs/langfuse-traces.jsonl
```

**Using Python SDK:**
```python
from langfuse import Langfuse
import json

langfuse = Langfuse(
    secret_key="your-secret-key",
    public_key="your-public-key"
)

# Get traces and save to log file
traces = langfuse.get_traces(limit=1000)
with open('.llm_logs/langfuse-traces.jsonl', 'w') as f:
    for trace in traces.data:
        f.write(json.dumps(trace.dict()) + '\n')
```

### OpenAI Direct Integration

**Manual Logging:**
```python
import json
import os
from datetime import datetime
from openai import OpenAI

client = OpenAI()

def log_openai_call(response, model, prompt_tokens):
    """Log OpenAI API call to .llm_logs/"""
    os.makedirs('.llm_logs', exist_ok=True)
    
    log_entry = {
        "trace_id": f"openai_{int(datetime.now().timestamp())}",
        "model": model,
        "usage": {
            "total_tokens": response.usage.total_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens
        },
        "cost": calculate_cost(model, response.usage.total_tokens),
        "timestamp": datetime.utcnow().isoformat(),
        "status": "success"
    }
    
    with open('.llm_logs/openai_calls.jsonl', 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

def calculate_cost(model, total_tokens):
    """Simple cost calculation - adjust rates as needed"""
    rates = {
        "gpt-4": 0.00003,  # $0.03 per 1K tokens
        "gpt-3.5-turbo": 0.000001  # $0.001 per 1K tokens
    }
    return rates.get(model, 0) * total_tokens

# Example usage
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
log_openai_call(response, "gpt-4", 10)
```

### LangChain Integration

**Using LangChain Callbacks:**
```python
import json
from datetime import datetime
from langchain.callbacks.base import BaseCallbackHandler

class CrashLensLogHandler(BaseCallbackHandler):
    def __init__(self, log_file='.llm_logs/langchain_calls.jsonl'):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    def on_llm_end(self, response, **kwargs):
        log_entry = {
            "trace_id": kwargs.get('run_id', str(uuid.uuid4())),
            "model": kwargs.get('invocation_params', {}).get('model_name', 'unknown'),
            "usage": {
                "total_tokens": response.llm_output.get('token_usage', {}).get('total_tokens', 0)
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": "success"
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

# Use in your LangChain calls
from langchain.llms import OpenAI

llm = OpenAI(callbacks=[CrashLensLogHandler()])
result = llm("What is the capital of France?")
```

### Custom/Generic Logging

**Wrapper Function Approach:**
```python
import json
import functools
from datetime import datetime

def crashlens_log(model_name, log_file='.llm_logs/custom_calls.jsonl'):
    """Decorator to log any LLM API call"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            
            try:
                result = func(*args, **kwargs)
                status = "success"
            except Exception as e:
                result = None
                status = "error"
                raise
            finally:
                # Log the call
                log_entry = {
                    "trace_id": f"custom_{int(start_time.timestamp())}",
                    "model": model_name,
                    "timestamp": start_time.isoformat(),
                    "status": status,
                    "usage": getattr(result, 'usage', {}).get('total_tokens', 0) if result else 0
                }
                
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                with open(log_file, 'a') as f:
                    f.write(json.dumps(log_entry) + '\n')
            
            return result
        return wrapper
    return decorator

# Usage
@crashlens_log("gpt-4")
def my_llm_call():
    # Your LLM API call here
    return client.chat.completions.create(...)
```

## 📊 Testing Your Setup

**Generate Test Data:**
```bash
# Create sample log files for testing
crashlens --simulate --source local --count 100 > .llm_logs/test-data.jsonl
```

**Validate Log Format:**
```bash
# Check if your logs are properly formatted
crashlens policy-check .llm_logs/*.jsonl --policy-template retry-loop-prevention --dry-run
```

**Quick Analysis:**
```bash
# Run a quick analysis to verify everything works
crashlens policy-check .llm_logs/*.jsonl --policy-template all --severity-threshold medium
```

## 🔍 Common Log Locations

**Different frameworks store logs in different places:**

| Framework/Service | Common Log Location | Log Format |
|-------------------|-------------------|------------|
| LangFuse | Dashboard export | Native JSONL |
| LangChain | Custom callbacks | Custom JSONL |
| OpenAI Direct | Manual logging | Custom JSONL |
| LiteLLM | Built-in logging | Standard JSONL |
| Helicone | API export | Native JSONL |
| Custom Apps | `.llm_logs/` or `logs/` | Custom JSONL |

## ❌ Troubleshooting

**No logs found:**
```bash
# Check if logs exist
ls -la .llm_logs/
ls -la logs/

# If empty, generate test data
crashlens --simulate --count 50 > .llm_logs/demo.jsonl
```

**Invalid log format:**
```bash
# Check first few lines of your logs
head -5 .llm_logs/*.jsonl

# Each line should be valid JSON
jq '.' .llm_logs/*.jsonl | head -10
```

**Missing required fields:**
```bash
# Check if logs have required fields
jq '.model, .usage.total_tokens' .llm_logs/*.jsonl | head -10
```

## 📋 Best Practices

1. **Use consistent log locations** - Stick to `.llm_logs/` for all projects
2. **Include cost data** - Essential for cost optimization analysis
3. **Log all API calls** - Don't filter out errors or retries
4. **Use unique trace IDs** - Helps with detailed analysis
5. **Include timestamps** - Useful for time-based analysis
6. **Rotate log files** - Keep file sizes manageable (<100MB per file)

## 🔗 Integration Examples

See the `examples/` directory for complete integration examples:
- `examples/langfuse-ci-contracts/` - LangFuse integration
- `examples/cost-policy-check/` - Cost monitoring setup
- `examples/ci-workflows/` - GitHub Actions integration

---

*For more help, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or open an issue on GitHub.*
