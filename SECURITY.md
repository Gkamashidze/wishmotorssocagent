# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please do NOT open a public GitHub issue.

**Contact:** Report privately via GitHub Security Advisories or directly to the maintainer.

## Response Timeline
- **Acknowledgment:** Within 48 hours
- **Initial assessment:** Within 5 business days
- **Fix or mitigation:** Within 30 days for critical issues

## Supported Versions
| Version | Supported |
|---------|-----------|
| Latest  | ✅ Yes    |

## Security Best Practices for Contributors
- Never commit secrets, API keys, or credentials
- Use parameterized queries — no raw SQL with user input
- Validate all inputs at system boundaries
- Follow the rules in `.claude/rules/security.md`
