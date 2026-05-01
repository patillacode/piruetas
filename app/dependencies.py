from fastapi import Depends, HTTPException, Request
from sqlmodel import Session
from starlette.status import HTTP_302_FOUND

from app.database import get_session
from app.models import User
from app.session_token import SESSION_COOKIE, parse_session_token
from app.settings import get_settings


async def get_current_user(request: Request, session: Session = Depends(get_session)) -> User:
    settings = get_settings()
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=HTTP_302_FOUND, headers={"Location": "/login"})

    result = parse_session_token(token, settings.secret_key)
    if result is None:
        raise HTTPException(status_code=HTTP_302_FOUND, headers={"Location": "/login"})

    user_id, _, token_version = result
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=HTTP_302_FOUND, headers={"Location": "/login"})

    if user.session_version != token_version:
        raise HTTPException(status_code=HTTP_302_FOUND, headers={"Location": "/login"})

    return user


async def get_current_user_optional(
    request: Request, session: Session = Depends(get_session)
) -> User | None:
    try:
        return await get_current_user(request, session)
    except HTTPException:
        return None


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user
