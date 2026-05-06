from playwright.sync_api import Page, expect

from app.rate_limit import clear_attempts


def test_rate_limiting_blocks_after_too_many_failures(page: Page, live_server, seed_user):
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
