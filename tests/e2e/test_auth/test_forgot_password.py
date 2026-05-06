import re

from playwright.sync_api import Page, expect


def test_forgot_password_page_loads(page: Page, live_server):
    page.goto(f"{live_server}/forgot-password")
    expect(page.locator('input[name="username"]')).to_be_visible()
    expect(page.locator('input[name="recovery_code"]')).to_be_visible()
    expect(page.locator('input[name="new_password"]')).to_be_visible()
    expect(page.locator('input[name="confirm_password"]')).to_be_visible()


def test_forgot_password_success(page: Page, live_server, seed_recovery_codes):
    code = seed_recovery_codes[0]
    page.goto(f"{live_server}/forgot-password")
    page.fill('input[name="username"]', "testuser")
    page.fill('input[name="recovery_code"]', code)
    page.fill('input[name="new_password"]', "newpassword456")
    page.fill('input[name="confirm_password"]', "newpassword456")
    page.click('button[type="submit"]')
    expect(page).to_have_url(re.compile(r".*/login"), timeout=10000)


def test_forgot_password_invalid_code(page: Page, live_server, seed_user):
    page.goto(f"{live_server}/forgot-password")
    page.fill('input[name="username"]', "testuser")
    page.fill('input[name="recovery_code"]', "XXXX-XXXX-XXXX")
    page.fill('input[name="new_password"]', "newpassword456")
    page.fill('input[name="confirm_password"]', "newpassword456")
    page.click('button[type="submit"]')
    expect(page.locator("text=Invalid username or recovery code")).to_be_visible()


def test_forgot_password_unknown_username(page: Page, live_server):
    page.goto(f"{live_server}/forgot-password")
    page.fill('input[name="username"]', "nonexistentuser")
    page.fill('input[name="recovery_code"]', "XXXX-XXXX-XXXX")
    page.fill('input[name="new_password"]', "newpassword456")
    page.fill('input[name="confirm_password"]', "newpassword456")
    page.click('button[type="submit"]')
    expect(page.locator("text=Invalid username or recovery code")).to_be_visible()
