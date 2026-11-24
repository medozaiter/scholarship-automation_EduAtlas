import os
import sys
import time
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from web.app import app
from services.security_utils import security_rate_limiter, create_session_token

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_rate_limiter_state():
    """Resets rate limiter state before and after each test."""
    security_rate_limiter.reset()
    yield
    security_rate_limiter.reset()
    # Clean any temporary environment overrides
    for key in list(os.environ.keys()):
        if key.startswith("RATE_LIMIT_"):
            del os.environ[key]


class TestRateLimitingCoverage:
    """
    Verification suite for Rate Limiting Coverage Remediation:
    - All public endpoints (/health, /metrics, /auth/*, /cron/*, search, general) are protected.
    - Limits are configurable via environment variables.
    - Requests are throttled after limit is exceeded (HTTP 429).
    - Authenticated users are tracked per account and not blocked by IP noise.
    """

    def test_health_endpoint_is_rate_limited(self):
        """Verifies /health probe is protected and throttles when limit is exceeded."""
        os.environ["RATE_LIMIT_HEALTH"] = "3"
        test_ip = "192.0.2.11"

        # First 3 requests must succeed (200 healthy or 503 if DB disconnected in test env)
        for i in range(3):
            res = client.get("/health", headers={"X-Forwarded-For": test_ip})
            assert res.status_code in [200, 503], f"Request {i+1} should succeed"
            assert "X-RateLimit-Limit" in res.headers

        # 4th request must be throttled
        res_throttled = client.get("/health", headers={"X-Forwarded-For": test_ip})
        assert res_throttled.status_code == 429
        data = res_throttled.json()
        assert data["success"] is False
        assert "Retry-After" in res_throttled.headers
        assert res_throttled.headers["X-RateLimit-Remaining"] == "0"

    def test_metrics_endpoint_is_rate_limited(self):
        """Verifies /metrics endpoint exists and enforces rate limiting."""
        os.environ["RATE_LIMIT_METRICS"] = "2"
        test_ip = "192.0.2.12"

        # 2 allowed
        for _ in range(2):
            res = client.get("/metrics", headers={"X-Forwarded-For": test_ip})
            assert res.status_code == 200
            assert res.json().get("service") == "EduAtlas"

        # 3rd throttled
        res_blocked = client.get("/metrics", headers={"X-Forwarded-For": test_ip})
        assert res_blocked.status_code == 429
        assert "Retry-After" in res_blocked.headers

    def test_cron_endpoint_is_rate_limited(self):
        """Verifies /api/cron/trigger-scan is rate limited even with valid cron secret."""
        os.environ["RATE_LIMIT_CRON"] = "2"
        cron_secret = "test-cron-secret-32-chars-long-abc"
        os.environ["CRON_SECRET"] = cron_secret
        test_ip = "192.0.2.13"

        headers = {
            "X-Forwarded-For": test_ip,
            "X-Cron-Secret": cron_secret
        }

        with patch("fastapi.BackgroundTasks.add_task"):
            # First 2 requests accepted
            for _ in range(2):
                res = client.post("/api/cron/trigger-scan", headers=headers)
                assert res.status_code == 202

            # 3rd request throttled
            res_throttled = client.post("/api/cron/trigger-scan", headers=headers)
            assert res_throttled.status_code == 429

    def test_public_search_endpoints_rate_limited(self):
        """Verifies public scholarship search endpoints enforce rate limiting."""
        os.environ["RATE_LIMIT_SEARCH"] = "3"
        test_ip = "192.0.2.14"

        headers = {"X-Forwarded-For": test_ip}

        for _ in range(3):
            res = client.get("/api/scholarships/live?search=computer", headers=headers)
            assert res.status_code == 200

        res_throttled = client.get("/api/scholarships/live?search=computer", headers=headers)
        assert res_throttled.status_code == 429

    def test_auth_login_endpoint_rate_limited(self):
        """Verifies /api/auth/login enforces strict login rate limits."""
        os.environ["RATE_LIMIT_LOGIN"] = "2"
        test_ip = "192.0.2.15"

        headers = {"X-Forwarded-For": test_ip}

        # 2 requests
        for _ in range(2):
            client.post(
                "/api/auth/login",
                json={"email": "nobody@example.com", "password": "WrongPassword1!"},
                headers=headers
            )

        # 3rd attempt throttled
        res_throttled = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "WrongPassword1!"},
            headers=headers
        )
        assert res_throttled.status_code == 429

    def test_configurable_limits_via_environment_variables(self):
        """Verifies rate limit thresholds dynamically adapt to environment configuration."""
        os.environ["RATE_LIMIT_HEALTH"] = "5,120"
        max_reqs, win = security_rate_limiter.get_limit("health")
        assert max_reqs == 5
        assert win == 120

        os.environ["RATE_LIMIT_METRICS_LIMIT"] = "15"
        os.environ["RATE_LIMIT_METRICS_WINDOW"] = "30"
        max_m, win_m = security_rate_limiter.get_limit("metrics")
        assert max_m == 15
        assert win_m == 30

    def test_authenticated_traffic_not_blocked_by_ip_exhaustion(self):
        """
        Guarantees that an anonymous user exhausting an IP limit
        does NOT block a legitimate authenticated student on the same IP (e.g. university NAT).
        """
        os.environ["RATE_LIMIT_GENERAL"] = "2"
        shared_ip = "192.0.2.99"

        # 1. Anonymous attacker exhausts IP rate limit on a general public endpoint
        res1 = client.get("/api/stats", headers={"X-Forwarded-For": shared_ip})
        assert res1.status_code in [200, 503]
        res2 = client.get("/api/stats", headers={"X-Forwarded-For": shared_ip})
        assert res2.status_code in [200, 503]

        # 3rd anonymous request from that IP is throttled
        res_blocked = client.get("/api/stats", headers={"X-Forwarded-For": shared_ip})
        assert res_blocked.status_code == 429

        # 2. Legitimate student with valid bearer token requests from the SAME shared IP
        student_email = "verified.student.rate@eduatlas.org"
        auth_token = create_session_token(email=student_email, role="student")

        auth_headers = {
            "X-Forwarded-For": shared_ip,
            "Authorization": f"Bearer {auth_token}"
        }

        # Authenticated student request MUST NOT be blocked by the anonymous IP exhaustion!
        res_auth = client.get("/api/stats", headers=auth_headers)
        assert res_auth.status_code != 429, "Authenticated user should not be blocked by anonymous IP exhaustion"

    def test_rate_limit_metrics_headers_rfc_compliance(self):
        """Verifies standard RFC rate limit headers are included in HTTP responses."""
        res = client.get("/health", headers={"X-Forwarded-For": "192.0.2.88"})
        assert res.status_code in [200, 503]
        assert "X-RateLimit-Limit" in res.headers
        assert "X-RateLimit-Remaining" in res.headers
        assert "X-RateLimit-Reset" in res.headers
        assert int(res.headers["X-RateLimit-Remaining"]) >= 0
