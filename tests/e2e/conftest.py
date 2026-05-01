import os
import socket
import threading
import time

import bcrypt
import httpx
import pytest
import uvicorn
from sqlmodel import Session, select

import app.database as db_module
from app.database import get_engine
from app.models import Entry, Image, RecoveryCode, User
from app.rate_limit import clear_attempts
from app.recovery import create_codes_for_user
from app.session_token import SESSION_COOKIE, make_session_token
from app.settings import get_settings

TEST_SECRET_KEY = "test-secret-key-for-playwright-e2e"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "testpassword123"
TEST_ADMIN_USERNAME = "testadmin"
TEST_ADMIN_PASSWORD = "adminpassword123"

DEVICES = {
    "desktop": {"width": 1280, "height": 800},
    "mobile": {"width": 390, "height": 844},
}


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _delete_user(user_id: int) -> None:
    with Session(get_engine()) as session:
        for entry in session.exec(select(Entry).where(Entry.user_id == user_id)).all():
            session.delete(entry)
        for image in session.exec(select(Image).where(Image.user_id == user_id)).all():
            session.delete(image)
        for code in session.exec(select(RecoveryCode).where(RecoveryCode.user_id == user_id)).all():
            session.delete(code)
        u = session.get(User, user_id)
        if u:
            session.delete(u)
        session.commit()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    clear_attempts("127.0.0.1")
    yield
    clear_attempts("127.0.0.1")


@pytest.fixture(scope="session")
def live_server(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("e2e")
    db_path = tmp_path / "test.db"
    data_dir = str(tmp_path)

    env_overrides = {
        "DATABASE_URL": f"sqlite:///{db_path}",
        "DATA_DIR": data_dir,
        "SECRET_KEY": TEST_SECRET_KEY,
        "SECURE_COOKIES": "false",
        "ADMIN_USERNAME": "sysadmin",
        "ADMIN_PASSWORD": "sysadminpassword",
        "REGISTRATION_OPEN": "false",
        "BCRYPT_ROUNDS": "4",
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

    try:
        base_url = f"http://127.0.0.1:{port}"
        for _ in range(100):
            try:
                if httpx.get(f"{base_url}/health", timeout=0.5).status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.1)
        else:
            raise RuntimeError("Test server did not start in time")

        yield base_url

    finally:
        server.should_exit = True
        thread.join(timeout=5)

        get_settings.cache_clear()
        if db_module._engine is not None:
            db_module._engine.dispose()
        db_module._engine = None

        for k, v in original_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.fixture()
def seed_user(live_server):
    hashed = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    user = User(username=TEST_USERNAME, hashed_password=hashed, is_admin=False)
    with Session(get_engine()) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
    yield user
    _delete_user(user.id)


@pytest.fixture()
def seed_admin(live_server):
    hashed = bcrypt.hashpw(TEST_ADMIN_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    admin = User(username=TEST_ADMIN_USERNAME, hashed_password=hashed, is_admin=True)
    with Session(get_engine()) as session:
        session.add(admin)
        session.commit()
        session.refresh(admin)
    yield admin
    _delete_user(admin.id)


def _make_auth_cookie(user: User) -> dict:
    assert user.id is not None
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


def _get_auth_cookies(user: User) -> dict:
    assert user.id is not None
    token = make_session_token(
        user_id=user.id,
        is_admin=user.is_admin,
        session_version=user.session_version,
        secret_key=TEST_SECRET_KEY,
    )
    return {SESSION_COOKIE: token}


@pytest.fixture(params=["desktop", "mobile"])
def viewport(request):
    return DEVICES[request.param]


@pytest.fixture()
def authenticated_page(page, live_server, seed_user, viewport):
    page.set_viewport_size(viewport)
    page.goto(live_server)
    page.context.add_cookies([_make_auth_cookie(seed_user)])
    yield page


@pytest.fixture()
def admin_page(page, live_server, seed_admin, viewport):
    page.set_viewport_size(viewport)
    page.goto(live_server)
    page.context.add_cookies([_make_auth_cookie(seed_admin)])
    yield page


@pytest.fixture()
def registration_enabled(live_server):
    old_val = os.environ.get("REGISTRATION_OPEN")
    os.environ["REGISTRATION_OPEN"] = "true"
    get_settings.cache_clear()
    yield live_server
    if old_val is None:
        os.environ.pop("REGISTRATION_OPEN", None)
    else:
        os.environ["REGISTRATION_OPEN"] = old_val
    get_settings.cache_clear()


@pytest.fixture()
def seed_recovery_codes(seed_user):
    with Session(get_engine()) as session:
        codes = create_codes_for_user(seed_user.id, session)
    return codes
