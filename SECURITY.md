# Security Policy

The Enterprise AI Workforce project takes security seriously. This document explains how to responsibly report vulnerabilities, what you can expect from us in response, and an overview of the security controls built into the platform.

---

## Supported Versions

Only the latest commit on the `main` branch receives security fixes. We do not back-port patches to older tags or releases.

| Version / Branch | Supported |
|------------------|-----------|
| `main` (latest) | Yes |
| Any tagged release older than `main` | No |
| `develop` and feature branches | No — pre-release, not for production |

If you are running a pinned older version in production, we strongly recommend upgrading to `main` before reporting issues that may already be resolved.

---

## Reporting a Vulnerability

**Please do NOT open a public GitHub Issue for security vulnerabilities.** Public disclosure before a patch is available puts all users at risk.

### Private Disclosure

Send an email to **hussainbold1997@gmail.com** with the subject line:

```
[SECURITY] <brief one-line description>
```

Encrypt your report using our PGP key (available on request) if it contains highly sensitive details.

### What to Include

A useful report helps us reproduce and fix the issue quickly. Please include:

1. **Description** — A clear explanation of the vulnerability, the affected component, and the type of weakness (e.g., SQL injection in the `/ask` endpoint, path traversal in document upload).
2. **Reproduction steps** — A numbered, step-by-step sequence to trigger the vulnerability. Include exact HTTP requests (curl commands or raw request/response pairs) where possible.
3. **Impact assessment** — Who is affected, what data or actions are exposed, and under what conditions (authenticated vs. unauthenticated, specific roles, etc.).
4. **Suggested fix** (optional but appreciated) — If you have ideas about how to remediate the issue, include them. We may or may not follow your suggestion exactly, but it accelerates triage.
5. **Proof of concept** — A script, payload, or screenshot demonstrating the issue. Do not perform destructive actions against systems you do not own.

### Coordinated Disclosure

We follow a coordinated disclosure model:

- We ask that you give us a reasonable amount of time to investigate and patch before making any public disclosure.
- Once a fix is released, we are happy to credit you in the release notes and/or our security acknowledgements unless you prefer to remain anonymous.
- If you discover the vulnerability while participating in a bug bounty programme, follow that programme's disclosure rules.

---

## Response Timeline

| Milestone | Target |
|-----------|--------|
| Acknowledgement of receipt | Within **48 hours** |
| Initial triage and severity assessment | Within **7 days** |
| Patch development and internal testing | Within **30 days** of triage |
| Coordinated public disclosure | After patch is available |

For critical vulnerabilities (CVSS 9.0+) we will expedite the timeline. If we are unable to meet these targets for a specific report we will communicate proactively.

---

## Scope

### In Scope

The following classes of vulnerability are considered in scope for private disclosure:

- **Authentication and authorisation bypass** — JWT forgery, role escalation, session fixation, insecure token handling
- **Injection attacks** — SQL injection, prompt injection into LLM pipelines, command injection, LDAP injection
- **Sensitive data exposure** — Leaking API keys, user credentials, or internal system paths in responses or logs
- **Server-Side Request Forgery (SSRF)** — Forcing the server to make requests to internal or cloud-metadata endpoints
- **Path traversal** — Reading or writing files outside permitted directories
- **Broken access control** — Accessing or modifying another user's data or agents without authorisation
- **Insecure deserialization** — Exploiting pickle or similar deserialisers
- **Dependency vulnerabilities** — Critical CVEs in `requirements.txt` or `package.json` dependencies that have a working exploit applicable to this project

### Out of Scope

The following are explicitly out of scope:

- Rate limiting edge cases that require an impractical number of requests or privileged access to observe
- Social engineering or phishing attacks against maintainers or users
- Vulnerabilities in third-party services (OpenAI, Redis Cloud, Railway, etc.) that are not caused by our configuration
- Self-XSS that requires the attacker to already have full access to the victim's browser session
- Missing HTTP security headers that carry no meaningful exploitable risk in context
- Theoretical vulnerabilities without a working proof of concept
- Issues already reported and awaiting a patch (check existing advisories first)
- Denial-of-service attacks that require significant resources to execute

---

## Security Design Overview

The following controls are part of the platform's security architecture:

### Authentication

- **JWT HS256** tokens are used for all authenticated API access. Tokens carry a short expiry (`ACCESS_TOKEN_EXPIRE_MINUTES` env var, default 30 minutes).
- Tokens are verified on every request by the `get_current_user` dependency; there is no bypass path.
- Refresh tokens are stored server-side (Redis) and can be revoked on logout or suspicious activity.

### Password Storage

- User passwords are hashed with **bcrypt at cost factor 12**. Plaintext passwords are never stored or logged.

### Path Traversal Protection

- All file I/O that accepts user-supplied filenames passes through `_safe_path()`, which resolves the canonical path and asserts it remains within the permitted base directory. Attempts to traverse outside the directory raise a `400 Bad Request` before any filesystem operation occurs.

### Secrets Management

- The `SECRET_KEY` environment variable is **enforced at container start**. If it is absent or set to a known-weak default value, the application refuses to start and exits with a non-zero status code.
- Docker Compose uses the `:?` syntax (`${SECRET_KEY:?SECRET_KEY must be set}`) to enforce the same constraint at the compose layer.
- No credentials, API keys, or secrets are committed to the git history. The `.env` file is listed in `.gitignore` and `.dockerignore`.

### Rate Limiting

- The `/ask` endpoint (LLM inference) is rate-limited per authenticated user to prevent abuse and runaway API costs.

### Dependencies

- Python dependencies are pinned in `requirements.txt`. We periodically run `pip-audit` and Dependabot to catch CVEs in transitive dependencies.
- Node dependencies are locked via `package-lock.json` and scanned by `npm audit` in CI.

### Docker

- The production image runs as a non-root user.
- Build secrets (e.g., pip tokens) are passed via Docker BuildKit secrets, not `ARG` or `ENV` layers, so they do not appear in the image layer history.

---

## Acknowledgements

We thank all researchers and community members who have helped improve the security of this project through responsible disclosure.

---

*This policy was last updated: May 2026.*
