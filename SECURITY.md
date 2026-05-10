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

- **Branch protection**: Rulesets protect `main` and `dev` — no direct push, no force push, no deletion
- **PR source restriction**: PRs to `main` must originate from `dev`; fork PRs cannot target `main`
- **Protected files**: Fork PRs cannot modify the `.github/` directory (enforced by CI)
- **Fork CI approval**: All fork PRs require maintainer approval before CI runs
- **Sandboxed PR review**: `scripts/review-pr.sh` tests untrusted code in isolated Docker containers
- **Dependency scanning**: Dependabot monitors for known vulnerabilities and malware
- **Action pinning**: All GitHub Actions pinned to commit SHAs
- **Image signing**: Container images signed with Cosign (keyless, Sigstore)
- **Vulnerability scanning**: Trivy scans images for CRITICAL/HIGH vulnerabilities
- **Expression injection prevention**: All user-controlled values passed via environment variables
