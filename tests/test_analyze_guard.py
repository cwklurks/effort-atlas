import json
import tempfile
import unittest
from pathlib import Path

from effort_atlas.analyze import (
    ConfirmatoryRowsUnsupportedError,
    main,
    reject_confirmatory_rows,
)


class AnalyzeGuardTests(unittest.TestCase):
    def test_guard_raises_before_cap_omitting_dedup_can_run(self):
        rows = [
            {"domain": "math", "item_id": "item-a", "effort": "low", "cap": 4096},
            {"domain": "math", "item_id": "item-a", "effort": "low", "cap": 16384},
        ]

        with self.assertRaisesRegex(ConfirmatoryRowsUnsupportedError, "cap"):
            reject_confirmatory_rows(rows)

    def test_guard_allows_legacy_exploratory_rows_without_cap_dimension(self):
        reject_confirmatory_rows(
            [{"domain": "math", "item_id": "item-a", "effort": "low", "max_tokens": 4096}]
        )

    def test_analyze_entry_point_invokes_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "confirmatory.jsonl"
            path.write_text(
                json.dumps(
                    {"domain": "math", "item_id": "item-a", "effort": "low", "cap": 4096}
                )
                + "\n"
            )

            with self.assertRaises(ConfirmatoryRowsUnsupportedError):
                main([str(path)])


if __name__ == "__main__":
    unittest.main()
