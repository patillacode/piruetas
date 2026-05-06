import re

from playwright.sync_api import Page, expect


def test_logout(authenticated_page: Page, live_server):
    authenticated_page.goto(f"{live_server}/account")
    if (authenticated_page.viewport_size or {}).get("width", 1280) < 768:
        authenticated_page.click("#mobile-menu-btn")
        authenticated_page.wait_for_function(
            "() => !document.getElementById('mobile-sheet').hidden"
        )
        authenticated_page.locator(".form--contents button[type='submit']").click()
    else:
        authenticated_page.click('form.signout-form button[type="submit"]')
    expect(authenticated_page).to_have_url(re.compile(r".*/login"))


def test_logout_clears_session(authenticated_page: Page, live_server):
    authenticated_page.goto(f"{live_server}/account")
    if (authenticated_page.viewport_size or {}).get("width", 1280) < 768:
        authenticated_page.click("#mobile-menu-btn")
        authenticated_page.wait_for_function(
            "() => !document.getElementById('mobile-sheet').hidden"
        )
        authenticated_page.locator(".form--contents button[type='submit']").click()
    else:
        authenticated_page.click('form.signout-form button[type="submit"]')
    expect(authenticated_page).to_have_url(re.compile(r".*/login"))
    authenticated_page.goto(f"{live_server}/account")
    expect(authenticated_page).to_have_url(re.compile(r".*/login"))
