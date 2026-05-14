# Android / Linux Debug Notes

Field notes for the signatures the harness recognizes, with the first
moves a validation engineer would normally make.

## Android (logcat)

| Signature              | First moves                                                                                  |
|------------------------|-----------------------------------------------------------------------------------------------|
| `fatal_exception`      | `adb pull /data/tombstones/`; identify process; rebuild with debug symbols and re-run.        |
| `anr`                  | Pull `/data/anr/traces.txt`; check main-thread stack and binder traffic at ANR time.          |
| `watchdog`             | Check `dmesg` for matching softlockup; usually correlates with a stuck kernel thread.         |
| `selinux_denial`       | `audit2allow -d`; decide policy-fix vs. legitimate access denial.                             |
| `camera_service_error` | Enable `setprop persist.camera.cb.dumpsys 1`; capture camx-hal traces, then check sensor I2C. |
| `binder_failure`       | `cat /sys/kernel/debug/binder/transactions` for stuck txns; check service availability.       |
| `crash`                | Decode tombstone with `ndk-stack`/`addr2line`; map crashing PC to symbol.                      |

## Linux (dmesg)

| Signature                  | First moves                                                                       |
|----------------------------|-----------------------------------------------------------------------------------|
| `kernel_panic`             | Decode panic backtrace; bisect kernel commits since last passing build.           |
| `oops`                     | Check for matching CVE; inspect faulting module via `lsmod` and `modinfo`.        |
| `segfault`                 | Re-run under ASan or core-dump enabled; map fault PC.                              |
| `driver_timeout`           | Check clock/regulator state via `clk_summary`; inspect IRQ counters.              |
| `thermal_throttling`       | Plot `tz0` temperature vs. workload; verify cooling-device policy.                |
| `firmware_load_failure`    | Confirm firmware blob is on `/vendor/firmware` and listed in the build manifest.   |
| `io_error`                 | Capture SMART / eMMC health; check bus error counters around failure window.       |

## Performance / power regressions

- p95 / p99 latency spikes that don't show in mean are the dangerous ones —
  always include tail metrics in pass criteria.
- Power regressions often correlate with a wakelock or a wireless driver
  that fails to drop to a low-power state — start with `dumpsys power`.

## Boot regressions

- Compare `dmesg` timestamps from the regressed boot against the last
  passing baseline; look for a service whose initialization newly takes
  much longer.
- `systemd-analyze blame` (Linux) or bootchart (Android) localizes the
  slowdown to a specific unit/service.

## Why flaky tests are dangerous

A flaky test slowly trains reviewers to ignore red builds, which means
the *real* regression that hides behind the next flake will not be acted
on. Quarantine flaky tests immediately and treat fixing them as a P1.
