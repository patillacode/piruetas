import datetime

from tests.conftest import login


def test_get_journal_today(client, admin_user):
    login(client, "admin", "adminpass123")
    today = datetime.date.today()
    resp = client.get(f"/journal/{today.year}/{today.month:02d}/{today.day:02d}")
    assert resp.status_code == 200
    assert b"Piruetas" in resp.content


def test_autosave_creates_entry(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.post(
        "/journal/2026/01/15",
        json={"content": "<p>Hello world</p>", "word_count": 2},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["saved"] is True
    assert "updated_at" in data


def test_autosave_updates_entry(client, admin_user):
    login(client, "admin", "adminpass123")
    client.post("/journal/2026/01/15", json={"content": "<p>First</p>", "word_count": 1})
    resp = client.post("/journal/2026/01/15", json={"content": "<p>Updated</p>", "word_count": 1})
    assert resp.status_code == 200
    assert resp.json()["saved"] is True


def test_delete_entry(client, admin_user):
    login(client, "admin", "adminpass123")
    client.post("/journal/2026/01/20", json={"content": "<p>Delete me</p>", "word_count": 2})
    resp = client.request("DELETE", "/journal/2026/01/20")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


def test_calendar_endpoint(client, admin_user):
    login(client, "admin", "adminpass123")
    client.post("/journal/2026/04/01", json={"content": "<p>April first</p>", "word_count": 2})
    resp = client.get("/calendar/2026/4")
    assert resp.status_code == 200
    data = resp.json()
    assert 1 in data["days"]


def test_invalid_date_returns_404(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.get("/journal/2026/13/99")
    assert resp.status_code == 404


def test_users_cannot_see_each_others_entries(client, session, admin_user, regular_user):
    """Admin creates an entry; regular user's calendar should not include it."""
    from tests.conftest import login as do_login

    do_login(client, "admin", "adminpass123")
    client.post("/journal/2026/04/01", json={"content": "<p>Admin secret</p>", "word_count": 2})
    client.post("/logout")
    do_login(client, "testuser", "userpass123")
    resp = client.get("/calendar/2026/4")
    assert 1 not in resp.json()["days"]
