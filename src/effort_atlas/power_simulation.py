"""Offline provenance records for deterministic simulation scenarios.

This module deliberately does not provide a power model.  Callers supply a fully
declared deterministic simulator and its assumptions; this module validates and
hashes the inputs and JSON-safe output so a later reviewer can reproduce that
specific scenario without treating it as an approved design choice.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Mapping
from typing import Any

PROVENANCE_VERSION = 1
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_PLACEHOLDER_VALUES = frozenset({"", "tbd", "pending", "unknown", "[__]", "__"})


class SimulationProvenanceError(ValueError):
    """Raised when a simulation record cannot be independently reproduced."""


def canonical_json(value: object) -> str:
    """Encode JSON deterministically after rejecting non-finite numeric values."""
    _validate_json_value(value, path="value")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def run_deterministic_simulation(
    simulator: Callable[..., Mapping[str, Any]],
    *,
    scenario_parameters: Mapping[str, Any],
    assumptions: Mapping[str, Any],
    seed: int,
    monte_carlo_counts: Mapping[str, int],
    simulator_identifier: str,
    simulator_version: str,
    simulator_source_sha256: str,
) -> dict[str, Any]:
    """Run a supplied simulator and return its output plus reproducibility record.

    The callable receives only the declared scenario, seed, and Monte Carlo counts.
    It must be deterministic for those inputs; this function records rather than
    attempts to infer, validate, or endorse any scientific assumptions.
    """
    _validate_nonempty_mapping(scenario_parameters, name="scenario_parameters")
    _validate_nonempty_mapping(assumptions, name="assumptions")
    _validate_seed(seed)
    _validate_monte_carlo_counts(monte_carlo_counts)
    _validate_metadata(
        simulator_identifier=simulator_identifier,
        simulator_version=simulator_version,
        simulator_source_sha256=simulator_source_sha256,
    )

    output = simulator(
        scenario_parameters=dict(scenario_parameters),
        seed=seed,
        monte_carlo_counts=dict(monte_carlo_counts),
    )
    if not isinstance(output, Mapping):
        raise SimulationProvenanceError("Simulator output must be a JSON object.")
    output_record = dict(output)
    _validate_json_value(output_record, path="output")

    unsigned_provenance = {
        "provenance_version": PROVENANCE_VERSION,
        "scenario_parameters": dict(scenario_parameters),
        "assumptions": dict(assumptions),
        "seed": seed,
        "monte_carlo_counts": dict(monte_carlo_counts),
        "simulator_identifier": simulator_identifier,
        "simulator_version": simulator_version,
        "simulator_source_sha256": simulator_source_sha256,
        "output": output_record,
    }
    provenance_sha256 = sha256_json(unsigned_provenance)
    provenance = {**unsigned_provenance, "provenance_sha256": provenance_sha256}
    return {
        "provenance": provenance,
        "provenance_sha256": provenance_sha256,
        "output": output_record,
    }


def _validate_nonempty_mapping(value: Mapping[str, Any], *, name: str) -> None:
    if not isinstance(value, Mapping) or not value:
        raise SimulationProvenanceError(f"{name} must be a nonempty mapping.")
    _validate_json_value(dict(value), path=name, reject_placeholders=True)


def _validate_seed(seed: int) -> None:
    if type(seed) is not int:
        raise SimulationProvenanceError("seed must be an integer, not a boolean.")
    if seed < 0:
        raise SimulationProvenanceError("seed must be nonnegative.")


def _validate_monte_carlo_counts(counts: Mapping[str, int]) -> None:
    if not isinstance(counts, Mapping) or not counts:
        raise SimulationProvenanceError("monte_carlo_counts must be a nonempty mapping.")
    for name, count in counts.items():
        if not isinstance(name, str) or not name.strip() or _is_placeholder(name):
            raise SimulationProvenanceError("Monte Carlo count names must be explicit strings.")
        if type(count) is not int:
            raise SimulationProvenanceError("Monte Carlo counts must be integers, not booleans.")
        if count <= 0:
            raise SimulationProvenanceError("Monte Carlo counts must be positive.")


def _validate_metadata(
    *, simulator_identifier: str, simulator_version: str, simulator_source_sha256: str,
) -> None:
    for name, value in (
        ("simulator_identifier", simulator_identifier),
        ("simulator_version", simulator_version),
    ):
        if not isinstance(value, str) or _is_placeholder(value):
            raise SimulationProvenanceError(f"{name} must be an explicit non-placeholder string.")
    if not isinstance(simulator_source_sha256, str) or not _SHA256_PATTERN.fullmatch(simulator_source_sha256):
        raise SimulationProvenanceError("simulator_source_sha256 must be a lowercase SHA-256 digest.")


def _validate_json_value(value: object, *, path: str, reject_placeholders: bool = False) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise SimulationProvenanceError(f"{path} contains a non-finite number.")
    if value is None or isinstance(value, (bool, int, float)):
        return
    if isinstance(value, str):
        if reject_placeholders and _is_placeholder(value):
            raise SimulationProvenanceError(f"{path} contains a placeholder value.")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise SimulationProvenanceError(f"{path} contains a non-string object key.")
            if reject_placeholders and _is_placeholder(key):
                raise SimulationProvenanceError(f"{path} contains a placeholder key.")
            _validate_json_value(
                child,
                path=f"{path}.{key}",
                reject_placeholders=reject_placeholders,
            )
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_json_value(
                child,
                path=f"{path}[{index}]",
                reject_placeholders=reject_placeholders,
            )
        return
    raise SimulationProvenanceError(f"{path} is not JSON-serializable.")


def _is_placeholder(value: str) -> bool:
    return value.strip().lower() in _PLACEHOLDER_VALUES
