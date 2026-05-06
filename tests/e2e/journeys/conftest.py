import re
import uuid

import pytest
from playwright.sync_api import Page, expect


def register_user(page: Page, live_server: str, username: str, password: str = "testpassword123"):
    page.goto(f"{live_server}/signup")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.fill('input[name="confirm_password"]', password)
    page.click('button[type="submit"]')
    expect(page).to_have_url(re.compile(r".*/account/recovery-codes"), timeout=15000)
    codes_text = page.locator("#codes-text").inner_text().strip().split("\n")
    page.check("#saved-confirm")
    page.click("#continue-btn")
    expect(page).to_have_url(re.compile(r".*/journal/\d{4}/\d{2}/\d{2}"), timeout=10000)
    return codes_text


@pytest.fixture()
def unique_username():
    return f"journey_{uuid.uuid4().hex[:8]}"
