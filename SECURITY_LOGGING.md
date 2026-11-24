# EduAtlas Application Logging Security Policy

## 1. Purpose & Guiding Principles

This Logging Security Policy defines strict rules and requirements for diagnostic, audit, and operational logging across the **EduAtlas / ScholarPilot AI** platform.

Under zero-trust application principles, log files, monitoring streams, and third-party observability aggregators must **never** contain sensitive user data, authentication credentials, or cryptographic keys.

---

## 2. Forbidden Data (NEVER LOG)

The following categories of data are classified as **Strictly Prohibited** from all log levels (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`):

1. **Passwords & Passphrases:**
   - Plaintext passwords, temporary PINs, OTP codes, or reset codes.
2. **Tokens & Keys:**
   - JWT session tokens, refresh tokens, CSRF tokens, API keys (Gemini, Telegram, Resend), and reCAPTCHA secret keys.
3. **Cron & Webhook Secrets:**
   - `CRON_SECRET`, webhook signing secrets, or HMAC validation signatures.
4. **Authorization Headers:**
   - `Authorization: Bearer <token>`, `Proxy-Authorization`, or basic auth credentials.
5. **Cookies & Session Identifiers:**
   - `session_token`, `minha_token`, `remember_me`, or custom session cookies.
6. **Database Connection Strings:**
   - `DATABASE_URL` or PostgreSQL credentials containing database passwords, hostnames with embedded auth, or internal connection parameters.
7. **Personally Identifiable & Protected User Data (PII):**
   - User financial details, uploaded student ID documents, or full national identification numbers.

---

## 3. Allowed & Required Data (SAFE TO LOG)

When recording security events, authentication attempts, errors, or operational metrics, logging must capture structured context without leaking secrets:

1. **Event Type:**
   - Descriptive identifier of the action (e.g. `user_login_success`, `user_login_failed`, `cron_scan_triggered`, `rate_limit_exceeded`, `token_revoked`).
2. **User Identifier (When Available):**
   - Clean email, hashed username, or user ID (e.g. `user:student@example.com` or `@username`).
3. **Timestamp:**
   - Standard ISO 8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SSZ`).
4. **Correlation / Request ID:**
   - Per-request trace identifier (e.g. `X-Request-ID`).
5. **Request Source:**
   - Client IP (after anti-spoofing verification), user agent, HTTP method, and normalized URL path.
6. **Execution Outcome:**
   - Status code (`200`, `401`, `403`, `429`, `500`), duration in milliseconds, and count of processed records.

---

## 4. Secret Sanitization Helper & Logging Filter

### Helper: `mask_secret(secret)`
Any secret that must be referenced for debugging or telemetry must pass through the platform's `mask_secret` utility located in `services/security_utils.py`:

```python
from services.security_utils import mask_secret

# Example:
# Input:  'abcd1234efgh5678wxyz'
# Output: 'abcd********wxyz'
masked = mask_secret(provided_key)
```

### Logging Filter: `SensitiveDataFilter`
The platform deploys an automated `SensitiveDataFilter` logging filter attached to root and application loggers. The filter automatically intercepts and sanitizes:
- `Bearer <token>` -> `Bearer abcd********wxyz`
- `X-Cron-Secret: <secret>` -> `X-Cron-Secret: abcd********wxyz`
- `password="<value>"` -> `password="abcd********wxyz"`
- `postgres://user:<password>@host/db` -> `postgres://user:********@host/db`

---

## 5. Standard Logging Code Examples

### A. Authentication & Cron Verification
```python
# BAD (Risky - Plaintext secret leak):
logger.debug(f"Cron secret received: {cron_header}")

# GOOD (Sanitized and compliant):
logger.debug("Cron authentication attempt received")
logger.info(f"Cron authentication verified successfully for caller: {client_ip}")
```

### B. User Authentication
```python
# BAD:
logger.error(f"Login failed for {email} with password {password}")

# GOOD:
logger.warning(f"Failed login attempt for account: {email_clean} from IP: {client_ip}")
```

### C. Database Connectivity
```python
# BAD:
logger.critical(f"Failed to connect to PostgreSQL at {os.getenv('DATABASE_URL')}")

# GOOD:
logger.critical("Failed to connect to PostgreSQL database server. Verify credentials and network reachability.")
```

---

## 6. Audit & Automated Verification

Adherence to this policy is continuously validated through automated test suites:
- `tests/test_secret_log_sanitization.py`: Validates that captured logs during authentication, password reset, and cron executions never contain secrets.
- `pip-audit` & CodeQL: Scans for credential exposures and unmasked sinks.
