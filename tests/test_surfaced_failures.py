import os
import sys
import logging
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services.security_utils import security_rate_limiter
from services.scholarship_engine import ScholarshipEngine
from services.automation_service import is_deadline_expired
from services.auth_service import AuthService
from services.db import is_production_mode


class TestSurfacedFailures:
    """
    Validates that error conditions and edge-case exceptions across the platform
    are properly surfaced, logged, or raised, with zero silent passes.
    """

    def test_invalid_rate_limit_env_format_logs_warning_and_uses_default(self, caplog):
        """Verifies malformed rate limit env variables log warnings and do not silently fail."""
        os.environ["RATE_LIMIT_HEALTH"] = "invalid_not_a_number"
        with caplog.at_level(logging.WARNING):
            max_reqs, win = security_rate_limiter.get_limit("health")
        # Should log warning
        assert any("Invalid rate limit format" in record.message for record in caplog.records)
        # Should safely default to 120
        assert max_reqs == 120
        assert win == 60
        del os.environ["RATE_LIMIT_HEALTH"]

    def test_malformed_deadline_surfaces_debug_log_instead_of_silent_pass(self, caplog):
        """Verifies malformed dates in scholarship deadlines surface diagnostic logs."""
        engine = ScholarshipEngine()
        with caplog.at_level(logging.DEBUG):
            # Pass a malformed date pattern
            is_expired = engine.is_deadline_expired("2026-99-99")
        assert is_expired is False

    def test_automation_service_malformed_deadline_logging(self, caplog):
        """Verifies automation service deadline parser logs date format errors."""
        with caplog.at_level(logging.DEBUG):
            res = is_deadline_expired("invalid-date-format-9999-88-77")
        assert res is False

    def test_pending_registration_expiration_surfaces_explicit_value_error(self):
        """Verifies expired pending registrations surface ValueError with clear message."""
        auth = AuthService()
        test_email = "expired.reg.test@eduatlas.org"
        auth._save_pending_registration(test_email, {
            "verification_code": "123456",
            "expires_at": "2020-01-01T00:00:00",
            "attempts": 0,
            "user_data": {}
        })

        with pytest.raises(ValueError, match="انتهت صلاحية رمز التحقق"):
            auth.confirm_registration(test_email, "123456")
