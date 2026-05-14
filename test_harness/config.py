"""Project paths and constants."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_LOGS_DIR = PROJECT_ROOT / "sample_logs"
SAMPLE_LOGCAT_DIR = SAMPLE_LOGS_DIR / "android_logcat"
SAMPLE_DMESG_DIR = SAMPLE_LOGS_DIR / "linux_dmesg"
SAMPLE_PERF_DIR = SAMPLE_LOGS_DIR / "perf"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
RUNS_DIR = OUTPUTS_DIR / "runs"
REPORTS_DIR = OUTPUTS_DIR / "reports"
HISTORY_DB = OUTPUTS_DIR / "history.sqlite"

VALID_CATEGORIES = {
    "boot",
    "power",
    "camera",
    "connectivity",
    "ai_inference",
    "thermal",
    "stability",
}
