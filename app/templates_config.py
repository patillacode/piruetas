from pathlib import Path

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.auth import SESSION_COOKIE
from app.csrf import generate_csrf_token
from app.i18n import get_locale, get_month_names, get_t, get_weekday_names
from app.settings import get_settings

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


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
        "csrf_token": csrf_token,
        "csp_nonce": csp_nonce,
        **kwargs,
    }
