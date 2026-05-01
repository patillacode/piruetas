from playwright.sync_api import Page


def test_admin_dashboard_loads(admin_page: Page, live_server: str, seed_admin):
    admin_page.goto(f"{live_server}/admin/")
    admin_page.wait_for_selector("text=testadmin")
    assert admin_page.locator("text=testadmin").count() >= 1


def test_delete_user(admin_page: Page, live_server: str, seed_admin, seed_user):
    user_id = seed_user.id
    admin_page.goto(f"{live_server}/admin/")
    admin_page.wait_for_selector(f'form[action="/admin/users/{user_id}/delete"]')
    admin_page.evaluate("window.onbeforeunload = null")
    admin_page.on("dialog", lambda dialog: dialog.accept())
    admin_page.click(f'form[action="/admin/users/{user_id}/delete"] button[type="submit"]')
    admin_page.wait_for_url(f"{live_server}/admin/")
    assert admin_page.locator(f"text={seed_user.username}").count() == 0


def test_non_admin_blocked(authenticated_page: Page, live_server: str, seed_user):
    response = authenticated_page.request.get(f"{live_server}/admin/")
    assert response.status == 403
