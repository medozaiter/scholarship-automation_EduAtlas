import os
import sys
import logging
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from web.app import app
from services.security_utils import mask_secret, SensitiveDataFilter, create_session_token

client = TestClient(app)


class TestSecretLogSanitization:
    """
    Verification suite for Secret Log Sanitization Remediation:
    - Tests mask_secret output patterns.
    - Tests SensitiveDataFilter scrubbing behavior.
    - Verifies captured logs never leak API keys, Cron secrets, passwords, tokens, or DB credentials.
    """

    def test_mask_secret_helper_behavior(self):
        """Verifies mask_secret adheres to mask specification (abcd********wxyz)."""
        # Long secret
        res = mask_secret("abcd1234efgh5678wxyz")
        assert res == "abcd********wxyz"

        # Another length variant
        res2 = mask_secret("CRON_SUPER_SECRET_TOKEN_9999")
        assert res2.startswith("CRON")
        assert res2.endswith("9999")
        assert "********" in res2

        # Short and boundary inputs
        assert mask_secret("") == ""
        assert mask_secret(None) == ""
        assert mask_secret("1234") == "****"
        assert mask_secret("secret") == "s****t"

    def test_sensitive_data_filter_scrubs_bearer_tokens(self):
        """Verifies SensitiveDataFilter intercepts and masks Bearer authorization tokens."""
        filter_instance = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.DEBUG,
            pathname=__file__,
            lineno=42,
            msg="Request incoming with Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sensitive_token_body.signature1234",
            args=(),
            exc_info=None
        )

        filter_instance.filter(record)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.sensitive_token_body.signature1234" not in record.msg
        assert "Bearer eyJh********1234" in record.msg

    def test_sensitive_data_filter_scrubs_cron_secrets(self):
        """Verifies SensitiveDataFilter intercepts and masks X-Cron-Secret tokens."""
        filter_instance = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.DEBUG,
            pathname=__file__,
            lineno=50,
            msg="Evaluating header X-Cron-Secret: super_secret_cron_pass_9988",
            args=(),
            exc_info=None
        )

        filter_instance.filter(record)
        assert "super_secret_cron_pass_9988" not in record.msg
        assert "X-Cron-Secret: supe********9988" in record.msg

    def test_sensitive_data_filter_scrubs_database_passwords(self):
        """Verifies database URLs containing passwords are masked in logs."""
        filter_instance = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname=__file__,
            lineno=60,
            msg="Database connection timeout: postgresql://admin_user:UltraSecretDbPassword2026!@ep-quiet-db.us-east-2.aws.neon.tech/main_db",
            args=(),
            exc_info=None
        )

        filter_instance.filter(record)
        assert "UltraSecretDbPassword2026!" not in record.msg
        assert "postgresql://admin_user:********@ep-quiet-db" in record.msg

    def test_cron_authentication_never_logs_plaintext_secret(self, caplog):
        """Verifies that executing cron authentication never logs the provided secret in plaintext."""
        raw_secret = "ConfidentialCronSecretToken2026XY"
        os.environ["CRON_SECRET"] = raw_secret

        with caplog.at_level(logging.DEBUG):
            # Unauthorized request with invalid secret
            client.post("/api/cron/trigger-scan", headers={"X-Cron-Secret": "WrongSecret99887766"})
            # Authorized request with valid secret
            client.post("/api/cron/trigger-scan", headers={"X-Cron-Secret": raw_secret})

        captured = caplog.text
        assert raw_secret not in captured, "Plaintext CRON_SECRET must never appear in logs"
        assert "WrongSecret99887766" not in captured, "Provided secret attempt must never appear in plaintext"

    def test_user_authentication_never_logs_passwords(self, caplog):
        """Verifies user login attempts never leak user passwords to log streams."""
        test_password = "SuperP@ssw0rd!DoNotLogMe"
        with caplog.at_level(logging.DEBUG):
            client.post(
                "/api/auth/login",
                json={
                    "email": "security.student@eduatlas.org",
                    "password": test_password
                }
            )

        captured = caplog.text
        assert test_password not in captured, "Plaintext password must NEVER appear in captured logs"

    def test_bearer_token_requests_never_leak_token_to_logs(self, caplog):
        """Verifies bearer token authenticated requests do not expose token in logs."""
        token = create_session_token("security.tester@eduatlas.org", role="student")
        with caplog.at_level(logging.DEBUG):
            client.get(
                "/api/user/profile",
                headers={"Authorization": f"Bearer {token}"}
            )

        captured = caplog.text
        assert token not in captured, "Plaintext Bearer token must never appear in logs"
