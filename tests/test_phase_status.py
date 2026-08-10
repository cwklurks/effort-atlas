from __future__ import annotations

import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from scripts.render_phase_status import MARKER, OUTPUT, SOURCE, TEMPLATE, render, validate_status

ROOT = Path(__file__).resolve().parents[1]
PROJECT_BRIEF = ROOT / "reap" / "claude_project" / "PROJECT_BRIEF.md"


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
    def test_status_data_has_at_most_one_current_active_phase_and_zero_paid_activity(self):
        data = json.loads(SOURCE.read_text())

        validate_status(data)
        self.assertEqual([phase["id"] for phase in data["phases"]], list(range(8)))
        current_phase = data["project"]["current_phase"]
        active = [phase["id"] for phase in data["phases"] if phase["status"] == "in_progress"]
        self.assertIn(active, ([], [current_phase]))
        self.assertEqual(data["safety"]["confirmatory_calls"], 0)
        self.assertEqual(data["safety"]["confirmatory_spend_usd"], 0)
        self.assertEqual(data["safety"]["paid_smoke_calls"], 0)
        self.assertEqual(data["safety"]["frozen_artifact_changes"], 0)

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
        self.assertEqual(phase_three["progress"], 45)
        self.assertEqual(
            phase_three["url"],
            "https://github.com/cwklurks/effort-atlas/pull/6",
        )
        self.assertIn("separate model", phase_three["gate"])
        self.assertIn("Codex audits", phase_three["gate"])
        self.assertIn("human", phase_three["gate"].lower())
        self.assertIn("2b9b161", phase_three_checkpoint["result"])
        self.assertIn("19 / 19 mutations", phase_three_checkpoint["result"])
        self.assertEqual(phase_three_checkpoint["status"], "passed")
        decision_record = next(
            decision
            for decision in data["decisions"]
            if "D01-D15" in decision
        )
        self.assertIn("advisory", decision_record)
        self.assertIn("authorize no calls", decision_record)
        activity = next(
            row
            for row in data["activity"]
            if row["title"] == "Phase 3 decision packet technical review passed"
        )
        self.assertEqual(activity["title"], "Phase 3 decision packet technical review passed")
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

        self.assertEqual(data["project"]["updated"], "2026-08-10")
        self.assertIn("portfolio", data["project"]["summary"])
        self.assertIn("30-of-33 HMMT-2026", phase_three["summary"])
        self.assertIn("separate model", phase_three["gate"])
        self.assertIn("no review artifact authorizes a call", phase_three["gate"])
        self.assertIn("$2", activity["detail"])
        self.assertIn("no call", activity["detail"].lower())
        self.assertIn("non-frozen", record.lower())
        self.assertIn("no call", record.lower())

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
        self.assertTrue({"main", "phases", "workstreams", "verification", "activity"} <= parser.ids)
        self.assertIn('aria-live="polite"', rendered)
        self.assertIn('aria-label="Safety counters"', rendered)
        self.assertIn(
            'progress.setAttribute("aria-label", `Phase ${phase.id} progress`);', rendered
        )
        self.assertIn('prefers-reduced-motion', rendered)

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

        payload = rendered.split('<script type="application/json" id="status-data">', 1)[1].split(
            "</script>", 1
        )[0]
        self.assertNotIn("</script>", payload)
        self.assertIn("<\\/script>", payload)


if __name__ == "__main__":
    unittest.main()
