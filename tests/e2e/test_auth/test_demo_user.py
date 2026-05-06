from playwright.sync_api import Page, expect
from sqlmodel import Session, select

from app.database import get_engine
from app.models import User
from app.recovery import create_codes_for_user


def test_demo_user_cannot_reset_password_via_forgot_password(page: Page, live_server):
    with Session(get_engine()) as session:
        demo = session.exec(select(User).where(User.username == "testdemo")).first()
        codes = create_codes_for_user(demo.id, session)
    page.goto(f"{live_server}/forgot-password")
    page.fill('input[name="username"]', "testdemo")
    page.fill('input[name="recovery_code"]', codes[0])
    page.fill('input[name="new_password"]', "newpassword456")
    page.fill('input[name="confirm_password"]', "newpassword456")
    page.click('button[type="submit"]')
    expect(page.locator("text=Invalid username or recovery code")).to_be_visible()
