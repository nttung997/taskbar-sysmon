from sysmon.metrics import Snapshot


def test_net_load_uses_busiest_direction():
    assert Snapshot(0, 0, 0, 10, 30, None, 0).net_load(100) == 30.0


def test_net_load_clamps_to_100():
    assert Snapshot(0, 0, 0, 500, 0, None, 0).net_load(100) == 100.0


def test_net_load_handles_zero_reference():
    assert Snapshot(0, 0, 0, 10, 10, None, 0).net_load(0) == 0.0
