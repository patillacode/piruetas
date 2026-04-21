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
    from sqlmodel import select

    from app.models import User

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


def test_reset_password(client, session, admin_user, regular_user):
    login(client, "admin", "adminpass123")
    resp = client.post(
        f"/admin/users/{regular_user.id}/reset-password",
        data={"new_password": "brandnew456", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 303
    session.refresh(regular_user)
    import bcrypt

    assert bcrypt.checkpw(b"brandnew456", regular_user.hashed_password.encode())
