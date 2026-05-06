import re

from playwright.sync_api import expect


def test_demo_user_cannot_change_password(demo_page, live_server):
    page = demo_page
    page.goto(f"{live_server}/account")
    page.fill('input[name="current_password"]', "demopassword123")
    page.fill('input[name="new_password"]', "newpassword456")
    page.fill('input[name="confirm_password"]', "newpassword456")
    page.click('form[action="/account/password"] button[type="submit"]')
    expect(page.locator("text=Password change is disabled for the demo account.")).to_be_visible()


def test_demo_user_cannot_access_recovery_codes(demo_page, live_server):
    page = demo_page
    page.goto(f"{live_server}/account/recovery-codes")
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r".*/account$"), timeout=5000)


def test_demo_user_cannot_regenerate_recovery_codes(demo_page, live_server):
    page = demo_page
    page.goto(f"{live_server}/account/recovery-codes")
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(re.compile(r".*/account$"), timeout=5000)
