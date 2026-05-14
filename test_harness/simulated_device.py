"""Simulated device backend.

Returns deterministic logs and metrics keyed off the command name and an
iteration counter. The seed-based scheme lets us inject specific failure
shapes (boot regression, ANR, thermal throttle, flaky AI inference) so
the harness produces a meaningful demo without hardware.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from .device import CommandResult, LogBundle, MetricSample


# Canonical logcat / dmesg fragments keyed by failure flavor.
_LOGCAT_CLEAN = (
    "01-01 00:00:01.000  100  100 I SystemServer: Entered the Android system server!\n"
    "01-01 00:00:02.500  100  100 I ActivityManager: Boot is finished\n"
    "01-01 00:00:03.100  120  140 I CameraService: Camera ready\n"
)

_LOGCAT_ANR = (
    "01-01 00:00:05.300  200  220 E ActivityManager: ANR in com.example.app\n"
    "01-01 00:00:05.301  200  220 E ActivityManager: Reason: executing service\n"
    "01-01 00:00:05.302  200  220 E ActivityManager: Load: 14.5 / 13.9 / 12.1\n"
)

_LOGCAT_FATAL = (
    "01-01 00:00:06.100  300  310 E AndroidRuntime: FATAL EXCEPTION: main\n"
    "01-01 00:00:06.101  300  310 E AndroidRuntime: Process: com.example.app, PID: 310\n"
    "01-01 00:00:06.102  300  310 E AndroidRuntime: java.lang.NullPointerException\n"
)

_LOGCAT_CAMERA_ERR = (
    "01-01 00:00:07.400  120  140 E CameraService: Camera service error: device disconnected\n"
    "01-01 00:00:07.401  120  140 E BufferQueueProducer: dequeueBuffer: BufferQueue has been abandoned\n"
)

_DMESG_CLEAN = (
    "[    0.000000] Booting Linux on physical CPU 0x0\n"
    "[    0.123456] usb 1-1: new high-speed USB device number 2\n"
    "[    1.234567] wlan0: link up, 866Mbps\n"
)

_DMESG_PANIC = (
    "[   42.012345] Kernel panic - not syncing: Attempted to kill init!\n"
    "[   42.012999] CPU: 0 PID: 1 Comm: init Not tainted\n"
)

_DMESG_DRIVER_TIMEOUT = (
    "[   31.998877] qcom-camss 1b00000.camss: driver timeout waiting for ISP ack\n"
    "[   32.001234] qcom-camss 1b00000.camss: I/O error on CSID0\n"
)

_DMESG_THERMAL = (
    "[   58.776655] thermal thermal_zone0: thermal throttling, cdev0: cooling state 3\n"
    "[   58.776700] cpufreq: CPU0 frequency capped at 1.4GHz due to thermal\n"
)


@dataclass
class SimulatedDevice:
    """Deterministic in-memory device backend."""

    name: str = "simulated_android"
    _connected: bool = field(default=False, init=False)
    _iteration_counters: dict[str, int] = field(default_factory=dict, init=False)
    _latest_logs: LogBundle = field(default_factory=LogBundle, init=False)
    _latest_metrics: list[MetricSample] = field(default_factory=list, init=False)
    _last_command: str = field(default="", init=False)

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def run_command(self, command: str, timeout_sec: float) -> CommandResult:
        if not self._connected:
            raise RuntimeError("device is not connected")
        self._last_command = command
        iteration = self._iteration_counters.get(command, 0)
        self._iteration_counters[command] = iteration + 1

        start = time.perf_counter()
        logs, metrics, exit_code = self._simulate(command, iteration)
        duration = time.perf_counter() - start

        self._latest_logs = logs
        self._latest_metrics = metrics
        stdout = f"[sim] {command} completed (iter={iteration})"
        return CommandResult(
            command=command,
            exit_code=exit_code,
            stdout=stdout,
            duration_sec=round(duration, 4),
            metadata={"iteration": iteration},
        )

    def pull_logs(self) -> LogBundle:
        return self._latest_logs

    def collect_metrics(self) -> list[MetricSample]:
        return self._latest_metrics

    def _simulate(
        self, command: str, iteration: int
    ) -> tuple[LogBundle, list[MetricSample], int]:
        """Return (logs, metrics, exit_code) for a given command/iteration."""
        base_ts = datetime(2026, 5, 14, 10, 0, 0, tzinfo=timezone.utc)

        if command == "simulate_boot":
            # Iteration 1 introduces a slow boot; otherwise clean.
            boot_time = 30.0 if iteration != 1 else 38.5
            metrics = [
                MetricSample(
                    (base_ts).isoformat(),
                    "boot_time_sec",
                    boot_time,
                    "s",
                )
            ]
            logs = LogBundle(logcat=_LOGCAT_CLEAN, dmesg=_DMESG_CLEAN)
            return logs, metrics, 0

        if command == "simulate_idle_power":
            avg = 720.0 if iteration % 2 == 0 else 905.0
            peak = avg + 120.0
            metrics = [
                MetricSample(
                    (base_ts + timedelta(seconds=i)).isoformat(),
                    "power_mw",
                    avg + ((i % 5) - 2) * 8.0,
                    "mW",
                )
                for i in range(20)
            ]
            metrics.append(
                MetricSample(base_ts.isoformat(), "peak_power_mw", peak, "mW")
            )
            logs = LogBundle(logcat=_LOGCAT_CLEAN, dmesg=_DMESG_CLEAN)
            return logs, metrics, 0

        if command == "simulate_ai_inference":
            # Flaky: every 2nd iteration spikes p95 latency, 1 iteration shows thermal throttle.
            spike = iteration % 2 == 1
            base = 38.0 if not spike else 62.0
            metrics = [
                MetricSample(
                    (base_ts + timedelta(milliseconds=50 * i)).isoformat(),
                    "inference_latency_ms",
                    base + (i % 7) * 1.3 + (8.0 if spike and i > 70 else 0.0),
                    "ms",
                )
                for i in range(100)
            ]
            dmesg = _DMESG_CLEAN + (_DMESG_THERMAL if iteration == 2 else "")
            logs = LogBundle(logcat=_LOGCAT_CLEAN, dmesg=dmesg)
            return logs, metrics, 0

        if command == "simulate_camera_open":
            broken = iteration == 0
            metrics = [
                MetricSample(
                    base_ts.isoformat(),
                    "camera_open_latency_ms",
                    180.0 if broken else 95.0,
                    "ms",
                )
            ]
            logcat = _LOGCAT_CLEAN + (_LOGCAT_CAMERA_ERR if broken else "")
            dmesg = _DMESG_CLEAN + (_DMESG_DRIVER_TIMEOUT if broken else "")
            logs = LogBundle(logcat=logcat, dmesg=dmesg)
            return logs, metrics, 1 if broken else 0

        if command == "simulate_app_launch_crash":
            metrics = [
                MetricSample(
                    base_ts.isoformat(),
                    "launch_to_first_frame_ms",
                    450.0,
                    "ms",
                )
            ]
            logs = LogBundle(
                logcat=_LOGCAT_CLEAN + _LOGCAT_FATAL + _LOGCAT_ANR,
                dmesg=_DMESG_CLEAN,
            )
            return logs, metrics, 1

        if command == "simulate_stability_soak":
            panic = iteration == 1
            metrics = [
                MetricSample(
                    base_ts.isoformat(),
                    "soak_uptime_sec",
                    3600.0 if not panic else 1742.0,
                    "s",
                )
            ]
            logs = LogBundle(
                logcat=_LOGCAT_CLEAN,
                dmesg=_DMESG_CLEAN + (_DMESG_PANIC if panic else ""),
            )
            return logs, metrics, 1 if panic else 0

        # Unknown command: produce a deterministic synthetic but mark non-zero exit.
        digest = hashlib.sha256(f"{command}-{iteration}".encode()).hexdigest()
        value = int(digest[:4], 16) / 1000.0
        metrics = [MetricSample(base_ts.isoformat(), "synthetic_value", value, "")]
        logs = LogBundle(logcat=_LOGCAT_CLEAN, dmesg=_DMESG_CLEAN)
        return logs, metrics, 0
