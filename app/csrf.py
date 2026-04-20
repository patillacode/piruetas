import hashlib
import hmac as _hmac
import secrets

from fastapi import Form, HTTPException, Request

from app.auth import SESSION_COOKIE
from app.settings import get_settings

LOGIN_CSRF_COOKIE = "piruetas_login_csrf"
LOGIN_CSRF_MAX_AGE = 60 * 30  # 30 minutes


def generate_login_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def validate_login_csrf(submitted: str, cookie_value: str) -> bool:
    if not submitted or not cookie_value:
        return False
    return _hmac.compare_digest(submitted, cookie_value)


def generate_csrf_token(session_token: str) -> str:
    settings = get_settings()
    return _hmac.new(
        settings.secret_key.encode(),
        session_token.encode(),
        hashlib.sha256,
    ).hexdigest()


def validate_csrf_token(submitted: str, session_token: str) -> bool:
    expected = generate_csrf_token(session_token)
    return _hmac.compare_digest(submitted, expected)


async def require_csrf(request: Request, csrf_token: str = Form("")):
    session_token = request.cookies.get(SESSION_COOKIE, "")
    if not session_token or not validate_csrf_token(csrf_token, session_token):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
