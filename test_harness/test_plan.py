"""YAML test plan loader and pydantic models.

Plans are validated strictly: bad configs fail fast instead of being
silently coerced. Pass criteria live in the plan, not in execution code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from .config import VALID_CATEGORIES


class PassCriteria(BaseModel):
    """Threshold-style pass criteria.

    All fields are optional — a test only declares the criteria that apply
    to it. Unknown keys are rejected so typos in YAML fail loudly.
    """

    model_config = {"extra": "forbid"}

    max_boot_time_sec: float | None = None
    max_avg_power_mw: float | None = None
    max_peak_power_mw: float | None = None
    max_p50_latency_ms: float | None = None
    max_p95_latency_ms: float | None = None
    max_p99_latency_ms: float | None = None
    max_temperature_c: float | None = None
    min_throughput_fps: float | None = None
    forbidden_log_patterns: list[str] = Field(default_factory=list)
    required_log_patterns: list[str] = Field(default_factory=list)


class TestCase(BaseModel):
    """One row in a YAML test plan."""

    model_config = {"extra": "forbid"}

    id: str
    name: str
    category: str
    command: str
    timeout_sec: float = 60.0
    pass_criteria: PassCriteria = Field(default_factory=PassCriteria)

    @field_validator("category")
    @classmethod
    def _normalize_category(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_CATEGORIES:
            raise ValueError(
                f"category '{v}' is not one of {sorted(VALID_CATEGORIES)}"
            )
        return v

    @field_validator("id", "name", "command")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be a non-empty string")
        return v.strip()


class TestPlan(BaseModel):
    """Top-level YAML test plan."""

    model_config = {"extra": "forbid"}

    name: str
    device: str
    iterations: int = 1
    tests: list[TestCase]

    @field_validator("iterations")
    @classmethod
    def _positive_iterations(cls, v: int) -> int:
        if v < 1:
            raise ValueError("iterations must be >= 1")
        return v

    @model_validator(mode="after")
    def _unique_ids(self) -> "TestPlan":
        ids = [t.id for t in self.tests]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate test ids in plan: {dupes}")
        if not self.tests:
            raise ValueError("plan must contain at least one test")
        return self


def load_plan(path: str | Path) -> TestPlan:
    """Load and validate a YAML test plan from disk."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"test plan not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        raw: Any = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"test plan {p} did not parse as a mapping")
    return TestPlan(**raw)
