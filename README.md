# SysMon 3x3

A tiny Windows tray monitor that renders CPU, RAM, disk read/write activity, network, and
temperature as a 3x3 dot matrix. Every dot is a traffic light: green = fine, yellow = watch
it, red = act now.

```
  ●   ●   ●      cpu   ram   disk
  ●   ●   ○      net   temp   -
  ○   ○   ○       -     -     -
```

`●` = live metric, `○` = idle placeholder. Hover the icon for exact numbers.

## Install

```powershell
# from the repo root
.\install.ps1
```

The script creates `.venv`, installs dependencies, drops a shortcut in your Startup folder,
and launches the app. Use `.\install.ps1 -NoStart` to skip the launch or
`-SkipAutostart` to skip the shortcut.

Re-running the script is safe: if SysMon is already running it says so and does not start a
second copy. Pass `-Restart` to stop the running instance and start the new code. The app
also holds a named mutex, so launching `run.pyw` twice still gives you one tray icon.

Remove it again with `.\uninstall.ps1`.

Requirements: Windows 10/11 and Python 3.10+.

## Run manually

```powershell
.\.venv\Scripts\pythonw.exe run.pyw      # tray app, no console window
.\.venv\Scripts\python.exe -m sysmon --once           # one reading as JSON
.\.venv\Scripts\python.exe -m sysmon --dump-icon icon.png
```

The first run writes `config.json` next to `run.pyw`. Right-click the tray icon →
**Open config** to edit it, then restart the app.

## Configuration

| Key | Default | Meaning |
| --- | --- | --- |
| `interval` | `2.0` | Seconds between samples (minimum 0.5) |
| `warn` | `60` | Percentage where a dot turns yellow |
| `crit` | `85` | Percentage where a dot turns red |
| `temp_warn` | `65` | Temperature in °C for yellow |
| `temp_crit` | `80` | Temperature in °C for red |
| `net_reference_mbps` | `100` | Link speed that counts as 100% for the net dot |
| `disk_reference_mbps` | `800` | Read + write throughput that counts as 100% for the disk dot |
| `icon_size` | `64` | Icon render size in pixels (Windows scales it down) |
| `temp_poll` | `10` | Seconds between temperature reads; `0` disables polling |
| `layout` | 3x3 grid | Which metric sits in which cell, `null` for an idle dot |

Swap slots freely, e.g. put temperature first:

```json
"layout": [
  ["temp", "cpu", "ram"],
  ["disk", "net", null],
  [null, null, null]
]
```

Colors: green `#2ECC71`, yellow `#F1C40F`, red `#E74C3C`, grey `#8C8C8C` (sensor
unavailable), small grey dot (idle slot).

## Temperature on Windows

Windows exposes no CPU temperature API to normal user code, so SysMon tries every source it
can find, in this priority order:

1. **LibreHardwareMonitor** WMI — CPU Package / Tctl first, then any CPU sensor, then GPU,
   then the hottest sensor. Start LHM with *Options → WMI provider* enabled. Best accuracy.
2. **OpenHardwareMonitor** WMI — same selection logic.
3. **ACPI thermal zone** (`Win32_PerfFormattedData_Counters_ThermalZoneInformation`) — works
   without admin, but it is the chassis zone, not the CPU die.
4. **ACPI WMI** (`MSAcpi_ThermalZoneTemperature`) — same zone, usually needs an elevated app.
5. **nvidia-smi** — GPU temperature, when an NVIDIA card is present.

The first source that answers wins; the menu names the source so you know what you are
looking at. If nothing answers, the temp dot is grey and shows `Temp n/a`; everything
else keeps working.

## How it decides

- CPU / RAM: percentage, colored by `warn` and `crit`.
- Disk: read + write throughput in MB/s against `disk_reference_mbps` — the disk dot is
  about activity, not free space.
- Network: the busier direction (down or up) as a share of `net_reference_mbps`.
- Temperature: absolute °C, colored by `temp_warn` and `temp_crit`.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-dev.txt
.\.venv\Scripts\python -m pytest
```

Layout: `sysmon/config.py` (settings), `metrics.py` (psutil sampling),
`temperature.py` (sensor probing off-thread), `render.py` (dot matrix drawing),
`app.py` (tray icon, menu, loop).

## License

MIT
