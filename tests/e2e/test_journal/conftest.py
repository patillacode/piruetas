import datetime
from datetime import date

import bcrypt
import pytest
from sqlmodel import Session

from app.database import get_engine
from app.models import Entry, User
from tests.e2e.conftest import TEST_PASSWORD, TEST_USERNAME, _delete_user


@pytest.fixture(scope="module")
def seed_user(live_server):
    hashed = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    user = User(username=TEST_USERNAME, hashed_password=hashed, is_admin=False)
    with Session(get_engine()) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        user.created_at = datetime.datetime.now(datetime.UTC).replace(
            tzinfo=None
        ) - datetime.timedelta(days=8)
        session.add(user)
        session.commit()
        session.refresh(user)
    yield user
    _delete_user(user.id)


@pytest.fixture()
def seeded_entry(seed_user):
    entry = Entry(
        user_id=seed_user.id,
        date=date(2020, 1, 15),
        content="<p>Hello world</p>",
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
