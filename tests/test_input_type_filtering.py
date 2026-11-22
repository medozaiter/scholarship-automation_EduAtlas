import unittest
from services.security_utils import (
    validate_name,
    validate_full_name,
    validate_city,
    validate_country,
    validate_field_of_study,
    validate_bio,
    validate_username,
    validate_gpa,
    validate_age,
    validate_graduation_year,
    validate_phone_number
)


class TestInputTypeFiltering(unittest.TestCase):
    """
    Dedicated test suite ensuring all inputs strictly enforce their respective data types,
    and text fields strictly forbid numbers, injection characters, and special symbols.
    """

    # 1. Full Name: Text Only (Arabic/English letters & spaces)
    def test_name_forbids_numbers_and_injection(self):
        # The user's exact test input from screenshot
        with self.assertRaises(ValueError):
            validate_name("'/ ,.....##$#!@156181", is_required=True)

        # Other numbers and symbol injection attempts
        for invalid in ["John123", "أحمد123", "User#404", "<script>alert(1)</script>", "123456", "محمد @@@"]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_name(invalid, is_required=True)

    def test_name_accepts_clean_text(self):
        valid_cases = ["أحمد محمد", "مصطفى زعيتر", "Sara Connor", "John Doe", "نور الدين عبد الله"]
        for val in valid_cases:
            res = validate_name(val, is_required=True)
            self.assertTrue(len(res) >= 2)

    # 2. City: Text Only (Letters & spaces only, NO numbers, NO symbols)
    def test_city_forbids_numbers_and_injection(self):
        # The user's exact test input from screenshot
        with self.assertRaises(ValueError):
            validate_city("#!$@%^!##,,,,48418", is_required=True)

        for invalid in ["Gaza123", "غزة 2026", "City#1", "<script>", "12345", "غزة/الرمال", "Ramallah!"]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_city(invalid, is_required=True)

    def test_city_accepts_clean_text(self):
        for city in ["غزة", "رام الله", "القدس", "خانيونس", "نابلس", "Jerusalem", "Cairo", "Amman"]:
            res = validate_city(city, is_required=True)
            self.assertTrue(len(res) >= 2)

    # 3. Country: Valid Catalogue / Text Only (NO numbers, NO symbols)
    def test_country_forbids_symbols_and_numbers(self):
        # The user's exact test input from screenshot
        with self.assertRaises(ValueError):
            validate_country(r"\#:xi.", is_required=True)

        for invalid in ["Palestine123", "12345", "@@@@", "<script>", "Palestine#1", "Westeros"]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_country(invalid, is_required=True)

    def test_country_accepts_valid(self):
        for c in ["Palestine", "فلسطين", "الأردن", "Jordan", "Egypt", "Germany"]:
            res = validate_country(c, is_required=True)
            self.assertTrue(len(res) >= 2)

    # 4. Username: Lowercase English Alphanumeric + _ - .
    def test_username_forbids_arabic_punctuation_and_injection(self):
        # The user's exact test input from screenshot
        with self.assertRaises(ValueError):
            validate_username("؟6448؟؟؟؟.,؟&%^$$#@")

        for invalid in ["user space", "user@handle", "<script>", "ahmed!#", "محمد"]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_username(invalid)

    def test_username_accepts_valid(self):
        for uname in ["ahmed-cs", "mustafa.z", "student_2026", "sarah123"]:
            res = validate_username(uname)
            self.assertEqual(res, uname.lower())

    # 5. Major: Text only, NO numbers
    def test_major_forbids_numbers_and_injection(self):
        for invalid in ["CS101", "Engineering 2026", "Major#1", "<script>alert(1)</script>", "1234"]:
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_field_of_study(invalid, is_required=True)

    def test_major_accepts_clean_text(self):
        for major in ["Software Engineering", "هندسة البرمجيات", "طب بشري", "Computer Science", "علوم الحاسوب"]:
            res = validate_field_of_study(major, is_required=True)
            self.assertTrue(len(res) >= 2)

    # 6. Bio: Rejects script injection and sanitizes dangerous characters
    def test_bio_rejects_script_injection(self):
        with self.assertRaises(ValueError):
            validate_bio("<script>alert(1)</script>", max_length=600)

    def test_bio_sanitizes_injection_quotes(self):
        raw = "طالب شغوف 'بالهندسة' ومشاريع البرمجة \"الذكية\""
        clean = validate_bio(raw, max_length=600)
        self.assertNotIn("'", clean)
        self.assertNotIn('"', clean)
        self.assertIn("طالب شغوف", clean)


if __name__ == '__main__':
    unittest.main()
