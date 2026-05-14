"""Metrics aggregation tests."""

from __future__ import annotations

from test_harness.device import MetricSample
from test_harness.metrics_parser import (
    _percentile,
    get_value,
    load_metrics_csv,
    summarize,
)
from test_harness.config import SAMPLE_PERF_DIR


def test_percentile_matches_known_value():
    vals = sorted([1.0, 2.0, 3.0, 4.0, 5.0])
    assert _percentile(vals, 50) == 3.0
    # p95 of 5 evenly spaced values is interpolated near the top.
    assert abs(_percentile(vals, 95) - 4.8) < 1e-9


def test_summarize_basic_stats():
    samples = [
        MetricSample("t0", "lat_ms", 10, "ms"),
        MetricSample("t1", "lat_ms", 20, "ms"),
        MetricSample("t2", "lat_ms", 30, "ms"),
    ]
    [s] = summarize(samples)
    assert s.count == 3
    assert s.mean == 20.0
    assert s.min == 10.0
    assert s.max == 30.0
    assert s.p50 == 20.0


def test_get_value_returns_none_for_missing():
    [s] = summarize([MetricSample("t0", "a", 1.0, "")])
    assert get_value([s], "missing", "mean") is None
    assert get_value([s], "a", "mean") == 1.0


def test_load_metrics_csv_round_trip():
    path = SAMPLE_PERF_DIR / "sample_metrics.csv"
    samples = load_metrics_csv(path)
    assert any(s.metric == "power_mw" for s in samples)
    assert any(s.metric == "inference_latency_ms" for s in samples)
    summaries = summarize(samples)
    p95 = get_value(summaries, "inference_latency_ms", "p95")
    assert p95 is not None and p95 >= 49
