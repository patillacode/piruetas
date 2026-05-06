from playwright.sync_api import Page


def test_admin_dashboard_loads(admin_page: Page, live_server: str, seed_admin):
    admin_page.goto(f"{live_server}/admin/")
    admin_page.wait_for_selector("text=testadmin")
    assert admin_page.locator("text=testadmin").count() >= 1


def test_admin_dashboard_shows_all_users(admin_page: Page, live_server: str, seed_admin, seed_user):
    admin_page.goto(f"{live_server}/admin/")
    admin_page.wait_for_load_state("networkidle")
    assert admin_page.locator(f"text={seed_user.username}").count() >= 1
    assert admin_page.locator(f"text={seed_admin.username}").count() >= 1


def test_non_admin_blocked(authenticated_page: Page, live_server: str, seed_user):
    response = authenticated_page.request.get(f"{live_server}/admin/")
    assert response.status == 403


def test_unauthenticated_admin_blocked(page: Page, live_server: str):
    import httpx

    response = httpx.get(f"{live_server}/admin/", follow_redirects=False)
    assert response.status_code in (302, 403)
