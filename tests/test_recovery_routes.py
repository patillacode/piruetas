from unittest.mock import patch

import bcrypt
from sqlmodel import select

from app.models import RecoveryCode, User
from app.recovery import create_codes_for_user
from app.recovery_flash import RECOVERY_FLASH_COOKIE
from tests.conftest import get_csrf, login


def _signup(client, username="newuser", password="password123"):
    get_resp = client.get("/signup")
    csrf_cookie = get_resp.cookies.get("piruetas_login_csrf", "")
    return client.post(
        "/signup",
        data={
            "username": username,
            "password": password,
            "confirm_password": password,
            "login_csrf_token": csrf_cookie,
        },
    )


def _forgot_password(client, username, recovery_code, new_password):
    get_resp = client.get("/forgot-password")
    csrf_cookie = get_resp.cookies.get("piruetas_login_csrf", "")
    return client.post(
        "/forgot-password",
        data={
            "username": username,
            "recovery_code": recovery_code,
            "new_password": new_password,
            "login_csrf_token": csrf_cookie,
        },
    )


def test_forgot_password_valid(client, regular_user, session):
    codes = create_codes_for_user(regular_user.id, session)
    resp = _forgot_password(client, "testuser", codes[0], "newpassword123")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/login"
    rows = session.exec(
        select(RecoveryCode).where(
            RecoveryCode.user_id == regular_user.id,
            RecoveryCode.used == True,  # noqa: E712
        )
    ).all()
    assert len(rows) == 1


def test_forgot_password_invalid_code(client, regular_user, session):
    create_codes_for_user(regular_user.id, session)
    resp = _forgot_password(client, "testuser", "AAAA-AAAA-AAAA", "newpassword123")
    assert resp.status_code == 400
    assert b"Invalid" in resp.content


def test_forgot_password_unknown_username(client):
    resp = _forgot_password(client, "nobody", "AAAA-AAAA-AAAA", "newpassword123")
    assert resp.status_code == 400
    assert b"Invalid" in resp.content


def test_forgot_password_unknown_same_error_as_invalid_code(client, regular_user, session):
    create_codes_for_user(regular_user.id, session)
    resp_bad_code = _forgot_password(client, "testuser", "AAAA-AAAA-AAAA", "newpassword123")
    resp_bad_user = _forgot_password(client, "nobody", "AAAA-AAAA-AAAA", "newpassword123")
    assert resp_bad_code.status_code == resp_bad_user.status_code
    assert b"Invalid" in resp_bad_code.content
    assert b"Invalid" in resp_bad_user.content


def test_signup_redirects_to_recovery_codes(client):
    resp = _signup(client)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/account/recovery-codes"


def test_signup_sets_recovery_flash_cookie(client):
    resp = _signup(client)
    assert RECOVERY_FLASH_COOKIE in resp.cookies


def test_signup_sets_session_cookie(client):
    resp = _signup(client)
    assert "piruetas_session" in resp.cookies


def test_recovery_codes_page_shows_codes_after_signup(client):
    _signup(client)
    resp = client.get("/account/recovery-codes")
    assert resp.status_code == 200
    assert b"Save these recovery codes" in resp.content


def test_recovery_codes_page_no_codes_on_second_visit(client):
    _signup(client)
    client.get("/account/recovery-codes")
    resp = client.get("/account/recovery-codes")
    assert resp.status_code == 200
    assert b"Save these recovery codes" not in resp.content


def test_recovery_codes_page_requires_auth(client):
    resp = client.get("/account/recovery-codes")
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


def test_regenerate_recovery_codes(client, regular_user, session):
    login(client, "testuser", "userpass123")
    csrf = get_csrf(client)
    resp = client.post(
        "/account/recovery-codes/regenerate",
        data={"current_password": "userpass123", "csrf_token": csrf},
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/account/recovery-codes"
    assert RECOVERY_FLASH_COOKIE in resp.cookies


def test_regenerate_recovery_codes_wrong_password(client, regular_user, session):
    login(client, "testuser", "userpass123")
    csrf = get_csrf(client)
    resp = client.post(
        "/account/recovery-codes/regenerate",
        data={"current_password": "wrongpassword", "csrf_token": csrf},
    )
    assert resp.status_code == 400
    assert b"incorrect" in resp.content


def test_forgot_password_csrf_required(client):
    resp = client.post(
        "/forgot-password",
        data={"username": "x", "recovery_code": "y", "new_password": "z", "login_csrf_token": ""},
    )
    assert resp.status_code == 403


def test_forgot_password_rate_limited(client, regular_user, session):
    create_codes_for_user(regular_user.id, session)
    with patch("app.routers.auth.is_rate_limited", return_value=True):
        resp = _forgot_password(client, "testuser", "AAAA-AAAA-AAAA", "newpassword123")
    assert resp.status_code == 429
    assert b"Too many" in resp.content


def test_forgot_password_short_password(client, regular_user, session):
    codes = create_codes_for_user(regular_user.id, session)
    resp = _forgot_password(client, "testuser", codes[0], "short")
    assert resp.status_code == 400
    assert b"8 characters" in resp.content


def _make_demo_user(session):
    hashed = bcrypt.hashpw(b"demo", bcrypt.gensalt(rounds=4)).decode()
    user = User(username="demo", hashed_password=hashed, is_admin=False)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_demo_user_cannot_view_recovery_codes(client, session):
    _make_demo_user(session)
    login(client, "demo", "demo")
    resp = client.get("/account/recovery-codes")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/account"


def test_demo_user_cannot_regenerate_recovery_codes(client, session):
    _make_demo_user(session)
    login(client, "demo", "demo")
    resp = client.post(
        "/account/recovery-codes/regenerate",
        data={"current_password": "demo", "csrf_token": get_csrf(client)},
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/account"


def test_demo_user_cannot_use_forgot_password(client, session):
    demo = _make_demo_user(session)
    create_codes_for_user(demo.id, session)
    codes = session.exec(select(RecoveryCode).where(RecoveryCode.user_id == demo.id)).all()
    resp = _forgot_password(client, "demo", codes[0].code_hash, "newpassword123")
    assert resp.status_code == 400
