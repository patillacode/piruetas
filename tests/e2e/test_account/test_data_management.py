from sqlmodel import Session

from app.database import get_engine
from app.models import Entry


def test_data_tab_navigation(authenticated_page, live_server):
    page = authenticated_page
    page.goto(f"{live_server}/account")
    page.wait_for_load_state("networkidle")

    security_link = page.locator('.page-tabs a[href="/account"]')
    data_link = page.locator('.page-tabs a[href="/account/data"]')
    assert security_link.is_visible()
    assert data_link.is_visible()
    assert "active" in (security_link.get_attribute("class") or "")

    data_link.click()
    page.wait_for_url(f"{live_server}/account/data")

    data_link_active = page.locator('.page-tabs a[href="/account/data"]')
    assert "active" in (data_link_active.get_attribute("class") or "")


def test_export_scope_visibility(authenticated_page, live_server):
    page = authenticated_page
    page.goto(f"{live_server}/account/data")
    page.wait_for_load_state("networkidle")

    assert page.is_hidden("#export-year")
    assert page.is_hidden("#export-month")
    assert page.is_hidden("#export-day")

    page.select_option("#export-scope", "year")
    assert not page.is_hidden("#export-year")
    assert page.is_hidden("#export-month")
    assert page.is_hidden("#export-day")

    page.select_option("#export-scope", "month")
    assert not page.is_hidden("#export-year")
    assert not page.is_hidden("#export-month")


def test_export_preview_no_entries(authenticated_page, live_server):
    page = authenticated_page
    page.goto(f"{live_server}/account/data")
    page.wait_for_load_state("networkidle")

    page.select_option("#export-scope", "all")
    page.click('#export-form button[type="submit"]')
    page.wait_for_function("() => !document.getElementById('export-modal').hidden")

    modal_body = page.locator("#export-modal-body")
    assert modal_body.is_visible()
    assert "No entries" in modal_body.inner_text()
    assert page.locator("#export-modal-actions a").count() == 0


def test_export_preview_with_entries(authenticated_page, live_server, seeded_entry):
    page = authenticated_page
    page.goto(f"{live_server}/account/data")
    page.wait_for_load_state("networkidle")

    page.select_option("#export-scope", "all")
    page.click('#export-form button[type="submit"]')
    page.wait_for_function("() => !document.getElementById('export-modal').hidden")

    modal_body = page.locator("#export-modal-body")
    assert "1" in modal_body.inner_text()

    actions = page.locator("#export-modal-actions")
    assert actions.locator("text=Download Text").is_visible()
    assert actions.locator("text=Download JSON").is_visible()


def test_delete_preview_and_cancel(authenticated_page, live_server, seeded_entry):
    page = authenticated_page
    page.goto(f"{live_server}/account/data")
    page.wait_for_load_state("networkidle")

    page.select_option("#delete-scope", "all")
    page.click('#delete-form button[type="submit"]')
    page.wait_for_function("() => !document.getElementById('bulk-delete-modal').hidden")

    modal_body = page.locator("#bulk-delete-modal-body")
    assert modal_body.is_visible()
    assert "1" in modal_body.inner_text()
    assert page.locator("#bulk-delete-modal-warning").is_visible()

    page.locator("#bulk-delete-modal-cancel").click()
    page.wait_for_function("() => document.getElementById('bulk-delete-modal').hidden === true")

    with Session(get_engine()) as session:
        assert session.get(Entry, seeded_entry.id) is not None


def test_delete_confirm_removes_entries(authenticated_page, live_server, seeded_entry):
    page = authenticated_page
    page.goto(f"{live_server}/account/data")
    page.wait_for_load_state("networkidle")

    page.select_option("#delete-scope", "all")
    page.click('#delete-form button[type="submit"]')
    page.wait_for_function("() => !document.getElementById('bulk-delete-modal').hidden")

    page.locator("#bulk-delete-modal-actions .btn-danger").click()
    page.wait_for_function("() => document.getElementById('bulk-delete-modal').hidden === true")

    assert not page.locator("#delete-success").is_hidden()

    page.select_option("#export-scope", "all")
    page.click('#export-form button[type="submit"]')
    page.wait_for_function("() => !document.getElementById('export-modal').hidden")
    assert "No entries" in page.locator("#export-modal-body").inner_text()


def test_data_page_mobile_viewport(authenticated_page, live_server):
    page = authenticated_page
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(f"{live_server}/account/data")
    page.wait_for_load_state("networkidle")

    assert page.locator('#export-form button[type="submit"]').is_visible()
    assert page.locator('#delete-form button[type="submit"]').is_visible()

    page.locator('#export-form button[type="submit"]').click()
    page.wait_for_function("() => !document.getElementById('export-modal').hidden")
    assert page.locator("#export-modal").is_visible()
