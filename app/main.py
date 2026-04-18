import datetime
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from app.database import get_engine, init_db, seed_admin
from app.routers import admin, auth, journal, upload
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    uploads_dir = Path(settings.data_dir) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    init_db()
    with Session(get_engine()) as session:
        seed_admin(session)
    yield


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
