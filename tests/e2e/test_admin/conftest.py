from datetime import date

import bcrypt
import pytest
from sqlmodel import Session

from app.database import get_engine
from app.models import Entry, User
from tests.e2e.conftest import TEST_ADMIN_PASSWORD, TEST_ADMIN_USERNAME, _delete_user


@pytest.fixture(scope="module")
def seed_admin(live_server):
    hashed = bcrypt.hashpw(TEST_ADMIN_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    admin = User(username=TEST_ADMIN_USERNAME, hashed_password=hashed, is_admin=True)
    with Session(get_engine()) as session:
        session.add(admin)
        session.commit()
        session.refresh(admin)
    yield admin
    _delete_user(admin.id)


@pytest.fixture()
def seeded_entry(seed_user):
    entry = Entry(
        user_id=seed_user.id,
        date=date(2020, 1, 15),
        content="<p>Admin test entry</p>",
        word_count=3,
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
