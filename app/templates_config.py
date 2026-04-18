from pathlib import Path

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.i18n import get_locale, get_month_names, get_t, get_weekday_names
from app.settings import get_settings

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def ctx(request: Request, **kwargs) -> dict:
    settings = get_settings()
    week_start = 1 if settings.week_start.lower() == "monday" else 0
    locale = get_locale(request)
    return {
        "locale": locale,
        "t": get_t(request),
        "week_start": week_start,
        "months": get_month_names(locale),
        "weekdays": get_weekday_names(locale),
        **kwargs,
    }
