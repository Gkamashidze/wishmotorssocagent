# Security Rules

## Secrets — NEVER in code
- All API keys, passwords, tokens → .env file ONLY
- .env is in .gitignore — NEVER commit it
- .env.example contains placeholders only
- Validate all env vars exist at startup — fail fast if missing

## Input Validation
- Validate ALL user inputs at every system boundary
- Use schema validation (Zod for TS, Pydantic for Python)
- Sanitize everything before rendering (XSS prevention)
- Never eval or exec user-provided content

## SQL / Database
- ALWAYS use parameterized queries or ORM methods
- NEVER concatenate user input into SQL strings
- Database user gets minimum required permissions

## Authentication
- Passwords: bcrypt (cost 12+) or argon2id — NEVER plaintext
- Sessions: cryptographically random, 128-bit minimum
- Session timeout: 30 min inactivity, 24h absolute max
- Rate limit: 5 login attempts per minute, lockout after 10 failures

## OWASP Top 10 — Auto-enforced
- A01 Broken Access Control: check ownership on every resource
- A02 Cryptographic Failures: HTTPS/TLS always, encrypt PII at rest
- A03 Injection: parameterized queries, never dynamic SQL
- A04 Insecure Design: rate limits on all endpoints
- A05 Security Misconfiguration: security headers always
- A06 Vulnerable Components: audit after every install
- A07 Authentication Failures: MFA for sensitive operations
- A08 Data Integrity: verify webhooks, use SRI for CDN scripts
- A09 Logging Failures: log auth events, NEVER log passwords
- A10 SSRF: validate URLs, block internal IP ranges

## Security Headers (mandatory on every response)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Strict-Transport-Security: max-age=31536000; includeSubDomains
- Content-Security-Policy: default-src 'self'
- Referrer-Policy: strict-origin-when-cross-origin
- Use helmet (Node.js) or flask-talisman (Python)

## File Uploads
- Validate by magic bytes, not extension
- Max size: 5MB (unless explicit approval for larger)
- Store outside web root, serve via signed URLs
- Generate random filenames — never use original

## Incident Response
If a security issue is detected:
1. STOP current task
2. Alert user in plain Georgian
3. Explain the risk simply
4. Provide specific fix steps
5. Wait for user acknowledgment before proceeding
