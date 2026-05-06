"""
Journey: user writes entry → creates share link → anonymous visitor views it →
         user revokes share → visitor gets 404
"""

import httpx
from playwright.sync_api import Page, expect

from tests.e2e.conftest import _get_auth_cookies


def test_full_share_flow(
    authenticated_page: Page,
    page: Page,
    live_server: str,
    seed_user,
):
    authenticated_page.goto(f"{live_server}/journal/2022/06/01")
    authenticated_page.wait_for_load_state("networkidle")
    editor = authenticated_page.locator(".ProseMirror")
    editor.click()
    editor.type("A shared journal entry for testing")
    authenticated_page.wait_for_function(
        "() => document.getElementById('save-toast')?.classList.contains('show')",
        timeout=5000,
    )
    authenticated_page.wait_for_function(
        "() => !document.getElementById('save-toast')?.classList.contains('show')",
        timeout=10000,
    )

    resp = httpx.post(
        f"{live_server}/journal/2022/06/01/share",
        cookies=_get_auth_cookies(seed_user),
    )
    assert resp.status_code == 200
    share_token = resp.json()["url"].split("/share/")[1]

    page.goto(f"{live_server}/share/{share_token}")
    page.wait_for_load_state("networkidle")
    expect(page.locator("body")).to_contain_text("A shared journal entry for testing")

    httpx.delete(
        f"{live_server}/journal/2022/06/01/share",
        cookies=_get_auth_cookies(seed_user),
    )

    revoke_resp = httpx.get(f"{live_server}/share/{share_token}", follow_redirects=False)
    assert revoke_resp.status_code == 404
