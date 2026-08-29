"""Pilot wrapper v1: source-item-v1 row -> model-facing request.

The capabilities/ JSONLs store the *source item only* (no instructions, no
lettering, no terminator). This module is the separately versioned artifact
that turns a source item into what the model actually sees. Its version string
is recorded on every rendered item so a later wrapper never silently changes
what a stored length measurement meant.

Rules, by grading.kind:

  gold_choice              question + lettered options (A..J, source order);
                           GPQA options are shuffled with a recorded seeded
                           permutation because the source stores [correct,
                           wrong, wrong, wrong]. Strict terminator required.
  gold_answer              problem verbatim + strict terminator required.
  verifiable_instructions  IFEval prompt verbatim, NO terminator: the prompt's
                           own constraints (no commas, all lowercase, exact
                           word counts...) can be violated by an added line.
  judge_checklist          WildBench conversation_input passed as chat
                           messages in order (serialization rule v1). NO
                           terminator: open-ended, judge-graded.

This is a pilot-only format for a length study. It is not the confirmatory
wrapper and does not claim to reproduce HELM's adapter prompts. No network.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass

WRAPPER_VERSION = "pilot-wrapper-v1"
TERMINATOR = "Final answer:"
LETTERS = "ABCDEFGHIJ"
SHUFFLED_DATASETS = frozenset({"gpqa_main"})

_CHOICE_INSTRUCTION = (
    "Think as much as you need, then end your response with exactly one line "
    f"of the form:\n{TERMINATOR} <letter>"
)
_ANSWER_INSTRUCTION = (
    "Think as much as you need, then end your response with exactly one line "
    f"of the form:\n{TERMINATOR} <answer>"
)
_STRICT_TERMINATOR = re.compile(r"^\s*Final answer:\s*(\S.*)$")


@dataclass
class Rendered:
    dataset: str
    source_item_id: str
    source_row_index: int
    grading_kind: str
    wrapper_version: str
    prompt: str | None            # single-turn text, or None when messages used
    messages: list[dict] | None   # multi-turn chat messages (WildBench)
    prompt_sha256: str            # sha256 of prompt or of canonical messages
    source_prompt_sha256: str     # the source row's own prompt_sha256
    terminator_required: bool
    choice_permutation: list[int] | None  # rendered position -> source index
    gold_letter: str | None       # letter after permutation (None if withheld)
    restricted: bool

    def manifest_row(self) -> dict:
        """Content-free record for the committed rendered manifest."""
        d = asdict(self)
        d.pop("prompt")
        d.pop("messages")
        return d

    def request_text_for_estimate(self) -> str:
        if self.prompt is not None:
            return self.prompt
        return "\n".join(m["content"] for m in self.messages or [])


def canonical_messages_sha256(messages: list[dict]) -> str:
    blob = json.dumps(messages, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def strict_terminator_present(text: str) -> bool:
    """True iff the LAST non-empty line is 'Final answer: <something>'.

    Deliberately strict (safeguard 5): no last-number, no boxed, no lenient
    fallback. A terminator buried mid-response does not count.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    return bool(_STRICT_TERMINATOR.match(lines[-1]))


def render(row: dict, *, seed: int) -> Rendered:
    kind = row["grading"]["kind"]
    dataset = row["dataset"]
    item_id = row["source_item_id"]
    restricted = row.get("license_policy") == "restricted_no_plaintext"
    base = dict(
        dataset=dataset,
        source_item_id=item_id,
        source_row_index=row["source_row_index"],
        grading_kind=kind,
        wrapper_version=WRAPPER_VERSION,
        source_prompt_sha256=row["prompt_sha256"],
        restricted=restricted,
    )

    if kind == "gold_choice":
        if row.get("prompt_text") is None or row.get("choices") is None:
            raise ValueError(
                f"{dataset}:{item_id} has no prompt text; for GPQA load the "
                "restricted_local row (run capabilities/acquire.py)"
            )
        choices = list(row["choices"])
        if len(choices) > len(LETTERS):
            raise ValueError(f"{dataset}:{item_id} has {len(choices)} options > {len(LETTERS)}")
        perm = list(range(len(choices)))
        if dataset in SHUFFLED_DATASETS:
            random.Random(f"{seed}:{dataset}:{item_id}").shuffle(perm)
        gold_index = row["grading"].get("gold_index")
        gold_letter = None
        if gold_index is not None:
            gold_letter = LETTERS[perm.index(gold_index)]
        option_lines = "\n".join(
            f"{LETTERS[pos]}. {choices[src]}" for pos, src in enumerate(perm)
        )
        prompt = f"{row['prompt_text'].rstrip()}\n\nOptions:\n{option_lines}\n\n{_CHOICE_INSTRUCTION}"
        return Rendered(
            **base, prompt=prompt, messages=None, prompt_sha256=_sha(prompt),
            terminator_required=True, choice_permutation=perm, gold_letter=gold_letter,
        )

    if kind == "gold_answer":
        prompt = f"{row['prompt_text'].rstrip()}\n\n{_ANSWER_INSTRUCTION}"
        return Rendered(
            **base, prompt=prompt, messages=None, prompt_sha256=_sha(prompt),
            terminator_required=True, choice_permutation=None, gold_letter=None,
        )

    if kind == "verifiable_instructions":
        prompt = row["prompt_text"]
        return Rendered(
            **base, prompt=prompt, messages=None, prompt_sha256=_sha(prompt),
            terminator_required=False, choice_permutation=None, gold_letter=None,
        )

    if kind == "judge_checklist":
        turns = row.get("conversation_input") or []
        if not turns:
            raise ValueError(f"{dataset}:{item_id} has no conversation_input")
        messages = [{"role": t["role"], "content": t["content"]} for t in turns]
        if messages[-1]["role"] != "user":
            raise ValueError(f"{dataset}:{item_id} last turn is {messages[-1]['role']!r}, not user")
        return Rendered(
            **base, prompt=None, messages=messages,
            prompt_sha256=canonical_messages_sha256(messages),
            terminator_required=False, choice_permutation=None, gold_letter=None,
        )

    raise ValueError(f"unknown grading.kind {kind!r}")
