import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.csrf import generate_csrf_token
from app.i18n import (
    MONTH_NAMES,
    get_locale,
    get_month_names,
    get_short_weekday_names,
    get_t,
    get_weekday_names,
)
from app.session_token import SESSION_COOKIE
from app.settings import get_settings

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _datefmt(value, locale: str = "en") -> str | None:
    if value is None:
        return None
    month = MONTH_NAMES.get(locale, MONTH_NAMES["en"])[value.month - 1]
    return f"{month} {value.day}, {value.year}"


def _filesizeformat(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{int(size)} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


templates.env.filters["datefmt"] = _datefmt
templates.env.filters["filesizeformat"] = _filesizeformat


def ctx(request: Request, **kwargs) -> dict:
    settings = get_settings()
    week_start = 1 if settings.week_start.lower() == "monday" else 0
    locale = get_locale(request)
    session_token = request.cookies.get(SESSION_COOKIE, "")
    csrf_token = generate_csrf_token(session_token) if session_token else ""
    csp_nonce = getattr(request.state, "csp_nonce", "")
    return {
        "locale": locale,
        "t": get_t(request),
        "week_start": week_start,
        "months": get_month_names(locale),
        "weekdays": get_weekday_names(locale),
        "short_weekdays": get_short_weekday_names(locale),
        "csrf_token": csrf_token,
        "csp_nonce": csp_nonce,
        "show_donation_prompts": settings.show_donation_prompts,
        "current_year": datetime.date.today().year,
        **kwargs,
    }
