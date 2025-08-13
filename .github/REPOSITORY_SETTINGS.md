# Repository Settings Template
# This file documents the recommended GitHub repository settings for branch protection and compliance

## Branch Protection Rules

### Main Branch Protection (main)
```
Require status checks to pass before merging: ✓
  - Require branches to be up to date before merging: ✓
  - Status checks that are required:
    - ci/lint
    - ci/type-check
    - ci/test
    - ci/integration-test
    - ci/security-scan

Require pull request reviews before merging: ✓
  - Required number of approvers: 2
  - Dismiss stale reviews when new commits are pushed: ✓
  - Require review from code owners: ✓
  - Require approval of the most recent reviewable push: ✓

Require conversation resolution before merging: ✓

Require signed commits: ✓

Require linear history: ✓

Include administrators: ✓

Allow force pushes: ✗

Allow deletions: ✗
```

### Development Branch Protection (develop)
```
Require status checks to pass before merging: ✓
  - Require branches to be up to date before merging: ✓
  - Status checks that are required:
    - ci/lint
    - ci/type-check
    - ci/test

Require pull request reviews before merging: ✓
  - Required number of approvers: 1
  - Dismiss stale reviews when new commits are pushed: ✓
  - Require review from code owners: ✓

Include administrators: ✓

Allow force pushes: ✗

Allow deletions: ✗
```

## Repository Settings

### General
- **Default branch**: main
- **Template repository**: ✗
- **Issues**: ✓
- **Sponsor button**: ✓ (if applicable)
- **Preserve this repository**: ✓
- **Discussions**: ✓
- **Projects**: ✓

### Features
- **Wikis**: ✗
- **Sponsorships**: ✓ (if applicable)
- **Allow forking**: ✓

### Pull Requests
- **Allow merge commits**: ✗
- **Allow squash merging**: ✓
  - Default to pull request title and description
- **Allow rebase merging**: ✓
- **Always suggest updating pull request branches**: ✓
- **Allow auto-merge**: ✓
- **Automatically delete head branches**: ✓

### Merging
- **Default merge method**: Squash and merge

### Pushes
- **Limit pushes that create files larger than**: 100 MB

## Security Settings

### Security & Analysis
- **Dependency graph**: ✓
- **Dependabot alerts**: ✓
- **Dependabot security updates**: ✓
- **Dependabot version updates**: ✓
- **Code scanning alerts**: ✓
- **Secret scanning alerts**: ✓
- **Secret scanning push protection**: ✓

### Deploy Keys
- Use deploy keys for deployment automation (read-only recommended)

### Secrets and Variables
- **Repository secrets**:
  - `PYPI_TOKEN` (for publishing)
  - `SLACK_WEBHOOK_URL` (for notifications)
  - `CODECOV_TOKEN` (for coverage reporting)
- **Environment secrets** (per environment):
  - Production secrets
  - Staging secrets

## Collaboration Settings

### Manage Access
- **Base permissions**: Read
- **Admin team**: @org/maintainers
- **Write team**: @org/contributors
- **Triage team**: @org/triagers

### Moderation
- **Interaction limits**: No restrictions
- **Code review limits**: No restrictions

## Pages Settings (if using GitHub Pages)
- **Source**: Deploy from a branch
- **Branch**: gh-pages / docs
- **Custom domain**: your-domain.com (if applicable)
- **Enforce HTTPS**: ✓

## Environments (for deployments)

### Production
- **Required reviewers**: @org/maintainers
- **Wait timer**: 5 minutes
- **Deployment branches**: main only

### Staging
- **Required reviewers**: @org/contributors
- **Deployment branches**: develop, main

## Webhooks
- **CI/CD webhooks**: Configured for your CI system
- **Slack notifications**: Configured for team alerts
- **Security webhooks**: Configured for security monitoring

---

## Setup Instructions

1. **Repository Settings**: Go to Settings > General and configure as above
2. **Branch Protection**: Go to Settings > Branches and create rules
3. **Security**: Go to Settings > Security & analysis and enable features
4. **Teams**: Create teams and assign permissions
5. **Webhooks**: Configure integrations as needed
6. **Secrets**: Add required secrets for CI/CD

## Compliance Checklist

- [ ] Branch protection rules configured
- [ ] Required status checks enabled
- [ ] Code owners file present (CODEOWNERS)
- [ ] Security features enabled
- [ ] Proper team permissions set
- [ ] Signed commits required
- [ ] Linear history enforced
- [ ] Auto-delete branches enabled
- [ ] Dependabot enabled
- [ ] Secret scanning enabled
- [ ] Issue templates configured
- [ ] PR template configured
- [ ] Contributing guidelines present
- [ ] Security policy present
- [ ] CI/CD pipeline configured
