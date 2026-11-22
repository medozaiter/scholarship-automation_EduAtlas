import unittest
import time
from starlette.testclient import TestClient
from web.app import app
from services.auth_service import AuthService
from services.db import get_user_by_email, delete_user_by_email
from services.subscriber_service import SubscriberService
from services.security_utils import security_rate_limiter


class TestEmailOtpRegistration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.auth_service = AuthService()

    def setUp(self):
        security_rate_limiter.reset()
        self.test_email = f"student_otp_test_{int(time.time() * 1000)}@example.com"
        self.test_password = "SecurePassword2026!"
        self.test_name = "سامي خالد"

    def tearDown(self):
        delete_user_by_email(self.test_email)
        self.auth_service._remove_pending_registration(self.test_email)

    def test_01_registration_fails_without_email(self):
        """Verify that account creation without email is strictly rejected."""
        # A. Missing email field
        bad_payload_missing = {
            "password": self.test_password,
            "full_name": self.test_name,
            "degree": "Undergraduate (Bachelor's)",
            "recaptcha_token": "test"
        }
        res = self.client.post("/api/auth/register-request", json=bad_payload_missing)
        self.assertIn(res.status_code, [400, 422], "Must reject request without email field")

        # B. Empty email field
        bad_payload_empty = {
            "email": "",
            "password": self.test_password,
            "full_name": self.test_name,
            "degree": "Undergraduate (Bachelor's)",
            "recaptcha_token": "test"
        }
        res = self.client.post("/api/auth/register-request", json=bad_payload_empty)
        self.assertIn(res.status_code, [400, 422], "Must reject request with empty email")

        # C. Whitespace email field
        bad_payload_ws = {
            "email": "   ",
            "password": self.test_password,
            "full_name": self.test_name,
            "degree": "Undergraduate (Bachelor's)",
            "recaptcha_token": "test"
        }
        res = self.client.post("/api/auth/register-request", json=bad_payload_ws)
        self.assertIn(res.status_code, [400, 422], "Must reject whitespace email")

        # D. Invalid email format
        bad_payload_invalid = {
            "email": "notanemail@fake",
            "password": self.test_password,
            "full_name": self.test_name,
            "degree": "Undergraduate (Bachelor's)",
            "recaptcha_token": "test"
        }
        res = self.client.post("/api/auth/register-request", json=bad_payload_invalid)
        self.assertIn(res.status_code, [400, 422], "Must reject invalid email format")

    def test_02_step1_initiate_registration_stores_pending_and_generates_otp(self):
        """Step 1: Request OTP code dispatches email and stores pending registration."""
        payload = {
            "email": self.test_email,
            "password": self.test_password,
            "full_name": self.test_name,
            "degree": "Undergraduate (Bachelor's)",
            "gpa": "91.5%",
            "country": "Palestine",
            "recaptcha_token": "test"
        }
        res = self.client.post("/api/auth/register-request", json=payload)
        self.assertEqual(res.status_code, 200, f"Register request failed: {res.text}")
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("email"), self.test_email)

        # Verify user is NOT yet in active database
        user = get_user_by_email(self.test_email)
        self.assertIsNone(user, "User must NOT exist in active database before OTP verification!")

        # Verify pending record exists
        pending = self.auth_service._get_pending_registration(self.test_email)
        self.assertIsNotNone(pending, "Pending registration must exist in pending storage")
        otp = pending.get("verification_code")
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp), 6, "Verification code must be exactly 6 digits")

    def test_03_step2_rejects_wrong_otp_code(self):
        """Step 2: Submitting an invalid OTP code must be rejected and track attempts."""
        # Initiate
        payload = {
            "email": self.test_email,
            "password": self.test_password,
            "full_name": self.test_name,
            "degree": "Undergraduate (Bachelor's)",
            "gpa": "91.5%",
            "country": "Palestine",
            "recaptcha_token": "test"
        }
        res_init = self.client.post("/api/auth/register-request", json=payload)
        self.assertEqual(res_init.status_code, 200)

        # Submit wrong code
        res = self.client.post("/api/auth/register-confirm", json={
            "email": self.test_email,
            "code": "000000"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("غير صحيح", res.text)

        # User must still not exist
        self.assertIsNone(get_user_by_email(self.test_email))

        # Check pending attempts count
        pending = self.auth_service._get_pending_registration(self.test_email)
        self.assertIsNotNone(pending)
        self.assertEqual(pending.get("attempts"), 1)

    def test_04_step2_success_creates_verified_user_and_subscribes(self):
        """Step 2: Submitting correct OTP creates verified account and subscribes to notifications."""
        # Initiate
        payload = {
            "email": self.test_email,
            "password": self.test_password,
            "full_name": self.test_name,
            "degree": "Undergraduate (Bachelor's)",
            "gpa": "91.5%",
            "country": "Palestine",
            "recaptcha_token": "test"
        }
        res_init = self.client.post("/api/auth/register-request", json=payload)
        self.assertEqual(res_init.status_code, 200)

        pending = self.auth_service._get_pending_registration(self.test_email)
        valid_otp = pending.get("verification_code")

        # Submit correct code
        res = self.client.post("/api/auth/register-confirm", json={
            "email": self.test_email,
            "code": valid_otp
        })
        self.assertEqual(res.status_code, 200, f"Register confirm failed: {res.text}")
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertIn("token", data)
        self.assertIn("user", data)

        # Verify user is now created in active database with email_verified=True
        user = get_user_by_email(self.test_email)
        self.assertIsNotNone(user, "User must be created in active database")
        self.assertTrue(user.get("email_verified"), "email_verified must be True")
        self.assertTrue(user.get("email_notifications"), "email_notifications must be True")

        # Verify user is enrolled in SubscriberService so alerts will be sent to their email
        sub_service = SubscriberService()
        sub = sub_service.get_by_email(self.test_email)
        self.assertIsNotNone(sub, "User must be enrolled in SubscriberService")
        self.assertEqual(sub.get("email"), self.test_email)

        # Verify pending record was cleaned up
        self.assertIsNone(self.auth_service._get_pending_registration(self.test_email))

        # Verify session cookies were set
        self.assertIn("session_token", res.cookies)
        self.assertIn("csrf_token", res.cookies)

    def test_05_resend_otp_and_cooldown(self):
        """Verify that resending OTP enforces 60-second cooldown protection."""
        payload = {
            "email": self.test_email,
            "password": self.test_password,
            "full_name": self.test_name,
            "degree": "Undergraduate (Bachelor's)",
            "gpa": "91.5%",
            "country": "Palestine",
            "recaptcha_token": "test"
        }
        res_init = self.client.post("/api/auth/register-request", json=payload)
        self.assertEqual(res_init.status_code, 200)

        # Immediate resend within 60 seconds must be rejected with cooldown notice
        res_resend = self.client.post("/api/auth/register-resend", json={
            "email": self.test_email
        })
        self.assertEqual(res_resend.status_code, 400)
        self.assertIn("ثانية", res_resend.text)


if __name__ == "__main__":
    unittest.main()
