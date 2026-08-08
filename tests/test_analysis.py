import json
import unittest
from pathlib import Path

from effort_atlas.analysis import (
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    KSCommonSupport,
    analyze_confirmatory_rows,
    cap_invariance_calibration,
    dose_response_summaries,
    factorial_effects,
    item_clustered_bootstrap,
    paired_cap_transitions,
    replicate_variance_components,
    summarize_cells,
    validate_analysis_rows,
    wilson,
)


FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "task_d_known_answers.json").read_text()
)


def result_row(
    item_id,
    effort,
    cap,
    replicate,
    correct,
    *,
    finish_reason="stop",
    completion_tokens=2,
    extracted_answer_present=True,
):
    return {
        "panel": "panel-a",
        "model": "model-a",
        "provider_route": "provider-a",
        "item_id": item_id,
        "effort": effort,
        "cap": cap,
        "replicate": replicate,
        "correct": correct,
        "extracted_answer_present": extracted_answer_present,
        "extracted_answer": ("1" if correct else "0") if extracted_answer_present else None,
        "finish_reason": finish_reason,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": max(0, completion_tokens - 1),
        "latency_s": 1.0,
        "receipt_cost_usd": 0.01,
    }


def planned_row(item_id, effort, cap, replicate):
    return {
        "panel": "panel-a",
        "model": "model-a",
        "provider_route": "provider-a",
        "item_id": item_id,
        "effort": effort,
        "cap": cap,
        "replicate": replicate,
    }


def bootstrap_rows():
    rows = []
    spec = FIXTURE["bootstrap"]
    for item_id, cells in spec["items"].items():
        for cell, outcomes in cells.items():
            effort, cap = cell.split("|")
            for replicate, correct in enumerate(outcomes, start=1):
                rows.append(result_row(item_id, effort, int(cap), replicate, correct))
    return rows


class ConfirmatoryAnalysisTests(unittest.TestCase):
    def test_wilson_interval_matches_known_answer(self):
        low, high = wilson(5, 10)

        self.assertAlmostEqual(low, 0.236590, places=6)
        self.assertAlmostEqual(high, 0.763410, places=6)
        self.assertEqual(wilson(0, 0), (0.0, 0.0))

    def test_factorial_effects_and_fixed_seed_clustered_bootstrap(self):
        rows = bootstrap_rows()
        expected = FIXTURE["bootstrap"]["expected"]

        effects = factorial_effects(rows, effort_order=["low", "high"], caps=[4, 8])
        first = item_clustered_bootstrap(
            rows,
            effort_order=["low", "high"],
            caps=[4, 8],
            resamples=BOOTSTRAP_RESAMPLES,
            seed=BOOTSTRAP_SEED,
        )
        second = item_clustered_bootstrap(
            rows,
            effort_order=["low", "high"],
            caps=[4, 8],
            resamples=BOOTSTRAP_RESAMPLES,
            seed=BOOTSTRAP_SEED,
        )

        self.assertEqual(first, second)
        self.assertEqual(first["resamples"], 10_000)
        self.assertEqual(first["seed"], 20260722)
        slopes = {row["cap"]: row for row in effects["effort_slopes"]}
        boot_slopes = {row["cap"]: row for row in first["effort_slopes"]}
        cap_effects = {row["effort"]: row for row in effects["cap_effects"]}
        boot_cap_effects = {row["effort"]: row for row in first["cap_effects"]}
        self.assertEqual(slopes[4]["estimate"], expected["slope_at_4"])
        self.assertEqual(slopes[8]["estimate"], expected["slope_at_8"])
        self.assertEqual(cap_effects["low"]["estimate"], expected["low_cap_effect"])
        self.assertEqual(cap_effects["high"]["estimate"], expected["high_cap_effect"])
        self.assertEqual(effects["interaction"]["estimate"], expected["interaction"])
        self.assertEqual(
            [boot_slopes[4]["ci_low"], boot_slopes[4]["ci_high"]],
            expected["slope_at_4_ci"],
        )
        self.assertEqual(
            [boot_slopes[8]["ci_low"], boot_slopes[8]["ci_high"]],
            expected["slope_at_8_ci"],
        )
        self.assertEqual(
            [first["interaction"]["ci_low"], first["interaction"]["ci_high"]],
            expected["interaction_ci"],
        )
        self.assertEqual(
            [boot_cap_effects["low"]["ci_low"], boot_cap_effects["low"]["ci_high"]],
            [-1.0, 0.0],
        )
        self.assertEqual(
            [boot_cap_effects["high"]["ci_low"], boot_cap_effects["high"]["ci_high"]],
            [0.0, 1.0],
        )

    def test_replicate_variance_components_known_between_and_within_cases(self):
        between_rows = [
            result_row("a", "low", 4, 1, False),
            result_row("a", "low", 4, 2, False),
            result_row("b", "low", 4, 1, True),
            result_row("b", "low", 4, 2, True),
        ]
        within_rows = [
            result_row("a", "low", 4, 1, False),
            result_row("a", "low", 4, 2, True),
            result_row("b", "low", 4, 1, False),
            result_row("b", "low", 4, 2, True),
        ]

        between = replicate_variance_components(between_rows)
        within = replicate_variance_components(within_rows)

        self.assertEqual(between["within_item_variance"], 0.0)
        self.assertEqual(between["between_item_variance"], 0.5)
        self.assertEqual(between["intraclass_correlation"], 1.0)
        self.assertEqual(within["within_item_variance"], 0.5)
        self.assertEqual(within["between_item_variance"], 0.0)
        self.assertEqual(within["intraclass_correlation"], 0.0)

    def test_cell_summaries_report_amended_and_cross_cell_missingness_bounds(self):
        planned = [
            planned_row("a", "low", 4, 1),
            planned_row("a", "low", 4, 2),
            planned_row("b", "low", 4, 1),
            planned_row("b", "low", 4, 2),
            planned_row("a", "high", 4, 1),
            planned_row("b", "high", 4, 1),
        ]
        observed = [
            result_row("a", "low", 4, 1, True),
            result_row(
                "a",
                "low",
                4,
                2,
                False,
                finish_reason="length",
                completion_tokens=4,
                extracted_answer_present=False,
            ),
        ]

        cells = summarize_cells(observed, planned_rows=planned, effort_order=["low", "high"], caps=[4])
        by_effort = {cell["effort"]: cell for cell in cells}
        low = by_effort["low"]
        high = by_effort["high"]

        self.assertEqual((low["n"], low["k"], low["planned_n"], low["missing_n"]), (2, 1, 4, 2))
        self.assertEqual((low["accuracy_bound_lo"], low["accuracy_bound_hi"]), (0.5, 1.0))
        self.assertEqual(
            (low["missing_all_wrong_accuracy"], low["missing_all_correct_accuracy"]),
            (0.25, 0.75),
        )
        self.assertEqual((high["n"], high["planned_n"], high["missing_n"]), (0, 2, 2))
        self.assertEqual(
            (high["missing_all_wrong_accuracy"], high["missing_all_correct_accuracy"]),
            (0.0, 1.0),
        )
        self.assertEqual(low["proportions"]["accuracy"]["wilson"], wilson(1, 2))
        self.assertEqual(low["proportions"]["unanswered_length_stop"]["wilson"], wilson(1, 2))
        self.assertEqual(low["latency_s"], {"n": 2, "median": 1.0, "minimum": 1.0, "maximum": 1.0})
        self.assertEqual(low["receipt_cost_usd"], {"n": 2, "total": 0.02})

    def test_paired_transition_table_and_amended_rescue_taxonomy(self):
        rows = [
            result_row("wc", "low", 4, 1, False),
            result_row("wc", "low", 8, 1, True),
            result_row("cw", "low", 4, 1, True),
            result_row("cw", "low", 8, 1, False),
            result_row("cc", "low", 4, 1, True),
            result_row("cc", "low", 8, 1, True),
            result_row("ww", "low", 4, 1, False),
            result_row("ww", "low", 8, 1, False),
            result_row(
                "rescue",
                "low",
                4,
                1,
                False,
                finish_reason="length",
                completion_tokens=4,
                extracted_answer_present=False,
            ),
            result_row("rescue", "low", 8, 1, True),
            result_row(
                "grade-transition",
                "low",
                4,
                1,
                False,
                finish_reason="length",
                completion_tokens=4,
                extracted_answer_present=True,
            ),
            result_row("grade-transition", "low", 8, 1, True),
            result_row("missing-large", "low", 4, 1, False),
        ]
        planned = [
            *rows,
            planned_row("missing-large", "low", 8, 1),
        ]

        tables = paired_cap_transitions(rows, planned_rows=planned, effort_order=["low"], caps=[4, 8])
        table = tables[0]

        self.assertEqual(table["outcomes"]["wrong_to_correct"], 3)
        self.assertEqual(table["outcomes"]["correct_to_wrong"], 1)
        self.assertEqual(table["outcomes"]["correct_to_correct"], 1)
        self.assertEqual(table["outcomes"]["wrong_to_wrong"], 1)
        self.assertEqual(table["missing_larger_cap"], 1)
        self.assertEqual(table["rescue_taxonomy"]["primary_answer_rescue"], 1)
        self.assertEqual(table["rescue_taxonomy"]["answer_present_grade_transition"], 1)

    def test_dose_response_summarizes_effort_and_cap_profiles(self):
        rows = bootstrap_rows()
        cells = summarize_cells(rows, effort_order=["low", "high"], caps=[4, 8])

        dose = dose_response_summaries(cells, effort_order=["low", "high"], caps=[4, 8])

        at_four = next(profile for profile in dose["effort_profiles"] if profile["cap"] == 4)
        for_low = next(profile for profile in dose["cap_profiles"] if profile["effort"] == "low")
        self.assertEqual([point["accuracy"] for point in at_four["points"]], [0.5, 0.0])
        self.assertEqual(at_four["endpoint_effort_slope"], -0.5)
        self.assertEqual([point["accuracy"] for point in for_low["points"]], [0.5, 0.0])
        self.assertEqual(for_low["endpoint_cap_effect"], -0.5)

    def test_cap_invariance_predicts_truncation_and_default_ks_on_common_support(self):
        rows = [
            result_row("r1", "low", 16, 1, True, completion_tokens=2),
            result_row("r2", "low", 16, 1, True, completion_tokens=4),
            result_row("r3", "low", 16, 1, True, completion_tokens=10),
            result_row("r4", "low", 16, 1, True, completion_tokens=12),
            result_row("s1", "low", 8, 1, True, completion_tokens=2),
            result_row("s2", "low", 8, 1, False, completion_tokens=4),
            result_row("s3", "low", 8, 1, False, finish_reason="length", completion_tokens=8, extracted_answer_present=False),
            result_row("s4", "low", 8, 1, False, finish_reason="length", completion_tokens=8, extracted_answer_present=False),
        ]

        result = cap_invariance_calibration(rows, reference_cap=16, caps=[8])
        row = result[0]

        self.assertEqual(row["predicted_truncation_rate"], 0.5)
        self.assertEqual(row["observed_truncation_rate"], 0.5)
        self.assertEqual(row["absolute_rate_error"], 0.0)
        self.assertEqual(row["calibration_strategy"], KSCommonSupport.name)
        self.assertEqual(row["calibration_error"], 0.0)
        self.assertEqual(
            KSCommonSupport().calibration_error([1, 2, 3, 4], [1, 1, 1, 1], 4),
            0.75,
        )

    def test_cap_invariance_strategy_can_be_swapped_without_changing_callers(self):
        class ExactStrategy:
            name = "exact-test-strategy"

            def __init__(self):
                self.calls = []

            def calibration_error(self, reference_lengths, observed_lengths, cap):
                self.calls.append((tuple(reference_lengths), tuple(observed_lengths), cap))
                return 0.125

        strategy = ExactStrategy()
        rows = [
            result_row("r1", "low", 16, 1, True, completion_tokens=2),
            result_row("r2", "low", 16, 1, True, completion_tokens=10),
            result_row("s1", "low", 8, 1, True, completion_tokens=2),
            result_row("s2", "low", 8, 1, False, finish_reason="length", completion_tokens=8, extracted_answer_present=False),
        ]

        result = cap_invariance_calibration(rows, reference_cap=16, caps=[8], strategy=strategy)

        self.assertEqual(result[0]["calibration_strategy"], "exact-test-strategy")
        self.assertEqual(result[0]["calibration_error"], 0.125)
        self.assertEqual(strategy.calls, [((2, 10), (2,), 8)])

    def test_analysis_enforces_grader_v2_output_contract_without_grading(self):
        malformed = result_row("a", "low", 4, 1, True, extracted_answer_present=False)

        with self.assertRaisesRegex(ValueError, "extracted_answer"):
            validate_analysis_rows([malformed])

    def test_end_to_end_report_contains_every_prespecified_section(self):
        rows = bootstrap_rows()
        report = analyze_confirmatory_rows(
            rows,
            planned_rows=rows,
            effort_order=["low", "high"],
            caps=[4, 8],
            bootstrap_resamples=100,
        )

        self.assertEqual(report["assumptions"]["effort_slope"], "higher_effort_minus_lower_effort")
        self.assertEqual(len(report["panels"]), 1)
        self.assertEqual(
            set(report["panels"][0]),
            {
                "panel",
                "model",
                "provider_route",
                "cells",
                "effects",
                "bootstrap",
                "variance_components",
                "cap_transitions",
                "dose_response",
                "cap_invariance",
            },
        )

    def test_end_to_end_report_keeps_panels_separate(self):
        first = bootstrap_rows()
        second = [
            {**row, "panel": "panel-b", "model": "model-b"}
            for row in bootstrap_rows()
        ]

        report = analyze_confirmatory_rows(
            [*first, *second],
            planned_rows=[*first, *second],
            effort_order=["low", "high"],
            caps=[4, 8],
            bootstrap_resamples=10,
        )

        self.assertEqual(
            [(panel["panel"], panel["model"]) for panel in report["panels"]],
            [("panel-a", "model-a"), ("panel-b", "model-b")],
        )


if __name__ == "__main__":
    unittest.main()
