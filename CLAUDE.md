# Embedded Test Automation Harness — Claude Context

## What this project is

A compact engineering-validation harness for embedded / Android / Linux / ADAS-style testing. YAML test plans drive a device backend (simulated by default, adb/ssh later), parse logcat and dmesg, score against pass criteria, classify failures, detect flaky tests, and produce CI-ready reports.

Target roles include Qualcomm AI/ADAS Test Automation, Qualcomm SWE, QA, KLA SWE, Intel validation roles.

See [README.md](README.md) for the full spec. This file is the working brief for Claude Code.

## Tech stack

- Python 3.10+
- pytest, pydantic, pyyaml
- pandas
- typer + rich (CLI)
- jinja2 (report templates)
- SQLite (run history for flaky-test detection)

Optional later: adb integration, paramiko (SSH), loguru, scikit-learn for flaky classification, FastAPI/Streamlit dashboard, JUnit XML export.

## Repository layout

```text
test_harness/
  cli.py, config.py
  device.py            # protocol
  simulated_device.py  # MVP backend
  adb_device.py, ssh_device.py
  test_plan.py, executor.py
  log_parser.py, metrics_parser.py
  triage.py, flaky.py
  report.py, storage.py
test_cases/            boot/, power/, camera/, connectivity/, ai_inference/
test_plans/            *.yaml   (e.g. smoke.yaml)
sample_logs/           android_logcat/, linux_dmesg/, perf/
outputs/               runs/, reports/   (gitignored)
tests/                 test_log_parser.py, test_triage.py, test_flaky.py, test_executor.py
docs/                  test_strategy.md, sample_triage_report.md, android_linux_debug_notes.md
```

## Common commands (PowerShell)

Setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run a test plan:

```powershell
python -m test_harness.cli run --plan test_plans/smoke.yaml --device simulated --output outputs/runs/run_001
```

Other CLI verbs:

```powershell
python -m test_harness.cli parse-logs --input sample_logs/android_logcat
python -m test_harness.cli summarize --run outputs/runs/run_001
python -m test_harness.cli compare --baseline outputs/runs/run_001 --candidate outputs/runs/run_002
```

Tests:

```powershell
python -m pytest -q
```

## Conventions

- **Device interface** is the seam: `connect()`, `run_command(cmd, timeout_sec)`, `pull_logs()`, `collect_metrics()`, `disconnect()`. Implement `SimulatedDevice` first; it must return deterministic logs/metrics so the project runs without hardware.
- **Test plans are YAML** with typed pass criteria. Validation via pydantic — fail fast on bad configs, do not silently coerce.
- **Pass criteria live in the plan, not in code.** Execution code should never hardcode thresholds.
- **Log parsers** emit structured events: `timestamp, severity, subsystem, message, signature`.
  - Android logcat signatures: fatal exception, ANR, crash, watchdog, SELinux denial, camera service error, binder transaction failure.
  - Linux dmesg signatures: kernel panic, oops, segfault, driver timeout, thermal throttling, firmware load failure, I/O error.
- **Triage rules are deterministic** and map signatures → category, likely owner team, severity, recommended next step.
- **Flaky detection**: a test is flaky if it mixes pass/fail across iterations in one run, or its failure signature changes across runs, or latency crosses threshold intermittently. Backed by SQLite tables: `runs`, `test_results`, `failure_signatures`, `metrics_summary`.
- **Run artifacts** under `outputs/runs/<run_id>/`: `results.csv`, `events.csv`, `metrics_summary.csv`, `report.md`, `report.html`.
- Result row schema: `run_id, test_id, iteration, status, duration_sec, failure_reason, log_path, metrics_path, triage_category, timestamp`.

## Definition of done

- `smoke.yaml` runs end-to-end against the simulated device.
- Logs are parsed into structured events; failures are classified with owner + next step.
- Flaky behavior is detected across iterations.
- Markdown + HTML report is generated.
- pytest passes.
- README has a copy-pasteable demo command and sample output path.

## Interview-ready talking points

How logcat / dmesg drive initial triage, why flaky tests are dangerous, separating pass criteria from execution code, scaling from simulated to real adb/ssh devices, baseline-vs-candidate comparison, what makes a good developer-facing bug report.
