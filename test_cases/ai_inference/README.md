# AI Inference Tests

Latency-budget checks for on-device NN runtimes. Per-sample
`inference_latency_ms` is aggregated to mean/p50/p95/p99 and compared
against the budget declared in YAML.

Driven by `AI-001` in `test_plans/smoke.yaml`.
