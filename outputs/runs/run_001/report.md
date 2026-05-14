# Run Report — chipset_smoke

- **Run ID:** run_001
- **Device:** simulated_android
- **Started:** 2026-05-14T21:59:28.423996+00:00
- **Finished:** 2026-05-14T21:59:28.438572+00:00
- **Pass / Fail:** 10 / 5
- **Flaky tests:** AI-001, BOOT-001, CAM-001, POWER-001, STAB-001
## Pass / Fail Table

| Test ID | Iteration | Status | Duration (s) | Failure | Triage |
|---|---|---|---|---|---|
| BOOT-001 | 1 | pass | 0.000 |  |  |
| POWER-001 | 1 | pass | 0.000 |  |  |
| AI-001 | 1 | pass | 0.000 |  |  |
| CAM-001 | 1 | fail | 0.000 | command exit_code=1 | Camera Subsystem |
| STAB-001 | 1 | pass | 0.000 |  |  |
| BOOT-001 | 2 | fail | 0.000 | max_boot_time_sec breached: 38.50 > 35.00 | Boot Regression |
| POWER-001 | 2 | fail | 0.000 | max_avg_power_mw breached: 905.00 > 800.00 | Power Regression |
| AI-001 | 2 | fail | 0.000 | max_p95_latency_ms breached: 76.50 > 50.00 | Performance Regression |
| CAM-001 | 2 | pass | 0.000 |  |  |
| STAB-001 | 2 | fail | 0.000 | command exit_code=1 | System Stability |
| BOOT-001 | 3 | pass | 0.000 |  |  |
| POWER-001 | 3 | pass | 0.000 |  |  |
| AI-001 | 3 | pass | 0.000 |  |  |
| CAM-001 | 3 | pass | 0.000 |  |  |
| STAB-001 | 3 | pass | 0.000 |  |  |

## Failure Triage

### CAM-001 (iteration 1)

- **Reason:** command exit_code=1
- **Category:** Camera Subsystem
- **Owner:** Camera / ISP
- **Severity:** high
- **Signature:** `camera_service_error`
- **Next step:** Pull camera HAL + CamX logs, replay with cameraserver verbose tag, check sensor I2C errors.
- **Rationale:** CameraService: Camera service error: device disconnected
### BOOT-001 (iteration 2)

- **Reason:** max_boot_time_sec breached: 38.50 > 35.00
- **Category:** Boot Regression
- **Owner:** Kernel / Platform
- **Severity:** high
- **Signature:** `boot_breach:max`
- **Next step:** Compare bootchart and dmesg timestamps with the last passing baseline to localize the slowdown to a service or driver init.
- **Rationale:** boot_time_sec was 38.50s against 35.00s threshold.
### POWER-001 (iteration 2)

- **Reason:** max_avg_power_mw breached: 905.00 > 800.00
- **Category:** Power Regression
- **Owner:** Thermal / Power
- **Severity:** high
- **Signature:** `power_breach:mean`
- **Next step:** Profile idle residency states and check for wakelocks, suspect wireless or display driver wakeups.
- **Rationale:** power_mw mean was 905.00 mW against 800.00 mW threshold.
### AI-001 (iteration 2)

- **Reason:** max_p95_latency_ms breached: 76.50 > 50.00
- **Category:** Performance Regression
- **Owner:** Performance / Runtime
- **Severity:** high
- **Signature:** `latency_breach:p95`
- **Next step:** Compare runtime logs against the previous passing run and inspect CPU/GPU frequency traces during the regression window.
- **Rationale:** inference_latency_ms p95 was 76.50 against 50.00 threshold.
### STAB-001 (iteration 2)

- **Reason:** command exit_code=1
- **Category:** System Stability
- **Owner:** Kernel / Platform
- **Severity:** critical
- **Signature:** `kernel_panic`
- **Next step:** Capture full dmesg and ramoops, decode panic backtrace, bisect kernel commits since last passing build.
- **Rationale:** Kernel panic - not syncing: Attempted to kill init!

## Top Log Signatures

| Signature | Count |
|---|---|
| `camera_service_error` | 1 |
| `driver_timeout` | 1 |
| `io_error` | 1 |
| `kernel_panic` | 1 |
| `thermal_throttling` | 1 |

## Metric Summaries

| Test ID | Iteration | Metric | Mean | p50 | p95 | p99 | Min | Max |
|---|---|---|---|---|---|---|---|---|
| BOOT-001 | 1 | boot_time_sec | 30.00 | 30.00 | 30.00 | 30.00 | 30.00 | 30.00 |
| POWER-001 | 1 | peak_power_mw | 840.00 | 840.00 | 840.00 | 840.00 | 840.00 | 840.00 |
| POWER-001 | 1 | power_mw | 720.00 | 720.00 | 736.00 | 736.00 | 704.00 | 736.00 |
| AI-001 | 1 | inference_latency_ms | 41.84 | 41.90 | 45.80 | 45.80 | 38.00 | 45.80 |
| CAM-001 | 1 | camera_open_latency_ms | 180.00 | 180.00 | 180.00 | 180.00 | 180.00 | 180.00 |
| STAB-001 | 1 | soak_uptime_sec | 3600.00 | 3600.00 | 3600.00 | 3600.00 | 3600.00 | 3600.00 |
| BOOT-001 | 2 | boot_time_sec | 38.50 | 38.50 | 38.50 | 38.50 | 38.50 | 38.50 |
| POWER-001 | 2 | peak_power_mw | 1025.00 | 1025.00 | 1025.00 | 1025.00 | 1025.00 | 1025.00 |
| POWER-001 | 2 | power_mw | 905.00 | 905.00 | 921.00 | 921.00 | 889.00 | 921.00 |
| AI-001 | 2 | inference_latency_ms | 68.16 | 67.20 | 76.50 | 77.80 | 62.00 | 77.80 |
| CAM-001 | 2 | camera_open_latency_ms | 95.00 | 95.00 | 95.00 | 95.00 | 95.00 | 95.00 |
| STAB-001 | 2 | soak_uptime_sec | 1742.00 | 1742.00 | 1742.00 | 1742.00 | 1742.00 | 1742.00 |
| BOOT-001 | 3 | boot_time_sec | 30.00 | 30.00 | 30.00 | 30.00 | 30.00 | 30.00 |
| POWER-001 | 3 | peak_power_mw | 840.00 | 840.00 | 840.00 | 840.00 | 840.00 | 840.00 |
| POWER-001 | 3 | power_mw | 720.00 | 720.00 | 736.00 | 736.00 | 704.00 | 736.00 |
| AI-001 | 3 | inference_latency_ms | 41.84 | 41.90 | 45.80 | 45.80 | 38.00 | 45.80 |
| CAM-001 | 3 | camera_open_latency_ms | 95.00 | 95.00 | 95.00 | 95.00 | 95.00 | 95.00 |
| STAB-001 | 3 | soak_uptime_sec | 3600.00 | 3600.00 | 3600.00 | 3600.00 | 3600.00 | 3600.00 |

## Recommended Next Steps

- **CAM-001** (Camera Subsystem): Pull camera HAL + CamX logs, replay with cameraserver verbose tag, check sensor I2C errors.
- **BOOT-001** (Boot Regression): Compare bootchart and dmesg timestamps with the last passing baseline to localize the slowdown to a service or driver init.
- **POWER-001** (Power Regression): Profile idle residency states and check for wakelocks, suspect wireless or display driver wakeups.
- **AI-001** (Performance Regression): Compare runtime logs against the previous passing run and inspect CPU/GPU frequency traces during the regression window.
- **STAB-001** (System Stability): Capture full dmesg and ramoops, decode panic backtrace, bisect kernel commits since last passing build.
