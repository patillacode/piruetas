import bcrypt
from fastapi import APIRouter, Depends, Form, Request
from sqlmodel import Session

from app.auth import SESSION_COOKIE, SESSION_MAX_AGE, make_session_token
from app.csrf import require_csrf
from app.database import get_session
from app.dependencies import get_current_user
from app.models import User
from app.settings import get_settings
from app.templates_config import ctx, templates

router = APIRouter(prefix="/account")


@router.get("")
async def account_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(request, "account.html", ctx(request, user=user, error=None, success=None))


@router.post("/password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    _csrf=Depends(require_csrf),
):
    def render(error=None, success=None):
        return templates.TemplateResponse(
            request, "account.html", ctx(request, user=user, error=error, success=success),
            status_code=400 if error else 200,
        )

    if not bcrypt.checkpw(current_password.encode(), user.hashed_password.encode()):
        return render(error="Current password is incorrect.")
    if len(new_password) < 8:
        return render(error="New password must be at least 8 characters.")
    if new_password != confirm_password:
        return render(error="Passwords do not match.")

    settings = get_settings()
    db_user = session.get(User, user.id)
    assert db_user is not None
    db_user.hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    db_user.session_version += 1
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    new_token = make_session_token(db_user.id, db_user.is_admin, db_user.session_version, settings.secret_key)
    response = render(success="Password changed successfully.")
    response.set_cookie(
        SESSION_COOKIE,
        new_token,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
        max_age=SESSION_MAX_AGE,
    )
    return response
