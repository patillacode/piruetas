import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.csrf import generate_csrf_token
from app.i18n import get_locale, get_month_names, get_short_weekday_names, get_t, get_weekday_names
from app.session_token import SESSION_COOKIE
from app.settings import get_settings

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _next_half_hour_ts() -> int:
    now = datetime.datetime.now()
    if now.minute < 30:
        next_reset = now.replace(minute=30, second=0, microsecond=0)
    else:
        next_reset = (now + datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return int(next_reset.timestamp())


def ctx(request: Request, **kwargs) -> dict:
    settings = get_settings()
    week_start = 1 if settings.week_start.lower() == "monday" else 0
    locale = get_locale(request)
    session_token = request.cookies.get(SESSION_COOKIE, "")
    csrf_token = generate_csrf_token(session_token) if session_token else ""
    csp_nonce = getattr(request.state, "csp_nonce", "")
    user = kwargs.get("user")
    is_demo = bool(
        settings.demo_enabled and user is not None and user.username == settings.demo_username
    )
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
        "is_demo": is_demo,
        "demo_next_reset_ts": _next_half_hour_ts() if is_demo else None,
        **kwargs,
    }
