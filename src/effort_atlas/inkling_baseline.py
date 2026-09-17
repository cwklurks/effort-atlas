"""Prepare the exploratory Tinker baseline offline. This module has no live path.

The request plan is concrete and reviewable, but route/accounting evidence is
still required before a human launch. Private request bytes stay in results_pilot.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
import hashlib
import math
from pathlib import Path

from . import ROOT
from .confirmatory import sha256_json
from .pilot_integrity import load_selected_items

MODEL = "thinkingmachines/Inkling"
BASE_URL = "https://tinker.thinkingmachines.dev/services/tinker-prod/anthropic/api"
CAP = 32768
DATASETS = ("mmlu_pro", "gpqa_main", "ifeval", "wildbench_v2", "omni_math")
SELECTION = "capabilities/selections/selection_stratified200_seed20260830_v1.json"
BLOCKERS = (
    "Tinker organization access and credit eligibility for this endpoint are unverified",
    "Reasoning-inclusive cap and token accounting require route evidence",
    "Whole-stage billing reconciliation requires verified attribution and account evidence",
    "Dated prices and verified balance are missing; approved stage ceilings are conditional",
    "Independent review and host-bound human launch evidence remain required",
)


def client_options() -> dict:
    """Pinned options for offline SDK transport tests; does not create a client."""
    return {"base_url": BASE_URL, "timeout": 3600.0, "max_retries": 0}


def build_request(template: dict, effort: str) -> dict:
    """Anthropic SDK kwargs, with the documented Tinker effort extension."""
    if effort not in {"medium", "max"}:
        raise ValueError("baseline effort must be medium or max")
    if set(template) != {"model", "max_tokens", "temperature", "messages"}:
        raise ValueError("unexpected or missing baseline request fields")
    if template["model"] != MODEL or type(template["max_tokens"]) is not int or template["max_tokens"] != CAP:
        raise ValueError("baseline requires the pinned Inkling model and explicit 32768 cap")
    temperature = template["temperature"]
    if type(temperature) not in (float, int) or not math.isfinite(temperature) or not 0 <= temperature <= 1:
        raise ValueError("invalid benchmark temperature")
    messages = template["messages"]
    if (not isinstance(messages, list) or not messages
            or not isinstance(messages[-1], dict) or messages[-1].get("role") != "user"):
        raise ValueError("baseline messages must end with a user turn")
    for message in messages:
        if (not isinstance(message, dict) or set(message) != {"role", "content"}
                or message["role"] not in {"user", "assistant"}
                or not isinstance(message["content"], str) or not message["content"].strip()):
            raise ValueError("invalid baseline message")
    request = deepcopy(template)
    # Anthropic 1.4 removed its typed temperature argument. Tinker's compatible
    # endpoint still documents it, so preserve it in the serialized extra body.
    temperature = request.pop("temperature")
    return {**request, "extra_body": {"temperature": temperature, "output_config": {"effort": effort}}}


def parse_response(body: dict, *, cap: int) -> dict:
    """Keep native accounting and finish facts; never infer missing token counts.

    A reported max_tokens stop is recorded as such, not treated as empirical
    proof that the endpoint's cap includes reasoning. Only text blocks can be
    graded; thinking blocks remain a separate private field.
    """
    if not isinstance(body, dict) or not isinstance(body.get("id"), str) or not body["id"]:
        raise ValueError("response identity missing")
    if body.get("model") != MODEL or body.get("role") != "assistant" or body.get("type") != "message":
        raise ValueError("unexpected response identity or type")
    blocks = body.get("content")
    if not isinstance(blocks, list):
        raise ValueError("response content missing")
    text, thinking = [], []
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") not in {"text", "thinking"}:
            raise ValueError("unexpected response block; tools are not enabled")
        field = "text" if block["type"] == "text" else "thinking"
        if not isinstance(block.get(field), str):
            raise ValueError("malformed response block")
        (text if field == "text" else thinking).append(block[field])
    usage = body.get("usage")
    if usage is None:
        usage = {}
    if not isinstance(usage, dict):
        raise ValueError("malformed usage")
    for name in ("input_tokens", "output_tokens", "reasoning_tokens"):
        value = usage.get(name)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("malformed token usage")
    output = usage.get("output_tokens")
    if output is not None and output > cap:
        raise ValueError("reported output exceeded requested cap")
    stop = body.get("stop_reason")
    if stop is not None and not isinstance(stop, str):
        raise ValueError("malformed native stop reason")
    complete_usage = usage.get("input_tokens") is not None and output is not None
    return {
        "generation_id": body["id"], "native_stop_reason": stop,
        "cap_hit_reported": True if stop == "max_tokens" else False if stop == "end_turn" else None,
        "text": "".join(text), "thinking": "".join(thinking),
        "input_tokens_reported": usage.get("input_tokens"),
        "output_tokens_reported": output,
        "reasoning_tokens_reported": usage.get("reasoning_tokens"),
        "accounting_status": "usage_reported_unreconciled" if complete_usage else "usage_missing",
        "billed_cost_usd": None,
    }


def prepare(*, root: Path = ROOT, upstream_root: Path | None = None, mock: bool = False) -> dict:
    from .baseline_upstream import render_baseline, score_baseline, verify_upstream

    root = root.resolve()
    upstream_root = upstream_root or root / ".cache_pilot/inkling_baseline_upstream"
    upstream = verify_upstream(upstream_root)
    selection = json.loads((root / SELECTION).read_text())
    cfg = {"pilot": {"datasets": list(DATASETS)}}
    source_rows = load_selected_items(cfg, selection, cap_dir=root / "capabilities")
    if Counter(row["dataset"] for row in source_rows) != Counter({name: 200 for name in DATASETS}):
        raise ValueError("baseline requires exactly 200 verified items per dataset")
    private, public = [], []
    for row in source_rows:
        rendered, temperature = render_baseline(row, seed=20260830)
        messages = rendered.messages if rendered.messages is not None else [{"role": "user", "content": rendered.prompt}]
        template = {"model": MODEL, "max_tokens": CAP, "temperature": temperature, "messages": messages}
        medium, maximum = (build_request(template, effort) for effort in ("medium", "max"))
        if len(json.dumps(messages, ensure_ascii=False).encode()) > 60000:
            raise ValueError("rendered request exceeds the proposed input admission limit")
        private.append({"dataset": row["dataset"], "source_item_id": row["source_item_id"],
                        "source_row_index": row["source_row_index"], "template": template,
                        "choice_permutation": rendered.choice_permutation, "gold_letter": rendered.gold_letter})
        # No questions, answers, option maps or reasoning text in the public plan.
        public.append({"dataset": row["dataset"], "source_item_id": row["source_item_id"],
                       "source_row_index": row["source_row_index"], "wrapper_version": rendered.wrapper_version,
                       "source_prompt_sha256": row["prompt_sha256"], "temperature": temperature,
                       "medium_request_sha256": sha256_json(medium), "max_request_sha256": sha256_json(maximum)})
    private_jsonl = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in private)
    manifest = {
        "schema_version": "inkling-baseline-preparation-v1", "phase": "exploratory",
        "live_enabled": False, "launch_ready": False, "launch_blockers": list(BLOCKERS),
        "endpoint": BASE_URL, "model": MODEL, "max_tokens": CAP,
        "initial_effort": "medium", "conditional_second_effort": "max",
        "second_stage_rule": "same items and prompts; consider after zero medium cap stops, with complete valid accounting",
        "generation_retries": 0, "tools_enabled": False,
        "sdk": {"name": "anthropic", "version": "1.4.0", "options": client_options(),
                "http_client_follow_redirects": False, "http_client_trust_env": False},
        "input_admission_bytes": 60000, "input_token_allowance_verified": False,
        "tinker_credits_reported_usd": 5000, "credit_balance_verified": False,
        "approved_run_ceiling_usd": 500, "approved_stage_ceilings_usd": {"medium": 250, "max": 250},
        "accounting_policy_approved_on": "2026-09-07", "pricing_verified": False,
        "selection_sha256": selection["selection_sha256"], "upstream": upstream,
        "private_requests_sha256": hashlib.sha256(private_jsonl.encode()).hexdigest(),
        "implementation_sha256": {
            str(path): hashlib.sha256((root / path).read_bytes()).hexdigest()
            for path in (Path("src/effort_atlas/inkling_baseline.py"),
                         Path("src/effort_atlas/baseline_upstream.py"),
                         Path("src/effort_atlas/graders.py"),
                         Path("src/effort_atlas/wrapper.py"),
                         Path("reap/inkling_baseline/requirements.lock"))
        },
        "dataset_counts": dict(Counter(row["dataset"] for row in source_rows)), "items": public,
        "scope": "adapted HELM zero-shot templates; no automatic prompt truncation; not an exact HELM replication",
    }
    manifest["plan_sha256"] = sha256_json(manifest)
    out = root / "results_pilot/inkling_tinker_baseline/preparation" / manifest["plan_sha256"]
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    out.chmod(0o700)
    _write_once(out / "manifest.json", json.dumps(manifest, indent=2) + "\n")
    _write_once(out / "requests.private.jsonl", private_jsonl)
    if mock:
        synthetic = []
        for index, (row, item) in enumerate(zip(source_rows, private)):
            rendered, _ = render_baseline(row, seed=20260830)
            body = {"id": f"synthetic-{index}", "type": "message", "role": "assistant", "model": MODEL,
                    "stop_reason": "end_turn", "usage": {"input_tokens": 10, "output_tokens": 20},
                    "content": [{"type": "text", "text": "Final answer: A"}]}
            parsed = parse_response(body, cap=CAP)
            grade = score_baseline(row, rendered, parsed["text"], upstream_root=upstream_root)
            synthetic.append({"synthetic": True, "phase": "mock_only", "dataset": item["dataset"],
                              "source_item_id": item["source_item_id"], "effort": "medium", "requested_cap": CAP,
                              **parsed, "grade": grade})
        _write_once(out / "mock_responses.private.jsonl", "".join(json.dumps(row) + "\n" for row in synthetic))
        statuses = dict(Counter(row["grade"]["grading_status"] for row in synthetic))
        summary = {"synthetic": True, "model_calls": 0, "rows": len(synthetic), "grading_status_counts": statuses}
        _write_once(out / "mock_summary.json", json.dumps(summary, indent=2) + "\n")
        if statuses.get("grader_error") or statuses.get("import_failed"):
            raise ValueError("mock encountered an upstream grader failure; see private mock output")
    return {"plan_sha256": manifest["plan_sha256"], "directory": str(out), "items": len(private),
            "launch_ready": False, "model_calls": 0, "mock": mock}


def _write_once(path: Path, text: str) -> None:
    data = text.encode()
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError("refusing to replace an existing preparation artifact with different bytes")
        return
    with path.open("xb") as handle:
        path.chmod(0o600)
        handle.write(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="default: prepare request bytes and a content-free plan")
    parser.add_argument("--mock", action="store_true", help="also exercise scoring with clearly synthetic responses")
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(mock=args.mock), indent=2))
        return 0
    except (ImportError, OSError, ValueError) as exc:
        # Exception text from an upstream grader can contain source text.
        print(json.dumps({"status": "preparation_refused", "error_class": type(exc).__name__, "model_calls": 0}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
