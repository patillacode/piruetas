import datetime

from playwright.sync_api import Page, expect
from sqlmodel import Session

from app.database import get_engine
from app.models import User


def _open_user_modal(page: Page, username: str):
    page.locator(f'.btn-details[data-username="{username}"]').click()
    page.wait_for_selector("#user-modal", state="visible")


def test_demo_user_banner_is_visible(demo_page, live_server):
    today = datetime.date.today()
    demo_page.goto(f"{live_server}/journal/{today.year}/{today.month:02d}/{today.day:02d}")
    demo_page.wait_for_load_state("networkidle")
    banner = demo_page.locator(".user-banner")
    expect(banner).to_be_visible()
    expect(banner).to_contain_text("demo account")


def test_regular_user_has_no_banner(authenticated_page, live_server):
    today = datetime.date.today()
    authenticated_page.goto(f"{live_server}/journal/{today.year}/{today.month:02d}/{today.day:02d}")
    authenticated_page.wait_for_load_state("networkidle")
    assert authenticated_page.locator(".user-banner").count() == 0


def test_admin_can_set_banner(admin_page: Page, live_server: str, seed_admin, seed_user):
    admin_page.goto(f"{live_server}/admin/")
    _open_user_modal(admin_page, seed_user.username)

    admin_page.fill("#modal-banner-text", "Test banner message")
    admin_page.click("#modal-set-banner")
    admin_page.wait_for_function("() => !document.getElementById('modal-feedback').hidden")

    with Session(get_engine()) as session:
        user = session.get(User, seed_user.id)
        assert user is not None
        assert user.banner_message == "Test banner message"


def test_admin_can_clear_banner(admin_page: Page, live_server: str, seed_admin, seed_user):
    with Session(get_engine()) as session:
        user = session.get(User, seed_user.id)
        assert user is not None
        user.banner_message = "Existing banner"
        session.commit()

    admin_page.goto(f"{live_server}/admin/")
    _open_user_modal(admin_page, seed_user.username)
    admin_page.click("#modal-clear-banner")
    admin_page.wait_for_function("() => !document.getElementById('modal-feedback').hidden")

    with Session(get_engine()) as session:
        user = session.get(User, seed_user.id)
        assert user is not None
        assert user.banner_message is None


def test_user_sees_admin_set_banner(
    admin_page: Page, authenticated_page: Page, live_server: str, seed_admin, seed_user
):
    admin_page.goto(f"{live_server}/admin/")
    _open_user_modal(admin_page, seed_user.username)
    admin_page.fill("#modal-banner-text", "Hello from admin")
    admin_page.click("#modal-set-banner")
    admin_page.wait_for_function("() => !document.getElementById('modal-feedback').hidden")

    today = datetime.date.today()
    authenticated_page.goto(f"{live_server}/journal/{today.year}/{today.month:02d}/{today.day:02d}")
    authenticated_page.wait_for_load_state("networkidle")
    banner = authenticated_page.locator(".user-banner")
    expect(banner).to_be_visible()
    expect(banner).to_contain_text("Hello from admin")


def test_banner_message_over_300_chars_rejected(
    admin_page: Page, live_server: str, seed_admin, seed_user
):
    admin_page.goto(f"{live_server}/admin/")
    _open_user_modal(admin_page, seed_user.username)
    admin_page.fill("#modal-banner-text", "x" * 301)
    admin_page.click("#modal-set-banner")
    admin_page.wait_for_function("() => !document.getElementById('modal-feedback').hidden")

    with Session(get_engine()) as session:
        user = session.get(User, seed_user.id)
        assert user is not None
        assert user.banner_message is None or len(user.banner_message) <= 300
