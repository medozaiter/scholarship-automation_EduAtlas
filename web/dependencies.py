"""
Common FastAPI dependencies and authentication extractors for ScholarPilot AI.
"""

import os
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import Response

from services.auth_service import AuthService
from services.security_utils import (
    generate_csrf_token,
    verify_cron_secret
)

auth_service = AuthService()

def get_authenticated_user(request: Request) -> Optional[Dict[str, Any]]:
    """Extracts bearer token or session cookie and authenticates student."""
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1].strip()
    if not token:
        token = request.cookies.get("session_token") or request.cookies.get("minha_token")
    if token:
        return auth_service.authenticate_token(token)
    return None

def require_authenticated_user(request: Request) -> Dict[str, Any]:
    """Dependency that ensures user is authenticated, otherwise raises 401."""
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="يجب تسجيل الدخول أولاً.")
    return user

def require_admin_user(request: Request) -> Dict[str, Any]:
    """Dependency that ensures user is authenticated and is an admin."""
    user = require_authenticated_user(request)
    if (user.get("role") or "").lower() != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="هذه العملية تتطلب صلاحيات المسؤول.")
    return user

def require_cron_auth(request: Request):
    """
    Protects webhook and cron automation endpoints strictly via X-Cron-Secret HTTP header.
    Query parameter credentials (?secret= or ?cron_secret=) are strictly forbidden to prevent
    credential leakage in access logs, proxies, and URLs.
    """
    if "secret" in request.query_params or "cron_secret" in request.query_params:
        raise HTTPException(
            status_code=403,
            detail="غير مصرح: تمرير مفاتيح الأتمتة والجدولة عبر معاملات الاستعلام (query parameters) محظور أمنياً. يجب استخدام ترويسة X-Cron-Secret حصراً."
        )

    cron_header = (
        request.headers.get("X-Cron-Secret")
        or request.headers.get("x-cron-secret")
    )
    if cron_header and verify_cron_secret(cron_header):
        return True

    # Also permit authenticated admin accounts
    user = get_authenticated_user(request)
    if user and (user.get("role") or "").lower() == "admin":
        return True

    raise HTTPException(
        status_code=403,
        detail="غير مصرح: مفتاح Cron غير صالح أو غير موجود (X-Cron-Secret required)."
    )

def _set_auth_cookies(response: Response, request: Request, token: str, refresh_tok: Optional[str] = None) -> str:
    csrf_tok = generate_csrf_token()
    is_secure = (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto") == "https"
        or os.getenv("ENVIRONMENT", "").lower() in ("production", "prod")
        or os.getenv("SECURE_COOKIES", "false").lower() == "true"
    )
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=1800,
        httponly=True,
        samesite="lax",
        secure=is_secure
    )
    response.set_cookie(
        key="minha_token",
        value=token,
        max_age=1800,
        httponly=True,
        samesite="lax",
        secure=is_secure
    )
    if refresh_tok:
        response.set_cookie(
            key="refresh_token",
            value=refresh_tok,
            max_age=7 * 86400,
            httponly=True,
            samesite="lax",
            secure=is_secure
        )
    response.set_cookie(
        key="csrf_token",
        value=csrf_tok,
        max_age=7 * 86400,
        httponly=False,
        samesite="lax",
        secure=is_secure
    )
    return csrf_tok

def _clear_auth_cookies(response: Response):
    response.delete_cookie("session_token")
    response.delete_cookie("minha_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("csrf_token")
