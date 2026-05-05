from datetime import date

from app.templates_config import _datefmt, _filesizeformat


def test_datefmt_none():
    assert _datefmt(None) is None


def test_datefmt_en():
    assert _datefmt(date(2024, 3, 15), "en") == "March 15, 2024"


def test_datefmt_es():
    assert _datefmt(date(2024, 3, 15), "es") == "Marzo 15, 2024"


def test_datefmt_default_locale():
    assert _datefmt(date(2024, 1, 1)) == "January 1, 2024"


def test_datefmt_unknown_locale_falls_back_to_en():
    assert _datefmt(date(2024, 6, 1), "fr") == "June 1, 2024"


def test_filesizeformat_bytes():
    assert _filesizeformat(512) == "512 B"


def test_filesizeformat_zero():
    assert _filesizeformat(0) == "0 B"


def test_filesizeformat_exactly_1kb():
    assert _filesizeformat(1024) == "1.0 KB"


def test_filesizeformat_mb():
    assert _filesizeformat(1024 * 1024) == "1.0 MB"


def test_filesizeformat_gb():
    assert _filesizeformat(1024**3) == "1.0 GB"


def test_filesizeformat_tb():
    assert _filesizeformat(1024**4) == "1.0 TB"
