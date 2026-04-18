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


class EntrySaveRequest(BaseModel):
    content: str
    word_count: int


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

    entry = session.exec(select(Entry).where(Entry.user_id == user.id, Entry.date == date)).first()

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

    entry = session.exec(select(Entry).where(Entry.user_id == user.id, Entry.date == date)).first()

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

    entry = session.exec(select(Entry).where(Entry.user_id == user.id, Entry.date == date)).first()

    if entry:
        settings = get_settings()
        images = session.exec(select(Image).where(Image.entry_id == entry.id)).all()
        for image in images:
            file_path = Path(settings.data_dir) / "uploads" / str(user.id) / image.filename
            file_path.unlink(missing_ok=True)
            session.delete(image)
        session.delete(entry)
        session.commit()

    return JSONResponse({"deleted": True})


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
    entries = session.exec(
        select(Entry).where(
            Entry.user_id == user.id,
            Entry.date >= datetime.date(year, month, 1),
            Entry.date < next_month_start,
        )
    ).all()

    return JSONResponse({"days": [e.date.day for e in entries]})


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

    entry = session.exec(select(Entry).where(Entry.user_id == user.id, Entry.date == date)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="No entry for this date")

    if not entry.share_token:
        entry.share_token = uuid4().hex
        session.add(entry)
        session.commit()
        session.refresh(entry)

    return JSONResponse({"url": f"/share/{entry.share_token}"})


@router.get("/share/{token}")
async def public_share(
    token: str,
    request: Request,
    session: Session = Depends(get_session),
):
    entry = session.exec(select(Entry).where(Entry.share_token == token)).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")

    author = session.get(User, entry.user_id)
    recent = session.exec(
        select(Entry)
        .where(Entry.user_id == entry.user_id, Entry.id != entry.id)
        .order_by(Entry.date.desc())
        .limit(4)
    ).all()
    entries = [entry] + list(recent)
    return templates.TemplateResponse(
        request, "share.html", ctx(request, entries=entries, user=author)
    )
