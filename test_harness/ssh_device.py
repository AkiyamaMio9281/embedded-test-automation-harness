"""Stub SSH-based device backend.

A real implementation would use paramiko to open a session and run
commands on a Linux target, pulling /var/log/messages and `dmesg`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .device import CommandResult, LogBundle, MetricSample


@dataclass
class SshDevice:
    """Placeholder SSH backend."""

    host: str
    user: str = "root"
    port: int = 22
    name: str = field(init=False)

    def __post_init__(self) -> None:
        self.name = f"ssh:{self.user}@{self.host}:{self.port}"

    def connect(self) -> None:
        raise NotImplementedError("SshDevice is a stub — paramiko wiring not added yet")

    def run_command(self, command: str, timeout_sec: float) -> CommandResult:
        raise NotImplementedError

    def pull_logs(self) -> LogBundle:
        raise NotImplementedError

    def collect_metrics(self) -> list[MetricSample]:
        raise NotImplementedError

    def disconnect(self) -> None:
        return None
