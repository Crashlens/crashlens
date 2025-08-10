## 📋 Pull Request Description

### What does this PR do?
<!-- Provide a clear and concise description of what this PR accomplishes -->

### Type of Change
<!-- Mark the relevant option with an "x" -->
- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to change)
- [ ] 📚 Documentation update
- [ ] 🔧 Refactoring (no functional changes, no API changes)
- [ ] 🧪 Test updates
- [ ] 🚀 Performance improvement
- [ ] 🔒 Security fix

### Related Issues
<!-- Link to related issues using "Fixes #123" or "Closes #123" -->
- Fixes #
- Related to #

## 🧪 Testing

### Test Coverage
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] All existing tests pass

### Test Results
<!-- Describe what you tested and the results -->
```bash
# Add commands you ran and their output
poetry run pytest
poetry run python -m crashlens scan examples-logs/demo-logs.jsonl
```

## 📊 Checklist

### Code Quality
- [ ] Code follows the project's style guidelines
- [ ] Self-review of code completed
- [ ] Code is commented, particularly in hard-to-understand areas
- [ ] No new linting errors introduced
- [ ] Type hints added where applicable

### Documentation
- [ ] README updated (if applicable)
- [ ] Docstrings added/updated for new functions
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Comments added for complex logic

### Dependencies
- [ ] No new dependencies added (or justified if added)
- [ ] Poetry lock file updated (`poetry lock`)
- [ ] Dependencies are secure and up-to-date

### Compatibility
- [ ] Changes are backward compatible
- [ ] Works on Python 3.10+
- [ ] Tested on multiple platforms (if applicable)

## 🔍 Review Notes

### Areas of Focus
<!-- Highlight specific areas you'd like reviewers to focus on -->

### Screenshots (if applicable)
<!-- Add screenshots for UI changes or CLI output changes -->

### Performance Impact
<!-- Describe any performance implications -->

### Breaking Changes
<!-- List any breaking changes and migration steps -->

## 🚀 Deployment Notes
<!-- Any special deployment considerations -->

---

## For Reviewers

### Review Checklist
- [ ] Code logic is sound and efficient
- [ ] Tests are comprehensive and pass
- [ ] Documentation is clear and complete
- [ ] No security vulnerabilities introduced
- [ ] Follows project conventions and style
- [ ] Branch is up-to-date with main
- [ ] All CI checks are passing

### Questions for Author
<!-- Questions or clarifications needed -->

---

**By submitting this PR, I confirm:**
- [ ] I have read and followed the [Contributing Guidelines](.github/CONTRIBUTING.md)
- [ ] I have tested my changes thoroughly
- [ ] I am willing to address feedback and make necessary changes
- [ ] This PR is ready for review
