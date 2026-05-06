import base64

import httpx
from playwright.sync_api import Page

from tests.e2e.conftest import _get_auth_cookies

MINIMAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def test_tasks_page_loads(admin_page: Page, live_server: str, seed_admin):
    admin_page.goto(f"{live_server}/admin/tasks")
    admin_page.wait_for_load_state("networkidle")
    assert admin_page.locator(".task-card").count() >= 3


def test_tasks_page_shows_all_three_tasks(admin_page: Page, live_server: str, seed_admin):
    admin_page.goto(f"{live_server}/admin/tasks")
    admin_page.wait_for_load_state("networkidle")
    page_text = admin_page.locator("body").inner_text()
    assert "Orphaned image cleanup" in page_text
    assert "Database VACUUM" in page_text
    assert "Recalculate" in page_text


def test_cleanup_images_task_runs(admin_page: Page, live_server: str, seed_admin):
    admin_page.goto(f"{live_server}/admin/tasks")
    admin_page.wait_for_load_state("networkidle")
    cleanup_form = admin_page.locator('form[action="/admin/tasks/cleanup-images/run"]')
    cleanup_form.locator('button[type="submit"]').click()
    admin_page.wait_for_url(f"{live_server}/admin/tasks")
    assert admin_page.locator(".task-card").count() >= 1


def test_vacuum_db_task_runs(admin_page: Page, live_server: str, seed_admin):
    admin_page.goto(f"{live_server}/admin/tasks")
    admin_page.wait_for_load_state("networkidle")
    vacuum_form = admin_page.locator('form[action="/admin/tasks/vacuum-db/run"]')
    vacuum_form.locator('button[type="submit"]').click()
    admin_page.wait_for_url(f"{live_server}/admin/tasks")
    assert admin_page.locator(".task-card").count() >= 1


def test_recalculate_storage_task_runs(admin_page: Page, live_server: str, seed_admin):
    admin_page.goto(f"{live_server}/admin/tasks")
    admin_page.wait_for_load_state("networkidle")
    recalc_form = admin_page.locator('form[action="/admin/tasks/recalculate-storage/run"]')
    recalc_form.locator('button[type="submit"]').click()
    admin_page.wait_for_url(f"{live_server}/admin/tasks")
    assert admin_page.locator(".task-card").count() >= 1


def test_cleanup_images_removes_orphaned_upload(
    admin_page: Page, live_server: str, seed_admin, seed_user
):
    resp = httpx.post(
        f"{live_server}/upload",
        files={"file": ("orphan.png", MINIMAL_PNG, "image/png")},
        cookies=_get_auth_cookies(seed_user),
    )
    assert resp.status_code == 200
    image_url = resp.json()["url"]

    image_resp = httpx.get(f"{live_server}{image_url}", cookies=_get_auth_cookies(seed_user))
    assert image_resp.status_code == 200

    admin_page.goto(f"{live_server}/admin/tasks")
    cleanup_form = admin_page.locator('form[action="/admin/tasks/cleanup-images/run"]')
    cleanup_form.locator('button[type="submit"]').click()
    admin_page.wait_for_url(f"{live_server}/admin/tasks")

    after_resp = httpx.get(f"{live_server}{image_url}", cookies=_get_auth_cookies(seed_user))
    assert after_resp.status_code == 404
