# -*- coding: utf-8 -*-
import unittest
import os
import re
from fastapi.testclient import TestClient
from web.app import app
from services.security_utils import validate_name, validate_gpa, security_rate_limiter

class TestWizardValidationAndHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        security_rate_limiter.reset() if hasattr(security_rate_limiter, "reset") else None

    def test_01_backend_name_validation(self):
        """Verify that validate_name rejects symbol gibberish and accepts authentic names."""
        invalid_names = [
            "@!@#$$@#@!,,,,,",
            "12345678",
            "<script>alert(1)</script>",
            "A",
            "!!!???",
            "   ",
        ]
        for bad_name in invalid_names:
            with self.assertRaises(ValueError, msg=f"Should reject: {bad_name}"):
                validate_name(bad_name)

        valid_names = ["أحمد محمد", "John Doe", "سارة خالد عبد الله", "Fatima Al-Zahra"]
        for good_name in valid_names:
            clean = validate_name(good_name)
            self.assertTrue(len(clean) >= 2)

    def test_02_backend_gpa_validation(self):
        """Verify that validate_gpa strictly rejects '3333333' and out-of-range values."""
        invalid_gpas = [
            "3333333",
            "99999999",
            "150%",
            "-5",
            "abc",
            "@#$%",
            "105",
            "<script>",
            "3.75/10",
        ]
        for bad_gpa in invalid_gpas:
            with self.assertRaises(ValueError, msg=f"Should reject: {bad_gpa}"):
                validate_gpa(bad_gpa)

        valid_gpas = ["3.75", "3.75/4", "4.5/5", "85.5%", "92%", "3.9"]
        for good_gpa in valid_gpas:
            result = validate_gpa(good_gpa)
            self.assertTrue(bool(result))

    def test_03_api_subscribe_rejects_garbage_inputs(self):
        """Verify /api/subscribe returns 400 or 422 when fed screenshot garbage data."""
        # 1. Invalid Name
        res1 = self.client.post("/api/subscribe", json={
            "email": "student.valid@example.com",
            "full_name": "@!@#$$@#@!,,,,,",
            "degree": "Undergraduate (Bachelor's)",
            "majors": ["Computer Science & IT"],
            "gpa": "3.8",
            "country": "Palestine"
        })
        self.assertIn(res1.status_code, [400, 422], f"Status: {res1.status_code}, Body: {res1.text}")

        # 2. Invalid GPA ('3333333')
        res2 = self.client.post("/api/subscribe", json={
            "email": "student.valid@example.com",
            "full_name": "أحمد محمود",
            "degree": "Undergraduate (Bachelor's)",
            "majors": ["Computer Science & IT"],
            "gpa": "3333333",
            "country": "Palestine"
        })
        self.assertIn(res2.status_code, [400, 422], f"Status: {res2.status_code}, Body: {res2.text}")

    def test_04_html_frontend_sanitization_and_guards_present(self):
        """Verify that web/templates/index.html includes all real-time sanitizers, error containers, and navigation guards."""
        with open("web/templates/index.html", "r", encoding="utf-8") as f:
            html = f.read()

        # Step 1 input sanitizers and handlers
        self.assertIn('id="fullName"', html)
        self.assertIn('sanitizeFullNameInput(this)', html)
        self.assertIn('id="fullNameError"', html)

        self.assertIn('id="gpaInput"', html)
        self.assertIn('sanitizeGpaInput(this)', html)
        self.assertIn('id="gpaError"', html)

        self.assertIn('id="institutionInput"', html)
        self.assertIn('sanitizeInstitutionInput(this)', html)
        self.assertIn('id="institutionError"', html)

        # Step 2 & 4 error containers
        self.assertIn('id="customMajorError"', html)
        self.assertIn('id="emailError"', html)

        # Strict JS functions
        self.assertIn('function isValidFullName', html)
        self.assertIn('function isValidGpa', html)
        self.assertIn('function isValidInstitution', html)
        self.assertIn('function isValidEmail', html)
        self.assertIn('function validateStep', html)
        self.assertIn('function validateField', html)
        self.assertIn('function goToWizardStep', html)

        # Ensure updateCompletenessMeter only awards points for valid fields
        self.assertIn('if (isValidFullName(name)) score += 25;', html)
        self.assertIn('if (isValidGpa(gpa)) score += 25;', html)

        # Ensure calculateInstantProbability checks isValidGpa
        self.assertIn('if (!isValidGpa(gpa))', html)


if __name__ == "__main__":
    unittest.main()
