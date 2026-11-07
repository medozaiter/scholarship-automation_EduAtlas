import unittest
from fastapi.testclient import TestClient
from web.app import app
from services.security_utils import (
    validate_full_name,
    validate_name,
    validate_university,
    validate_field_of_study,
    validate_gpa,
    validate_country,
    validate_email,
    validate_phone_number,
    validate_bio,
    validate_username,
    detect_gibberish_and_spam,
    security_rate_limiter,
)


class TestEnterpriseValidation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        security_rate_limiter.reset()

    # =========================================================================
    # 1. Full Name Validation Tests
    # =========================================================================
    def test_full_name_rejects_symbols_and_numbers(self):
        invalid_names = [
            "@@@@@",
            "!!!!!!",
            "123456",
            "testtesttesttesttesttest",
            "<svg>",
            "<script>",
            "@!@#$$@#@!,,,,,",
            "   ",
            "",
            "a",
            "John123",
            "User#404",
        ]
        for name in invalid_names:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    validate_full_name(name, is_required=True)

    def test_full_name_accepts_valid_names(self):
        valid_names = [
            ("أحمد محمد", "أحمد محمد"),
            ("مصطفى زعيتر", "مصطفى زعيتر"),
            ("Sara Connor", "Sara Connor"),
            ("John O'Connor", "John O&#x27;Connor"),
            ("Fatima Al-Zahra", "Fatima Al-Zahra"),
            ("نور الدين عبد الله", "نور الدين عبد الله"),
        ]
        for name, expected in valid_names:
            with self.subTest(name=name):
                res = validate_full_name(name, is_required=True)
                self.assertEqual(res, expected)

    # =========================================================================
    # 2. University Name Validation Tests
    # =========================================================================
    def test_university_rejects_symbols_and_numbers_only(self):
        invalid_univs = [
            "%%%%%%",
            "@@@@@@@",
            "99999999999999999999999",
            ",,,,,,,,,,,,,,,",
            "???????",
            "1234",
            "999999999999999999999,,,,,,,,,,,,,,!@#@#@!؟؟؟؟؟",
            "<script>alert(1)</script>",
            "   ",
            "a",
        ]
        for u in invalid_univs:
            with self.subTest(univ=u):
                with self.assertRaises(ValueError):
                    validate_university(u, is_required=True)

    def test_university_accepts_valid_institutions(self):
        valid_univs = [
            "الجامعة الإسلامية بغزة",
            "جامعة النجاح الوطنية",
            "Harvard University",
            "MIT",
            "جامعة القدس (أبو ديس)",
            "University of Oxford",
        ]
        for u in valid_univs:
            with self.subTest(univ=u):
                res = validate_university(u, is_required=True)
                self.assertTrue(len(res) >= 2)

    # =========================================================================
    # 3. GPA Validation Tests
    # =========================================================================
    def test_gpa_rejects_irrational_and_spam_values(self):
        invalid_gpas = [
            "333333",
            "999999",
            "-999",
            "abc",
            "@@@@",
            "120%",
            "0.2",
            "6.0",
            "15",
            "35%",
            "-3.5",
            "10000000000000",
        ]
        for g in invalid_gpas:
            with self.subTest(gpa=g):
                with self.assertRaises(ValueError):
                    validate_gpa(g)

    def test_gpa_accepts_valid_ranges(self):
        test_cases = [
            ("3.75", "3.75/4"),
            ("4.0", "4/4"),
            ("3.8/4", "3.8/4"),
            ("4.5/5", "4.5/5"),
            ("85%", "85%"),
            ("92.5%", "92.5%"),
            ("95", "95%"),
            ("ممتاز", "ممتاز"),
            ("امتياز", "امتياز"),
            ("جيد جدا", "جيد جدا"),
        ]
        for inp, exp in test_cases:
            with self.subTest(gpa=inp):
                res = validate_gpa(inp)
                self.assertEqual(res, exp)

    # =========================================================================
    # 4. Country Validation Tests
    # =========================================================================
    def test_country_rejects_fake_and_malicious(self):
        invalid_countries = [
            "Krypton",
            "FakeCountry",
            "Atlantis",
            "12345",
            "@@@@",
            "<script>",
            "Westeros",
        ]
        for c in invalid_countries:
            with self.subTest(country=c):
                with self.assertRaises(ValueError):
                    validate_country(c, is_required=True)

    def test_country_accepts_valid_catalogue(self):
        valid_cases = [
            ("Palestine", "Palestine"),
            ("فلسطين", "Palestine"),
            ("الأردن", "Jordan"),
            ("Jordan", "Jordan"),
            ("Egypt", "Egypt"),
            ("مصر", "Egypt"),
            ("Germany", "Germany"),
            ("ألمانيا", "Germany"),
            ("United States", "United States"),
            ("فلسطين (Palestine) - أولوية ومنح معفاة 100%", "Palestine"),
        ]
        for inp, exp in valid_cases:
            with self.subTest(country=inp):
                res = validate_country(inp, is_required=True)
                self.assertEqual(res, exp)

    # =========================================================================
    # 5. Field of Study / Major Validation Tests
    # =========================================================================
    def test_major_rejects_injections_and_gibberish(self):
        invalid_majors = [
            "<script>alert(1)</script>",
            "' OR '1'='1",
            "@@@@@",
            "123456",
            "testtesttesttesttesttest",
            "a",
        ]
        for m in invalid_majors:
            with self.subTest(major=m):
                with self.assertRaises(ValueError):
                    validate_field_of_study(m, is_required=True)

    def test_major_accepts_valid_names(self):
        valid_majors = [
            "Computer Science",
            "هندسة البرمجيات",
            "Software Engineering",
            "طب بشري",
            "Civil Engineering",
        ]
        for m in valid_majors:
            with self.subTest(major=m):
                res = validate_field_of_study(m, is_required=True)
                self.assertTrue(len(res) >= 2)

    # =========================================================================
    # 6. Anti-Gibberish and Spam Tests
    # =========================================================================
    def test_gibberish_detector(self):
        self.assertTrue(detect_gibberish_and_spam("aaaaaaa"))
        self.assertTrue(detect_gibberish_and_spam("99999999"))
        self.assertTrue(detect_gibberish_and_spam("!!!!!!!!!"))
        self.assertTrue(detect_gibberish_and_spam("testtesttesttesttesttest"))
        self.assertTrue(detect_gibberish_and_spam("abcabcabc"))

        self.assertFalse(detect_gibberish_and_spam("جامعة القدس المفتوحة"))
        self.assertFalse(detect_gibberish_and_spam("Software Engineering and Artificial Intelligence"))
        self.assertFalse(detect_gibberish_and_spam("طالب متميز في علوم الحاسوب"))

    # =========================================================================
    # 7. Endpoint Backend Validation Enforcement (Client-Bypass Defense)
    # =========================================================================
    def test_register_endpoint_rejects_invalid_inputs(self):
        security_rate_limiter.reset()
        bad_payload = {
            "full_name": "@@@@@",
            "email": "valid.student@example.com",
            "password": "ValidPassword123!",
            "gpa": "333333",
            "university": "%%%%%%",
            "country": "Krypton",
        }
        res = self.client.post("/api/auth/register", json=bad_payload)
        self.assertIn(res.status_code, [400, 422])
        self.assertFalse(res.json().get("success", True))

    def test_subscribe_endpoint_rejects_invalid_inputs(self):
        security_rate_limiter.reset()
        bad_payload = {
            "email": "student@example.com",
            "full_name": "!!!!!!",
            "gpa": "999999",
            "country": "FakeCountry",
            "majors": ["%%%%%%"],
        }
        res = self.client.post("/api/subscribe", json=bad_payload)
        self.assertIn(res.status_code, [400, 422])
        self.assertFalse(res.json().get("success", True))

    def test_contact_form_rejects_gibberish_and_bad_name(self):
        security_rate_limiter.reset()
        bad_payload = {
            "name": "123456",
            "email": "student@example.com",
            "subject": "testtesttesttesttesttest",
            "message": "testtesttesttesttesttest message text",
        }
        res = self.client.post("/api/contact", json=bad_payload)
        self.assertIn(res.status_code, [400, 422])
        self.assertFalse(res.json().get("success", True))


if __name__ == "__main__":
    unittest.main()
