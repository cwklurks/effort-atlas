from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "ecosystem_audit"


# This is deliberately an independent, path-and-symbol-level contract rather than
# merely checking that a listed receipt ID exists. A byte-valid receipt for an
# unrelated task must not satisfy dispatch provenance.
DISPATCH_CONTRACTS = {
    "gsm8k_flexible_extract": {
        "callable": "lm_eval.filters.extraction:RegexFilter.apply + lm_eval.api.metrics:exact_match_hf_evaluate",
        "task": "lm_eval/tasks/gsm8k/gsm8k-cot.yaml flexible-extract",
        "headline": "true",
        "receipts": {
            "F004": ("lm_eval/tasks/gsm8k/gsm8k-cot.yaml", ("group_select: -1", "name: flexible-extract")),
            "F005": ("lm_eval/filters/extraction.py", ("def apply(", "self.group_select")),
        },
    },
    "aime_process_results": {
        "callable": "lm_eval.tasks.aime.utils:process_results",
        "task": "lm_eval/tasks/aime/aime.yaml",
        "headline": "true",
        "receipts": {
            "F068": ("lm_eval/tasks/aime/aime.yaml", ("process_results: !function utils.process_results", "max_gen_toks: 32768")),
            "F069": ("lm_eval/tasks/aime/utils.py", ("def process_results", 'return {"exact_match": retval}')),
        },
    },
    "gsm8k_last_number": {
        "callable": "opencompass.datasets.gsm8k:gsm8k_postprocess + Gsm8kEvaluator.score",
        "task": "configs/datasets/gsm8k/gsm8k_gen_1d7fe4.py",
        "headline": "true",
        "receipts": {
            "F066": ("opencompass/configs/datasets/gsm8k/gsm8k_gen_1d7fe4.py", ("Gsm8kEvaluator", "gsm8k_postprocess")),
        },
    },
    "math_chain_of_thought": {
        "callable": "helm.benchmark.scenarios.math_scenario:get_answer + is_equiv",
        "task": "src/helm/benchmark/run_specs/lite_run_specs.py MATH CoT",
        "headline": "true",
        "receipts": {
            "F056": ("src/helm/benchmark/run_specs/lite_run_specs.py", ("def get_math_spec", "math_chain_of_thought")),
            "F058": ("src/helm/benchmark/scenarios/math_scenario.py", ("def get_answer", "def is_equiv")),
        },
    },
    "gsm8k_numeric_match": {
        "callable": "inspect_ai.scorer:match(numeric=True)",
        "task": "inspect_evals/gsm8k",
        "headline": "true",
        "receipts": {
            "F064": ("src/inspect_evals/gsm8k/gsm8k.py", ('path="openai/gsm8k"', "scorer=match(numeric=True)")),
        },
    },
    "aime_last_line_numeric": {
        "callable": "inspect_evals.utils.aime_common:aime_scorer",
        "task": "inspect_evals/aime2026",
        "headline": "true",
        "receipts": {
            "F019": ("src/inspect_evals/aime2026/aime2026.py", ("def aime2026", "aime_scorer()")),
            "F020": ("src/inspect_evals/utils/aime_common.py", ("def aime_scorer", "match(numeric=True)")),
        },
    },
    "mgsm_answer_prefix": {
        "callable": "mgsm_eval:parse_answer + score_mgsm",
        "task": "mgsm_eval English Answer: prefix",
        "headline": "true",
        "receipts": {
            "F060": ("mgsm_eval.py", ("parse_answer(response_text, answer_prefix)", "score_mgsm(correct_answer, extracted_answer)")),
        },
    },
    "math_extractive_match": {
        "callable": "lighteval.metrics.metrics:Metrics.expr_gold_metric.value.compute_sample + lighteval.metrics.utils.extractive_match_utils:extract_target_from_pred",
        "task": "src/lighteval/tasks/tasks/gsm8k.py Metrics.expr_gold_metric",
        "headline": "true",
        "receipts": {
            "F044": ("src/lighteval/tasks/tasks/gsm8k.py", ('name="gsm8k"', "Metrics.expr_gold_metric")),
            "F071": ("src/lighteval/metrics/utils/extractive_match_utils.py", ("def extract_target_from_pred", 'fallback_mode: Literal["no_fallback", "first_match"]', 'extraction_mode: Literal["first_match", "any_match"]')),
        },
    },
    "aime_last50": {
        "callable": "livebench.process_results.math.math_competitions.utils:aime_process_results",
        "task": "gen_ground_truth_judgment.py AIME dispatch",
        "headline": "true",
        "receipts": {
            "F031": ("livebench/process_results/math/math_competitions/utils.py", ("def aime_process_results", "llm_answer[-50:]")),
            "F070": ("livebench/gen_ground_truth_judgment.py", ('splits[0] == "aime"', "aime_process_results")),
        },
    },
    "olympiad_expression": {
        "callable": "livebench.process_results.math.olympiad.utils:extract_expression_completions_from_generation + proof_rearrangement_process_results",
        "task": "LiveBench IMO/USAMO-only olympiad dispatch",
        "headline": "false",
        "non_headline_status": "wrong_task_dispatch",
        "receipts": {
            "F067": ("livebench/process_results/math/olympiad/utils.py", ("def extract_expression_completions_from_generation", "def proof_rearrangement_process_results")),
            "F070": ("livebench/gen_ground_truth_judgment.py", ('splits[0] in ["imo", "usamo"]', "proof_rearrangement_process_results")),
        },
    },
    "default_parse_verify": {
        "callable": "math_verify:parse + verify",
        "task": "generic public utility; no task registration executed",
        "headline": "false",
        "non_headline_status": "generic_utility_only",
        "receipts": {
            "F034": ("src/math_verify/parser.py", ("def parse(", "LatexExtractionConfig()", "ExprExtractionConfig()")),
            "F035": ("src/math_verify/parser.py", ("get_extraction_regexes", "extract_target_from_pred")),
            "F036": ("src/math_verify/grader.py", ("def verify(", "target expression matches the gold expression")),
        },
    },
    "competition_extract_and_grade": {
        "callable": "matharena.grader:extract_and_grade",
        "task": "dataset-matched AIME/BRUMO/HMMT configs, strict_parsing=false",
        "headline": "true",
        "receipts": {
            "F039": ("src/matharena/grader.py", ("def extract_and_grade", 'messages[-1]["content"]')),
            "F043": ("configs/competitions/aime/aime_2025.yaml", ("strict_parsing: false", "dataset_path: MathArena/aime_2025")),
        },
    },
}


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "ecosystem_audit_runner", AUDIT / "run_executable_audit.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RoundTwoContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner = _load_runner()
        with gzip.open(
            ROOT / "observational" / "real_truncated_fixtures.jsonl.gz",
            "rt",
            encoding="utf-8",
        ) as handle:
            cls.real_rows = [json.loads(line) for line in handle]

    def test_one_frozen_integer_gold_control_schema(self):
        controls = [
            row
            for row in self.real_rows
            if row["kind"] == "control_correct"
            and self.runner.control_gold_eligible(row)
        ]
        unique_items = {
            (row["dataset"], row["problem_idx"], str(row["gold_answer"]))
            for row in controls
        }
        self.assertEqual(len(controls), 28)
        self.assertEqual(len(unique_items), 4)

    def test_pre_truncation_answer_marker_strata_are_frozen(self):
        truncated = [row for row in self.real_rows if row["kind"] == "truncated"]
        counts = {
            True: sum(
                self.runner.pre_truncation_answer_present(row["text"])
                for row in truncated
            ),
            False: sum(
                not self.runner.pre_truncation_answer_present(row["text"])
                for row in truncated
            ),
        }
        self.assertEqual(counts, {True: 26, False: 105})

    def test_metric_contract_never_blends_real_and_synthetic(self):
        with (AUDIT / "pipeline_metrics.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertNotIn("combined", {row["stratum"] for row in rows})
        self.assertNotIn("fabrication_pct", {row["metric"] for row in rows})

    def test_report_is_real_first_and_labels_constructed_probes(self):
        report = (AUDIT / "results_table.md").read_text(encoding="utf-8")
        real = report.index("## Real truncated generations")
        synthetic = report.index("## Constructed synthetic probes")
        self.assertLess(real, synthetic)
        self.assertIn("insufficient_power", report)
        self.assertIn("aime_last50", report)
        self.assertNotIn("91.216216%", report)

    def _assert_dispatch_contract(self, pipelines):
        receipts = {
            row["finding_id"]: row
            for row in json.loads(
                (AUDIT / "receipt_index.json").read_text(encoding="utf-8")
            )["receipts"]
        }
        self.assertEqual(set(pipelines), set(DISPATCH_CONTRACTS))
        for pipeline_id, pipeline in pipelines.items():
            contract = DISPATCH_CONTRACTS[pipeline_id]
            self.assertEqual(pipeline["callable"], contract["callable"], pipeline_id)
            self.assertEqual(pipeline["task_or_config"], contract["task"], pipeline_id)
            self.assertEqual(pipeline["headline_eligible"], contract["headline"], pipeline_id)
            self.assertEqual(
                pipeline.get("non_headline_status", ""),
                contract.get("non_headline_status", ""),
                pipeline_id,
            )
            declared = {
                item.strip()
                for item in pipeline["dispatch_receipt_ids"].split(";")
                if item.strip()
            }
            self.assertEqual(declared, set(contract["receipts"]), pipeline_id)
            for finding_id, (expected_path, quote_tokens) in contract["receipts"].items():
                receipt = receipts[finding_id]
                self.assertEqual(receipt["path"], expected_path, finding_id)
                for token in quote_tokens:
                    self.assertIn(token, receipt["quote"], finding_id)

    def test_every_executed_pipeline_has_semantically_exact_dispatch_receipts(self):
        with (AUDIT / "applicability.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            pipelines = {
                row["pipeline_id"]: row for row in csv.DictReader(handle)
            }
        self._assert_dispatch_contract(pipelines)

    def test_unrelated_byte_valid_receipt_fails_dispatch_contract(self):
        with (AUDIT / "applicability.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            pipelines = {
                row["pipeline_id"]: dict(row) for row in csv.DictReader(handle)
            }
        pipelines["math_extractive_match"]["dispatch_receipt_ids"] = "F068"
        with self.assertRaises(AssertionError):
            self._assert_dispatch_contract(pipelines)


if __name__ == "__main__":
    unittest.main()
