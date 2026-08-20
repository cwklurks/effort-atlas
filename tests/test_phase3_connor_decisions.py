from __future__ import annotations

import re
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSHEET = ROOT / "reap" / "12_PHASE3_CONNOR_DECISION_WORKSHEET_2026-08-10.md"

POSITION_CONTRACT = {
    "D01": "choose C with a proposed $2 Tinker smoke ceiling",
    "D02": "accept B",
    "D03": "keep a common planned 30-item HMMT-2026 subset",
    "D04": "accept standard Inkling and the recommended effort/cap scientific direction",
    "D05": "choose A",
    "D06": "include Terra in principle",
    "D07": "choose B as primary",
    "D08": "keep the recommended primary",
    "D09": "absolute error is sensible",
    "D10": "choose B for the first pass",
    "D11": "shared/strict looks right",
    "D12": "deterministic arm-aware scheduling is accepted",
    "D13": "reopen D13",
    "D14": "choose C",
    "D15": "conditional interest if the exact lane is genuinely ZDR and cheap",
}
SAFETY_COUNTERS = (
    "CONFIRMATORY_CALLS",
    "PAID_STUDY_GENERATION_CALLS",
    "SMOKE_CALLS",
    "PROVIDER_PROBE_CALLS",
    "DEEPSEEK_DEVELOPMENT_CALLS",
)


def _section(text: str, decision: str) -> str:
    section = text.split(f"### {decision} —", 1)[1]
    next_heading = re.search(r"^### D\d{2} —", section, flags=re.MULTILINE)
    return section[: next_heading.start()] if next_heading else section


def _position_contract_errors(text: str) -> list[str]:
    errors = []
    for decision, expected in POSITION_CONTRACT.items():
        section = " ".join(_section(text, decision).split())
        position = section.split("**Connor's position:**", 1)[1].split(
            "**What remains open:**", 1
        )[0]
        if expected not in position:
            errors.append(decision)
    d15 = " ".join(_section(text, "D15").split()).lower()
    if "it is not authorized yet" not in d15 or "authorized now" in d15:
        errors.append("D15_AUTHORIZATION")
    return errors


def _authorization_contract_errors(text: str) -> list[str]:
    errors = []
    for counter in SAFETY_COUNTERS:
        values = re.findall(rf"^{counter}=(\d+)$", text, flags=re.MULTILINE)
        if values != ["0"]:
            errors.append(counter)
    lowered = text.lower()
    for forbidden in ("status: approved", "authorized now", "call authorization granted"):
        if forbidden in lowered:
            errors.append(forbidden)
    return errors


class Phase3ConnorDecisionWorksheetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKSHEET.read_text()
        cls.normalized = " ".join(cls.text.split())

    def test_is_dated_non_frozen_and_authorizes_nothing(self):
        self.assertIn("**Dated:** 2026-08-10", self.text)
        self.assertIn("NON-FROZEN WORKING RECORD", self.text)
        self.assertIn("NO CALL AUTHORIZATION", self.text)
        self.assertIn("CONFIRMATORY_CALLS=0", self.text)
        self.assertIn("PAID_STUDY_GENERATION_CALLS=0", self.text)
        self.assertIn("SMOKE_CALLS=0", self.text)
        self.assertIn("PROVIDER_PROBE_CALLS=0", self.text)
        self.assertIn("DEEPSEEK_DEVELOPMENT_CALLS=0", self.text)
        self.assertNotIn("Status: APPROVED", self.text)
        self.assertEqual(_authorization_contract_errors(self.text), [])

    def test_authorization_and_counter_mutations_fail(self):
        mutations = [
            self.text.replace(f"{counter}=0", f"{counter}=1", 1)
            for counter in SAFETY_COUNTERS
        ]
        mutations.extend(
            (
                self.text + "\nStatus: APPROVED\n",
                self.text + "\nCall authorization granted\n",
                self.text.replace("It is not authorized yet.", "It is authorized now.", 1),
            )
        )
        for index, mutated in enumerate(mutations):
            self.assertNotEqual(_authorization_contract_errors(mutated), [], index)

    def test_has_one_detailed_section_and_alternatives_for_every_decision(self):
        headings = re.findall(r"^### (D\d{2}) —", self.text, flags=re.MULTILINE)
        self.assertEqual(headings, [f"D{index:02d}" for index in range(1, 16)])
        expected_alternatives = {
            "D01": "ABCD",
            "D02": "ABC",
            "D03": "ABBBC",
            "D04": "ABCDEF",
            "D05": "ABCD",
            "D06": "ABCDE",
            "D07": "ABCD",
            "D08": "ABCD",
            "D09": "ABCDE",
            "D10": "ABCD",
            "D11": "ABCDE",
            "D12": "ABCD",
            "D13": "ABCDEF",
            "D14": "ABCD",
            "D15": "ABCDE",
        }
        for decision in headings:
            section = _section(self.text, decision)
            self.assertIn("**Alternatives:**", section, decision)
            self.assertIn("**Connor's position:**", section, decision)
            self.assertIn("**What remains open:**", section, decision)
            present = "".join(
                re.findall(r"^- ([A-F])(?:\d)?:", section, flags=re.MULTILINE)
            )
            self.assertEqual(present, expected_alternatives[decision], decision)

    def test_section_scoped_positions_and_mutations(self):
        self.assertEqual(_position_contract_errors(self.text), [])
        mutations = {
            "D01": ("choose C with", "choose A with"),
            "D02": ("accept B.", "accept A."),
            "D03": ("keep a common planned", "reject the common planned"),
            "D04": ("accept standard Inkling", "reject standard Inkling"),
            "D05": ("choose A.", "choose B."),
            "D06": ("include Terra in principle", "omit Terra"),
            "D07": ("choose B as primary", "choose C as primary"),
            "D08": ("keep the recommended primary", "replace the recommended primary"),
            "D09": ("absolute error is sensible", "absolute error is rejected"),
            "D10": ("choose B for the first pass", "choose A for the first pass"),
            "D11": ("shared/strict looks right", "panel-specific/flexible is chosen"),
            "D12": ("scheduling is accepted", "scheduling is rejected"),
            "D13": ("reopen D13", "accept the original D13"),
            "D14": ("choose C.", "choose A."),
            "D15": ("It is not authorized yet.", "It is authorized now."),
        }
        for decision, (old, new) in mutations.items():
            section = _section(self.text, decision)
            self.assertIn(old, section, decision)
            mutated_section = section.replace(old, new, 1)
            mutated = self.text.replace(section, mutated_section, 1)
            self.assertNotEqual(_position_contract_errors(mutated), [], decision)

    def test_records_reopened_and_conditional_decisions(self):
        matrix = self.text.split("## Decision record", 1)[1].split(
            "## Detailed decisions", 1
        )[0]
        for decision in ("D03", "D04", "D06", "D09", "D11", "D12", "D13"):
            self.assertRegex(matrix, rf"\| {decision} \|[^\n]*\bOPEN|\| {decision} \|[^\n]*\bREOPENED")
        self.assertRegex(matrix, r"\| D15 \|[^\n]*CONDITIONAL")
        self.assertIn("remains disabled", matrix)

    def test_dataset_record_preserves_shared_anchor_and_provenance_limits(self):
        self.assertIn("same planned 30-item subset of HMMT-2026", self.text)
        self.assertIn("planned 30-of-33 subset", self.text)
        self.assertIn("all 30 HMMT-2025 items", self.text)
        self.assertIn("60-item Tinker scope", self.text)
        self.assertIn("REAP dataset manifest does not exist yet", self.text)
        for dataset in ("AIME", "GPQA-Diamond", "HARP", "GSM8K"):
            self.assertIn(dataset, self.text)

    def test_model_record_covers_catalog_and_closed_model_boundaries(self):
        for exact_id in (
            "thinkingmachines/Inkling",
            "openai/gpt-oss-120b",
            "nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16",
            "Qwen/Qwen3.5-397B-A17B",
            "Qwen/Qwen3.6-35B-A3B",
            "gpt-5.6-terra",
            "gpt-5.6-sol",
            "gpt-5.6-luna",
        ):
            self.assertIn(exact_id, self.text)
        self.assertIn("24 base routes", self.text)
        self.assertIn("Qwen is documented as thinking on/off", self.text)
        self.assertIn("Fable 5 is not a Tinker route", self.text)
        self.assertIn("no current official model named Claude Opus 5", self.text)

    def test_arm_a_candidate_costs_recompute_from_exact_bounds(self):
        items, efforts, caps, replicates, prompt_bound = 30, 2, 2, 8, 8192
        generations = items * efforts * caps * replicates
        prompt_tokens = generations * prompt_bound
        output_tokens = items * efforts * replicates * (4096 + 16384)
        self.assertIn("30 items × 2 endpoint efforts × 2 caps", self.text)
        self.assertIn("× n=8 = 960 generations", self.text)
        self.assertIn(f"{prompt_tokens:,} prompt tokens", self.text)
        self.assertIn(f"{output_tokens:,} output tokens", self.text)
        prompt_m = Decimal(prompt_tokens) / Decimal(1_000_000)
        output_m = Decimal(output_tokens) / Decimal(1_000_000)
        cases = {
            "Inkling n=8 breadth anchor: $60.71": (Decimal("1.87"), Decimal("4.68")),
            "Nemotron Ultra n=8 breadth anchor: $80.78": (
                Decimal("2.49"),
                Decimal("6.225"),
            ),
            "Qwen397 n=8 breadth anchor: $97.32": (
                Decimal("3.00"),
                Decimal("7.50"),
            ),
            "Nemotron Super n=8 breadth anchor: $18.64": (
                Decimal("0.57"),
                Decimal("1.44"),
            ),
            "Qwen3.6 n=8 breadth anchor: $17.37": (
                Decimal("0.54"),
                Decimal("1.335"),
            ),
        }
        for label, (input_rate, output_rate) in cases.items():
            calculated = prompt_m * input_rate + output_m * output_rate
            displayed = Decimal(label.rsplit("$", 1)[1])
            self.assertEqual(calculated.quantize(Decimal("0.01")), displayed, label)
            self.assertIn(label, self.text)

    def test_explains_statistical_and_operational_choices(self):
        for phrase in (
            "independent-draw expected transition mass",
            "random item intercept",
            "item-clustered bootstrap remains primary",
            "one-sided 95% upper confidence bound",
            "31 adjacent comparisons",
            "exact UTF-8 template bytes",
            "sample_index",
            "One batched request cannot have n different request seeds",
            "complete matching line if later text follows it",
            "one and only one billed submission",
        ):
            self.assertIn(phrase, self.normalized)

    def test_deepseek_scope_is_zdr_development_only_and_still_disabled(self):
        for phrase in (
            "accounts/fireworks/models/deepseek-v4-flash",
            "store=False",
            "Chat Completions",
            "$10 cumulative hard ceiling",
            "No research data",
            "No scientific or financial verification",
            "not authorized yet",
        ):
            self.assertIn(phrase, self.normalized)

        governance = "\n".join(
            (ROOT / path).read_text()
            for path in (
                "AGENTS.md",
                "reap/CODEX_BRIEFING.md",
                "reap/09_AGENT_PLAYBOOK.md",
                "reap/claude_project/PROJECT_BRIEF.md",
                "reap/status/phase_status.json",
            )
        )
        lowered = " ".join(governance.lower().split())
        self.assertNotRegex(lowered, r"selected.{0,80}fireworks|fireworks.{0,80}selected")
        self.assertIn("proposed", lowered)
        self.assertIn("disabled", lowered)

    def test_primary_sources_are_linked(self):
        for url in (
            "https://huggingface.co/datasets/MathArena/hmmt_feb_2026/blob/ea21409b2e8362f71205985277b4c084f30c92cc/README.md",
            "https://tinker-docs.thinkingmachines.ai/tinker/models/",
            "https://developers.openai.com/api/docs/models",
            "https://www.anthropic.com/claude/fable",
            "https://fireworks.ai/models/fireworks/deepseek-v4-flash",
            "https://docs.fireworks.ai/guides/security_compliance/data_handling",
        ):
            self.assertIn(url, self.text)


if __name__ == "__main__":
    unittest.main()
