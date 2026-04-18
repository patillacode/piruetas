import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("SECURE_COOKIES", "false")
os.environ.setdefault("DATA_DIR", "/tmp/piruetas-test")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/piruetas-test.db")

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app
from app.models import User

TEST_DB_URL = "sqlite://"  # in-memory


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app, follow_redirects=False)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="admin_user")
def admin_user_fixture(session):
    hashed = bcrypt.hashpw(b"adminpass123", bcrypt.gensalt()).decode()
    user = User(username="admin", hashed_password=hashed, is_admin=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="regular_user")
def regular_user_fixture(session):
    hashed = bcrypt.hashpw(b"userpass123", bcrypt.gensalt()).decode()
    user = User(username="testuser", hashed_password=hashed, is_admin=False)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def login(client, username, password):
    """Helper: login and return client with session cookie set."""
    resp = client.post("/login", data={"username": username, "password": password})
    return resp
