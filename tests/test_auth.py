import datetime
from unittest.mock import patch

from app.auth import make_session_token
from app.settings import get_settings
from tests.conftest import get_csrf, login


def signup(client, username, password, confirm_password=None):
    get_resp = client.get("/signup")
    csrf_cookie = get_resp.cookies.get("piruetas_login_csrf", "")
    return client.post(
        "/signup",
        data={
            "username": username,
            "password": password,
            "confirm_password": confirm_password if confirm_password is not None else password,
            "login_csrf_token": csrf_cookie,
        },
    )


def test_login_success(client, admin_user):
    resp = login(client, "admin", "adminpass123")
    assert resp.status_code == 302
    today = datetime.date.today()
    assert resp.headers["location"] == f"/journal/{today.year}/{today.month:02d}/{today.day:02d}"
    assert "piruetas_session" in resp.cookies


def test_login_wrong_password(client, admin_user):
    resp = login(client, "admin", "wrongpassword")
    assert resp.status_code == 401
    assert b"Invalid" in resp.content


def test_login_unknown_user(client):
    resp = login(client, "nobody", "doesntmatter")
    assert resp.status_code == 401
    assert b"Invalid" in resp.content


def test_logout(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.post("/logout", data={"csrf_token": get_csrf(client)})
    assert resp.status_code == 302
    assert (
        client.cookies.get("piruetas_session") is None or resp.cookies.get("piruetas_session") == ""
    )


def test_protected_route_redirects_unauthenticated(client):
    resp = client.get("/journal/2026/04/17")
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


def test_login_page_accessible(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Sign in" in resp.content


def test_login_page_redirects_when_already_authenticated(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.get("/login")
    assert resp.status_code == 302
    today = datetime.date.today()
    assert resp.headers["location"] == f"/journal/{today.year}/{today.month:02d}/{today.day:02d}"


def test_set_locale_sets_cookie(client):
    resp = client.get("/locale/en", headers={"referer": "/journal/2026/01/01"})
    assert resp.status_code == 302
    assert resp.cookies.get("piruetas_locale") == "en"


def test_set_locale_unsupported_lang_skips_cookie(client):
    resp = client.get("/locale/de")
    assert resp.status_code == 302
    assert "piruetas_locale" not in resp.cookies


def test_protected_route_with_invalid_session_token(client):
    client.cookies.set("piruetas_session", "invalid.token.value")
    resp = client.get("/journal/2026/01/01")
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


def test_signup_page_accessible(client):
    resp = client.get("/signup")
    assert resp.status_code == 200
    assert b"Create account" in resp.content


def test_signup_success_redirects_and_sets_session(client):
    import datetime
    resp = signup(client, "newuser", "securepass123")
    assert resp.status_code == 302
    today = datetime.date.today()
    assert resp.headers["location"] == f"/journal/{today.year}/{today.month:02d}/{today.day:02d}"
    assert "piruetas_session" in resp.cookies


def test_signup_page_redirects_when_authenticated(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.get("/signup")
    assert resp.status_code == 302
    today = datetime.date.today()
    assert resp.headers["location"] == f"/journal/{today.year}/{today.month:02d}/{today.day:02d}"


def test_signup_duplicate_username(client, admin_user):
    resp = signup(client, "admin", "anotherpass123")
    assert resp.status_code == 400
    assert b"already taken" in resp.content


def test_signup_invalid_username(client):
    resp = signup(client, "a!", "securepass123")
    assert resp.status_code == 400
    assert b"letters, numbers" in resp.content


def test_signup_short_password(client):
    resp = signup(client, "validuser", "short")
    assert resp.status_code == 400
    assert b"8 characters" in resp.content


def test_signup_password_mismatch(client):
    resp = signup(client, "validuser", "securepass123", confirm_password="different123")
    assert resp.status_code == 400
    assert b"do not match" in resp.content


def test_signup_csrf_required(client):
    resp = client.post(
        "/signup",
        data={"username": "x", "password": "y", "confirm_password": "y", "login_csrf_token": ""},
    )
    assert resp.status_code == 403


def test_signup_rate_limited(client):
    with patch("app.routers.auth.is_rate_limited", return_value=True):
        resp = signup(client, "validuser", "securepass123")
    assert resp.status_code == 429
    assert b"Too many requests" in resp.content


def test_protected_route_with_nonexistent_user_token(client):
    token = make_session_token(
        user_id=99999,
        is_admin=False,
        session_version=0,
        secret_key=get_settings().secret_key,
    )
    client.cookies.set("piruetas_session", token)
    resp = client.get("/journal/2026/01/01")
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]
