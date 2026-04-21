from urllib.parse import urlparse

import bcrypt
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.auth import SESSION_COOKIE, SESSION_MAX_AGE, make_session_token
from app.csrf import (
    LOGIN_CSRF_COOKIE,
    LOGIN_CSRF_MAX_AGE,
    generate_login_csrf_token,
    require_csrf,
    validate_login_csrf,
)
from app.database import get_session
from app.dependencies import get_current_user_optional
from app.models import User
from app.rate_limit import clear_attempts, is_rate_limited, record_failed_attempt
from app.settings import get_settings
from app.templates_config import ctx, templates

router = APIRouter()


def _get_client_ip(request: Request, trust_proxy: bool) -> str:
    if trust_proxy:
        forwarded_for = request.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/login")
async def login_page(request: Request, user=Depends(get_current_user_optional)):
    if user is not None:
        return RedirectResponse(url="/", status_code=302)
    login_csrf_token = generate_login_csrf_token()
    settings = get_settings()
    response = templates.TemplateResponse(
        request, "login.html", ctx(request, error=None, login_csrf_token=login_csrf_token)
    )
    response.set_cookie(
        LOGIN_CSRF_COOKIE,
        login_csrf_token,
        httponly=True,
        samesite="strict",
        secure=settings.secure_cookies,
        max_age=LOGIN_CSRF_MAX_AGE,
    )
    return response


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    login_csrf_token: str = Form(""),
    session: Session = Depends(get_session),
):
    csrf_cookie = request.cookies.get(LOGIN_CSRF_COOKIE, "")
    if not validate_login_csrf(login_csrf_token, csrf_cookie):
        raise HTTPException(status_code=403, detail="CSRF validation failed")

    settings = get_settings()
    ip = _get_client_ip(request, settings.trust_proxy)
    if is_rate_limited(ip):
        new_csrf = generate_login_csrf_token()
        resp = templates.TemplateResponse(
            request,
            "login.html",
            ctx(
                request,
                error="Too many login attempts. Please try again later.",
                login_csrf_token=new_csrf,
            ),
            status_code=429,
        )
        resp.set_cookie(
            LOGIN_CSRF_COOKIE,
            new_csrf,
            httponly=True,
            samesite="strict",
            secure=settings.secure_cookies,
            max_age=LOGIN_CSRF_MAX_AGE,
        )
        return resp
    user = session.exec(select(User).where(User.username == username)).first()
    if user and bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
        clear_attempts(ip)
        token = make_session_token(
            user.id, user.is_admin, user.session_version, settings.secret_key
        )
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            SESSION_COOKIE,
            token,
            httponly=True,
            samesite="lax",
            secure=settings.secure_cookies,
            max_age=SESSION_MAX_AGE,
        )
        response.delete_cookie(LOGIN_CSRF_COOKIE)
        return response
    record_failed_attempt(ip)
    new_csrf = generate_login_csrf_token()
    resp = templates.TemplateResponse(
        request,
        "login.html",
        ctx(request, error="Invalid username or password", login_csrf_token=new_csrf),
        status_code=401,
    )
    resp.set_cookie(
        LOGIN_CSRF_COOKIE,
        new_csrf,
        httponly=True,
        samesite="strict",
        secure=settings.secure_cookies,
        max_age=LOGIN_CSRF_MAX_AGE,
    )
    return resp


@router.get("/locale/{lang}")
async def set_locale(lang: str, request: Request):
    referer = request.headers.get("referer", "/")
    safe_path = urlparse(referer).path or "/"
    response = RedirectResponse(url=safe_path, status_code=302)
    if lang in ("en", "es"):
        response.set_cookie("piruetas_locale", lang, max_age=365 * 24 * 3600, samesite="lax")
    return response


@router.post("/logout")
async def logout(_csrf=Depends(require_csrf)):
    settings = get_settings()
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
    )
    return response
