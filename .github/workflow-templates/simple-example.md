# Simple Crashlens Workflow Example

Copy this to `.github/workflows/crashlens.yml` in your repository:

```yaml
name: Crashlens Policy Check

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  crashlens:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - run: pip install crashlens
    - run: |
        if find . -name "*.jsonl" -type f | grep -q .; then
          find . -name "*.jsonl" -type f -exec crashlens policy-check {} --policy-template all --fail-on-violations --severity-threshold high \;
        else
          echo "No .jsonl files found. Add your log files and re-run."
        fi
```

That's it! This minimal version:
- ✅ Runs on push/PR to main
- ✅ Sets up Python 3.11  
- ✅ Installs Crashlens from PyPI
- ✅ Runs policy check with all templates
- ✅ Fails CI on high/critical violations
- ✅ Handles missing log files gracefully
