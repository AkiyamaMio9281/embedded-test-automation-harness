"""Test executor.

Drives the device, parses logs/metrics, evaluates pass criteria, calls
triage, persists artifacts under ``outputs/runs/<run_id>/``, and writes
to the SQLite history database.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import HISTORY_DB
from .device import Device, LogBundle, MetricSample
from .flaky import IterationResult, detect_flaky_within_run
from .log_parser import LogEvent, parse_dmesg, parse_logcat
from .metrics_parser import MetricSummary, get_value, summarize
from .storage import (
    connect,
    insert_metric_summary,
    insert_result,
    insert_run,
    insert_signature,
    mark_run_finished,
)
from .test_plan import PassCriteria, TestCase, TestPlan
from .triage import (
    TriageVerdict,
    triage_flaky,
    triage_log_events,
    triage_threshold_breach,
)


@dataclass
class IterationArtifact:
    test_id: str
    iteration: int
    status: str
    duration_sec: float
    failure_reason: str
    triage: TriageVerdict | None
    events: list[LogEvent]
    metric_summaries: list[MetricSummary]
    metrics: list[MetricSample]
    timestamp: str
    log_path: str = ""
    metrics_path: str = ""


@dataclass
class RunReport:
    run_id: str
    plan_name: str
    device: str
    started_at: str
    finished_at: str
    output_dir: Path
    iterations: list[IterationArtifact] = field(default_factory=list)
    flaky_test_ids: list[str] = field(default_factory=list)

    @property
    def pass_count(self) -> int:
        return sum(1 for it in self.iterations if it.status == "pass")

    @property
    def fail_count(self) -> int:
        return sum(1 for it in self.iterations if it.status != "pass")


def _evaluate_pass_criteria(
    criteria: PassCriteria,
    summaries: list[MetricSummary],
    events: list[LogEvent],
) -> tuple[bool, str, TriageVerdict | None]:
    """Return (passed, failure_reason, optional_metric_breach_verdict)."""

    # 1. Forbidden log patterns short-circuit on first match.
    log_text_joined = " | ".join(f"{e.signature} {e.message}" for e in events).lower()
    for pat in criteria.forbidden_log_patterns:
        if pat.lower() in log_text_joined:
            return False, f"forbidden log pattern matched: '{pat}'", None

    # 2. Required log patterns.
    for pat in criteria.required_log_patterns:
        if pat.lower() not in log_text_joined:
            return False, f"required log pattern missing: '{pat}'", None

    # 3. Threshold checks. Each criterion knows which metric/stat to read.
    threshold_map: list[tuple[str, str, float | None, str]] = [
        ("boot_time_sec", "max", criteria.max_boot_time_sec, "max_boot_time_sec"),
        ("power_mw", "mean", criteria.max_avg_power_mw, "max_avg_power_mw"),
        ("peak_power_mw", "max", criteria.max_peak_power_mw, "max_peak_power_mw"),
        ("inference_latency_ms", "p50", criteria.max_p50_latency_ms, "max_p50_latency_ms"),
        ("inference_latency_ms", "p95", criteria.max_p95_latency_ms, "max_p95_latency_ms"),
        ("inference_latency_ms", "p99", criteria.max_p99_latency_ms, "max_p99_latency_ms"),
        ("temperature_c", "max", criteria.max_temperature_c, "max_temperature_c"),
    ]
    for metric, stat, threshold, label in threshold_map:
        if threshold is None:
            continue
        observed = get_value(summaries, metric, stat)
        if observed is None:
            # The metric simply was not present this iteration — skip.
            continue
        if observed > threshold:
            verdict = triage_threshold_breach(metric, stat, observed, threshold)
            return False, f"{label} breached: {observed:.2f} > {threshold:.2f}", verdict

    if criteria.min_throughput_fps is not None:
        observed = get_value(summaries, "throughput_fps", "mean")
        if observed is not None and observed < criteria.min_throughput_fps:
            verdict = triage_threshold_breach(
                "throughput_fps", "mean", observed, criteria.min_throughput_fps
            )
            return False, (
                f"min_throughput_fps breached: {observed:.2f} < "
                f"{criteria.min_throughput_fps:.2f}"
            ), verdict

    return True, "", None


def _write_iteration_artifacts(
    out_dir: Path,
    test: TestCase,
    iteration: int,
    logs: LogBundle,
    metrics: list[MetricSample],
) -> tuple[Path, Path]:
    iter_dir = out_dir / "tests" / test.id / f"iter_{iteration:03d}"
    iter_dir.mkdir(parents=True, exist_ok=True)

    log_path = iter_dir / "device.log"
    with log_path.open("w", encoding="utf-8") as f:
        if logs.logcat:
            f.write("=== logcat ===\n")
            f.write(logs.logcat)
            if not logs.logcat.endswith("\n"):
                f.write("\n")
        if logs.dmesg:
            f.write("=== dmesg ===\n")
            f.write(logs.dmesg)
            if not logs.dmesg.endswith("\n"):
                f.write("\n")

    metrics_path = iter_dir / "metrics.csv"
    with metrics_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "metric", "value", "unit"])
        for m in metrics:
            writer.writerow([m.timestamp, m.metric, m.value, m.unit])

    return log_path, metrics_path


def _write_run_csvs(run_dir: Path, report: RunReport) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)

    # results.csv — one row per iteration.
    with (run_dir / "results.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "run_id",
                "test_id",
                "iteration",
                "status",
                "duration_sec",
                "failure_reason",
                "log_path",
                "metrics_path",
                "triage_category",
                "timestamp",
            ]
        )
        for it in report.iterations:
            w.writerow(
                [
                    report.run_id,
                    it.test_id,
                    it.iteration,
                    it.status,
                    f"{it.duration_sec:.4f}",
                    it.failure_reason,
                    it.log_path,
                    it.metrics_path,
                    it.triage.category if it.triage else "",
                    it.timestamp,
                ]
            )

    # events.csv — one row per parsed log event.
    with (run_dir / "events.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["test_id", "iteration", "source", "timestamp", "severity",
             "subsystem", "signature", "message"]
        )
        for it in report.iterations:
            for ev in it.events:
                w.writerow(
                    [
                        it.test_id,
                        it.iteration,
                        ev.source,
                        ev.timestamp,
                        ev.severity,
                        ev.subsystem,
                        ev.signature,
                        ev.message,
                    ]
                )

    # metrics_summary.csv — aggregated metrics per iteration.
    with (run_dir / "metrics_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["test_id", "iteration", "metric", "unit", "count",
             "mean", "min", "max", "p50", "p95", "p99"]
        )
        for it in report.iterations:
            for ms in it.metric_summaries:
                w.writerow(
                    [
                        it.test_id,
                        it.iteration,
                        ms.metric,
                        ms.unit,
                        ms.count,
                        f"{ms.mean:.4f}",
                        f"{ms.min:.4f}",
                        f"{ms.max:.4f}",
                        f"{ms.p50:.4f}",
                        f"{ms.p95:.4f}",
                        f"{ms.p99:.4f}",
                    ]
                )

    # A small manifest for the compare command.
    manifest = {
        "run_id": report.run_id,
        "plan_name": report.plan_name,
        "device": report.device,
        "started_at": report.started_at,
        "finished_at": report.finished_at,
        "pass_count": report.pass_count,
        "fail_count": report.fail_count,
        "flaky_test_ids": report.flaky_test_ids,
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def execute_plan(
    plan: TestPlan,
    device: Device,
    output_dir: str | Path,
    *,
    run_id: str | None = None,
    history_db: str | Path | None = None,
) -> RunReport:
    """Execute a test plan against ``device`` and produce a RunReport."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).isoformat()
    if run_id is None:
        run_id = out_dir.name or f"run_{int(datetime.now().timestamp())}"

    report = RunReport(
        run_id=run_id,
        plan_name=plan.name,
        device=device.name,
        started_at=started_at,
        finished_at="",
        output_dir=out_dir,
    )

    device.connect()
    try:
        for iteration in range(1, plan.iterations + 1):
            for test in plan.tests:
                artifact = _run_single(device, test, iteration, out_dir)
                report.iterations.append(artifact)
    finally:
        device.disconnect()

    # Mark flaky tests once all iterations are in.
    iter_results = [
        IterationResult(
            test_id=it.test_id,
            iteration=it.iteration,
            status=it.status,
            failure_signature=it.triage.signature if it.triage else "",
        )
        for it in report.iterations
    ]
    flaky_verdicts = detect_flaky_within_run(iter_results)
    report.flaky_test_ids = [v.test_id for v in flaky_verdicts if v.is_flaky]
    # Annotate failing iterations of flaky tests *without* a more specific
    # verdict — passes stay un-triaged so the report stays honest.
    for it in report.iterations:
        if (
            it.test_id in report.flaky_test_ids
            and it.status != "pass"
            and it.triage is None
        ):
            it.triage = triage_flaky(it.test_id)

    report.finished_at = datetime.now(timezone.utc).isoformat()
    _write_run_csvs(out_dir, report)

    # Persist to SQLite history.
    db_path = Path(history_db) if history_db else HISTORY_DB
    with connect(db_path) as conn:
        insert_run(conn, report.run_id, plan.name, device.name, started_at)
        for it in report.iterations:
            insert_result(
                conn,
                report.run_id,
                it.test_id,
                it.iteration,
                it.status,
                it.duration_sec,
                it.failure_reason,
                it.triage.category if it.triage else "",
                it.timestamp,
            )
            if it.triage and it.status != "pass":
                insert_signature(
                    conn,
                    report.run_id,
                    it.test_id,
                    it.iteration,
                    it.triage.signature,
                    it.triage.severity,
                    it.triage.owner,
                )
            for ms in it.metric_summaries:
                insert_metric_summary(
                    conn,
                    report.run_id,
                    it.test_id,
                    it.iteration,
                    ms.metric,
                    ms.mean,
                    ms.p50,
                    ms.p95,
                    ms.p99,
                    ms.min,
                    ms.max,
                )
        mark_run_finished(conn, report.run_id, report.finished_at)

    return report


def _run_single(
    device: Device, test: TestCase, iteration: int, out_dir: Path
) -> IterationArtifact:
    started = datetime.now(timezone.utc).isoformat()
    cmd_result = device.run_command(test.command, test.timeout_sec)
    logs = device.pull_logs()
    metrics = device.collect_metrics()

    events = parse_logcat(logs.logcat) + parse_dmesg(logs.dmesg)
    summaries = summarize(metrics)

    if cmd_result.exit_code != 0:
        status = "fail"
        failure_reason = f"command exit_code={cmd_result.exit_code}"
        triage = triage_log_events(events)
        if triage is None:
            triage = TriageVerdict(
                category="Command Failure",
                owner="Test Owner",
                severity="high",
                signature="nonzero_exit",
                rationale=failure_reason,
                next_step="Re-run with verbose stderr capture and inspect device-side state.",
            )
    else:
        passed, reason, breach_verdict = _evaluate_pass_criteria(
            test.pass_criteria, summaries, events
        )
        if passed:
            status, failure_reason, triage = "pass", "", None
        else:
            status = "fail"
            failure_reason = reason
            triage = breach_verdict or triage_log_events(events)

    log_path, metrics_path = _write_iteration_artifacts(
        out_dir, test, iteration, logs, metrics
    )

    return IterationArtifact(
        test_id=test.id,
        iteration=iteration,
        status=status,
        duration_sec=cmd_result.duration_sec,
        failure_reason=failure_reason,
        triage=triage,
        events=events,
        metric_summaries=summaries,
        metrics=metrics,
        timestamp=started,
        log_path=str(log_path.relative_to(out_dir)),
        metrics_path=str(metrics_path.relative_to(out_dir)),
    )


def iteration_as_row(it: IterationArtifact, run_id: str) -> dict:
    """Flat dict view of an iteration suitable for ad-hoc serialization."""
    base = asdict(it)
    base["run_id"] = run_id
    return base
