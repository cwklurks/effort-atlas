#!/usr/bin/env python3
"""Independently recompute round-2 headlines from committed rows only."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "ecosystem_audit"
OUTPUT = AUDIT / "independent_recomputation.json"
MARKER = re.compile(r"\\boxed\{.+?\}", re.DOTALL)
INTEGER = re.compile(r"^[+-]?\d+$")


def table(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def ratio(rows: list[dict[str, str]], field: str) -> dict[str, int | str]:
    measured = [row for row in rows if row[field] != ""]
    if not measured:
        return {"status": "not_measured", "numerator": 0, "denominator": 0}
    return {
        "status": "ok",
        "numerator": sum(row[field] == "true" for row in measured),
        "denominator": len(measured),
    }


def recompute() -> dict:
    with gzip.open(
        ROOT / "observational" / "real_truncated_fixtures.jsonl.gz",
        "rt",
        encoding="utf-8",
    ) as handle:
        corpus = [json.loads(line) for line in handle]
    truncated = [row for row in corpus if row["kind"] == "truncated"]
    controls = [
        row
        for row in corpus
        if row["kind"] == "control_correct"
        and INTEGER.fullmatch(str(row["gold_answer"]).strip())
    ]
    results = table(AUDIT / "fixture_results.csv")
    metric_rows = table(AUDIT / "pipeline_metrics.csv")
    assert "combined" not in {row["stratum"] for row in metric_rows}
    assert "fabrication_pct" not in {row["metric"] for row in metric_rows}
    statuses = {
        row["pipeline_id"]: row["pipeline_status"] for row in metric_rows
    }
    pipelines = []
    answer_sets: dict[frozenset[str], list[str]] = defaultdict(list)
    for pipeline_id in sorted({row["pipeline_id"] for row in results}):
        rows = [row for row in results if row["pipeline_id"] == pipeline_id]
        real = [
            row
            for row in rows
            if row["stratum"] == "real_truncated" and row["adapter_status"] == "ok"
        ]
        synthetic = [
            row
            for row in rows
            if row["stratum"] == "synthetic_truncated"
            and row["adapter_status"] == "ok"
        ]
        selected_controls = [row for row in rows if row["control_gold_eligible"] == "true"]
        returned_ids = frozenset(
            row["fixture_id"] for row in real if row["answer_returned"] == "true"
        )
        if real and any(row["answer_returned"] != "" for row in real):
            answer_sets[returned_ids].append(pipeline_id)
        pipelines.append(
            {
                "pipeline_id": pipeline_id,
                "pipeline_status": statuses[pipeline_id],
                "real": {
                    "n": len(real),
                    "n_eff_dataset_problem": len(
                        {(row["dataset"], row["problem_idx"]) for row in real}
                    ),
                    "empty_text": sum(row["text_empty"] == "true" for row in real),
                    "answer_returned": ratio(real, "answer_returned"),
                    "answer_is_numeric_among_returned": ratio(
                        [row for row in real if row["answer_returned"] == "true"],
                        "answer_is_numeric",
                    ),
                    "accidental_correct": ratio(real, "native_correct"),
                    "marker_present": ratio(
                        [
                            row
                            for row in real
                            if row["pre_truncation_answer_present"] == "true"
                        ],
                        "answer_returned",
                    ),
                    "marker_absent": ratio(
                        [
                            row
                            for row in real
                            if row["pre_truncation_answer_present"] == "false"
                        ],
                        "answer_returned",
                    ),
                },
                "synthetic_constructed": {
                    "n": len(synthetic),
                    "answer_returned": ratio(synthetic, "answer_returned"),
                    "accidental_correct": ratio(synthetic, "native_correct"),
                },
                "uniform_controls": ratio(selected_controls, "native_correct"),
            }
        )
    by_pipeline = {row["pipeline_id"]: row for row in pipelines}
    assert len(truncated) == 131
    assert sum(bool(MARKER.search(row["text"])) for row in truncated) == 26
    assert len(controls) == 28
    assert len({(row["dataset"], row["problem_idx"], row["gold_answer"]) for row in controls}) == 4
    assert by_pipeline["gsm8k_flexible_extract"]["real"]["answer_returned"] == {
        "status": "ok", "numerator": 111, "denominator": 131
    }
    assert by_pipeline["gsm8k_flexible_extract"]["real"]["answer_is_numeric_among_returned"] == {
        "status": "ok", "numerator": 105, "denominator": 111
    }
    lm_eval_non_numeric = Counter(
        row["extracted_answer"]
        for row in results
        if row["pipeline_id"] == "gsm8k_flexible_extract"
        and row["stratum"] == "real_truncated"
        and row["answer_returned"] == "true"
        and row["answer_is_numeric"] == "false"
    )
    assert lm_eval_non_numeric == {"$$": 3, "$.": 2, "$,": 1}
    assert by_pipeline["math_chain_of_thought"]["real"]["answer_returned"]["numerator"] == 23
    for pipeline_id in ("math_extractive_match", "default_parse_verify", "competition_extract_and_grade"):
        assert by_pipeline[pipeline_id]["real"]["answer_returned"] == {
            "status": "ok", "numerator": 111, "denominator": 131
        }
    inspect = by_pipeline["aime_last_line_numeric"]
    assert inspect["pipeline_status"] == "insufficient_power"
    assert inspect["real"]["n"] == 7 and inspect["real"]["empty_text"] == 5
    identical = [
        {"pipelines": sorted(ids), "returned_fixture_count": len(answer_ids)}
        for answer_ids, ids in answer_sets.items()
        if len(ids) > 1
    ]
    return {
        "corpus": {
            "frozen_integer_controls": 28,
            "frozen_integer_controls_n_eff": 4,
            "real_truncated": 131,
            "real_truncated_pre_answer": 26,
            "real_truncated_without_pre_answer": 105,
        },
        "generated_at": "2026-08-08T00:00:00+00:00",
        "identical_real_answer_returned_fixture_sets": sorted(
            identical, key=lambda row: row["pipelines"]
        ),
        "lm_eval_non_numeric_returned_values": dict(sorted(lm_eval_non_numeric.items())),
        "method": "standard-library recomputation from the compressed corpus plus committed fixture_results.csv; does not import run_executable_audit or any adapter",
        "pipelines": pipelines,
        "schema_version": 1,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(recompute(), indent=2, sort_keys=True) + "\n"
    if args.write:
        OUTPUT.write_text(rendered, encoding="utf-8")
        print(f"wrote {OUTPUT.relative_to(ROOT)}")
    else:
        assert OUTPUT.read_text(encoding="utf-8") == rendered
        print("independent recomputation matches committed evidence")


if __name__ == "__main__":
    main()
