# tests for app/main.py lifespan and demo cleanup loop
import asyncio
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app.database as db_module
from app.main import _demo_cleanup_loop, app
from app.settings import get_settings


@pytest.fixture()
def lifespan_env(tmp_path):
    db_path = tmp_path / "main_test.db"
    env_overrides = {
        "DATABASE_URL": f"sqlite:///{db_path}",
        "DATA_DIR": str(tmp_path),
        "SECRET_KEY": "key-for-main-tests",
        "SECURE_COOKIES": "false",
        "ADMIN_USERNAME": "mainadmin",
        "ADMIN_PASSWORD": "mainpassword123",
        "DEMO_ENABLED": "false",
    }
    original_env = {k: os.environ.get(k) for k in env_overrides}
    os.environ.update(env_overrides)
    get_settings.cache_clear()
    saved_engine = db_module._engine
    db_module._engine = None
    yield tmp_path
    if db_module._engine is not None:
        db_module._engine.dispose()
    db_module._engine = saved_engine
    get_settings.cache_clear()
    for k, v in original_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_lifespan_startup_and_shutdown(lifespan_env):
    with TestClient(app, follow_redirects=False) as tc:
        resp = tc.get("/health")
        assert resp.status_code == 200


def test_lifespan_with_demo_enabled(lifespan_env):
    os.environ["DEMO_ENABLED"] = "true"
    os.environ["DEMO_USERNAME"] = "demomain"
    os.environ["DEMO_PASSWORD"] = "demopassword123"
    get_settings.cache_clear()
    try:
        with TestClient(app, follow_redirects=False) as tc:
            resp = tc.get("/health")
            assert resp.status_code == 200
    finally:
        os.environ["DEMO_ENABLED"] = "false"
        get_settings.cache_clear()


async def test_demo_cleanup_loop_executes_body():
    call_count = 0

    async def mock_sleep(n):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with (
        patch("asyncio.sleep", side_effect=mock_sleep),
        patch("app.main.delete_demo_user_content") as mock_del,
        patch("app.main.get_engine", return_value=MagicMock()),
        patch("app.main.Session"),
    ):
        with pytest.raises(asyncio.CancelledError):
            await _demo_cleanup_loop()

    assert mock_del.call_count == 1
