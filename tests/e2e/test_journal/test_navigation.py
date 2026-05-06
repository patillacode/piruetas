from playwright.sync_api import expect


def test_dashboard_redirects_to_today(authenticated_page, live_server):
    authenticated_page.goto(live_server)
    authenticated_page.wait_for_url(f"{live_server}/journal/**")
    assert "/journal/" in authenticated_page.url
    assert authenticated_page.locator("#editor").is_visible()
    assert authenticated_page.locator(".date-heading").is_visible()


def test_navigate_to_specific_day(authenticated_page, live_server):
    authenticated_page.goto(f"{live_server}/journal/2023/06/15")
    authenticated_page.wait_for_load_state("networkidle")
    assert authenticated_page.locator("#editor").is_visible()
    assert "2023" in authenticated_page.locator(".date-heading__full").inner_text()


def test_empty_state_shows_blank_editor(authenticated_page, live_server):
    authenticated_page.goto(f"{live_server}/journal/2000/02/29")
    authenticated_page.wait_for_load_state("networkidle")
    editor = authenticated_page.locator(".ProseMirror")
    assert editor.is_visible()
    assert editor.inner_text().strip() == ""


def test_journal_mobile_viewport(authenticated_page, live_server, seeded_entry):
    is_mobile = (authenticated_page.viewport_size or {}).get("width", 1280) < 768
    if not is_mobile:
        return
    authenticated_page.goto(f"{live_server}/journal/2020/01/15")
    authenticated_page.wait_for_load_state("networkidle")
    expect(authenticated_page.locator(".tiptap, [contenteditable]")).to_be_visible()
