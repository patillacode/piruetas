"""
Journey: user registers → writes entries → admin opens Details modal → sees correct stats →
         admin deletes user
"""

from playwright.sync_api import Page

from tests.e2e.journeys.conftest import register_user


def test_user_stats_and_admin_delete_journey(
    page: Page,
    admin_page: Page,
    live_server: str,
    seed_admin,
    registration_enabled,
    unique_username,
):
    register_user(page, registration_enabled, unique_username)

    page.goto(f"{live_server}/journal/2023/04/10")
    page.wait_for_load_state("networkidle")
    editor = page.locator(".ProseMirror")
    editor.click()
    editor.type("First entry by new user")
    page.wait_for_function(
        "() => document.getElementById('save-toast')?.classList.contains('show')",
        timeout=5000,
    )
    page.wait_for_function(
        "() => !document.getElementById('save-toast')?.classList.contains('show')",
        timeout=10000,
    )

    admin_page.goto(f"{live_server}/admin/")
    admin_page.wait_for_load_state("networkidle")
    admin_page.locator(f'.btn-details[data-username="{unique_username}"]').click()
    admin_page.wait_for_selector("#user-modal", state="visible")

    entries_text = admin_page.locator("#modal-entries").inner_text()
    assert "1" in entries_text

    admin_page.click("#modal-delete-btn")
    admin_page.wait_for_selector("#modal-delete-confirm", state="visible")
    admin_page.click('#modal-delete-form button[type="submit"]')
    admin_page.wait_for_url(f"{live_server}/admin/")

    assert admin_page.locator(f"text={unique_username}").count() == 0
