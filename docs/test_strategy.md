# Test Strategy

## Goals

The harness exists to give a single engineer the leverage of a validation
team: drive a device, capture logs and metrics, evaluate pass criteria,
classify failures, detect flakiness, and produce a report a developer can
actually act on.

It is intentionally compact (one Python package, no cloud services) but
follows the same architectural seams a production validation rig uses.

## Layers

1. **Device** — `connect()`, `run_command()`, `pull_logs()`,
   `collect_metrics()`, `disconnect()`. Implementations: `SimulatedDevice`
   (deterministic, runs anywhere), `AdbDevice` (stub), `SshDevice` (stub).
2. **Test plan** — YAML, validated by pydantic. Pass criteria live here,
   *never* in code, so changing a threshold does not require a code review.
3. **Executor** — drives the device, evaluates criteria, persists artifacts.
4. **Parsers** — turn raw log/metric blobs into structured rows.
5. **Triage** — deterministic, table-driven mapping from signature → owner /
   severity / next step. Reviewable without running anything.
6. **Flaky detection** — within-run iteration variance plus cross-run
   signature drift, backed by SQLite.
7. **Report** — Markdown + HTML, plus the raw CSV / SQLite for downstream
   tooling.

## What we measure and why

| Suite       | Metric                           | Why it matters                                          |
|-------------|----------------------------------|---------------------------------------------------------|
| boot        | `boot_time_sec`                  | First-impression UX; regression often signals init churn |
| power       | `power_mw` mean, `peak_power_mw` | Battery life and thermal headroom                       |
| ai_inference| `inference_latency_ms` p50/p95/p99 | NN runtime budget; tail latency is what users feel    |
| camera      | open latency, log absence        | Camera bring-up is a frequent first-day issue           |
| stability   | uptime + absence of `kernel panic` | Catches resource leaks and driver crashes              |

## Pass criteria philosophy

- One **threshold per criterion**, declared in YAML.
- The same metric can appear under multiple thresholds (p50 vs p95) — they
  are independent gates.
- Forbidden / required log patterns short-circuit *before* numeric checks,
  so a kernel panic is always reported as a stability issue rather than a
  latency one.
- Unknown keys in YAML are rejected by pydantic. Typos fail fast.

## Triage philosophy

Triage is rule-based and deterministic. A reviewer should be able to read
`triage.py` and predict what every failure type will be classified as.
That is the difference between an automation tool and a black box.

## Scaling out

- Add hardware backends by implementing the `Device` protocol —
  `AdbDevice` for Android targets, `SshDevice` for Linux, plus optional
  serial/JTAG for early bring-up boards.
- The SQLite history already supports cross-run signature drift; a future
  baseline-vs-candidate comparison can plot per-metric deltas directly.
- A JUnit XML exporter is straightforward (one writer over `results.csv`)
  for CI integration.
