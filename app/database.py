import shutil
import warnings
from pathlib import Path
from typing import Generator

import bcrypt
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from app import models as _models  # noqa: F401
from app.models import Entry, Image, User
from app.settings import get_settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.database_url
        if db_url.startswith("sqlite:///"):
            db_file = db_url[len("sqlite:///") :]
            db_path = Path(db_file) if db_file else Path("piruetas.db")
            data_dir = Path(settings.data_dir)
            if not db_path.is_absolute() or not str(db_path).startswith(str(data_dir)):
                warnings.warn(
                    f"DATABASE_URL resolves to '{db_path}', which is outside DATA_DIR '{data_dir}'. "
                    "Use 4 slashes for an absolute path: sqlite:////data/piruetas.db",
                    stacklevel=2,
                )
            db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(db_url, connect_args={"check_same_thread": False})
    return _engine


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _run_migrations(engine)


def _run_migrations(engine) -> None:
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE entry ADD COLUMN share_token TEXT"))
        except OperationalError:
            pass
        conn.commit()


def seed_admin(session: Session) -> None:
    settings = get_settings()
    existing = session.exec(select(User).where(User.username == settings.admin_username)).first()
    if not existing:
        hashed = bcrypt.hashpw(settings.admin_password.encode(), bcrypt.gensalt()).decode()
        admin = User(username=settings.admin_username, hashed_password=hashed, is_admin=True)
        try:
            session.add(admin)
            session.commit()
        except IntegrityError:
            session.rollback()


def seed_demo(session: Session) -> None:
    settings = get_settings()
    if not settings.demo_enabled:
        return
    existing = session.exec(select(User).where(User.username == settings.demo_username)).first()
    if not existing:
        hashed = bcrypt.hashpw(settings.demo_password.encode(), bcrypt.gensalt()).decode()
        demo = User(username=settings.demo_username, hashed_password=hashed, is_admin=False)
        try:
            session.add(demo)
            session.commit()
        except IntegrityError:
            session.rollback()


def delete_demo_user_content(session: Session) -> None:
    settings = get_settings()
    demo = session.exec(select(User).where(User.username == settings.demo_username)).first()
    if not demo:
        return
    for entry in session.exec(select(Entry).where(Entry.user_id == demo.id)).all():
        session.delete(entry)
    for image in session.exec(select(Image).where(Image.user_id == demo.id)).all():
        session.delete(image)
    session.commit()
    uploads = Path(settings.data_dir) / "uploads" / str(demo.id)
    if uploads.exists():
        shutil.rmtree(uploads)
        uploads.mkdir(parents=True, exist_ok=True)


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
