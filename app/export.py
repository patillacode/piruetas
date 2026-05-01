import calendar
import re
from datetime import date
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.i18n import MONTH_NAMES, TRANSLATIONS
from app.models import Entry

_EXPORT_CSS = (Path(__file__).parent / "static" / "css" / "export-bundle.css").read_text()


def get_entries_for_scope(
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
        try:
            d = date.fromisoformat(day_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date") from None
        stmt = stmt.where(col(Entry.date) == d)
    return list(session.exec(stmt.order_by(col(Entry.date))).all())


def scope_label(
    scope: str, year: int | None, month: int | None, day_str: str | None, locale: str = "en"
) -> str:
    names = MONTH_NAMES.get(locale, MONTH_NAMES["en"])
    t = TRANSLATIONS.get(locale, TRANSLATIONS["en"])
    if scope == "year" and year:
        return str(year)
    if scope == "month" and year and month:
        return f"{names[month - 1]} {year}"
    if scope == "day" and day_str:
        try:
            d = date.fromisoformat(day_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date") from None
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


def strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html)
    return unescape(s.get_text())


def rewrite_html_srcs(content: str) -> str:
    return re.sub(r'src="/uploads/\d+/([^"]+)"', r'src="images/\1"', content)


def rewrite_md_imgs(md: str) -> str:
    return re.sub(r"!\[([^\]]*)\]\(/uploads/\d+/([^)]+)\)", r"![\1](images/\2)", md)


def build_html_export(content: str, entry_date: date) -> str:
    day_str = entry_date.strftime("%A")
    month_str = entry_date.strftime("%B")
    date_heading = f"{day_str} · {month_str} {entry_date.day}, {entry_date.year}"
    html_content = rewrite_html_srcs(content)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{date_heading}</title>
<style>
{_EXPORT_CSS}
</style>
</head>
<body>
<div class="entry-wrap">
<p class="entry-date">{date_heading}</p>
{html_content}
</div>
</body>
</html>"""
