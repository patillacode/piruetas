import base64
import datetime

import bcrypt
import httpx
from playwright.sync_api import expect
from sqlmodel import Session

from app.database import get_engine
from app.models import Entry, User
from tests.e2e.conftest import TEST_PASSWORD, _delete_user, _get_auth_cookies

MINIMAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _click_share(page, is_mobile: bool):
    if is_mobile:
        page.click("#mobile-menu-btn")
        page.wait_for_function("() => !document.getElementById('mobile-sheet').hidden")
        page.click("#sheet-share-btn")
    else:
        page.locator("#share-btn").click()


def test_share_page_renders_entry_content(page, live_server, seed_user, seeded_entry):
    resp = httpx.post(
        f"{live_server}/journal/2020/01/15/share",
        cookies=_get_auth_cookies(seed_user),
    )
    assert resp.status_code == 200
    share_token = resp.json()["url"].split("/share/")[1]

    page.goto(f"{live_server}/share/{share_token}")
    page.wait_for_load_state("networkidle")
    expect(page.locator("body")).to_contain_text("Hello world")


def test_share_token_grants_image_access(page, live_server, seed_user, seeded_entry):
    resp_upload = httpx.post(
        f"{live_server}/upload",
        files={"file": ("test.png", MINIMAL_PNG, "image/png")},
        cookies=_get_auth_cookies(seed_user),
    )
    assert resp_upload.status_code == 200
    image_url = resp_upload.json()["url"]

    with Session(get_engine()) as session:
        entry = session.get(Entry, seeded_entry.id)
        assert entry is not None
        entry.content = f'<p>Shared entry</p><img src="{image_url}">'
        session.commit()

    resp_share = httpx.post(
        f"{live_server}/journal/2020/01/15/share",
        cookies=_get_auth_cookies(seed_user),
    )
    assert resp_share.status_code == 200
    share_token = resp_share.json()["url"].split("/share/")[1]

    img_resp = httpx.get(
        f"{live_server}{image_url}",
        params={"share_token": share_token},
        follow_redirects=False,
    )
    assert img_resp.status_code == 200


def test_share_toggle_flow(authenticated_page, live_server, seeded_entry):
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


def test_share_modal_shows_url(authenticated_page, live_server, seeded_entry):
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


def test_share_revoked_entry_returns_404(page, live_server, seed_user, seeded_entry):
    resp = httpx.post(
        f"{live_server}/journal/2020/01/15/share",
        cookies=_get_auth_cookies(seed_user),
    )
    share_token = resp.json()["url"].split("/share/")[1]

    httpx.delete(
        f"{live_server}/journal/2020/01/15/share",
        cookies=_get_auth_cookies(seed_user),
    )

    page.goto(f"{live_server}/share/{share_token}")
    page.wait_for_load_state("networkidle")
    assert page.title() == "" or "404" in page.content() or page.url.endswith(share_token)
    resp_check = httpx.get(f"{live_server}/share/{share_token}", follow_redirects=False)
    assert resp_check.status_code == 404


def test_share_blocked_for_new_account(live_server):
    hashed = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    user = User(username="fresh_agegate_user", hashed_password=hashed, is_admin=False)
    with Session(get_engine()) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        entry = Entry(
            user_id=user.id,
            date=datetime.date(2020, 2, 1),
            content="<p>Fresh entry</p>",
            word_count=2,
        )
        session.add(entry)
        session.commit()
        session.refresh(user)
        session.expunge(user)

    try:
        resp = httpx.post(
            f"{live_server}/journal/2020/02/01/share",
            cookies=_get_auth_cookies(user),
        )
        assert resp.status_code == 403
    finally:
        _delete_user(user.id)


def test_share_legend_label(authenticated_page, live_server, seeded_entry):
    with Session(get_engine()) as session:
        entry = session.get(Entry, seeded_entry.id)
        assert entry is not None
        entry.share_token = "test-legend-token"
        session.commit()

    authenticated_page.goto(f"{live_server}/journal/2020/01/15")
    authenticated_page.wait_for_load_state("networkidle")

    legend_text = authenticated_page.locator(".calendar-legend .is-shared + span").inner_text()
    assert legend_text == "Shared entry"
