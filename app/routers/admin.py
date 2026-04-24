import re
import shutil
from pathlib import Path

import bcrypt
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.csrf import require_csrf
from app.database import get_session
from app.dependencies import require_admin
from app.models import Entry, Image, User
from app.settings import get_settings
from app.tasks import get_tasks, run_cleanup_images, run_vacuum_db
from app.templates_config import ctx, templates

router = APIRouter(prefix="/admin")


@router.get("/")
async def admin_users(
    request: Request,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
):
    users = session.exec(select(User).order_by(User.created_at)).all()
    error = request.query_params.get("error")
    return templates.TemplateResponse(
        request, "admin/users.html", ctx(request, users=users, user=current_admin, error=error, nav_section="admin")
    )


@router.get("/users/new")
async def create_user_form(
    request: Request,
    current_admin: User = Depends(require_admin),
):
    return templates.TemplateResponse(
        request, "admin/create_user.html", ctx(request, error=None, username=None)
    )


@router.post("/users/new")
async def create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
    _csrf=Depends(require_csrf),
):
    error = None
    if not re.match(r"^[a-zA-Z0-9_]{3,32}$", username):
        error = "Username must be 3-32 characters: letters, numbers, underscore only."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    else:
        existing = session.exec(select(User).where(User.username == username)).first()
        if existing:
            error = "Username already taken."

    if error:
        return templates.TemplateResponse(
            request, "admin/create_user.html", ctx(request, error=error, username=username)
        )

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(username=username, hashed_password=hashed, is_admin=False)
    session.add(user)
    session.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/users/{user_id}/delete")
async def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
    _csrf=Depends(require_csrf),
):
    if user_id == current_admin.id:
        return RedirectResponse("/admin", status_code=303)

    user = session.get(User, user_id)
    if not user:
        return RedirectResponse("/admin", status_code=303)

    settings = get_settings()
    uploads_dir = Path(settings.data_dir) / "uploads" / str(user.id)
    try:
        if uploads_dir.exists():
            shutil.rmtree(uploads_dir)
    except Exception:
        pass

    images = session.exec(select(Image).where(Image.user_id == user_id)).all()
    for image in images:
        session.delete(image)

    entries = session.exec(select(Entry).where(Entry.user_id == user_id)).all()
    for entry in entries:
        session.delete(entry)

    session.delete(user)
    session.commit()
    return RedirectResponse("/admin", status_code=303)


@router.get("/tasks")
async def admin_tasks(
    request: Request,
    current_admin: User = Depends(require_admin),
):
    return templates.TemplateResponse(
        request, "admin/tasks.html", ctx(request, user=current_admin, tasks=get_tasks(), nav_section="admin")
    )


@router.post("/tasks/cleanup-images/run")
async def run_task_cleanup_images(
    request: Request,
    current_admin: User = Depends(require_admin),
    _csrf=Depends(require_csrf),
):
    settings = get_settings()
    run_cleanup_images(settings.data_dir)
    return RedirectResponse("/admin/tasks", status_code=303)


@router.post("/tasks/vacuum-db/run")
async def run_task_vacuum_db(
    request: Request,
    current_admin: User = Depends(require_admin),
    _csrf=Depends(require_csrf),
):
    run_vacuum_db()
    return RedirectResponse("/admin/tasks", status_code=303)


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    new_password: str = Form(...),
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
    _csrf=Depends(require_csrf),
):
    if len(new_password) < 8:
        return RedirectResponse(
            "/admin?error=Password+must+be+at+least+8+characters",
            status_code=303,
        )

    user = session.get(User, user_id)
    if not user:
        return RedirectResponse("/admin", status_code=303)

    user.hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    user.session_version += 1
    session.add(user)
    session.commit()
    return RedirectResponse("/admin", status_code=303)
