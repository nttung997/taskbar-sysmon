from __future__ import annotations

from PIL import Image, ImageDraw

from .config import Config
from .metrics import Snapshot

GREEN = (46, 204, 113, 255)
YELLOW = (241, 196, 15, 255)
RED = (231, 76, 60, 255)
UNKNOWN = (140, 140, 140, 255)
IDLE = (150, 150, 150, 120)

SUPERSAMPLE = 4


def status_color(value: float | None, warn: float, crit: float) -> tuple[int, int, int, int]:
    if value is None:
        return UNKNOWN
    if value >= crit:
        return RED
    if value >= warn:
        return YELLOW
    return GREEN


def slot_colors(snapshot: Snapshot, config: Config) -> list[list[tuple[int, int, int, int]]]:
    values = {
        "cpu": (snapshot.cpu, config.warn, config.crit),
        "ram": (snapshot.ram, config.warn, config.crit),
        "disk": (snapshot.disk_load(config.disk_reference_mbps), config.warn, config.crit),
        "net": (snapshot.net_load(config.net_reference_mbps), config.warn, config.crit),
        "temp": (snapshot.temp, config.temp_warn, config.temp_crit),
    }
    return [
        [IDLE if key is None else status_color(*values[key]) for key in row]
        for row in config.layout
    ]


def render_icon(snapshot: Snapshot, config: Config) -> Image.Image:
    size = config.icon_size
    canvas = size * SUPERSAMPLE
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    margin = canvas * 0.11
    gap = canvas * 0.055
    dot = (canvas - 2 * margin - 2 * gap) / 3

    for row_index, row in enumerate(slot_colors(snapshot, config)):
        for column_index, color in enumerate(row):
            inset = dot * 0.225 if color == IDLE else 0.0
            x = margin + column_index * (dot + gap) + inset
            y = margin + row_index * (dot + gap) + inset
            draw.ellipse((x, y, x + dot - 2 * inset, y + dot - 2 * inset), fill=color)

    return image.resize((size, size), Image.LANCZOS)


def tooltip_text(snapshot: Snapshot, config: Config) -> str:
    temp = f"{snapshot.temp:.0f} C" if snapshot.temp is not None else "n/a"
    drive = config.disk_path.rstrip("\\") or config.disk_path
    return (
        f"CPU {snapshot.cpu:.0f}%   RAM {snapshot.ram:.0f}%   {drive} {snapshot.disk_used_pct:.0f}% used\n"
        f"Disk {snapshot.disk_read_mbps:.1f} read / {snapshot.disk_write_mbps:.1f} write MB/s\n"
        f"Net \u2193{snapshot.net_down_mbps:.1f} \u2191{snapshot.net_up_mbps:.1f} Mbps   Temp {temp}"
    )
