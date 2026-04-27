import re

import httpx
from playwright.sync_api import Page, expect


def test_landing_no_access_dropdown(page: Page, live_server):
    page.goto(live_server)
    expect(page.locator("#access-toggle")).to_have_count(0)


def test_landing_hero_ctas_unauthenticated(page: Page, live_server):
    page.goto(live_server)
    # Registration is closed by default — button still links to /signup but is muted
    expect(page.locator('.hero-cta > a.hero-cta-primary[href="/signup"]')).to_be_visible()
    expect(page.locator('.hero-cta > a.hero-cta-secondary[href="/login"]')).to_be_visible()


def test_landing_pricing_table_visible(page: Page, live_server):
    page.goto(live_server)
    expect(page.locator(".pricing-grid")).to_be_visible()
    expect(page.locator(".pricing-card")).to_have_count(2)
    # Registration closed by default: coming-soon badge instead of CTA
    expect(page.locator(".pricing-card--featured .pricing-coming-soon")).to_be_visible()
    expect(page.locator(".pricing-card--featured a.hero-cta-primary")).to_have_count(0)


def test_landing_pricing_shows_price(page: Page, live_server):
    page.goto(live_server)
    # Default price is €5/month
    expect(page.locator(".pricing-card--featured .pricing-amount")).to_contain_text("5")
    expect(page.locator(".pricing-card--featured .pricing-period")).to_be_visible()


def test_landing_logged_in_shows_journal_cta(authenticated_page: Page, live_server):
    authenticated_page.goto(f"{live_server}/about")
    expect(authenticated_page.locator('a.hero-cta-primary[href*="/journal/"]')).to_be_visible()
    expect(authenticated_page.locator('a.hero-cta-primary[href="/signup"]')).to_have_count(0)
    expect(authenticated_page.locator('a.hero-cta-secondary[href="/login"]')).to_have_count(0)


def test_landing_logged_in_journal_cta_links_to_today(authenticated_page: Page, live_server):
    authenticated_page.goto(f"{live_server}/about")
    cta = authenticated_page.locator('a.hero-cta-primary[href*="/journal/"]')
    expect(cta).to_be_visible()
    href = cta.get_attribute("href")
    assert href and re.match(r"/journal/\d{4}/\d{2}/\d{2}", href)


# --- Registration closed (default) ---

def test_signup_cta_shows_coming_soon(page: Page, live_server):
    page.goto(live_server)
    cta = page.locator('.hero-cta > a.hero-cta-soon')
    expect(cta).to_be_visible()
    expect(cta).to_contain_text("coming soon")


def test_signup_page_shows_closed_message(page: Page, live_server):
    page.goto(f"{live_server}/signup")
    expect(page.locator("form")).to_have_count(0)
    expect(page.locator("body")).to_contain_text("Registration is not open yet")


def test_signup_post_redirects_when_closed(live_server):
    resp = httpx.post(
        f"{live_server}/signup",
        data={"username": "x", "password": "x", "confirm_password": "x", "login_csrf_token": "x"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/signup"


def test_pricing_paid_shows_coming_soon_badge(page: Page, live_server):
    page.goto(live_server)
    expect(page.locator(".pricing-card--featured .pricing-coming-soon")).to_be_visible()
    expect(page.locator(".pricing-card--featured a.hero-cta-primary")).to_have_count(0)


# --- Mobile viewport ---

def test_landing_mobile_viewport(page: Page, live_server):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(live_server)
    expect(page.locator(".hero")).to_be_visible()
    expect(page.locator(".features-section")).to_be_visible()
    expect(page.locator(".pricing-grid")).to_be_visible()
