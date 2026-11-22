import os
import unittest
from fastapi.testclient import TestClient
from web.app import app
from services.security_utils import (
    verify_recaptcha,
    validate_environment_at_startup,
    validate_production_configuration,
    is_production_environment,
    is_recaptcha_placeholder_key,
    security_rate_limiter,
)


class TestRecaptchaSecurity(unittest.TestCase):
    """
    Comprehensive test suite for Google reCAPTCHA server-side verification:
    1. Production Fail-Closed Security:
       - Rejection when RECAPTCHA_SECRET_KEY is missing.
       - Rejection when RECAPTCHA_SECRET_KEY is a placeholder/mock string.
       - Rejection of bypass tokens (test_captcha_token, dev_token, etc.) in production.
       - Protected API endpoints (/api/contact, /api/auth/register-request, /api/auth/register)
         fail closed and reject requests.
       - Startup configuration validation detects missing/placeholder production keys.
    2. Development / Testing Flexibility:
       - Dev bypass available when secret key is unconfigured.
       - Bypass tokens accepted in development.
       - Token presence enforced when secret key is explicitly configured.
       - Startup validation reports development bypass mode without critical failure.
    """

    def setUp(self):
        self._orig_env = os.environ.copy()
        self.client = TestClient(app)
        # Clear rate limiter state to avoid throttling in tests
        security_rate_limiter._requests.clear()
        security_rate_limiter._failed_logins.clear()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    # =========================================================================
    # PRODUCTION SCENARIOS (FAIL CLOSED)
    # =========================================================================

    def test_production_fails_closed_when_secret_key_missing(self):
        """[PROD] verify_recaptcha must fail closed when RECAPTCHA_SECRET_KEY is missing in production."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ.pop("RECAPTCHA_SECRET_KEY", None)

        self.assertTrue(is_production_environment())

        # Calling with any token, empty token, or test token must fail closed
        ok, msg = verify_recaptcha("any_submitted_token")
        self.assertFalse(ok)
        self.assertIn("reCAPTCHA", msg)

        ok_empty, msg_empty = verify_recaptcha("")
        self.assertFalse(ok_empty)

        ok_test_token, msg_test_token = verify_recaptcha("test_captcha_token")
        self.assertFalse(ok_test_token)

    def test_production_fails_closed_when_secret_key_is_placeholder(self):
        """[PROD] verify_recaptcha must fail closed when RECAPTCHA_SECRET_KEY contains placeholder values."""
        placeholders = [
            "",
            "   ",
            "test",
            "dummy",
            "disabled",
            "none",
            "bypass",
            "placeholder",
            "mock",
            "changeme",
            "your_secret_key",
            "your_recaptcha_secret_key",
            "replace_with_your_recaptcha_secret_key",
            "replace_with_a_64_character_random_hex_string_in_production",
        ]
        os.environ["ENVIRONMENT"] = "production"

        for ph in placeholders:
            with self.subTest(placeholder=ph):
                os.environ["RECAPTCHA_SECRET_KEY"] = ph
                self.assertTrue(is_recaptcha_placeholder_key(ph))
                ok, msg = verify_recaptcha("user_client_token_12345")
                self.assertFalse(ok, f"Placeholder '{ph}' should fail closed in production")
                self.assertIn("reCAPTCHA", msg)

    def test_production_rejects_bypass_tokens_even_with_configured_secret(self):
        """[PROD] Test/dev bypass tokens must NEVER bypass verification in production."""
        bypass_tokens = [
            "test_captcha_token",
            "dev_token",
            "bypass_token",
            "mock_recaptcha",
            "test_token",
            "test",
        ]
        os.environ["ENVIRONMENT"] = "production"
        os.environ["RECAPTCHA_SECRET_KEY"] = "6Le_production_key_01234567890123456789"

        for token in bypass_tokens:
            with self.subTest(token=token):
                ok, msg = verify_recaptcha(token)
                self.assertFalse(ok, f"Bypass token '{token}' must be rejected in production")
                self.assertIn("غير صالح في بيئة الإنتاج", msg)

    def test_production_rejects_empty_or_missing_tokens(self):
        """[PROD] Protected requests with missing or empty tokens must be rejected."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["RECAPTCHA_SECRET_KEY"] = "6Le_production_key_01234567890123456789"

        ok_none, _ = verify_recaptcha(None)
        self.assertFalse(ok_none)

        ok_empty, _ = verify_recaptcha("   ")
        self.assertFalse(ok_empty)

    def test_production_protected_endpoints_reject_when_secret_missing(self):
        """[PROD] Protected HTTP endpoints must return 400 when RECAPTCHA_SECRET_KEY is missing."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ.pop("RECAPTCHA_SECRET_KEY", None)

        # 1. Contact Form endpoint
        res_contact = self.client.post("/api/contact", json={
            "name": "محمود خليل",
            "email": "mahmoud.khalil@example.com",
            "subject": "طلب استفسار أمني",
            "message": "رسالة تجريبية للتأكد من الرفض عند غياب المفتاح.",
            "recaptcha_token": "some_token_value"
        })
        self.assertEqual(res_contact.status_code, 400)
        self.assertIn("reCAPTCHA", res_contact.text)

        # 2. Registration Request endpoint (/api/auth/register-request)
        res_req = self.client.post("/api/auth/register-request", json={
            "email": "prod_candidate@example.com",
            "password": "StrongPassword123#@",
            "full_name": "طالب فحص الإنتاج",
            "recaptcha_token": "some_token_value"
        })
        self.assertEqual(res_req.status_code, 400)
        self.assertIn("reCAPTCHA", res_req.text)

        # 3. Direct Registration endpoint (/api/auth/register)
        res_reg = self.client.post("/api/auth/register", json={
            "email": "prod_direct@example.com",
            "password": "StrongPassword123#@",
            "full_name": "طالب تسجيل مباشر",
            "recaptcha_token": "some_token_value"
        })
        self.assertEqual(res_reg.status_code, 400)
        self.assertIn("reCAPTCHA", res_reg.text)

    def test_production_protected_endpoints_reject_bypass_tokens(self):
        """[PROD] Protected endpoints must reject test bypass tokens in production."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["RECAPTCHA_SECRET_KEY"] = "6Le_production_key_01234567890123456789"

        res = self.client.post("/api/contact", json={
            "name": "زياد أحمد",
            "email": "ziad@example.com",
            "subject": "محاولة تجاوز الكابتشا",
            "message": "اختبار محاولة إرسال توكن تجريبي في بيئة الإنتاج.",
            "recaptcha_token": "test_captcha_token"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("reCAPTCHA", res.text)

    def test_production_startup_validation_detects_configuration_status(self):
        """[PROD] validate_environment_at_startup flags missing or placeholder keys as CRITICAL."""
        os.environ["ENVIRONMENT"] = "production"

        # 1. Missing secret key
        os.environ.pop("RECAPTCHA_SECRET_KEY", None)
        report_missing = validate_environment_at_startup()
        self.assertTrue(report_missing["is_production"])
        self.assertEqual(report_missing["recaptcha_status"], "missing")
        critical_missing = [i for i in report_missing["issues"] if "CRITICAL: RECAPTCHA_SECRET_KEY" in i]
        self.assertEqual(len(critical_missing), 1)

        # validate_production_configuration should raise RuntimeError when raise_on_error=True
        with self.assertRaises(RuntimeError):
            validate_production_configuration(raise_on_error=True)

        # 2. Placeholder secret key
        os.environ["RECAPTCHA_SECRET_KEY"] = "your_secret_key"
        report_ph = validate_environment_at_startup()
        self.assertEqual(report_ph["recaptcha_status"], "placeholder")
        critical_ph = [i for i in report_ph["issues"] if "CRITICAL: RECAPTCHA_SECRET_KEY" in i]
        self.assertEqual(len(critical_ph), 1)

        # 3. Properly configured secret key
        os.environ["RECAPTCHA_SECRET_KEY"] = "6Le_valid_production_secret_key_123456789"
        report_ok = validate_environment_at_startup()
        self.assertEqual(report_ok["recaptcha_status"], "configured")
        recaptcha_issues = [i for i in report_ok["issues"] if "RECAPTCHA_SECRET_KEY" in i]
        self.assertEqual(len(recaptcha_issues), 0)

        # validate_production_configuration passes cleanly
        prod_report = validate_production_configuration(raise_on_error=True)
        self.assertEqual(prod_report["recaptcha_status"], "configured")

    # =========================================================================
    # DEVELOPMENT / TESTING SCENARIOS (BYPASS PERMITTED)
    # =========================================================================

    def test_development_bypass_when_secret_key_unconfigured(self):
        """[DEV] verify_recaptcha permits automatic bypass in development when key is unconfigured."""
        os.environ["ENVIRONMENT"] = "development"
        os.environ.pop("RECAPTCHA_SECRET_KEY", None)

        self.assertFalse(is_production_environment())

        # Empty token passes with BYPASSED_NO_SECRET
        ok_empty, status_empty = verify_recaptcha("")
        self.assertTrue(ok_empty)
        self.assertEqual(status_empty, "BYPASSED_NO_SECRET")

        # Any token also passes with BYPASSED_NO_SECRET
        ok_any, status_any = verify_recaptcha("random_unverified_token")
        self.assertTrue(ok_any)
        self.assertEqual(status_any, "BYPASSED_NO_SECRET")

    def test_development_bypass_tokens(self):
        """[DEV] Recognized test tokens successfully bypass verification in dev/test."""
        os.environ["ENVIRONMENT"] = "development"
        # Even if a mock secret is present, test tokens are recognized
        os.environ["RECAPTCHA_SECRET_KEY"] = "6Le_mock_key_for_local_development"

        test_tokens = [
            "test_captcha_token",
            "dev_token",
            "bypass_token",
            "mock_recaptcha",
            "test_token",
            "test",
        ]

        for token in test_tokens:
            with self.subTest(token=token):
                ok, status = verify_recaptcha(token)
                self.assertTrue(ok)
                self.assertEqual(status, "BYPASSED_TEST_TOKEN")

    def test_development_enforces_token_when_secret_configured(self):
        """[DEV] If a secret key is configured, an empty token is rejected."""
        os.environ["ENVIRONMENT"] = "development"
        os.environ["RECAPTCHA_SECRET_KEY"] = "6Le_mock_key_for_local_development"

        ok_empty, msg = verify_recaptcha("")
        self.assertFalse(ok_empty)
        self.assertIn("مطلوب", msg)

    def test_development_protected_endpoints_allow_dev_bypass(self):
        """[DEV] Protected endpoints succeed when using test bypass in development."""
        os.environ["ENVIRONMENT"] = "development"
        os.environ.pop("RECAPTCHA_SECRET_KEY", None)

        res_contact = self.client.post("/api/contact", json={
            "name": "طالب محلي",
            "email": "dev_student@example.com",
            "subject": "اختبار محلي للنموذج",
            "message": "رسالة اختبارية في بيئة التطوير المحلية للتأكد من قبول الطلب.",
            "recaptcha_token": "test_captcha_token"
        })
        self.assertEqual(res_contact.status_code, 200)
        self.assertTrue(res_contact.json().get("success"))

    def test_development_startup_validation(self):
        """[DEV] validate_environment_at_startup reports bypass notice without critical errors."""
        os.environ["ENVIRONMENT"] = "development"
        os.environ.pop("RECAPTCHA_SECRET_KEY", None)

        report = validate_environment_at_startup()
        self.assertFalse(report["is_production"])
        self.assertEqual(report["recaptcha_status"], "missing")

        # Must NOT flag as CRITICAL in development
        recaptcha_issues = [i for i in report["issues"] if "RECAPTCHA_SECRET_KEY" in i]
        self.assertTrue(len(recaptcha_issues) > 0)
        self.assertFalse(any("CRITICAL" in i for i in recaptcha_issues))
        self.assertIn("development bypass mode active", recaptcha_issues[0])


if __name__ == "__main__":
    unittest.main()
