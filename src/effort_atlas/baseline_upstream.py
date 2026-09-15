"""Pinned upstream rendering and grading for the exploratory baseline.

No provider client or tokenizer service is constructed. HELM builds the prompts;
the explicit adaptation disables its automatic prompt truncation. Input/context
admission still requires separate route evidence before collection.
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
import hashlib
import importlib
import json
from pathlib import Path
import random
import sys
import zipfile

from . import ROOT
from .benchmark_provenance import load_manifest, validate_manifest, verify_download_root
from .graders import extract_final_answer
from .wrapper import render

LOCK = ROOT / "reap/inkling_baseline/upstream_sources.json"
WRAPPER_VERSION = "helm-baseline-v1-bfa36d33-final-answer"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_installed_helm(manifest: dict) -> None:
    import helm
    package = Path(helm.__file__).parent
    for entry in manifest["entries"]:
        if entry.get("installed_helm_path"):
            if _digest(package / entry["installed_helm_path"]) != entry["sha256"]:
                raise ImportError("installed HELM does not match the pinned renderer source")


def verify_upstream(root: Path) -> dict:
    manifest = load_manifest(LOCK)
    validate_manifest(manifest)
    verify_download_root(manifest, root)
    _check_installed_helm(manifest)
    # Extract only four hash-pinned English tables, never arbitrary ZIP members.
    with zipfile.ZipFile(root / "punkt_tab.zip") as archive:
        for spec in manifest["nltk_english_files"]:
            data = archive.read(spec["member"])
            if len(data) != spec["bytes"] or hashlib.sha256(data).hexdigest() != spec["sha256"]:
                raise ValueError("NLTK table differs from the pinned source")
            target = (root / spec["path"]).resolve()
            target.relative_to(root.resolve())
            if target.exists():
                if target.read_bytes() != data:
                    raise ValueError("refusing to overwrite a changed NLTK table")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as handle:
                    handle.write(data)
    return {"helm_revision": manifest["helm_revision"],
            "google_ifeval_revision": manifest["google_ifeval_revision"],
            "source_manifest_sha256": _digest(LOCK)}


@lru_cache(maxsize=1)
def _renderers():
    _check_installed_helm(load_manifest(LOCK))
    from helm.benchmark.run_specs import capabilities_run_specs as specs
    from helm.benchmark.adaptation.adapters.multiple_choice_joint_chain_of_thought_adapter import (
        MultipleChoiceJointChainOfThoughtAdapter,
    )
    from helm.benchmark.adaptation.adapters.generation_adapter import GenerationAdapter
    from helm.benchmark.adaptation.adapters.chat_adapter import ChatAdapter

    class PromptOnly:
        def __init__(self, adapter_spec):
            # Deliberately omit the model/window-service constructor. The
            # inherited formatter is used; no fallback formatter is supplied.
            self.adapter_spec = adapter_spec

        def _make_prompt_fit(self, prompt):
            # Scientific adaptation: preserve the complete source input rather
            # than letting HELM shorten it to a guessed model context window.
            return prompt

    class ChoicePrompt(PromptOnly, MultipleChoiceJointChainOfThoughtAdapter):
        pass

    class GenerationPrompt(PromptOnly, GenerationAdapter):
        pass

    class ChatPrompt(PromptOnly, ChatAdapter):
        pass

    return specs, ChoicePrompt, GenerationPrompt, ChatPrompt


def render_baseline(row: dict, *, seed: int):
    from helm.benchmark.scenarios.scenario import Input, Output, Reference, Instance
    specs, ChoicePrompt, GenerationPrompt, ChatPrompt = _renderers()
    # Reuse the existing validated option permutation and source metadata.
    base = render(row, seed=seed)
    dataset = row["dataset"]
    if dataset == "mmlu_pro":
        spec = specs.get_mmlu_pro_spec(row["meta"]["category"]).adapter_spec
    elif dataset == "gpqa_main":
        spec = specs.get_gpqa_spec("gpqa_main").adapter_spec
    elif dataset == "omni_math":
        spec = specs.get_omni_math_spec().adapter_spec
    elif dataset == "ifeval":
        # Preserve the source prompt verbatim, including any existing trailing
        # newline; HELM's default input suffix would append another newline.
        spec = replace(specs.get_ifeval_spec().adapter_spec, input_suffix="")
    elif dataset == "wildbench_v2":
        spec = specs.get_wildbench_spec("v2").adapter_spec
    else:
        raise ValueError("unsupported baseline dataset")
    if base.grading_kind == "gold_choice":
        original = 'Format your response as follows: "The correct answer is (insert answer here)".'
        if spec.global_suffix.count(original) != 1:
            raise ValueError("upstream multiple-choice answer instruction changed")
        spec = replace(spec, global_suffix=spec.global_suffix.replace(
            original, "End your response with exactly one line of the form:\nFinal answer: <letter>"))
    elif base.grading_kind == "gold_answer":
        original = "Wrap the final answer with the \\boxed{} command."
        if spec.instructions.count(original) != 1:
            raise ValueError("upstream math answer instruction changed")
        spec = replace(spec, instructions=spec.instructions.replace(
            original, "End your response with exactly one line of the form:\nFinal answer: <answer>"))
    spec = replace(spec, max_tokens=32768, num_outputs=1, max_train_instances=0)
    if base.grading_kind == "judge_checklist":
        instance = Instance(input=Input(messages=base.messages), references=[], split="test")
        request = ChatPrompt(spec).generate_requests(instance, 0, [])[0].request
        messages, prompt = request.messages, None
        from .wrapper import canonical_messages_sha256
        digest = canonical_messages_sha256(messages)
    else:
        references = [Reference(output=Output(text=row["choices"][i]), tags=[])
                      for i in (base.choice_permutation or [])]
        instance = Instance(input=Input(text=row["prompt_text"]), references=references, split="test")
        adapter = ChoicePrompt(spec) if base.grading_kind == "gold_choice" else GenerationPrompt(spec)
        built = adapter.construct_prompt([], instance, include_output=False, reference_index=None)
        if built.truncated or built.num_train_instances:
            raise ValueError("baseline prompt unexpectedly truncated or contains demonstrations")
        prompt, messages = built.text, None
        digest = hashlib.sha256(prompt.encode()).hexdigest()
    return replace(base, prompt=prompt, messages=messages, prompt_sha256=digest,
                   wrapper_version=WRAPPER_VERSION), float(spec.temperature)


@lru_cache(maxsize=1)
def _ifeval(root: Path):
    verify_upstream(root)
    sys.path.insert(0, str(root.resolve()))
    module = importlib.import_module("instruction_following_eval.evaluation_main")
    if Path(module.__file__).resolve() != (root / "instruction_following_eval/evaluation_main.py").resolve():
        raise ImportError("IFEval was imported from an unpinned location")
    import nltk
    nltk.data.path.insert(0, str(root.resolve() / "nltk_data"))
    return module


def score_baseline(row: dict, rendered, text: str, *, upstream_root: Path) -> dict:
    kind = row["grading"]["kind"]
    if kind == "gold_choice":
        if rendered.gold_letter is None:
            return {"grading_status": "gold_missing", "correct": None}
        extracted = extract_final_answer(text)
        letter = extracted.upper() if extracted is not None else None
        valid = letter is not None and len(letter) == 1 and letter in "ABCDEFGHIJ"[:len(row["choices"])]
        return {"grading_status": "graded", "metric": "choice_accuracy",
                "extracted_answer_present": extracted is not None, "extracted_answer": extracted,
                "answer_format_valid": valid, "correct": valid and letter == rendered.gold_letter}
    if kind == "gold_answer":
        extracted = extract_final_answer(text)
        return {"grading_status": "pending_official_judge", "correct": None,
                "extracted_answer_present": extracted is not None, "extracted_answer": extracted}
    if kind == "judge_checklist":
        return {"grading_status": "quality_judging_deferred", "correct": None}
    if kind != "verifiable_instructions":
        raise ValueError("unsupported grading kind")
    try:
        evaluator = _ifeval(upstream_root)
        ids, kwargs = row["grading"]["instruction_id_list"], row["grading"]["kwargs"]
        if not ids or len(ids) != len(kwargs):
            raise ValueError("invalid IFEval metadata")
        item = evaluator.InputExample(key=row["source_row_index"], instruction_id_list=ids,
                                      prompt=row["prompt_text"], kwargs=kwargs)
        # Upstream's language detection and unspecified checker parameters can
        # use randomness. Pin it without changing the model's sampling state.
        from langdetect import DetectorFactory
        DetectorFactory.seed = 20260830
        state = random.getstate()
        try:
            random.seed(20260830)
            result = evaluator.test_instruction_following_strict(item, {item.prompt: text})
        finally:
            random.setstate(state)
        return {"grading_status": "graded", "metric": "ifeval_prompt_strict_accuracy",
                "correct": result.follow_all_instructions,
                "instruction_results": result.follow_instruction_list}
    except ImportError:
        return {"grading_status": "import_failed", "correct": None}
    except Exception as exc:
        # An upstream exception is a grading failure, never an incorrect answer.
        return {"grading_status": "grader_error", "correct": None, "error_class": type(exc).__name__}
