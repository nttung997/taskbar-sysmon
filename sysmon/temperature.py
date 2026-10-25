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

# CPU package first, then any CPU sensor, then GPU, then the hottest sensor.
_SENSOR_SCRIPT = """
$all = @(Get-CimInstance -Namespace '__NS__' -ClassName Sensor -ErrorAction Stop |
  Where-Object { $_.SensorType -eq 'Temperature' -and $_.Value -gt 0 })
if ($all.Count -eq 0) { return }
$pick = $all | Where-Object { $_.Name -match 'CPU Package|CPU Total|CPU Core Max|Tctl' } |
  Sort-Object Value -Descending | Select-Object -First 1
if (-not $pick) {
  $pick = $all | Where-Object { $_.Identifier -match '/cpu/' } |
    Sort-Object Value -Descending | Select-Object -First 1
}
if (-not $pick) {
  $pick = $all | Where-Object { $_.Name -match 'GPU' } |
    Sort-Object Value -Descending | Select-Object -First 1
}
if (-not $pick) {
  $pick = $all | Sort-Object Value -Descending | Select-Object -First 1
}
if ($pick) {
  [string]::Format([System.Globalization.CultureInfo]::InvariantCulture, '{0}|{1}', $pick.Value, $pick.Name)
}
"""

# ACPI thermal zone through the WMI performance class: no admin needed and the
# class name is not localized (the Get-Counter path would be).
_THERMAL_ZONE_SCRIPT = """
$z = Get-CimInstance -ClassName Win32_PerfFormattedData_Counters_ThermalZoneInformation -ErrorAction Stop |
  Where-Object { $_.HighPrecisionTemperature -gt 0 } |
  Sort-Object HighPrecisionTemperature -Descending | Select-Object -First 1
if ($z) {
  [string]::Format([System.Globalization.CultureInfo]::InvariantCulture, '{0}', ($z.HighPrecisionTemperature / 10.0 - 273.15))
}
"""

# Same zone through the ACPI provider; usually only readable elevated.
_ACPI_SCRIPT = """
$t = Get-CimInstance -Namespace 'root/wmi' -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction Stop |
  Sort-Object CurrentTemperature -Descending | Select-Object -First 1
if ($t) {
  [string]::Format([System.Globalization.CultureInfo]::InvariantCulture, '{0}', ($t.CurrentTemperature / 10.0 - 273.15))
}
"""

_preferred: str | None = None


def _run_powershell(script: str) -> str | None:
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


def parse_number(text: str | None) -> float | None:
    if not text:
        return None
    try:
        value = float(text.replace(",", "."))
    except ValueError:
        return None
    if -40.0 <= value <= 150.0:
        return value
    return None


def parse_sensor(text: str | None) -> tuple[float | None, str | None]:
    """Split the ``value|sensor name`` payload returned by the sensor script."""
    if not text or "|" not in text:
        return parse_number(text), None
    raw_value, raw_name = text.split("|", 1)
    name = raw_name.strip() or None
    return parse_number(raw_value.strip()), name


def _query_sensors(namespace: str) -> tuple[float | None, str | None]:
    source = namespace.rsplit("/", 1)[-1]
    value, name = parse_sensor(_run_powershell(_SENSOR_SCRIPT.replace("__NS__", namespace)))
    if value is None:
        return None, None
    return value, f"{name} ({source})" if name else source


def _query_thermal_zone() -> tuple[float | None, str | None]:
    value = parse_number(_run_powershell(_THERMAL_ZONE_SCRIPT))
    return (value, "ACPI thermal zone") if value is not None else (None, None)


def _query_acpi() -> tuple[float | None, str | None]:
    value = parse_number(_run_powershell(_ACPI_SCRIPT))
    return (value, "ACPI thermal zone (elevated)") if value is not None else (None, None)


def _query_nvidia() -> tuple[float | None, str | None]:
    if os.name != "nt":
        return None, None
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None, None
    for line in result.stdout.splitlines():
        value = parse_number(line.strip())
        if value is not None:
            return value, "GPU (nvidia-smi)"
    return None, None


def probe() -> tuple[float | None, str]:
    """Best available temperature in Celsius plus a label naming the source."""
    global _preferred

    if os.name != "nt":
        return None, "unsupported platform"

    providers = [
        ("LibreHardwareMonitor", lambda: _query_sensors("root/LibreHardwareMonitor")),
        ("OpenHardwareMonitor", lambda: _query_sensors("root/OpenHardwareMonitor")),
        ("APCI thermal zone", _query_thermal_zone),
        ("ACPI WMI", _query_acpi),
        ("nvidia-smi", _query_nvidia),
    ]
    if _preferred is not None:
        providers.sort(key=lambda item: item[0] != _preferred)

    for label, provider in providers:
        value, source = provider()
        if value is not None:
            _preferred = label
            return value, source or label

    return None, "no sensor (install LibreHardwareMonitor with WMI enabled)"


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
