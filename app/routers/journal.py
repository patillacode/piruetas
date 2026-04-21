import datetime
import re
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, select
from starlette.requests import Request

from app.database import get_session
from app.dependencies import get_current_user
from app.models import Entry, Image, User
from app.settings import get_settings
from app.templates_config import ctx, templates

router = APIRouter()


def compute_word_count(html_content: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html_content)
    return len(text.split())


def _link_images_to_entry(session: Session, content: str, user_id: int, entry_id: int) -> None:
    filenames = re.findall(r"/uploads/\d+/([a-f0-9]+\.\w+)", content)
    for filename in filenames:
        stmt = select(Image).where(Image.filename == filename, Image.user_id == user_id)
        image = session.execute(stmt).scalars().first()
        if image and image.entry_id != entry_id:
            image.entry_id = entry_id
            session.add(image)


class EntrySaveRequest(BaseModel):
    content: str


@router.get("/journal/{year}/{month}/{day}")
async def journal_day(
    year: int,
    month: int,
    day: int,
    request: Request,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        date = datetime.date(year, month, day)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid date")

    stmt = select(Entry).where(Entry.user_id == user.id, Entry.date == date)
    entry = session.execute(stmt).scalars().first()

    return templates.TemplateResponse(
        request, "journal.html", ctx(request, entry=entry, date=date, user=user)
    )


@router.post("/journal/{year}/{month}/{day}")
async def journal_save(
    year: int,
    month: int,
    day: int,
    body: EntrySaveRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        date = datetime.date(year, month, day)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid date")

    stmt = select(Entry).where(Entry.user_id == user.id, Entry.date == date)
    entry = session.execute(stmt).scalars().first()

    now = datetime.datetime.now(datetime.UTC)

    wc = compute_word_count(body.content)

    if entry:
        entry.content = body.content
        entry.word_count = wc
        entry.updated_at = now
    else:
        entry = Entry(
            user_id=user.id,
            date=date,
            content=body.content,
            word_count=wc,
            created_at=now,
            updated_at=now,
        )
        session.add(entry)

    session.commit()
    session.refresh(entry)

    _link_images_to_entry(session, body.content, user.id, entry.id)
    session.commit()

    return JSONResponse({"saved": True, "updated_at": entry.updated_at.isoformat()})


@router.delete("/journal/{year}/{month}/{day}")
async def journal_delete(
    year: int,
    month: int,
    day: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        date = datetime.date(year, month, day)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid date")

    stmt = select(Entry).where(Entry.user_id == user.id, Entry.date == date)
    entry = session.execute(stmt).scalars().first()

    if entry:
        settings = get_settings()
        images = session.execute(select(Image).where(Image.entry_id == entry.id)).scalars().all()
        for image in images:
            file_path = Path(settings.data_dir) / "uploads" / str(user.id) / image.filename
            file_path.unlink(missing_ok=True)
            session.delete(image)
        session.delete(entry)
        session.commit()

    return JSONResponse({"deleted": True})


@router.get("/journal/stats")
async def journal_stats(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    today = datetime.date.today()
    month_start = datetime.date(today.year, today.month, 1)
    next_month_start = (
        datetime.date(today.year, today.month + 1, 1)
        if today.month < 12
        else datetime.date(today.year + 1, 1, 1)
    )

    month_stmt = select(Entry).where(
        Entry.user_id == user.id,
        Entry.date >= month_start,
        Entry.date < next_month_start,
    )
    month_entries = session.execute(month_stmt).scalars().all()
    month_count = len(month_entries)
    month_words = sum(e.word_count or 0 for e in month_entries)

    all_entries = session.execute(select(Entry).where(Entry.user_id == user.id)).scalars().all()
    entry_dates = {e.date for e in all_entries}
    streak = 0
    current = today
    while current in entry_dates:
        streak += 1
        current -= datetime.timedelta(days=1)

    return JSONResponse(
        {
            "streak": streak,
            "month_entries": month_count,
            "month_words": month_words,
        }
    )


@router.get("/calendar/{year}/{month}")
async def calendar_month(
    year: int,
    month: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        datetime.date(year, month, 1)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid year/month")

    next_month_start = (
        datetime.date(year, month + 1, 1) if month < 12 else datetime.date(year + 1, 1, 1)
    )
    stmt = select(Entry).where(
        Entry.user_id == user.id,
        Entry.date >= datetime.date(year, month, 1),
        Entry.date < next_month_start,
    )
    entries = session.execute(stmt).scalars().all()

    return JSONResponse(
        {
            "days": [e.date.day for e in entries],
            "shared": [e.date.day for e in entries if e.share_token],
        }
    )


@router.post("/journal/{year}/{month}/{day}/share")
async def journal_share(
    year: int,
    month: int,
    day: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        date = datetime.date(year, month, day)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid date")

    stmt = select(Entry).where(Entry.user_id == user.id, Entry.date == date)
    entry = session.execute(stmt).scalars().first()
    if not entry:
        raise HTTPException(status_code=404, detail="No entry for this date")

    if not entry.share_token:
        entry.share_token = uuid4().hex
        session.add(entry)
        session.commit()
        session.refresh(entry)

    return JSONResponse({"url": f"/share/{entry.share_token}"})


@router.delete("/journal/{year}/{month}/{day}/share")
async def journal_revoke_share(
    year: int,
    month: int,
    day: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        date = datetime.date(year, month, day)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid date")

    stmt = select(Entry).where(Entry.user_id == user.id, Entry.date == date)
    entry = session.execute(stmt).scalars().first()
    if not entry or not entry.share_token:
        return JSONResponse({"revoked": False})

    entry.share_token = None
    session.add(entry)
    session.commit()
    return JSONResponse({"revoked": True})


@router.get("/share/{token}")
async def public_share(
    token: str,
    request: Request,
    session: Session = Depends(get_session),
):
    stmt = select(Entry).where(Entry.share_token == token)
    entry = session.execute(stmt).scalars().first()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")

    author = session.get(User, entry.user_id)

    shared_content = re.sub(
        r'(src="/uploads/[^"?]+)"',
        rf'\1?share_token={token}"',
        entry.content,
    )

    return templates.TemplateResponse(
        request, "share.html", ctx(request, entry=entry, shared_content=shared_content, user=author)
    )
