# ==============================================================================
# EduAtlas / ScholarPilot AI - Production Container Image
# ==============================================================================
# Security Hardening & Packaging Standards:
# - Minimal base image (python:3.11-slim)
# - Non-root container execution (UID/GID 1000)
# - Strict allowlist copying (No runtime data, secrets, dev tools, or logs)
# - Container healthcheck endpoint configured (/healthz)
# - Safe defaults: PYTHONDONTWRITEBYTECODE=1, PYTHONUNBUFFERED=1
# ==============================================================================

FROM python:3.11-slim

WORKDIR /app

# Install minimal system utilities & clear apt cache in single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Optimize layer caching: Install Python dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Non-root user setup (UID 1000 for least-privilege & Hugging Face / k8s compatibility)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ALLOWLIST APPROACH: Copy ONLY verified production application code & seed data
COPY --chown=user:user services/ ./services/
COPY --chown=user:user web/ ./web/
COPY --chown=user:user data/live_scholarships.json ./data/live_scholarships.json
COPY --chown=user:user dispatch_weekly_subscribers.py ./

# Ensure data and upload directories exist and are owned by non-root user
# Purge any stray upload files as defense-in-depth against builder edge cases
RUN mkdir -p /app/data /app/web/static/uploads/avatars /app/web/static/uploads/covers && \
    rm -rf /app/web/static/uploads/avatars/* /app/web/static/uploads/covers/* && \
    touch /app/web/static/uploads/avatars/.gitkeep /app/web/static/uploads/covers/.gitkeep && \
    chown -R user:user /app/data /app/web/static/uploads

USER user

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-7860}/healthz || exit 1

CMD ["sh", "-c", "uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-7860} --proxy-headers"]
