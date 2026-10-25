from sysmon.metrics import Snapshot


def make(**overrides):
    values = {
        "cpu": 0.0,
        "ram": 0.0,
        "disk_read_mbps": 0.0,
        "disk_write_mbps": 0.0,
        "disk_used_pct": 0.0,
        "net_down_mbps": 0.0,
        "net_up_mbps": 0.0,
        "temp": None,
        "temp_source": "test",
        "at": 0.0,
    }
    values.update(overrides)
    return Snapshot(**values)


def test_net_load_uses_busiest_direction():
    assert make(net_down_mbps=10, net_up_mbps=30).net_load(100) == 30.0


def test_net_load_clamps_to_100():
    assert make(net_down_mbps=500).net_load(100) == 100.0


def test_net_load_handles_zero_reference():
    assert make(net_down_mbps=10, net_up_mbps=10).net_load(0) == 0.0


def test_disk_load_combines_read_and_write():
    assert make(disk_read_mbps=100, disk_write_mbps=100).disk_load(400) == 50.0


def test_disk_load_clamps_and_handles_zero_reference():
    assert make(disk_read_mbps=400, disk_write_mbps=400).disk_load(400) == 100.0
    assert make(disk_read_mbps=10).disk_load(0) == 0.0
