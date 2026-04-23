import bcrypt

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
