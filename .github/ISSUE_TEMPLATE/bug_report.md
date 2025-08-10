---
name: 🐛 Bug Report
about: Create a report to help us improve
title: '[BUG] '
labels: ['bug', 'needs-triage']
assignees: ''
---

## 🐛 Bug Description

### What happened?
<!-- A clear and concise description of what the bug is -->

### Expected Behavior
<!-- A clear and concise description of what you expected to happen -->

### Actual Behavior
<!-- A clear and concise description of what actually happened -->

## 🔍 Reproduction Steps

### Steps to Reproduce
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

### Minimal Reproducible Example
```bash
# Commands that reproduce the issue
poetry run python -m crashlens scan examples/demo-logs.jsonl
```

### Sample Input Data
```json
{
  "trace_id": "example",
  "input": "sample input",
  "output": "sample output"
}
```

## 📊 Environment Information

### CrashLens Version
<!-- Run: python -m crashlens --version -->
```
CrashLens version: 
```

### System Information
- **OS**: [e.g., Windows 11, macOS 13, Ubuntu 22.04]
- **Python Version**: [e.g., 3.11.5]
- **Poetry Version**: [e.g., 1.6.1]
- **Shell**: [e.g., PowerShell, Bash, Zsh]

### Installation Method
- [ ] Poetry (`poetry install`)
- [ ] pip (`pip install crashlens`)
- [ ] Docker
- [ ] Source installation

### Dependencies
<!-- Run: poetry show -->
```
# Paste relevant dependency versions
```

## 📋 Additional Context

### Error Messages
```
# Paste any error messages, stack traces, or logs
```

### Log Files
<!-- Attach relevant log files or paste log excerpts -->

### Screenshots
<!-- If applicable, add screenshots to help explain your problem -->

### Related Issues
<!-- Link to related issues -->

## 🧪 Investigation

### What I've Tried
- [ ] Checked the documentation
- [ ] Searched existing issues
- [ ] Tested with latest version
- [ ] Tested with minimal example

### Potential Root Cause
<!-- If you have any insights about what might be causing this -->

### Workarounds
<!-- Any temporary workarounds you've found -->

---

## For Maintainers

### Triage Checklist
- [ ] Issue is reproducible
- [ ] Labels applied appropriately
- [ ] Severity assessed
- [ ] Assignment determined
- [ ] Milestone set (if applicable)

### Priority Assessment
- [ ] 🔴 Critical (blocks users, security issue)
- [ ] 🟠 High (significant impact, no workaround)
- [ ] 🟡 Medium (moderate impact, workaround exists)
- [ ] 🟢 Low (minor issue, cosmetic)
