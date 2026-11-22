"""
Comprehensive Production Database Audit & Enforcement Test Suite.
Validates:
1. PostgreSQL is strictly mandatory in production mode.
2. Startup fails immediately if DATABASE_URL is missing, malformed, or connection fails.
3. Silent fallback to local JSON is strictly prohibited in production mode.
4. Local JSON storage is preserved ONLY for explicit development mode.
5. Configuration validation and clear audit logging are enforced across all services.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services.db import (
    is_explicit_dev_mode,
    is_production_mode,
    can_use_local_json_storage,
    validate_database_at_startup,
    is_db_available,
    get_user_by_email,
    get_all_scholarships,
    get_notification_history,
)
from services.security_utils import validate_environment_at_startup


class TestProductionDatabaseEnforcement(unittest.TestCase):
    """Test suite for production database audit and mandatory PostgreSQL enforcement."""

    def setUp(self):
        self._orig_env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._orig_env)

    # --------------------------------------------------------------------------
    # 1. Environment Mode Detection Tests
    # --------------------------------------------------------------------------
    def test_mode_detection_production_by_default(self):
        """Unset ENVIRONMENT must default to production mode (strict by default)."""
        os.environ.pop("ENVIRONMENT", None)
        os.environ.pop("APP_ENV", None)
        os.environ.pop("DEV_MODE", None)

        self.assertTrue(is_production_mode(), "Unset ENVIRONMENT should be production mode.")
        self.assertFalse(is_explicit_dev_mode(), "Unset ENVIRONMENT should NOT be explicit dev mode.")
        self.assertFalse(can_use_local_json_storage(), "Local JSON storage must be disabled by default.")

    def test_mode_detection_explicit_production(self):
        """Explicit ENVIRONMENT=production must enforce production mode."""
        os.environ["ENVIRONMENT"] = "production"
        self.assertTrue(is_production_mode())
        self.assertFalse(is_explicit_dev_mode())
        self.assertFalse(can_use_local_json_storage())

        os.environ["ENVIRONMENT"] = "prod"
        self.assertTrue(is_production_mode())
        self.assertFalse(can_use_local_json_storage())

    def test_mode_detection_explicit_development(self):
        """Explicit ENVIRONMENT=development or DEV_MODE=true must allow dev mode."""
        os.environ["ENVIRONMENT"] = "development"
        self.assertFalse(is_production_mode())
        self.assertTrue(is_explicit_dev_mode())
        self.assertTrue(can_use_local_json_storage())

        os.environ["ENVIRONMENT"] = "dev"
        self.assertTrue(can_use_local_json_storage())

        os.environ["ENVIRONMENT"] = "test"
        self.assertTrue(can_use_local_json_storage())

        os.environ["ENVIRONMENT"] = "local"
        self.assertTrue(can_use_local_json_storage())

        os.environ["ENVIRONMENT"] = "production"
        os.environ["DEV_MODE"] = "true"
        self.assertTrue(can_use_local_json_storage())

    # --------------------------------------------------------------------------
    # 2. Production Startup Validation & Failure Tests
    # --------------------------------------------------------------------------
    def test_startup_fails_when_database_url_missing_in_production(self):
        """Production startup must raise RuntimeError when DATABASE_URL is missing."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ.pop("DATABASE_URL", None)

        with self.assertRaises(RuntimeError) as ctx:
            validate_database_at_startup()

        self.assertIn("DATABASE_URL", str(ctx.exception))
        self.assertIn("missing", str(ctx.exception).lower())
        self.assertIn("mandatory in production", str(ctx.exception))

    def test_startup_fails_when_database_url_not_postgresql_in_production(self):
        """Production startup must reject SQLite or non-PostgreSQL URLs."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["DATABASE_URL"] = "sqlite:///data/scholarpilot.db"

        with self.assertRaises(RuntimeError) as ctx:
            validate_database_at_startup()

        self.assertIn("Invalid DATABASE_URL", str(ctx.exception))
        self.assertIn("PostgreSQL connection string", str(ctx.exception))

    def test_startup_fails_when_connection_fails_in_production(self):
        """Production startup must raise RuntimeError if PostgreSQL server is unreachable."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["DATABASE_URL"] = "postgresql://user:pass@127.0.0.1:54321/nonexistent_db"

        with self.assertRaises(RuntimeError) as ctx:
            validate_database_at_startup()

        self.assertIn("PostgreSQL", str(ctx.exception))
        self.assertIn("Startup aborted", str(ctx.exception))

    # --------------------------------------------------------------------------
    # 3. Explicit Development Mode Fallback Tests
    # --------------------------------------------------------------------------
    def test_development_mode_allows_json_storage_when_db_missing(self):
        """Development mode must gracefully allow local JSON storage without raising RuntimeError."""
        os.environ["ENVIRONMENT"] = "development"
        os.environ.pop("DATABASE_URL", None)

        # In dev mode, this returns diagnostic dict rather than raising
        result = validate_database_at_startup()
        self.assertEqual(result.get("mode"), "development")
        self.assertEqual(result.get("status"), "local_json")
        self.assertFalse(result.get("url_configured"))

    def test_development_mode_allows_fallback_when_db_unreachable(self):
        """Development mode must log warning and fall back to local JSON when DB is unreachable."""
        os.environ["ENVIRONMENT"] = "development"
        os.environ["DATABASE_URL"] = "postgresql://user:pass@127.0.0.1:54321/nonexistent_db"

        result = validate_database_at_startup()
        self.assertEqual(result.get("mode"), "development")
        self.assertEqual(result.get("status"), "fallback_json")

    # --------------------------------------------------------------------------
    # 4. Strict Elimination of Silent Local JSON Fallbacks in Production
    # --------------------------------------------------------------------------
    def test_production_prohibits_silent_json_fallback_on_db_queries(self):
        """In production mode, db read functions must NOT read local JSON files when DB is unavailable."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ.pop("DATABASE_URL", None)

        # When DB is unavailable in production mode, functions should return empty/default,
        # never reading from local JSON files.
        user = get_user_by_email("test@example.com")
        self.assertIsNone(user, "Production must not return local JSON user data when DB is down.")

        notifs = get_notification_history()
        self.assertEqual(notifs, [], "Production must not read notification_history.json when DB is down.")

    def test_production_prohibits_silent_json_fallback_in_auth_service(self):
        """In production mode, AuthService._load_users must raise RuntimeError if DB is down."""
        from services.auth_service import AuthService
        os.environ["ENVIRONMENT"] = "production"
        os.environ.pop("DATABASE_URL", None)

        service = AuthService()
        with self.assertRaises(RuntimeError) as ctx:
            service._load_users()

        self.assertIn("PostgreSQL", str(ctx.exception))
        self.assertIn("Local JSON storage is disabled in production", str(ctx.exception))

    def test_production_prohibits_silent_json_fallback_in_subscriber_service(self):
        """In production mode, SubscriberService.get_all must raise RuntimeError if DB is down."""
        from services.subscriber_service import SubscriberService
        os.environ["ENVIRONMENT"] = "production"
        os.environ.pop("DATABASE_URL", None)

        service = SubscriberService()
        with self.assertRaises(RuntimeError) as ctx:
            service.get_all()

        self.assertIn("PostgreSQL", str(ctx.exception))
        self.assertIn("Local JSON storage is disabled in production", str(ctx.exception))

    def test_production_prohibits_silent_json_fallback_in_automation_service(self):
        """In production mode, AutomationService.get_live_scholarships must raise RuntimeError if DB is down."""
        from services.automation_service import AutomationService
        os.environ["ENVIRONMENT"] = "production"
        os.environ.pop("DATABASE_URL", None)

        service = AutomationService()
        with self.assertRaises(RuntimeError) as ctx:
            service.get_live_scholarships()

        self.assertIn("PostgreSQL", str(ctx.exception))
        self.assertIn("Local JSON storage is disabled in production", str(ctx.exception))

    # --------------------------------------------------------------------------
    # 5. Security & Configuration Validation Tests
    # --------------------------------------------------------------------------
    def test_security_utils_flags_missing_database_url_in_production(self):
        """validate_environment_at_startup must record FATAL issue if DATABASE_URL missing in production."""
        os.environ["ENVIRONMENT"] = "production"
        os.environ.pop("DATABASE_URL", None)

        report = validate_environment_at_startup()
        self.assertTrue(report.get("is_production"))
        self.assertFalse(report.get("database_configured"))

        fatal_issues = [issue for issue in report.get("issues", []) if "FATAL" in issue and "DATABASE_URL" in issue]
        self.assertTrue(len(fatal_issues) > 0, "Missing DATABASE_URL in production must be flagged as FATAL.")


if __name__ == "__main__":
    unittest.main()
