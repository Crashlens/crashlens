# Contributing to CrashLens

Thank you for your interest in contributing to CrashLens! This document outlines our contribution process and guidelines.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/crashlens.git
   cd crashlens
   ```
3. **Set up development environment**:
   ```bash
   # Install Poetry if you haven't already
   curl -sSL https://install.python-poetry.org | python3 -
   
   # Install dependencies
   poetry install
   
   # Activate virtual environment
   poetry shell
   ```

## 🔧 Development Workflow

### Branch Protection Rules
Our `main` branch is protected with the following rules:
- ✅ **Pull requests required** - No direct pushes to `main`
- ✅ **At least 1 approval required** - PRs must be reviewed
- ✅ **Up-to-date branch required** - Must be current with `main`
- ✅ **Conversation resolution required** - All review comments must be resolved

### Creating a Pull Request

1. **Create a feature branch** from `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards:
   - Write clear, descriptive commit messages
   - Add tests for new functionality
   - Update documentation if needed
   - Follow existing code style and patterns

3. **Test your changes**:
   ```bash
   # Run tests
   poetry run pytest
   
   # Run linting
   poetry run black crashlens/
   poetry run flake8 crashlens/
   
   # Type checking
   poetry run mypy crashlens/
   ```

4. **Commit and push**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request**:
   - Go to GitHub and create a PR from your branch to `main`
   - Fill out the PR template (if provided)
   - Request review from maintainers
   - Address any feedback

## 📝 Commit Message Guidelines

We follow conventional commits format:

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, missing semi-colons, etc)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

**Examples:**
```
feat: add retry loop detector with configurable thresholds
fix: handle missing timestamp fields gracefully
docs: update README with new CLI options
```

## 🧪 Testing

- **Write tests** for new features and bug fixes
- **Run the full test suite** before submitting PRs
- **Ensure tests pass** in CI/CD pipeline
- Tests are located in the `tests/` directory

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_detectors.py

# Run with coverage
poetry run pytest --cov=crashlens
```

## 📊 Code Quality

We maintain high code quality standards:

### Linting
```bash
# Format code
poetry run black crashlens/

# Check code style
poetry run flake8 crashlens/
```

### Type Checking
```bash
# Run mypy
poetry run mypy crashlens/
```

### Pre-commit Hooks (Recommended)
```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install
```

## 🔒 Security & Signed Commits

### GPG Signing (Optional but Recommended)
To enable signed commits:

1. **Generate a GPG key**:
   ```bash
   gpg --full-generate-key
   ```

2. **Add to GitHub**: Copy your public key and add it to your GitHub account

3. **Configure Git**:
   ```bash
   git config --global user.signingkey YOUR_KEY_ID
   git config --global commit.gpgsign true
   ```

4. **Sign commits**:
   ```bash
   git commit -S -m "your commit message"
   ```

## 🎯 Types of Contributions

### 🐛 Bug Reports
- Use GitHub Issues with the "bug" label
- Include steps to reproduce
- Provide system information (OS, Python version, etc.)
- Include relevant log outputs

### 💡 Feature Requests
- Use GitHub Issues with the "enhancement" label
- Describe the use case and expected behavior
- Consider if it fits CrashLens's core mission

### 🔍 New Detectors
- Follow existing detector patterns in `crashlens/detectors/`
- Include comprehensive tests
- Document the detection logic
- Add configuration options to `pricing.yaml`

### 📚 Documentation
- Update relevant sections for code changes
- Improve clarity and examples
- Fix typos and formatting issues

## 🏗️ Project Structure

```
crashlens/
├── crashlens/           # Main package
│   ├── cli.py          # CLI interface
│   ├── detectors/      # Detection algorithms
│   ├── parsers/        # Log parsers
│   ├── reporters/      # Output formatters
│   └── utils/          # Utility functions
├── tests/              # Test suite
├── examples-logs/      # Sample data
├── docs/               # Documentation
└── .github/           # GitHub workflows & templates
```

## 📋 Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows project style guidelines
- [ ] Tests pass locally (`poetry run pytest`)
- [ ] New functionality includes tests
- [ ] Documentation is updated if needed
- [ ] Commit messages follow conventional format
- [ ] Branch is up-to-date with `main`
- [ ] No merge conflicts exist
- [ ] PR description clearly explains changes

## 🤝 Code Review Process

1. **Automated Checks**: CI must pass (tests, linting, type checking)
2. **Peer Review**: At least one maintainer approval required
3. **Conversation Resolution**: All review comments must be addressed
4. **Final Review**: Last push requires re-approval
5. **Merge**: Squash and merge (preferred) or merge commit

## 🙋‍♂️ Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and ideas
- **Code Review**: Tag maintainers in PRs for faster review

## 📜 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help newcomers learn and contribute

## 🚀 Recognition

Contributors are recognized in:
- `CHANGELOG.md` for their contributions
- GitHub contributors list
- Release announcements for significant contributions

Thank you for contributing to CrashLens and helping developers optimize their AI costs! 🎉
