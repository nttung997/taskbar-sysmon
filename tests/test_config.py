import json

import pytest

from sysmon.config import DEFAULT_LAYOUT, Config


def test_defaults_validate():
    config = Config()
    assert config.layout == [list(row) for row in DEFAULT_LAYOUT]
    assert config.disk_path == "C:\\"


def test_missing_file_creates_default(tmp_path):
    path = tmp_path / "config.json"
    config = Config.load(path)
    assert path.exists()
    assert config.icon_size == 64


def test_round_trip(tmp_path):
    path = tmp_path / "config.json"
    Config(warn=50, crit=80, interval=5).save(path)
    loaded = Config.load(path)
    assert loaded.warn == 50
    assert loaded.crit == 80
    assert loaded.interval == 5


def test_partial_file_keeps_defaults_and_ignores_unknown_keys(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"warn": 40, "crit": 70, "bogus": True}), encoding="utf-8")
    config = Config.load(path)
    assert config.warn == 40
    assert config.crit == 70
    assert config.icon_size == 64


@pytest.mark.parametrize(
    "layout",
    [
        [["cpu", "ram"], ["net"]],
        [["gpu"], ["cpu"], ["ram"]],
        [["cpu", "ram", "disk"], ["net", "temp", None], [None, None, None], [None, None, None]],
    ],
)
def test_invalid_layouts_rejected(layout):
    with pytest.raises(ValueError):
        Config(layout=layout)


def test_threshold_order_enforced():
    with pytest.raises(ValueError):
        Config(warn=90, crit=90)
    with pytest.raises(ValueError):
        Config(temp_warn=90, temp_crit=80)


def test_interval_floor_enforced():
    with pytest.raises(ValueError):
        Config(interval=0.1)
