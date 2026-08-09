"""Deterministic, offline confirmatory analysis for REAP.

This module consumes already-collected and already-graded rows. It does not extract
answers, grade responses, infer termination, deduplicate attempts, or make API calls.
The caller must provide the grader-v2 output contract explicitly.
"""

from __future__ import annotations

import itertools
import math
import random
import statistics
from collections import Counter, defaultdict
from typing import Any, Iterable, Protocol, Sequence


BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20260722
PANEL_KEYS = ("panel", "model", "provider_route")
PAIR_KEYS = ("item_id", "replicate")
RESULT_KEYS = (
    *PANEL_KEYS,
    *PAIR_KEYS,
    "effort",
    "cap",
    "correct",
    "extracted_answer_present",
    "extracted_answer",
    "finish_reason",
    "completion_tokens",
)
PLANNED_KEYS = (*PANEL_KEYS, *PAIR_KEYS, "effort", "cap")
LENGTH_FINISH_REASONS = {"length", "max_tokens", "max_output_tokens"}
NORMAL_FINISH_REASONS = {"stop", "complete", "completed"}
KNOWN_EFFORT_ORDER = {
    "none": 0,
    "minimal": 1,
    "low": 2,
    "medium": 3,
    "high": 4,
    "max": 5,
    "xhigh": 6,
}


class CalibrationStrategy(Protocol):
    """Swappable cap-invariance distribution calibration metric."""

    name: str

    def calibration_error(
        self,
        reference_lengths: Sequence[int],
        observed_lengths: Sequence[int],
        cap: int,
    ) -> float | None:
        ...


class KSCommonSupport:
    """Two-sample KS distance on the shared observable support at or below cap."""

    name = "ks_on_common_support"

    def calibration_error(
        self,
        reference_lengths: Sequence[int],
        observed_lengths: Sequence[int],
        cap: int,
    ) -> float | None:
        reference = [value for value in reference_lengths if value <= cap]
        observed = [value for value in observed_lengths if value <= cap]
        if not reference or not observed:
            return None
        checkpoints = sorted(set(reference) | set(observed))
        return max(
            abs(
                sum(value <= checkpoint for value in reference) / len(reference)
                - sum(value <= checkpoint for value in observed) / len(observed)
            )
            for checkpoint in checkpoints
        )


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval, ported from the legacy exploratory analyzer."""
    if type(k) is not int or type(n) is not int or n < 0 or k < 0 or k > n:
        raise ValueError("Wilson inputs must be integers satisfying 0 <= k <= n.")
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))
    return (max(0.0, center - half), min(1.0, center + half))


def validate_analysis_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate analysis fields without performing extraction or grading."""
    validated = list(rows)
    seen: set[tuple[Any, ...]] = set()
    identity_keys = (*PANEL_KEYS, *PAIR_KEYS, "effort", "cap")
    for index, row in enumerate(validated, start=1):
        missing = [key for key in RESULT_KEYS if key not in row]
        if missing:
            raise ValueError(f"Analysis row {index} is missing: {', '.join(missing)}")
        if any(row[key] is None for key in (*PANEL_KEYS, *PAIR_KEYS, "effort")):
            raise ValueError(f"Analysis row {index} has an incomplete immutable identity.")
        if type(row["cap"]) is not int or row["cap"] <= 0:
            raise ValueError(f"Analysis row {index} has an invalid cap.")
        if type(row["replicate"]) is not int or row["replicate"] <= 0:
            raise ValueError(f"Analysis row {index} has an invalid replicate.")
        if type(row["correct"]) is not bool:
            raise ValueError(f"Analysis row {index} has a non-boolean grade.")
        if type(row["extracted_answer_present"]) is not bool:
            raise ValueError(
                f"Analysis row {index} has invalid extracted_answer_present."
            )
        extracted = row["extracted_answer"]
        if row["extracted_answer_present"]:
            if not isinstance(extracted, str) or not extracted.strip():
                raise ValueError(
                    f"Analysis row {index} requires a nonempty string extracted_answer."
                )
        elif extracted is not None:
            raise ValueError(
                f"Analysis row {index} requires extracted_answer=null when absent."
            )
        if row["correct"] and not row["extracted_answer_present"]:
            raise ValueError(
                f"Analysis row {index} is internally inconsistent: correct without extracted_answer."
            )
        if not str(row["finish_reason"] or "").strip():
            raise ValueError(f"Analysis row {index} has no finish_reason.")
        if type(row["completion_tokens"]) is not int or row["completion_tokens"] < 0:
            raise ValueError(f"Analysis row {index} has invalid completion_tokens.")
        if "reasoning_tokens" in row and (
            type(row["reasoning_tokens"]) is not int or row["reasoning_tokens"] < 0
        ):
            raise ValueError(f"Analysis row {index} has invalid reasoning_tokens.")
        if "latency_s" in row and (
            type(row["latency_s"]) not in (int, float)
            or not math.isfinite(row["latency_s"])
            or row["latency_s"] < 0
        ):
            raise ValueError(f"Analysis row {index} has invalid latency_s.")
        if "receipt_cost_usd" in row and (
            type(row["receipt_cost_usd"]) not in (int, float)
            or not math.isfinite(row["receipt_cost_usd"])
            or row["receipt_cost_usd"] < 0
        ):
            raise ValueError(f"Analysis row {index} has invalid receipt_cost_usd.")
        identity = tuple(row[key] for key in identity_keys)
        if identity in seen:
            raise ValueError(f"Duplicate immutable analysis row: {identity!r}")
        seen.add(identity)
    return validated


def _validate_planned_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    planned = list(rows)
    seen: set[tuple[Any, ...]] = set()
    for index, row in enumerate(planned, start=1):
        missing = [key for key in PLANNED_KEYS if key not in row]
        if missing:
            raise ValueError(f"Planned row {index} is missing: {', '.join(missing)}")
        if any(row[key] is None for key in (*PANEL_KEYS, *PAIR_KEYS, "effort")):
            raise ValueError(f"Planned row {index} has an incomplete immutable identity.")
        if type(row["cap"]) is not int or row["cap"] <= 0:
            raise ValueError(f"Planned row {index} has an invalid cap.")
        if type(row["replicate"]) is not int or row["replicate"] <= 0:
            raise ValueError(f"Planned row {index} has an invalid replicate.")
        identity = tuple(row[key] for key in PLANNED_KEYS)
        if identity in seen:
            raise ValueError(f"Duplicate planned analysis row: {identity!r}")
        seen.add(identity)
    return planned


def _panel_identity(rows: Sequence[dict[str, Any]]) -> tuple[Any, Any, Any]:
    identities = {tuple(row[key] for key in PANEL_KEYS) for row in rows}
    if len(identities) != 1:
        raise ValueError("A panel statistic cannot pool rows across panels or routes.")
    return next(iter(identities))


def _is_length_stop(row: dict[str, Any]) -> bool:
    return str(row.get("finish_reason", "")).strip().lower() in LENGTH_FINISH_REASONS


def _is_normal_stop(row: dict[str, Any]) -> bool:
    return str(row.get("finish_reason", "")).strip().lower() in NORMAL_FINISH_REASONS


def _mean(values: Sequence[int | float]) -> float | None:
    return sum(values) / len(values) if values else None


def _proportion(k: int, n: int) -> dict[str, Any]:
    return {
        "k": k,
        "n": n,
        "estimate": k / n if n else None,
        "wilson": wilson(k, n),
    }


def _ordered_efforts(rows: Sequence[dict[str, Any]]) -> list[Any]:
    values = {row["effort"] for row in rows}

    def sort_key(value: Any) -> tuple[int, float | str]:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return (0, float(value))
        label = str(value)
        if label in KNOWN_EFFORT_ORDER:
            return (1, float(KNOWN_EFFORT_ORDER[label]))
        return (2, label)

    return sorted(values, key=sort_key)


def _require_dimensions(
    rows: Sequence[dict[str, Any]],
    effort_order: Sequence[Any] | None,
    caps: Sequence[int] | None,
) -> tuple[list[Any], list[int]]:
    efforts = list(effort_order) if effort_order is not None else _ordered_efforts(rows)
    ordered_caps = list(caps) if caps is not None else sorted({row["cap"] for row in rows})
    if len(efforts) != len(set(map(str, efforts))):
        raise ValueError("effort_order contains duplicates.")
    if ordered_caps != sorted(set(ordered_caps)):
        raise ValueError("caps must be unique and increasing.")
    unknown_efforts = {row["effort"] for row in rows} - set(efforts)
    unknown_caps = {row["cap"] for row in rows} - set(ordered_caps)
    if unknown_efforts or unknown_caps:
        raise ValueError("Rows contain effort or cap values outside the configured grid.")
    return efforts, ordered_caps


def replicate_variance_components(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """One-way random-intercept method-of-moments components for binary grades."""
    records = list(rows)
    by_item: defaultdict[Any, list[float]] = defaultdict(list)
    for row in records:
        if type(row.get("correct")) is not bool:
            raise ValueError("Variance components require boolean correct values.")
        by_item[row.get("item_id")].append(float(row["correct"]))
    n_observations = len(records)
    n_items = len(by_item)
    if n_items < 2 or n_observations <= n_items:
        return {
            "method": "one_way_random_intercept_method_of_moments",
            "n_items": n_items,
            "n_observations": n_observations,
            "within_item_variance": None,
            "between_item_variance": None,
            "intraclass_correlation": None,
        }
    grand_mean = sum(sum(values) for values in by_item.values()) / n_observations
    item_means = {item: sum(values) / len(values) for item, values in by_item.items()}
    ss_within = sum(
        (value - item_means[item]) ** 2
        for item, values in by_item.items()
        for value in values
    )
    ms_within = ss_within / (n_observations - n_items)
    ss_between = sum(
        len(values) * (item_means[item] - grand_mean) ** 2
        for item, values in by_item.items()
    )
    ms_between = ss_between / (n_items - 1)
    effective_replicates = (
        n_observations
        - sum(len(values) ** 2 for values in by_item.values()) / n_observations
    ) / (n_items - 1)
    between = max(0.0, (ms_between - ms_within) / effective_replicates)
    total = between + ms_within
    return {
        "method": "one_way_random_intercept_method_of_moments",
        "n_items": n_items,
        "n_observations": n_observations,
        "within_item_variance": ms_within,
        "between_item_variance": between,
        "intraclass_correlation": between / total if total else 0.0,
    }


def summarize_cells(
    rows: Iterable[dict[str, Any]],
    *,
    planned_rows: Iterable[dict[str, Any]] | None = None,
    effort_order: Sequence[Any] | None = None,
    caps: Sequence[int] | None = None,
) -> list[dict[str, Any]]:
    records = validate_analysis_rows(rows)
    planned = _validate_planned_rows(planned_rows or [])
    identity_source = [*records, *planned]
    if not identity_source:
        return []
    _panel_identity(identity_source)
    efforts, ordered_caps = _require_dimensions(identity_source, effort_order, caps)
    observed_by_cell: defaultdict[tuple[Any, int], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        observed_by_cell[(row["effort"], row["cap"])].append(row)
    planned_by_cell: defaultdict[tuple[Any, int], list[dict[str, Any]]] = defaultdict(list)
    if planned:
        observed_keys = {tuple(row[key] for key in PLANNED_KEYS) for row in records}
        planned_keys = {tuple(row[key] for key in PLANNED_KEYS) for row in planned}
        if not observed_keys <= planned_keys:
            raise ValueError("Observed analysis rows include identities absent from the plan.")
        for row in planned:
            planned_by_cell[(row["effort"], row["cap"])].append(row)
    cells = []
    for effort in efforts:
        for cap in ordered_caps:
            cell_rows = observed_by_cell[(effort, cap)]
            n = len(cell_rows)
            k = sum(row["correct"] for row in cell_rows)
            length_stops = sum(_is_length_stop(row) for row in cell_rows)
            unanswered_length_stops = sum(
                _is_length_stop(row) and not row["extracted_answer_present"]
                for row in cell_rows
            )
            answer_present_length_stops = length_stops - unanswered_length_stops
            empty_extracted_answers = sum(
                not row["extracted_answer_present"] for row in cell_rows
            )
            planned_n = len(planned_by_cell[(effort, cap)]) if planned else n
            missing_n = planned_n - n
            if missing_n < 0:
                raise ValueError("Observed cell size exceeds its planned denominator.")
            completion_tokens = [row["completion_tokens"] for row in cell_rows]
            reasoning_tokens = [
                row["reasoning_tokens"]
                for row in cell_rows
                if "reasoning_tokens" in row
            ]
            latencies = [row["latency_s"] for row in cell_rows if "latency_s" in row]
            receipt_costs = [
                row["receipt_cost_usd"]
                for row in cell_rows
                if "receipt_cost_usd" in row
            ]
            proportions = {
                "accuracy": _proportion(k, n),
                "length_stop": _proportion(length_stops, n),
                "unanswered_length_stop": _proportion(unanswered_length_stops, n),
                "answer_present_length_stop": _proportion(answer_present_length_stops, n),
                "empty_extracted_answer": _proportion(empty_extracted_answers, n),
            }
            cells.append(
                {
                    "effort": effort,
                    "cap": cap,
                    "n": n,
                    "k": k,
                    "accuracy": k / n if n else None,
                    "proportions": proportions,
                    "length_stops": length_stops,
                    "length_stop_rate": length_stops / n if n else None,
                    "unanswered_length_stops": unanswered_length_stops,
                    "unanswered_length_stop_rate": unanswered_length_stops / n if n else None,
                    "answer_present_length_stops": answer_present_length_stops,
                    "empty_extracted_answers": empty_extracted_answers,
                    "accuracy_bound_lo": k / n if n else None,
                    "accuracy_bound_hi": (
                        (k + unanswered_length_stops) / n if n else None
                    ),
                    "planned_n": planned_n,
                    "missing_n": missing_n,
                    "missing_all_wrong_accuracy": k / planned_n if planned_n else None,
                    "missing_all_correct_accuracy": (
                        (k + missing_n) / planned_n if planned_n else None
                    ),
                    "completion_tokens": {
                        "mean": _mean(completion_tokens),
                        "median": statistics.median(completion_tokens) if completion_tokens else None,
                        "minimum": min(completion_tokens) if completion_tokens else None,
                        "maximum": max(completion_tokens) if completion_tokens else None,
                    },
                    "reasoning_tokens": {
                        "n": len(reasoning_tokens),
                        "mean": _mean(reasoning_tokens),
                        "median": statistics.median(reasoning_tokens) if reasoning_tokens else None,
                    },
                    "latency_s": {
                        "n": len(latencies),
                        "median": statistics.median(latencies) if latencies else None,
                        "minimum": min(latencies) if latencies else None,
                        "maximum": max(latencies) if latencies else None,
                    },
                    "receipt_cost_usd": {
                        "n": len(receipt_costs),
                        "total": sum(receipt_costs) if receipt_costs else None,
                    },
                    "variance_components": replicate_variance_components(cell_rows),
                }
            )
    return cells


def _cell_accuracies(rows: Sequence[dict[str, Any]]) -> dict[tuple[Any, int], float]:
    totals: defaultdict[tuple[Any, int], list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        key = (row["effort"], row["cap"])
        totals[key][0] += int(row["correct"])
        totals[key][1] += 1
    return {key: k / n for key, (k, n) in totals.items() if n}


def _effects_from_accuracies(
    accuracies: dict[tuple[Any, int], float],
    efforts: Sequence[Any],
    caps: Sequence[int],
) -> dict[str, Any]:
    if len(efforts) < 2 or len(caps) < 2:
        raise ValueError("Factorial effects require at least two efforts and two caps.")
    lower, higher = efforts[0], efforts[-1]
    small, large = caps[0], caps[-1]
    slopes = []
    for cap in caps:
        values = (accuracies.get((lower, cap)), accuracies.get((higher, cap)))
        slopes.append(
            {
                "lower_effort": lower,
                "higher_effort": higher,
                "cap": cap,
                "estimate": None if None in values else values[1] - values[0],
            }
        )
    cap_effects = []
    for effort in efforts:
        values = (accuracies.get((effort, small)), accuracies.get((effort, large)))
        cap_effects.append(
            {
                "effort": effort,
                "small_cap": small,
                "large_cap": large,
                "estimate": None if None in values else values[1] - values[0],
            }
        )
    small_slope = next(row["estimate"] for row in slopes if row["cap"] == small)
    large_slope = next(row["estimate"] for row in slopes if row["cap"] == large)
    interaction = None if small_slope is None or large_slope is None else large_slope - small_slope
    return {
        "effort_slopes": slopes,
        "cap_effects": cap_effects,
        "interaction": {
            "lower_effort": lower,
            "higher_effort": higher,
            "small_cap": small,
            "large_cap": large,
            "estimate": interaction,
        },
    }


def factorial_effects(
    rows: Iterable[dict[str, Any]],
    *,
    effort_order: Sequence[Any],
    caps: Sequence[int],
) -> dict[str, Any]:
    records = validate_analysis_rows(rows)
    if records:
        _panel_identity(records)
    efforts, ordered_caps = _require_dimensions(records, effort_order, caps)
    return _effects_from_accuracies(_cell_accuracies(records), efforts, ordered_caps)


def _percentile(values: Sequence[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def item_clustered_bootstrap(
    rows: Iterable[dict[str, Any]],
    *,
    effort_order: Sequence[Any],
    caps: Sequence[int],
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
    confidence: float = 0.95,
) -> dict[str, Any]:
    records = validate_analysis_rows(rows)
    if type(resamples) is not int or resamples <= 0:
        raise ValueError("Bootstrap resamples must be a positive integer.")
    if not 0 < confidence < 1:
        raise ValueError("Bootstrap confidence must lie between zero and one.")
    if records:
        _panel_identity(records)
    efforts, ordered_caps = _require_dimensions(records, effort_order, caps)
    point = _effects_from_accuracies(_cell_accuracies(records), efforts, ordered_caps)
    by_item: defaultdict[Any, dict[tuple[Any, int], list[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0])
    )
    for row in records:
        total = by_item[row["item_id"]][(row["effort"], row["cap"])]
        total[0] += int(row["correct"])
        total[1] += 1
    items = sorted(by_item, key=str)
    if not items:
        def unavailable(row: dict[str, Any]) -> dict[str, Any]:
            return {**row, "ci_low": None, "ci_high": None, "valid_resamples": 0}

        return {
            "method": "item_clustered_percentile_bootstrap",
            "resamples": resamples,
            "seed": seed,
            "confidence": confidence,
            "n_item_clusters": 0,
            "effort_slopes": [unavailable(row) for row in point["effort_slopes"]],
            "cap_effects": [unavailable(row) for row in point["cap_effects"]],
            "interaction": unavailable(point["interaction"]),
        }
    rng = random.Random(seed)
    slope_samples: dict[int, list[float]] = {cap: [] for cap in ordered_caps}
    cap_samples: dict[Any, list[float]] = {effort: [] for effort in efforts}
    interaction_samples: list[float] = []
    for _ in range(resamples):
        totals: defaultdict[tuple[Any, int], list[int]] = defaultdict(lambda: [0, 0])
        for item in (rng.choice(items) for _ in items):
            for cell, (k, n) in by_item[item].items():
                totals[cell][0] += k
                totals[cell][1] += n
        accuracies = {cell: k / n for cell, (k, n) in totals.items() if n}
        sampled = _effects_from_accuracies(accuracies, efforts, ordered_caps)
        for row in sampled["effort_slopes"]:
            if row["estimate"] is not None:
                slope_samples[row["cap"]].append(row["estimate"])
        for row in sampled["cap_effects"]:
            if row["estimate"] is not None:
                cap_samples[row["effort"]].append(row["estimate"])
        if sampled["interaction"]["estimate"] is not None:
            interaction_samples.append(sampled["interaction"]["estimate"])
    alpha = (1 - confidence) / 2

    def with_interval(row: dict[str, Any], values: Sequence[float]) -> dict[str, Any]:
        return {
            **row,
            "ci_low": _percentile(values, alpha),
            "ci_high": _percentile(values, 1 - alpha),
            "valid_resamples": len(values),
        }

    return {
        "method": "item_clustered_percentile_bootstrap",
        "resamples": resamples,
        "seed": seed,
        "confidence": confidence,
        "n_item_clusters": len(items),
        "effort_slopes": [
            with_interval(row, slope_samples[row["cap"]])
            for row in point["effort_slopes"]
        ],
        "cap_effects": [
            with_interval(row, cap_samples[row["effort"]])
            for row in point["cap_effects"]
        ],
        "interaction": with_interval(point["interaction"], interaction_samples),
    }


def _rescue_status(small: dict[str, Any], large: dict[str, Any]) -> str:
    if (
        _is_length_stop(small)
        and not small["extracted_answer_present"]
        and _is_normal_stop(large)
        and large["correct"]
    ):
        return "primary_answer_rescue"
    if (
        _is_length_stop(small)
        and small["extracted_answer_present"]
        and not small["correct"]
        and _is_normal_stop(large)
        and large["correct"]
    ):
        return "answer_present_grade_transition"
    if not _is_length_stop(small):
        return "smaller_cap_not_length_stopped"
    if _is_length_stop(large):
        return "still_length_stopped"
    if _is_normal_stop(large) and not large["correct"]:
        return "larger_cap_completed_wrong"
    return "other_terminal_transition"


def paired_cap_transitions(
    rows: Iterable[dict[str, Any]],
    *,
    planned_rows: Iterable[dict[str, Any]] | None = None,
    effort_order: Sequence[Any] | None = None,
    caps: Sequence[int] | None = None,
) -> list[dict[str, Any]]:
    records = validate_analysis_rows(rows)
    planned = _validate_planned_rows(planned_rows or [])
    identity_source = [*records, *planned]
    if not identity_source:
        return []
    _panel_identity(identity_source)
    efforts, ordered_caps = _require_dimensions(identity_source, effort_order, caps)
    observed_by_cell: defaultdict[tuple[Any, Any, int], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        observed_by_cell[(row["item_id"], row["effort"], row["cap"])].append(row)
    planned_by_cell: Counter[tuple[Any, Any, int]] = Counter(
        (row["item_id"], row["effort"], row["cap"]) for row in planned
    )
    item_keys = {
        (row["item_id"], row["effort"], row["cap"])
        for row in [*records, *planned]
    }
    tables = []
    for effort in efforts:
        for small_cap, large_cap in itertools.combinations(ordered_caps, 2):
            item_ids = sorted(
                {
                    item_id
                    for item_id, row_effort, cap in item_keys
                    if row_effort == effort and cap in {small_cap, large_cap}
                },
                key=str,
            )
            expected_mass = {
                "wrong_to_wrong": 0.0,
                "wrong_to_correct": 0.0,
                "correct_to_wrong": 0.0,
                "correct_to_correct": 0.0,
            }
            exact_states: Counter[tuple[int, int, int, int]] = Counter()
            item_statistics = []
            missing_small = missing_large = missing_both = 0
            rescue_evidence_items = 0
            paired_items = 0
            for item_id in item_ids:
                small_rows = observed_by_cell[(item_id, effort, small_cap)]
                large_rows = observed_by_cell[(item_id, effort, large_cap)]
                small_observed = len(small_rows)
                large_observed = len(large_rows)
                small_correct = sum(row["correct"] for row in small_rows)
                large_correct = sum(row["correct"] for row in large_rows)
                small_planned = planned_by_cell[(item_id, effort, small_cap)] or small_observed
                large_planned = planned_by_cell[(item_id, effort, large_cap)] or large_observed
                if small_observed > small_planned or large_observed > large_planned:
                    raise ValueError(
                        "Observed item-level transition replicates exceed the planned count."
                    )
                if not small_observed and not large_observed:
                    missing_both += 1
                elif not small_observed:
                    missing_small += 1
                elif not large_observed:
                    missing_large += 1
                small_unanswered = sum(
                    _is_length_stop(row) and not row["extracted_answer_present"]
                    for row in small_rows
                )
                large_normal_correct = sum(
                    _is_normal_stop(row) and row["correct"] for row in large_rows
                )
                rescue_evidence_present = bool(
                    small_unanswered and large_normal_correct
                )
                rescue_evidence_items += rescue_evidence_present
                item_statistics.append(
                    {
                        "item_id": item_id,
                        "small_correct_n": small_correct,
                        "small_observed_n": small_observed,
                        "small_planned_n": small_planned,
                        "small_missing_n": small_planned - small_observed,
                        "small_accuracy": (
                            small_correct / small_observed if small_observed else None
                        ),
                        "large_correct_n": large_correct,
                        "large_observed_n": large_observed,
                        "large_planned_n": large_planned,
                        "large_missing_n": large_planned - large_observed,
                        "large_accuracy": (
                            large_correct / large_observed if large_observed else None
                        ),
                        "small_unanswered_length_n": small_unanswered,
                        "large_normal_correct_n": large_normal_correct,
                        "rescue_evidence_present": rescue_evidence_present,
                        "rescue_evidence_interpretation": (
                            "descriptive_independent_draw_evidence_not_a_continuation"
                        ),
                    }
                )
                if not small_observed or not large_observed:
                    continue
                paired_items += 1
                exact_states[
                    (small_correct, small_observed, large_correct, large_observed)
                ] += 1
                p_small = small_correct / small_observed
                p_large = large_correct / large_observed
                expected_mass["wrong_to_wrong"] += (1 - p_small) * (1 - p_large)
                expected_mass["wrong_to_correct"] += (1 - p_small) * p_large
                expected_mass["correct_to_wrong"] += p_small * (1 - p_large)
            expected_mass["correct_to_correct"] = float(paired_items) - math.fsum(
                expected_mass[key]
                for key in (
                    "wrong_to_wrong",
                    "wrong_to_correct",
                    "correct_to_wrong",
                )
            )
            exact_state_rows = [
                {
                    "small_correct_n": state[0],
                    "small_observed_n": state[1],
                    "large_correct_n": state[2],
                    "large_observed_n": state[3],
                    "item_n": item_n,
                }
                for state, item_n in sorted(exact_states.items())
            ]
            tables.append(
                {
                    "effort": effort,
                    "small_cap": small_cap,
                    "large_cap": large_cap,
                    "is_adjacent": ordered_caps.index(large_cap) - ordered_caps.index(small_cap) == 1,
                    "is_primary_endpoint_contrast": (
                        small_cap == ordered_caps[0] and large_cap == ordered_caps[-1]
                    ),
                    "pairing_unit": "item_id",
                    "independent_draws": True,
                    "interpretation": "expected_item_mass_not_observed_continuations",
                    "n_items": len(item_ids),
                    "n_paired_items": paired_items,
                    "expected_item_mass": expected_mass,
                    "exact_state_transitions": exact_state_rows,
                    "item_sufficient_statistics": item_statistics,
                    "n_rescue_evidence_items": rescue_evidence_items,
                    "missing_smaller_cap_items": missing_small,
                    "missing_larger_cap_items": missing_large,
                    "missing_both_caps_items": missing_both,
                }
            )
    return tables


def dose_response_summaries(
    cells: Iterable[dict[str, Any]],
    *,
    effort_order: Sequence[Any],
    caps: Sequence[int],
) -> dict[str, Any]:
    records = list(cells)
    lookup = {(row["effort"], row["cap"]): row for row in records}

    def point(effort: Any, cap: int) -> dict[str, Any]:
        cell = lookup.get((effort, cap), {})
        return {
            "effort": effort,
            "cap": cap,
            "n": cell.get("n", 0),
            "accuracy": cell.get("accuracy"),
            "length_stop_rate": cell.get("length_stop_rate"),
            "unanswered_length_stop_rate": cell.get("unanswered_length_stop_rate"),
        }

    effort_profiles = []
    for cap in caps:
        points = [point(effort, cap) for effort in effort_order]
        endpoints = (points[0]["accuracy"], points[-1]["accuracy"])
        effort_profiles.append(
            {
                "cap": cap,
                "points": points,
                "endpoint_effort_slope": (
                    None if None in endpoints else endpoints[1] - endpoints[0]
                ),
            }
        )
    cap_profiles = []
    for effort in effort_order:
        points = [point(effort, cap) for cap in caps]
        endpoints = (points[0]["accuracy"], points[-1]["accuracy"])
        cap_profiles.append(
            {
                "effort": effort,
                "points": points,
                "endpoint_cap_effect": (
                    None if None in endpoints else endpoints[1] - endpoints[0]
                ),
            }
        )
    return {"effort_profiles": effort_profiles, "cap_profiles": cap_profiles}


def cap_invariance_calibration(
    rows: Iterable[dict[str, Any]],
    *,
    reference_cap: int,
    caps: Sequence[int] | None = None,
    effort_order: Sequence[Any] | None = None,
    strategy: CalibrationStrategy | None = None,
) -> list[dict[str, Any]]:
    records = validate_analysis_rows(rows)
    if records:
        _panel_identity(records)
    efforts = list(effort_order) if effort_order is not None else _ordered_efforts(records)
    if {row["effort"] for row in records} - set(efforts):
        raise ValueError("Rows contain effort values outside the configured calibration grid.")
    target_caps = list(caps) if caps is not None else sorted(
        {row["cap"] for row in records if row["cap"] < reference_cap}
    )
    if any(cap >= reference_cap for cap in target_caps):
        raise ValueError("Calibration target caps must be smaller than reference_cap.")
    metric = strategy or KSCommonSupport()
    output = []
    for effort in efforts:
        reference_rows = [
            row for row in records if row["effort"] == effort and row["cap"] == reference_cap
        ]
        reference_lengths = [
            row["completion_tokens"] for row in reference_rows if not _is_length_stop(row)
        ]
        reference_length_stops = sum(_is_length_stop(row) for row in reference_rows)
        for cap in target_caps:
            observed_rows = [
                row for row in records if row["effort"] == effort and row["cap"] == cap
            ]
            observed_lengths = [
                row["completion_tokens"] for row in observed_rows if not _is_length_stop(row)
            ]
            predicted = (
                sum(length > cap for length in reference_lengths) / len(reference_lengths)
                if reference_lengths
                else None
            )
            observed = (
                sum(_is_length_stop(row) for row in observed_rows) / len(observed_rows)
                if observed_rows
                else None
            )
            output.append(
                {
                    "effort": effort,
                    "reference_cap": reference_cap,
                    "cap": cap,
                    "reference_n_completed": len(reference_lengths),
                    "reference_length_stops_excluded": reference_length_stops,
                    "observed_n": len(observed_rows),
                    "predicted_truncation_rate": predicted,
                    "observed_truncation_rate": observed,
                    "signed_rate_error": (
                        None if predicted is None or observed is None else predicted - observed
                    ),
                    "absolute_rate_error": (
                        None if predicted is None or observed is None else abs(predicted - observed)
                    ),
                    "calibration_strategy": metric.name,
                    "calibration_error": metric.calibration_error(
                        reference_lengths, observed_lengths, cap
                    ),
                }
            )
    return output


def analyze_confirmatory_rows(
    rows: Iterable[dict[str, Any]],
    *,
    planned_rows: Iterable[dict[str, Any]] | None = None,
    effort_order: Sequence[Any] | None = None,
    caps: Sequence[int] | None = None,
    bootstrap_resamples: int = BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
    calibration_strategy: CalibrationStrategy | None = None,
) -> dict[str, Any]:
    """Analyze panels separately and return a JSON-serializable pre-data report."""
    records = validate_analysis_rows(rows)
    planned = _validate_planned_rows(planned_rows or [])
    panel_ids = sorted(
        {
            tuple(row[key] for key in PANEL_KEYS)
            for row in [*records, *planned]
        },
        key=lambda value: tuple(map(str, value)),
    )
    panels = []
    for panel_id in panel_ids:
        panel_rows = [
            row for row in records if tuple(row[key] for key in PANEL_KEYS) == panel_id
        ]
        panel_plan = [
            row for row in planned if tuple(row[key] for key in PANEL_KEYS) == panel_id
        ]
        dimension_source = panel_rows or panel_plan
        efforts, ordered_caps = _require_dimensions(dimension_source, effort_order, caps)
        cells = summarize_cells(
            panel_rows,
            planned_rows=panel_plan,
            effort_order=efforts,
            caps=ordered_caps,
        )
        effects = factorial_effects(
            panel_rows, effort_order=efforts, caps=ordered_caps
        )
        bootstrap = item_clustered_bootstrap(
            panel_rows,
            effort_order=efforts,
            caps=ordered_caps,
            resamples=bootstrap_resamples,
            seed=bootstrap_seed,
        )
        transitions = paired_cap_transitions(
            panel_rows,
            planned_rows=panel_plan,
            effort_order=efforts,
            caps=ordered_caps,
        )
        variance = [
            {
                "effort": cell["effort"],
                "cap": cell["cap"],
                **cell["variance_components"],
            }
            for cell in cells
        ]
        panels.append(
            {
                "panel": panel_id[0],
                "model": panel_id[1],
                "provider_route": panel_id[2],
                "cells": cells,
                "effects": effects,
                "bootstrap": bootstrap,
                "variance_components": variance,
                "cap_transitions": transitions,
                "dose_response": dose_response_summaries(
                    cells, effort_order=efforts, caps=ordered_caps
                ),
                "cap_invariance": cap_invariance_calibration(
                    panel_rows,
                    reference_cap=ordered_caps[-1],
                    caps=ordered_caps[:-1],
                    effort_order=efforts,
                    strategy=calibration_strategy,
                ),
            }
        )
    return {
        "analysis_version": 1,
        "assumptions": {
            "panel_pooling": "none",
            "accuracy": "grader_boolean_regardless_of_finish_reason",
            "unanswered_length_stop": "length_finish_and_extracted_answer_present_false",
            "unanswered_accuracy_bound": "observed_k_over_n_to_observed_k_plus_unanswered_length_stops_over_n",
            "cross_cell_missingness": "per_cell_all_missing_wrong_and_all_missing_correct",
            "effort_slope": "higher_effort_minus_lower_effort",
            "effort_contrast_on_multilevel_grid": "first_vs_last_configured_effort",
            "cap_effect": "larger_cap_minus_smaller_cap",
            "cap_effect_on_multicap_grid": "first_vs_last_configured_cap",
            "interaction": "large_cap_effort_slope_minus_small_cap_effort_slope",
            "bootstrap_unit": "item_id_with_all_replicates_and_cells",
            "bootstrap_interval": "percentile",
            "variance_components": "one_way_random_intercept_method_of_moments",
            "negative_between_item_variance": "clamped_to_zero",
            "cap_transition_pairing": "item_id_empirical_marginal_outer_product",
            "cap_transition_interpretation": "expected_item_mass_not_observed_continuations",
            "cap_transition_scope": "all_ordered_cap_pairs",
            "reference_length_distribution": "empirical_completed_lengths_at_largest_cap",
            "reference_length_stops": "excluded_and_counted",
            "reference_truncation_rule": "completion_tokens_strictly_greater_than_cap",
            "default_calibration": "two_sample_ks_on_shared_support_at_or_below_target_cap",
        },
        "panels": panels,
    }
