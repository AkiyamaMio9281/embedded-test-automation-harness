"""Metrics ingestion and aggregation.

Accepts either an in-memory list of ``MetricSample`` or a CSV file with
columns ``timestamp,metric,value,unit``. Aggregations are computed per
metric name (mean, min, max, p50, p95, p99).
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from .device import MetricSample


@dataclass
class MetricSummary:
    metric: str
    unit: str
    count: int
    mean: float
    min: float
    max: float
    p50: float
    p95: float
    p99: float


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Linear-interpolation percentile, NumPy-equivalent for our purposes."""
    if not sorted_values:
        return math.nan
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def load_metrics_csv(path: str | Path) -> list[MetricSample]:
    """Load metric samples from a CSV with timestamp,metric,value,unit."""
    out: list[MetricSample] = []
    p = Path(path)
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                value = float(row["value"])
            except (KeyError, ValueError) as e:
                raise ValueError(f"bad metric row in {p}: {row}") from e
            out.append(
                MetricSample(
                    timestamp=row.get("timestamp", ""),
                    metric=row["metric"],
                    value=value,
                    unit=row.get("unit", ""),
                )
            )
    return out


def summarize(samples: list[MetricSample]) -> list[MetricSummary]:
    """Aggregate samples by metric name."""
    by_metric: dict[str, list[MetricSample]] = {}
    for s in samples:
        by_metric.setdefault(s.metric, []).append(s)

    summaries: list[MetricSummary] = []
    for metric, rows in by_metric.items():
        vals = sorted(r.value for r in rows)
        unit = next((r.unit for r in rows if r.unit), "")
        summaries.append(
            MetricSummary(
                metric=metric,
                unit=unit,
                count=len(vals),
                mean=sum(vals) / len(vals),
                min=vals[0],
                max=vals[-1],
                p50=_percentile(vals, 50),
                p95=_percentile(vals, 95),
                p99=_percentile(vals, 99),
            )
        )
    summaries.sort(key=lambda s: s.metric)
    return summaries


def get_value(summaries: list[MetricSummary], metric: str, stat: str) -> float | None:
    """Lookup helper used by the executor when evaluating pass criteria."""
    for s in summaries:
        if s.metric == metric:
            return getattr(s, stat, None)
    return None
