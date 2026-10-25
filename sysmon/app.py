from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

from pystray import Icon, Menu, MenuItem

from .config import DEFAULT_CONFIG_PATH, Config
from .metrics import EMPTY, Sampler, Snapshot
from .render import render_icon, tooltip_text
from .temperature import TemperatureReader


class SysMon:
    def __init__(self, config: Config, config_path: Path) -> None:
        self.config = config
        self.config_path = config_path
        self.temperature = TemperatureReader(config.temp_poll)
        self.sampler = Sampler(self.temperature, config.disk_path)
        self.snapshot: Snapshot = EMPTY
        self._stop = threading.Event()
        self.icon = Icon(
            "sysmon",
            render_icon(self.snapshot, config),
            "System monitor",
            menu=Menu(
                MenuItem(lambda _: self._menu_line(), None, enabled=False),
                Menu.SEPARATOR,
                MenuItem("Sample now", self._sample_now),
                MenuItem("Open config", self._open_config),
                Menu.SEPARATOR,
                MenuItem("Quit", self._quit),
            ),
        )

    def run(self) -> None:
        self.temperature.start()
        self._refresh()
        threading.Thread(target=self._loop, name="sampler", daemon=True).start()
        try:
            self.icon.run()
        finally:
            self._shutdown()

    def _loop(self) -> None:
        while not self._stop.wait(self.config.interval):
            self._refresh()

    def _refresh(self) -> None:
        snapshot = self.sampler.sample()
        self.snapshot = snapshot
        self.icon.icon = render_icon(snapshot, self.config)
        self.icon.title = tooltip_text(snapshot, self.config)
        self.icon.update_menu()

    def _sample_now(self) -> None:
        self._refresh()

    def _menu_line(self) -> str:
        snapshot = self.snapshot
        temp = f"{snapshot.temp:.0f} C" if snapshot.temp is not None else "n/a"
        return (
            f"CPU {snapshot.cpu:.0f}%   RAM {snapshot.ram:.0f}%   "
            f"Disk {snapshot.disk:.0f}%   Temp {temp}"
        )

    def _open_config(self) -> None:
        if not self.config_path.exists():
            self.config.save(self.config_path)
        os.startfile(self.config_path)

    def _quit(self) -> None:
        self._shutdown()
        self.icon.stop()

    def _shutdown(self) -> None:
        self._stop.set()
        self.temperature.stop()


def _sample(config: Config) -> tuple[Snapshot, str]:
    temperature = TemperatureReader(config.temp_poll)
    temperature.read_now()
    sampler = Sampler(temperature, config.disk_path)
    sampler.sample()
    time.sleep(min(config.interval, 1.0))
    return sampler.sample(), temperature.source()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sysmon",
        description="3x3 dot-matrix system monitor for the Windows tray.",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--once", action="store_true", help="print one reading as JSON and exit")
    parser.add_argument("--dump-icon", type=Path, metavar="PNG", help="save the current icon as PNG and exit")
    parser.add_argument("--interval", type=float, help="override the sampling interval in seconds")
    args = parser.parse_args(argv)

    try:
        config = Config.load(args.config)
        if args.interval is not None:
            config.interval = args.interval
            config.validate()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"sysmon: invalid config: {exc}", file=sys.stderr)
        return 2

    if args.once or args.dump_icon:
        snapshot, source = _sample(config)
        if args.once:
            print(
                json.dumps(
                    {
                        "cpu_pct": round(snapshot.cpu, 1),
                        "ram_pct": round(snapshot.ram, 1),
                        "disk_pct": round(snapshot.disk, 1),
                        "net_down_mbps": round(snapshot.net_down_mbps, 2),
                        "net_up_mbps": round(snapshot.net_up_mbps, 2),
                        "cpu_temp_c": None if snapshot.temp is None else round(snapshot.temp, 1),
                        "temp_source": source,
                    },
                    indent=2,
                )
            )
        if args.dump_icon:
            args.dump_icon.parent.mkdir(parents=True, exist_ok=True)
            render_icon(snapshot, config).save(args.dump_icon)
            print(f"icon written to {args.dump_icon}")
        return 0

    if os.name != "nt":
        print("sysmon: the tray front-end targets Windows", file=sys.stderr)
        return 1

    SysMon(config, args.config).run()
    return 0
