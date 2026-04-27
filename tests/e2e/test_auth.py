import re

from playwright.sync_api import Page, expect

from app.rate_limit import clear_attempts


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
    if (authenticated_page.viewport_size or {}).get("width", 1280) < 768:
        authenticated_page.click("#mobile-menu-btn")
        authenticated_page.wait_for_function("() => !document.getElementById('mobile-sheet').hidden")
        authenticated_page.locator(".form--contents button[type='submit']").click()
    else:
        authenticated_page.click('form.signout-form button[type="submit"]')
    expect(authenticated_page).to_have_url(re.compile(r".*/login"))


def test_locale_switch_to_spanish(page: Page, live_server):
    page.goto(live_server)
    expect(page.locator('a.hero-cta-secondary[href="/login"]')).to_contain_text("Log in")
    page.select_option('#lang-select', 'es')
    page.wait_for_load_state("load")
    expect(page.locator('a.hero-cta-secondary[href="/login"]')).to_contain_text("Iniciar sesión")
    # Reset locale for test isolation
    page.goto(f"{live_server}/locale/en")


def test_rate_limiting(page: Page, live_server, seed_user):
    clear_attempts("127.0.0.1")
    for _ in range(11):
        page.goto(f"{live_server}/login")
        page.fill('input[name="username"]', "testuser")
        page.fill('input[name="password"]', "wrongpassword")
        page.click('button[type="submit"]')
        page.wait_for_load_state("load")
        if page.locator("text=Too many login attempts").is_visible():
            break
    expect(page.locator("text=Too many login attempts")).to_be_visible()
