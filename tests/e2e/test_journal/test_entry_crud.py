def test_create_entry(authenticated_page, live_server):
    authenticated_page.goto(f"{live_server}/journal/2021/03/10")
    authenticated_page.wait_for_load_state("networkidle")

    editor = authenticated_page.locator(".ProseMirror")
    editor.click()
    editor.type("My new test entry")

    authenticated_page.wait_for_function(
        "() => document.getElementById('save-toast')?.classList.contains('show')",
        timeout=5000,
    )
    authenticated_page.wait_for_function(
        "() => !document.getElementById('save-toast')?.classList.contains('show')",
        timeout=10000,
    )

    resp = authenticated_page.request.get(f"{live_server}/journal/2021/03/10")
    assert resp.status == 200
    assert "My new test entry" in resp.text()


def test_edit_entry(authenticated_page, live_server, seeded_entry):
    authenticated_page.goto(f"{live_server}/journal/2020/01/15")
    authenticated_page.wait_for_load_state("networkidle")

    editor = authenticated_page.locator(".ProseMirror")
    editor.click()
    editor.press("Control+End")
    editor.type(" Updated")

    authenticated_page.wait_for_function(
        "() => document.getElementById('save-toast')?.classList.contains('show')",
        timeout=5000,
    )
    authenticated_page.wait_for_function(
        "() => !document.getElementById('save-toast')?.classList.contains('show')",
        timeout=10000,
    )

    resp = authenticated_page.request.get(f"{live_server}/journal/2020/01/15")
    assert "Updated" in resp.text()


def test_delete_entry_via_api(authenticated_page, live_server, seeded_entry):
    resp = authenticated_page.request.delete(f"{live_server}/journal/2020/01/15")
    assert resp.json()["deleted"] is True

    check = authenticated_page.request.get(f"{live_server}/journal/2020/01/15")
    assert "Hello world" not in check.text()


def test_delete_entry_via_modal(authenticated_page, live_server, seeded_entry):
    authenticated_page.goto(f"{live_server}/journal/2020/01/15")
    authenticated_page.wait_for_load_state("networkidle")

    is_mobile = (authenticated_page.viewport_size or {}).get("width", 1280) < 768
    if is_mobile:
        authenticated_page.click("#mobile-menu-btn")
        authenticated_page.wait_for_function(
            "() => !document.getElementById('mobile-sheet').hidden"
        )
        authenticated_page.click("#sheet-delete-btn")
    else:
        authenticated_page.click("#delete-btn")

    authenticated_page.wait_for_function("() => !document.getElementById('delete-modal').hidden")
    authenticated_page.click("#delete-modal-confirm")
    authenticated_page.wait_for_url(f"{live_server}/journal/**")

    resp = authenticated_page.request.get(f"{live_server}/journal/2020/01/15")
    assert "Hello world" not in resp.text()
