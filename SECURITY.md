# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| Latest (main branch) | ✅ |
| Older versions | ❌ |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT open a public issue**
2. Use [GitHub Security Advisories](https://github.com/whw23/searxng_http_mcp/security/advisories/new) to report privately
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

You should receive a response within **72 hours**. We will work with you to understand and address the issue before any public disclosure.

## Security Measures

This project implements the following security controls:

- **CI isolation**: Pull request events never execute external code
- **Fork workflow verification**: Fork CI results are only trusted if the workflow file matches upstream
- **Branch protection**: `main` requires passing CI and PR from `dev` only; admin bypass is disabled
- **Expression injection prevention**: All user-controlled values passed via environment variables
- **Protected files**: Fork PRs cannot modify `.github/` directory
- **Dependency scanning**: Dependabot monitors for known vulnerabilities
- **Action pinning**: All GitHub Actions pinned to commit SHAs
