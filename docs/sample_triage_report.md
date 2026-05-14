# Sample Triage Report

This is an example of the kind of developer-facing summary the harness
produces. The wording is deterministic — every field comes from
`triage.py` plus the parsed log/metric facts.

---

## Failure AI-001 (iteration 1)

**Reason:** `max_p95_latency_ms` breached: 62.40 ms > 50.00 ms

- **Category:** Performance Regression
- **Owner:** Performance / Runtime
- **Severity:** high
- **Signature:** `latency_breach:p95`
- **Rationale:** `inference_latency_ms` p95 was 62.40 against 50.00 threshold.
- **Next step:** Compare runtime logs against the previous passing run
  and inspect CPU/GPU frequency traces during the regression window.

## Failure CAM-001 (iteration 1)

**Reason:** forbidden log pattern matched: 'camera service error'

- **Category:** Camera Subsystem
- **Owner:** Camera / ISP
- **Severity:** high
- **Signature:** `camera_service_error`
- **Rationale:** CameraService: Camera service error: device disconnected
- **Next step:** Pull camera HAL + CamX logs, replay with cameraserver
  verbose tag, check sensor I2C errors.

## Failure STAB-001 (iteration 2)

**Reason:** forbidden log pattern matched: 'kernel panic'

- **Category:** System Stability
- **Owner:** Kernel / Platform
- **Severity:** critical
- **Signature:** `kernel_panic`
- **Rationale:** kernel: Kernel panic - not syncing: Attempted to kill init!
- **Next step:** Capture full dmesg and ramoops, decode panic backtrace,
  bisect kernel commits since last passing build.

## Flaky tests

- **AI-001** — 2 pass / 1 fail across 3 iterations in the same run.
  Stabilize the test fixture or quarantine pending root-cause.
