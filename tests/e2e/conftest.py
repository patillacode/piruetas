import os
import socket
import threading
import time

import bcrypt
import httpx
import pytest
import uvicorn
from sqlmodel import Session

from app.auth import SESSION_COOKIE, make_session_token
from app.database import get_engine, init_db
from app.models import User
from app.settings import get_settings


TEST_SECRET_KEY = "test-secret-key-for-playwright-e2e"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpassword123"
TEST_ADMIN_USERNAME = "testadmin"
TEST_ADMIN_PASSWORD = "adminpassword123"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture()
def live_server(tmp_path):
    import app.database as db_module

    db_path = tmp_path / "test.db"
    data_dir = str(tmp_path)

    env_overrides = {
        "DATABASE_URL": f"sqlite:///{db_path}",
        "DATA_DIR": data_dir,
        "SECRET_KEY": TEST_SECRET_KEY,
        "SECURE_COOKIES": "false",
        "ADMIN_USERNAME": "sysadmin",
        "ADMIN_PASSWORD": "sysadminpassword",
    }
    original_env = {k: os.environ.get(k) for k in env_overrides}
    os.environ.update(env_overrides)

    get_settings.cache_clear()
    db_module._engine = None

    port = _find_free_port()
    config = uvicorn.Config(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="error",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            httpx.get(f"{base_url}/health", timeout=0.5)
            break
        except Exception:
            time.sleep(0.1)
    else:
        raise RuntimeError("Test server did not start in time")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)

    get_settings.cache_clear()
    db_module._engine = None

    for k, v in original_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.fixture()
def seed_user(live_server):
    hashed = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()
    user = User(username=TEST_USERNAME, hashed_password=hashed, is_admin=False)
    with Session(get_engine()) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
    yield user


@pytest.fixture()
def seed_admin(live_server):
    hashed = bcrypt.hashpw(TEST_ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
    admin = User(username=TEST_ADMIN_USERNAME, hashed_password=hashed, is_admin=True)
    with Session(get_engine()) as session:
        session.add(admin)
        session.commit()
        session.refresh(admin)
    yield admin


def _make_auth_cookie(user: User, base_url: str) -> dict:
    token = make_session_token(
        user_id=user.id,
        is_admin=user.is_admin,
        session_version=user.session_version,
        secret_key=TEST_SECRET_KEY,
    )
    return {
        "name": SESSION_COOKIE,
        "value": token,
        "domain": "127.0.0.1",
        "path": "/",
    }


@pytest.fixture()
def authenticated_page(page, live_server, seed_user):
    page.goto(live_server)
    page.context.add_cookies([_make_auth_cookie(seed_user, live_server)])
    yield page


@pytest.fixture()
def admin_page(page, live_server, seed_admin):
    page.goto(live_server)
    page.context.add_cookies([_make_auth_cookie(seed_admin, live_server)])
    yield page
