"""
Journey: user registers → admin sets banner → user sees it → admin clears it → user doesn't see it
"""

import datetime

from playwright.sync_api import Page, expect

from tests.e2e.journeys.conftest import register_user


def test_admin_banner_lifecycle(
    page: Page,
    admin_page: Page,
    live_server: str,
    seed_admin,
    registration_enabled,
    unique_username,
):
    register_user(page, registration_enabled, unique_username)

    admin_page.goto(f"{live_server}/admin/")
    admin_page.locator(f'.btn-details[data-username="{unique_username}"]').click()
    admin_page.wait_for_selector("#user-modal", state="visible")
    admin_page.fill("#modal-banner-text", "Welcome to Piruetas!")
    admin_page.click("#modal-set-banner")
    admin_page.wait_for_function("() => !document.getElementById('modal-feedback').hidden")

    today = datetime.date.today()
    page.goto(f"{live_server}/journal/{today.year}/{today.month:02d}/{today.day:02d}")
    page.wait_for_load_state("networkidle")
    expect(page.locator(".user-banner")).to_contain_text("Welcome to Piruetas!")

    admin_page.click("#modal-clear-banner")
    admin_page.wait_for_function("() => !document.getElementById('modal-feedback').hidden")

    page.reload()
    page.wait_for_load_state("networkidle")
    assert page.locator(".user-banner").count() == 0
