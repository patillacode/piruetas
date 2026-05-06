from datetime import date

import pytest
from sqlmodel import Session

from app.database import get_engine
from app.models import Entry


@pytest.fixture()
def seeded_entry(seed_user):
    entry = Entry(
        user_id=seed_user.id,
        date=date(2024, 1, 15),
        content="<p>Test entry</p>",
        word_count=2,
    )
    with Session(get_engine()) as session:
        session.add(entry)
        session.commit()
        session.refresh(entry)
    yield entry
    with Session(get_engine()) as session:
        e = session.get(Entry, entry.id)
        if e:
            session.delete(e)
            session.commit()
