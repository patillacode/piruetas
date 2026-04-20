import re

from playwright.sync_api import Page, expect


def test_login_success(page: Page, live_server, seed_user):
    page.goto(f"{live_server}/login")
    page.fill('input[name="username"]', "testuser")
    page.fill('input[name="password"]', "testpassword123")
    page.click('button[type="submit"]')
    expect(page).to_have_url(re.compile(r".*/journal/\d{4}/\d{2}/\d{2}"))


def test_login_wrong_password(page: Page, live_server, seed_user):
    page.goto(f"{live_server}/login")
    page.fill('input[name="username"]', "testuser")
    page.fill('input[name="password"]', "wrongpassword")
    page.click('button[type="submit"]')
    expect(page.locator("text=Invalid username or password")).to_be_visible()


def test_unauthenticated_redirect(page: Page, live_server):
    page.goto(f"{live_server}/account")
    expect(page).to_have_url(re.compile(r".*/login"))


def test_logout(authenticated_page: Page, live_server):
    authenticated_page.goto(f"{live_server}/account")
    authenticated_page.click('form[action="/logout"] button[type="submit"]')
    expect(authenticated_page).to_have_url(re.compile(r".*/login"))


def test_rate_limiting(page: Page, live_server, seed_user):
    for _ in range(10):
        page.goto(f"{live_server}/login")
        page.fill('input[name="username"]', "testuser")
        page.fill('input[name="password"]', "wrongpassword")
        page.click('button[type="submit"]')

    page.goto(f"{live_server}/login")
    page.fill('input[name="username"]', "testuser")
    page.fill('input[name="password"]', "wrongpassword")
    page.click('button[type="submit"]')
    expect(page.locator("text=Too many login attempts")).to_be_visible()
