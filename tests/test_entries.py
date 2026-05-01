import datetime
import io

from app.models import Entry
from tests.conftest import get_csrf, login


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


def test_share_creates_url(client, admin_user):
    login(client, "admin", "adminpass123")
    client.post("/journal/2026/04/10", json={"content": "<p>Shareable</p>", "word_count": 1})
    resp = client.post("/journal/2026/04/10/share")
    assert resp.status_code == 200
    data = resp.json()
    assert "url" in data
    assert data["url"].startswith("/share/")


def test_share_is_idempotent(client, admin_user):
    login(client, "admin", "adminpass123")
    client.post("/journal/2026/04/10", json={"content": "<p>Same token</p>", "word_count": 2})
    url1 = client.post("/journal/2026/04/10/share").json()["url"]
    url2 = client.post("/journal/2026/04/10/share").json()["url"]
    assert url1 == url2


def test_share_missing_entry_returns_404(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.post("/journal/2026/04/10/share")
    assert resp.status_code == 404


def test_share_url_accessible_without_auth(client, admin_user):
    login(client, "admin", "adminpass123")
    client.post("/journal/2026/04/10", json={"content": "<p>Public</p>", "word_count": 1})
    url = client.post("/journal/2026/04/10/share").json()["url"]
    client.cookies.clear()
    resp = client.get(url)
    assert resp.status_code == 200
    assert b"Public" in resp.content


def test_autosave_invalid_date_returns_404(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.post("/journal/2026/13/99", json={"content": "<p>x</p>"})
    assert resp.status_code == 404


def test_delete_invalid_date_returns_404(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.request("DELETE", "/journal/2026/13/99")
    assert resp.status_code == 404


def test_delete_entry_with_images(client, session, admin_user):
    login(client, "admin", "adminpass123")
    jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    upload_resp = client.post(
        "/upload",
        files={"file": ("photo.jpg", io.BytesIO(jpeg), "image/jpeg")},
    )
    image_url = upload_resp.json()["url"]
    client.post("/journal/2026/05/01", json={"content": f'<img src="{image_url}">'})
    resp = client.request("DELETE", "/journal/2026/05/01")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


def test_journal_stats(client, admin_user):
    login(client, "admin", "adminpass123")
    today = datetime.date.today()
    client.post(
        f"/journal/{today.year}/{today.month:02d}/{today.day:02d}",
        json={"content": "<p>streak entry</p>"},
    )
    resp = client.get("/journal/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["streak"] >= 1
    assert "month_entries" in data
    assert "month_words" in data


def test_streak_no_entry_today_carries_from_yesterday(client, session, regular_user):
    login(client, "testuser", "userpass123")
    today = datetime.date.today()
    for delta in range(1, 4):
        d = today - datetime.timedelta(days=delta)
        session.add(Entry(user_id=regular_user.id, date=d, content="<p>x</p>", word_count=1))
    session.commit()
    resp = client.get("/journal/stats")
    assert resp.status_code == 200
    assert resp.json()["streak"] == 3


def test_streak_today_only_is_one(client, session, regular_user):
    login(client, "testuser", "userpass123")
    today = datetime.date.today()
    session.add(Entry(user_id=regular_user.id, date=today, content="<p>x</p>", word_count=1))
    session.commit()
    resp = client.get("/journal/stats")
    assert resp.json()["streak"] == 1


def test_streak_today_and_yesterday_is_two(client, session, regular_user):
    login(client, "testuser", "userpass123")
    today = datetime.date.today()
    for d in [today, today - datetime.timedelta(days=1)]:
        session.add(Entry(user_id=regular_user.id, date=d, content="<p>x</p>", word_count=1))
    session.commit()
    resp = client.get("/journal/stats")
    assert resp.json()["streak"] == 2


def test_streak_no_recent_entries_is_zero(client, session, regular_user):
    login(client, "testuser", "userpass123")
    two_days_ago = datetime.date.today() - datetime.timedelta(days=2)
    session.add(Entry(user_id=regular_user.id, date=two_days_ago, content="<p>x</p>", word_count=1))
    session.commit()
    resp = client.get("/journal/stats")
    assert resp.json()["streak"] == 0


def test_calendar_invalid_date_returns_404(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.get("/calendar/2026/13")
    assert resp.status_code == 404


def test_share_invalid_date_returns_404(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.post("/journal/2026/13/99/share")
    assert resp.status_code == 404


def test_revoke_share_invalid_date_returns_404(client, admin_user):
    login(client, "admin", "adminpass123")
    resp = client.request("DELETE", "/journal/2026/13/99/share")
    assert resp.status_code == 404


def test_users_cannot_see_each_others_entries(client, session, admin_user, regular_user):
    """Admin creates an entry; regular user's calendar should not include it."""
    login(client, "admin", "adminpass123")
    client.post("/journal/2026/04/01", json={"content": "<p>Admin secret</p>", "word_count": 2})
    client.post("/logout", data={"csrf_token": get_csrf(client)})
    login(client, "testuser", "userpass123")
    resp = client.get("/calendar/2026/4")
    assert 1 not in resp.json()["days"]
