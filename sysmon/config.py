from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config.json"

METRICS = ("cpu", "ram", "disk", "net", "temp")

DEFAULT_LAYOUT: tuple[tuple[str | None, ...], ...] = (
    ("cpu", "ram", "disk"),
    ("net", "temp", None),
    (None, None, None),
)


@dataclass
class Config:
    """User-tunable settings, persisted as JSON next to the app."""

    interval: float = 2.0
    warn: float = 60.0
    crit: float = 85.0
    temp_warn: float = 65.0
    temp_crit: float = 80.0
    net_reference_mbps: float = 100.0
    disk_reference_mbps: float = 800.0
    icon_size: int = 64
    temp_poll: float = 10.0
    layout: list[list[str | None]] = field(
        default_factory=lambda: [list(row) for row in DEFAULT_LAYOUT]
    )

    def __post_init__(self) -> None:
        self.layout = [list(row) for row in self.layout]
        self.validate()

    def validate(self) -> None:
        if self.warn >= self.crit:
            raise ValueError("warn must be lower than crit")
        if self.temp_warn >= self.temp_crit:
            raise ValueError("temp_warn must be lower than temp_crit")
        if self.interval < 0.5:
            raise ValueError("interval must be at least 0.5 seconds")
        if not 16 <= self.icon_size <= 256:
            raise ValueError("icon_size must be between 16 and 256")
        if len(self.layout) != 3 or any(len(row) != 3 for row in self.layout):
            raise ValueError("layout must be a 3x3 grid")
        for row in self.layout:
            for slot in row:
                if slot is not None and slot not in METRICS:
                    raise ValueError(f"unknown metric in layout: {slot!r}")

    def save(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> "Config":
        path = Path(path)
        if not path.exists():
            config = cls()
            config.save(path)
            return config
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("config root must be a JSON object")
        known = {item.name for item in fields(cls)}
        return cls(**{key: value for key, value in raw.items() if key in known})
