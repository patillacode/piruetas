import datetime

from playwright.sync_api import expect


def test_user_banner_visible_for_demo(demo_page, live_server):
    today = datetime.date.today()
    demo_page.goto(f"{live_server}/journal/{today.year}/{today.month:02d}/{today.day:02d}")
    demo_page.wait_for_load_state("networkidle")
    banner = demo_page.locator(".user-banner")
    expect(banner).to_be_visible()
    expect(banner).to_contain_text("demo account")


def test_user_banner_not_visible_for_regular_user(authenticated_page, live_server):
    today = datetime.date.today()
    authenticated_page.goto(f"{live_server}/journal/{today.year}/{today.month:02d}/{today.day:02d}")
    authenticated_page.wait_for_load_state("networkidle")
    assert authenticated_page.locator(".user-banner").count() == 0
