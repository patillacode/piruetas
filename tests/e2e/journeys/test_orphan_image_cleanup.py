"""
Journey: user uploads image (not saved in any entry) → admin runs cleanup task → image is gone
"""

import httpx
from playwright.sync_api import Page

from tests.e2e.conftest import _get_auth_cookies


def test_orphan_image_cleanup_journey(
    admin_page: Page,
    live_server: str,
    seed_admin,
    seed_user,
):
    resp = httpx.post(
        f"{live_server}/upload",
        files={"file": ("orphan.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        cookies=_get_auth_cookies(seed_user),
    )
    assert resp.status_code == 200
    image_url = resp.json()["url"]

    before_resp = httpx.get(f"{live_server}{image_url}", cookies=_get_auth_cookies(seed_user))
    assert before_resp.status_code == 200

    admin_page.goto(f"{live_server}/admin/tasks")
    admin_page.wait_for_load_state("networkidle")
    cleanup_form = admin_page.locator('form[action="/admin/tasks/cleanup-images/run"]')
    cleanup_form.locator('button[type="submit"]').click()
    admin_page.wait_for_url(f"{live_server}/admin/tasks")

    after_resp = httpx.get(f"{live_server}{image_url}", cookies=_get_auth_cookies(seed_user))
    assert after_resp.status_code == 404
