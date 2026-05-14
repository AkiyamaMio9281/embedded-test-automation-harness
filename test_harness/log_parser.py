"""Android logcat and Linux dmesg parsers.

Each parser turns raw log text into structured ``LogEvent`` rows and
attaches a stable ``signature`` keyword that downstream triage uses to
classify failures. Signatures are intentionally short and lower-case
so they survive line-wrapping and minor format drift between vendors.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class LogEvent:
    timestamp: str
    severity: str
    subsystem: str
    message: str
    signature: str
    source: str = ""  # "logcat" or "dmesg"

    def as_dict(self) -> dict:
        return asdict(self)


# (signature, compiled regex) — order matters, first match wins per line.
_LOGCAT_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("fatal_exception", re.compile(r"FATAL EXCEPTION", re.IGNORECASE)),
    ("anr", re.compile(r"\bANR in\b", re.IGNORECASE)),
    ("watchdog", re.compile(r"\bwatchdog\b", re.IGNORECASE)),
    ("selinux_denial", re.compile(r"avc:\s*denied", re.IGNORECASE)),
    ("camera_service_error", re.compile(r"CameraService.*error", re.IGNORECASE)),
    ("binder_failure", re.compile(r"binder transaction failed", re.IGNORECASE)),
    ("crash", re.compile(r"\b(SIGSEGV|tombstone|libc:\s*Fatal)\b", re.IGNORECASE)),
]

_DMESG_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("kernel_panic", re.compile(r"Kernel panic", re.IGNORECASE)),
    ("oops", re.compile(r"\bOops\b", re.IGNORECASE)),
    ("segfault", re.compile(r"segfault", re.IGNORECASE)),
    ("driver_timeout", re.compile(r"driver timeout", re.IGNORECASE)),
    ("thermal_throttling", re.compile(r"thermal throttling", re.IGNORECASE)),
    ("firmware_load_failure", re.compile(r"firmware.*(failed|not found)", re.IGNORECASE)),
    ("io_error", re.compile(r"I/O error", re.IGNORECASE)),
]


# Standard logcat threadtime format: MM-DD HH:MM:SS.mmm  PID  TID L TAG: msg
_LOGCAT_LINE = re.compile(
    r"^(?P<ts>\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+"
    r"\d+\s+\d+\s+(?P<sev>[VDIWEF])\s+(?P<tag>[^:]+):\s*(?P<msg>.*)$"
)

# dmesg "[   42.123456] subsystem: message" — subsystem optional.
_DMESG_LINE = re.compile(
    r"^\[\s*(?P<ts>\d+\.\d+)\]\s*(?:(?P<sub>[^:]+):\s*)?(?P<msg>.*)$"
)


def _classify(line: str, rules: list[tuple[str, re.Pattern[str]]]) -> str:
    for sig, pattern in rules:
        if pattern.search(line):
            return sig
    return ""


def parse_logcat(text: str) -> list[LogEvent]:
    """Parse Android logcat (threadtime format) into structured events.

    Only lines matching known failure signatures are emitted, keeping
    output sized to interesting rows.
    """
    events: list[LogEvent] = []
    for line in text.splitlines():
        signature = _classify(line, _LOGCAT_RULES)
        if not signature:
            continue
        m = _LOGCAT_LINE.match(line)
        if m:
            ts = m.group("ts")
            sev = m.group("sev")
            tag = m.group("tag").strip()
            msg = m.group("msg").strip()
        else:
            ts, sev, tag, msg = "", "?", "", line.strip()
        events.append(
            LogEvent(
                timestamp=ts,
                severity=sev,
                subsystem=tag,
                message=msg,
                signature=signature,
                source="logcat",
            )
        )
    return events


def parse_dmesg(text: str) -> list[LogEvent]:
    """Parse Linux dmesg lines into structured events."""
    events: list[LogEvent] = []
    for line in text.splitlines():
        signature = _classify(line, _DMESG_RULES)
        if not signature:
            continue
        m = _DMESG_LINE.match(line)
        if m:
            ts = m.group("ts")
            sub = (m.group("sub") or "kernel").strip()
            msg = m.group("msg").strip()
        else:
            ts, sub, msg = "", "kernel", line.strip()
        sev = "F" if signature in {"kernel_panic", "oops"} else "E"
        events.append(
            LogEvent(
                timestamp=ts,
                severity=sev,
                subsystem=sub,
                message=msg,
                signature=signature,
                source="dmesg",
            )
        )
    return events


def parse_log_file(path: str | Path) -> list[LogEvent]:
    """Parse a file from disk; chooses logcat vs dmesg by filename/parent-dir hint."""
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    hint = f"{p.parent.name} {p.name}".lower()
    if "dmesg" in hint or "kernel" in hint:
        return parse_dmesg(text)
    return parse_logcat(text)


def parse_directory(directory: str | Path) -> list[LogEvent]:
    """Parse every .log/.txt file in a directory."""
    d = Path(directory)
    if not d.exists():
        return []
    events: list[LogEvent] = []
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix.lower() in {".log", ".txt"}:
            events.extend(parse_log_file(f))
    return events
