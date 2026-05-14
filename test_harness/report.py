"""Markdown + HTML report generation for a single run."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from jinja2 import Environment, BaseLoader, select_autoescape

from .executor import RunReport


_MD_TEMPLATE = """# Run Report — {{ report.plan_name }}

- **Run ID:** {{ report.run_id }}
- **Device:** {{ report.device }}
- **Started:** {{ report.started_at }}
- **Finished:** {{ report.finished_at }}
- **Pass / Fail:** {{ report.pass_count }} / {{ report.fail_count }}
- **Flaky tests:** {% if report.flaky_test_ids %}{{ report.flaky_test_ids | join(", ") }}{% else %}none{% endif %}

## Pass / Fail Table

| Test ID | Iteration | Status | Duration (s) | Failure | Triage |
|---|---|---|---|---|---|
{% for it in report.iterations -%}
| {{ it.test_id }} | {{ it.iteration }} | {{ it.status }} | {{ "%.3f"|format(it.duration_sec) }} | {{ it.failure_reason or "" }} | {{ it.triage.category if it.triage else "" }} |
{% endfor %}

## Failure Triage

{% set any_failed = false -%}
{% for it in report.iterations if it.status != "pass" -%}
{% set any_failed = true -%}
### {{ it.test_id }} (iteration {{ it.iteration }})

- **Reason:** {{ it.failure_reason }}
{% if it.triage -%}
- **Category:** {{ it.triage.category }}
- **Owner:** {{ it.triage.owner }}
- **Severity:** {{ it.triage.severity }}
- **Signature:** `{{ it.triage.signature }}`
- **Next step:** {{ it.triage.next_step }}
- **Rationale:** {{ it.triage.rationale }}
{%- endif %}

{% endfor -%}
{% if report.fail_count == 0 %}No failures in this run.{% endif %}

## Top Log Signatures

{% if top_signatures -%}
| Signature | Count |
|---|---|
{% for sig, count in top_signatures -%}
| `{{ sig }}` | {{ count }} |
{% endfor %}
{% else %}No notable log signatures detected.
{% endif %}

## Metric Summaries

| Test ID | Iteration | Metric | Mean | p50 | p95 | p99 | Min | Max |
|---|---|---|---|---|---|---|---|---|
{% for it in report.iterations -%}
{% for ms in it.metric_summaries -%}
| {{ it.test_id }} | {{ it.iteration }} | {{ ms.metric }} | {{ "%.2f"|format(ms.mean) }} | {{ "%.2f"|format(ms.p50) }} | {{ "%.2f"|format(ms.p95) }} | {{ "%.2f"|format(ms.p99) }} | {{ "%.2f"|format(ms.min) }} | {{ "%.2f"|format(ms.max) }} |
{% endfor -%}
{% endfor %}

## Recommended Next Steps

{% for it in report.iterations if it.status != "pass" and it.triage -%}
- **{{ it.test_id }}** ({{ it.triage.category }}): {{ it.triage.next_step }}
{% endfor -%}
{% if report.fail_count == 0 %}All tests passed — nothing to investigate.{% endif %}
"""


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{{ report.plan_name }} — {{ report.run_id }}</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 980px; margin: 32px auto; padding: 0 16px; color: #1f2328; }
  h1, h2, h3 { line-height: 1.2; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0 24px; font-size: 14px; }
  th, td { padding: 6px 10px; border: 1px solid #d0d7de; text-align: left; }
  th { background: #f6f8fa; }
  tr.pass td { background: #f0fff4; }
  tr.fail td { background: #fff5f5; }
  code { background: #f6f8fa; padding: 1px 4px; border-radius: 3px; }
  .meta { background: #f6f8fa; padding: 12px 16px; border-radius: 6px; }
  .sev-critical { color: #b91c1c; font-weight: 700; }
  .sev-high { color: #c2410c; font-weight: 600; }
  .sev-medium { color: #92400e; }
  .sev-low { color: #1f6feb; }
</style>
</head>
<body>
<h1>{{ report.plan_name }}</h1>
<div class="meta">
  <div><strong>Run ID:</strong> {{ report.run_id }}</div>
  <div><strong>Device:</strong> {{ report.device }}</div>
  <div><strong>Started:</strong> {{ report.started_at }}</div>
  <div><strong>Finished:</strong> {{ report.finished_at }}</div>
  <div><strong>Pass / Fail:</strong> {{ report.pass_count }} / {{ report.fail_count }}</div>
  <div><strong>Flaky tests:</strong> {% if report.flaky_test_ids %}{{ report.flaky_test_ids | join(", ") }}{% else %}none{% endif %}</div>
</div>

<h2>Pass / Fail Table</h2>
<table>
  <thead><tr>
    <th>Test ID</th><th>Iteration</th><th>Status</th><th>Duration (s)</th>
    <th>Failure</th><th>Triage</th>
  </tr></thead>
  <tbody>
  {% for it in report.iterations %}
    <tr class="{{ it.status }}">
      <td>{{ it.test_id }}</td>
      <td>{{ it.iteration }}</td>
      <td>{{ it.status }}</td>
      <td>{{ "%.3f"|format(it.duration_sec) }}</td>
      <td>{{ it.failure_reason or "" }}</td>
      <td>{{ it.triage.category if it.triage else "" }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>

<h2>Failure Triage</h2>
{% if report.fail_count == 0 %}
<p>No failures in this run.</p>
{% else %}
{% for it in report.iterations if it.status != "pass" %}
<h3>{{ it.test_id }} (iteration {{ it.iteration }})</h3>
<ul>
  <li><strong>Reason:</strong> {{ it.failure_reason }}</li>
  {% if it.triage %}
  <li><strong>Category:</strong> {{ it.triage.category }}</li>
  <li><strong>Owner:</strong> {{ it.triage.owner }}</li>
  <li><strong>Severity:</strong> <span class="sev-{{ it.triage.severity }}">{{ it.triage.severity }}</span></li>
  <li><strong>Signature:</strong> <code>{{ it.triage.signature }}</code></li>
  <li><strong>Next step:</strong> {{ it.triage.next_step }}</li>
  <li><strong>Rationale:</strong> {{ it.triage.rationale }}</li>
  {% endif %}
</ul>
{% endfor %}
{% endif %}

<h2>Top Log Signatures</h2>
{% if top_signatures %}
<table>
  <thead><tr><th>Signature</th><th>Count</th></tr></thead>
  <tbody>
  {% for sig, count in top_signatures %}
    <tr><td><code>{{ sig }}</code></td><td>{{ count }}</td></tr>
  {% endfor %}
  </tbody>
</table>
{% else %}<p>No notable log signatures detected.</p>{% endif %}

<h2>Metric Summaries</h2>
<table>
  <thead><tr>
    <th>Test ID</th><th>Iteration</th><th>Metric</th>
    <th>Mean</th><th>p50</th><th>p95</th><th>p99</th><th>Min</th><th>Max</th>
  </tr></thead>
  <tbody>
  {% for it in report.iterations %}{% for ms in it.metric_summaries %}
    <tr>
      <td>{{ it.test_id }}</td>
      <td>{{ it.iteration }}</td>
      <td>{{ ms.metric }}</td>
      <td>{{ "%.2f"|format(ms.mean) }}</td>
      <td>{{ "%.2f"|format(ms.p50) }}</td>
      <td>{{ "%.2f"|format(ms.p95) }}</td>
      <td>{{ "%.2f"|format(ms.p99) }}</td>
      <td>{{ "%.2f"|format(ms.min) }}</td>
      <td>{{ "%.2f"|format(ms.max) }}</td>
    </tr>
  {% endfor %}{% endfor %}
  </tbody>
</table>
</body>
</html>
"""


def _top_signatures(report: RunReport, n: int = 10) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for it in report.iterations:
        for ev in it.events:
            counter[ev.signature] += 1
    return counter.most_common(n)


def write_reports(report: RunReport) -> tuple[Path, Path]:
    """Write report.md and report.html into the run's output dir."""
    md_env = Environment(
        loader=BaseLoader(),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    html_env = Environment(
        loader=BaseLoader(),
        autoescape=select_autoescape(default_for_string=True, default=True),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    md_template = md_env.from_string(_MD_TEMPLATE)
    html_template = html_env.from_string(_HTML_TEMPLATE)

    ctx = {"report": report, "top_signatures": _top_signatures(report)}
    md_path = report.output_dir / "report.md"
    html_path = report.output_dir / "report.html"
    md_path.write_text(md_template.render(**ctx), encoding="utf-8")
    html_path.write_text(html_template.render(**ctx), encoding="utf-8")
    return md_path, html_path
