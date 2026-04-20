import asyncio
import datetime
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.database import delete_demo_user_content, get_engine, init_db, seed_admin, seed_demo
from app.routers import account, admin, auth, journal, upload
from app.settings import get_settings
from app.templates_config import templates


async def _demo_cleanup_loop() -> None:
    settings = get_settings()
    while True:
        await asyncio.sleep(settings.demo_reset_interval)
        with Session(get_engine()) as session:
            delete_demo_user_content(session)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    uploads_dir = Path(settings.data_dir) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    with Session(get_engine()) as session:
        seed_admin(session)
        seed_demo(session)
    task = asyncio.create_task(_demo_cleanup_loop()) if settings.demo_enabled else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="Piruetas", lifespan=lifespan)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    settings = get_settings()
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    nonce = getattr(request.state, "csp_nonce", "")
    script_src = f"'self' 'nonce-{nonce}' https://esm.sh" if nonce else "'self' 'unsafe-inline' https://esm.sh"
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; "
        f"script-src {script_src}; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:;"
    )
    if settings.secure_cookies:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(request, "errors/404.html", {}, status_code=404)
    if exc.status_code >= 500:
        return templates.TemplateResponse(request, "errors/500.html", {}, status_code=exc.status_code)
    return Response(status_code=exc.status_code, headers=dict(exc.headers) if exc.headers else {})


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        request, "errors/500.html", {}, status_code=500
    )


@app.middleware("http")
async def generate_csp_nonce(request: Request, call_next):
    request.state.csp_nonce = secrets.token_hex(16)
    return await call_next(request)


app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(journal.router)
app.include_router(upload.router)
app.include_router(admin.router)
app.include_router(account.router)


@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})


@app.get("/")
def root():
    today = datetime.date.today()
    return RedirectResponse(url=f"/journal/{today.year}/{today.month:02d}/{today.day:02d}")
