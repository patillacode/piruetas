import re

from playwright.sync_api import expect


def test_account_page_loads(authenticated_page, live_server):
    page = authenticated_page
    page.goto(f"{live_server}/account")
    expect(page).to_have_title("Account — Piruetas")
    expect(page.locator('input[name="current_password"]')).to_be_visible()
    expect(page.locator('input[name="new_password"]')).to_be_visible()


def test_password_change_success(authenticated_page, live_server):
    page = authenticated_page
    page.goto(f"{live_server}/account")
    page.fill('input[name="current_password"]', "testpassword123")
    page.fill('input[name="new_password"]', "newpassword456")
    page.fill('input[name="confirm_password"]', "newpassword456")
    page.click('form[action="/account/password"] button[type="submit"]')
    expect(page.locator("text=Password changed successfully.")).to_be_visible()


def test_password_change_wrong_current(authenticated_page, live_server):
    page = authenticated_page
    page.goto(f"{live_server}/account")
    page.fill('input[name="current_password"]', "wrongpassword")
    page.fill('input[name="new_password"]', "newpassword456")
    page.fill('input[name="confirm_password"]', "newpassword456")
    page.click('form[action="/account/password"] button[type="submit"]')
    expect(page.locator("text=Current password is incorrect.")).to_be_visible()


# ── Recovery codes ────────────────────────────────────────────────────────────


def test_recovery_codes_page_shows_remaining(authenticated_page, live_server, seed_recovery_codes):
    page = authenticated_page
    page.goto(f"{live_server}/account/recovery-codes")
    page.wait_for_load_state("networkidle")
    expect(page.locator("text=12")).to_be_visible()


def test_recovery_code_regeneration_wrong_password(
    authenticated_page, live_server, seed_recovery_codes
):
    page = authenticated_page
    page.goto(f"{live_server}/account/recovery-codes")
    page.fill('input[name="current_password"]', "wrongpassword")
    page.click('form[action="/account/recovery-codes/regenerate"] button[type="submit"]')
    expect(page.locator("text=Current password is incorrect")).to_be_visible()


def test_recovery_code_regeneration_success(authenticated_page, live_server, seed_recovery_codes):
    page = authenticated_page
    page.goto(f"{live_server}/account/recovery-codes")
    page.fill('input[name="current_password"]', "testpassword123")
    page.click('form[action="/account/recovery-codes/regenerate"] button[type="submit"]')
    expect(page).to_have_url(re.compile(r".*/account/recovery-codes"), timeout=15000)
    expect(page.locator("#codes-text")).to_be_visible()
    codes = page.locator("#codes-text").inner_text().strip().split("\n")
    assert len(codes) == 12
