"""Flaky-test detection.

A test is flagged flaky if any of:
  * its status varies across iterations within the same run
  * its failure signature differs across runs that all failed
  * a latency metric crosses its threshold only intermittently
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass
class IterationResult:
    test_id: str
    iteration: int
    status: str  # "pass" | "fail" | "error"
    failure_signature: str = ""
    breached_metric_value: float | None = None


@dataclass
class FlakyVerdict:
    test_id: str
    is_flaky: bool
    reason: str
    pass_count: int
    fail_count: int


def detect_flaky_within_run(results: list[IterationResult]) -> list[FlakyVerdict]:
    """Find tests whose iteration statuses are not unanimous."""
    by_test: dict[str, list[IterationResult]] = {}
    for r in results:
        by_test.setdefault(r.test_id, []).append(r)

    verdicts: list[FlakyVerdict] = []
    for test_id, rows in by_test.items():
        statuses = Counter(r.status for r in rows)
        passes = statuses.get("pass", 0)
        fails = statuses.get("fail", 0) + statuses.get("error", 0)
        is_flaky = passes > 0 and fails > 0
        if is_flaky:
            reason = (
                f"{passes} pass / {fails} fail across {len(rows)} iterations "
                "in the same run"
            )
        else:
            reason = "unanimous result across iterations"
        verdicts.append(
            FlakyVerdict(
                test_id=test_id,
                is_flaky=is_flaky,
                reason=reason,
                pass_count=passes,
                fail_count=fails,
            )
        )
    verdicts.sort(key=lambda v: (not v.is_flaky, v.test_id))
    return verdicts


def detect_signature_drift(
    history_signatures: dict[str, list[str]],
) -> dict[str, bool]:
    """Across previous failing runs, did the test fail with different signatures?

    ``history_signatures[test_id]`` is the list of failure_signatures for
    runs where this test failed. If the set has more than one distinct
    non-empty entry, the test is flaky-by-drift.
    """
    out: dict[str, bool] = {}
    for test_id, sigs in history_signatures.items():
        distinct = {s for s in sigs if s}
        out[test_id] = len(distinct) > 1
    return out
