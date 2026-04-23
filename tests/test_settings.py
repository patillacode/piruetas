import pytest
from pydantic import ValidationError

from app.settings import Settings


def test_default_secret_key_with_secure_cookies_raises(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "change-me-in-production")
    monkeypatch.setenv("SECURE_COOKIES", "true")
    with pytest.raises(ValidationError):
        Settings()


def test_invalid_week_start_raises(monkeypatch):
    monkeypatch.setenv("WEEK_START", "wednesday")
    with pytest.raises(ValidationError):
        Settings()
