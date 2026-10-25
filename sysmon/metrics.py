from __future__ import annotations

import time
from dataclasses import dataclass

import psutil

from .temperature import TemperatureReader

BYTES_PER_SECOND_PER_MBPS = 125_000.0
BYTES_PER_SECOND_PER_MB = 1_000_000.0


@dataclass(frozen=True)
class Snapshot:
    cpu: float
    ram: float
    disk_read_mbps: float
    disk_write_mbps: float
    net_down_mbps: float
    net_up_mbps: float
    temp: float | None
    temp_source: str
    at: float

    def net_load(self, reference_mbps: float) -> float:
        """Busiest direction as a percentage of the reference bandwidth."""
        if reference_mbps <= 0:
            return 0.0
        peak = max(self.net_down_mbps, self.net_up_mbps)
        return min(100.0, peak / reference_mbps * 100.0)

    def disk_load(self, reference_mbps: float) -> float:
        """Combined read + write throughput as a percentage of the reference."""
        if reference_mbps <= 0:
            return 0.0
        return min(100.0, (self.disk_read_mbps + self.disk_write_mbps) / reference_mbps * 100.0)


EMPTY = Snapshot(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, None, "not polled", 0.0)


class Sampler:
    def __init__(self, temperature: TemperatureReader) -> None:
        self._temperature = temperature
        self._last_net = None
        self._last_disk = None
        self._last_at: float | None = None
        psutil.cpu_percent(interval=None)

    def sample(self) -> Snapshot:
        now = time.monotonic()
        elapsed = None if self._last_at is None else now - self._last_at
        net = psutil.net_io_counters()
        disk = psutil.disk_io_counters()

        down = up = read = write = 0.0
        if elapsed is not None and elapsed > 0:
            if self._last_net is not None:
                down = (
                    max(0, net.bytes_recv - self._last_net.bytes_recv)
                    / elapsed
                    / BYTES_PER_SECOND_PER_MBPS
                )
                up = (
                    max(0, net.bytes_sent - self._last_net.bytes_sent)
                    / elapsed
                    / BYTES_PER_SECOND_PER_MBPS
                )
            if self._last_disk is not None and disk is not None:
                read = (
                    max(0, disk.read_bytes - self._last_disk.read_bytes)
                    / elapsed
                    / BYTES_PER_SECOND_PER_MB
                )
                write = (
                    max(0, disk.write_bytes - self._last_disk.write_bytes)
                    / elapsed
                    / BYTES_PER_SECOND_PER_MB
                )

        self._last_net = net
        self._last_disk = disk
        self._last_at = now

        return Snapshot(
            cpu=psutil.cpu_percent(interval=None),
            ram=psutil.virtual_memory().percent,
            disk_read_mbps=read,
            disk_write_mbps=write,
            net_down_mbps=down,
            net_up_mbps=up,
            temp=self._temperature.value(),
            temp_source=self._temperature.source(),
            at=time.time(),
        )
