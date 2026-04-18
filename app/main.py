import asyncio
import datetime
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.database import delete_demo_user_content, get_engine, init_db, seed_admin, seed_demo
from app.routers import admin, auth, journal, upload
from app.settings import get_settings


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

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(journal.router)
app.include_router(upload.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return JSONResponse({"status": "ok"})


@app.get("/")
def root():
    today = datetime.date.today()
    return RedirectResponse(url=f"/journal/{today.year}/{today.month:02d}/{today.day:02d}")
