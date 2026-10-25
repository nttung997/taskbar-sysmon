from sysmon.config import Config
from sysmon.metrics import Snapshot
from sysmon.render import (
    GREEN,
    IDLE,
    RED,
    UNKNOWN,
    YELLOW,
    render_icon,
    slot_colors,
    status_color,
    tooltip_text,
)


def snapshot(**overrides):
    values = {
        "cpu": 10.0,
        "ram": 10.0,
        "disk": 10.0,
        "net_down_mbps": 0.0,
        "net_up_mbps": 0.0,
        "temp": 40.0,
        "at": 0.0,
    }
    values.update(overrides)
    return Snapshot(**values)


def test_status_bands():
    assert status_color(59.9, 60, 85) == GREEN
    assert status_color(60.0, 60, 85) == YELLOW
    assert status_color(84.9, 60, 85) == YELLOW
    assert status_color(85.0, 60, 85) == RED
    assert status_color(None, 60, 85) == UNKNOWN


def test_default_layout_mapping():
    colors = slot_colors(snapshot(cpu=95, ram=70, disk=10), Config())
    assert colors[0] == [RED, YELLOW, GREEN]
    assert colors[1][0] == GREEN
    assert colors[1][2] == IDLE
    assert colors[2] == [IDLE, IDLE, IDLE]


def test_unknown_temperature_is_grey():
    assert slot_colors(snapshot(temp=None), Config())[1][1] == UNKNOWN


def test_network_uses_share_of_reference_bandwidth():
    config = Config(net_reference_mbps=100, warn=60, crit=85)
    assert slot_colors(snapshot(net_down_mbps=50), config)[1][0] == GREEN
    assert slot_colors(snapshot(net_down_mbps=65), config)[1][0] == YELLOW
    assert slot_colors(snapshot(net_up_mbps=90), config)[1][0] == RED


def test_icon_is_square_rgba_and_drawn():
    image = render_icon(snapshot(), Config())
    assert image.size == (64, 64)
    assert image.mode == "RGBA"
    assert image.getbbox() is not None


def test_icon_respects_configured_size():
    assert render_icon(snapshot(), Config(icon_size=32)).size == (32, 32)


def test_tooltip_contains_every_metric():
    text = tooltip_text(snapshot(cpu=12, ram=34, disk=56, temp=57), Config())
    assert "12%" in text
    assert "34%" in text
    assert "56%" in text
    assert "57 C" in text
    assert "n/a" in tooltip_text(snapshot(temp=None), Config())
