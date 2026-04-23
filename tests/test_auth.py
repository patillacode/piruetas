from app.auth import make_session_token
from app.settings import get_settings
from tests.conftest import get_csrf, login


def test_login_success(client, admin_user):
    resp = login(client, "admin", "adminpass123")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"
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
    assert resp.headers["location"] == "/"


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
