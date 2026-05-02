import datetime

from playwright.sync_api import expect


def test_demo_banner_visible(demo_page, live_server):
    today = datetime.date.today()
    demo_page.goto(f"{live_server}/journal/{today.year}/{today.month:02d}/{today.day:02d}")
    demo_page.wait_for_load_state("networkidle")
    banner = demo_page.locator(".demo-banner")
    expect(banner).to_be_visible()
    expect(banner).to_contain_text("demo account")
    expect(banner).to_contain_text("next reset in")


def test_demo_banner_countdown_ticking(demo_page, live_server):
    today = datetime.date.today()
    demo_page.goto(f"{live_server}/journal/{today.year}/{today.month:02d}/{today.day:02d}")
    demo_page.wait_for_function(
        "() => !!document.querySelector('.demo-banner__countdown')?.textContent",
        timeout=3000,
    )
    first = demo_page.locator(".demo-banner__countdown").inner_text()
    demo_page.wait_for_timeout(2000)
    second = demo_page.locator(".demo-banner__countdown").inner_text()
    assert first != second


def test_demo_banner_not_visible_for_regular_user(authenticated_page, live_server):
    today = datetime.date.today()
    authenticated_page.goto(f"{live_server}/journal/{today.year}/{today.month:02d}/{today.day:02d}")
    authenticated_page.wait_for_load_state("networkidle")
    assert authenticated_page.locator(".demo-banner").count() == 0
