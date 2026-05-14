"""Triage rule tests."""

from __future__ import annotations

from test_harness.log_parser import LogEvent
from test_harness.triage import (
    triage_flaky,
    triage_log_events,
    triage_threshold_breach,
)


def _ev(sig: str, sev: str = "E") -> LogEvent:
    return LogEvent(
        timestamp="t",
        severity=sev,
        subsystem="x",
        message="m",
        signature=sig,
        source="logcat",
    )


def test_kernel_panic_dominates_lower_severity():
    verdict = triage_log_events([_ev("kernel_panic"), _ev("selinux_denial")])
    assert verdict is not None
    assert verdict.category == "System Stability"
    assert verdict.severity == "critical"


def test_camera_service_error_maps_to_camera_subsystem():
    verdict = triage_log_events([_ev("camera_service_error")])
    assert verdict is not None
    assert verdict.owner == "Camera / ISP"


def test_unknown_signature_falls_back_to_unclassified():
    verdict = triage_log_events([_ev("not_a_real_signature")])
    assert verdict is not None
    assert verdict.category == "Unclassified"


def test_threshold_breach_latency_maps_to_performance():
    v = triage_threshold_breach("inference_latency_ms", "p95", 68.0, 50.0)
    assert v.category == "Performance Regression"
    assert "compare" in v.next_step.lower()


def test_threshold_breach_power_maps_to_thermal_power():
    v = triage_threshold_breach("power_mw", "mean", 905.0, 800.0)
    assert v.category == "Power Regression"


def test_threshold_breach_boot_maps_to_boot_regression():
    v = triage_threshold_breach("boot_time_sec", "max", 38.5, 35.0)
    assert v.category == "Boot Regression"


def test_flaky_verdict_text_mentions_test_id():
    v = triage_flaky("AI-001")
    assert "AI-001" in v.rationale
    assert v.signature == "flaky"


def test_triage_empty_events_returns_none():
    assert triage_log_events([]) is None
