from playwright.sync_api import Page


def test_admin_dashboard_loads(admin_page: Page, live_server: str, seed_admin):
    admin_page.goto(f"{live_server}/admin/")
    admin_page.wait_for_selector("text=testadmin")
    assert admin_page.locator("text=testadmin").count() >= 1


def test_create_user(admin_page: Page, live_server: str, seed_admin):
    admin_page.goto(f"{live_server}/admin/users/new")
    admin_page.fill('input[name="username"]', "newuser_e2e")
    admin_page.fill('input[name="password"]', "newpassword123")
    admin_page.click('button[type="submit"]')
    admin_page.wait_for_url(f"{live_server}/admin/")
    assert admin_page.locator("text=newuser_e2e").count() >= 1


def test_delete_user(admin_page: Page, live_server: str, seed_admin, seed_user):
    user_id = seed_user.id
    admin_page.goto(f"{live_server}/admin/")
    admin_page.wait_for_selector(f'form[action="/admin/users/{user_id}/delete"]')
    admin_page.evaluate("window.onbeforeunload = null")
    admin_page.on("dialog", lambda dialog: dialog.accept())
    admin_page.click(f'form[action="/admin/users/{user_id}/delete"] button[type="submit"]')
    admin_page.wait_for_url(f"{live_server}/admin/")
    assert admin_page.locator(f"text={seed_user.username}").count() == 0


def test_reset_user_password(admin_page: Page, live_server: str, seed_admin, seed_user):
    user_id = seed_user.id
    admin_page.goto(f"{live_server}/admin/")
    admin_page.evaluate(f"document.getElementById('reset-{user_id}').style.display='block'")
    admin_page.fill(
        f'form[action="/admin/users/{user_id}/reset-password"] input[name="new_password"]',
        "newpass456",
    )
    admin_page.click(f'form[action="/admin/users/{user_id}/reset-password"] button[type="submit"]')
    admin_page.wait_for_url(f"{live_server}/admin/")


def test_non_admin_blocked(authenticated_page: Page, live_server: str, seed_user):
    response = authenticated_page.request.get(f"{live_server}/admin/")
    assert response.status == 403
