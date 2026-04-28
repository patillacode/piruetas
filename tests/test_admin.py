import io
import os
from pathlib import Path
from unittest.mock import patch

import bcrypt
from sqlmodel import select

from app.models import User
from app.routers import admin as admin_router
from tests.conftest import get_csrf, login


def test_admin_page_accessible_to_admin(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.get("/admin/")
    assert resp.status_code == 200
    assert b"Users" in resp.content


def test_admin_page_forbidden_to_regular_user(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.get("/admin/")
    assert resp.status_code in (302, 403)


def test_create_user(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.post(
        "/admin/users/new",
        data={
            "username": "newuser",
            "password": "newpass123",
            "csrf_token": get_csrf(client),
        },
    )
    assert resp.status_code == 303
    assert resp.headers["location"] == "/admin"


def test_create_user_duplicate_username(client, admin_user, regular_user):
    login(client, "admin", "adminpass123")
    resp = client.post(
        "/admin/users/new",
        data={
            "username": "testuser",
            "password": "newpass456",
            "csrf_token": get_csrf(client),
        },
    )
    assert resp.status_code == 200
    assert b"already taken" in resp.content


def test_create_user_invalid_username(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.post(
        "/admin/users/new",
        data={
            "username": "ab",
            "password": "validpass123",
            "csrf_token": get_csrf(client),
        },
    )
    assert resp.status_code == 200
    assert b"3-32" in resp.content


def test_delete_user(client, session, admin_user, regular_user):
    login(client, "admin", "adminpass123")
    resp = client.post(
        f"/admin/users/{regular_user.id}/delete",
        data={
            "csrf_token": get_csrf(client),
        },
    )
    assert resp.status_code == 303

    found = session.exec(select(User).where(User.id == regular_user.id)).first()
    assert found is None


def test_cannot_delete_self(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.post(
        f"/admin/users/{admin_user.id}/delete",
        data={
            "csrf_token": get_csrf(client),
        },
    )
    assert resp.status_code == 303
    resp2 = client.get("/admin/")
    assert resp2.status_code == 200


def test_create_user_short_password_rejected(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.post(
        "/admin/users/new",
        data={
            "username": "validuser",
            "password": "short",
            "csrf_token": get_csrf(client),
        },
    )
    assert resp.status_code == 200
    assert b"8 characters" in resp.content


def test_create_user_form_get(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.get("/admin/users/new")
    assert resp.status_code == 200
    assert b"username" in resp.content.lower()


def test_delete_nonexistent_user_redirects(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.post(
        "/admin/users/99999/delete",
        data={"csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 303


def test_delete_user_with_uploads_images_entries(client, session, admin_user, regular_user):

    login(client, "testuser", "userpass123")
    jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 20
    upload_resp = client.post(
        "/upload",
        files={"file": ("photo.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    image_url = upload_resp.json()["url"]
    client.post("/journal/2026/01/10", json={"content": f'<img src="{image_url}">'})
    client.post("/logout", data={"csrf_token": get_csrf(client)})

    login(client, "admin", "adminpass123")
    resp = client.post(
        f"/admin/users/{regular_user.id}/delete",
        data={"csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 303


def test_delete_user_rmtree_exception_is_swallowed(client, admin_user, regular_user, monkeypatch):

    uploads_dir = Path(os.environ["DATA_DIR"]) / "uploads" / str(regular_user.id)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    def fail_rmtree(p):
        raise OSError("simulated failure")

    with patch("app.routers.admin.shutil.rmtree", side_effect=fail_rmtree):
        login(client, "admin", "adminpass123")
        resp = client.post(
            f"/admin/users/{regular_user.id}/delete",
            data={"csrf_token": get_csrf(client)},
        )
    assert resp.status_code == 303


def test_admin_tasks_page(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.get("/admin/tasks")
    assert resp.status_code == 200


def test_run_cleanup_images_task(client, admin_user, monkeypatch):

    monkeypatch.setattr(admin_router, "run_cleanup_images", lambda data_dir: "ok")
    login(client, "admin", "adminpass123")
    resp = client.post(
        "/admin/tasks/cleanup-images/run",
        data={"csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 303


def test_run_vacuum_db_task(client, admin_user, monkeypatch):

    monkeypatch.setattr(admin_router, "run_vacuum_db", lambda: "ok")
    login(client, "admin", "adminpass123")
    resp = client.post(
        "/admin/tasks/vacuum-db/run",
        data={"csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 303


