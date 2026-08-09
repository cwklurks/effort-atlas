"""Locked MathArena adapter using its full competition grading callable."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

from common import main, serialize


_CONFIG_PATHS = {
    "aime_2026_outputs": "configs/competitions/aime/aime_2026.yaml",
    "brumo_2025_outputs": "configs/competitions/brumo/brumo_2025.yaml",
    "hmmt_feb_2025_outputs": "configs/competitions/hmmt/hmmt_feb_2025.yaml",
    "hmmt_feb_2026_outputs": "configs/competitions/hmmt/hmmt_feb_2026.yaml",
}
_SYNTHETIC_CONFIG = "configs/competitions/aime/aime_2026.yaml"


def importer(repo: Path):
    source = (repo / "src").resolve()
    sys.path.insert(0, str(source))
    from matharena import grader

    imported_from = Path(grader.__file__).resolve()
    if source not in imported_from.parents:
        raise ImportError(f"matharena imported outside locked checkout: {imported_from}")

    configs = {}
    for dataset, relative_path in _CONFIG_PATHS.items():
        with (repo / relative_path).open(encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        if config.get("strict_parsing") is not False:
            raise ValueError(f"locked competition config is not strict_parsing=false: {relative_path}")
        configs[dataset] = config
    with (repo / _SYNTHETIC_CONFIG).open(encoding="utf-8") as handle:
        synthetic_config = yaml.safe_load(handle)
    if synthetic_config.get("strict_parsing") is not False:
        raise ValueError(f"locked competition config is not strict_parsing=false: {_SYNTHETIC_CONFIG}")
    return grader.extract_and_grade, configs, synthetic_config


def function_builder(imported):
    extract_and_grade, configs, synthetic_config = imported

    def evaluate(row):
        is_synthetic = row.get("stratum") == "synthetic_truncated" or str(row.get("fixture_id", "")).startswith("synthetic-")
        if is_synthetic:
            if re.fullmatch(r"\s*-?\d+\s*", str(row["gold_answer"])) is None:
                return {
                    "adapter_status": "not_applicable",
                    "status_reason": "synthetic gold is not an integer",
                }
            competition_config = synthetic_config
        else:
            dataset = row.get("dataset")
            if dataset not in configs:
                return {
                    "adapter_status": "not_applicable",
                    "status_reason": f"no frozen competition config mapping for dataset {dataset!r}",
                }
            competition_config = configs[dataset]

        output_tokens = row.get("output_tokens", 0)
        if output_tokens is None:
            output_tokens = 0
        answer, correct, _warning = extract_and_grade(
            [{"role": "assistant", "content": row["text"]}],
            int(output_tokens),
            str(row["gold_answer"]),
            competition_config,
        )
        return {
            "extracted_answer": serialize(answer),
            "native_correct": bool(correct),
        }

    return evaluate


if __name__ == "__main__":
    main(importer, function_builder)
