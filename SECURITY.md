# Security Policy

## Supported Versions

We actively support the following versions of CrashLens with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | ✅ Yes             |
| 0.x.x   | ⚠️ Critical fixes only |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue in CrashLens, please follow these steps:

### 🔒 Private Disclosure Process

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please:

1. **Email us directly** at: [your-security-email@domain.com]
2. **Include the following information**:
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact assessment
   - Any suggested fixes (if you have them)
   - Your contact information for follow-up

### 📋 What to Include

When reporting a security vulnerability, please provide:

- **CrashLens version** affected
- **Operating system** and Python version
- **Detailed description** of the vulnerability
- **Proof of concept** or steps to reproduce
- **Potential impact** (data exposure, code execution, etc.)
- **Suggested mitigation** (if any)

### ⏰ Response Timeline

We are committed to responding to security reports promptly:

- **24 hours**: Initial acknowledgment of your report
- **72 hours**: Initial assessment and severity classification
- **7 days**: Detailed response with our action plan
- **30 days**: Resolution timeline (may vary based on complexity)

### 🏆 Security Researcher Recognition

We believe in recognizing security researchers who help keep CrashLens secure:

- **Acknowledgment**: With your permission, we'll acknowledge your contribution in our security advisories
- **Credits**: Listed in our Hall of Fame for responsible disclosure
- **Collaboration**: We may invite you to help verify our fixes

## 🛡️ Security Best Practices

When using CrashLens:

### For Users
- **Keep updated**: Always use the latest version
- **Secure logs**: Ensure your log files don't contain sensitive data
- **Access control**: Limit who can access CrashLens reports
- **Environment isolation**: Run in secure, isolated environments

### For Contributors
- **Code review**: All code changes require review
- **Dependencies**: Keep dependencies updated and secure
- **Secrets**: Never commit API keys, tokens, or passwords
- **Input validation**: Validate all user inputs and file contents

## 🔍 Security Features

CrashLens includes several security features:

- **PII Scrubbing**: Automatic removal of personally identifiable information
- **Local Processing**: All analysis runs locally - no data leaves your system
- **Input Validation**: Robust parsing and validation of log files
- **Safe Defaults**: Secure default configurations

## 🚨 Known Security Considerations

- **Log File Contents**: CrashLens processes log files that may contain sensitive information
- **File System Access**: CrashLens reads files from the local file system
- **Output Files**: Generated reports may contain traces and patterns from your data

## 📊 Vulnerability Disclosure Policy

Our vulnerability disclosure follows these principles:

1. **Coordinated Disclosure**: We work with reporters to ensure responsible timing
2. **Transparency**: We publish security advisories for confirmed vulnerabilities
3. **User Protection**: We prioritize user safety over public disclosure timelines
4. **Learning**: We use incidents to improve our security practices

## 🔗 Related Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Security Best Practices](https://python-security.readthedocs.io/)
- [GitHub Security Advisories](https://docs.github.com/en/code-security/security-advisories)

## 📞 Contact Information

For security-related questions or concerns:

- **Security Email**: [your-security-email@domain.com]
- **GPG Key**: [Link to public GPG key if available]
- **Response Time**: We aim to respond within 24 hours

## 🔄 Policy Updates

This security policy may be updated periodically. Please check back regularly for the latest information.

Last updated: August 10, 2025
