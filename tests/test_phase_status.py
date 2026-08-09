from __future__ import annotations

import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from scripts.render_phase_status import MARKER, OUTPUT, SOURCE, TEMPLATE, render, validate_status


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
