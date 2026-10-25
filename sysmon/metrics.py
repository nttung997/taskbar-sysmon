from __future__ import annotations

import time
from dataclasses import dataclass

import psutil

from .temperature import TemperatureReader

BYTES_PER_SECOND_PER_MBPS = 125_000.0


@dataclass(frozen=True)
class Snapshot:
    cpu: float
    ram: float
    disk: float
    net_down_mbps: float
    net_up_mbps: float
    temp: float | None
    at: float

    def net_load(self, reference_mbps: float) -> float:
        """Busiest direction as a percentage of the reference bandwidth."""
        if reference_mbps <= 0:
            return 0.0
        peak = max(self.net_down_mbps, self.net_up_mbps)
        return min(100.0, peak / reference_mbps * 100.0)


EMPTY = Snapshot(0.0, 0.0, 0.0, 0.0, 0.0, None, 0.0)


class Sampler:
    def __init__(self, temperature: TemperatureReader, disk_path: str = "C:\\") -> None:
        self._temperature = temperature
        self._disk_path = disk_path
        self._last_counters = None
        self._last_at: float | None = None
        psutil.cpu_percent(interval=None)

    def sample(self) -> Snapshot:
        now = time.monotonic()
        counters = psutil.net_io_counters()
        down = up = 0.0
        if self._last_counters is not None and self._last_at is not None:
            elapsed = now - self._last_at
            if elapsed > 0:
                down = (
                    max(0, counters.bytes_recv - self._last_counters.bytes_recv)
                    / elapsed
                    / BYTES_PER_SECOND_PER_MBPS
                )
                up = (
                    max(0, counters.bytes_sent - self._last_counters.bytes_sent)
                    / elapsed
                    / BYTES_PER_SECOND_PER_MBPS
                )
        self._last_counters = counters
        self._last_at = now
        return Snapshot(
            cpu=psutil.cpu_percent(interval=None),
            ram=psutil.virtual_memory().percent,
            disk=self._disk_usage(),
            net_down_mbps=down,
            net_up_mbps=up,
            temp=self._temperature.value(),
            at=time.time(),
        )

    def _disk_usage(self) -> float:
        try:
            return psutil.disk_usage(self._disk_path).percent
        except OSError:
            return 0.0
