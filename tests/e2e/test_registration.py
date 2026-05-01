import re
import uuid

import httpx
import pytest
from playwright.sync_api import Page, expect

# ── Registration closed (default server state) ────────────────────────────────


def test_signup_cta_shows_coming_soon(page: Page, live_server):
    page.goto(live_server)
    cta = page.locator(".hero-cta > a.hero-cta-soon")
    expect(cta).to_be_visible()
    expect(cta).to_contain_text("coming soon")


def test_signup_page_shows_closed_message(page: Page, live_server):
    page.goto(f"{live_server}/signup")
    expect(page.locator("form")).to_have_count(0)
    expect(page.locator("body")).to_contain_text("Registration is not open yet")


def test_signup_post_redirects_when_closed(live_server):
    resp = httpx.post(
        f"{live_server}/signup",
        data={
            "username": "x",
            "password": "x",
            "confirm_password": "x",
            "login_csrf_token": "x",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/signup"


# ── Registration open ─────────────────────────────────────────────────────────


def _unique_username() -> str:
    return f"reg_{uuid.uuid4().hex[:8]}"


def _register(page: Page, live_server: str, username: str, password: str = "testpassword123"):
    page.goto(f"{live_server}/signup")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.fill('input[name="confirm_password"]', password)
    page.click('button[type="submit"]')


def test_registration_form_loads(page: Page, registration_enabled):
    page.goto(f"{registration_enabled}/signup")
    expect(page.locator('input[name="username"]')).to_be_visible()
    expect(page.locator('input[name="password"]')).to_be_visible()
    expect(page.locator('input[name="confirm_password"]')).to_be_visible()
    expect(page.locator('button[type="submit"]')).to_be_visible()


def test_registration_success_lands_on_recovery_codes(page: Page, registration_enabled):
    _register(page, registration_enabled, _unique_username())
    expect(page).to_have_url(re.compile(r".*/account/recovery-codes"), timeout=15000)
    expect(page.locator("#codes-text")).to_be_visible()


def test_registration_shows_twelve_codes(page: Page, registration_enabled):
    _register(page, registration_enabled, _unique_username())
    page.wait_for_url(re.compile(r".*/account/recovery-codes"), timeout=15000)
    codes = page.locator("#codes-text").inner_text().strip().split("\n")
    assert len(codes) == 12


def test_registration_username_taken(page: Page, registration_enabled, seed_user):
    page.goto(f"{registration_enabled}/signup")
    page.fill('input[name="username"]', "testuser")
    page.fill('input[name="password"]', "testpassword123")
    page.fill('input[name="confirm_password"]', "testpassword123")
    page.click('button[type="submit"]')
    expect(page.locator("text=Username already taken")).to_be_visible()


# ── Recovery codes page ───────────────────────────────────────────────────────


def _go_to_recovery_codes(page: Page, live_server: str) -> Page:
    _register(page, live_server, _unique_username())
    page.wait_for_url(re.compile(r".*/account/recovery-codes"), timeout=15000)
    return page


def test_recovery_codes_continue_disabled_until_confirmed(page: Page, registration_enabled):
    _go_to_recovery_codes(page, registration_enabled)
    continue_btn = page.locator("#continue-btn")
    assert continue_btn.get_attribute("disabled") is not None
    page.check("#saved-confirm")
    assert continue_btn.get_attribute("disabled") is None


def test_recovery_codes_continue_navigates_to_journal(page: Page, registration_enabled):
    _go_to_recovery_codes(page, registration_enabled)
    page.check("#saved-confirm")
    page.click("#continue-btn")
    expect(page).to_have_url(re.compile(r".*/journal/\d{4}/\d{2}/\d{2}"))


def test_recovery_codes_download(page: Page, registration_enabled):
    _go_to_recovery_codes(page, registration_enabled)
    with page.expect_download() as download_info:
        page.click("#download-codes-link")
    download = download_info.value
    assert download.suggested_filename == "piruetas-recovery-codes.txt"


def test_recovery_codes_copy_button(page: Page, registration_enabled, browser_name: str):
    if browser_name == "firefox":
        pytest.skip("clipboard permissions not supported in Firefox via Playwright")
    page.context.grant_permissions(
        ["clipboard-read", "clipboard-write"],
        origin=registration_enabled,
    )
    _go_to_recovery_codes(page, registration_enabled)
    page.click("#copy-codes-btn")
    page.wait_for_function(
        "() => document.getElementById('copy-codes-btn')?.textContent?.includes('Copied')",
        timeout=3000,
    )
