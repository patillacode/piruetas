import re

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
    expect(page.locator(".pricing-grid li")).to_have_count(4)


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


def test_pricing_section_shows_features(page: Page, live_server):
    page.goto(live_server)
    expect(page.locator(".pricing-grid")).to_contain_text("Journal entries")
    expect(page.locator(".pricing-grid")).to_contain_text("Image uploads")


# --- Mobile viewport ---


def test_landing_mobile_viewport(page: Page, live_server):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(live_server)
    expect(page.locator(".hero")).to_be_visible()
    expect(page.locator(".features-section")).to_be_visible()
    expect(page.locator(".pricing-grid")).to_be_visible()
