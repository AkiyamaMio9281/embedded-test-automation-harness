# Embedded Test Automation Harness

> **Demo**
>
> ```powershell
> python -m venv .venv ; .\.venv\Scripts\Activate.ps1
> python -m pip install -r requirements.txt
> python -m test_harness.cli run --plan test_plans/smoke.yaml --device simulated --output outputs/runs/run_001 --run-id run_001
> python -m pytest -q
> ```
>
> Sample output: `outputs/runs/run_001/report.md` (and `report.html`,
> `results.csv`, `events.csv`, `metrics_summary.csv`).
> SQLite run history lives at `outputs/history.sqlite`.
> 28 unit tests cover parsing, triage, flaky detection, plan validation,
> and the end-to-end executor.

## Purpose

Build a realistic automation framework for embedded, Android, Linux, or ADAS-style system testing.

This project is designed for roles involving test automation, system validation, mobile chipset testing, Linux/Android debugging, QA, and AI-assisted test triage.



## Core Story

The project should demonstrate that you can:

- design test plans
- implement automated test cases
- execute tests against device-like logs and metrics
- detect failures and flaky behavior
- parse system logs
- produce bug triage reports
- work with Linux/Android-style validation workflows

This is not a simple pytest demo. It should look like a compact version of an engineering validation harness.

## Recommended Tech Stack

Use:

- Python 3.10+
- pytest
- pydantic
- pandas
- typer
- rich
- jinja2
- matplotlib or plotly
- SQLite

Optional:

- adb integration
- paramiko for SSH-based Linux device execution
- loguru for logging
- scikit-learn for flaky-test classification
- FastAPI or Streamlit dashboard

## Suggested Repository Structure

```text
embedded-test-automation-harness/
  README.md
  requirements.txt
  pyproject.toml
  test_harness/
    cli.py
    config.py
    device.py
    adb_device.py
    ssh_device.py
    simulated_device.py
    test_plan.py
    executor.py
    log_parser.py
    metrics_parser.py
    triage.py
    flaky.py
    report.py
    storage.py
  test_cases/
    boot/
    power/
    camera/
    connectivity/
    ai_inference/
  sample_logs/
    android_logcat/
    linux_dmesg/
    perf/
  outputs/
    runs/
    reports/
  tests/
    test_log_parser.py
    test_triage.py
    test_flaky.py
    test_executor.py
  docs/
    test_strategy.md
    sample_triage_report.md
    android_linux_debug_notes.md
```

## Minimum Viable Version

The first useful version should include:

1. YAML test plan format.
2. Simulated device backend.
3. Test executor.
4. Android logcat parser.
5. Linux dmesg parser.
6. Failure classification rules.
7. Flaky test detector.
8. Markdown/HTML report.
9. pytest unit tests for parsing and triage.

## Example Test Plan

Create `test_plans/smoke.yaml`:

```yaml
name: chipset_smoke
device: simulated_android
iterations: 3
tests:
  - id: BOOT-001
    name: Boot completes within threshold
    category: boot
    command: simulate_boot
    timeout_sec: 60
    pass_criteria:
      max_boot_time_sec: 35
      forbidden_log_patterns:
        - "kernel panic"
        - "fatal exception"

  - id: POWER-001
    name: Idle power remains under threshold
    category: power
    command: simulate_idle_power
    timeout_sec: 30
    pass_criteria:
      max_avg_power_mw: 800

  - id: AI-001
    name: AI inference latency stays below threshold
    category: ai_inference
    command: simulate_ai_inference
    timeout_sec: 45
    pass_criteria:
      max_p95_latency_ms: 50
```

## Build Steps

### 1. Create Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Suggested `requirements.txt`:

```text
pydantic
pyyaml
pandas
typer
rich
jinja2
pytest
```

### 2. Define the Device Interface

Create a common protocol:

```text
connect()
run_command(command, timeout_sec)
pull_logs()
collect_metrics()
disconnect()
```

Implement `SimulatedDevice` first. It should return deterministic sample logs and metrics.

Later add:

- `AdbDevice`
- `SshDevice`

The simulated backend makes the project runnable without hardware.

### 3. Implement Test Plan Loader

The loader should:

- read YAML
- validate required fields
- normalize category names
- validate pass criteria
- produce a typed test plan object

This shows production discipline and prevents silent bad configs.

### 4. Implement Executor

Execution flow:

```text
load test plan
connect to device
for each iteration:
  for each test:
    run command
    collect logs
    collect metrics
    evaluate pass criteria
    store result
disconnect
generate report
```

Result fields:

```text
run_id
test_id
iteration
status
duration_sec
failure_reason
log_path
metrics_path
triage_category
timestamp
```

### 5. Implement Log Parsers

Android logcat parser should detect:

- fatal exception
- ANR
- crash
- watchdog
- SELinux denial
- camera service error
- binder transaction failure

Linux dmesg parser should detect:

- kernel panic
- oops
- segmentation fault
- driver timeout
- thermal throttling
- firmware load failure
- I/O error

Each parser should return structured events:

```text
timestamp
severity
subsystem
message
signature
```

### 6. Implement Metrics Parser

Support simple files:

```csv
timestamp,metric,value,unit
2026-05-14T10:00:00,power_mw,720,mW
2026-05-14T10:00:01,inference_latency_ms,42,ms
```

Compute:

- mean
- min/max
- p50
- p95
- p99
- threshold pass/fail

### 7. Implement Triage Rules

Create deterministic rules:

```text
kernel panic -> System Stability
fatal exception -> Framework Crash
driver timeout -> Driver/Firmware
thermal throttling -> Performance/Thermal
p95 latency threshold breach -> Performance Regression
intermittent failure across iterations -> Flaky
```

Output should include:

- likely owner team
- severity
- recommended next debugging step

Example:

```text
Failure AI-001 classified as Performance Regression. p95 latency was 68 ms against a 50 ms threshold. Recommended next step: compare runtime logs against previous passing run and inspect CPU/GPU frequency traces.
```

### 8. Implement Flaky Test Detection

A test is flaky if:

- it passes and fails across repeated iterations in the same run
- or its failure signature changes across runs
- or latency crosses threshold intermittently

Save historical results in SQLite:

```text
runs
test_results
failure_signatures
metrics_summary
```

### 9. Implement CLI

Example:

```powershell
python -m test_harness.cli run `
  --plan test_plans/smoke.yaml `
  --device simulated `
  --output outputs/runs/run_001
```

Other commands:

```powershell
python -m test_harness.cli parse-logs --input sample_logs/android_logcat
python -m test_harness.cli summarize --run outputs/runs/run_001
python -m test_harness.cli compare --baseline outputs/runs/run_001 --candidate outputs/runs/run_002
```

### 10. Generate Reports

Report should include:

- run summary
- pass/fail table
- failure triage
- flaky test list
- top log signatures
- latency/power charts
- recommended debugging steps

Outputs:

```text
outputs/runs/run_001/results.csv
outputs/runs/run_001/events.csv
outputs/runs/run_001/metrics_summary.csv
outputs/runs/run_001/report.md
outputs/runs/run_001/report.html
```

## Optional Advanced Features

Add these after the MVP:

- adb real-device command backend
- SSH backend for Linux target
- CI integration that runs simulated tests
- AI-generated triage summary from deterministic facts
- dashboard showing run history
- baseline-vs-candidate regression comparison
- JUnit XML export for CI systems

## Testing Plan

Minimum tests:

- YAML test plan validation
- log parser detects known signatures
- metrics parser computes p95 correctly
- triage maps failures to categories
- flaky detector identifies mixed pass/fail results
- report generator writes expected files

Run:

```powershell
python -m pytest -q
```

## Resume Bullets

Use bullets like:

- Built an embedded test automation harness with YAML test plans, simulated Android/Linux device execution, structured log parsing, and automated failure triage.
- Implemented latency, power, and stability checks with flaky-test detection across repeated validation runs.
- Generated CI-ready Markdown/HTML reports summarizing pass rates, failure signatures, likely owner teams, and recommended debugging steps.

## Interview Talking Points

Be ready to explain:

- how logcat and dmesg help with initial triage
- why flaky tests are dangerous in automation
- how pass criteria should be separated from execution code
- how you would connect the harness to real Android devices through adb
- how to compare baseline and candidate firmware/software builds
- what makes a good bug report for a developer team

## Definition of Done

The project is portfolio-ready when:

- simulated test plan runs end to end
- logs are parsed into structured events
- failures are classified
- flaky behavior is detected
- report is generated
- tests pass
- README includes a demo command and sample output path

## License

MIT — see [LICENSE](LICENSE).
