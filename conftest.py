import os

# Default pytest execution to development mode so tests can run
# without requiring a live external PostgreSQL instance or Google reCAPTCHA server.
# Production audit tests explicitly set ENVIRONMENT="production" to test fail-closed behavior.
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SECRET_KEY", "pytest-test-environment-secret-key-32-chars-long")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:8000")
