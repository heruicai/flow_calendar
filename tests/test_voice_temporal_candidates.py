from datetime import datetime

import pytest

from src.voice_understanding.temporal_candidates import parse_temporal_candidates


NOW = datetime(2026, 5, 31, 9, 0)


@pytest.mark.parametrize(
    ("text", "date"),
    [
        ("\u4eca\u5929", "2026-05-31"),
        ("\u660e\u5929", "2026-06-01"),
        ("\u540e\u5929", "2026-06-02"),
        ("\u4e09\u5929\u540e", "2026-06-03"),
        ("\u4e0b\u5468\u4e09", "2026-06-10"),
        ("6\u67083\u53f7", "2026-06-03"),
    ],
)
def test_parse_temporal_dates(text, date):
    assert parse_temporal_candidates(text, now=NOW)[0]["date"] == date


@pytest.mark.parametrize(
    ("text", "time"),
    [
        ("\u4e0b\u5348\u4e09\u70b9", "15:00"),
        ("\u4e0b\u5348\u4e09\u70b9\u534a", "15:30"),
        ("\u665a\u4e0a\u516b\u70b9\u4e00\u523b", "20:15"),
    ],
)
def test_parse_temporal_times(text, time):
    assert parse_temporal_candidates(text, now=NOW)[0]["start_time"] == time
