from __future__ import annotations

import unittest

from effort_atlas.analysis import analyze_confirmatory_rows


def _row(
    *,
    item_id: str,
    effort: str,
    cap: int = 4096,
    arm_key: str | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "panel": "panel-a",
        "model": "model-a",
        "provider_route": "route-a",
        "item_id": item_id,
        "effort": effort,
        "cap": cap,
        "replicate": 1,
        "correct": True,
        "extracted_answer_present": True,
        "extracted_answer": "1",
        "finish_reason": "stop",
        "completion_tokens": 8,
    }
    if arm_key is not None:
        row["arm_key"] = arm_key
    return row


class AnalysisSchemaGateTests(unittest.TestCase):
    def test_confirmatory_rows_cannot_fall_back_to_legacy_when_arm_keys_are_removed(
        self,
    ) -> None:
        rows = [
            {
                **_row(item_id="item-a", effort="low"),
                "phase": "main",
                "job_id": "a" * 64,
            },
            {
                **_row(item_id="item-b", effort="high"),
                "phase": "main",
                "job_id": "b" * 64,
            },
        ]

        with self.assertRaisesRegex(ValueError, "arm_key on every"):
            analyze_confirmatory_rows(
                rows,
                planned_rows=rows,
                effort_order=["low", "high"],
                caps=[4096],
                bootstrap_resamples=10,
            )

    def test_legacy_compatibility_requires_explicit_mode_and_rejects_reap_markers(
        self,
    ) -> None:
        legacy_rows = [
            _row(item_id="item-a", effort="low", cap=4096),
            _row(item_id="item-a", effort="low", cap=8192),
            _row(item_id="item-b", effort="high", cap=4096),
            _row(item_id="item-b", effort="high", cap=8192),
        ]
        report = analyze_confirmatory_rows(
            legacy_rows,
            planned_rows=legacy_rows,
            effort_order=["low", "high"],
            caps=[4096, 8192],
            bootstrap_resamples=10,
            input_schema="legacy",
        )
        self.assertEqual(report["assumptions"]["input_schema"], "legacy")

        reap_labeled = [{**row, "phase": "main"} for row in legacy_rows]
        with self.assertRaisesRegex(ValueError, "REAP marker"):
            analyze_confirmatory_rows(
                reap_labeled,
                planned_rows=reap_labeled,
                effort_order=["low", "high"],
                caps=[4096, 8192],
                bootstrap_resamples=10,
                input_schema="legacy",
            )


if __name__ == "__main__":
    unittest.main()
