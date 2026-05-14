"""YAML test plan loader tests."""

from __future__ import annotations

import textwrap

import pytest

from test_harness.config import PROJECT_ROOT
from test_harness.test_plan import load_plan


def _write_plan(tmp_path, body: str):
    p = tmp_path / "plan.yaml"
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


def test_load_real_smoke_plan():
    plan = load_plan(PROJECT_ROOT / "test_plans" / "smoke.yaml")
    assert plan.name == "chipset_smoke"
    assert plan.iterations >= 1
    ids = {t.id for t in plan.tests}
    assert {"BOOT-001", "POWER-001", "AI-001"} <= ids


def test_duplicate_ids_raise(tmp_path):
    path = _write_plan(
        tmp_path,
        """
        name: p
        device: simulated_android
        iterations: 1
        tests:
          - id: X
            name: a
            category: boot
            command: c
          - id: X
            name: b
            category: boot
            command: c
        """,
    )
    with pytest.raises(Exception):
        load_plan(path)


def test_invalid_category_rejected(tmp_path):
    path = _write_plan(
        tmp_path,
        """
        name: p
        device: simulated_android
        iterations: 1
        tests:
          - id: X
            name: a
            category: not_a_real_category
            command: c
        """,
    )
    with pytest.raises(Exception):
        load_plan(path)


def test_zero_iterations_rejected(tmp_path):
    path = _write_plan(
        tmp_path,
        """
        name: p
        device: simulated_android
        iterations: 0
        tests:
          - id: X
            name: a
            category: boot
            command: c
        """,
    )
    with pytest.raises(Exception):
        load_plan(path)
