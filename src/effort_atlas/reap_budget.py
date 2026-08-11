"""Exact worst-case budget arithmetic for planned REAP rows."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

MILLION = Decimal(1_000_000)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
RESERVED_SCOPE_IDS = frozenset(
    {"unscoped", "tbd", "pending", "unknown", "[__]", "__", "[decide]"}
)


class BudgetCeilingExceeded(ValueError):
    """Raised when a worst-case projection is above its hard ceiling."""


def _nonempty_string(label: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _scope_id(label: str, value: object) -> str:
    scope_id = _nonempty_string(label, value)
    if scope_id.strip().casefold() in RESERVED_SCOPE_IDS:
        raise ValueError(f"{label} must be an explicit non-placeholder scope identifier")
    return scope_id


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
    pool_id: str
    panel_id: str

    def __post_init__(self) -> None:
        _nonempty_string("job_id", self.job_id)
        _nonempty_string("route_id", self.route_id)
        _nonempty_string("phase", self.phase)
        _token_bound("prompt_token_bound", self.prompt_token_bound, positive=False)
        _token_bound("max_output_tokens", self.max_output_tokens, positive=True)
        _scope_id("pool_id", self.pool_id)
        _scope_id("panel_id", self.panel_id)


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
    snapshot_sha256: str
    by_pool_usd: tuple[tuple[str, Decimal], ...]
    by_pool_panel_usd: tuple[tuple[str, str, Decimal], ...]
    price_basis: str


def project_maximum_exposure(
    rows: Iterable[BudgetRow], rates: Iterable[RouteRate], *, price_basis: str = "list"
) -> BudgetProjection:
    """Sum prompt bounds and explicit output caps using list rates by default."""

    if price_basis not in {"list", "discount"}:
        raise ValueError("price_basis must be list or discount")

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

    snapshot_digests: set[str] = set()
    rates_by_route: dict[tuple[str, str], RouteRate] = {}
    for rate in materialized_rates:
        if not isinstance(rate, RouteRate):
            raise TypeError("every rate must be a RouteRate")
        rate_key = (rate.route_id, rate.basis)
        if rate_key in rates_by_route:
            raise ValueError(
                f"Duplicate route_id and basis: {rate.route_id}/{rate.basis}"
            )
        rates_by_route[rate_key] = rate
        snapshot_digests.add(rate.snapshot_sha256)
    if len(snapshot_digests) > 1:
        raise ValueError(
            "All route rates in a projection must share one snapshot_sha256"
        )

    by_phase: defaultdict[str, Decimal] = defaultdict(Decimal)
    by_basis: defaultdict[str, Decimal] = defaultdict(Decimal)
    by_pool: defaultdict[str, Decimal] = defaultdict(Decimal)
    by_pool_panel: defaultdict[tuple[str, str], Decimal] = defaultdict(Decimal)
    total = Decimal(0)
    for row in materialized_rows:
        rate = rates_by_route.get((row.route_id, price_basis))
        if rate is None:
            raise ValueError(
                f"Planned row {row.job_id} has no price for {row.route_id} at {price_basis} basis"
            )
        exposure = (
            Decimal(row.prompt_token_bound) * rate.input_usd_per_million
            + Decimal(row.max_output_tokens) * rate.output_usd_per_million
        ) / MILLION
        total += exposure
        by_phase[row.phase] += exposure
        by_basis[rate.basis] += exposure
        by_pool[row.pool_id] += exposure
        by_pool_panel[(row.pool_id, row.panel_id)] += exposure

    return BudgetProjection(
        maximum_exposure_usd=total,
        row_count=len(materialized_rows),
        by_phase_usd=tuple(sorted(by_phase.items())),
        by_price_basis_usd=tuple(sorted(by_basis.items())),
        snapshot_sha256=next(iter(snapshot_digests)),
        by_pool_usd=tuple(sorted(by_pool.items())),
        by_pool_panel_usd=tuple(
            (pool_id, panel_id, exposure)
            for (pool_id, panel_id), exposure in sorted(by_pool_panel.items())
        ),
        price_basis=price_basis,
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


def enforce_freeze_budget_gate(
    projection: BudgetProjection,
    *,
    pool_ceilings_usd: dict[str, Decimal],
    panel_ceilings_usd: dict[tuple[str, str], Decimal],
    receipt_checked_discount_policy: bool = False,
) -> BudgetProjection:
    """Fail closed unless frozen pool and panel ceilings cover list-rate exposure.

    A discount projection is admissible only when a separately frozen policy commits
    to receipt checks.  This flag records that policy; it does not verify receipts.
    """
    if not isinstance(projection, BudgetProjection):
        raise TypeError("projection must be a BudgetProjection")
    if projection.price_basis == "discount" and not receipt_checked_discount_policy:
        raise BudgetCeilingExceeded(
            "discount-only projection cannot satisfy a freeze gate without a receipt-checked discount policy"
        )
    if projection.price_basis != "list" and projection.price_basis != "discount":
        raise BudgetCeilingExceeded("freeze projection has an unrecognized price basis")
    _require_ceiling_map(pool_ceilings_usd, label="pool")
    _require_ceiling_map(panel_ceilings_usd, label="panel")
    for pool_id, exposure in projection.by_pool_usd:
        _scope_id("projection pool_id", pool_id)
        ceiling = pool_ceilings_usd.get(pool_id)
        if ceiling is None:
            raise BudgetCeilingExceeded(f"pool ceiling is missing for {pool_id}")
        if exposure > ceiling:
            raise BudgetCeilingExceeded(
                f"pool {pool_id} maximum exposure {exposure} exceeds hard ceiling {ceiling}"
            )
    for pool_id, panel_id, exposure in projection.by_pool_panel_usd:
        _scope_id("projection panel pool_id", pool_id)
        _scope_id("projection panel_id", panel_id)
        ceiling = panel_ceilings_usd.get((pool_id, panel_id))
        if ceiling is None:
            raise BudgetCeilingExceeded(
                f"panel ceiling is missing for {pool_id}/{panel_id}"
            )
        if exposure > ceiling:
            raise BudgetCeilingExceeded(
                f"panel {pool_id}/{panel_id} maximum exposure {exposure} exceeds hard ceiling {ceiling}"
            )
    return projection


def _require_ceiling_map(values: dict[object, object], *, label: str) -> None:
    if not isinstance(values, dict):
        raise TypeError(f"{label}_ceilings_usd must be a dictionary")
    for key, ceiling in values.items():
        if label == "pool":
            _scope_id("pool ceiling key", key)
        else:
            if not isinstance(key, tuple) or len(key) != 2:
                raise ValueError(
                    "panel ceiling keys must be (pool_id, panel_id) tuples"
                )
            _scope_id("panel pool_id", key[0])
            _scope_id("panel panel_id", key[1])
        _rate(f"{label} ceiling", ceiling)
