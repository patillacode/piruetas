from playwright.sync_api import Page, expect


def test_locale_switch_to_spanish(page: Page, live_server):
    page.goto(live_server)
    expect(page.locator('a.hero-cta-secondary[href="/login"]')).to_contain_text("Log in")
    page.select_option("#lang-select", "es")
    page.wait_for_load_state("load")
    expect(page.locator('a.hero-cta-secondary[href="/login"]')).to_contain_text("Iniciar sesión")
    page.goto(f"{live_server}/locale/en")


def test_locale_switch_to_english(page: Page, live_server):
    page.goto(f"{live_server}/locale/es")
    page.wait_for_load_state("load")
    page.goto(live_server)
    expect(page.locator('a.hero-cta-secondary[href="/login"]')).to_contain_text("Iniciar sesión")
    page.select_option("#lang-select", "en")
    page.wait_for_load_state("load")
    expect(page.locator('a.hero-cta-secondary[href="/login"]')).to_contain_text("Log in")


def test_locale_persists_across_navigation(page: Page, live_server):
    page.goto(live_server)
    page.select_option("#lang-select", "es")
    page.wait_for_load_state("networkidle")
    page.goto(f"{live_server}/login")
    page.wait_for_load_state("networkidle")
    assert (
        "Iniciar" in page.locator("body").inner_text()
        or "Contraseña" in page.locator("body").inner_text()
    )
    page.goto(f"{live_server}/locale/en")
