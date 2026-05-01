import io
import json
import os
import zipfile
from datetime import date as date_type

import bcrypt
import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.export import scope_label
from app.models import Entry, Image
from app.settings import get_settings
from tests.conftest import get_csrf, login


def test_account_page_requires_auth(client):
    resp = client.get("/account")
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


def test_account_page_accessible_when_logged_in(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.get("/account")
    assert resp.status_code == 200
    assert b"Change password" in resp.content


def test_password_change_success(client, session, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/account/password",
        data={
            "current_password": "userpass123",
            "new_password": "newpassword99",
            "confirm_password": "newpassword99",
            "csrf_token": get_csrf(client),
        },
    )
    assert resp.status_code == 200
    assert b"Password changed" in resp.content
    session.refresh(regular_user)
    assert bcrypt.checkpw(b"newpassword99", regular_user.hashed_password.encode())


def test_password_change_wrong_current(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/account/password",
        data={
            "current_password": "wrongpassword",
            "new_password": "newpassword99",
            "confirm_password": "newpassword99",
            "csrf_token": get_csrf(client),
        },
    )
    assert resp.status_code == 400
    assert b"incorrect" in resp.content


def test_password_change_mismatch(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/account/password",
        data={
            "current_password": "userpass123",
            "new_password": "newpassword99",
            "confirm_password": "differentpassword",
            "csrf_token": get_csrf(client),
        },
    )
    assert resp.status_code == 400
    assert b"do not match" in resp.content


def test_password_change_too_short(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/account/password",
        data={
            "current_password": "userpass123",
            "new_password": "short",
            "confirm_password": "short",
            "csrf_token": get_csrf(client),
        },
    )
    assert resp.status_code == 400
    assert b"8 characters" in resp.content


def test_password_change_csrf_rejected(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/account/password",
        data={
            "current_password": "userpass123",
            "new_password": "newpassword99",
            "confirm_password": "newpassword99",
            "csrf_token": "invalid",
        },
    )
    assert resp.status_code == 403


# --- Tab navigation / new pages ---


def test_account_page_has_tab_nav(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.get("/account")
    assert resp.status_code == 200
    assert b"/account/data" in resp.content
    assert b"/account" in resp.content


def test_account_page_requires_auth_redirect(client):
    resp = client.get("/account")
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


def test_data_page_requires_auth_redirect(client):
    resp = client.get("/account/data")
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


def test_data_page_accessible(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.get("/account/data")
    assert resp.status_code == 200
    assert b"data" in resp.content


def test_data_page_no_entries_no_crash(client, session, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.get("/account/data")
    assert resp.status_code == 200


# --- Export preview ---


def _make_entry(session, user_id, d, content="<p>Hello</p>", word_count=1):
    entry = Entry(user_id=user_id, date=d, content=content, word_count=word_count)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def test_export_preview_requires_auth(client):
    resp = client.post("/account/export/preview", data={"scope": "all", "csrf_token": "x"})
    assert resp.status_code == 302


def test_export_preview_requires_csrf(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post("/account/export/preview", data={"scope": "all", "csrf_token": "invalid"})
    assert resp.status_code == 403


def test_export_preview_scope_all(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 1, 15))
    _make_entry(session, regular_user.id, date_type(2024, 2, 20))
    resp = client.post(
        "/account/export/preview",
        data={"scope": "all", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2


def test_export_preview_scope_year(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 6, 1))
    _make_entry(session, regular_user.id, date_type(2023, 6, 1))
    resp = client.post(
        "/account/export/preview",
        data={"scope": "year", "year": 2024, "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_export_preview_scope_month(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 3, 5))
    _make_entry(session, regular_user.id, date_type(2024, 4, 5))
    resp = client.post(
        "/account/export/preview",
        data={"scope": "month", "year": 2024, "month": 3, "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_export_preview_scope_day_found(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 1, 15))
    resp = client.post(
        "/account/export/preview",
        data={"scope": "day", "day": "2024-01-15", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


def test_export_preview_scope_day_not_found(client, session, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/account/export/preview",
        data={"scope": "day", "day": "2024-01-15", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_export_preview_scope_label_all(client, session, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/account/export/preview",
        data={"scope": "all", "csrf_token": get_csrf(client)},
    )
    assert resp.json()["scope_label"] == "All entries"


def test_export_preview_scope_label_month(client, session, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/account/export/preview",
        data={"scope": "month", "year": 2024, "month": 3, "csrf_token": get_csrf(client)},
    )
    assert resp.json()["scope_label"] == "March 2024"


# --- Export download — text bundle ---


def test_export_download_text_returns_zip(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 1, 15), content="<p>Hello world</p>")
    resp = client.get("/account/export/download?bundle=text&scope=all")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"


def test_export_download_text_zip_structure(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 1, 15), content="<p>Hello world</p>")
    resp = client.get("/account/export/download?bundle=text&scope=all")
    buf = io.BytesIO(resp.content)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        assert any("2024/01/2024-01-15/" in n for n in names)
        assert any("entry.txt" in n for n in names)
        assert any("entry.html" in n for n in names)
        assert any("entry.md" in n for n in names)


def test_export_download_text_entry_txt_content(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 1, 15), content="<p>Hello world</p>")
    resp = client.get("/account/export/download?bundle=text&scope=all")
    buf = io.BytesIO(resp.content)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        txt_name = next(n for n in names if "entry.txt" in n)
        txt = zf.read(txt_name).decode()
        assert "Date: 2024-01-15" in txt
        assert "Hello world" in txt


def test_export_download_text_no_images_no_images_folder(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 1, 15))
    resp = client.get("/account/export/download?bundle=text&scope=all")
    buf = io.BytesIO(resp.content)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        assert not any("images/" in n for n in names)


def test_export_download_text_missing_image_file_no_crash(client, session, regular_user):
    login(client, "testuser", "userpass123")
    entry = _make_entry(session, regular_user.id, date_type(2024, 1, 15))
    img = Image(
        entry_id=entry.id,
        user_id=regular_user.id,
        filename="nonexistent.jpg",
        original_name="nonexistent.jpg",
    )
    session.add(img)
    session.commit()
    resp = client.get("/account/export/download?bundle=text&scope=all")
    assert resp.status_code == 200
    buf = io.BytesIO(resp.content)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        assert not any("images/" in n for n in names)


def test_export_download_text_scope_day(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 1, 15))
    _make_entry(session, regular_user.id, date_type(2024, 2, 20))
    resp = client.get("/account/export/download?bundle=text&scope=day&day=2024-01-15")
    buf = io.BytesIO(resp.content)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        assert any("2024-01-15" in n for n in names)
        assert not any("2024-02-20" in n for n in names)


# --- Export download — JSON bundle ---


def test_export_download_json_returns_zip(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 1, 15), content="<p>Hi</p>", word_count=1)
    resp = client.get("/account/export/download?bundle=json&scope=all")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"


def test_export_download_json_entry_fields(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 1, 15), content="<p>Hi</p>", word_count=1)
    resp = client.get("/account/export/download?bundle=json&scope=all")
    buf = io.BytesIO(resp.content)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        json_name = next(n for n in names if "entry.json" in n)
        data = json.loads(zf.read(json_name).decode())
        assert data["date"] == "2024-01-15"
        assert "content_html" in data
        assert "content_markdown" in data
        assert "content_text" in data
        assert "word_count" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["images"] == []


def test_export_download_json_images_empty_when_no_records(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 1, 15))
    resp = client.get("/account/export/download?bundle=json&scope=all")
    buf = io.BytesIO(resp.content)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        json_name = next(n for n in names if "entry.json" in n)
        data = json.loads(zf.read(json_name).decode())
        assert data["images"] == []


def test_export_download_text_existing_image_included_in_zip(client, session, regular_user):
    login(client, "testuser", "userpass123")
    entry = _make_entry(session, regular_user.id, date_type(2024, 1, 15))
    settings = get_settings()
    upload_dir = os.path.join(settings.data_dir, "uploads", str(regular_user.id))
    os.makedirs(upload_dir, exist_ok=True)
    img_filename = "real_test_image.jpg"
    img_path = os.path.join(upload_dir, img_filename)
    with open(img_path, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 10)
    img = Image(
        entry_id=entry.id,
        user_id=regular_user.id,
        filename=img_filename,
        original_name="photo.jpg",
    )
    session.add(img)
    session.commit()
    try:
        resp = client.get("/account/export/download?bundle=text&scope=all")
        assert resp.status_code == 200
        buf = io.BytesIO(resp.content)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert any("images/" in n for n in names)
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)


def test_export_download_invalid_bundle_defaults_to_text(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 1, 15))
    resp = client.get("/account/export/download?bundle=invalid&scope=all")
    assert resp.status_code == 200
    buf = io.BytesIO(resp.content)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        assert any("entry.txt" in n for n in names)


# --- User isolation ---


def test_export_preview_user_isolation(client, session, regular_user, admin_user):
    _make_entry(session, admin_user.id, date_type(2024, 1, 15))
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/account/export/preview",
        data={"scope": "all", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


# --- Delete preview ---


def test_delete_preview_requires_auth(client):
    resp = client.post("/account/delete/preview", data={"scope": "all", "csrf_token": "x"})
    assert resp.status_code == 302


def test_delete_preview_requires_csrf(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post("/account/delete/preview", data={"scope": "all", "csrf_token": "invalid"})
    assert resp.status_code == 403


def test_delete_preview_scope_all(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 1, 15))
    _make_entry(session, regular_user.id, date_type(2024, 2, 20))
    resp = client.post(
        "/account/delete/preview",
        data={"scope": "all", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 2


def test_delete_preview_scope_day_no_entry(client, session, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/account/delete/preview",
        data={"scope": "day", "day": "2024-01-15", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_delete_preview_invalid_day_returns_400(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/account/delete/preview",
        data={"scope": "day", "day": "not-a-date", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 400


def test_export_preview_invalid_day_returns_400(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/account/export/preview",
        data={"scope": "day", "day": "not-a-date", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 400


# --- Delete confirm ---


def test_delete_confirm_requires_auth(client):
    resp = client.post("/account/delete/confirm", data={"scope": "all", "csrf_token": "x"})
    assert resp.status_code == 302


def test_delete_confirm_requires_csrf(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post("/account/delete/confirm", data={"scope": "all", "csrf_token": "invalid"})
    assert resp.status_code == 403


def test_delete_confirm_deletes_entries(client, session, regular_user):
    login(client, "testuser", "userpass123")
    _make_entry(session, regular_user.id, date_type(2024, 1, 15))
    _make_entry(session, regular_user.id, date_type(2024, 2, 20))
    resp = client.post(
        "/account/delete/confirm",
        data={"scope": "all", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 2
    remaining = list(session.exec(select(Entry).where(Entry.user_id == regular_user.id)).all())
    assert remaining == []


def test_delete_confirm_deletes_associated_images(client, session, regular_user):
    login(client, "testuser", "userpass123")
    entry = _make_entry(session, regular_user.id, date_type(2024, 1, 15))
    img = Image(
        entry_id=entry.id,
        user_id=regular_user.id,
        filename="test.jpg",
        original_name="test.jpg",
    )
    session.add(img)
    session.commit()
    resp = client.post(
        "/account/delete/confirm",
        data={"scope": "all", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 200
    remaining_imgs = list(session.exec(select(Image).where(Image.user_id == regular_user.id)).all())
    assert remaining_imgs == []


def test_delete_confirm_unlinks_image_files(client, session, regular_user):
    login(client, "testuser", "userpass123")
    entry = _make_entry(session, regular_user.id, date_type(2024, 1, 15))
    settings = get_settings()
    upload_dir = os.path.join(settings.data_dir, "uploads", str(regular_user.id))
    os.makedirs(upload_dir, exist_ok=True)
    img_filename = "delete_test.jpg"
    img_path = os.path.join(upload_dir, img_filename)
    with open(img_path, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 10)
    img = Image(
        entry_id=entry.id, user_id=regular_user.id, filename=img_filename, original_name="photo.jpg"
    )
    session.add(img)
    session.commit()
    assert os.path.exists(img_path)
    resp = client.post(
        "/account/delete/confirm",
        data={"scope": "all", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 200
    assert not os.path.exists(img_path)


def test_delete_confirm_no_entries_returns_zero(client, session, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/account/delete/confirm",
        data={"scope": "all", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 0


def test_scope_label_invalid_day_raises():
    with pytest.raises(HTTPException) as exc_info:
        scope_label("day", None, None, "not-a-date")
    assert exc_info.value.status_code == 400
