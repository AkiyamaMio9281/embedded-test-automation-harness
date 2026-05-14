# Test Cases

This directory holds per-category notes and any hand-written helpers for
test cases. Test execution itself is driven by YAML test plans under
`test_plans/` — these subfolders document the intent of each suite so a
reviewer can read them top-down before opening code.

- `boot/` — first-boot and reboot timing checks
- `power/` — idle / load power envelopes
- `camera/` — camera HAL open, streaming, and ISP timing
- `connectivity/` — Wi-Fi, BT, modem attach checks
- `ai_inference/` — NN runtime latency and throughput
