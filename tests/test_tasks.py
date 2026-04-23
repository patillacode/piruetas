# tests for app/tasks.py
import os
from pathlib import Path
from unittest.mock import patch

import bcrypt
import pytest
from sqlmodel import Session

import app.database as db_module
from app.models import Image, User
from app.settings import get_settings
from app.tasks import (
    get_tasks,
    run_cleanup_images,
    run_vacuum_db,
    scheduled_cleanup_images,
    scheduled_vacuum_db,
)


@pytest.fixture()
def task_env(tmp_path):
    db_path = tmp_path / "tasks_test.db"
    env_overrides = {
        "DATABASE_URL": f"sqlite:///{db_path}",
        "DATA_DIR": str(tmp_path),
        "SECRET_KEY": "key-for-task-tests",
        "SECURE_COOKIES": "false",
        "ADMIN_USERNAME": "taskadmin",
        "ADMIN_PASSWORD": "taskpassword123",
    }
    original_env = {k: os.environ.get(k) for k in env_overrides}
    os.environ.update(env_overrides)
    get_settings.cache_clear()
    saved_engine = db_module._engine
    db_module._engine = None
    db_module.init_db()
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


def test_get_tasks_returns_registry(task_env):
    tasks = get_tasks()
    assert "cleanup_images" in tasks
    assert "vacuum_db" in tasks


def test_run_cleanup_images_no_uploads_dir(task_env, tmp_path):
    result = run_cleanup_images(str(tmp_path))
    assert "Removed" in result


def test_run_vacuum_db(task_env):
    result = run_vacuum_db()
    assert "VACUUM" in result
    tasks = get_tasks()
    assert tasks["vacuum_db"].last_result == result
    assert tasks["vacuum_db"].last_run is not None


def test_scheduled_cleanup_images_delegates(task_env, tmp_path):
    assert scheduled_cleanup_images(str(tmp_path)) is None


def test_scheduled_vacuum_db_delegates(task_env):
    assert scheduled_vacuum_db() is None


def _seed_user(session, username):
    hashed = bcrypt.hashpw(b"pw", bcrypt.gensalt(rounds=4)).decode()
    user = User(username=username, hashed_password=hashed, is_admin=False)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_run_cleanup_removes_disk_only_files(task_env, tmp_path):
    with Session(db_module.get_engine()) as s:
        user = _seed_user(s, "oc0")
        uid = user.id

    uploads = tmp_path / "uploads" / str(uid)
    uploads.mkdir(parents=True, exist_ok=True)
    ghost = uploads / "ghost.jpg"
    ghost.write_bytes(b"\xff\xd8\xff")
    run_cleanup_images(str(tmp_path))
    assert not ghost.exists()


def test_run_cleanup_removes_orphaned_image_and_file(task_env, tmp_path):
    with Session(db_module.get_engine()) as s:
        user = _seed_user(s, "oc1")
        img = Image(user_id=user.id, filename="orphan.jpg", original_name="orphan.jpg")
        s.add(img)
        s.commit()
        uploads = tmp_path / "uploads" / str(user.id)
        uploads.mkdir(parents=True, exist_ok=True)
        (uploads / "orphan.jpg").write_bytes(b"\xff\xd8\xff")

    run_cleanup_images(str(tmp_path))

    with Session(db_module.get_engine()) as s:
        remaining = s.execute(
            Image.__table__.select().where(Image.filename == "orphan.jpg")
        ).fetchall()
        assert len(remaining) == 0


def test_run_cleanup_orphaned_by_missing_entry(task_env, tmp_path):
    with Session(db_module.get_engine()) as s:
        user = _seed_user(s, "oc2")
        img = Image(
            user_id=user.id,
            filename="linked.jpg",
            original_name="linked.jpg",
            entry_id=9999,
        )
        s.add(img)
        s.commit()

    result = run_cleanup_images(str(tmp_path))
    assert "Removed" in result


def test_run_cleanup_orphaned_unlink_exception_is_swallowed(task_env, tmp_path):
    with Session(db_module.get_engine()) as s:
        user = _seed_user(s, "oc3")
        img = Image(user_id=user.id, filename="err.jpg", original_name="err.jpg")
        s.add(img)
        s.commit()
        uploads = tmp_path / "uploads" / str(user.id)
        uploads.mkdir(parents=True, exist_ok=True)
        (uploads / "err.jpg").write_bytes(b"\xff\xd8\xff")

    real_unlink = Path.unlink

    def fail_unlink(self, missing_ok=False):
        if self.name == "err.jpg":
            raise OSError("simulated failure")
        return real_unlink(self, missing_ok=missing_ok)

    with patch.object(Path, "unlink", fail_unlink):
        result = run_cleanup_images(str(tmp_path))
    assert "Removed" in result


def test_run_cleanup_disk_only_unlink_exception_is_swallowed(task_env, tmp_path):
    with Session(db_module.get_engine()) as s:
        user = _seed_user(s, "oc4")
        uid = user.id

    uploads = tmp_path / "uploads" / str(uid)
    uploads.mkdir(parents=True, exist_ok=True)
    ghost = uploads / "ghost2.jpg"
    ghost.write_bytes(b"\xff\xd8\xff")

    real_unlink = Path.unlink

    def fail_unlink(self, missing_ok=False):
        if self.name == "ghost2.jpg":
            raise OSError("simulated failure")
        return real_unlink(self, missing_ok=missing_ok)

    with patch.object(Path, "unlink", fail_unlink):
        result = run_cleanup_images(str(tmp_path))
    assert "Removed" in result
