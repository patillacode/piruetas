from playwright.sync_api import Page


def test_admin_dashboard_loads(admin_page: Page, live_server: str, seed_admin):
    admin_page.goto(f"{live_server}/admin/")
    admin_page.wait_for_selector("text=testadmin")
    assert admin_page.locator("text=testadmin").count() >= 1


def test_delete_user(admin_page: Page, live_server: str, seed_admin, seed_user):
    admin_page.goto(f"{live_server}/admin/")
    admin_page.locator(f'.btn-details[data-username="{seed_user.username}"]').click()
    admin_page.wait_for_selector("#user-modal", state="visible")
    admin_page.click("#modal-delete-btn")
    admin_page.wait_for_selector("#modal-delete-confirm", state="visible")
    admin_page.click('#modal-delete-form button[type="submit"]')
    admin_page.wait_for_url(f"{live_server}/admin/")
    assert admin_page.locator(f"text={seed_user.username}").count() == 0


def test_non_admin_blocked(authenticated_page: Page, live_server: str, seed_user):
    response = authenticated_page.request.get(f"{live_server}/admin/")
    assert response.status == 403
