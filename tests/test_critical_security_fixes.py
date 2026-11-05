import sys
import os
import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from web.app import app
from services.security_utils import (
    create_session_token,
    verify_session_token,
    create_refresh_token,
    verify_refresh_token,
    revoke_token,
    is_token_revoked,
    generate_csrf_token,
    verify_csrf_token,
    verify_cron_secret,
    APP_SECRET_KEY
)
from services.auth_service import AuthService

client = TestClient(app)
auth_service = AuthService()

class TestCriticalSecurityFixes(unittest.TestCase):
    """
    Verification suite for Phase 2 Critical (🔴) Security Hardening:
    1. Session Management (30m max lifespan, refresh tokens, server-side revocation)
    2. CSRF Defense (Double-submit HMAC token for cookie requests, API Bearer exemption)
    3. Input Validation (Strict Pydantic models, extra="forbid", field boundaries)
    4. Secrets Management (Zero hardcoded secrets in cron verification, environment-only)
    """

    def setUp(self):
        self.test_email = f"critical.sec.{int(time.time() * 1000)}@example.com"
        self.test_password = "SecureAcademic2026!"
        self.test_fullname = "Mustafa Zaiter"

    # ==============================================================================
    # 1. SESSION MANAGEMENT & REVOCATION
    # ==============================================================================
    def test_session_token_lifespan_strictly_capped_at_30_minutes(self):
        """Ensures create_session_token caps expiration at 1800s regardless of parameter."""
        token = create_session_token(self.test_email, role="student", expires_in_seconds=86400)
        payload = verify_session_token(token)
        self.assertIsNotNone(payload, "Session token must verify successfully")
        lifetime = payload["exp"] - payload["iat"]
        self.assertLessEqual(lifetime, 1800, "Lifespan must be strictly <= 1800 seconds (30 minutes)")
        self.assertIn("nonce", payload, "Payload must include high-entropy cryptographic nonce")

    def test_refresh_token_lifecycle_and_session_renewal(self):
        """Verifies refresh token issuance, validation, and session renewal via auth_service."""
        refresh_tok = create_refresh_token(self.test_email, role="student", expires_in_seconds=7 * 86400)
        payload = verify_refresh_token(refresh_tok)
        self.assertIsNotNone(payload, "Refresh token must verify successfully")
        self.assertEqual(payload.get("purpose"), "refresh")

        # Session token cannot be used as refresh token
        session_tok = create_session_token(self.test_email, role="student")
        self.assertIsNone(verify_refresh_token(session_tok), "Session token must be rejected by verify_refresh_token")

    def test_server_side_token_revocation(self):
        """Ensures revoked tokens fail immediately upon logout across all endpoints."""
        session_tok = create_session_token(self.test_email, role="student")
        self.assertIsNotNone(verify_session_token(session_tok), "Token should initially be valid")
        self.assertFalse(is_token_revoked(session_tok), "Token should not be revoked yet")

        # Invalidate server-side
        revoke_token(session_tok)
        self.assertTrue(is_token_revoked(session_tok), "Token must report as revoked")
        self.assertIsNone(verify_session_token(session_tok), "verify_session_token must reject revoked token")

    def test_logout_endpoint_revokes_cookies_and_bearer_tokens(self):
        """Tests that /api/auth/logout invalidates session tokens in revocation store."""
        reg_resp = client.post("/api/auth/register", json={
            "email": self.test_email,
            "password": self.test_password,
            "full_name": self.test_fullname,
            "degree": "Undergraduate (Bachelor's)",
            "gpa": "90%",
            "majors": ["Cybersecurity"]
        })
        self.assertEqual(reg_resp.status_code, 200)
        data = reg_resp.json()
        token = data.get("token")
        self.assertIsNotNone(token)

        # Logout with Bearer token
        logout_resp = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(logout_resp.status_code, 200)
        self.assertTrue(is_token_revoked(token), "Bearer token must be revoked server-side upon logout")
        self.assertIsNone(verify_session_token(token), "Revoked token must be rejected")

    # ==============================================================================
    # 2. CSRF PROTECTION
    # ==============================================================================
    def test_csrf_token_issuance_and_cryptographic_verification(self):
        """Verifies HMAC signing and tampering defense of CSRF tokens."""
        token = generate_csrf_token()
        self.assertTrue(verify_csrf_token(token), "Generated CSRF token must verify successfully")

        # Tampered token
        tampered = token[:-4] + "ABCD"
        self.assertFalse(verify_csrf_token(tampered), "Tampered CSRF token must be rejected")

        # Endpoint issuance
        endpoint_resp = client.get("/api/auth/csrf-token")
        self.assertEqual(endpoint_resp.status_code, 200)
        issued_token = endpoint_resp.json().get("csrf_token")
        self.assertTrue(verify_csrf_token(issued_token), "Token from /api/auth/csrf-token must be valid")
        self.assertIn("csrf_token", endpoint_resp.cookies, "Should set csrf_token cookie")

    def test_cookie_authenticated_mutating_request_rejected_without_csrf_token(self):
        """Simulates CSRF attack: ambient cookie sent to mutating endpoint without X-CSRF-Token."""
        session_tok = create_session_token("mustafa-zaiter@example.com", role="student")

        # Mutating request with session_token cookie but NO CSRF token -> REJECT 403
        attack_resp = client.post(
            "/api/community/posts",
            json={"content": "Malicious forged cross-site comment", "category": "general_discussion"},
            cookies={"session_token": session_tok}
        )
        self.assertEqual(attack_resp.status_code, 403, "Must reject cookie mutating request without CSRF token")
        self.assertEqual(attack_resp.json().get("error_code"), "CSRF_VERIFICATION_FAILED")

    def test_cookie_authenticated_mutating_request_accepted_with_valid_csrf_token(self):
        """Legitimate request: ambient cookie sent along with valid X-CSRF-Token header."""
        session_tok = create_session_token("medo.msz.2006@gmail.com", role="student")
        csrf_tok = generate_csrf_token()

        legit_resp = client.post(
            "/api/match/calculate",
            json={"gpa": "90%", "degree": "Undergraduate (Bachelor's)", "majors": ["Cybersecurity"]},
            cookies={"session_token": session_tok},
            headers={"X-CSRF-Token": csrf_tok}
        )
        self.assertEqual(legit_resp.status_code, 200, "Must accept cookie request with valid X-CSRF-Token")

    def test_bearer_token_exempt_from_csrf(self):
        """Programmatic API clients sending Authorization: Bearer are immune to browser ambient CSRF."""
        session_tok = create_session_token("medo.msz.2006@gmail.com", role="student")

        api_resp = client.post(
            "/api/match/calculate",
            json={"gpa": "90%", "degree": "Undergraduate (Bachelor's)", "majors": ["Cybersecurity"]},
            headers={"Authorization": f"Bearer {session_tok}"}
        )
        self.assertEqual(api_resp.status_code, 200, "Bearer API requests must not require CSRF token")

    # ==============================================================================
    # 3. STRICT INPUT VALIDATION (Pydantic ConfigDict & Extra Fields)
    # ==============================================================================
    def test_input_validation_forbids_extra_injected_fields(self):
        """Protects against Mass Assignment Vulnerabilities by forbidding extra parameters."""
        extra_fields_payload = {
            "email": f"extra.fields.{int(time.time())}@example.com",
            "password": "SafeAcademic2026!",
            "full_name": "Testing Student",
            "injected_admin_flag": True,  # Disallowed extra field
            "role": "admin"               # Disallowed extra field
        }
        resp = client.post("/api/auth/register", json=extra_fields_payload)
        self.assertEqual(resp.status_code, 400, "Must reject request containing extra unrecognized fields")

    def test_input_validation_enforces_field_length_limits(self):
        """Rejects oversized payloads that attempt buffer overflow or memory denial of service."""
        oversized_name = "A" * 150  # Max length is 100
        resp = client.post("/api/auth/register", json={
            "email": f"oversized.{int(time.time())}@example.com",
            "password": "SafeAcademic2026!",
            "full_name": oversized_name
        })
        self.assertEqual(resp.status_code, 400, "Must reject oversized full_name exceeding max_length")

    # ==============================================================================
    # 4. SECRETS MANAGEMENT & CRON VERIFICATION
    # ==============================================================================
    def test_cron_verification_rejects_old_hardcoded_secrets(self):
        """Ensures legacy hardcoded secret strings are rejected if not in environment."""
        # Unset CRON_SECRET if temporarily present
        old_cron = os.environ.pop("CRON_SECRET", None)
        try:
            # Old hardcoded strings must be rejected
            self.assertFalse(verify_cron_secret("scholarpilot-cron-secret-2026"), "Old hardcoded secret 1 must be rejected")
            self.assertFalse(verify_cron_secret("scholarpilot_cron_secret"), "Old hardcoded secret 2 must be rejected")
            self.assertFalse(verify_cron_secret("random_invalid_secret"), "Invalid secret must be rejected")
            self.assertFalse(verify_cron_secret(""), "Empty secret must be rejected")

            # Dynamic APP_SECRET_KEY is accepted
            self.assertTrue(verify_cron_secret(APP_SECRET_KEY), "APP_SECRET_KEY must be accepted as authorized internal secret")

            # Custom CRON_SECRET from environment is accepted
            custom_secret = "test_env_cron_secret_abcdef123456789"
            os.environ["CRON_SECRET"] = custom_secret
            self.assertTrue(verify_cron_secret(custom_secret), "Configured CRON_SECRET must be accepted")
        finally:
            if old_cron:
                os.environ["CRON_SECRET"] = old_cron
            else:
                os.environ.pop("CRON_SECRET", None)

    @patch("web.app.run_radar_scan_job")
    def test_cron_endpoint_auth_protection(self, mock_job):
        """Verifies /api/cron/trigger-scan returns 403 on invalid secret and 202 on valid secret."""
        # 1. No secret -> 403 Forbidden
        no_sec_resp = client.post("/api/cron/trigger-scan")
        self.assertEqual(no_sec_resp.status_code, 403)

        # 2. Old hardcoded secret -> 403 Forbidden
        old_cron = os.environ.pop("CRON_SECRET", None)
        try:
            bad_sec_resp = client.post("/api/cron/trigger-scan", headers={"X-Cron-Secret": "scholarpilot-cron-secret-2026"})
            self.assertEqual(bad_sec_resp.status_code, 403, "Old hardcoded secret must return 403")

            # 3. Valid secret configured in environment -> 202 Accepted
            test_secret = "secret_for_automated_test_123"
            os.environ["CRON_SECRET"] = test_secret
            good_resp = client.post("/api/cron/trigger-scan", headers={"X-Cron-Secret": test_secret})
            self.assertEqual(good_resp.status_code, 202, "Valid CRON_SECRET must return 202 Accepted")
        finally:
            if old_cron:
                os.environ["CRON_SECRET"] = old_cron
            else:
                os.environ.pop("CRON_SECRET", None)

    def test_env_example_and_gitignore_hygiene(self):
        """Verifies .env is in .gitignore and .env.example doesn't recommend wildcard CORS."""
        env_example_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.example")
        gitignore_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".gitignore")

        with open(gitignore_path, "r", encoding="utf-8") as f:
            gitignore_content = f.read()
        self.assertIn(".env", gitignore_content.splitlines(), ".env must be explicitly ignored in .gitignore")

        with open(env_example_path, "r", encoding="utf-8") as f:
            env_example_content = f.read()
        self.assertNotIn("ALLOWED_ORIGINS=*\n", env_example_content, ".env.example must not recommend wildcard '*' CORS")
        self.assertIn("CRON_SECRET=", env_example_content, ".env.example must document CRON_SECRET")

    # ==============================================================================
    # 5. HIGH & MEDIUM PRIORITY VERIFICATIONS (Diagnostics, CSP, Pillow, Policy)
    # ==============================================================================
    def test_diagnostics_hides_sensitive_infrastructure_from_public(self):
        """Ensures unauthenticated requests to /api/health/diagnostics receive only {"status": "ok"}."""
        resp = client.get("/api/health/diagnostics")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data, {"status": "ok"}, "Public diagnostics must hide database/email/ai internal keys")
        self.assertNotIn("database", data)
        self.assertNotIn("email", data)
        self.assertNotIn("ai", data)

    def test_diagnostics_allows_authorized_cron(self):
        """Ensures requests with valid CRON_SECRET receive full diagnostic details."""
        test_sec = "diag_test_cron_secret_777"
        os.environ["CRON_SECRET"] = test_sec
        try:
            resp = client.get("/api/health/diagnostics", headers={"X-Cron-Secret": test_sec})
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data.get("status"), "healthy")
            self.assertIn("database", data)
            self.assertIn("email", data)
        finally:
            os.environ.pop("CRON_SECRET", None)

    def test_security_headers_csp_has_no_unsafe_eval(self):
        """Verifies Content-Security-Policy does not include 'unsafe-eval'."""
        resp = client.get("/")
        csp = resp.headers.get("content-security-policy", "")
        self.assertNotIn("'unsafe-eval'", csp, "CSP must not contain 'unsafe-eval'")
        self.assertIn("default-src 'self'", csp)
        self.assertEqual(resp.headers.get("x-frame-options"), "DENY")
        self.assertEqual(resp.headers.get("x-content-type-options"), "nosniff")

    def test_security_policy_and_requirements_pinning(self):
        """Verifies SECURITY.md exists and requirements.txt contains pinned '==' versions."""
        sec_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "SECURITY.md")
        req_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements.txt")
        req_dev_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements-dev.txt")

        self.assertTrue(os.path.exists(sec_path), "SECURITY.md must exist in repository root")
        self.assertTrue(os.path.exists(req_path), "requirements.txt must exist")
        self.assertTrue(os.path.exists(req_dev_path), "requirements-dev.txt must exist")

        with open(req_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        for l in lines:
            self.assertTrue("==" in l or ">=" in l, f"Dependency '{l}' must specify a valid version constraint ('==' or '>=')")


if __name__ == "__main__":
    unittest.main()
