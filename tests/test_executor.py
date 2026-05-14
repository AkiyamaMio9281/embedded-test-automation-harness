"""End-to-end executor tests against the simulated device."""

from __future__ import annotations

import json

from test_harness.config import PROJECT_ROOT
from test_harness.executor import execute_plan
from test_harness.report import write_reports
from test_harness.simulated_device import SimulatedDevice
from test_harness.test_plan import load_plan


def test_execute_smoke_plan_end_to_end(tmp_path):
    plan = load_plan(PROJECT_ROOT / "test_plans" / "smoke.yaml")
    device = SimulatedDevice()
    out_dir = tmp_path / "run_001"
    report = execute_plan(
        plan,
        device,
        out_dir,
        run_id="run_001",
        history_db=tmp_path / "history.sqlite",
    )

    # All expected per-iteration rows are present.
    assert len(report.iterations) == len(plan.tests) * plan.iterations

    # The simulated device deterministically produces some failures.
    assert report.fail_count > 0
    assert report.pass_count > 0

    # AI-001 alternates pass/fail across iterations -> flaky.
    assert "AI-001" in report.flaky_test_ids

    # Output files were written.
    assert (out_dir / "results.csv").exists()
    assert (out_dir / "events.csv").exists()
    assert (out_dir / "metrics_summary.csv").exists()
    assert (out_dir / "manifest.json").exists()

    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == "run_001"
    assert manifest["plan_name"] == "chipset_smoke"

    md_path, html_path = write_reports(report)
    assert md_path.exists() and html_path.exists()
    md = md_path.read_text(encoding="utf-8")
    assert "chipset_smoke" in md
    assert "AI-001" in md


def test_boot_iteration_2_breach_classified_as_boot_regression(tmp_path):
    plan = load_plan(PROJECT_ROOT / "test_plans" / "smoke.yaml")
    device = SimulatedDevice()
    report = execute_plan(
        plan,
        device,
        tmp_path / "run",
        run_id="run_boot_check",
        history_db=tmp_path / "history.sqlite",
    )
    boot_failures = [
        it for it in report.iterations if it.test_id == "BOOT-001" and it.status != "pass"
    ]
    assert boot_failures, "expected at least one BOOT-001 failure from the simulator"
    assert boot_failures[0].triage is not None
    assert boot_failures[0].triage.category == "Boot Regression"


def test_camera_failure_carries_camera_or_driver_triage(tmp_path):
    plan = load_plan(PROJECT_ROOT / "test_plans" / "smoke.yaml")
    device = SimulatedDevice()
    report = execute_plan(
        plan,
        device,
        tmp_path / "run",
        run_id="run_cam_check",
        history_db=tmp_path / "history.sqlite",
    )
    cam_failures = [
        it for it in report.iterations if it.test_id == "CAM-001" and it.status != "pass"
    ]
    assert cam_failures, "expected CAM-001 to fail on at least one iteration"
    assert cam_failures[0].triage is not None
    assert cam_failures[0].triage.category in {"Camera Subsystem", "Driver / Firmware"}
