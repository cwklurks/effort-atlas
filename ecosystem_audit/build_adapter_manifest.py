#!/usr/bin/env python3
"""Regenerate deterministic round-2 adapter/environment provenance."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "ecosystem_audit"
CREATED_AT = "2026-08-08T00:00:00+00:00"


ENVIRONMENTS = {
    "lm-evaluation-harness": (
        "ecosystem_audit/_envs/lm_eval/bin/python",
        "ecosystem_audit/environments/lm_eval.requirements.txt",
        "uv venv --python 3.12.8 ecosystem_audit/_envs/lm_eval && uv pip install --python ecosystem_audit/_envs/lm_eval/bin/python -r ecosystem_audit/environments/lm_eval.requirements.txt && uv pip install --python ecosystem_audit/_envs/lm_eval/bin/python --no-deps -e ecosystem_audit/_repos/lm-evaluation-harness",
    ),
    "opencompass": (
        "ecosystem_audit/_envs/opencompass/bin/python",
        "ecosystem_audit/environments/opencompass.requirements.txt",
        "uv venv --python 3.12.8 ecosystem_audit/_envs/opencompass && uv pip install --python ecosystem_audit/_envs/opencompass/bin/python -r ecosystem_audit/environments/opencompass.requirements.txt && uv pip install --python ecosystem_audit/_envs/opencompass/bin/python --no-deps -e ecosystem_audit/_repos/opencompass",
    ),
    "helm": (
        "ecosystem_audit/_envs/helm/bin/python",
        "ecosystem_audit/environments/helm.requirements.txt",
        "uv venv --python 3.12.8 ecosystem_audit/_envs/helm && uv pip install --python ecosystem_audit/_envs/helm/bin/python -r ecosystem_audit/environments/helm.requirements.txt && uv pip install --python ecosystem_audit/_envs/helm/bin/python --no-deps -e ecosystem_audit/_repos/helm",
    ),
    "inspect_ai": (
        "ecosystem_audit/_envs/inspect/bin/python",
        "ecosystem_audit/environments/inspect.requirements.txt",
        "uv venv --python 3.12.8 ecosystem_audit/_envs/inspect && uv pip install --python ecosystem_audit/_envs/inspect/bin/python -r ecosystem_audit/environments/inspect.requirements.txt && uv pip install --python ecosystem_audit/_envs/inspect/bin/python --no-deps -e ecosystem_audit/_repos/inspect_ai -e ecosystem_audit/_repos/inspect_evals",
    ),
    "inspect_evals": (
        "ecosystem_audit/_envs/inspect/bin/python",
        "ecosystem_audit/environments/inspect.requirements.txt",
        "uv venv --python 3.12.8 ecosystem_audit/_envs/inspect && uv pip install --python ecosystem_audit/_envs/inspect/bin/python -r ecosystem_audit/environments/inspect.requirements.txt && uv pip install --python ecosystem_audit/_envs/inspect/bin/python --no-deps -e ecosystem_audit/_repos/inspect_ai -e ecosystem_audit/_repos/inspect_evals",
    ),
    "simple-evals": (
        "ecosystem_audit/_envs/simple/bin/python",
        "ecosystem_audit/environments/simple.requirements.txt",
        "uv venv --python 3.12.8 ecosystem_audit/_envs/simple && uv pip install --python ecosystem_audit/_envs/simple/bin/python -r ecosystem_audit/environments/simple.requirements.txt",
    ),
    "lighteval": (
        "ecosystem_audit/_envs/lighteval/bin/python",
        "ecosystem_audit/environments/lighteval.requirements.txt",
        "uv venv --python 3.12.8 ecosystem_audit/_envs/lighteval && uv pip install --python ecosystem_audit/_envs/lighteval/bin/python -r ecosystem_audit/environments/lighteval.requirements.txt && uv pip install --python ecosystem_audit/_envs/lighteval/bin/python --no-deps -e ecosystem_audit/_repos/lighteval",
    ),
    "livebench": (
        "ecosystem_audit/_envs/livebench/bin/python",
        "ecosystem_audit/environments/livebench.requirements.txt",
        "uv venv --python 3.12.8 ecosystem_audit/_envs/livebench",
    ),
    "math-verify": (
        "ecosystem_audit/_envs/math_verify/bin/python",
        "ecosystem_audit/environments/math_verify.requirements.txt",
        "uv venv --python 3.12.8 ecosystem_audit/_envs/math_verify && uv pip install --python ecosystem_audit/_envs/math_verify/bin/python -r ecosystem_audit/environments/math_verify.requirements.txt && uv pip install --python ecosystem_audit/_envs/math_verify/bin/python --no-deps -e ecosystem_audit/_repos/math-verify",
    ),
    "matharena": (
        "ecosystem_audit/_envs/matharena/bin/python",
        "ecosystem_audit/environments/matharena.requirements.txt",
        "uv venv --python 3.12.8 ecosystem_audit/_envs/matharena && uv pip install --python ecosystem_audit/_envs/matharena/bin/python -r ecosystem_audit/environments/matharena.requirements.txt",
    ),
}


def table(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    configs = table(AUDIT / "applicability.csv")
    results = table(AUDIT / "fixture_results.csv")
    metrics = table(AUDIT / "pipeline_metrics.csv")
    locks = {
        row["name"]: row
        for row in json.loads((AUDIT / "repos.lock.json").read_text())["repositories"]
    }
    receipts = {
        row["finding_id"]: row
        for row in json.loads((AUDIT / "receipt_index.json").read_text())["receipts"]
    }
    pipelines = []
    for config in configs:
        target = config["target"]
        pipeline_id = config["pipeline_id"]
        interpreter, lock_file, install_command = ENVIRONMENTS[target]
        lock_path = ROOT / lock_file
        subset = [row for row in results if row["pipeline_id"] == pipeline_id]
        status = next(
            row["pipeline_status"]
            for row in metrics
            if row["pipeline_id"] == pipeline_id
        )
        receipt_ids = [
            item.strip()
            for item in config["dispatch_receipt_ids"].split(";")
            if item.strip()
        ]
        pipelines.append(
            {
                "adapter_file": config["adapter_file"],
                "adapter_status_counts": dict(
                    sorted(Counter(row["adapter_status"] for row in subset).items())
                ),
                "applicability": config["inclusion_rule"],
                "callable": config["callable"],
                "dispatch_receipt_ids": receipt_ids,
                "environment": {
                    "install_command": install_command,
                    "interpreter": interpreter,
                    "lock_file": lock_file,
                    "lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
                    "python": "3.12.8",
                },
                "headline_eligible": config["headline_eligible"] == "true",
                "nonsemantic_marshaling": config["fixture_schema"],
                "pipeline_id": pipeline_id,
                "repository": locks[target]["repository"],
                "resource_ceiling": config["resource_ceiling"],
                "sha": locks[target]["sha"],
                "source_receipts": [
                    {
                        "finding_id": finding_id,
                        "permalink": receipts[finding_id]["permalink"],
                    }
                    for finding_id in receipt_ids
                ],
                "status": status,
                "status_reasons": sorted(
                    {
                        row["status_reason"]
                        for row in subset
                        if row["status_reason"]
                    }
                ),
                "target": target,
                "task_or_config": config["task_or_config"],
                "timeout_seconds": int(config["timeout_seconds"]),
                "timing": "per-fixture wall duration captured in ephemeral .timings.jsonl and excluded from deterministic committed outputs",
            }
        )
    output = {
        "created_at": CREATED_AT,
        "no_model_calls": True,
        "pipelines": pipelines,
        "schema_version": 2,
    }
    (AUDIT / "adapter_manifest.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    execution = {
        "pipelines": [
            {
                "adapter_status_counts": pipeline["adapter_status_counts"],
                "command": (
                    f"{pipeline['environment']['interpreter']} "
                    f"ecosystem_audit/adapters/{pipeline['adapter_file']} "
                    "--input <canonical-fixtures.jsonl> --output <results.jsonl> "
                    f"--repo ecosystem_audit/_repos/{pipeline['target']}"
                ),
                "pipeline_id": pipeline["pipeline_id"],
                "status_reasons": pipeline["status_reasons"],
                "target": pipeline["target"],
            }
            for pipeline in pipelines
        ],
        "schema_version": 2,
    }
    (AUDIT / "execution_log.json").write_text(
        json.dumps(execution, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    reproduction_path = AUDIT / "reproduction_manifest.json"
    reproduction = json.loads(reproduction_path.read_text(encoding="utf-8"))
    reproduction["adapter_environments"] = {
        target: {
            "install_command": values[2],
            "interpreter": values[0],
            "lock_file": values[1],
            "lock_sha256": hashlib.sha256((ROOT / values[1]).read_bytes()).hexdigest(),
            "python": "3.12.8",
        }
        for target, values in sorted(ENVIRONMENTS.items())
    }
    reproduction["schema_version"] = 2
    reproduction_path.write_text(
        json.dumps(reproduction, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote adapter_manifest.json, execution_log.json, and reproduction_manifest.json for {len(pipelines)} pipelines")


if __name__ == "__main__":
    main()
