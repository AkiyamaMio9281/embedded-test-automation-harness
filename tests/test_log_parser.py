"""Log parser tests."""

from __future__ import annotations

from test_harness.config import SAMPLE_LOGCAT_DIR, SAMPLE_DMESG_DIR
from test_harness.log_parser import (
    parse_directory,
    parse_dmesg,
    parse_logcat,
)


def test_logcat_detects_fatal_exception_and_anr():
    sample = (
        "01-01 00:00:05.300  200  220 E ActivityManager: ANR in com.example.app\n"
        "01-01 00:00:06.100  300  310 E AndroidRuntime: FATAL EXCEPTION: main\n"
        "01-01 00:00:01.000  100  100 I SystemServer: boring info line\n"
    )
    events = parse_logcat(sample)
    sigs = {e.signature for e in events}
    assert "anr" in sigs
    assert "fatal_exception" in sigs
    # The benign info line is not emitted.
    assert all(e.signature for e in events)


def test_logcat_detects_camera_and_selinux_and_binder():
    sample = (
        "01-01 00:01:00.205  120  140 E CameraService: Camera service error: device disconnected\n"
        "01-01 00:00:06.200  400  410 W SELinux: avc:  denied  { read } for pid=410\n"
        "01-01 00:00:06.350  500  510 E binder: binder transaction failed - dead process\n"
    )
    events = parse_logcat(sample)
    sigs = {e.signature for e in events}
    assert sigs == {"camera_service_error", "selinux_denial", "binder_failure"}


def test_dmesg_detects_panic_driver_thermal_oops_segfault_firmware_io():
    sample = (
        "[   31.998877] qcom-camss 1b00000.camss: driver timeout waiting for ISP ack\n"
        "[   32.001234] qcom-camss 1b00000.camss: I/O error on CSID0\n"
        "[   33.554321] firmware_class: firmware: failed to load qcom/adreno630.fw\n"
        "[   42.012345] Kernel panic - not syncing: Attempted to kill init!\n"
        "[   58.776655] thermal thermal_zone0: thermal throttling, cdev0: cooling state 3\n"
        "[   59.000122] BUG: unable to handle kernel paging request — Oops\n"
        "[   60.123456] traps: app[1234] segfault at 0\n"
    )
    events = parse_dmesg(sample)
    sigs = {e.signature for e in events}
    assert {
        "driver_timeout",
        "io_error",
        "firmware_load_failure",
        "kernel_panic",
        "thermal_throttling",
        "oops",
        "segfault",
    } <= sigs


def test_parse_directory_against_sample_logs():
    logcat_events = parse_directory(SAMPLE_LOGCAT_DIR)
    dmesg_events = parse_directory(SAMPLE_DMESG_DIR)
    # Each sample folder should produce at least one classified event.
    assert any(e.signature == "fatal_exception" for e in logcat_events)
    assert any(e.signature == "kernel_panic" for e in dmesg_events)


def test_logcat_event_has_timestamp_and_subsystem():
    sample = "01-01 00:00:05.300  200  220 E ActivityManager: ANR in com.example.app\n"
    events = parse_logcat(sample)
    assert len(events) == 1
    ev = events[0]
    assert ev.timestamp == "01-01 00:00:05.300"
    assert ev.severity == "E"
    assert ev.subsystem == "ActivityManager"
    assert ev.signature == "anr"
    assert ev.source == "logcat"
