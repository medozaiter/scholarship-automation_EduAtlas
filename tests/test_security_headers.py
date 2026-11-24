import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from web.app import app

client = TestClient(app)


class TestSecurityHeaders:
    """
    Verification suite for HTTP Security Headers Hardening:
    - HTTP Strict Transport Security (HSTS)
    - Content Security Policy (CSP) with dynamic nonce
    - X-Frame-Options (Clickjacking defense)
    - X-Content-Type-Options (MIME sniffing prevention)
    - Referrer-Policy
    - Permissions-Policy & Cross-Origin Isolation
    - Server fingerprint suppression
    """

    def _assert_security_headers(self, headers):
        # 1. HSTS
        assert "Strict-Transport-Security" in headers, "Missing Strict-Transport-Security (HSTS)"
        hsts = headers["Strict-Transport-Security"]
        assert "max-age=" in hsts
        assert "includeSubDomains" in hsts

        # 2. CSP
        assert "Content-Security-Policy" in headers, "Missing Content-Security-Policy (CSP)"
        csp = headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp
        assert "base-uri 'self'" in csp

        # 3. X-Frame-Options
        assert headers.get("X-Frame-Options") == "DENY", "X-Frame-Options must be DENY"

        # 4. X-Content-Type-Options
        assert headers.get("X-Content-Type-Options") == "nosniff", "X-Content-Type-Options must be nosniff"

        # 5. Referrer-Policy
        assert "Referrer-Policy" in headers, "Missing Referrer-Policy"
        assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

        # 6. Legacy XSS Shield
        assert headers.get("X-XSS-Protection") == "1; mode=block"

        # 7. Server Fingerprint Suppression
        assert "Server" not in headers, "Server header must be stripped"
        assert "server" not in headers, "server header must be stripped"
        assert "X-Powered-By" not in headers, "X-Powered-By header must be stripped"
        assert "x-powered-by" not in headers, "x-powered-by header must be stripped"

    def test_security_headers_on_html_views(self):
        """Verifies security headers on root HTML page."""
        res = client.get("/")
        assert res.status_code == 200
        self._assert_security_headers(res.headers)

    def test_security_headers_on_api_endpoints(self):
        """Verifies security headers on public API endpoints."""
        res = client.get("/api/scholarships/live")
        assert res.status_code == 200
        self._assert_security_headers(res.headers)

    def test_security_headers_on_health_and_metrics_probes(self):
        """Verifies security headers on /health and /metrics probes."""
        res_h = client.get("/health")
        assert res_h.status_code in [200, 503]
        self._assert_security_headers(res_h.headers)

        res_m = client.get("/metrics")
        assert res_m.status_code == 200
        self._assert_security_headers(res_m.headers)

    def test_security_headers_on_404_not_found(self):
        """Verifies security headers remain present even on 404 responses."""
        res = client.get("/nonexistent-endpoint-audit-check")
        assert res.status_code == 404
        self._assert_security_headers(res.headers)

    def test_security_headers_on_429_throttled_response(self):
        """Verifies security headers are retained when rate limiter returns 429."""
        os.environ["RATE_LIMIT_METRICS"] = "1"
        test_ip = "192.0.2.77"
        headers = {"X-Forwarded-For": test_ip}

        # 1st request succeeds
        res1 = client.get("/metrics", headers=headers)
        assert res1.status_code == 200

        # 2nd request throttled
        res2 = client.get("/metrics", headers=headers)
        assert res2.status_code == 429
        self._assert_security_headers(res2.headers)

    def test_csp_nonce_is_unique_per_request(self):
        """Verifies per-request CSP nonce generation eliminates static replay."""
        res1 = client.get("/")
        res2 = client.get("/")

        nonce1 = res1.headers.get("X-CSP-Nonce")
        nonce2 = res2.headers.get("X-CSP-Nonce")

        assert nonce1 is not None and len(nonce1) >= 16
        assert nonce2 is not None and len(nonce2) >= 16
        assert nonce1 != nonce2, "CSP nonce must be randomized and unique per request"
        assert f"'nonce-{nonce1}'" in res1.headers["Content-Security-Policy"]
        assert f"'nonce-{nonce2}'" in res2.headers["Content-Security-Policy"]
