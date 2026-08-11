import re
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "reap" / "11_PHASE3_DECISION_PACKET_2026-08-08.md"
EXPECTED_DECISION_IDS = tuple(f"D{index:02d}" for index in range(1, 16))
EXPECTED_COUNTERS = {
    "CONFIRMATORY_CALLS": 0,
    "PAID_STUDY_GENERATION_CALLS": 0,
    "SMOKE_CALLS": 0,
    "PROVIDER_PROBE_CALLS": 0,
    "DEEPSEEK_DEVELOPMENT_CALLS": 0,
}
EXPECTED_ARM_ROWS = {
    ("P1", "A"): (60, 2, (4096, 16384), 20, 8192, 4800, 39_321_600, 49_152_000),
    ("P1", "B"): (60, 4, (2048, 4096, 8192, 16384, 32768), 8, 8192, 9600, 78_643_200, 121_896_960),
    ("P1", "C"): (60, 4, (49152,), 8, 8192, 1920, 15_728_640, 94_371_840),
    ("P2", "A"): (60, 2, (4096, 16384), 20, 8192, 4800, 39_321_600, 49_152_000),
    ("P2", "B"): (60, 4, (2048, 4096, 8192, 12288, 16384), 8, 8192, 9600, 78_643_200, 82_575_360),
    ("P2", "C"): (60, 4, (20000,), 8, 8192, 1920, 15_728_640, 38_400_000),
    ("P3", "A"): (30, 2, (4096, 16384), 8, 4096, 960, 3_932_160, 9_830_400),
}
EXPECTED_TOTALS = {
    "P1": (16_320, 133_693_440, 265_420_800, Decimal("1.87"), Decimal("4.68"), Decimal("1492.1761")),
    "P2": (16_320, 133_693_440, 170_127_360, Decimal("0.33"), Decimal("0.84"), Decimal("187.0258")),
    "P3": (960, 3_932_160, 9_830_400, Decimal("2"), Decimal("12"), Decimal("125.8291")),
}
FINAL_DISCLAIMER = (
    "This packet is advisory only. It does not authorize drafting, offline "
    "implementation, smoke, confirmatory collection, a paid provider probe, or spending."
)


def _section(text, heading, next_heading=None):
    start = text.index(heading)
    if next_heading is None:
        return text[start:]
    end = text.index(next_heading, start + len(heading))
    return text[start:end]


def _matrix_rows(text):
    section = _section(text, "## Numbered decision matrix", "## Why these defaults are conservative")
    lines = section.splitlines()
    header = next(line for line in lines if line.startswith("| ID |"))
    assert header == "| ID | Decision and options | Recommended conservative default | Human owner | Status / freeze blocker | Implementation consequence |"
    rows = {}
    for line in lines:
        if re.match(r"^\| D\d{2} \|", line):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            assert len(cells) == 6
            assert cells[0] not in rows
            rows[cells[0]] = cells
    assert tuple(rows) == EXPECTED_DECISION_IDS
    return rows


def _parse_cost_tables(text):
    section = _section(
        text,
        "## Auditable schedule and cost derivation",
        "## Proposed exact first-pass prompt",
    )
    arm_rows = {}
    total_rows = {}
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if re.match(r"^\| P[123] \| [ABC] \|", line):
            assert len(cells) == 11
            panel, arm = cells[:2]
            assert (panel, arm) not in arm_rows
            arm_rows[(panel, arm)] = (
                int(cells[2]),
                int(cells[3]),
                tuple(int(value) for value in cells[4].split(",")),
                int(cells[5]),
                int(cells[6]),
                int(cells[8].replace(",", "")),
                int(cells[9].replace(",", "")),
                int(cells[10].replace(",", "")),
            )
        elif re.match(r"^\| P[123] \| [\d,]+ \|", line):
            assert len(cells) == 9
            panel = cells[0]
            assert panel not in total_rows
            total_rows[panel] = (
                int(cells[1].replace(",", "")),
                int(cells[2].replace(",", "")),
                int(cells[3].replace(",", "")),
                Decimal(cells[4]),
                Decimal(cells[5]),
                cells[6].strip("`"),
                Decimal(cells[7].replace("$", "").replace(",", "")),
                cells[8],
            )
    assert arm_rows == EXPECTED_ARM_ROWS
    assert set(total_rows) == set(EXPECTED_TOTALS)
    return arm_rows, total_rows


def validate_packet(text):
    assert text.startswith("# REAP Phase 3 supervisor decision packet\n\n**Dated:** 2026-08-08\n\n**Status: HUMAN DECISIONS REQUIRED**")
    header = _section(text, "# REAP Phase 3 supervisor decision packet", "## Safety snapshot")
    flat_header = re.sub(r"\s+", " ", header)
    assert "**Purpose:** decision aid for Connor Klann and Chirag Nagpal" in flat_header
    assert "Recommended defaults are not approvals" in flat_header
    assert "Every D01-D15 row remains HUMAN DECISION REQUIRED" in flat_header
    assert not any(line != line.rstrip() for line in text.splitlines())
    for forbidden in (
        r"\bAPPROVED\b",
        r"\bAUTHORIZED\s+FOR\s+EXECUTION\b",
        r"\bEXECUTION\s+(?:IS\s+|NOW\s+)?AUTHORIZED\b",
        r"\bCALLS?\s+(?:ARE\s+|NOW\s+)?AUTHORIZED\b",
        r"\bSMOKE\s+(?:IS\s+|NOW\s+)?AUTHORIZED\b",
        r"\bSPENDING\s+(?:IS\s+|NOW\s+)?AUTHORIZED\b",
        r"\bGLOBAL\s+EXECUTION\s+APPROVAL\b",
    ):
        assert re.search(forbidden, text, re.IGNORECASE) is None

    safety = _section(text, "## Safety snapshot", "## How to read the evidence")
    blocks = re.findall(r"```text\n(.*?)\n```", safety, re.DOTALL)
    assert len(blocks) == 1
    pairs = re.findall(r"^([A-Z_]+)=(\d+)$", blocks[0], re.MULTILINE)
    assert Counter(name for name, _ in pairs) == Counter(EXPECTED_COUNTERS.keys())
    assert {name: int(value) for name, value in pairs} == EXPECTED_COUNTERS
    all_counter_mentions = re.findall(
        r"^(CONFIRMATORY_CALLS|PAID_STUDY_GENERATION_CALLS|SMOKE_CALLS|PROVIDER_PROBE_CALLS|DEEPSEEK_DEVELOPMENT_CALLS)=(\d+)$",
        text,
        re.MULTILINE,
    )
    assert Counter(name for name, _ in all_counter_mentions) == Counter(EXPECTED_COUNTERS.keys())

    rows = _matrix_rows(text)
    for decision_id, cells in rows.items():
        assert cells[3] in {"Connor", "Chirag", "both"}
        assert "HUMAN DECISION REQUIRED" in cells[4]
        assert decision_id in text

    assert "NO SUBSTITUTION" in _section(text, "### Audit 1: preregistration completeness and sequencing", "### Audit 2: merged analysis and schedule capabilities")
    assert "NO SUBSTITUTION" in _section(text, "## Recommended sequencing resolution", "## Numbered decision matrix")
    assert "NO SUBSTITUTION" in rows["D01"][2]
    assert "NO SUBSTITUTION" in _section(text, "## Frozen activation predicates to write after decisions", "## Required artifacts and code after decisions")

    approval = _section(text, "## Copyable approval form")
    blocks = re.findall(r"```text\n(.*?)\n```", approval, re.DOTALL)
    assert len(blocks) == 1
    form = blocks[0]
    choices = re.findall(
        r"^(D\d{2}) .*? \| choice: ([^|]+) \| rationale: (.+)$",
        form,
        re.MULTILINE,
    )
    assert tuple(row[0] for row in choices) == EXPECTED_DECISION_IDS
    assert all(choice.strip() == "PENDING" and rationale.strip() == "PENDING" for _, choice, rationale in choices)
    confirmations = re.findall(r"^- (.+): (.+)$", form, re.MULTILINE)
    assert len(confirmations) == 8
    assert all(value == "PENDING" for _, value in confirmations)
    signoffs = re.findall(r"^(Connor|Chirag) sign-off and timestamp: (.+)$", form, re.MULTILINE)
    assert signoffs == [("Connor", "PENDING"), ("Chirag", "PENDING")]
    assert "Smoke failure action is whole-panel omission with NO SUBSTITUTION: PENDING" in form

    arm_rows, total_rows = _parse_cost_tables(text)
    for (panel, _), (items, efforts, caps, n, prompt_bound, generations, prompt_tokens, output_tokens) in arm_rows.items():
        assert generations == items * efforts * len(caps) * n
        assert prompt_tokens == generations * prompt_bound
        assert output_tokens == items * efforts * n * sum(caps)
        context = {"P1": 65_536, "P2": 32_768, "P3": 1_050_000}[panel]
        assert max(caps) + prompt_bound < context
    for panel, expected in EXPECTED_TOTALS.items():
        generations, prompt_tokens, output_tokens, prefill_rate, sample_rate, formula, reported_cost, stage = total_rows[panel]
        assert (generations, prompt_tokens, output_tokens, prefill_rate, sample_rate, reported_cost) == expected
        assert formula == f"(({prompt_tokens}*{prefill_rate})+({output_tokens}*{sample_rate}))/1000000"
        recomputed = (
            Decimal(prompt_tokens) * prefill_rate + Decimal(output_tokens) * sample_rate
        ) / Decimal(1_000_000)
        assert reported_cost == recomputed.quantize(Decimal("0.0001"))
        assert stage == "before smoke"

    assert "A: efforts 0.7/0.99, caps 4096/16384, n=20" in rows["D04"][2]
    assert "B: efforts 0.1/0.4/0.7/0.99, caps 2048/4096/8192/16384/32768, n=8" in rows["D04"][2]
    assert "C: same four efforts, 49152 large-cap reference, n=8" in rows["D04"][2]
    assert "B: no-sysprompt/low/medium/high, caps 2048/4096/8192/12288/16384, n=8" in rows["D05"][2]
    assert "C: same four efforts, 20000 large-cap reference, n=8" in rows["D05"][2]
    assert "medium/xhigh; caps 4096/16384; n=8 per item/cell; prompt bound 4096 tokens" in rows["D06"][2]

    assert text.rstrip().endswith(FINAL_DISCLAIMER)
    return True


def _replace_nth(text, old, new, occurrence):
    matches = list(re.finditer(re.escape(old), text))
    assert len(matches) >= occurrence
    match = matches[occurrence - 1]
    return text[: match.start()] + new + text[match.end() :]


class Phase3DecisionPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PACKET.read_text(encoding="utf-8")
        cls.flat_text = re.sub(r"\s+", " ", cls.text)

    def test_structural_contract_and_advisory_state(self):
        self.assertTrue(validate_packet(self.text))

    def test_packet_has_no_unresolved_bracket_placeholders(self):
        for placeholder in ("[__]", "[TBD]", "[DECIDE]", "n=__"):
            self.assertNotIn(placeholder, self.text)

    def test_context_budget_and_reference_blockers_are_prominent(self):
        for blocker in (
            "standard GPT-OSS-120B route is 32K context",
            "128K PEFT route is a distinct",
            "Inkling standard route is 64K context",
            "literal 64K output allowance plus a prompt is unsafe",
            "90-item worst-case grid exceeds the $2,000 Tinker ceiling",
            "P3 n=28 exceeds the approximately $200 OpenAI pool",
            "reference-cap length stops remain censored floors",
        ):
            self.assertIn(blocker, self.flat_text)

    def test_required_analysis_terms_and_unimplemented_tests_are_disclosed(self):
        for statement in (
            "item-level empirical-marginal expected mass",
            "item-level independent-draw rescue evidence",
            "method-of-moments variance components are descriptive",
            "KS on common support",
            "absolute truncation-rate error",
            "H6 tolerance is not implemented",
            "H5 monotonicity is not implemented",
        ):
            self.assertIn(statement, self.flat_text)

    def test_sources_artifacts_and_protected_paths_are_present(self):
        for url in (
            "https://tinker-docs.thinkingmachines.ai/tinker/models/",
            "https://developers.openai.com/api/docs/models/gpt-5.6-terra",
            "https://fireworks.ai/models/fireworks/deepseek-v4-flash",
        ):
            self.assertIn(url, self.text)
        self.assertIn("Retrieval date for all route facts: 2026-08-08", self.text)
        self.assertIn("## Required artifacts and code after decisions", self.text)
        for protected in (
            "PREREGISTRATION*.md",
            "confirmatory_artifacts/**",
            "observational/pipeline.py",
            "reap/status/",
            "reap/CODEX_BRIEFING.md",
        ):
            self.assertIn(protected, self.text)

    def test_mutation_matrix_rejects_every_critical_change(self):
        mutations = [
            self.text.replace("D01 sequencing | owner both | choice: PENDING", "D01 sequencing | owner both | choice: APPROVED", 1),
            self.text + "\nGLOBAL EXECUTION APPROVAL\n",
            self.text.replace("CONFIRMATORY_CALLS=0", "CONFIRMATORY_CALLS=0\nCONFIRMATORY_CALLS=1", 1),
            *[_replace_nth(self.text, "NO SUBSTITUTION", "ALTERNATE PATH", index) for index in range(1, 6)],
            self.text.replace("caps 4096/16384, n=20", "caps 4096/16384, n=21", 1),
            self.text.replace("49152 large-cap reference", "49153 large-cap reference", 1),
            self.text.replace("2048/4096/8192/12288/16384", "2048/4096/8192/12289/16384", 1),
            self.text.replace("20000 large-cap reference", "21000 large-cap reference", 1),
            self.text.replace("medium/xhigh; caps 4096/16384; n=8", "medium/xhigh; caps 4096/16384; n=9", 1),
            self.text.replace("| P1 | A | 60 | 2 | 4096,16384 | 20 |", "| P1 | A | 60 | 2 | 4096,16384 | 21 |", 1),
            self.text.replace("| P2 | B | 60 | 4 | 2048,4096,8192,12288,16384 |", "| P2 | B | 60 | 4 | 2048,4096,8192,12289,16384 |", 1),
            self.text.replace("$1,492.1761", "$1,492.1762", 1),
            self.text.replace("Smoke failure action is whole-panel omission with NO SUBSTITUTION: PENDING", "Smoke failure action is whole-panel omission with NO SUBSTITUTION: YES", 1),
            self.text.replace("Connor sign-off and timestamp: PENDING", "Connor sign-off and timestamp: SIGNED", 1),
            self.text + "\nEXECUTION IS AUTHORIZED\n",
        ]
        self.assertEqual(len(mutations), 19)
        for index, mutated in enumerate(mutations, start=1):
            with self.subTest(mutation=index):
                with self.assertRaises(AssertionError):
                    validate_packet(mutated)


if __name__ == "__main__":
    unittest.main()
