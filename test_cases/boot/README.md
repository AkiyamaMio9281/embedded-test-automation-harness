# Boot Tests

Cold-boot and reboot scenarios. Pass criteria are time-to-`Boot is finished`,
absence of `kernel panic` / `FATAL EXCEPTION`, and clean SELinux/AVC log
during the boot window.

Driven by `BOOT-001` in `test_plans/smoke.yaml`.
