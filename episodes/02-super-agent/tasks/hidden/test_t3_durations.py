import pytest
from widgets.durations import parse_duration
def test_all_forms():
    assert parse_duration("1h30m") == 5400
    assert parse_duration("2h") == 7200
    assert parse_duration("45m") == 2700
    assert parse_duration("90s") == 90
    assert parse_duration("1h2m3s") == 3723
    assert parse_duration(" 10m ") == 600
def test_rejects_bad():
    for bad in ("", "h", "1x", "m5", "1h1h"):
        with pytest.raises(ValueError):
            parse_duration(bad)
