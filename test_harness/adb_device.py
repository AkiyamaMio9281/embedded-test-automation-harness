"""Stub adb-based device backend.

A real implementation would shell out to `adb -s <serial> shell ...`,
pull `/data/anr/`, `logcat -d`, and `dmesg`. The stub is intentionally
non-functional but conforms to the Device protocol so it can be wired
in by the executor once hardware is available.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .device import CommandResult, LogBundle, MetricSample


@dataclass
class AdbDevice:
    """Placeholder adb backend."""

    serial: str
    name: str = field(init=False)

    def __post_init__(self) -> None:
        self.name = f"adb:{self.serial}"

    def connect(self) -> None:
        raise NotImplementedError("AdbDevice is a stub — adb integration not wired up")

    def run_command(self, command: str, timeout_sec: float) -> CommandResult:
        raise NotImplementedError

    def pull_logs(self) -> LogBundle:
        raise NotImplementedError

    def collect_metrics(self) -> list[MetricSample]:
        raise NotImplementedError

    def disconnect(self) -> None:
        return None
