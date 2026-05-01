import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ["SECURE_COOKIES"] = "false"  # must be false so TestClient (HTTP) sends cookies back
os.environ["REGISTRATION_OPEN"] = "true"  # unit tests exercise signup logic directly
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ.setdefault("DATA_DIR", "/tmp/piruetas-test")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/piruetas-test.db")

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.csrf import generate_csrf_token
from app.database import get_session
from app.main import app
from app.models import User
from app.session_token import SESSION_COOKIE
from app.settings import get_settings

TEST_DB_URL = "sqlite://"  # in-memory


@pytest.fixture(autouse=True)
def clear_settings_cache():
    yield
    get_settings.cache_clear()


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
    engine.dispose()


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
    hashed = bcrypt.hashpw(b"adminpass123", bcrypt.gensalt(rounds=4)).decode()
    user = User(username="admin", hashed_password=hashed, is_admin=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="regular_user")
def regular_user_fixture(session):
    hashed = bcrypt.hashpw(b"userpass123", bcrypt.gensalt(rounds=4)).decode()
    user = User(username="testuser", hashed_password=hashed, is_admin=False)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_csrf(client) -> str:
    """Compute the CSRF token for the client's current session cookie."""
    session_token = client.cookies.get(SESSION_COOKIE, "")
    return generate_csrf_token(session_token)


def login(client, username, password):
    """Helper: login and return client with session cookie set."""
    get_resp = client.get("/login")
    csrf_cookie = get_resp.cookies.get("piruetas_login_csrf", "")
    resp = client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "login_csrf_token": csrf_cookie,
        },
    )
    return resp
