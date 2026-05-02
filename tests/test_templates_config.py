import datetime as dt
from unittest.mock import MagicMock, patch

from app.templates_config import _next_half_hour_ts


def _mock_dt(fixed: dt.datetime):
    m = MagicMock()
    m.datetime.now.return_value = fixed
    m.timedelta = dt.timedelta
    return m


def test_next_half_hour_ts_before_half():
    fixed = dt.datetime(2024, 1, 1, 10, 15, 0, 0)
    expected = int(dt.datetime(2024, 1, 1, 10, 30, 0, 0).timestamp())
    with patch("app.templates_config.datetime", _mock_dt(fixed)):
        assert _next_half_hour_ts() == expected


def test_next_half_hour_ts_after_half():
    fixed = dt.datetime(2024, 1, 1, 10, 45, 0, 0)
    expected = int(dt.datetime(2024, 1, 1, 11, 0, 0, 0).timestamp())
    with patch("app.templates_config.datetime", _mock_dt(fixed)):
        assert _next_half_hour_ts() == expected
