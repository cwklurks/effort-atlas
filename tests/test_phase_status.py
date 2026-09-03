from __future__ import annotations

import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from scripts.render_phase_status import (
    MARKER,
    OUTPUT,
    SOURCE,
    TEMPLATE,
    render,
    validate_status,
)

ROOT = Path(__file__).resolve().parents[1]
PROJECT_BRIEF = ROOT / "reap" / "claude_project" / "PROJECT_BRIEF.md"


def discovered_test_counts() -> tuple[int, int]:
    loader = unittest.TestLoader()
    ordinary = loader.discover(
        str(ROOT / "tests"), pattern="test_*.py"
    ).countTestCases()
    exact_lock = loader.discover(
        str(ROOT / "tests"), pattern="tinker_probe_suite.py"
    ).countTestCases()
    return ordinary, exact_lock


class _StatusHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.external_resources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(str(attributes["id"]))
        resource = attributes.get("src") or attributes.get("href")
        if resource and str(resource).startswith(("http://", "https://", "//")):
            self.external_resources.append(str(resource))


class PhaseStatusTests(unittest.TestCase):
    def test_status_data_has_at_most_one_current_active_phase_and_zero_paid_activity(
        self,
    ):
        data = json.loads(SOURCE.read_text())

        validate_status(data)
        self.assertEqual([phase["id"] for phase in data["phases"]], list(range(8)))
        current_phase = data["project"]["current_phase"]
        active = [
            phase["id"] for phase in data["phases"] if phase["status"] == "in_progress"
        ]
        self.assertIn(active, ([], [current_phase]))
        expected_safety = {
            "confirmatory_calls",
            "paid_study_generation_calls",
            "paid_smoke_calls",
            "provider_probe_calls",
            "deepseek_development_calls",
            "confirmatory_spend_usd",
            "frozen_artifact_changes",
        }
        self.assertEqual(set(data["safety"]), expected_safety)
        for key in expected_safety:
            self.assertIn(type(data["safety"][key]), (int, float), key)
            self.assertEqual(data["safety"][key], 0, key)

    def test_status_records_current_dynamic_verification_and_non_authoritative_relay(
        self,
    ):
        data = json.loads(SOURCE.read_text())
        ordinary, exact_lock = discovered_test_counts()
        checkpoint = next(
            row
            for row in data["verification"]
            if row["label"] == "Phase 3 current offline checkpoint"
        )
        relay = next(
            row
            for row in data["verification"]
            if row["label"] == "Bounded Claude/Codex adversarial relay"
        )
        implementation = next(
            row
            for row in data["verification"]
            if row["label"] == "Phase 3 offline implementation"
        )
        final_review = next(
            row
            for row in data["verification"]
            if row["label"] == "Phase 3 implementation adversarial review"
        )

        self.assertIn(
            f"{ordinary} ordinary tests plus {exact_lock} exact-lock Tinker tests",
            checkpoint["result"],
        )
        self.assertIn("completed development relay", relay["result"])
        self.assertIn("non-authoritative", relay["result"])
        self.assertIn("not freeze-eligible", relay["result"])
        self.assertIn("internal CLI request counts remain unverified", relay["result"])
        self.assertNotIn("has not been run", relay["result"])
        for capability in (
            "schedule",
            "manifest",
            "activation",
            "budget",
            "scorer",
            "simulation",
            "dataset",
        ):
            self.assertIn(capability, implementation["result"])
        self.assertIn("non-frozen", implementation["result"])
        self.assertIn("authorizes no", implementation["result"])
        self.assertIn("planning-budget", implementation["result"])
        self.assertIn("not freeze authority", implementation["result"])
        self.assertIn("Phase 4", implementation["result"])
        self.assertEqual(final_review["status"], "passed")
        self.assertIn("f9aef0b", final_review["result"])
        self.assertIn("no critical or warning findings", final_review["result"])
        hardening = next(
            row
            for row in data["activity"]
            if row["title"] == "Phase 3 trust boundaries hardened"
        )
        self.assertIn("not freeze authority", hardening["detail"])
        self.assertIn("Final adversarial review approved", hardening["detail"])
        self.assertIn("every call/spend counter remains zero", hardening["detail"])

        pricing = next(
            row
            for row in data["verification"]
            if row["label"] == "Current OpenAI planning prices"
        )
        self.assertIn("Luna $0.20/$0.02/$1.20", pricing["result"])
        self.assertIn("Terra $2.00/$0.20/$12.00", pricing["result"])
        self.assertIn("planning-only", pricing["result"])
        self.assertIn("no route or portfolio activation", pricing["result"])

    def test_status_records_phase_three_decision_checkpoint_and_zdr_gate(self):
        data = json.loads(SOURCE.read_text())
        checkpoint = next(
            row
            for row in data["verification"]
            if row["label"] == "Phase 2 approved canonical suite"
        )
        phase = next(row for row in data["phases"] if row["id"] == 2)
        fireworks_entry = next(
            row
            for row in data["verification"]
            if row["label"] == "DeepSeek V4 Flash development lane"
        )
        fireworks_decision = next(
            decision for decision in data["decisions"] if "Fireworks ZDR" in decision
        )
        phase_three_checkpoint = next(
            row
            for row in data["verification"]
            if row["label"] == "Phase 3 decision-packet adversarial review"
        )

        self.assertEqual(
            checkpoint["result"],
            "89 ordinary tests plus 26 exact-lock Tinker tests passed; "
            "private 78-row archives verified",
        )
        self.assertEqual(phase["status"], "complete")
        self.assertEqual(phase["progress"], 100)
        self.assertIn("Independent statistical re-review passed", phase["gate"])
        self.assertIn("human-merged", phase["gate"])
        phase_three = next(row for row in data["phases"] if row["id"] == 3)
        self.assertEqual(data["project"]["current_phase"], 3)
        self.assertEqual(phase_three["status"], "in_progress")
        self.assertEqual(phase_three["progress"], 65)
        self.assertEqual(
            phase_three["url"],
            "https://github.com/cwklurks/effort-atlas/pull/6",
        )
        self.assertIn("dataset", phase_three["gate"])
        self.assertIn("statistical choices", phase_three["gate"])
        self.assertIn("human", phase_three["gate"].lower())
        self.assertIn("2b9b161", phase_three_checkpoint["result"])
        self.assertIn("19 / 19 mutations", phase_three_checkpoint["result"])
        self.assertEqual(phase_three_checkpoint["status"], "passed")
        decision_record = next(
            decision for decision in data["decisions"] if "D01-D15" in decision
        )
        self.assertIn("advisory", decision_record)
        self.assertIn("authorize no calls", decision_record)
        activity = next(
            row
            for row in data["activity"]
            if row["title"] == "Phase 3 decision packet technical review passed"
        )
        self.assertEqual(
            activity["title"], "Phase 3 decision packet technical review passed"
        )
        for statement in (fireworks_entry["result"], fireworks_decision):
            self.assertIn("Fireworks ZDR", statement)
            self.assertIn("development-only", statement)
            self.assertIn("disabled", statement)
            self.assertIn("route configuration", statement)
            self.assertIn("hard dollar ceiling", statement)

    def test_status_records_connor_decisions_without_authorizing_execution(self):
        data = json.loads(SOURCE.read_text())
        phase_three = next(row for row in data["phases"] if row["id"] == 3)
        activity = next(
            row
            for row in data["activity"]
            if row["title"] == "Connor's Phase 3 positions recorded"
        )
        record = next(
            decision
            for decision in data["decisions"]
            if "12_PHASE3_CONNOR_DECISION_WORKSHEET_2026-08-10.md" in decision
        )

        self.assertEqual(data["project"]["updated"], "2026-08-20")
        self.assertIn("benchmark chapter", data["project"]["summary"])
        self.assertIn("HMMT-2026 item 25", phase_three["summary"])
        self.assertIn("dataset", phase_three["gate"])
        self.assertIn(
            "no review, report, or Linux handoff authorizes a call",
            phase_three["gate"],
        )
        self.assertIn("$2", activity["detail"])
        self.assertIn("no call", activity["detail"].lower())
        self.assertIn("non-frozen", record.lower())
        self.assertIn("no call", record.lower())

        scope_record = next(
            decision
            for decision in data["decisions"]
            if "23_BENCHMARK_SCOPE_DECISION_2026-08-20.md" in decision
        )
        self.assertIn("exploratory public archives", scope_record)
        self.assertIn("controlled-effect denominator", scope_record)
        self.assertIn("human-pending", scope_record)
        self.assertIn("authorizes no calls", scope_record)

        integrated_record = next(
            decision
            for decision in data["decisions"]
            if "13_PHASE3_INTEGRATED_RECOMMENDATION_2026-08-10.md" in decision
        )
        integrated_activity = next(
            row
            for row in data["activity"]
            if row["title"]
            == "Integrated recommendation and external-review prompt prepared"
        )
        self.assertIn("separate-model review", integrated_record)
        self.assertIn("not a human decision", integrated_record)
        self.assertIn("symbolic HMMT grading", integrated_activity["detail"])
        self.assertIn("authorizes no call", integrated_activity["detail"])

    def test_canonical_brief_does_not_repeat_superseded_route_or_budget_summary(self):
        text = PROJECT_BRIEF.read_text()
        design_summary = text.split("## REAP (Phase II) design summary", 1)[1].split(
            "## Positioning", 1
        )[0]
        normalized_summary = " ".join(design_summary.split())

        self.assertNotIn("uncapped reference (64k", normalized_summary)
        self.assertNotIn("Estimated cost ≈ $1,030", normalized_summary)
        self.assertIn("large-cap reference", normalized_summary)
        self.assertIn("human-pending", normalized_summary)
        self.assertIn("11_PHASE3_DECISION_PACKET_2026-08-08.md", normalized_summary)

    def test_rendered_page_is_current_self_contained_and_accessible_by_landmark(self):
        rendered = render()
        parser = _StatusHTMLParser()
        parser.feed(rendered)

        self.assertNotIn(MARKER, rendered)
        self.assertEqual(OUTPUT.read_text(), rendered)
        self.assertEqual(parser.external_resources, [])
        self.assertTrue(
            {"main", "phases", "workstreams", "verification", "activity"} <= parser.ids
        )
        self.assertIn('aria-live="polite"', rendered)
        self.assertIn('aria-label="Safety counters"', rendered)
        self.assertIn(
            'progress.setAttribute("aria-label", `Phase ${phase.id} progress`);',
            rendered,
        )
        self.assertIn("prefers-reduced-motion", rendered)

    def test_renderer_rejects_multiple_active_phases(self):
        data = json.loads(SOURCE.read_text())
        data["phases"][1]["status"] = "in_progress"
        data["phases"][2]["status"] = "in_progress"

        with self.assertRaisesRegex(ValueError, "at most one phase"):
            validate_status(data)

    def test_renderer_escapes_script_closing_sequences_in_data(self):
        data = json.loads(SOURCE.read_text())
        data["project"]["summary"] = "safe </script><script>alert(1)</script>"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "status.json"
            source.write_text(json.dumps(data))
            rendered = render(source=source, template=TEMPLATE)

        payload = rendered.split(
            '<script type="application/json" id="status-data">', 1
        )[1].split("</script>", 1)[0]
        self.assertNotIn("</script>", payload)
        self.assertIn("<\\/script>", payload)


if __name__ == "__main__":
    unittest.main()
