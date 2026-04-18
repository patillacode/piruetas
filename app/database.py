from pathlib import Path
from typing import Generator

import bcrypt
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from app import models as _models  # noqa: F401
from app.models import User
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


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
