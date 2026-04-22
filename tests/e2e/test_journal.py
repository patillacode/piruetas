import base64
from datetime import date

import httpx
from sqlmodel import Session

from app.auth import SESSION_COOKIE, make_session_token
from app.database import get_engine
from app.models import Entry

TEST_SECRET_KEY = "test-secret-key-for-playwright-e2e"


MINIMAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _seed_entry(user_id: int, content: str = "<p>Hello world</p>") -> Entry:
    entry = Entry(user_id=user_id, date=date(2020, 1, 15), content=content, word_count=2)
    with Session(get_engine()) as session:
        session.add(entry)
        session.commit()
        session.refresh(entry)
    return entry


def test_dashboard_loads(authenticated_page, live_server):
    authenticated_page.goto(live_server)
    authenticated_page.wait_for_url(f"{live_server}/journal/**")
    assert "/journal/" in authenticated_page.url
    assert authenticated_page.locator("#editor").is_visible()
    assert authenticated_page.locator(".date-heading").is_visible()


def test_navigate_to_day(authenticated_page, live_server):
    authenticated_page.goto(f"{live_server}/journal/2023/06/15")
    authenticated_page.wait_for_load_state("networkidle")
    assert authenticated_page.locator("#editor").is_visible()
    assert "2023" in authenticated_page.locator(".date-heading__full").inner_text()


def test_create_entry(authenticated_page, live_server):
    authenticated_page.goto(f"{live_server}/journal/2021/03/10")
    authenticated_page.wait_for_load_state("networkidle")

    editor = authenticated_page.locator(".ProseMirror")
    editor.click()
    editor.type("My new test entry")

    authenticated_page.wait_for_function(
        "() => document.getElementById('save-toast')?.classList.contains('show')",
        timeout=5000,
    )

    toast = authenticated_page.locator("#save-toast")
    assert toast.is_visible()

    authenticated_page.wait_for_function(
        "() => !document.getElementById('save-toast')?.classList.contains('show')",
        timeout=10000,
    )
    authenticated_page.wait_for_load_state("networkidle")

    resp = authenticated_page.request.get(f"{live_server}/journal/2021/03/10")
    assert resp.status == 200
    assert "My new test entry" in resp.text()


def test_edit_entry(authenticated_page, live_server, seed_user):
    _seed_entry(seed_user.id, "<p>Original content</p>")

    authenticated_page.goto(f"{live_server}/journal/2020/01/15")
    authenticated_page.wait_for_load_state("networkidle")

    editor = authenticated_page.locator(".ProseMirror")
    editor.click()
    editor.press("Control+End")
    editor.type(" Updated")

    authenticated_page.wait_for_function(
        "() => document.getElementById('save-toast')?.classList.contains('show')",
        timeout=5000,
    )
    authenticated_page.wait_for_function(
        "() => !document.getElementById('save-toast')?.classList.contains('show')",
        timeout=10000,
    )
    authenticated_page.wait_for_load_state("networkidle")

    resp = authenticated_page.request.get(f"{live_server}/journal/2020/01/15")
    assert "Updated" in resp.text()


def test_delete_entry(authenticated_page, live_server, seed_user):
    _seed_entry(seed_user.id)

    resp = authenticated_page.request.delete(f"{live_server}/journal/2020/01/15")
    assert resp.json()["deleted"] is True

    check = authenticated_page.request.get(f"{live_server}/journal/2020/01/15")
    assert "Hello world" not in check.text()


def test_empty_state(authenticated_page, live_server):
    authenticated_page.goto(f"{live_server}/journal/2000/02/29")
    authenticated_page.wait_for_load_state("networkidle")

    editor = authenticated_page.locator(".ProseMirror")
    assert editor.is_visible()
    assert editor.inner_text().strip() == ""


def test_upload_image(authenticated_page, live_server, seed_user):
    resp = authenticated_page.request.post(
        f"{live_server}/upload",
        multipart={"file": {"name": "test.png", "mimeType": "image/png", "buffer": MINIMAL_PNG}},
    )
    assert resp.status == 200
    data = resp.json()
    assert "url" in data
    image_url = data["url"]
    assert image_url.startswith("/uploads/")

    content = f'<p>Entry with image</p><img src="{image_url}">'
    _seed_entry(seed_user.id, content)

    authenticated_page.goto(f"{live_server}/journal/2020/01/15")
    authenticated_page.wait_for_load_state("networkidle")

    img = authenticated_page.locator('.ProseMirror img[src*="uploads"]')
    assert img.is_visible()


def test_unauthenticated_image_access(live_server, seed_user):
    upload_path = f"/uploads/{seed_user.id}/nonexistent.png"

    resp = httpx.get(f"{live_server}{upload_path}", follow_redirects=False)
    assert resp.status_code in (401, 403)


def test_share_token_image_access(page, live_server, seed_user):
    resp_upload = httpx.post(
        f"{live_server}/upload",
        files={"file": ("test.png", MINIMAL_PNG, "image/png")},
        cookies=_get_auth_cookies(seed_user),
    )
    assert resp_upload.status_code == 200
    image_url = resp_upload.json()["url"]

    content = f'<p>Shared entry</p><img src="{image_url}">'
    _seed_entry(seed_user.id, content)

    assert seed_user.id is not None
    token = make_session_token(
        user_id=seed_user.id,
        is_admin=seed_user.is_admin,
        session_version=seed_user.session_version,
        secret_key=TEST_SECRET_KEY,
    )

    resp_share = httpx.post(
        f"{live_server}/journal/2020/01/15/share",
        cookies={SESSION_COOKIE: token},
    )
    assert resp_share.status_code == 200
    share_token = resp_share.json()["url"].split("/share/")[1]

    page.goto(f"{live_server}/share/{share_token}")
    page.wait_for_load_state("networkidle")
    assert page.locator("body").is_visible()
    assert "Shared entry" in page.locator("body").inner_text()

    img_resp = httpx.get(
        f"{live_server}{image_url}",
        params={"share_token": share_token},
        follow_redirects=False,
    )
    assert img_resp.status_code == 200


def test_share_button_labels(authenticated_page, live_server, seed_user):
    _seed_entry(seed_user.id)

    authenticated_page.goto(f"{live_server}/journal/2020/01/15")
    authenticated_page.wait_for_load_state("networkidle")

    share_btn = authenticated_page.locator("#share-btn")
    assert share_btn.inner_text() == "Share"

    share_btn.click()
    authenticated_page.wait_for_function(
        "() => document.getElementById('share-btn')?.textContent === 'Stop sharing'",
        timeout=5000,
    )
    assert share_btn.inner_text() == "Stop sharing"

    authenticated_page.locator("#share-modal-close").click()
    authenticated_page.wait_for_function(
        "() => document.getElementById('share-modal')?.hidden === true",
        timeout=5000,
    )

    share_btn.click()
    authenticated_page.wait_for_function(
        "() => document.getElementById('unshare-modal')?.hidden === false",
        timeout=5000,
    )
    authenticated_page.locator("#unshare-modal-confirm").click()
    authenticated_page.wait_for_function(
        "() => document.getElementById('share-btn')?.textContent === 'Share'",
        timeout=5000,
    )
    assert share_btn.inner_text() == "Share"


def test_share_legend_label(authenticated_page, live_server, seed_user):
    entry = _seed_entry(seed_user.id)
    with Session(get_engine()) as session:
        db_entry = session.get(Entry, entry.id)
        assert db_entry is not None
        db_entry.share_token = "test-legend-token"
        session.commit()

    authenticated_page.goto(f"{live_server}/journal/2020/01/15")
    authenticated_page.wait_for_load_state("networkidle")

    legend_text = authenticated_page.locator(".calendar-legend .is-shared + span").inner_text()
    assert legend_text == "Shared entry"


def _get_auth_cookies(user) -> dict:
    assert user.id is not None
    token = make_session_token(
        user_id=user.id,
        is_admin=user.is_admin,
        session_version=user.session_version,
        secret_key=TEST_SECRET_KEY,
    )
    return {SESSION_COOKIE: token}
