import bcrypt
import pytest
from sqlmodel import Session

from app.database import get_engine
from app.models import User
from tests.e2e.conftest import TEST_PASSWORD, TEST_USERNAME, _delete_user


@pytest.fixture(scope="module")
def seed_user(live_server):
    hashed = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    user = User(username=TEST_USERNAME, hashed_password=hashed, is_admin=False)
    with Session(get_engine()) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
    yield user
    _delete_user(user.id)
