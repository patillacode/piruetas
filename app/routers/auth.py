import bcrypt
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.auth import SESSION_COOKIE, SESSION_MAX_AGE, make_session_token
from app.database import get_session
from app.dependencies import get_current_user_optional
from app.models import User
from app.settings import get_settings
from app.templates_config import ctx, templates

router = APIRouter()


@router.get("/login")
async def login_page(request: Request, user=Depends(get_current_user_optional)):
    if user is not None:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(request, "login.html", ctx(request, error=None))


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    settings = get_settings()
    user = session.exec(select(User).where(User.username == username)).first()
    if user and bcrypt.checkpw(password.encode(), user.hashed_password.encode()):
        token = make_session_token(user.id, user.is_admin, settings.secret_key)
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            SESSION_COOKIE,
            token,
            httponly=True,
            samesite="lax",
            secure=settings.secure_cookies,
            max_age=SESSION_MAX_AGE,
        )
        return response
    return templates.TemplateResponse(
        request,
        "login.html",
        ctx(request, error="Invalid username or password"),
        status_code=401,
    )


@router.get("/locale/{lang}")
async def set_locale(lang: str, request: Request):
    referer = request.headers.get("referer", "/")
    response = RedirectResponse(url=referer, status_code=302)
    if lang in ("en", "es"):
        response.set_cookie("piruetas_locale", lang, max_age=365 * 24 * 3600, samesite="lax")
    return response


@router.post("/logout")
async def logout():
    settings = get_settings()
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
    )
    return response
