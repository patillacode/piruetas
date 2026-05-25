import datetime
from unittest.mock import AsyncMock, patch

from sqlmodel import select

from app.models import User
from app.rate_limit import MAX_ATTEMPTS, clear_attempts
from app.session_token import make_session_token
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


def test_login_success(client, admin_user, session):
    resp = login(client, "admin", "adminpass123")
    assert resp.status_code == 302
    today = datetime.date.today()
    assert resp.headers["location"] == f"/journal/{today.year}/{today.month:02d}/{today.day:02d}"
    assert "piruetas_session" in resp.cookies
    session.refresh(admin_user)
    assert admin_user.last_login is not None


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


def test_signup_success_redirects_and_sets_session(client, session):
    resp = signup(client, "newuser", "securepass123")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/account/recovery-codes"
    assert "piruetas_session" in resp.cookies
    user = session.exec(select(User).where(User.username == "newuser")).first()
    assert user is not None
    assert user.last_login is not None


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


def test_signup_page_closed_registration(client):
    with patch("app.routers.auth.get_settings") as m:
        m.return_value.registration_open = False
        resp = client.get("/signup")
    assert resp.status_code == 200
    assert b"Registration is not open" in resp.content


def test_signup_post_closed_registration(client):
    get_resp = client.get("/signup")
    csrf_cookie = get_resp.cookies.get("piruetas_login_csrf", "")
    with patch("app.routers.auth.get_settings") as m:
        m.return_value.registration_open = False
        resp = client.post(
            "/signup",
            data={
                "username": "newuser",
                "password": "securepass123",
                "confirm_password": "securepass123",
                "login_csrf_token": csrf_cookie,
            },
        )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/signup"


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


# --- Notification tests ---


def test_signup_triggers_notification(client):
    with patch("app.routers.auth.send_notification", new_callable=AsyncMock) as mock_notify:
        resp = signup(client, "notifyuser", "securepass123")
    assert resp.status_code == 302
    mock_notify.assert_called_once()
    _, title, message = mock_notify.call_args[0]
    assert title == "New signup"
    assert "notifyuser" in message


def test_admin_login_triggers_notification(client, admin_user):
    with patch("app.routers.auth.send_notification", new_callable=AsyncMock) as mock_notify:
        resp = login(client, "admin", "adminpass123")
    assert resp.status_code == 302
    mock_notify.assert_called_once()
    _, title, message = mock_notify.call_args[0]
    assert title == "Admin login"
    assert "admin" in message


def test_regular_login_does_not_trigger_notification(client, regular_user):
    with patch("app.routers.auth.send_notification", new_callable=AsyncMock) as mock_notify:
        resp = login(client, "testuser", "userpass123")
    assert resp.status_code == 302
    mock_notify.assert_not_called()


def test_login_rate_limit_threshold_triggers_notification(client, admin_user):
    test_ip = "10.0.0.99"
    clear_attempts(test_ip)
    try:
        with (
            patch("app.routers.auth.send_notification", new_callable=AsyncMock) as mock_notify,
            patch("app.routers.auth.record_failed_attempt", return_value=True),
        ):
            resp = login(client, "admin", "wrongpass")
        assert resp.status_code == 401
        mock_notify.assert_called_once()
        _, title, _ = mock_notify.call_args[0]
        assert title == "Rate limit hit"
    finally:
        clear_attempts(test_ip)


def test_login_below_rate_limit_threshold_no_notification(client, admin_user):
    with (
        patch("app.routers.auth.send_notification", new_callable=AsyncMock) as mock_notify,
        patch("app.routers.auth.record_failed_attempt", return_value=False),
    ):
        resp = login(client, "admin", "wrongpass")
    assert resp.status_code == 401
    mock_notify.assert_not_called()


def test_signup_validation_error_rate_limit_triggers_notification(client):
    with (
        patch("app.routers.auth.send_notification", new_callable=AsyncMock) as mock_notify,
        patch("app.routers.auth.record_failed_attempt", return_value=True),
    ):
        resp = signup(client, "a!", "securepass123")
    assert resp.status_code == 400
    mock_notify.assert_called_once()
    _, title, _ = mock_notify.call_args[0]
    assert title == "Rate limit hit"


def test_signup_validation_error_below_threshold_no_notification(client):
    with (
        patch("app.routers.auth.send_notification", new_callable=AsyncMock) as mock_notify,
        patch("app.routers.auth.record_failed_attempt", return_value=False),
    ):
        resp = signup(client, "a!", "securepass123")
    assert resp.status_code == 400
    mock_notify.assert_not_called()


# --- record_failed_attempt return value tests ---


def test_record_failed_attempt_returns_false_below_threshold():
    ip = "192.168.99.1"
    clear_attempts(ip)
    try:
        from app.rate_limit import record_failed_attempt

        for _ in range(MAX_ATTEMPTS - 1):
            result = record_failed_attempt(ip)
        assert result is False
    finally:
        clear_attempts(ip)


def test_record_failed_attempt_returns_true_at_threshold():
    ip = "192.168.99.2"
    clear_attempts(ip)
    try:
        from app.rate_limit import record_failed_attempt

        result = None
        for _ in range(MAX_ATTEMPTS):
            result = record_failed_attempt(ip)
        assert result is True
    finally:
        clear_attempts(ip)


def test_record_failed_attempt_returns_false_above_threshold():
    ip = "192.168.99.3"
    clear_attempts(ip)
    try:
        from app.rate_limit import record_failed_attempt

        for _ in range(MAX_ATTEMPTS + 1):
            result = record_failed_attempt(ip)
        assert result is False
    finally:
        clear_attempts(ip)
