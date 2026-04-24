import calendar
import io
import json
import re
import zipfile
from datetime import date
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

import bcrypt
import markdownify  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import JSONResponse, Response
from sqlmodel import Session, col, select

from app.auth import SESSION_COOKIE, SESSION_MAX_AGE, make_session_token
from app.csrf import require_csrf
from app.database import get_session
from app.dependencies import get_current_user
from app.i18n import MONTH_NAMES, TRANSLATIONS, get_locale, get_month_names
from app.models import Entry, Image, User
from app.settings import get_settings
from app.templates_config import ctx, templates

router = APIRouter(prefix="/account")


@router.get("")
async def account_page(request: Request, user: User = Depends(get_current_user)):
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
        ),
    )


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


def _get_entries_for_scope(
    session: Session,
    user_id: int,
    scope: str,
    year: int | None,
    month: int | None,
    day_str: str | None,
) -> list[Entry]:
    stmt = select(Entry).where(Entry.user_id == user_id)
    if scope == "year" and year:
        stmt = stmt.where(
            col(Entry.date) >= date(year, 1, 1),
            col(Entry.date) <= date(year, 12, 31),
        )
    elif scope == "month" and year and month:
        last_day = calendar.monthrange(year, month)[1]
        stmt = stmt.where(
            col(Entry.date) >= date(year, month, 1),
            col(Entry.date) <= date(year, month, last_day),
        )
    elif scope == "day" and day_str:
        d = date.fromisoformat(day_str)
        stmt = stmt.where(col(Entry.date) == d)
    return list(session.exec(stmt.order_by(col(Entry.date))).all())


def _scope_label(
    scope: str, year: int | None, month: int | None, day_str: str | None, locale: str = "en"
) -> str:
    names = MONTH_NAMES.get(locale, MONTH_NAMES["en"])
    t = TRANSLATIONS.get(locale, TRANSLATIONS["en"])
    if scope == "year" and year:
        return str(year)
    if scope == "month" and year and month:
        return f"{names[month - 1]} {year}"
    if scope == "day" and day_str:
        d = date.fromisoformat(day_str)
        return f"{names[d.month - 1]} {d.day}, {d.year}"
    return t.get("scope_all", "All entries")


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def _strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html)
    return unescape(s.get_text())


def _rewrite_html_srcs(content: str) -> str:
    return re.sub(r'src="/uploads/\d+/([^"]+)"', r'src="images/\1"', content)


def _rewrite_md_imgs(md: str) -> str:
    return re.sub(r"!\[([^\]]*)\]\(/uploads/\d+/([^)]+)\)", r"![\1](images/\2)", md)


def _build_html_export(content: str, entry_date: date) -> str:
    day_str = entry_date.strftime("%A")
    month_str = entry_date.strftime("%B")
    date_heading = f"{day_str} · {month_str} {entry_date.day}, {entry_date.year}"
    html_content = _rewrite_html_srcs(content)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{date_heading}</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; }}
:root {{
    --bg: #faf8f5;
    --text: #1c1917;
    --accent: #b5735a;
    --muted: #9e9189;
}}
@media (prefers-color-scheme: dark) {{
    :root {{
        --bg: #18150f;
        --text: #f2ede3;
        --accent: #c4856a;
        --muted: #a89e93;
    }}
}}
body {{
    background: var(--bg);
    color: var(--text);
    font-family: Georgia, serif;
    font-size: 1.0625rem;
    line-height: 1.85;
    margin: 0;
    padding: 2rem 1.5rem 4rem;
}}
.entry-wrap {{
    max-width: 680px;
    margin: 0 auto;
}}
.entry-date {{
    font-family: system-ui, sans-serif;
    font-size: 0.875rem;
    color: var(--muted);
    margin-bottom: 2rem;
    letter-spacing: 0.01em;
}}
p {{ margin: 0 0 0.875em; }}
p:last-child {{ margin-bottom: 0; }}
strong {{ font-weight: 700; }}
em {{ font-style: italic; }}
a {{ color: var(--accent); }}
img {{
    max-width: 100%;
    border-radius: 4px;
    margin: 0.5em 0;
    display: block;
}}
</style>
</head>
<body>
<div class="entry-wrap">
<p class="entry-date">{date_heading}</p>
{html_content}
</div>
</body>
</html>"""


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
    entries = _get_entries_for_scope(session, user.id, scope, year, month, day)
    label = _scope_label(scope, year, month, day, locale=get_locale(request))

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
    entries = _get_entries_for_scope(session, user.id, scope, year, month, day)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for entry in entries:
            d = entry.date
            day_folder = f"{user.username}-piruetas/{d.year}/{d.month:02d}/{d.isoformat()}/"
            images = list(session.exec(select(Image).where(Image.entry_id == entry.id)).all())
            image_filenames = [img.filename for img in images]

            plain_text = _strip_html(entry.content)
            md_raw = markdownify.markdownify(entry.content, heading_style="ATX")
            md_text = _rewrite_md_imgs(md_raw)

            if bundle == "text":
                txt_header = f"Date: {d.isoformat()}\nWords: {entry.word_count}\n\n"
                zf.writestr(day_folder + "entry.txt", txt_header + plain_text)

                zf.writestr(day_folder + "entry.html", _build_html_export(entry.content, d))

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
    entries = _get_entries_for_scope(session, user.id, scope, year, month, day)
    label = _scope_label(scope, year, month, day, locale=get_locale(request))
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
    entries = _get_entries_for_scope(session, user.id, scope, year, month, day)
    for entry in entries:
        images = list(session.exec(select(Image).where(Image.entry_id == entry.id)).all())
        for img in images:
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
        return templates.TemplateResponse(
            request,
            "account/security.html",
            ctx(request, user=user, error=error, success=success, active_tab="security", nav_section="account"),
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
