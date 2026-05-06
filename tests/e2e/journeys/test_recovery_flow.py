"""
Journey: user registers → gets recovery codes → uses a code to reset forgotten password → logs in
"""

import re

from playwright.sync_api import Page, expect

from tests.e2e.journeys.conftest import register_user


def test_full_recovery_flow(page: Page, live_server: str, registration_enabled, unique_username):
    password = "originalpass99"
    codes = register_user(page, registration_enabled, unique_username, password)
    assert len(codes) == 12

    page.goto(f"{live_server}/forgot-password")
    page.fill('input[name="username"]', unique_username)
    page.fill('input[name="recovery_code"]', codes[0])
    page.fill('input[name="new_password"]', "newpassword456")
    page.fill('input[name="confirm_password"]', "newpassword456")
    page.click('button[type="submit"]')
    expect(page).to_have_url(re.compile(r".*/login"), timeout=10000)

    page.fill('input[name="username"]', unique_username)
    page.fill('input[name="password"]', "newpassword456")
    page.click('button[type="submit"]')
    expect(page).to_have_url(re.compile(r".*/journal/\d{4}/\d{2}/\d{2}"))
