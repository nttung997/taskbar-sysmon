from __future__ import annotations

import os
import subprocess
import threading

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_POWERSHELL = ("powershell", "-NoProfile", "-NonInteractive", "-Command")

_CPU_NAMESPACES = (
    ("LibreHardwareMonitor", "root/LibreHardwareMonitor"),
    ("OpenHardwareMonitor", "root/OpenHardwareMonitor"),
)

_preferred_namespace: str | None = None

_SENSOR_SCRIPT = """
$s = Get-CimInstance -Namespace '{ns}' -ClassName Sensor -ErrorAction Stop |
  Where-Object {{
    $_.SensorType -eq 'Temperature' -and
    ($_.Name -match 'CPU Package|CPU Core Max|CPU Total|Tctl/Tdie' -or $_.Identifier -match '/cpu/')
  }} |
  Sort-Object Value -Descending |
  Select-Object -First 1
if ($s) {{ [string]::Format([System.Globalization.CultureInfo]::InvariantCulture, '{{0}}', $s.Value) }}
"""

_ACPI_SCRIPT = """
$t = Get-CimInstance -Namespace 'root/wmi' -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction Stop |
  Sort-Object CurrentTemperature -Descending |
  Select-Object -First 1
if ($t) {{ [string]::Format([System.Globalization.CultureInfo]::InvariantCulture, '{{0}}', ($t.CurrentTemperature / 10.0 - 273.15)) }}
"""


def _run(script: str) -> str | None:
    try:
        result = subprocess.run(
            [*_POWERSHELL, script],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = result.stdout.strip()
    return output or None


def _as_temperature(text: str | None) -> float | None:
    if not text:
        return None
    try:
        value = float(text.replace(",", "."))
    except ValueError:
        return None
    if -40.0 <= value <= 150.0:
        return value
    return None


def _query_sensor(namespace: str) -> float | None:
    return _as_temperature(_run(_SENSOR_SCRIPT.format(ns=namespace)))


def _query_acpi() -> float | None:
    return _as_temperature(_run(_ACPI_SCRIPT))


def probe() -> tuple[float | None, str]:
    """Best-effort CPU temperature in Celsius plus a human readable source."""
    global _preferred_namespace

    if os.name != "nt":
        return None, "unsupported platform"

    candidates = list(_CPU_NAMESPACES)
    if _preferred_namespace is not None:
        candidates.sort(key=lambda item: item[1] != _preferred_namespace)
    for label, namespace in candidates:
        value = _query_sensor(namespace)
        if value is not None:
            _preferred_namespace = namespace
            return value, label

    value = _query_acpi()
    if value is not None:
        return value, "ACPI thermal zone"

    return None, "no sensor (needs admin, or LibreHardwareMonitor with WMI enabled)"


class TemperatureReader:
    """Polls the sensor off the UI thread; ``value()`` never blocks."""

    def __init__(self, poll_seconds: float = 10.0) -> None:
        self._poll_seconds = poll_seconds
        self._value: float | None = None
        self._source = "not polled"
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None or self._poll_seconds <= 0:
            return
        self.read_now()
        self._thread = threading.Thread(target=self._loop, name="temperature", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def value(self) -> float | None:
        with self._lock:
            return self._value

    def source(self) -> str:
        with self._lock:
            return self._source

    def read_now(self) -> float | None:
        value, source = probe()
        with self._lock:
            self._value = value
            self._source = source
        return value

    def _loop(self) -> None:
        while not self._stop.wait(self._poll_seconds):
            self.read_now()
