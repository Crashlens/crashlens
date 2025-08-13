## CrashLens CI Workflows

Active workflows that are part of the CrashLens project itself live here (release, schema checks, publishing, etc.).

Sample (non-project) workflows have been moved to:

`examples/ci-workflows/`

There you will find:

- `crashlens-analysis.yml.example` – Comprehensive scan (policies, optional cost/perf hooks)  
- `crashlens-starter.yml.example` – Minimal, fast starter

Copy one of those into *your* repository at `.github/workflows/*.yml`, rename it (remove the `.example` suffix), then tailor:

```yaml
env:
  CRASHLENS_TEMPLATES: "retry-loop-prevention,model-overkill-detection"
  CRASHLENS_SEVERITY: "high"
  CRASHLENS_FAIL_ON_VIOLATIONS: "false"   # set true to break CI
```

Quick copy commands (run inside your repo after adding CrashLens as a dependency):

```bash
curl -o .github/workflows/crashlens.yml \
  https://raw.githubusercontent.com/Crashlens/crashlens/HEAD/examples/ci-workflows/crashlens-starter.yml.example
```

or for the comprehensive one:

```bash
curl -o .github/workflows/crashlens-analysis.yml \
  https://raw.githubusercontent.com/Crashlens/crashlens/HEAD/examples/ci-workflows/crashlens-analysis.yml.example
```

Then adjust triggers (push / pull_request / schedule) and thresholds to match your governance model.

If you need help customizing, open an issue.
3. **Artifacts Download** - Detailed reports available for 30 days (comprehensive) or 7 days (starter)

## Example Repository Structure

```
your-repository/
├── .github/
│   └── workflows/
│       └── crashlens-analysis.yml
├── .llm_logs/                    # Your LLM logs (auto-detected)
│   ├── trace-2024-01-01.jsonl
│   └── trace-2024-01-02.jsonl
├── logs/                         # Alternative log location
│   └── application.jsonl
├── src/                          # Your application code
└── README.md
```

## Troubleshooting

### Common Issues

1. **No logs found**
   ```
   Solution: Ensure your logs are in .llm_logs/ or logs/ directory, 
   or modify the workflow to point to your log location.
   ```

2. **Workflow fails with permission error**
   ```
   Solution: Ensure your repository has GitHub Actions enabled and 
   the workflow has appropriate permissions.
   ```

3. **Cost analysis shows zero**
   ```
   Solution: Ensure your log files contain cost information in the 
   'totalCost' field, or customize the cost extraction logic.
   ```

4. **Security scan fails**
   ```
   Solution: The security scan is set to continue-on-error by default. 
   Check the artifacts for detailed security findings.
   ```

### Getting Help

If you encounter issues:
1. Check the workflow run logs for detailed error messages
2. Review the artifacts for analysis results
3. Open an issue in the CrashLens repository
4. Join our community discussions

## Advanced Customization

### Custom Policy Files
To use your own policy files instead of templates:

```yaml
- name: Run Custom Policy Check
  run: |
    crashlens policy-check logs/*.jsonl \
      --policy-file .crashlens/custom-policy.yaml \
      --severity-threshold high
```

### Multiple Environment Analysis
To analyze different environments separately:

```yaml
- name: Analyze Production Logs
  run: |
    crashlens policy-check logs/production/*.jsonl \
      --policy-template all \
      --severity-threshold critical > prod-analysis.md

- name: Analyze Development Logs  
  run: |
    crashlens policy-check logs/development/*.jsonl \
      --policy-template all \
      --severity-threshold medium > dev-analysis.md
```

### Slack Integration
To send results to Slack, add your webhook URL as a repository secret:

```yaml
- name: Send to Slack
  if: always()
  run: |
    crashlens policy-check logs/*.jsonl \
      --format slack \
      --slack-webhook ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

*For more information, visit the [CrashLens documentation](https://github.com/Crashlens/crashlens) or check out our [examples directory](../examples/).*
