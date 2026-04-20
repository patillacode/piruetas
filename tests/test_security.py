from tests.conftest import get_csrf, login

from app.rate_limit import _attempts


def _clear_rate_limit():
    with __import__("app.rate_limit", fromlist=["_lock"])._lock:
        _attempts.clear()


def test_404_returns_custom_page(client):
    resp = client.get("/this-does-not-exist")
    assert resp.status_code == 404
    assert b"Page not found" in resp.content


def test_security_headers_present(client):
    resp = client.get("/login")
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert "content-security-policy" in resp.headers


def test_csrf_rejection_on_logout(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.post("/logout", data={"csrf_token": "invalid"})
    assert resp.status_code == 403


def test_csrf_rejection_on_admin_post(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.post(
        "/admin/users/new",
        data={"username": "x", "password": "y", "csrf_token": "bad"},
    )
    assert resp.status_code == 403


def _login_attempt(client, username, password):
    """POST to /login with a fresh CSRF token (for rate limit testing)."""
    get_resp = client.get("/login")
    csrf = get_resp.cookies.get("piruetas_login_csrf", "")
    return client.post("/login", data={"username": username, "password": password, "login_csrf_token": csrf})


def test_rate_limit_blocks_after_threshold(client):
    _clear_rate_limit()
    for _ in range(10):
        _login_attempt(client, "nobody", "wrong")
    resp = _login_attempt(client, "nobody", "wrong")
    assert resp.status_code == 429
    assert b"Too many" in resp.content
    _clear_rate_limit()


def test_rate_limit_clears_on_success(client, admin_user):
    _clear_rate_limit()
    for _ in range(5):
        _login_attempt(client, "admin", "wrong")
    resp = login(client, "admin", "adminpass123")
    assert resp.status_code == 302
    _clear_rate_limit()


def test_permissions_policy_header(client):
    resp = client.get("/login")
    assert "permissions-policy" in resp.headers
    pp = resp.headers["permissions-policy"]
    assert "camera=()" in pp
    assert "microphone=()" in pp
    assert "geolocation=()" in pp


def test_hsts_absent_without_secure_cookies(client):
    resp = client.get("/login")
    assert "strict-transport-security" not in resp.headers


# Task 2: session_version
from app.auth import make_session_token, parse_session_token


def test_session_token_includes_version():
    token = make_session_token(
        user_id=1, is_admin=False, session_version=0, secret_key="test-secret-key-not-for-production"
    )
    result = parse_session_token(token, "test-secret-key-not-for-production")
    assert result is not None
    user_id, is_admin, version = result
    assert user_id == 1
    assert is_admin is False
    assert version == 0


def test_stale_session_version_rejected(client, session, regular_user):
    login(client, "testuser", "userpass123")
    regular_user.session_version = 1
    session.add(regular_user)
    session.commit()
    resp = client.get("/journal/2025/01/01")
    assert resp.status_code == 302
    assert "/login" in resp.headers["location"]


# Task 3: session invalidation on password reset/change
def test_admin_password_reset_increments_session_version(client, session, admin_user, regular_user):
    login(client, "admin", "adminpass123")
    csrf = get_csrf(client)
    client.post(
        f"/admin/users/{regular_user.id}/reset-password",
        data={"new_password": "newpassword123", "csrf_token": csrf},
    )
    session.refresh(regular_user)
    assert regular_user.session_version == 1


def test_self_password_change_increments_version_and_reissues_cookie(client, session, regular_user):
    login(client, "testuser", "userpass123")
    old_cookie = client.cookies.get("piruetas_session")
    csrf = get_csrf(client)
    resp = client.post(
        "/account/password",
        data={
            "current_password": "userpass123",
            "new_password": "newpassword456",
            "confirm_password": "newpassword456",
            "csrf_token": csrf,
        },
    )
    assert resp.status_code == 200
    session.refresh(regular_user)
    assert regular_user.session_version == 1
    new_cookie = client.cookies.get("piruetas_session")
    assert new_cookie != old_cookie


# Task 4: Login CSRF
def test_login_csrf_cookie_set_on_get(client):
    resp = client.get("/login")
    assert "piruetas_login_csrf" in resp.cookies


def test_login_blocked_without_csrf_token(client, regular_user):
    client.get("/login")
    resp = client.post("/login", data={"username": "testuser", "password": "userpass123"})
    assert resp.status_code == 403


def test_login_blocked_with_wrong_csrf_token(client, regular_user):
    client.get("/login")
    resp = client.post("/login", data={
        "username": "testuser",
        "password": "userpass123",
        "login_csrf_token": "wrong-token",
    })
    assert resp.status_code == 403


def test_login_succeeds_with_valid_csrf(client, regular_user):
    resp = client.get("/login")
    csrf_cookie = resp.cookies.get("piruetas_login_csrf")
    resp2 = client.post("/login", data={
        "username": "testuser",
        "password": "userpass123",
        "login_csrf_token": csrf_cookie,
    })
    assert resp2.status_code == 302


# Task 5: Magic byte validation
import io


def _make_jpeg() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"\x00" * 100


def _make_png() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def test_upload_rejects_fake_mime_type(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/upload",
        files={"file": ("evil.jpg", io.BytesIO(b"this is not an image"), "image/jpeg")},
    )
    assert resp.status_code == 400


def test_upload_accepts_valid_jpeg(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/upload",
        files={"file": ("photo.jpg", io.BytesIO(_make_jpeg()), "image/jpeg")},
    )
    assert resp.status_code == 200
    assert "url" in resp.json()


def test_upload_accepts_valid_png(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/upload",
        files={"file": ("photo.png", io.BytesIO(_make_png()), "image/png")},
    )
    assert resp.status_code == 200


# Task 6: TRUST_PROXY
def test_get_client_ip_prefers_forwarded_for_when_trust_proxy():
    from app.routers.auth import _get_client_ip
    from unittest.mock import MagicMock

    request = MagicMock()
    request.headers = {"X-Forwarded-For": "203.0.113.1, 10.0.0.1"}
    request.client.host = "127.0.0.1"

    assert _get_client_ip(request, trust_proxy=True) == "203.0.113.1"
    assert _get_client_ip(request, trust_proxy=False) == "127.0.0.1"


# Task 7: CSP nonces
import re


def test_csp_uses_nonce_not_unsafe_inline(client):
    resp = client.get("/login")
    csp = resp.headers.get("content-security-policy", "")
    # script-src should use nonce, not unsafe-inline
    script_src = next((p for p in csp.split(";") if "script-src" in p), "")
    assert "'unsafe-inline'" not in script_src
    assert "nonce-" in script_src


def test_csp_nonce_present_in_html(client):
    resp = client.get("/login")
    csp = resp.headers.get("content-security-policy", "")
    match = re.search(r"'nonce-([a-f0-9]+)'", csp)
    assert match, "No nonce in CSP header"
    nonce = match.group(1)
    assert f'nonce="{nonce}"'.encode() in resp.content


def test_csp_nonce_changes_per_request(client):
    csp1 = client.get("/login").headers.get("content-security-policy", "")
    csp2 = client.get("/login").headers.get("content-security-policy", "")
    n1 = re.search(r"'nonce-([a-f0-9]+)'", csp1).group(1)
    n2 = re.search(r"'nonce-([a-f0-9]+)'", csp2).group(1)
    assert n1 != n2


# Task 8: Image access control
import datetime as _dt


def test_upload_serve_requires_auth(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.post(
        "/upload",
        files={"file": ("photo.jpg", io.BytesIO(_make_jpeg()), "image/jpeg")},
    )
    image_url = resp.json()["url"]
    client.cookies.clear()
    resp2 = client.get(image_url)
    assert resp2.status_code in (401, 302, 403)


def test_upload_serve_allowed_with_valid_share_token(client, session, regular_user):
    from app.models import Entry, Image
    from sqlmodel import select

    login(client, "testuser", "userpass123")
    resp = client.post(
        "/upload",
        files={"file": ("photo.jpg", io.BytesIO(_make_jpeg()), "image/jpeg")},
    )
    image_url = resp.json()["url"]
    user_id = regular_user.id

    entry = Entry(
        user_id=user_id,
        date=_dt.date(2025, 1, 1),
        content=f'<img src="{image_url}">',
        share_token="validsharetoken999",
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)

    image = session.exec(select(Image).where(Image.user_id == user_id)).first()
    image.entry_id = entry.id
    session.add(image)
    session.commit()

    client.cookies.clear()
    resp2 = client.get(f"{image_url}?share_token=validsharetoken999")
    assert resp2.status_code == 200


def test_images_linked_to_entry_on_save(client, session, regular_user):
    from app.models import Image
    from sqlmodel import select

    login(client, "testuser", "userpass123")
    resp = client.post(
        "/upload",
        files={"file": ("photo.jpg", io.BytesIO(_make_jpeg()), "image/jpeg")},
    )
    image_url = resp.json()["url"]

    client.post("/journal/2025/01/01", json={"content": f'<p><img src="{image_url}"></p>'})

    image = session.exec(select(Image).where(Image.user_id == regular_user.id)).first()
    assert image.entry_id is not None


# Task 9: Share token revocation
def test_share_revocation_clears_token(client, session, regular_user):
    login(client, "testuser", "userpass123")
    client.post("/journal/2025/06/15", json={"content": "<p>Secret</p>"})

    share_resp = client.post("/journal/2025/06/15/share")
    token = share_resp.json()["url"].split("/share/")[1]

    client.cookies.clear()
    assert client.get(f"/share/{token}").status_code == 200

    login(client, "testuser", "userpass123")
    revoke = client.request("DELETE", "/journal/2025/06/15/share")
    assert revoke.status_code == 200
    assert revoke.json() == {"revoked": True}

    client.cookies.clear()
    assert client.get(f"/share/{token}").status_code == 404


def test_share_revocation_nonexistent_entry_returns_false(client, regular_user):
    login(client, "testuser", "userpass123")
    resp = client.request("DELETE", "/journal/2025/12/31/share")
    assert resp.status_code == 200
    assert resp.json() == {"revoked": False}
