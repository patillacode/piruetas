import base64
from datetime import date

import httpx
from sqlmodel import Session

from app.database import get_engine
from app.models import Entry

MINIMAL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _seed_entry(user_id: int, content: str) -> Entry:
    entry = Entry(user_id=user_id, date=date(2020, 1, 15), content=content, word_count=2)
    with Session(get_engine()) as session:
        session.add(entry)
        session.commit()
        session.refresh(entry)
    return entry


def test_upload_image_and_view_in_entry(authenticated_page, live_server, seed_user):
    resp = authenticated_page.request.post(
        f"{live_server}/upload",
        multipart={"file": {"name": "test.png", "mimeType": "image/png", "buffer": MINIMAL_PNG}},
    )
    assert resp.status == 200
    data = resp.json()
    assert "url" in data
    image_url = data["url"]
    assert image_url.startswith("/uploads/")

    content = f'<p>Entry with image</p><img src="{image_url}">'
    entry = _seed_entry(seed_user.id, content)

    authenticated_page.goto(f"{live_server}/journal/2020/01/15")
    authenticated_page.wait_for_load_state("networkidle")

    img = authenticated_page.locator('.ProseMirror img[src*="uploads"]')
    assert img.is_visible()

    with Session(get_engine()) as session:
        e = session.get(Entry, entry.id)
        if e:
            session.delete(e)
            session.commit()


def test_unauthenticated_cannot_access_uploads(live_server, seed_user):
    upload_path = f"/uploads/{seed_user.id}/nonexistent.png"
    resp = httpx.get(f"{live_server}{upload_path}", follow_redirects=False)
    assert resp.status_code in (401, 403)
