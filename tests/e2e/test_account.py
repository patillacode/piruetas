from playwright.sync_api import expect


def test_account_page_loads(authenticated_page, live_server):
    page = authenticated_page
    page.goto(f"{live_server}/account")
    expect(page).to_have_title("Account — Piruetas")
    expect(page.locator('input[name="current_password"]')).to_be_visible()
    expect(page.locator('input[name="new_password"]')).to_be_visible()


def test_password_change_success(authenticated_page, live_server):
    page = authenticated_page
    page.goto(f"{live_server}/account")
    page.fill('input[name="current_password"]', "testpassword123")
    page.fill('input[name="new_password"]', "newpassword456")
    page.fill('input[name="confirm_password"]', "newpassword456")
    page.click('form[action="/account/password"] button[type="submit"]')
    expect(page.locator("text=Password changed successfully.")).to_be_visible()


def test_password_change_wrong_current(authenticated_page, live_server):
    page = authenticated_page
    page.goto(f"{live_server}/account")
    page.fill('input[name="current_password"]', "wrongpassword")
    page.fill('input[name="new_password"]', "newpassword456")
    page.fill('input[name="confirm_password"]', "newpassword456")
    page.click('form[action="/account/password"] button[type="submit"]')
    expect(page.locator("text=Current password is incorrect.")).to_be_visible()
