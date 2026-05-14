"""SQLite-backed run history for flaky detection and baseline compare."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    plan_name TEXT NOT NULL,
    device TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS test_results (
    run_id TEXT NOT NULL,
    test_id TEXT NOT NULL,
    iteration INTEGER NOT NULL,
    status TEXT NOT NULL,
    duration_sec REAL NOT NULL,
    failure_reason TEXT,
    triage_category TEXT,
    timestamp TEXT NOT NULL,
    PRIMARY KEY (run_id, test_id, iteration),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS failure_signatures (
    run_id TEXT NOT NULL,
    test_id TEXT NOT NULL,
    iteration INTEGER NOT NULL,
    signature TEXT NOT NULL,
    severity TEXT NOT NULL,
    owner TEXT,
    PRIMARY KEY (run_id, test_id, iteration, signature)
);

CREATE TABLE IF NOT EXISTS metrics_summary (
    run_id TEXT NOT NULL,
    test_id TEXT NOT NULL,
    iteration INTEGER NOT NULL,
    metric TEXT NOT NULL,
    mean REAL,
    p50 REAL,
    p95 REAL,
    p99 REAL,
    min REAL,
    max REAL,
    PRIMARY KEY (run_id, test_id, iteration, metric)
);
"""


@contextmanager
def connect(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_run(conn: sqlite3.Connection, run_id: str, plan_name: str, device: str, started_at: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO runs(run_id, plan_name, device, started_at) VALUES (?,?,?,?)",
        (run_id, plan_name, device, started_at),
    )


def mark_run_finished(conn: sqlite3.Connection, run_id: str, finished_at: str) -> None:
    conn.execute(
        "UPDATE runs SET finished_at = ? WHERE run_id = ?",
        (finished_at, run_id),
    )


def insert_result(
    conn: sqlite3.Connection,
    run_id: str,
    test_id: str,
    iteration: int,
    status: str,
    duration_sec: float,
    failure_reason: str,
    triage_category: str,
    timestamp: str,
) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO test_results
        (run_id, test_id, iteration, status, duration_sec, failure_reason, triage_category, timestamp)
        VALUES (?,?,?,?,?,?,?,?)""",
        (
            run_id,
            test_id,
            iteration,
            status,
            duration_sec,
            failure_reason,
            triage_category,
            timestamp,
        ),
    )


def insert_signature(
    conn: sqlite3.Connection,
    run_id: str,
    test_id: str,
    iteration: int,
    signature: str,
    severity: str,
    owner: str,
) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO failure_signatures
        (run_id, test_id, iteration, signature, severity, owner)
        VALUES (?,?,?,?,?,?)""",
        (run_id, test_id, iteration, signature, severity, owner),
    )


def insert_metric_summary(
    conn: sqlite3.Connection,
    run_id: str,
    test_id: str,
    iteration: int,
    metric: str,
    mean: float,
    p50: float,
    p95: float,
    p99: float,
    min_v: float,
    max_v: float,
) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO metrics_summary
        (run_id, test_id, iteration, metric, mean, p50, p95, p99, min, max)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (run_id, test_id, iteration, metric, mean, p50, p95, p99, min_v, max_v),
    )


def failure_signatures_for_test(conn: sqlite3.Connection, test_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT signature FROM failure_signatures WHERE test_id = ?",
        (test_id,),
    ).fetchall()
    return [r["signature"] for r in rows]


def runs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM runs ORDER BY started_at DESC").fetchall()
