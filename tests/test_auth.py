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
