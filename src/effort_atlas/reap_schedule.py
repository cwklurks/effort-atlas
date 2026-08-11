"""Decision-independent identity primitives for REAP schedule schema v2.

This module intentionally contains no panel roster, arm vocabulary, cap grid,
effort grid, item set, or replication count.  Those choices belong in later
frozen artifacts.  It also does not import or alter the Phase-I scheduler in
``confirmatory.py``.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TypeAlias

IDENTITY_FIELDS = (
    "phase",
    "panel",
    "model",
    "provider_route",
    "item_id",
    "effort",
    "cap",
    "replicate",
    "arm_key",
    "master_seed",
)
PROVIDER_SEED_MAX = 2**31 - 1

EffortValue: TypeAlias = str | float


def _canonical_json(value: Mapping[str, object]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _require_nonempty_string(field: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string.")
    return value


def _require_positive_integer(field: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field} must be a positive integer, not a boolean.")
    return value


def _require_nonnegative_integer(field: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a nonnegative integer, not a boolean.")
    return value


def _require_effort(value: object) -> EffortValue:
    if isinstance(value, bool):
        raise ValueError(  # noqa: TRY004 - all invalid schema values use ValueError
            "effort must be a nonempty label or a finite number, not a boolean."
        )
    if isinstance(value, str):
        if not value.strip():
            raise ValueError("effort must be a nonempty label or a finite number.")
        return value
    if isinstance(value, (int, float)):
        try:
            normalized = float(value)
        except OverflowError as exc:
            raise ValueError(
                "effort must be a nonempty label or a finite number."
            ) from exc
        if math.isfinite(normalized):
            return normalized
    raise ValueError("effort must be a nonempty label or a finite number.")


@dataclass(frozen=True, slots=True)
class ReapScheduleIdentity:
    """The complete immutable identity of one planned REAP output."""

    phase: str
    panel: str
    model: str
    provider_route: str
    item_id: str
    effort: EffortValue
    cap: int
    replicate: int
    arm_key: str
    master_seed: int

    def __post_init__(self) -> None:
        """Reject invalid identities even when constructed without a mapping."""
        _require_nonempty_string("phase", self.phase)
        _require_nonempty_string("panel", self.panel)
        _require_nonempty_string("model", self.model)
        _require_nonempty_string("provider_route", self.provider_route)
        _require_nonempty_string("item_id", self.item_id)
        object.__setattr__(self, "effort", _require_effort(self.effort))
        _require_positive_integer("cap", self.cap)
        _require_positive_integer("replicate", self.replicate)
        _require_nonempty_string("arm_key", self.arm_key)
        _require_nonnegative_integer("master_seed", self.master_seed)

    @classmethod
    def from_mapping(cls, row: Mapping[str, object]) -> ReapScheduleIdentity:
        """Validate a strict identity mapping, rejecting schema drift."""
        supplied = set(row)
        expected = set(IDENTITY_FIELDS)
        missing = sorted(expected - supplied)
        unknown = sorted(str(field) for field in supplied - expected)
        if missing or unknown:
            details = []
            if missing:
                details.append(f"missing fields: {', '.join(missing)}")
            if unknown:
                details.append(f"unknown fields: {', '.join(unknown)}")
            raise ValueError(
                "Invalid REAP schedule identity; " + "; ".join(details) + "."
            )

        return cls(
            phase=_require_nonempty_string("phase", row["phase"]),
            panel=_require_nonempty_string("panel", row["panel"]),
            model=_require_nonempty_string("model", row["model"]),
            provider_route=_require_nonempty_string(
                "provider_route", row["provider_route"]
            ),
            item_id=_require_nonempty_string("item_id", row["item_id"]),
            effort=_require_effort(row["effort"]),
            cap=_require_positive_integer("cap", row["cap"]),
            replicate=_require_positive_integer("replicate", row["replicate"]),
            arm_key=_require_nonempty_string("arm_key", row["arm_key"]),
            master_seed=_require_nonnegative_integer("master_seed", row["master_seed"]),
        )

    def as_dict(self) -> dict[str, object]:
        """Return all identity fields in the schema's documented order."""
        return {field: getattr(self, field) for field in IDENTITY_FIELDS}

    def canonical_json(self) -> str:
        """Return the stable canonical bytestring source for derived identity."""
        return _canonical_json(self.as_dict())

    @property
    def job_id(self) -> str:
        """Return the SHA-256 job ID for this complete arm-aware identity."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    @property
    def provider_seed(self) -> int:
        """Return a deterministic seed in the portable signed 31-bit range."""
        seed_source = (
            b"reap-schedule-v2-provider-seed\0" + self.canonical_json().encode("utf-8")
        )
        return (
            int.from_bytes(hashlib.sha256(seed_source).digest()[:4], "big")
            & PROVIDER_SEED_MAX
        )


@dataclass(frozen=True, slots=True)
class ReapScheduledJob:
    """A validated identity plus its deterministic request metadata."""

    identity: ReapScheduleIdentity

    @property
    def job_id(self) -> str:
        return self.identity.job_id

    @property
    def provider_seed(self) -> int:
        return self.identity.provider_seed


def build_reap_schedule(
    planned_rows: Iterable[Mapping[str, object]],
) -> tuple[ReapScheduledJob, ...]:
    """Validate, deduplicate, and canonically order planned REAP rows."""
    identities = [ReapScheduleIdentity.from_mapping(row) for row in planned_rows]
    by_canonical_json: dict[str, ReapScheduleIdentity] = {}
    for identity in identities:
        canonical = identity.canonical_json()
        if canonical in by_canonical_json:
            raise ValueError(f"Duplicate canonical identity: {canonical}")
        by_canonical_json[canonical] = identity

    canonical_by_provider_seed: dict[int, str] = {}
    for canonical, identity in by_canonical_json.items():
        existing = canonical_by_provider_seed.get(identity.provider_seed)
        if existing is not None:
            raise ValueError(
                "provider seed collision between distinct canonical identities: "
                f"{existing} and {canonical}"
            )
        canonical_by_provider_seed[identity.provider_seed] = canonical

    return tuple(
        ReapScheduledJob(by_canonical_json[canonical])
        for canonical in sorted(by_canonical_json)
    )
