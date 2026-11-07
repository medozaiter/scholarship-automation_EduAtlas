import unittest
import os
import json
import time
from fastapi.testclient import TestClient
from web.app import app
from services.security_utils import (
    security_rate_limiter,
    validate_environment_at_startup,
    verify_recaptcha
)

class TestAdditionalSecurityRequirements(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Clear rate limiter state for clean isolated test runs
        with security_rate_limiter._lock:
            security_rate_limiter._requests.clear()
            security_rate_limiter._failed_logins.clear()
            security_rate_limiter._daily_advisor_quotas.clear()

    def test_ai_assistant_daily_quotas_guests_and_registered(self):
        """Verify: Guests limited to 10 msgs/day; Registered limited to 100 msgs/day."""
        # 1. Guest Check (10 msgs/day)
        guest_id = "test_guest_ip_1"
        for i in range(10):
            allowed, used, remaining = security_rate_limiter.check_daily_advisor_quota(guest_id, is_registered=False)
            self.assertTrue(allowed, f"Guest question {i+1} should be allowed")
            self.assertEqual(remaining, 10 - i)
            security_rate_limiter.consume_daily_advisor_question(guest_id, is_registered=False)

        # 11th request for guest must be rejected
        allowed_11, used, remaining = security_rate_limiter.check_daily_advisor_quota(guest_id, is_registered=False)
        self.assertFalse(allowed_11, "11th guest question must be rejected")
        self.assertEqual(remaining, 0)

        # 2. Registered User Check (100 msgs/day)
        user_id = "registered_scholar@example.com"
        for i in range(100):
            allowed, used, remaining = security_rate_limiter.check_daily_advisor_quota(user_id, is_registered=True)
            self.assertTrue(allowed, f"Registered user message {i+1} should be allowed")
            self.assertEqual(remaining, 100 - i)
            security_rate_limiter.consume_daily_advisor_question(user_id, is_registered=True)

        # 101st request for registered user must be rejected
        allowed_101, used, remaining = security_rate_limiter.check_daily_advisor_quota(user_id, is_registered=True)
        self.assertFalse(allowed_101, "101st registered message must be rejected")
        self.assertEqual(remaining, 0)

    def test_api_rate_limiting_thresholds(self):
        """Verify rate limits: Auth (5/15m), Search (60/m), AI assistant (20/m), Contact (3/h)."""
        # 1. Authentication Limit: (5, 900)
        self.assertEqual(security_rate_limiter.LIMITS["auth"], (5, 900))
        self.assertEqual(security_rate_limiter.LIMITS["login"], (5, 900))

        # 2. Search Limit: (60, 60)
        self.assertEqual(security_rate_limiter.LIMITS["search"], (60, 60))

        # 3. AI Assistant Limit: (20, 60)
        self.assertEqual(security_rate_limiter.LIMITS["advisor"], (20, 60))

        # 4. Contact Form Limit: (3, 3600)
        self.assertEqual(security_rate_limiter.LIMITS["contact"], (3, 3600))

    def test_contact_form_rate_limiting_enforcement(self):
        """Verify contact form allows 3 requests then blocks with 429 on 4th."""
        payload = {
            "name": "أحمد الفلسطيني",
            "email": "ahmed.contact@example.com",
            "subject": "استفسار بخصوص منحة الداد",
            "message": "مرحباً، أود الاستفسار عن الموعد النهائي لمنحة DAAD الألمانية لعام 2026.",
            "recaptcha_token": "test_captcha_token"
        }
        # First 3 submissions should succeed
        for i in range(3):
            res = self.client.post("/api/contact", json=payload)
            self.assertEqual(res.status_code, 200, f"Contact attempt {i+1} should succeed")
            self.assertTrue(res.json().get("success"))

        # 4th submission must be blocked by rate limiter (3 requests/hour)
        res_4 = self.client.post("/api/contact", json=payload)
        self.assertEqual(res_4.status_code, 429, "4th contact request within hour must return 429 Too Many Requests")

    def test_enforce_captcha_on_registration_and_contact(self):
        """Verify CAPTCHA enforcement on Registration and Contact form."""
        # 1. Contact Form without CAPTCHA token when secret is active (or verify rejection)
        os.environ["RECAPTCHA_SECRET_KEY"] = "6Le_mock_secret_key_for_testing_123456"
        res_contact = self.client.post("/api/contact", json={
            "name": "محمود علي",
            "email": "mahmoud@example.com",
            "subject": "رسالة دعم فني",
            "message": "استفسار عاجل بخصوص التقديم لمنحة تشيفنينغ.",
            "recaptcha_token": ""  # Missing CAPTCHA
        })
        self.assertEqual(res_contact.status_code, 400, "Missing CAPTCHA on contact form must return 400")

        # 2. Registration without CAPTCHA token
        res_reg = self.client.post("/api/auth/register", json={
            "email": "nocaptcha@example.com",
            "password": "Password123#@",
            "full_name": "طالب بلا كابتشا",
            "recaptcha_token": ""  # Missing CAPTCHA
        })
        self.assertEqual(res_reg.status_code, 400, "Missing CAPTCHA on registration must return 400")

    def test_enforce_captcha_on_login_after_failed_attempts(self):
        """Verify adaptive CAPTCHA on Login: enforced after failed attempts."""
        os.environ["RECAPTCHA_SECRET_KEY"] = "6Le_mock_secret_key_for_testing_123456"
        test_email = "target_student@example.com"

        # Record a failed attempt
        security_rate_limiter.record_failed_login(test_email)
        self.assertEqual(security_rate_limiter.get_failed_login_count(test_email), 1)

        # Subsequent login without CAPTCHA token must be challenged
        res_challenged = self.client.post("/api/auth/login", json={
            "email": test_email,
            "password": "SomeWrongPassword123!",
            "recaptcha_token": ""
        })
        self.assertEqual(res_challenged.status_code, 400)
        self.assertIn("CAPTCHA", res_challenged.text)
        self.assertEqual(res_challenged.headers.get("X-Requires-Captcha"), "true")

    def test_secrets_stored_in_environment_variables(self):
        """Verify all secrets and configuration are read from environment variables."""
        status = validate_environment_at_startup()
        self.assertIn("is_production", status)
        self.assertIn("secret_key_status", status)
        self.assertIn("gemini_api_key_status", status)
        self.assertIn("email_provider_configured", status)
        self.assertIn("database_configured", status)

if __name__ == "__main__":
    unittest.main()
