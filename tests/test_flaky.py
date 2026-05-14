"""Flaky-test detection tests."""

from __future__ import annotations

from test_harness.flaky import (
    IterationResult,
    detect_flaky_within_run,
    detect_signature_drift,
)


def _r(test_id: str, it: int, status: str, sig: str = "") -> IterationResult:
    return IterationResult(test_id=test_id, iteration=it, status=status, failure_signature=sig)


def test_mixed_pass_fail_is_flaky():
    results = [_r("AI-001", 1, "pass"), _r("AI-001", 2, "fail"), _r("AI-001", 3, "pass")]
    verdicts = detect_flaky_within_run(results)
    assert verdicts[0].test_id == "AI-001"
    assert verdicts[0].is_flaky is True
    assert verdicts[0].pass_count == 2
    assert verdicts[0].fail_count == 1


def test_unanimous_pass_is_not_flaky():
    results = [_r("BOOT-001", i, "pass") for i in range(1, 4)]
    verdicts = detect_flaky_within_run(results)
    assert verdicts[0].is_flaky is False


def test_unanimous_fail_is_not_flaky():
    results = [_r("STAB-001", i, "fail") for i in range(1, 4)]
    verdicts = detect_flaky_within_run(results)
    assert verdicts[0].is_flaky is False


def test_signature_drift_across_runs():
    drift = detect_signature_drift(
        {
            "AI-001": ["latency_breach:p95", "thermal_throttling"],
            "BOOT-001": ["kernel_panic", "kernel_panic"],
            "POWER-001": [],
        }
    )
    assert drift["AI-001"] is True
    assert drift["BOOT-001"] is False
    assert drift["POWER-001"] is False
