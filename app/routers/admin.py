import logging
import shutil
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy import select as sa_select
from sqlmodel import Session, select

from app.csrf import require_csrf
from app.database import get_session
from app.dependencies import require_admin
from app.models import Entry, Image, User
from app.settings import get_settings
from app.tasks import get_tasks, run_cleanup_images, run_recalculate_storage, run_vacuum_db
from app.templates_config import ctx, templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")


@router.get("/")
async def admin_users(
    request: Request,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
):
    stmt = (
        sa_select(User, func.count(Entry.id).label("entry_count"))
        .outerjoin(Entry, Entry.user_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at)
    )
    rows = session.execute(stmt).all()
    today = date.today()
    user_stats = []
    for user, entry_count in rows:
        days = max((today - user.created_at.date()).days, 1)
        pct_days = round(entry_count / days * 100)
        user_stats.append({"user": user, "entry_count": entry_count, "pct_days": pct_days})
    error = request.query_params.get("error")
    return templates.TemplateResponse(
        request,
        "admin/users.html",
        ctx(request, user_stats=user_stats, user=current_admin, error=error, nav_section="admin"),
    )


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
        logger.exception("Failed to delete uploads directory for user %d", user.id)

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
        request,
        "admin/tasks.html",
        ctx(request, user=current_admin, tasks=get_tasks(), nav_section="admin"),
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


@router.post("/users/{user_id}/set-banner")
async def set_user_banner(
    user_id: int,
    banner_message: str = Form(...),
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
    _csrf=Depends(require_csrf),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if len(banner_message.strip()) > 300:
        raise HTTPException(status_code=400, detail="Banner message exceeds 300 characters")
    user.banner_message = banner_message.strip() or None
    session.add(user)
    session.commit()
    return JSONResponse({"ok": True})


@router.post("/users/{user_id}/clear-banner")
async def clear_user_banner(
    user_id: int,
    session: Session = Depends(get_session),
    current_admin: User = Depends(require_admin),
    _csrf=Depends(require_csrf),
):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.banner_message = None
    session.add(user)
    session.commit()
    return JSONResponse({"ok": True})


@router.post("/tasks/recalculate-storage/run")
async def run_task_recalculate_storage(
    request: Request,
    current_admin: User = Depends(require_admin),
    _csrf=Depends(require_csrf),
):
    settings = get_settings()
    run_recalculate_storage(settings.data_dir)
    return RedirectResponse("/admin/tasks", status_code=303)
