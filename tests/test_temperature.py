import pytest

from sysmon.temperature import parse_number, parse_sensor


@pytest.mark.parametrize(
    "text, expected",
    [
        ("54.5", 54.5),
        ("54,5", 54.5),
        ("-12.5", -12.5),
        ("3312", None),
        ("999", None),
        ("-100", None),
        ("abc", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_number(text, expected):
    assert parse_number(text) == expected


def test_parse_sensor_splits_value_and_name():
    assert parse_sensor("61.5|CPU Package") == (61.5, "CPU Package")
    assert parse_sensor("61.5|") == (61.5, None)
    assert parse_sensor("61.5") == (61.5, None)
    assert parse_sensor(None) == (None, None)
