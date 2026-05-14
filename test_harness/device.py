"""Device backend protocol.

The Device protocol is the seam between the executor and the underlying
target (simulated, adb, ssh, ...). All backends must satisfy this surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class CommandResult:
    """Result of a single command invocation on a device."""

    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_sec: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class LogBundle:
    """Logs pulled from a device after a command run."""

    logcat: str = ""
    dmesg: str = ""
    extra: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSample:
    """A single timestamped metric reading."""

    timestamp: str
    metric: str
    value: float
    unit: str = ""


@runtime_checkable
class Device(Protocol):
    """Common protocol all device backends must implement."""

    name: str

    def connect(self) -> None: ...

    def run_command(self, command: str, timeout_sec: float) -> CommandResult: ...

    def pull_logs(self) -> LogBundle: ...

    def collect_metrics(self) -> list[MetricSample]: ...

    def disconnect(self) -> None: ...
