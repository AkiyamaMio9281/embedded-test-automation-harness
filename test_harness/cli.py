"""Typer-based command-line interface for the harness.

Verbs:
  run         execute a YAML test plan against a device
  parse-logs  parse a directory of logcat/dmesg files
  summarize   print a saved run's pass/fail breakdown
  compare     compare baseline vs candidate run manifests
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .config import OUTPUTS_DIR
from .executor import execute_plan
from .log_parser import parse_directory
from .report import write_reports
from .simulated_device import SimulatedDevice
from .test_plan import load_plan

app = typer.Typer(help="Embedded test automation harness CLI.")
console = Console()


def _device_factory(name: str):
    if name == "simulated":
        return SimulatedDevice()
    if name.startswith("adb:"):
        from .adb_device import AdbDevice

        return AdbDevice(serial=name.split(":", 1)[1])
    if name.startswith("ssh:"):
        from .ssh_device import SshDevice

        host = name.split(":", 1)[1]
        return SshDevice(host=host)
    raise typer.BadParameter(
        f"unknown device '{name}'. Try 'simulated', 'adb:<serial>', 'ssh:<host>'."
    )


@app.command()
def run(
    plan: Path = typer.Option(..., exists=True, help="Path to YAML test plan."),
    device: str = typer.Option("simulated", help="Device backend identifier."),
    output: Path = typer.Option(
        None, help="Output directory for this run (defaults to outputs/runs/<run_id>)."
    ),
    run_id: str = typer.Option(None, help="Optional explicit run id."),
) -> None:
    """Execute a test plan end-to-end and write report artifacts."""
    test_plan = load_plan(plan)
    backend = _device_factory(device)

    if output is None:
        rid = run_id or f"run_{Path(plan).stem}_{int(__import__('time').time())}"
        output = OUTPUTS_DIR / "runs" / rid

    console.print(
        f"[bold]Running plan[/bold] [cyan]{test_plan.name}[/cyan] "
        f"({len(test_plan.tests)} tests x {test_plan.iterations} iterations) "
        f"on [magenta]{backend.name}[/magenta]"
    )

    report = execute_plan(test_plan, backend, output, run_id=run_id)
    md_path, html_path = write_reports(report)

    table = Table(title=f"Run {report.run_id} summary", show_lines=False)
    table.add_column("Test")
    table.add_column("Iter")
    table.add_column("Status")
    table.add_column("Triage")
    table.add_column("Failure reason")
    for it in report.iterations:
        style = "green" if it.status == "pass" else "red"
        table.add_row(
            it.test_id,
            str(it.iteration),
            f"[{style}]{it.status}[/{style}]",
            it.triage.category if it.triage else "",
            it.failure_reason,
        )
    console.print(table)
    console.print(
        f"[bold]Pass / Fail:[/bold] {report.pass_count}/{report.fail_count}  "
        f"[bold]Flaky:[/bold] {', '.join(report.flaky_test_ids) or 'none'}"
    )
    console.print(f"[dim]Markdown:[/dim] {md_path}")
    console.print(f"[dim]HTML:[/dim]     {html_path}")


@app.command("parse-logs")
def parse_logs(
    input: Path = typer.Option(..., exists=True, help="Directory of logcat/dmesg files."),
    output: Path = typer.Option(
        None, help="Optional CSV path to write parsed events."
    ),
) -> None:
    """Parse a directory of logcat/dmesg into structured events."""
    events = parse_directory(input)
    console.print(f"Parsed [bold]{len(events)}[/bold] events from {input}")
    counter: Counter[str] = Counter(e.signature for e in events)
    table = Table(title="Signature counts")
    table.add_column("Signature")
    table.add_column("Count", justify="right")
    for sig, count in counter.most_common():
        table.add_row(sig, str(count))
    console.print(table)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(
                ["source", "timestamp", "severity", "subsystem", "signature", "message"]
            )
            for e in events:
                w.writerow(
                    [e.source, e.timestamp, e.severity, e.subsystem, e.signature, e.message]
                )
        console.print(f"[dim]Wrote events CSV: {output}[/dim]")


@app.command()
def summarize(
    run: Path = typer.Option(..., exists=True, help="Path to a run directory."),
) -> None:
    """Print a saved run's manifest and pass/fail breakdown."""
    manifest_path = run / "manifest.json"
    if not manifest_path.exists():
        raise typer.BadParameter(f"manifest.json missing in {run}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    console.print(f"[bold]Run:[/bold] {manifest['run_id']} ({manifest['plan_name']})")
    console.print(f"Device: {manifest['device']}")
    console.print(f"Pass/Fail: {manifest['pass_count']}/{manifest['fail_count']}")
    console.print(f"Flaky:    {', '.join(manifest.get('flaky_test_ids', [])) or 'none'}")

    results_path = run / "results.csv"
    if results_path.exists():
        table = Table(title="Results", show_lines=False)
        for col in ["test_id", "iteration", "status", "duration_sec",
                    "triage_category", "failure_reason"]:
            table.add_column(col)
        with results_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                style = "green" if row["status"] == "pass" else "red"
                table.add_row(
                    row["test_id"],
                    row["iteration"],
                    f"[{style}]{row['status']}[/{style}]",
                    row["duration_sec"],
                    row.get("triage_category", ""),
                    row.get("failure_reason", ""),
                )
        console.print(table)


@app.command()
def compare(
    baseline: Path = typer.Option(..., exists=True, help="Baseline run directory."),
    candidate: Path = typer.Option(..., exists=True, help="Candidate run directory."),
) -> None:
    """Compare a candidate run against a baseline."""
    base_manifest = json.loads((baseline / "manifest.json").read_text(encoding="utf-8"))
    cand_manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))

    console.print(
        f"[bold]Baseline:[/bold] {base_manifest['run_id']} — "
        f"{base_manifest['pass_count']}/{base_manifest['fail_count']}"
    )
    console.print(
        f"[bold]Candidate:[/bold] {cand_manifest['run_id']} — "
        f"{cand_manifest['pass_count']}/{cand_manifest['fail_count']}"
    )

    base_results = _load_results(baseline)
    cand_results = _load_results(candidate)

    changes = []
    keys = sorted(set(base_results) | set(cand_results))
    for key in keys:
        b = base_results.get(key)
        c = cand_results.get(key)
        if b is None:
            changes.append((key, "—", c["status"], "added in candidate"))
            continue
        if c is None:
            changes.append((key, b["status"], "—", "removed in candidate"))
            continue
        if b["status"] != c["status"]:
            changes.append((key, b["status"], c["status"], "status changed"))

    if not changes:
        console.print("[green]No status changes between baseline and candidate.[/green]")
        return

    table = Table(title="Status changes")
    table.add_column("Test / iter")
    table.add_column("Baseline")
    table.add_column("Candidate")
    table.add_column("Delta")
    for key, b, c, delta in changes:
        table.add_row(key, b, c, delta)
    console.print(table)


def _load_results(run_dir: Path) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    p = run_dir / "results.csv"
    if not p.exists():
        return out
    with p.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = f"{row['test_id']}#iter{row['iteration']}"
            out[key] = row
    return out


if __name__ == "__main__":
    app()
