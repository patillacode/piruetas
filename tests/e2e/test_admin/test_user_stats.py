from playwright.sync_api import Page


def _open_user_modal(page: Page, username: str):
    page.locator(f'.btn-details[data-username="{username}"]').click()
    page.wait_for_selector("#user-modal", state="visible")


def test_stats_modal_opens_for_user(admin_page: Page, live_server: str, seed_admin, seed_user):
    admin_page.goto(f"{live_server}/admin/")
    _open_user_modal(admin_page, seed_user.username)
    assert admin_page.locator("#user-modal").is_visible()


def test_stats_modal_shows_username_in_title(
    admin_page: Page, live_server: str, seed_admin, seed_user
):
    admin_page.goto(f"{live_server}/admin/")
    _open_user_modal(admin_page, seed_user.username)
    title = admin_page.locator("#user-modal-title").inner_text()
    assert seed_user.username in title


def test_stats_modal_shows_entry_count(
    admin_page: Page, live_server: str, seed_admin, seed_user, seeded_entry
):
    admin_page.goto(f"{live_server}/admin/")
    _open_user_modal(admin_page, seed_user.username)
    entries_text = admin_page.locator("#modal-entries").inner_text()
    assert "1" in entries_text


def test_stats_modal_shows_storage(admin_page: Page, live_server: str, seed_admin, seed_user):
    admin_page.goto(f"{live_server}/admin/")
    _open_user_modal(admin_page, seed_user.username)
    storage_text = admin_page.locator("#modal-storage").inner_text()
    assert storage_text.strip() != ""


def test_stats_modal_shows_last_login(admin_page: Page, live_server: str, seed_admin, seed_user):
    admin_page.goto(f"{live_server}/admin/")
    _open_user_modal(admin_page, seed_user.username)
    last_login_text = admin_page.locator("#modal-last-login").inner_text()
    assert last_login_text.strip() != ""


def test_stats_modal_closes_on_close_button(
    admin_page: Page, live_server: str, seed_admin, seed_user
):
    admin_page.goto(f"{live_server}/admin/")
    _open_user_modal(admin_page, seed_user.username)
    admin_page.click("#modal-close")
    admin_page.wait_for_function("() => document.getElementById('user-modal').hidden === true")
    assert admin_page.locator("#user-modal").is_hidden()
