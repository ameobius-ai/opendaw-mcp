# Security Policy

## Reporting a Vulnerability

If you discover a security issue in openDAW MCP, please **do not** open a public issue.

Instead, email: **security@ameobius.dev** (or use GitHub's private vulnerability reporting).

Include:
- Description of the issue
- Steps to reproduce
- Potential impact

You will receive a response within 48 hours.

## Automated Security Scanning

This project uses automated security scanning to detect vulnerabilities in dependencies:

### Python Dependencies
- **Tool**: [pip-audit](https://github.com/pypa/pip-audit)
- **Frequency**: Every push to main, every pull request, and weekly (Mondays at 9:00 UTC)
- **Workflow**: `.github/workflows/security.yml`
- **Reports**: Available as GitHub Actions artifacts for 30 days

### NPM Dependencies
- **Tool**: npm audit
- **Scope**: `tests/e2e/test_host` (Playwright test environment)
- **Frequency**: Same as Python dependencies

### Dependency Review
- **Tool**: [dependency-review-action](https://github.com/actions/dependency-review-action)
- **Behavior**: Fails PRs that introduce high-severity vulnerabilities
- **Denied Licenses**: GPL-3.0, AGPL-3.0 (to maintain Apache-2.0 compatibility)

### Dependabot
- **Configuration**: `.github/dependabot.yml`
- **Scope**: GitHub Actions, NPM, and Python dependencies
- **Frequency**: Weekly updates
- **Auto-merge**: Disabled (manual review required)

## Local Security Audit

To run security audits locally:

### Python Dependencies

    # Install pip-audit
    pip install pip-audit
    
    # Run audit
    pip-audit --requirement requirements.txt
    
    # Generate JSON report
    pip-audit --requirement requirements.txt --format json --output audit-report.json

### NPM Dependencies

    cd tests/e2e/test_host
    npm audit
    npm audit --audit-level=high

## Scope

This policy covers the MCP server (`server.py`), the Playwright bridge, and the headless Chromium integration.

## Architecture Notes

- The server launches a **headless Chromium** instance with openDAW loaded from a local Vite dev server.
- `evaluate_raw` and `evaluate` tools execute arbitrary JavaScript in the DAW's V8 context — these are powerful debugging tools intended for development use only.
- No credentials, API keys, or personal data are stored or transmitted by the server itself.
- Environment variables (`OPENDAW_HOST_DIR`, `OPENDAW_URL`, etc.) are read at startup and not persisted.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Security Best Practices

When using openDAW MCP:

1. **Environment Isolation**: Run in a sandboxed environment (Docker recommended)
2. **Network Security**: The MCP server should not be exposed to the public internet
3. **Access Control**: Restrict access to trusted clients only
4. **Regular Updates**: Keep dependencies up to date (Dependabot will create PRs automatically)
5. **Review evaluate_raw**: Be cautious with arbitrary JavaScript execution in production
