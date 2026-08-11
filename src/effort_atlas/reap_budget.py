"""Exact worst-case budget arithmetic for planned REAP rows."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

MILLION = Decimal(1_000_000)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class BudgetCeilingExceeded(ValueError):
    """Raised when a worst-case projection is above its hard ceiling."""


def _nonempty_string(label: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _token_bound(label: str, value: object, *, positive: bool) -> int:
    minimum = 1 if positive else 0
    if type(value) is not int or value < minimum:
        qualifier = "positive" if positive else "nonnegative"
        raise ValueError(f"{label} must be a {qualifier} integer")
    return value


def _rate(label: str, value: object) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError(f"{label} must be a finite nonnegative Decimal")
    return value


@dataclass(frozen=True, slots=True)
class BudgetRow:
    job_id: str
    route_id: str
    phase: str
    prompt_token_bound: int
    max_output_tokens: int

    def __post_init__(self) -> None:
        _nonempty_string("job_id", self.job_id)
        _nonempty_string("route_id", self.route_id)
        _nonempty_string("phase", self.phase)
        _token_bound("prompt_token_bound", self.prompt_token_bound, positive=False)
        _token_bound("max_output_tokens", self.max_output_tokens, positive=True)


@dataclass(frozen=True, slots=True)
class RouteRate:
    route_id: str
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    snapshot_sha256: str
    basis: str

    def __post_init__(self) -> None:
        _nonempty_string("route_id", self.route_id)
        _rate("input_usd_per_million", self.input_usd_per_million)
        _rate("output_usd_per_million", self.output_usd_per_million)
        if (
            not isinstance(self.snapshot_sha256, str)
            or SHA256_PATTERN.fullmatch(self.snapshot_sha256) is None
        ):
            raise ValueError("snapshot_sha256 must be a lowercase SHA-256 digest")
        if self.basis not in {"list", "discount"}:
            raise ValueError("basis must be list or discount")


@dataclass(frozen=True, slots=True)
class BudgetProjection:
    maximum_exposure_usd: Decimal
    row_count: int
    by_phase_usd: tuple[tuple[str, Decimal], ...]
    by_price_basis_usd: tuple[tuple[str, Decimal], ...]


def project_maximum_exposure(
    rows: Iterable[BudgetRow], rates: Iterable[RouteRate]
) -> BudgetProjection:
    """Sum prompt bounds and explicit output caps for every planned row."""

    materialized_rows = tuple(rows)
    materialized_rates = tuple(rates)
    if not materialized_rows:
        raise ValueError("budget projection requires at least one planned row")

    job_ids: set[str] = set()
    for row in materialized_rows:
        if not isinstance(row, BudgetRow):
            raise TypeError("every planned row must be a BudgetRow")
        if row.job_id in job_ids:
            raise ValueError(f"Duplicate job_id: {row.job_id}")
        job_ids.add(row.job_id)

    rates_by_route: dict[str, RouteRate] = {}
    for rate in materialized_rates:
        if not isinstance(rate, RouteRate):
            raise TypeError("every rate must be a RouteRate")
        if rate.route_id in rates_by_route:
            raise ValueError(f"Duplicate route_id: {rate.route_id}")
        rates_by_route[rate.route_id] = rate

    by_phase: defaultdict[str, Decimal] = defaultdict(Decimal)
    by_basis: defaultdict[str, Decimal] = defaultdict(Decimal)
    total = Decimal(0)
    for row in materialized_rows:
        rate = rates_by_route.get(row.route_id)
        if rate is None:
            raise ValueError(
                f"Planned row {row.job_id} has no price for {row.route_id}"
            )
        exposure = (
            Decimal(row.prompt_token_bound) * rate.input_usd_per_million
            + Decimal(row.max_output_tokens) * rate.output_usd_per_million
        ) / MILLION
        total += exposure
        by_phase[row.phase] += exposure
        by_basis[rate.basis] += exposure

    return BudgetProjection(
        maximum_exposure_usd=total,
        row_count=len(materialized_rows),
        by_phase_usd=tuple(sorted(by_phase.items())),
        by_price_basis_usd=tuple(sorted(by_basis.items())),
    )


def enforce_budget_ceiling(
    projection: BudgetProjection, ceiling_usd: Decimal
) -> BudgetProjection:
    """Return the projection at or below the ceiling; refuse any excess."""

    if (
        not isinstance(ceiling_usd, Decimal)
        or not ceiling_usd.is_finite()
        or ceiling_usd < 0
    ):
        raise ValueError("ceiling_usd must be a finite nonnegative Decimal")
    if projection.maximum_exposure_usd > ceiling_usd:
        raise BudgetCeilingExceeded(
            f"maximum exposure {projection.maximum_exposure_usd} exceeds hard ceiling {ceiling_usd}"
        )
    return projection
