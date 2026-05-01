from datetime import date as date_type

from sqlmodel import Session

from app.database import get_engine
from app.models import Entry


def _seed_entry(
    user_id: int,
    year: int = 2024,
    month: int = 1,
    day: int = 15,
    content: str = "<p>Test entry</p>",
) -> Entry:
    entry = Entry(
        user_id=user_id,
        date=date_type(year, month, day),
        content=content,
        word_count=2,
    )
    with Session(get_engine()) as session:
        session.add(entry)
        session.commit()
        session.refresh(entry)
    return entry


def _delete_entry(entry_id: int) -> None:
    with Session(get_engine()) as session:
        e = session.get(Entry, entry_id)
        if e:
            session.delete(e)
            session.commit()


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
    body_text = modal_body.inner_text()
    assert "No entries" in body_text

    download_links = page.locator("#export-modal-actions a")
    assert download_links.count() == 0


def test_export_preview_with_entries(authenticated_page, live_server, seed_user):
    page = authenticated_page
    entry = _seed_entry(seed_user.id)
    try:
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
    finally:
        assert entry.id is not None
        _delete_entry(entry.id)


def test_delete_preview_and_cancel(authenticated_page, live_server, seed_user):
    page = authenticated_page
    entry = _seed_entry(seed_user.id)
    try:
        page.goto(f"{live_server}/account/data")
        page.wait_for_load_state("networkidle")

        page.select_option("#delete-scope", "all")
        page.click('#delete-form button[type="submit"]')
        page.wait_for_function("() => !document.getElementById('bulk-delete-modal').hidden")

        modal_body = page.locator("#bulk-delete-modal-body")
        assert modal_body.is_visible()
        assert "1" in modal_body.inner_text()

        warning = page.locator("#bulk-delete-modal-warning")
        assert warning.is_visible()

        page.locator("#bulk-delete-modal-cancel").click()
        page.wait_for_function("() => document.getElementById('bulk-delete-modal').hidden === true")

        with Session(get_engine()) as session:
            still_there = session.get(Entry, entry.id)
            assert still_there is not None
    finally:
        assert entry.id is not None
        _delete_entry(entry.id)


def test_delete_confirm(authenticated_page, live_server, seed_user):
    page = authenticated_page
    entry = _seed_entry(seed_user.id)
    try:
        page.goto(f"{live_server}/account/data")
        page.wait_for_load_state("networkidle")

        page.select_option("#delete-scope", "all")
        page.click('#delete-form button[type="submit"]')
        page.wait_for_function("() => !document.getElementById('bulk-delete-modal').hidden")

        confirm_btn = page.locator("#bulk-delete-modal-actions .btn-danger")
        confirm_btn.click()
        page.wait_for_function("() => document.getElementById('bulk-delete-modal').hidden === true")

        success_el = page.locator("#delete-success")
        assert not success_el.is_hidden()

        page.select_option("#export-scope", "all")
        page.click('#export-form button[type="submit"]')
        page.wait_for_function("() => !document.getElementById('export-modal').hidden")
        body_text = page.locator("#export-modal-body").inner_text()
        assert "No entries" in body_text
    finally:
        with Session(get_engine()) as session:
            e = session.get(Entry, entry.id)
            if e:
                session.delete(e)
                session.commit()


def test_mobile_viewport(authenticated_page, live_server):
    page = authenticated_page
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(f"{live_server}/account/data")
    page.wait_for_load_state("networkidle")

    export_submit = page.locator('#export-form button[type="submit"]')
    delete_submit = page.locator('#delete-form button[type="submit"]')
    assert export_submit.is_visible()
    assert delete_submit.is_visible()

    export_submit.click()
    page.wait_for_function("() => !document.getElementById('export-modal').hidden")
    assert page.locator("#export-modal").is_visible()
