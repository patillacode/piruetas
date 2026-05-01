import base64
from datetime import date

import httpx
from playwright.sync_api import expect
from sqlmodel import Session

from app.database import get_engine
from app.models import Entry
from tests.e2e.conftest import _get_auth_cookies

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


def _click_share(page, is_mobile: bool):
    if is_mobile:
        page.click("#mobile-menu-btn")
        page.wait_for_function("() => !document.getElementById('mobile-sheet').hidden")
        page.click("#sheet-share-btn")
    else:
        page.locator("#share-btn").click()


def test_share_page_renders_entry_content(page, live_server, seed_user):
    entry_text = "My uniquely identifiable journal entry"
    _seed_entry(seed_user.id, f"<p>{entry_text}</p>")

    resp = httpx.post(
        f"{live_server}/journal/2020/01/15/share",
        cookies=_get_auth_cookies(seed_user),
    )
    assert resp.status_code == 200
    share_token = resp.json()["url"].split("/share/")[1]

    page.goto(f"{live_server}/share/{share_token}")
    page.wait_for_load_state("networkidle")
    expect(page.locator("body")).to_contain_text(entry_text)


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

    resp_share = httpx.post(
        f"{live_server}/journal/2020/01/15/share",
        cookies=_get_auth_cookies(seed_user),
    )
    assert resp_share.status_code == 200
    share_token = resp_share.json()["url"].split("/share/")[1]

    page.goto(f"{live_server}/share/{share_token}")
    page.wait_for_load_state("networkidle")
    assert "Shared entry" in page.locator("body").inner_text()

    img_resp = httpx.get(
        f"{live_server}{image_url}",
        params={"share_token": share_token},
        follow_redirects=False,
    )
    assert img_resp.status_code == 200


def test_share_toggle_flow(authenticated_page, live_server, seed_user):
    _seed_entry(seed_user.id)
    authenticated_page.goto(f"{live_server}/journal/2020/01/15")
    authenticated_page.wait_for_load_state("networkidle")

    is_mobile = (authenticated_page.viewport_size or {}).get("width", 1280) < 768
    share_btn = authenticated_page.locator("#share-btn")
    assert share_btn.get_attribute("aria-label") == "Share"

    _click_share(authenticated_page, is_mobile)
    authenticated_page.wait_for_function(
        "() => document.getElementById('share-btn')?.getAttribute('aria-label') === 'Stop sharing'",
        timeout=5000,
    )
    assert share_btn.get_attribute("aria-label") == "Stop sharing"

    authenticated_page.locator("#share-modal-close").click()
    authenticated_page.wait_for_function(
        "() => document.getElementById('share-modal')?.hidden === true",
        timeout=5000,
    )

    _click_share(authenticated_page, is_mobile)
    authenticated_page.wait_for_function(
        "() => document.getElementById('unshare-modal')?.hidden === false",
        timeout=5000,
    )
    authenticated_page.locator("#unshare-modal-confirm").click()
    authenticated_page.wait_for_function(
        "() => document.getElementById('share-btn')?.getAttribute('aria-label') === 'Share'",
        timeout=5000,
    )
    assert share_btn.get_attribute("aria-label") == "Share"


def test_share_modal_shows_url(authenticated_page, live_server, seed_user):
    _seed_entry(seed_user.id)
    authenticated_page.goto(f"{live_server}/journal/2020/01/15")
    authenticated_page.wait_for_load_state("networkidle")

    is_mobile = (authenticated_page.viewport_size or {}).get("width", 1280) < 768
    _click_share(authenticated_page, is_mobile)
    authenticated_page.wait_for_function(
        "() => !document.getElementById('share-modal').hidden",
        timeout=5000,
    )
    url_input = authenticated_page.locator("#share-modal-url")
    assert url_input.is_visible()
    share_url = url_input.input_value()
    assert "/share/" in share_url


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
