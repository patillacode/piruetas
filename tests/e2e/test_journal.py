import base64
from datetime import date

import httpx
from playwright.sync_api import expect
from sqlmodel import Session

from app.database import get_engine
from app.models import Entry

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


def test_delete_entry_via_modal(authenticated_page, live_server, seed_user):
    _seed_entry(seed_user.id)
    authenticated_page.goto(f"{live_server}/journal/2020/01/15")
    authenticated_page.wait_for_load_state("networkidle")

    is_mobile = (authenticated_page.viewport_size or {}).get("width", 1280) < 768
    if is_mobile:
        authenticated_page.click("#mobile-menu-btn")
        authenticated_page.wait_for_function(
            "() => !document.getElementById('mobile-sheet').hidden"
        )
        authenticated_page.click("#sheet-delete-btn")
    else:
        authenticated_page.click("#delete-btn")

    authenticated_page.wait_for_function("() => !document.getElementById('delete-modal').hidden")
    authenticated_page.click("#delete-modal-confirm")
    authenticated_page.wait_for_url(f"{live_server}/journal/**")

    resp = authenticated_page.request.get(f"{live_server}/journal/2020/01/15")
    assert "Hello world" not in resp.text()


def test_journal_mobile_viewport(authenticated_page, live_server, seed_user):
    _seed_entry(seed_user.id)
    is_mobile = (authenticated_page.viewport_size or {}).get("width", 1280) < 768
    if not is_mobile:
        return  # Only assert on mobile param
    authenticated_page.goto(f"{live_server}/journal/2020/01/15")
    authenticated_page.wait_for_load_state("networkidle")
    expect(authenticated_page.locator(".tiptap, [contenteditable]")).to_be_visible()
