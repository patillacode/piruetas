# tests for app/database.py
import datetime
import os
import warnings
from unittest.mock import patch

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

import app.database as db_module
from app.models import Entry, Image, User
from app.settings import get_settings


@pytest.fixture()
def db_env(tmp_path):
    db_path = tmp_path / "test.db"
    env_overrides = {
        "DATABASE_URL": f"sqlite:///{db_path}",
        "DATA_DIR": str(tmp_path),
        "SECRET_KEY": "key-for-db-tests-only",
        "SECURE_COOKIES": "false",
        "ADMIN_USERNAME": "dbadmin",
        "ADMIN_PASSWORD": "dbpassword123",
        "DEMO_USERNAME": "dbdemo",
        "DEMO_PASSWORD": "dbdemo123",
        "DEMO_ENABLED": "false",
    }
    original_env = {k: os.environ.get(k) for k in env_overrides}
    os.environ.update(env_overrides)
    get_settings.cache_clear()
    saved_engine = db_module._engine
    db_module._engine = None
    yield tmp_path
    if db_module._engine is not None:
        db_module._engine.dispose()
    db_module._engine = saved_engine
    get_settings.cache_clear()
    for k, v in original_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_get_engine_creates_and_caches(db_env):
    engine = db_module.get_engine()
    assert engine is not None
    assert db_module.get_engine() is engine


def test_get_engine_warns_path_outside_data_dir(db_env, tmp_path):
    db_module._engine = None
    os.environ["DATABASE_URL"] = "sqlite:///relative/path.db"
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            db_module.get_engine()
        assert any("outside DATA_DIR" in str(warning.message) for warning in w)
    finally:
        db_module._engine.dispose()
        db_module._engine = None
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path}/test.db"


def test_init_db_creates_tables(db_env):
    db_module.init_db()
    inspector = inspect(db_module.get_engine())
    assert "user" in inspector.get_table_names()
    assert "entry" in inspector.get_table_names()


def test_run_migrations_is_idempotent(db_env):
    db_module.init_db()
    db_module._run_migrations(db_module.get_engine())


def test_seed_admin_creates_user(db_env):
    db_module.init_db()
    with Session(db_module.get_engine()) as session:
        db_module.seed_admin(session)
        user = session.exec(select(User).where(User.username == "dbadmin")).first()
        assert user is not None and user.is_admin


def test_seed_admin_handles_integrity_error(db_env):
    db_module.init_db()
    with Session(db_module.get_engine()) as session:
        fake_result = type("R", (), {"first": lambda self: None})()
        with patch.object(session, "exec", return_value=fake_result):
            with patch.object(session, "commit", side_effect=IntegrityError("dup", {}, None)):
                db_module.seed_admin(session)


def test_seed_demo_disabled_skips(db_env):
    db_module.init_db()
    with Session(db_module.get_engine()) as session:
        db_module.seed_demo(session)
        user = session.exec(select(User).where(User.username == "dbdemo")).first()
        assert user is None


def test_seed_demo_enabled_creates_user(db_env):
    os.environ["DEMO_ENABLED"] = "true"
    get_settings.cache_clear()
    db_module.init_db()
    try:
        with Session(db_module.get_engine()) as session:
            db_module.seed_demo(session)
            user = session.exec(select(User).where(User.username == "dbdemo")).first()
            assert user is not None and not user.is_admin
    finally:
        os.environ["DEMO_ENABLED"] = "false"
        get_settings.cache_clear()


def test_seed_demo_handles_integrity_error(db_env):
    os.environ["DEMO_ENABLED"] = "true"
    get_settings.cache_clear()
    db_module.init_db()
    try:
        with Session(db_module.get_engine()) as session:
            fake_result = type("R", (), {"first": lambda self: None})()
            with patch.object(session, "exec", return_value=fake_result):
                with patch.object(session, "commit", side_effect=IntegrityError("dup", {}, None)):
                    db_module.seed_demo(session)
    finally:
        os.environ["DEMO_ENABLED"] = "false"
        get_settings.cache_clear()


def test_delete_demo_user_content_no_user(db_env):
    db_module.init_db()
    with Session(db_module.get_engine()) as session:
        db_module.delete_demo_user_content(session)


def test_delete_demo_user_content_with_data(db_env, tmp_path):
    os.environ["DEMO_ENABLED"] = "true"
    get_settings.cache_clear()
    db_module.init_db()
    try:
        with Session(db_module.get_engine()) as session:
            db_module.seed_demo(session)
            demo = session.exec(select(User).where(User.username == "dbdemo")).first()

            entry = Entry(user_id=demo.id, date=datetime.date.today(), content="<p>demo</p>")
            session.add(entry)
            image = Image(user_id=demo.id, filename="demo.jpg", original_name="demo.jpg")
            session.add(image)
            session.commit()

            uploads = tmp_path / "uploads" / str(demo.id)
            uploads.mkdir(parents=True, exist_ok=True)
            (uploads / "demo.jpg").write_bytes(b"\xff\xd8\xff")

            db_module.delete_demo_user_content(session)
            assert session.exec(select(Entry).where(Entry.user_id == demo.id)).first() is None
    finally:
        os.environ["DEMO_ENABLED"] = "false"
        get_settings.cache_clear()


def test_get_session_yields_session(db_env):
    db_module.init_db()
    gen = db_module.get_session()
    session = next(gen)
    assert isinstance(session, Session)
    try:
        next(gen)
    except StopIteration:
        pass
