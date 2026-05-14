"""Deterministic failure triage.

Maps log-event signatures and pass-criteria breaches to a category,
likely owner team, severity, and a recommended debugging next step.
The rules are intentionally simple and table-driven so they can be
audited by reviewers without running the code.
"""

from __future__ import annotations

from dataclasses import dataclass

from .log_parser import LogEvent


@dataclass
class TriageVerdict:
    category: str
    owner: str
    severity: str  # "low" | "medium" | "high" | "critical"
    signature: str
    rationale: str
    next_step: str


# signature -> (category, owner, severity, next_step)
_SIGNATURE_RULES: dict[str, tuple[str, str, str, str]] = {
    "kernel_panic": (
        "System Stability",
        "Kernel / Platform",
        "critical",
        "Capture full dmesg and ramoops, decode panic backtrace, bisect kernel commits since last passing build.",
    ),
    "oops": (
        "System Stability",
        "Kernel / Platform",
        "high",
        "Decode the Oops backtrace and check for matching kernel CVEs or driver regressions.",
    ),
    "fatal_exception": (
        "Framework Crash",
        "Android Framework",
        "high",
        "Pull tombstones and stack traces from /data/anr/ and /data/tombstones/, identify offending package.",
    ),
    "anr": (
        "Framework Responsiveness",
        "Android Framework",
        "high",
        "Inspect traces.txt for main-thread block; correlate with binder traffic and CPU load at ANR time.",
    ),
    "crash": (
        "Native Crash",
        "Android Framework",
        "high",
        "Run addr2line / breakpad on tombstone to localize the native crash to a specific .so symbol.",
    ),
    "watchdog": (
        "System Stability",
        "Kernel / Platform",
        "high",
        "Cross-check watchdog timeout against kernel softlockup messages; bisect last DRM/GPU driver change.",
    ),
    "selinux_denial": (
        "Security Policy",
        "Platform Security",
        "medium",
        "Audit2allow the denial; confirm whether the rule is missing or the access is genuinely disallowed.",
    ),
    "camera_service_error": (
        "Camera Subsystem",
        "Camera / ISP",
        "high",
        "Pull camera HAL + CamX logs, replay with cameraserver verbose tag, check sensor I2C errors.",
    ),
    "binder_failure": (
        "IPC",
        "Android Framework",
        "medium",
        "Inspect /sys/kernel/debug/binder/transactions for stuck transactions and check service availability.",
    ),
    "segfault": (
        "Native Crash",
        "Userspace",
        "high",
        "Re-run under address sanitizer or core-dump enabled to capture the faulting instruction.",
    ),
    "driver_timeout": (
        "Driver / Firmware",
        "Driver",
        "high",
        "Inspect peripheral clock/regulator state and confirm firmware was loaded; check IRQ counters.",
    ),
    "thermal_throttling": (
        "Performance / Thermal",
        "Thermal / Power",
        "medium",
        "Plot tz0 temperature vs. workload, verify thermal policy thresholds match HW thermal design.",
    ),
    "firmware_load_failure": (
        "Driver / Firmware",
        "Driver",
        "high",
        "Verify firmware path on /vendor/firmware and that the build manifest includes the binary.",
    ),
    "io_error": (
        "Storage / Bus",
        "Driver",
        "medium",
        "Capture SMART / eMMC health and inspect bus error counters around the failure window.",
    ),
}


def _verdict_from_signature(sig: str, rationale: str) -> TriageVerdict:
    cat, owner, sev, step = _SIGNATURE_RULES.get(
        sig,
        (
            "Unclassified",
            "Triage",
            "low",
            "Collect full logs and metrics; escalate to the on-call validation engineer.",
        ),
    )
    return TriageVerdict(
        category=cat,
        owner=owner,
        severity=sev,
        signature=sig,
        rationale=rationale,
        next_step=step,
    )


def triage_log_events(events: list[LogEvent]) -> TriageVerdict | None:
    """Pick the most severe signature among events as the dominant verdict."""
    if not events:
        return None
    severity_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    best: TriageVerdict | None = None
    for ev in events:
        v = _verdict_from_signature(
            ev.signature, f"{ev.subsystem}: {ev.message}".strip(": ")
        )
        if best is None or severity_rank[v.severity] > severity_rank[best.severity]:
            best = v
    return best


def triage_threshold_breach(
    metric: str, stat: str, observed: float, threshold: float
) -> TriageVerdict:
    """Map a numeric pass-criterion breach to a verdict."""
    if "latency" in metric:
        return TriageVerdict(
            category="Performance Regression",
            owner="Performance / Runtime",
            severity="high",
            signature=f"latency_breach:{stat}",
            rationale=f"{metric} {stat} was {observed:.2f} against {threshold:.2f} threshold.",
            next_step=(
                "Compare runtime logs against the previous passing run and inspect "
                "CPU/GPU frequency traces during the regression window."
            ),
        )
    if "power" in metric:
        return TriageVerdict(
            category="Power Regression",
            owner="Thermal / Power",
            severity="high",
            signature=f"power_breach:{stat}",
            rationale=f"{metric} {stat} was {observed:.2f} mW against {threshold:.2f} mW threshold.",
            next_step=(
                "Profile idle residency states and check for wakelocks, suspect "
                "wireless or display driver wakeups."
            ),
        )
    if "boot" in metric:
        return TriageVerdict(
            category="Boot Regression",
            owner="Kernel / Platform",
            severity="high",
            signature=f"boot_breach:{stat}",
            rationale=f"{metric} was {observed:.2f}s against {threshold:.2f}s threshold.",
            next_step=(
                "Compare bootchart and dmesg timestamps with the last passing baseline "
                "to localize the slowdown to a service or driver init."
            ),
        )
    if "temperature" in metric:
        return TriageVerdict(
            category="Thermal",
            owner="Thermal / Power",
            severity="medium",
            signature=f"temp_breach:{stat}",
            rationale=f"{metric} {stat} was {observed:.2f}C against {threshold:.2f}C threshold.",
            next_step="Inspect thermal zones and active cooling state during the workload window.",
        )
    return TriageVerdict(
        category="Threshold Breach",
        owner="Triage",
        severity="medium",
        signature=f"threshold_breach:{metric}:{stat}",
        rationale=f"{metric} {stat} was {observed:.2f} against {threshold:.2f} threshold.",
        next_step="Investigate the offending subsystem and compare against the prior passing run.",
    )


def triage_flaky(test_id: str) -> TriageVerdict:
    return TriageVerdict(
        category="Flaky",
        owner="Test Owner",
        severity="medium",
        signature="flaky",
        rationale=f"{test_id} mixed pass/fail across iterations in this run.",
        next_step=(
            "Stabilize the test fixture (timing, environment, simulator state) or "
            "quarantine the test pending root-cause."
        ),
    )
