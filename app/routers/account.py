import io
import json
import zipfile
from datetime import date
from pathlib import Path

import bcrypt
import markdownify  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from sqlmodel import Session, col, func, select

from app.csrf import require_csrf
from app.database import get_session
from app.dependencies import get_current_user
from app.export import (
    build_html_export,
    get_entries_for_scope,
    rewrite_md_imgs,
    scope_label,
    strip_html,
)
from app.i18n import get_locale, get_month_names
from app.models import Entry, Image, RecoveryCode, User
from app.recovery import create_codes_for_user
from app.recovery_flash import RECOVERY_FLASH_COOKIE, pop_recovery_flash, set_recovery_flash
from app.session_token import SESSION_COOKIE, SESSION_MAX_AGE, make_session_token
from app.settings import get_settings
from app.templates_config import ctx, templates

router = APIRouter(prefix="/account")


def _count_unused_recovery_codes(session: Session, user_id: int) -> int:
    return session.exec(
        select(func.count(RecoveryCode.id)).where(
            RecoveryCode.user_id == user_id,
            RecoveryCode.used == False,  # noqa: E712
        )
    ).one()


@router.get("")
async def account_page(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    assert user.id is not None
    recovery_remaining = _count_unused_recovery_codes(session, user.id)
    return templates.TemplateResponse(
        request,
        "account/security.html",
        ctx(
            request,
            user=user,
            error=None,
            success=None,
            active_tab="security",
            nav_section="account",
            recovery_remaining=recovery_remaining,
        ),
    )


@router.get("/recovery-codes")
async def recovery_codes_page(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    assert user.id is not None
    settings = get_settings()
    if user.username == settings.demo_username:
        return RedirectResponse(url="/account", status_code=302)
    codes = pop_recovery_flash(dict(request.cookies), settings.secret_key)
    remaining = _count_unused_recovery_codes(session, user.id)
    response = templates.TemplateResponse(
        request,
        "account/recovery_codes.html",
        ctx(
            request,
            user=user,
            codes=codes,
            remaining=remaining,
            active_tab="security",
            nav_section="account",
        ),
    )
    response.delete_cookie(RECOVERY_FLASH_COOKIE)
    return response


@router.post("/recovery-codes/regenerate")
async def regenerate_recovery_codes(
    request: Request,
    current_password: str = Form(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    _csrf=Depends(require_csrf),
):
    assert user.id is not None
    settings = get_settings()

    if user.username == settings.demo_username:
        return RedirectResponse(url="/account", status_code=302)

    if not bcrypt.checkpw(current_password.encode(), user.hashed_password.encode()):
        remaining = _count_unused_recovery_codes(session, user.id)
        return templates.TemplateResponse(
            request,
            "account/recovery_codes.html",
            ctx(
                request,
                user=user,
                codes=None,
                remaining=remaining,
                active_tab="security",
                nav_section="account",
                error="Current password is incorrect.",
            ),
            status_code=400,
        )

    plaintext_codes = create_codes_for_user(user.id, session)
    response = RedirectResponse(url="/account/recovery-codes", status_code=302)
    set_recovery_flash(response, plaintext_codes, settings.secret_key, settings.secure_cookies)
    return response


@router.get("/data")
async def data_page(
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    current_year = date.today().year
    first_entry = session.exec(
        select(Entry).where(Entry.user_id == user.id).order_by(col(Entry.date)).limit(1)
    ).first()
    first_year = first_entry.date.year if first_entry else current_year
    months = get_month_names(get_locale(request))
    return templates.TemplateResponse(
        request,
        "account/data.html",
        ctx(
            request,
            user=user,
            active_tab="data",
            first_year=first_year,
            current_year=current_year,
            months=months,
            nav_section="account",
        ),
    )


@router.post("/export/preview")
async def export_preview(
    request: Request,
    scope: str = Form("all"),
    year: int | None = Form(None),
    month: int | None = Form(None),
    day: str | None = Form(None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    _csrf=Depends(require_csrf),
):
    assert user.id is not None
    entries = get_entries_for_scope(session, user.id, scope, year, month, day)
    label = scope_label(scope, year, month, day, locale=get_locale(request))

    params = f"scope={scope}"
    if year:
        params += f"&year={year}"
    if month:
        params += f"&month={month}"
    if day:
        params += f"&day={day}"

    return JSONResponse(
        {
            "count": len(entries),
            "scope_label": label,
            "text_url": f"/account/export/download?bundle=text&{params}",
            "json_url": f"/account/export/download?bundle=json&{params}",
        }
    )


@router.get("/export/download")
async def export_download(
    request: Request,
    bundle: str = Query("text"),
    scope: str = Query("all"),
    year: int | None = Query(None),
    month: int | None = Query(None),
    day: str | None = Query(None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if bundle not in ("text", "json"):
        bundle = "text"
    settings = get_settings()
    assert user.id is not None
    entries = get_entries_for_scope(session, user.id, scope, year, month, day)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for entry in entries:
            d = entry.date
            day_folder = f"{user.username}-piruetas/{d.year}/{d.month:02d}/{d.isoformat()}/"
            images = list(session.exec(select(Image).where(Image.entry_id == entry.id)).all())
            image_filenames = [img.filename for img in images]

            plain_text = strip_html(entry.content)
            md_raw = markdownify.markdownify(entry.content, heading_style="ATX")
            md_text = rewrite_md_imgs(md_raw)

            if bundle == "text":
                txt_header = f"Date: {d.isoformat()}\nWords: {entry.word_count}\n\n"
                zf.writestr(day_folder + "entry.txt", txt_header + plain_text)

                zf.writestr(day_folder + "entry.html", build_html_export(entry.content, d))

                md_header = f"Date: {d.isoformat()}\nWords: {entry.word_count}\n\n"
                zf.writestr(day_folder + "entry.md", md_header + md_text)
            else:
                entry_json = {
                    "date": d.isoformat(),
                    "content_html": entry.content,
                    "content_markdown": md_text,
                    "content_text": plain_text,
                    "word_count": entry.word_count,
                    "created_at": entry.created_at.isoformat(),
                    "updated_at": entry.updated_at.isoformat(),
                    "images": image_filenames,
                }
                zf.writestr(
                    day_folder + "entry.json",
                    json.dumps(entry_json, ensure_ascii=False, indent=2),
                )

            for img in images:
                img_path = Path(settings.data_dir) / "uploads" / str(user.id) / img.filename
                if img_path.exists():
                    zf.write(img_path, day_folder + f"images/{img.filename}")

    filename = f"{user.username}-piruetas-{bundle}.zip"
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/delete/preview")
async def delete_preview(
    request: Request,
    scope: str = Form("all"),
    year: int | None = Form(None),
    month: int | None = Form(None),
    day: str | None = Form(None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    _csrf=Depends(require_csrf),
):
    assert user.id is not None
    entries = get_entries_for_scope(session, user.id, scope, year, month, day)
    label = scope_label(scope, year, month, day, locale=get_locale(request))
    return JSONResponse({"count": len(entries), "scope_label": label})


@router.post("/delete/confirm")
async def delete_confirm(
    request: Request,
    scope: str = Form("all"),
    year: int | None = Form(None),
    month: int | None = Form(None),
    day: str | None = Form(None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
    _csrf=Depends(require_csrf),
):
    assert user.id is not None
    settings = get_settings()
    entries = get_entries_for_scope(session, user.id, scope, year, month, day)
    for entry in entries:
        images = list(session.exec(select(Image).where(Image.entry_id == entry.id)).all())
        for img in images:
            file_path = Path(settings.data_dir) / "uploads" / str(user.id) / img.filename
            file_path.unlink(missing_ok=True)
            session.delete(img)
    session.flush()
    for entry in entries:
        session.delete(entry)
    session.commit()
    return JSONResponse({"deleted": len(entries)})


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
        recovery_remaining = _count_unused_recovery_codes(session, user.id)
        return templates.TemplateResponse(
            request,
            "account/security.html",
            ctx(
                request,
                user=user,
                error=error,
                success=success,
                active_tab="security",
                nav_section="account",
                recovery_remaining=recovery_remaining,
            ),
            status_code=400 if error else 200,
        )

    if user.username == get_settings().demo_username:
        return render(error="Password change is disabled for the demo account.")

    if not bcrypt.checkpw(current_password.encode(), user.hashed_password.encode()):
        return render(error="Current password is incorrect.")
    if len(new_password) < 8:
        return render(error="New password must be at least 8 characters.")
    if new_password != confirm_password:
        return render(error="Passwords do not match.")

    settings = get_settings()
    db_user = session.get(User, user.id)
    assert db_user is not None
    db_user.hashed_password = bcrypt.hashpw(
        new_password.encode(),
        bcrypt.gensalt(),
    ).decode()
    db_user.session_version += 1
    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    new_token = make_session_token(
        db_user.id, db_user.is_admin, db_user.session_version, settings.secret_key
    )
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
