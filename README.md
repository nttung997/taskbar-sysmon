# SysMon 3x3

A tiny Windows tray monitor that renders CPU, RAM, disk, network, and CPU temperature as a
3x3 dot matrix. Every dot is a traffic light: green = fine, yellow = watch it, red = act now.

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
| `disk_path` | `C:\\` | Volume to watch |
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
unavailable), faint white (idle slot).

## Temperature on Windows

Windows exposes no CPU temperature API to normal user code. SysMon tries, in order:

1. **LibreHardwareMonitor** WMI (`root/LibreHardwareMonitor`) — start LHM with
   *Options → WMI provider* enabled. Most reliable, no admin rights needed for the reader.
2. **OpenHardwareMonitor** WMI (`root/OpenHardwareMonitor`).
3. **ACPI thermal zone** (`MSAcpi_ThermalZoneTemperature`) — works on some laptops only and
   usually needs an elevated process.

If all three fail, the temp dot stays grey and the tooltip shows `Temp n/a`. Everything
else keeps working.

## How it decides

- CPU / RAM / disk / network: percentage, colored by `warn` and `crit`.
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
